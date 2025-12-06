# Finance LLM Backend - RAG-based Document Assistant

A local, on-premise RAG (Retrieval-Augmented Generation) system for processing and querying PDF financial reports. Built with Flask, Ollama, ChromaDB, and Redis.

## 🎯 Overview

This backend service provides intelligent document processing and conversational AI capabilities for PDF documents, with a focus on financial reports. It combines modern LLM technology with vector search to enable accurate, context-aware responses.

### Key Features

- **PDF Processing Pipeline**: Automated extraction, cleaning, chunking, and embedding generation
- **RAG System**: Retrieval-augmented generation for accurate, context-based answers
- **Conversation Memory**: Redis-backed chat history for multi-turn conversations
- **Vector Storage**: ChromaDB for efficient semantic search
- **Local LLM**: Ollama integration for on-premise AI inference

## 🏗️ Architecture

### Technology Stack

- **Framework**: Flask (Python)
- **LLM Engine**: Ollama
- **Vector Database**: ChromaDB
- **Memory Store**: Redis
- **PDF Processing**: PyMuPDF / pdfplumber
- **Embeddings**: Ollama embedding models

### System Flow

```
PDF Upload → Extraction → Cleaning → Chunking → Embedding → ChromaDB
                                                                  ↓
User Query → Redis (History) → Retrieval ← ChromaDB
                ↓
         Prompt Builder → Ollama → Response → Redis (Store)
```

## 📁 Project Structure

```
llm-finance-backend/
│
├── app.py                    # Flask application entry point
├── config.py                 # Configuration and environment variables
│
├── core/                     # Core business logic
│   ├── extractor/            # PDF processing
│   │   ├── pdf_reader.py     # PDF text and table extraction
│   │   ├── cleaner.py        # Text cleaning and normalization
│   │   └── chunker.py        # Text chunking with metadata
│   │
│   ├── embeddings/           # Embedding generation and storage
│   │   ├── embedder.py       # Ollama embedding client
│   │   └── vectorstore.py    # ChromaDB interface
│   │
│   ├── rag/                  # RAG pipeline
│   │   ├── retriever.py      # Semantic search and retrieval
│   │   ├── prompt_builder.py # Prompt construction with context
│   │   └── llm_client.py     # Ollama LLM client
│   │
│   ├── memory/               # Conversation management
│   │   └── redis_memory.py   # Redis-based chat history
│   │
│   └── utils/                # Utilities
│       ├── logger.py         # Logging configuration
│       └── validators.py     # Input validation
│
├── routes/                   # API endpoints
│   ├── pdf_routes.py         # PDF upload endpoints
│   ├── chat_routes.py        # Chat/query endpoints
│   └── health_routes.py      # Health check endpoints
│
└── tests/                    # Test suite
```

## 🔄 Core Components

### 1. PDF Processing Pipeline

The pipeline transforms raw PDFs into searchable, embedded chunks:

#### **Step 1: PDF Extraction** (`pdf_reader.py`)
- Extracts text and tables using PyMuPDF or pdfplumber
- Preserves document structure and formatting

#### **Step 2: Cleaning** (`cleaner.py`)
- **Rule 1**: Removes Urdu/Arabic translations (detects non-English content)
- **Rule 2**: Prioritizes consolidated financials, discards unconsolidated
- **Rule 3**: Removes headers, footers, page numbers, and metadata
- Separates tables from narrative text
- Eliminates repeated whitespace and broken lines
- Normalizes text formatting

#### **Step 3: Chunking** (`chunker.py`)
- Splits text into 800–1000 token chunks
- Adds metadata to each chunk:
  - Company name
  - Section type
  - Page range
  - PDF title
- Maintains context overlap between chunks

#### **Step 4: Embedding** (`embedder.py`)
- Generates vector embeddings using Ollama
- Creates semantic representations of text chunks

#### **Step 5: Vector Storage** (`vectorstore.py`)
- Stores embeddings with metadata in ChromaDB
- Enables fast semantic search and retrieval

### 2. RAG (Retrieval-Augmented Generation) System

When a user asks a question, the RAG system:

1. **Retrieval** (`retriever.py`):
   - Searches ChromaDB for semantically similar chunks
   - Ranks and filters results by relevance

2. **Context Building** (`prompt_builder.py`):
   - Retrieves conversation history from Redis
   - Constructs prompt with:
     - System instructions
     - Conversation memory
     - Retrieved document context
     - User query

3. **Generation** (`llm_client.py`):
   - Sends structured prompt to Ollama
   - Receives and processes LLM response

4. **Memory Update** (`redis_memory.py`):
   - Stores user query and assistant response
   - Maintains session-based conversation history

### 3. Redis Conversation Memory

- **Session Management**: Each user gets a unique session ID
- **History Storage**: Stores complete conversation turns
- **Multi-turn Support**: Enables contextual follow-up questions
- **Reset Capability**: Allows clearing conversation history

## 🚀 API Endpoints

### `POST /api/upload`
Upload and process a PDF document.

**Request:**
```json
{
  "file": "<PDF file>"
}
```

**Response:**
```json
{
  "status": "success",
  "chunks_stored": 127,
  "document_id": "abc123"
}
```

**Process:**
1. Receives PDF file
2. Runs extraction → cleaning → chunking → embedding pipeline
3. Stores chunks in ChromaDB
4. Returns confirmation with chunk count

---

### `POST /api/chat`
Ask a question and receive an AI-generated answer.

**Request:**
```json
{
  "question": "What was the revenue growth in Q4?",
  "session_id": "user-session-123"
}
```

**Response:**
```json
{
  "answer": "According to the financial report, Q4 revenue grew by 15.3%...",
  "sources": [
    {
      "page": 12,
      "section": "Financial Results"
    }
  ]
}
```

**Process:**
1. Retrieves relevant document chunks from ChromaDB
2. Fetches conversation history from Redis
3. Builds contextualized prompt
4. Sends to Ollama for generation
5. Stores conversation turn in Redis
6. Returns response with source citations

---

### `GET /api/health`
Check service health and dependencies.

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "redis": "connected",
    "chromadb": "connected",
    "ollama": "running"
  }
}
```

## 🔧 Configuration

Key configuration parameters in `config.py`:

- **Ollama Settings**:
  - Model name (e.g., `llama2`, `mistral`)
  - Embedding model (e.g., `nomic-embed-text`)
  - API endpoint

- **ChromaDB Settings**:
  - Collection name
  - Persistence directory
  - Distance metric

- **Redis Settings**:
  - Host and port
  - Session TTL
  - Max history length

- **Chunking Settings**:
  - Chunk size (tokens)
  - Overlap size
  - Metadata fields


## 📊 Data Flow

### Upload Flow
```
PDF File → pdf_reader → cleaner → chunker → embedder → ChromaDB
                                                            ↓
                                                   [Vector Index]
```

### Query Flow
```
User Question → retriever → ChromaDB (search)
                    ↓
              Retrieved Chunks
                    ↓
         prompt_builder ← redis_memory (history)
                    ↓
              Full Prompt
                    ↓
           llm_client → Ollama → Response
                                    ↓
                          redis_memory (store)
```

## 🧪 Testing & Usage

### PDF Extraction & Cleaning

```bash
# Extract only (see raw data)
python core/extractor/pdf_reader.py path/to/report.pdf

# Extract + Clean + Export (full pipeline)
python core/extractor/cleaner.py path/to/report.pdf ./output

# This creates 3 files in ./output/:
#   - {pdf_name}_tables.txt      → Tables for vector DB
#   - {pdf_name}_narrative.txt   → Cleaned text for LLM
#   - {pdf_name}_summary.txt     → Processing summary
```

## 🔐 Security Considerations

- Local deployment ensures data privacy
- No external API calls for LLM inference
- Session-based isolation for multi-user scenarios
- Input validation on all endpoints

## 🎯 Future Enhancements

- [ ] Support for multiple document formats (DOCX, TXT, HTML)
- [ ] Advanced table extraction and querying
- [ ] Document comparison and analysis
- [ ] Export conversation history
- [ ] Fine-tuning support for domain-specific models
- [ ] Batch document processing
- [ ] Advanced metadata filtering

## 🤝 Related Repositories

- **Frontend**: `llm-finance-frontend` - React-based user interface

## 👥 Contributors

Muhammad Muzamil Kaleem
Muhammad Hadi Khan
Syed Aman Hussain

---

