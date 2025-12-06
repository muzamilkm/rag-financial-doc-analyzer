# RAG Pipeline Architecture - Complete Implementation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RAG FINANCIAL DOC ANALYZER                          │
│                      Complete Pipeline Implementation                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: PDF PROCESSING & DATA PREPARATION                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Input: Financial PDF (e.g., PTCL_2024Q3.pdf)                              │
│    │                                                                         │
│    ├──> core/extractor/pdf_reader.py                                       │
│    │    └─ Extract text and tables                                         │
│    │                                                                         │
│    ├──> core/extractor/cleaner.py                                          │
│    │    └─ Clean, normalize, extract metadata                              │
│    │                                                                         │
│    ├──> core/extractor/chunker.py (TextChunker)                            │
│    │    └─ Chunk text: 500 tokens, 100 overlap                             │
│    │    └─ Output: List[{text, metadata}]                                  │
│    │                                                                         │
│    └──> core/embeddings/table_embeddings.py (TableRowSerializer)           │
│         └─ Serialize table rows to text                                    │
│         └─ Output: List[{text, metadata}]                                  │
│                                                                              │
│  Output: output/processed_chunks.json                                       │
│          output/processed_tables.json                                       │
│          metadata: {company, period, type, source_file, ...}                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: EMBEDDING GENERATION                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Input: Prepared chunks/tables from Stage 1                                │
│    │                                                                         │
│    └──> core/embeddings/embedder.py (EmbeddingGenerator)                   │
│         │                                                                    │
│         ├─ Model: intfloat/e5-large-v2                                     │
│         ├─ Framework: sentence-transformers 5.1.2                          │
│         ├─ Embedding dimension: 1024                                       │
│         ├─ Batch processing with progress bars                             │
│         │                                                                    │
│         └─> encode_batch(texts) -> List[np.array(1024)]                   │
│                                                                              │
│  Output: List[{text, embedding[1024], metadata}]                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: DATABASE STORAGE (pgvector)                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────┐        │
│  │ Supabase PostgreSQL + pgvector Extension                        │        │
│  └────────────────────────────────────────────────────────────────┘        │
│                                                                              │
│  core/database/config.py (DatabaseConfig)                                  │
│    └─ Load credentials from .env                                           │
│    └─ Build connection string                                              │
│                                                                              │
│  core/database/schema.py (DatabaseSchema)                                  │
│    └─ Table: financial_documents                                           │
│        ├─ id: SERIAL PRIMARY KEY                                           │
│        ├─ content: TEXT                                                    │
│        ├─ embedding: vector(1024) ← pgvector type                         │
│        ├─ metadata: JSONB                                                  │
│        ├─ company, period, content_type, table_name (generated)            │
│        ├─ created_at: TIMESTAMP                                            │
│        │                                                                    │
│        ├─ HNSW Index on embedding (cosine distance)                       │
│        │   └─ Fast similarity search: O(log n)                            │
│        │                                                                    │
│        └─ GIN Index on metadata (JSON queries)                            │
│                                                                              │
│  core/database/pgvector_store.py (PgVectorStore)                           │
│    ├─ insert_documents(docs, batch_size=100)                              │
│    ├─ search_similar(query_embedding, filters, limit)                     │
│    ├─ get_documents_by_company(company)                                   │
│    └─ delete_by_period(company, period)                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 4: RETRIEVAL & SEARCH                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User Query: "What was PTCL's revenue in Q3 2024?"                         │
│    │                                                                         │
│    ├──> core/embeddings/embedder.py                                        │
│    │    └─ Generate query embedding (1024 dims)                            │
│    │                                                                         │
│    └──> core/database/pgvector_store.py                                    │
│         │                                                                    │
│         ├─ SQL: SELECT ... ORDER BY embedding <=> query_embedding         │
│         ├─ HNSW index accelerated search                                  │
│         ├─ Apply filters: {company: "PTCL", period: "2024Q3"}             │
│         ├─ Calculate similarity: 1 - cosine_distance                      │
│         │                                                                    │
│         └─> Top K similar documents                                        │
│             [{content, similarity, company, period, ...}, ...]             │
│                                                                              │
│  Output: Ranked list of relevant chunks + metadata                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ STAGE 5: LLM GENERATION (Future Integration)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Retrieved Context from Stage 4                                            │
│    │                                                                         │
│    ├──> core/rag/prompt_builder.py                                         │
│    │    └─ Build prompt with context + query                               │
│    │                                                                         │
│    └──> core/rag/llm_client.py                                             │
│         └─ Send to LLM (Ollama/OpenAI)                                     │
│         └─ Generate answer                                                 │
│                                                                              │
│  Output: Contextual answer to user query                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════
 CURRENT IMPLEMENTATION STATUS
═══════════════════════════════════════════════════════════════════════════════

✅ Stage 1: Data Preparation Layer
   ├─ ✅ PDF text extraction
   ├─ ✅ Text cleaning & normalization
   ├─ ✅ Metadata extraction (company, period)
   ├─ ✅ Token-based chunking (500 tokens, 100 overlap)
   └─ ✅ Table row serialization

✅ Stage 2: Embedding Generation
   ├─ ✅ Sentence-transformers integration
   ├─ ✅ Model: intfloat/e5-large-v2 (1024 dims)
   ├─ ✅ Batch processing
   └─ ✅ Progress tracking

✅ Stage 3: Database Storage (pgvector)
   ├─ ✅ Schema design (financial_documents table)
   ├─ ✅ HNSW vector indexing
   ├─ ✅ JSONB metadata storage
   ├─ ✅ Batch insertion pipeline
   ├─ ✅ Configuration management
   └─ ✅ Supabase integration

✅ Stage 4: Retrieval & Search
   ├─ ✅ Similarity search with cosine distance
   ├─ ✅ Metadata filtering (company, period, type)
   ├─ ✅ Top-K retrieval
   └─ ✅ Similarity scoring

⏳ Stage 5: LLM Integration
   ├─ ⏳ Update Flask routes for pgvector
   ├─ ⏳ Prompt engineering with context
   └─ ⏳ Answer generation


═══════════════════════════════════════════════════════════════════════════════
 KEY FILES & MODULES
═══════════════════════════════════════════════════════════════════════════════

Data Preparation:
  core/extractor/chunker.py          - TextChunker class
  core/embeddings/table_embeddings.py - TableRowSerializer
  core/utils/metadata.py             - Metadata helpers

Embedding Generation:
  core/embeddings/embedder.py        - EmbeddingGenerator
  core/embeddings/embedding_pipeline.py - Full pipeline orchestration

Database Layer:
  core/database/config.py            - Configuration management
  core/database/schema.py            - Schema definition
  core/database/pgvector_store.py    - Vector operations

Examples & Scripts:
  example_complete_pipeline.py       - End-to-end demonstration
  init_database.py                   - Schema initialization
  test_data_preparation.py           - Test data prep layer
  test_embedding_generation.py       - Test embeddings

Documentation:
  DATABASE_SETUP.md                  - Setup guide for Supabase
  PGVECTOR_IMPLEMENTATION.md         - Implementation summary
  PGVECTOR_QUICKREF.md               - Quick reference
  core/database/README.md            - API documentation


═══════════════════════════════════════════════════════════════════════════════
 TECH STACK
═══════════════════════════════════════════════════════════════════════════════

Backend:          Python 3.11.6
Chunking:         tiktoken 0.12.0 (cl100k_base)
Embeddings:       sentence-transformers 5.1.2
Model:            intfloat/e5-large-v2 (1024 dims)
Database:         PostgreSQL (via Supabase)
Vector Index:     pgvector extension
Index Algorithm:  HNSW (cosine distance)
Database Driver:  psycopg2-binary 2.9.9
Config:           python-dotenv 1.0.0


═══════════════════════════════════════════════════════════════════════════════
 PERFORMANCE CHARACTERISTICS
═══════════════════════════════════════════════════════════════════════════════

Chunking:         ~1000 chunks/second
Embedding:        ~50-100 texts/second (CPU), ~500+ texts/second (GPU)
Insertion:        ~100-500 docs/second (batch=100)
Search:           <100ms for 100K+ documents
Index Build:      ~1-2 minutes for 10K documents
Embedding Dim:    1024 (optimal for e5-large-v2)
Storage/Doc:      ~4-5 KB (1024 float32 + metadata + text)


═══════════════════════════════════════════════════════════════════════════════
 DATA FLOW EXAMPLE: PTCL Q3 2024
═══════════════════════════════════════════════════════════════════════════════

1. Input PDF: 264237.pdf (PTCL Quarterly Report)
   
2. Extraction:
   ├─ Narrative text: 264237_narrative.txt
   └─ Tables: 264237_tables.txt
   
3. Chunking:
   ├─ 61 text chunks (500 tokens each, 100 overlap)
   └─ Metadata: {company: "PTCL", period: "2024Q3", type: "text_chunk"}
   
4. Embedding:
   ├─ Generate 1024-dim vector for each chunk
   └─ Model: intfloat/e5-large-v2
   
5. Storage:
   ├─ Insert into financial_documents table
   ├─ HNSW index created automatically
   └─ Fast cosine similarity search enabled
   
6. Query: "What is PTCL's revenue in Q3 2024?"
   ├─ Generate query embedding
   ├─ Find top 5 similar chunks
   ├─ Filter: {company: "PTCL", period: "2024Q3"}
   └─ Return ranked results with similarity scores
   
7. Result:
   [
     {similarity: 0.87, content: "Revenue for Q3 2024 was PKR 35.2B..."},
     {similarity: 0.82, content: "Total revenue increased 12% YoY..."},
     ...
   ]


═══════════════════════════════════════════════════════════════════════════════
 QUICK START
═══════════════════════════════════════════════════════════════════════════════

1. Install dependencies:
   pip install -r requirements.txt

2. Configure Supabase:
   cp .env.example .env
   # Edit .env with your Supabase credentials

3. Initialize database:
   python init_database.py

4. Run complete pipeline:
   python example_complete_pipeline.py

5. Use in your code:
   from core.database import PgVectorStore, get_connection_string
   import psycopg2
   
   conn = psycopg2.connect(get_connection_string())
   store = PgVectorStore(conn)
   results = store.search_similar(query_embedding, limit=5)


═══════════════════════════════════════════════════════════════════════════════
 NEXT STEPS
═══════════════════════════════════════════════════════════════════════════════

1. Complete Setup:
   ✓ Set up Supabase account and project
   ✓ Enable pgvector extension
   ✓ Configure .env with credentials
   ✓ Initialize database schema

2. Test Pipeline:
   ✓ Run example_complete_pipeline.py
   ✓ Verify embeddings are stored
   ✓ Test similarity search

3. Integration:
   - Update Flask routes to use pgvector
   - Replace ChromaDB with PgVectorStore
   - Integrate with existing LLM client

4. Enhancements:
   - Hybrid search (semantic + keyword)
   - Re-ranking with cross-encoders
   - Query expansion
   - Result caching
   - Connection pooling


═══════════════════════════════════════════════════════════════════════════════
 DOCUMENTATION
═══════════════════════════════════════════════════════════════════════════════

📘 DATABASE_SETUP.md            - Complete setup guide with troubleshooting
📗 PGVECTOR_IMPLEMENTATION.md   - Detailed implementation documentation
📙 PGVECTOR_QUICKREF.md         - Quick reference for common operations
📕 core/database/README.md      - Full API documentation and examples

For questions or issues, refer to the documentation above.
```
