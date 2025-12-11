"""
Vector Store module for RAG (Retrieval Augmented Generation).
Uses Milvus for vector storage and Google's embedding API.
"""

import os
from typing import List, Dict, Optional
from datetime import datetime
from pymilvus import (
    connections,
    Collection,
    FieldSchema,
    CollectionSchema,
    DataType,
    utility
)
import google.generativeai as genai


class VectorStore:
    """
    Vector store for storing and retrieving conversation messages using embeddings.
    Uses Milvus for vector storage and enables RAG by finding semantically similar past messages.
    """
    
    # Embedding dimension for Google's text-embedding-004
    EMBEDDING_DIM = 768
    
    def __init__(
        self,
        host: str = "localhost",
        port: str = "19530",
        collection_name: str = "chat_messages",
        api_key: Optional[str] = None
    ):
        """
        Initialize the Milvus vector store.
        
        Args:
            host: Milvus server host
            port: Milvus server port
            collection_name: Name of the collection to use
            api_key: Google API key for embeddings
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name
        
        # Initialize Google Generative AI for embeddings
        api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        
        # Connect to Milvus
        self._connect()
        
        # Initialize collection
        self._init_collection()
        
        print(f"[VectorStore] Initialized Milvus connection to {host}:{port}")
    
    def _connect(self):
        """Establish connection to Milvus server."""
        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port
            )
            print(f"[VectorStore] Connected to Milvus at {self.host}:{self.port}")
        except Exception as e:
            print(f"[VectorStore] Connection error: {e}")
            raise
    
    def _init_collection(self):
        """Initialize the Milvus collection with schema."""
        # Check if collection exists
        if utility.has_collection(self.collection_name):
            self.collection = Collection(self.collection_name)
            self.collection.load()
            print(f"[VectorStore] Loaded existing collection: {self.collection_name}")
            return
        
        # Define schema
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
            FieldSchema(name="room_id", dtype=DataType.INT64),
            FieldSchema(name="author", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="message_type", dtype=DataType.VARCHAR, max_length=32),
            FieldSchema(name="timestamp", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.EMBEDDING_DIM)
        ]
        
        schema = CollectionSchema(
            fields=fields,
            description="Chat messages for RAG"
        )
        
        # Create collection
        self.collection = Collection(
            name=self.collection_name,
            schema=schema
        )
        
        # Create index on embedding field for fast similarity search
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        self.collection.create_index(
            field_name="embedding",
            index_params=index_params
        )
        
        # Load collection into memory
        self.collection.load()
        
        print(f"[VectorStore] Created new collection: {self.collection_name}")
    
    def _get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using Google's embedding model.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding
        """
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"[VectorStore] Embedding error: {e}")
            return [0.0] * self.EMBEDDING_DIM
    
    def _get_query_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a query (uses different task type for better retrieval).
        
        Args:
            text: Query text to embed
            
        Returns:
            List of floats representing the embedding
        """
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_query"
            )
            return result['embedding']
        except Exception as e:
            print(f"[VectorStore] Query embedding error: {e}")
            return [0.0] * self.EMBEDDING_DIM
    
    def add_message(
        self,
        message_id: str,
        room_id: int,
        author: str,
        content: str,
        timestamp: datetime,
        message_type: str = "user"
    ) -> bool:
        """
        Add a message to the vector store.
        
        Args:
            message_id: Unique message ID
            room_id: Room the message belongs to
            author: Message author
            content: Message content
            timestamp: Message timestamp
            message_type: Type of message (user, ai, system)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Skip system messages and very short messages
            if message_type == "system" or len(content.strip()) < 5:
                return False
            
            # Truncate content if too long
            content_truncated = content[:4000] if len(content) > 4000 else content
            
            # Generate embedding
            embedding = self._get_embedding(content_truncated)
            
            # Insert into Milvus
            data = [
                [message_id],
                [room_id],
                [author[:128]],
                [content_truncated],
                [message_type],
                [timestamp.isoformat()],
                [embedding]
            ]
            
            self.collection.insert(data)
            self.collection.flush()
            
            print(f"[VectorStore] Added message: '{content[:50]}...' from {author}")
            return True
            
        except Exception as e:
            print(f"[VectorStore] Error adding message: {e}")
            return False
    
    def search_similar(
        self,
        query: str,
        room_id: Optional[int] = None,
        n_results: int = 5,
        exclude_ids: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Search for messages similar to the query.
        
        Args:
            query: Search query
            room_id: Optional room ID to filter by
            n_results: Number of results to return
            exclude_ids: Message IDs to exclude from results
            
        Returns:
            List of similar messages with metadata
        """
        try:
            # Generate query embedding
            query_embedding = self._get_query_embedding(query)
            
            # Build filter expression
            expr = None
            if room_id is not None:
                expr = f"room_id == {room_id}"
            
            # Search parameters
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 16}
            }
            
            # Perform search
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=n_results + len(exclude_ids or []),
                expr=expr,
                output_fields=["id", "room_id", "author", "content", "message_type", "timestamp"]
            )
            
            # Format results
            similar_messages = []
            for hit in results[0]:
                msg_id = hit.entity.get("id")
                
                # Skip excluded IDs
                if exclude_ids and msg_id in exclude_ids:
                    continue
                
                similar_messages.append({
                    "id": msg_id,
                    "content": hit.entity.get("content"),
                    "metadata": {
                        "room_id": hit.entity.get("room_id"),
                        "author": hit.entity.get("author"),
                        "message_type": hit.entity.get("message_type"),
                        "timestamp": hit.entity.get("timestamp")
                    },
                    "distance": hit.distance
                })
                
                if len(similar_messages) >= n_results:
                    break
            
            return similar_messages
            
        except Exception as e:
            print(f"[VectorStore] Search error: {e}")
            return []
    
    def get_context_for_query(
        self,
        query: str,
        room_id: Optional[int] = None,
        n_results: int = 3,
        max_context_length: int = 1000
    ) -> str:
        """
        Get formatted context string for RAG.
        
        Args:
            query: The user's query
            room_id: Optional room ID to filter by
            n_results: Number of similar messages to include
            max_context_length: Maximum length of context string
            
        Returns:
            Formatted context string for the AI prompt
        """
        similar = self.search_similar(query, room_id, n_results)
        
        if not similar:
            return ""
        
        context_parts = []
        total_length = 0
        
        for msg in similar:
            author = msg['metadata'].get('author', 'Unknown')
            content = msg['content']
            
            # Check if adding this would exceed max length
            part = f"[Previous] {author}: {content}"
            if total_length + len(part) > max_context_length:
                break
            
            context_parts.append(part)
            total_length += len(part)
        
        if not context_parts:
            return ""
        
        return "Relevant past context:\n" + "\n".join(context_parts)
    
    def get_stats(self) -> Dict:
        """
        Get statistics about the vector store.
        
        Returns:
            Dictionary with stats
        """
        doc_count = 0
        if hasattr(self, 'doc_collection') and self.doc_collection:
            doc_count = self.doc_collection.num_entities
        
        return {
            "total_messages": self.collection.num_entities,
            "total_document_chunks": doc_count,
            "host": self.host,
            "port": self.port,
            "collection_name": self.collection_name
        }
    
    # ==================== Document Collection Methods ====================
    
    def _init_document_collection(self):
        """Initialize the document collection for storing PDF chunks."""
        doc_collection_name = "documents"
        
        if utility.has_collection(doc_collection_name):
            self.doc_collection = Collection(doc_collection_name)
            self.doc_collection.load()
            print(f"[VectorStore] Loaded existing document collection: {doc_collection_name}")
            return
        
        # Define schema for documents
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
            FieldSchema(name="doc_name", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
            FieldSchema(name="page_num", dtype=DataType.INT64),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
            FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.EMBEDDING_DIM)
        ]
        
        schema = CollectionSchema(
            fields=fields,
            description="Document chunks for RAG"
        )
        
        self.doc_collection = Collection(
            name=doc_collection_name,
            schema=schema
        )
        
        # Create index
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        self.doc_collection.create_index(
            field_name="embedding",
            index_params=index_params
        )
        
        self.doc_collection.load()
        print(f"[VectorStore] Created new document collection: {doc_collection_name}")
    
    def ensure_document_collection(self):
        """Ensure document collection is initialized."""
        if not hasattr(self, 'doc_collection') or self.doc_collection is None:
            self._init_document_collection()
    
    def add_document_chunk(
        self,
        chunk_id: str,
        doc_name: str,
        chunk_index: int,
        page_num: int,
        content: str,
        created_at: str
    ) -> bool:
        """
        Add a document chunk to the vector store.
        
        Args:
            chunk_id: Unique chunk ID
            doc_name: Name of the source document
            chunk_index: Index of chunk within document
            page_num: Page number in source document
            content: Text content of the chunk
            created_at: Timestamp string
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.ensure_document_collection()
            
            # Skip very short content
            if len(content.strip()) < 10:
                return False
            
            # Truncate content if too long
            content_truncated = content[:8000] if len(content) > 8000 else content
            
            # Generate embedding
            embedding = self._get_embedding(content_truncated)
            
            # Insert into Milvus
            data = [
                [chunk_id],
                [doc_name[:256]],
                [chunk_index],
                [page_num],
                [content_truncated],
                [created_at],
                [embedding]
            ]
            
            self.doc_collection.insert(data)
            return True
            
        except Exception as e:
            print(f"[VectorStore] Error adding document chunk: {e}")
            return False
    
    def flush_documents(self):
        """Flush document collection to persist changes."""
        if hasattr(self, 'doc_collection') and self.doc_collection:
            self.doc_collection.flush()
            print(f"[VectorStore] Flushed document collection")
    
    def search_documents(
        self,
        query: str,
        n_results: int = 5,
        doc_name: Optional[str] = None
    ) -> List[Dict]:
        """
        Search for document chunks similar to the query.
        
        Args:
            query: Search query
            n_results: Number of results to return
            doc_name: Optional document name to filter by
            
        Returns:
            List of similar document chunks with metadata
        """
        try:
            self.ensure_document_collection()
            
            # Generate query embedding
            query_embedding = self._get_query_embedding(query)
            
            # Build filter expression
            expr = None
            if doc_name:
                expr = f'doc_name == "{doc_name}"'
            
            # Search parameters
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 16}
            }
            
            # Perform search
            results = self.doc_collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=n_results,
                expr=expr,
                output_fields=["id", "doc_name", "chunk_index", "page_num", "content", "created_at"]
            )
            
            # Format results
            similar_chunks = []
            for hit in results[0]:
                similar_chunks.append({
                    "id": hit.entity.get("id"),
                    "doc_name": hit.entity.get("doc_name"),
                    "chunk_index": hit.entity.get("chunk_index"),
                    "page_num": hit.entity.get("page_num"),
                    "content": hit.entity.get("content"),
                    "created_at": hit.entity.get("created_at"),
                    "score": hit.distance
                })
            
            return similar_chunks
            
        except Exception as e:
            print(f"[VectorStore] Document search error: {e}")
            return []
    
    def get_document_context(
        self,
        query: str,
        n_results: int = 3,
        max_context_length: int = 2000
    ) -> str:
        """
        Get formatted document context string for RAG.
        
        Args:
            query: The user's query
            n_results: Number of document chunks to include
            max_context_length: Maximum length of context string
            
        Returns:
            Formatted context string for the AI prompt
        """
        similar = self.search_documents(query, n_results)
        
        if not similar:
            return ""
        
        context_parts = []
        total_length = 0
        
        for chunk in similar:
            doc_name = chunk.get('doc_name', 'Unknown')
            page_num = chunk.get('page_num', '?')
            content = chunk.get('content', '')
            
            # Check if adding this would exceed max length
            part = f"[From {doc_name}, page {page_num}]: {content}"
            if total_length + len(part) > max_context_length:
                # Try to add truncated version
                remaining = max_context_length - total_length - 50
                if remaining > 100:
                    part = f"[From {doc_name}, page {page_num}]: {content[:remaining]}..."
                    context_parts.append(part)
                break
            
            context_parts.append(part)
            total_length += len(part)
        
        if not context_parts:
            return ""
        
        return "Relevant document context:\n" + "\n\n".join(context_parts)
    
    def close(self):
        """Close the Milvus connection."""
        connections.disconnect("default")
        print("[VectorStore] Disconnected from Milvus")
