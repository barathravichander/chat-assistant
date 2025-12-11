from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import json
import asyncio
from datetime import datetime
import uuid
import os
import httpx
from dotenv import load_dotenv

from models import (
    Room, Message, MessageType, JoinRoomRequest, SendMessageRequest, 
    CreateRoomRequest, AIMessageRequest, ContextResponse, ContextMessage
)
from ai_agent import AIAgent
from vector_store import VectorStore

# Load environment variables
load_dotenv()

app = FastAPI(title="RE Assistant API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
rooms: Dict[int, Room] = {}
messages: Dict[int, List[Message]] = {}
room_id_counter = 1
active_connections: Dict[str, WebSocket] = {}

# Initialize AI Agent with Phi/Agno + Google Gemini, Currently setup done for Google Key. 
try:
    ai_agent = AIAgent(api_key=os.getenv("GOOGLE_API_KEY"))
    print("[OK] AI Agent initialized with Phi framework + Google Gemini")
except Exception as e:
    print(f"[WARN] Warning: AI Agent initialization failed: {e}")
    ai_agent = None

# Initialize Vector Store for RAG
vector_store = None
try:
    milvus_host = os.getenv("MILVUS_HOST", "localhost")
    milvus_port = os.getenv("MILVUS_PORT", "19530")
    vector_store = VectorStore(
        host=milvus_host,
        port=milvus_port,
        api_key=os.getenv("GOOGLE_API_KEY")
    )
    print(f"[OK] Vector Store initialized (Milvus at {milvus_host}:{milvus_port})")
except Exception as e:
    print(f"[WARN] Vector Store initialization failed (RAG disabled): {e}")
    vector_store = None

@app.get("/")
async def root():
    return {"message": "REChat API", "status": "running"}

@app.get("/rooms")
async def get_rooms():
    """Get all available chat rooms"""
    return list(rooms.values())

@app.post("/rooms/create")
async def create_room(request: CreateRoomRequest):
    """Create a new chat room"""
    global room_id_counter
    
    new_room = Room(
        id=room_id_counter,
        name=request.name,
        description=request.description,
        users=[]
    )
    
    rooms[room_id_counter] = new_room
    messages[room_id_counter] = []
    room_id_counter += 1
    
    return {"status": "created", "room": new_room}

@app.delete("/rooms/{room_id}")
async def delete_room(room_id: int):
    """Delete a chat room"""
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    del rooms[room_id]
    if room_id in messages:
        del messages[room_id]
    
    return {"status": "deleted", "room_id": room_id}

@app.get("/rooms/{room_id}/messages")
async def get_room_messages(room_id: int):
    """Get all messages for a specific room"""
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return messages.get(room_id, [])

@app.post("/rooms/join")
async def join_room(request: JoinRoomRequest):
    """Join a chat room"""
    if request.room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[request.room_id]
    if request.username not in room.users:
        room.users.append(request.username)
    
    # Create system message
    system_msg = Message(
        id=str(uuid.uuid4()),
        room_id=request.room_id,
        author="System",
        content=f"{request.username} joined the room",
        timestamp=datetime.now(),
        message_type=MessageType.SYSTEM
    )
    messages[request.room_id].append(system_msg)
    
    # Broadcast to all connections
    await broadcast_message(request.room_id, system_msg)
    
    return {"status": "joined", "room": room}

@app.post("/rooms/leave")
async def leave_room(request: JoinRoomRequest):
    """Leave a chat room"""
    if request.room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[request.room_id]
    if request.username in room.users:
        room.users.remove(request.username)
    
    # Create system message
    system_msg = Message(
        id=str(uuid.uuid4()),
        room_id=request.room_id,
        author="System",
        content=f"{request.username} left the room",
        timestamp=datetime.now(),
        message_type=MessageType.SYSTEM
    )
    messages[request.room_id].append(system_msg)
    
    await broadcast_message(request.room_id, system_msg)
    
    return {"status": "left"}

@app.post("/messages/send")
async def send_message(request: SendMessageRequest):
    """Send a message to a room"""
    if request.room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Create user message
    user_msg = Message(
        id=str(uuid.uuid4()),
        room_id=request.room_id,
        author=request.username,
        content=request.content,
        timestamp=datetime.now(),
        message_type=MessageType.USER
    )
    messages[request.room_id].append(user_msg)
    
    # Store message in vector store for RAG
    if vector_store:
        try:
            vector_store.add_message(
                message_id=user_msg.id,
                room_id=request.room_id,
                author=request.username,
                content=request.content,
                timestamp=user_msg.timestamp,
                message_type="user"
            )
        except Exception as e:
            print(f"[WARN] Failed to store message in vector store: {e}")
    
    # Broadcast user message
    await broadcast_message(request.room_id, user_msg)
    
    # Trigger N8N workflow if AI should potentially respond
    if ai_agent and ai_agent.should_respond(request.content):
        print(f"[AI] AI should respond to: '{request.content}'")
        # Try N8N workflow first
        n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL")
        print(f"   N8N_WEBHOOK_URL from env: {n8n_webhook_url}")
        if n8n_webhook_url:
            try:
                asyncio.create_task(trigger_n8n_workflow(
                    webhook_url=n8n_webhook_url,
                    room_id=request.room_id,
                    message=request.content,
                    author=request.username,
                    timestamp=user_msg.timestamp
                ))
            except Exception as e:
                print(f"N8N webhook failed, using embedded AI: {e}")
                # Fallback to embedded AI if N8N fails
                await asyncio.sleep(1.5)
                
                # Get conversation context
                recent_messages = messages[request.room_id][-10:]
                context = [{
                    "author": msg.author, 
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                } for msg in recent_messages]
                
                # Generate AI response using embedded agent
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
                    model = genai.GenerativeModel('gemini-flash-latest')
                    
                    system_prompt = """You are Jarvis, a knowledgeable renewable energy expert.
                    
Guidelines:
- Keep responses concise (2-3 sentences)
- Focus on solar, wind, hydro, and other renewable energy topics
- Be helpful and encouraging
- Provide accurate information"""
                    
                    # Get RAG context from vector store (chat history + documents)
                    rag_context = ""
                    doc_context = ""
                    if vector_store:
                        try:
                            rag_context = vector_store.get_context_for_query(
                                query=request.content,
                                room_id=request.room_id,
                                n_results=3
                            )
                            if rag_context:
                                print(f"[RAG] Retrieved chat context: {rag_context[:100]}...")
                        except Exception as rag_err:
                            print(f"[WARN] RAG retrieval failed: {rag_err}")
                        
                        # Also get document context
                        try:
                            doc_context = vector_store.get_document_context(
                                query=request.content,
                                n_results=3
                            )
                            if doc_context:
                                print(f"[RAG] Retrieved document context: {doc_context[:100]}...")
                        except Exception as doc_err:
                            print(f"[WARN] Document retrieval failed: {doc_err}")
                    
                    context_str = "\n".join([f"{msg['author']}: {msg['content']}" for msg in context[-5:]])
                    
                    # Build prompt with RAG context (documents + chat history)
                    combined_context = "\n\n".join(filter(None, [doc_context, rag_context]))
                    if combined_context:
                        prompt = f"{system_prompt}\n\n{combined_context}\n\nRecent conversation:\n{context_str}\n\nRespond to: {request.content}"
                    else:
                        prompt = f"{system_prompt}\n\nRecent conversation:\n{context_str}\n\nRespond to: {request.content}"
                    
                    response = model.generate_content(prompt)
                    ai_response = response.text
                    
                    ai_msg = Message(
                        id=str(uuid.uuid4()),
                        room_id=request.room_id,
                        author="Jarvis",
                        content=ai_response,
                        timestamp=datetime.now(),
                        message_type=MessageType.AI
                    )
                    messages[request.room_id].append(ai_msg)
                    await broadcast_message(request.room_id, ai_msg)
                except Exception as ai_error:
                    print(f"Embedded AI also failed: {ai_error}")
        else:
            # No N8N URL configured, use embedded AI
            await asyncio.sleep(1.5)
            
            # Get conversation context
            recent_messages = messages[request.room_id][-10:]
            context = [{
                "author": msg.author, 
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            } for msg in recent_messages]
            
            # Generate AI response using embedded agent
            try:
                import google.generativeai as genai
                genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
                model = genai.GenerativeModel('gemini-flash-latest')
                
                system_prompt = """You are Jarvis, a knowledgeable renewable energy expert.
                
Guidelines:
- Keep responses concise (2-3 sentences)
- Focus on solar, wind, hydro, and other renewable energy topics
- Be helpful and encouraging
- Provide accurate information"""
                
                # Get RAG context from vector store (chat history + documents)
                rag_context = ""
                doc_context = ""
                if vector_store:
                    try:
                        rag_context = vector_store.get_context_for_query(
                            query=request.content,
                            room_id=request.room_id,
                            n_results=3
                        )
                        if rag_context:
                            print(f"[RAG] Retrieved chat context: {rag_context[:100]}...")
                    except Exception as rag_err:
                        print(f"[WARN] RAG retrieval failed: {rag_err}")
                    
                    # Also get document context
                    try:
                        doc_context = vector_store.get_document_context(
                            query=request.content,
                            n_results=3
                        )
                        if doc_context:
                            print(f"[RAG] Retrieved document context: {doc_context[:100]}...")
                    except Exception as doc_err:
                        print(f"[WARN] Document retrieval failed: {doc_err}")
                
                context_str = "\n".join([f"{msg['author']}: {msg['content']}" for msg in context[-5:]])
                
                # Build prompt with RAG context (documents + chat history)
                combined_context = "\n\n".join(filter(None, [doc_context, rag_context]))
                if combined_context:
                    prompt = f"{system_prompt}\n\n{combined_context}\n\nRecent conversation:\n{context_str}\n\nRespond to: {request.content}"
                else:
                    prompt = f"{system_prompt}\n\nRecent conversation:\n{context_str}\n\nRespond to: {request.content}"
                
                response = model.generate_content(prompt)
                ai_response = response.text
                
                ai_msg = Message(
                    id=str(uuid.uuid4()),
                    room_id=request.room_id,
                    author="Jarvis",
                    content=ai_response,
                    timestamp=datetime.now(),
                    message_type=MessageType.AI
                )
                messages[request.room_id].append(ai_msg)
                await broadcast_message(request.room_id, ai_msg)
            except Exception as ai_error:
                print(f"Embedded AI failed: {ai_error}")
    
    return {"status": "sent", "message": user_msg}

@app.get("/api/context/{room_id}")
async def get_conversation_context(room_id: int, limit: int = 10):
    """Get recent conversation context for N8N AI agent"""
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = rooms[room_id]
    room_messages = messages.get(room_id, [])
    
    # Get last N messages
    recent_messages = room_messages[-limit:] if len(room_messages) > limit else room_messages
    
    # Convert to ContextMessage format
    context_messages = [
        ContextMessage(
            author=msg.author,
            content=msg.content,
            timestamp=msg.timestamp,
            message_type=msg.message_type
        )
        for msg in recent_messages
    ]
    
    return ContextResponse(
        room_id=room_id,
        room_name=room.name,
        messages=context_messages,
        total_messages=len(room_messages)
    )

@app.post("/api/ai-message")
async def receive_ai_message(request: AIMessageRequest):
    """Webhook endpoint for N8N to post AI-generated messages"""
    if request.room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Create AI message
    ai_msg = Message(
        id=str(uuid.uuid4()),
        room_id=request.room_id,
        author=request.author,
        content=request.content,
        timestamp=datetime.now(),
        message_type=MessageType.AI
    )
    messages[request.room_id].append(ai_msg)
    
    # Broadcast AI message to all connected clients
    await broadcast_message(request.room_id, ai_msg)
    
    return {"status": "sent", "message": ai_msg}


# ==================== Document API Endpoints ====================

@app.post("/api/documents/ingest")
async def ingest_documents():
    """Trigger document ingestion from Files folder"""
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not available")
    
    try:
        from document_processor import DocumentProcessor
        
        # Get Files directory path
        files_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Files")
        
        if not os.path.isdir(files_dir):
            raise HTTPException(status_code=404, detail=f"Files directory not found: {files_dir}")
        
        # Find PDF files
        pdf_files = [f for f in os.listdir(files_dir) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            return {"status": "no_files", "message": "No PDF files found in Files directory"}
        
        # Process documents
        processor = DocumentProcessor(chunk_size=500, chunk_overlap=50)
        
        total_chunks = 0
        processed_docs = []
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(files_dir, pdf_file)
            try:
                chunks = processor.process_pdf(pdf_path)
                
                stored = 0
                for chunk in chunks:
                    success = vector_store.add_document_chunk(
                        chunk_id=chunk.id,
                        doc_name=chunk.doc_name,
                        chunk_index=chunk.chunk_index,
                        page_num=chunk.page_num,
                        content=chunk.content,
                        created_at=chunk.created_at.isoformat()
                    )
                    if success:
                        stored += 1
                
                total_chunks += stored
                processed_docs.append({"file": pdf_file, "chunks": stored})
                
            except Exception as e:
                processed_docs.append({"file": pdf_file, "error": str(e)})
        
        # Flush to persist
        vector_store.flush_documents()
        
        return {
            "status": "completed",
            "total_chunks": total_chunks,
            "documents": processed_docs
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.get("/api/documents/search")
async def search_documents(query: str, limit: int = 5):
    """Search documents by semantic query"""
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not available")
    
    try:
        results = vector_store.search_documents(query=query, n_results=limit)
        return {
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/api/documents/stats")
async def get_document_stats():
    """Get document store statistics"""
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not available")
    
    try:
        stats = vector_store.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    """WebSocket connection for real-time updates"""
    await websocket.accept()
    active_connections[username] = websocket
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages if needed
    except WebSocketDisconnect:
        del active_connections[username]

async def broadcast_message(room_id: int, message: Message):
    """Broadcast a message to all connected clients"""
    room = rooms.get(room_id)
    if not room:
        return
    
    # Convert message to dict and handle datetime serialization
    msg_dict = message.model_dump()
    msg_dict['timestamp'] = msg_dict['timestamp'].isoformat()
    
    message_data = json.dumps({
        "type": "message",
        "room_id": room_id,
        "message": msg_dict
    })
    
    # Send to all users in the room
    disconnected = []
    for username in room.users:
        if username in active_connections:
            try:
                await active_connections[username].send_text(message_data)
            except:
                disconnected.append(username)
    
    # Clean up disconnected users
    for username in disconnected:
        if username in active_connections:
            del active_connections[username]

async def trigger_n8n_workflow(webhook_url: str, room_id: int, message: str, author: str, timestamp: datetime):
    """Trigger N8N workflow via webhook"""
    try:
        print(f"[N8N] Triggering N8N workflow for message: '{message}' from {author} in room {room_id}")
        print(f"   Webhook URL: {webhook_url}")
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            payload = {
                "room_id": room_id,
                "message": message,
                "author": author,
                "timestamp": timestamp.isoformat()
            }
            print(f"   Payload: {payload}")
            
            response = await client.post(webhook_url, json=payload)
            print(f"   [OK] N8N responded with status: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   [ERROR] Error triggering N8N workflow: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
