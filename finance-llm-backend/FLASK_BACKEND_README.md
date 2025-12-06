# Flask Backend - PDF RAG System with Mistral 7.2B

Complete Flask backend for a PDF-based RAG (Retrieval-Augmented Generation) system using Mistral 7.2B via Ollama, pgvector for semantic search, and Redis for session management.

## 🚀 Features

- **PDF Ingestion Pipeline**: Upload PDFs, extract text/tables, chunk, embed, and store in pgvector
- **RAG-based Chat**: Semantic retrieval + LLM generation with Mistral 7.2B
- **Session Management**: Redis-based chat history with configurable TTL
- **Production-Ready**: Error handling, logging, health checks, CORS support

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running the Server](#running-the-server)
5. [API Endpoints](#api-endpoints)
6. [Architecture](#architecture)
7. [Testing](#testing)

---

## Prerequisites

### Required Services

1. **PostgreSQL with pgvector** (Supabase or local)
2. **Ollama with Mistral 7.2B**
3. **Redis** (optional, for chat history)
4. **Python 3.11+**

### Install Ollama and Mistral

```bash
# Install Ollama (see https://ollama.ai)
# For Windows: Download from https://ollama.ai/download

# Pull Mistral 7.2B model
ollama pull mistral:7b

# Verify it's running
curl http://localhost:11434/api/tags
```

### Install Redis (Optional)

```bash
# Windows (using Chocolatey)
choco install redis-64

# Or use Docker
docker run -d -p 6379:6379 redis:alpine

# Verify
redis-cli ping  # Should return PONG
```

---

## Installation

### 1. Clone and Setup

```bash
cd finance-llm-backend

# Create virtual environment
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Supabase/PostgreSQL credentials
# See Configuration section below

# Initialize pgvector schema
python init_database.py
```

---

## Configuration

### Environment Variables

Edit `.env` file with your settings:

```env
# Flask
FLASK_ENV=development
FLASK_PORT=5000
CORS_ORIGINS=http://localhost:3000

# Ollama (Mistral 7.2B)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:7b
OLLAMA_TIMEOUT=120

# Embedding Model
EMBEDDING_MODEL=intfloat/e5-large-v2

# Chunking
CHUNK_SIZE=500
CHUNK_OVERLAP=100

# Retrieval
RETRIEVAL_TOP_K=5
RETRIEVAL_MIN_SIMILARITY=0.5

# Redis (optional)
REDIS_HOST=localhost
REDIS_PORT=6379

# PostgreSQL/Supabase
SUPABASE_DB_HOST=db.xxxxx.supabase.co
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=your-password
SUPABASE_DB_SSLMODE=require
```

### Key Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| `OLLAMA_MODEL` | LLM model name | `mistral:7b` |
| `EMBEDDING_MODEL` | Embedding model | `intfloat/e5-large-v2` |
| `CHUNK_SIZE` | Tokens per chunk | 500 |
| `CHUNK_OVERLAP` | Token overlap | 100 |
| `RETRIEVAL_TOP_K` | Chunks to retrieve | 5 |
| `RETRIEVAL_MIN_SIMILARITY` | Min similarity score | 0.5 |
| `REDIS_SESSION_TTL` | Session timeout (seconds) | 3600 |

---

## Running the Server

### Development Mode

```bash
# Activate venv if not already
venv\Scripts\activate

# Run Flask server
python app.py
```

Server starts on `http://localhost:5000`

### Production Mode

```bash
# Set production environment
$env:FLASK_ENV="production"

# Run with gunicorn (Linux/Mac)
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Or use waitress (Windows)
pip install waitress
waitress-serve --port=5000 app:app
```

---

## API Endpoints

### 1. Upload PDF (`/api/upload`)

**POST** - Upload and process PDF file

**Request:**
```http
POST /api/upload
Content-Type: multipart/form-data

file: <PDF file>
company: "PTCL" (optional)
period: "2024Q3" (optional)
```

**Response:**
```json
{
  "success": true,
  "message": "PDF processed and ingested successfully",
  "statistics": {
    "filename": "report.pdf",
    "company": "PTCL",
    "period": "2024Q3",
    "text_chunks": 45,
    "table_chunks": 12,
    "total_chunks": 57,
    "embedding_dimension": 1024
  }
}
```

**Process Flow:**
1. Upload PDF → Save temporarily
2. Extract text and tables using PyMuPDF/pdfplumber
3. Clean text and extract metadata (company, period)
4. Chunk text (500 tokens, 100 overlap)
5. Serialize table rows
6. Generate embeddings (intfloat/e5-large-v2, 1024-dim)
7. Store in pgvector with metadata
8. Return statistics

**cURL Example:**
```bash
curl -X POST http://localhost:5000/api/upload \
  -F "file=@report.pdf" \
  -F "company=PTCL" \
  -F "period=2024Q3"
```

---

### 2. Chat Query (`/api/chat`)

**POST** - Query documents with RAG

**Request:**
```json
{
  "query": "What is the revenue for Q3 2024?",
  "session_id": "user-123-session-456",
  "company": "PTCL",
  "period": "2024Q3",
  "top_k": 5
}
```

**Response:**
```json
{
  "answer": "Based on the Q3 2024 financial report, PTCL's revenue was PKR 35.2 billion, representing a 12% increase compared to Q3 2023...",
  "sources": [
    {
      "company": "PTCL",
      "period": "2024Q3",
      "content_type": "text_chunk",
      "similarity": 0.87,
      "snippet": "Revenue for the quarter ended September 30, 2024..."
    }
  ],
  "metadata": {
    "chunks_retrieved": 5,
    "session_id": "user-123-session-456",
    "model": "mistral:7b",
    "filters_applied": {
      "company": "PTCL",
      "period": "2024Q3"
    }
  }
}
```

**Process Flow:**
1. Receive user query
2. Generate query embedding (1024-dim)
3. Search pgvector for similar chunks (cosine similarity)
4. Filter by company/period if specified
5. Retrieve top-k most similar chunks (default: 5)
6. Load chat history from Redis
7. Build prompt with:
   - System prompt (financial assistant instructions)
   - Retrieved context chunks
   - Chat history
   - User query
8. Call Mistral 7.2B via Ollama
9. Save conversation to Redis
10. Return answer + sources

**System Prompt:**
```
You are a financial-document assistant. Your job is to answer questions about company reports, including financial statements, cash flow, and management discussion.

Key Guidelines:
1. Always prioritize accuracy and refer to the retrieved context
2. If data is numerical, summarize it clearly with proper formatting
3. If the answer is not present, explicitly state: "I cannot find this information in the provided documents"
4. When citing figures, include the reporting period
5. Be concise but comprehensive
6. If asked about trends, compare data across periods
7. Always maintain a professional, factual tone
```

**cURL Example:**
```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the revenue for Q3 2024?",
    "session_id": "user-123",
    "company": "PTCL"
  }'
```

---

### 3. Additional Endpoints

#### Get Chat History
```http
GET /api/chat/history/<session_id>
```

#### Clear Chat History
```http
DELETE /api/chat/history/<session_id>
```

#### List Documents
```http
GET /api/documents?company=PTCL&limit=100
```

#### Health Check
```http
GET /api/health
```

Returns status of database, LLM, and retriever services.

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Flask Application                       │
├─────────────────────────────────────────────────────────────┤
│  Routes:                                                     │
│  • /api/upload    (PDF ingestion)                          │
│  • /api/chat      (RAG query)                              │
│  • /api/health    (Health check)                           │
└─────────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌───────────┐   ┌──────────┐   ┌──────────────┐
    │ Extractor │   │ Chunker  │   │  Embedder    │
    │ (PDF)     │   │ (500tok) │   │  (e5-large)  │
    └───────────┘   └──────────┘   └──────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   PostgreSQL    │
                  │   + pgvector    │
                  │  (1024-dim)     │
                  └─────────────────┘
                           │
                           ▼
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌───────────┐   ┌──────────┐
    │Retriever │───▶│LLM Client │◀──│  Redis   │
    │ (Search) │    │(Mistral7B)│   │(History) │
    └──────────┘    └───────────┘   └──────────┘
```

### File Structure

```
finance-llm-backend/
├── app.py                      # Flask application entry
├── config.py                   # Configuration management
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
│
├── routes/
│   ├── pdf_routes.py          # /api/upload endpoint
│   ├── chat_routes.py         # /api/chat endpoint
│   └── health_routes.py       # /api/health endpoint
│
├── core/
│   ├── extractor/             # PDF extraction
│   │   ├── pdf_reader.py
│   │   ├── cleaner.py
│   │   └── chunker.py
│   │
│   ├── embeddings/            # Embedding generation
│   │   ├── embedder.py
│   │   └── table_embeddings.py
│   │
│   ├── database/              # pgvector storage
│   │   ├── config.py
│   │   ├── schema.py
│   │   └── pgvector_store.py
│   │
│   ├── rag/                   # RAG components
│   │   ├── retriever.py       # Semantic search
│   │   └── llm_client.py      # Ollama integration
│   │
│   └── utils/
│       ├── logger.py
│       ├── metadata.py
│       └── validators.py
│
└── uploads/                   # Temporary PDF storage
```

---

## Testing

### 1. Health Check

```bash
curl http://localhost:5000/api/health
```

Expected output:
```json
{
  "status": "healthy",
  "services": {
    "database": {"status": "healthy"},
    "llm": {"status": "healthy", "model": "mistral:7b"},
    "retriever": {"status": "healthy", "embedding_model": "intfloat/e5-large-v2"}
  }
}
```

### 2. Upload Test PDF

```bash
curl -X POST http://localhost:5000/api/upload \
  -F "file=@test_report.pdf" \
  -F "company=TestCorp" \
  -F "period=2024Q3"
```

### 3. Query Test

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the revenue?",
    "company": "TestCorp",
    "period": "2024Q3"
  }'
```

### 4. Integration Test Script

```python
# test_api.py
import requests

BASE_URL = "http://localhost:5000/api"

# Test health
response = requests.get(f"{BASE_URL}/health")
print("Health:", response.json())

# Test upload
with open("test.pdf", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/upload",
        files={"file": f},
        data={"company": "TestCorp"}
    )
print("Upload:", response.json())

# Test chat
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "query": "What is the revenue?",
        "company": "TestCorp"
    }
)
print("Chat:", response.json())
```

---

## Troubleshooting

### Ollama Not Running

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama service
# Windows: Run Ollama from Start Menu
# Linux/Mac: ollama serve
```

### Model Not Found

```bash
# Pull Mistral model
ollama pull mistral:7b

# List installed models
ollama list
```

### Database Connection Error

```bash
# Test connection
python -c "import psycopg2; from config import config; conn = psycopg2.connect(config.get_db_connection_string()); print('✓ Connected'); conn.close()"

# Reinitialize schema
python init_database.py --recreate
```

### Redis Connection Error

```bash
# Check Redis is running
redis-cli ping

# If Redis is unavailable, chat will work without history
# Check logs: "Redis not available: ... Chat history will be disabled"
```

### Slow Embedding Generation

- Use GPU if available (requires `sentence-transformers` with CUDA)
- Reduce `CHUNK_SIZE` in config
- Use smaller embedding model (lower dimensions)

---

## Production Deployment

### 1. Security Checklist

- [ ] Change `SECRET_KEY` in .env
- [ ] Set `FLASK_ENV=production`
- [ ] Use strong database passwords
- [ ] Enable SSL/TLS for database
- [ ] Configure firewall rules
- [ ] Set up Redis password

### 2. Performance Optimization

```env
# Production settings
FLASK_ENV=production
OLLAMA_TIMEOUT=60
CHUNK_SIZE=400  # Smaller chunks = faster processing
RETRIEVAL_TOP_K=3  # Fewer chunks = faster response
```

### 3. Logging

```python
# Configure in production
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log'
)
```

### 4. Docker Deployment (Optional)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

---

## License

Part of the finance-llm-backend RAG pipeline project.

## Support

For issues or questions:
1. Check troubleshooting section
2. Review logs in console/app.log
3. Test with `/api/health` endpoint
4. Verify all services are running (Ollama, PostgreSQL, Redis)
