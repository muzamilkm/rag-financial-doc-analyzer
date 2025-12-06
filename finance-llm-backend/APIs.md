# Finance LLM Backend APIs

This document describes all available APIs in the Finance LLM Backend system. The base URL for all endpoints is `http://localhost:5000/api`.

---

## 1. Health Check Endpoints

### 1.1 Comprehensive Health Check

**Endpoint:** `GET /health`

**Description:** Performs a comprehensive health check of all services (database, LLM, retriever).

**Response:**

```json
{
  "status": "healthy",
  "services": {
    "database": {
      "status": "healthy"
    },
    "llm": {
      "status": "healthy",
      "model": "mistral"
    },
    "retriever": {
      "status": "healthy",
      "embedding_model": "all-minilm-l6-v2"
    }
  }
}
```

**cURL Request:**

```bash
curl -X GET http://localhost:5000/api/health
```

---

### 1.2 Simple Ping

**Endpoint:** `GET /ping`

**Description:** Simple endpoint to check if the server is running.

**Response:**

```json
{
  "status": "ok"
}
```

**cURL Request:**

```bash
curl -X GET http://localhost:5000/api/ping
```

---

## 2. PDF Upload & Document Management Endpoints

### 2.1 Upload and Process PDF

**Endpoint:** `POST /upload`

**Description:** Uploads a PDF file, extracts text and tables, chunks the content, generates embeddings, and stores in the vector database.

**Request Parameters (Form Data):**

- `file` (required): PDF file to upload
- `company` (optional): Company name (if not provided, will be extracted from document)
- `period` (optional): Reporting period (e.g., "2024Q3", if not provided, will be extracted)

**Response:**

```json
{
  "success": true,
  "message": "PDF processed and ingested successfully",
  "statistics": {
    "filename": "financial_report.pdf",
    "company": "Acme Corp",
    "period": "2024Q3",
    "text_chunks": 250,
    "table_chunks": 45,
    "total_chunks": 295,
    "embedding_dimension": 384
  }
}
```

**cURL Request:**

```bash
# Upload with automatic metadata extraction
curl -X POST -F "file=@/path/to/financial_report.pdf" \
  http://localhost:5000/api/upload

# Upload with explicit metadata
curl -X POST -F "file=@/path/to/financial_report.pdf" \
  -F "company=Acme Corp" \
  -F "period=2024Q3" \
  http://localhost:5000/api/upload
```

---

### 2.2 List Documents

**Endpoint:** `GET /documents`

**Description:** Lists all ingested documents with their metadata. Can be filtered by company.

**Query Parameters:**

- `company` (optional): Filter documents by company name
- `limit` (optional): Maximum number of results (default: 100)

**Response (without company filter):**

```json
{
  "total_documents": 125,
  "companies": ["Acme Corp", "TechCorp Inc", "Global Finance Ltd"]
}
```

**Response (with company filter):**

```json
{
  "documents": [
    {
      "id": 1,
      "company": "Acme Corp",
      "period": "2024Q3",
      "content_type": "financial_report"
    },
    {
      "id": 2,
      "company": "Acme Corp",
      "period": "2024Q4",
      "content_type": "financial_report"
    }
  ],
  "count": 2
}
```

**cURL Requests:**

```bash
# List all companies with document counts
curl -X GET http://localhost:5000/api/documents

# List documents for a specific company
curl -X GET "http://localhost:5000/api/documents?company=Acme%20Corp"

# List documents with limit
curl -X GET "http://localhost:5000/api/documents?company=Acme%20Corp&limit=50"
```

---

## 3. Chat & Query Endpoints

### 3.1 Ask a Question (Chat)

**Endpoint:** `POST /chat`

**Description:** Process a user query using RAG (Retrieval-Augmented Generation). Retrieves relevant document chunks, generates context-aware answers using Ollama LLM, and maintains conversation history.

**Request Body (JSON):**

```json
{
  "query": "What was the revenue in Q3 2024?",
  "session_id": "user-123-session-1",
  "company": "Acme Corp",
  "period": "2024Q3",
  "top_k": 5
}
```

**Request Parameters:**

- `query` (required): User's question
- `chat_id` (optional): UUID of existing chat (creates new if omitted)
- `company` (optional): Filter by company name
- `period` (optional): Filter by period (e.g., "2024Q3")
- `top_k` (optional): Number of chunks to retrieve (default: 5)

**Response:**

```json
{
  "chat_id": "550e8400-e29b-41d4-a716-446655440000",
  "answer": "Based on the financial documents, the revenue for Q3 2024 was $2.5 billion...",
  "sources": [
    {
      "company": "Acme Corp",
      "period": "2024Q3",
      "content_type": "text_chunk",
      "similarity": 0.892,
      "snippet": "Q3 2024 Revenue: $2.5 billion..."
    }
  ],
  "metadata": {
    "chunks_retrieved": 2,
    "model": "mistral"
  }
}
```

**cURL Examples:**

```bash
# Create new chat
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What was the revenue in Q3 2024?"}'

# Continue existing chat
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "How does this compare to Q2?", "chat_id": "550e8400-e29b-41d4-a716-446655440000"}'
```

---

### 3.2 Get All Chats

**Endpoint:** `GET /chats`

**Description:** Retrieves all chat sessions with metadata from PostgreSQL database.

**Response:**

```json
{
  "chats": [
    {
      "chat_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "What was the revenue in Q3 2024?",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:35:00Z",
      "message_count": 4,
      "last_message_at": "2024-01-15T10:35:00Z"
    },
    {
      "chat_id": "660e8400-e29b-41d4-a716-446655440001",
      "title": "Analyze operating expenses",
      "created_at": "2024-01-14T09:20:00Z",
      "updated_at": "2024-01-14T09:25:00Z",
      "message_count": 2,
      "last_message_at": "2024-01-14T09:25:00Z"
    }
  ],
  "count": 2
}
```

**cURL Request:**

```bash
curl -X GET http://localhost:5000/api/chats
```

---

### 3.3 Get Single Chat

**Endpoint:** `GET /chats/<chat_id>`

**Description:** Retrieves a specific chat session with all messages from PostgreSQL database.

**Path Parameters:**

- `chat_id` (required): UUID of the chat session

**Response:**

```json
{
  "chat_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "What was the revenue in Q3 2024?",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z",
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "What was the revenue in Q3 2024?",
      "sources": null,
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "Based on the financial documents, the revenue for Q3 2024 was $2.5 billion...",
      "sources": [
        {
          "company": "Acme Corp",
          "period": "2024Q3",
          "similarity": 0.892
        }
      ],
      "created_at": "2024-01-15T10:30:05Z"
    },
    {
      "id": 3,
      "role": "user",
      "content": "How does this compare to Q4 2024?",
      "sources": null,
      "created_at": "2024-01-15T10:35:00Z"
    },
    {
      "id": 4,
      "role": "assistant",
      "content": "Q4 2024 revenue was $2.8 billion, showing a 12% increase compared to Q3...",
      "sources": [
        {
          "company": "Acme Corp",
          "period": "2024Q4",
          "similarity": 0.878
        }
      ],
      "created_at": "2024-01-15T10:35:05Z"
    }
  ]
}
```

**cURL Request:**

```bash
curl -X GET http://localhost:5000/api/chats/550e8400-e29b-41d4-a716-446655440000
```

---

### 3.4 Delete Single Chat

**Endpoint:** `DELETE /chats/<chat_id>`

**Description:** Deletes a specific chat session and all its messages from PostgreSQL database.

**Path Parameters:**

- `chat_id` (required): UUID of the chat session

**Response:**

```json
{
  "success": true,
  "message": "Chat session 550e8400-e29b-41d4-a716-446655440000 deleted successfully"
}
```

**cURL Request:**

```bash
curl -X DELETE http://localhost:5000/api/chats/550e8400-e29b-41d4-a716-446655440000
```

---

### 3.5 Delete All Chats

**Endpoint:** `DELETE /chats`

**Description:** Deletes all chat sessions and messages from PostgreSQL database.

**Response:**

```json
{
  "success": true,
  "message": "Deleted 15 chat sessions",
  "count": 15
}
```

**cURL Request:**

```bash
curl -X DELETE http://localhost:5000/api/chats
```

---

### 3.6 Update Chat Title

**Endpoint:** `PUT /chats/<chat_id>/title`

**Description:** Updates the title of a specific chat session.

**Path Parameters:**

- `chat_id` (required): UUID of the chat session

**Request Body:**

```json
{
  "title": "Q3 2024 Revenue Analysis"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Chat title updated successfully"
}
```

**cURL Request:**

```bash
curl -X PUT http://localhost:5000/api/chats/550e8400-e29b-41d4-a716-446655440000/title \
  -H "Content-Type: application/json" \
  -d '{"title": "Q3 2024 Revenue Analysis"}'
```

---

## Error Responses

### Common Error Codes

**400 - Bad Request**

```json
{
  "error": "No query provided"
}
```

**413 - Payload Too Large**

```json
{
  "error": "File too large",
  "message": "The uploaded file exceeds the maximum size limit"
}
```

**500 - Internal Server Error**

```json
{
  "error": "PDF processing failed",
  "message": "Detailed error message"
}
```

**503 - Service Unavailable**

```json
{
  "status": "degraded",
  "services": {
    "database": {
      "status": "unhealthy",
      "error": "Connection refused"
    }
  }
}
```

---

## Configuration

- **Base URL:** `http://localhost:5000/api`
- **Max File Size:** 16 MB
- **Allowed Extensions:** PDF only
- **Embedding Model:** intfloat/e5-large-v2 (1024-dim)
- **LLM Model:** Mistral (via Ollama)
- **Database:** PostgreSQL with pgvector
- **Storage:** All chats persisted in PostgreSQL

---

## Testing Quick Start

```bash
# 1. Check server health
curl http://localhost:5000/api/health

# 2. Upload a PDF
curl -X POST -F "file=@report.pdf" http://localhost:5000/api/upload

# 3. Create new chat
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What was the revenue?"}'

# 4. List all chats
curl http://localhost:5000/api/chats

# 5. Get specific chat
curl http://localhost:5000/api/chats/YOUR_CHAT_ID

# 6. Delete a chat
curl -X DELETE http://localhost:5000/api/chats/YOUR_CHAT_ID

# 7. Delete all chats
curl -X DELETE http://localhost:5000/api/chats
```

---

## CORS Configuration

The API is configured to allow requests from the React frontend. Allowed origins and methods are configurable via environment variables:

- **CORS_ORIGINS:** Comma-separated list of allowed origins (default: `http://localhost:3000`)
- **Allowed Methods:** GET, POST, PUT, DELETE
- **Allowed Headers:** Content-Type, Authorization
