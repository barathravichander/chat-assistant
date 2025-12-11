# Agentic RAG Architecture

This document describes the Agentic RAG (Retrieval Augmented Generation) architecture implemented in the Jarvis Chat Assistant.

---

## What is Agentic RAG?

**Agentic RAG** extends traditional RAG by adding autonomous decision-making capabilities. Instead of blindly retrieving and responding to every query, an Agentic RAG system:

- **Reasons** about user intent before acting
- **Decides** whether a response is warranted
- **Chooses** which tools (retrieval, generation) to use
- **Acts** autonomously based on context

This transforms a passive pipeline into an intelligent agent.

---

## Why This System is Agentic

| Traditional RAG | Agentic RAG (This System) |
|----------------|---------------------------|
| Responds to every message | AI decides IF to respond |
| No intent understanding | Classifies user intent first |
| Fixed pipeline execution | Conditional execution based on reasoning |
| Passive tool | Active agent with judgment |

### Key Agentic Capabilities

1. **Intent Classification**: Uses LLM to understand if user needs help
2. **Autonomous Decision**: Chooses to respond or stay silent
3. **Tool Selection**: Uses vector store only when relevant
4. **Context Awareness**: Considers full conversation history

---

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  USER MESSAGE                                                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 0: AI INTENT CLASSIFICATION                               │
│  ─────────────────────────────────────────────────────────────  │
│  LLM analyzes the message to determine:                         │
│  • Is user asking a question?                                   │
│  • Seeking information or help?                                 │
│  • Showing confusion?                                           │
│  • Engaging in meaningful dialogue?                             │
│                                                                 │
│  This is what makes it AGENTIC - the AI reasons before acting   │
└──────────────┬──────────────────────────┬───────────────────────┘
               │                          │
               │ YES                      │ NO
               │ (user needs assistance)  │ (casual message)
               │                          │
               ▼                          ▼
┌──────────────────────────┐    ┌─────────────────────────────────┐
│  Continue to             │    │  MESSAGE STORED, AI SILENT      │
│  RAG pipeline            │    │  ─────────────────────────────  │
│                          │    │  • Message saved to chat        │
│                          │    │  • Stored in vector store       │
│                          │    │  • Available for future context │
│                          │    │  • AI does NOT reply            │
└──────────────┬───────────┘    └─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: EMBED QUERY                                            │
│  ─────────────────────────────────────────────────────────────  │
│  Convert user question to vector embedding                      │
│  Model: Google text-embedding-004 (768 dimensions)              │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: VECTOR SIMILARITY SEARCH                               │
│  ─────────────────────────────────────────────────────────────  │
│  Database: Milvus Vector Store                                  │
│  Metric: Cosine Similarity                                      │
│                                                                 │
│  ┌─────────────────────┐    ┌─────────────────────┐            │
│  │ Documents           │    │ Chat History        │            │
│  │ (ingested PDFs)     │    │ (past messages)     │            │
│  └──────────┬──────────┘    └──────────┬──────────┘            │
│             │                          │                        │
│             └──────────┬───────────────┘                        │
│                        ▼                                        │
│  Returns: Top 3 most semantically similar chunks from each      │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: BUILD PROMPT                                           │
│  ─────────────────────────────────────────────────────────────  │
│  Combines:                                                      │
│  • System prompt (agent personality and guidelines)             │
│  • Document context (retrieved PDF chunks)                      │
│  • Chat context (retrieved past conversations)                  │
│  • User question (original message)                             │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: GENERATE & SEND RESPONSE                               │
│  ─────────────────────────────────────────────────────────────  │
│  LLM generates answer grounded in retrieved context             │
│  Response sent to user via WebSocket                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Components

### Vector Store (Milvus)

| Collection | Purpose | Schema |
|------------|---------|--------|
| `documents` | Ingested PDF chunks | id, doc_name, chunk_index, page_num, content, embedding |
| `chat_messages` | Conversation history | id, room_id, author, content, message_type, timestamp, embedding |

---

## Semantic Embedding Architecture

This system uses **Semantic Embedding with Asymmetric Retrieval** - a REFRAG-inspired approach where queries and documents are embedded differently for optimal retrieval.

### Embedding Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│  DOCUMENT INGESTION (One-time)                                  │
│  ─────────────────────────────────────────────────────────────  │
│  PDF → Extract Text → Chunk → Embed → Store in Milvus          │
│                                 │                               │
│                    task_type: "retrieval_document"              │
│                    (optimized for being found)                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  QUERY TIME (Per request)                                       │
│  ─────────────────────────────────────────────────────────────  │
│  User Question → Embed → Search Milvus → Return similar chunks  │
│                    │                                            │
│       task_type: "retrieval_query"                              │
│       (optimized for finding documents)                         │
└─────────────────────────────────────────────────────────────────┘
```

### Why Asymmetric Embedding (REFRAG Style)?

| Aspect | Symmetric Embedding | Asymmetric Embedding (This System) |
|--------|--------------------|------------------------------------|
| Same embedding for query & doc | ✓ | ✗ |
| Optimized for retrieval | ✗ | ✓ |
| Task-specific embeddings | ✗ | ✓ |
| Better semantic matching | ✗ | ✓ |

**REFRAG Principle**: Queries and documents have different characteristics:
- **Queries** are short, question-like, seeking information
- **Documents** are longer, declarative, containing information

Using different `task_type` parameters aligns embeddings for better cross-modal matching.

### Chunking Strategy

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Chunk Size | 500 characters | Balanced context without exceeding token limits |
| Chunk Overlap | 50 characters | Preserves context across chunk boundaries |
| Min Chunk Length | 20 characters | Filters out noise/empty chunks |

```
Document: "Carbon capture technology involves... [500 chars] ...reducing emissions."
                                              ↓
Chunk 1: "Carbon capture technology involves... [500 chars]"
Chunk 2: [50 char overlap] "...involves post-combustion... [450 chars]"
Chunk 3: [50 char overlap] "...combustion capture which... [450 chars]"
```

---

## Models Used

### Embedding Model

| Property | Value |
|----------|-------|
| **Model** | `text-embedding-004` |
| **Provider** | Google Generative AI |
| **Dimensions** | 768 |
| **Max Input** | 2,048 tokens |
| **Task Types** | `retrieval_document`, `retrieval_query` |

**Why text-embedding-004?**
- State-of-the-art semantic understanding
- Optimized for retrieval with task-specific modes
- Low latency, high quality embeddings
- Native support for asymmetric retrieval

### Intent Classification Model

| Property | Value |
|----------|-------|
| **Model** | `gemini-flash-latest` |
| **Provider** | Google Generative AI |
| **Purpose** | Classify if AI should respond |
| **Temperature** | 0.1 (deterministic) |
| **Max Tokens** | 10 (YES/NO only) |

### Response Generation Model

| Property | Value |
|----------|-------|
| **Model** | `gemini-flash-latest` |
| **Provider** | Google Generative AI |
| **Purpose** | Generate grounded responses |
| **Context** | System prompt + retrieved chunks + query |

---

## Similarity Search

| Property | Value |
|----------|-------|
| **Metric** | Cosine Similarity |
| **Index Type** | IVF_FLAT |
| **nlist** | 128 clusters |
| **nprobe** | 16 (search probes) |
| **Top-K** | 3 results per collection |

```
Query Vector: [0.12, -0.34, 0.56, ...]
              ↓
        Cosine Similarity
              ↓
┌─────────────────────────────────────────┐
│  Results ranked by similarity score     │
│  1. Chunk A (score: 0.92)              │
│  2. Chunk B (score: 0.87)              │
│  3. Chunk C (score: 0.81)              │
└─────────────────────────────────────────┘
```

---

## Comparison with Other Approaches

```
┌─────────────────────────────────────────────────────────────────┐
│  SIMPLE CHATBOT                                                 │
│  User → LLM → Response                                          │
│  (No retrieval, no memory, no decision-making)                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  TRADITIONAL RAG                                                │
│  User → Embed → Search → LLM → Response                         │
│  (Retrieval but no decision-making, always responds)            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  AGENTIC RAG (This System)                                      │
│  User → AI Decides → [Embed → Search] → LLM → Response          │
│                 ↓                                               │
│           OR Silent                                             │
│  (Retrieval WITH autonomous decision-making)                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Usage

### Start the System

```bash
# 1. Start Milvus vector store
docker-compose up -d

# 2. Ingest documents (one-time)
python3 backend/ingest_documents.py

# 3. Start the application
./start_all.sh
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/documents/ingest` | POST | Ingest PDFs from Files folder |
| `/api/documents/search?query=...` | GET | Search documents |
| `/api/documents/stats` | GET | Vector store statistics |

---

## Benefits of Agentic RAG

1. **Reduced Noise**: AI doesn't respond to every "ok" or "thanks"
2. **Better UX**: Feels like a smart assistant, not a chatbot
3. **Efficient**: Vector search only when needed
4. **Contextual**: Uses documents + chat history for grounded responses
5. **Scalable**: Add more documents, AI automatically uses them
