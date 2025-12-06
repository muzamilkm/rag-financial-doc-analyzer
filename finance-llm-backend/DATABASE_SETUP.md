# Database Setup Guide: pgvector with Supabase

This guide walks you through setting up the pgvector database layer for the RAG pipeline.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Supabase Setup](#supabase-setup)
3. [Environment Configuration](#environment-configuration)
4. [Install Dependencies](#install-dependencies)
5. [Initialize Database Schema](#initialize-database-schema)
6. [Run Complete Pipeline](#run-complete-pipeline)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Python 3.11+ installed
- Virtual environment activated
- Supabase account (free tier works)
- Processed chunks available (`output/processed_chunks.json`)

---

## Supabase Setup

### 1. Create Supabase Project

1. Go to https://supabase.com/dashboard
2. Click "New project"
3. Choose organization and fill in:
   - **Name**: `finance-rag` (or your choice)
   - **Database Password**: Choose a strong password (save it!)
   - **Region**: Choose closest to you
4. Click "Create new project" and wait 2-3 minutes

### 2. Enable pgvector Extension

1. In Supabase dashboard, go to **Database** → **Extensions**
2. Search for "vector"
3. Enable the **pgvector** extension
4. Verify it's enabled (should show green checkmark)

### 3. Get Connection Details

Go to **Settings** → **Database**:

**Option A: Individual credentials** (recommended for security)
- **Host**: `db.xxxxxxxxxxxxx.supabase.co`
- **Database name**: `postgres`
- **Port**: `5432`
- **User**: `postgres`
- **Password**: (the one you set during project creation)

**Option B: Connection string** (simpler)
- Find "Connection string" section
- Select "URI" tab
- Copy the connection string:
  ```
  postgresql://postgres.xxxxxxxxxxxxx:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres
  ```
- **Important**: Replace `[YOUR-PASSWORD]` with your actual password

---

## Environment Configuration

### 1. Create .env File

Copy the example file:
```bash
cp .env.example .env
```

### 2. Add Supabase Credentials

Edit `.env` and add your credentials:

**Option A: Using individual credentials**
```env
SUPABASE_DB_HOST=db.xxxxxxxxxxxxx.supabase.co
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=your-actual-password-here
SUPABASE_DB_SSLMODE=require
```

**Option B: Using connection string**
```env
DATABASE_URL=postgresql://postgres.xxxxxxxxxxxxx:your-password@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

### 3. Test Configuration

```bash
python -c "from core.database.config import get_config; config = get_config(); config.print_info(); print('\n✓ Valid' if config.validate() else '\n❌ Invalid')"
```

You should see your configuration details (with password hidden).

---

## Install Dependencies

Install the required packages for database functionality:

```bash
pip install psycopg2-binary==2.9.9 pgvector==0.2.4 python-dotenv==1.0.0
```

Or install all updated requirements:
```bash
pip install -r requirements.txt
```

---

## Initialize Database Schema

### Option 1: Using Python Script

Create and run a simple initialization script:

```python
# init_database.py
from core.database.config import get_connection_string
from core.database.schema import DatabaseSchema
import psycopg2

# Connect
conn = psycopg2.connect(get_connection_string())

# Create schema
schema = DatabaseSchema(conn)
schema.create_schema(drop_existing=False)

# Show stats
stats = schema.get_table_stats()
print(f"✓ Schema initialized")
print(f"  Tables: financial_documents")
print(f"  Documents: {stats['total_documents']}")
print(f"  Text chunks: {stats['text_chunks']}")
print(f"  Table rows: {stats['table_rows']}")

conn.close()
```

Run it:
```bash
python init_database.py
```

### Option 2: Manual SQL Execution

1. Go to Supabase dashboard → **SQL Editor**
2. Open `core/database/schema.py` and copy the `SCHEMA_DEFINITION` constant
3. Paste and execute in SQL Editor

---

## Run Complete Pipeline

Now you can run the end-to-end pipeline:

```bash
python example_complete_pipeline.py
```

This will:
1. ✅ Load prepared chunks from `output/processed_chunks.json`
2. ✅ Generate embeddings using `intfloat/e5-large-v2`
3. ✅ Initialize database schema (if not exists)
4. ✅ Insert documents into pgvector
5. ✅ Perform similarity searches

### Expected Output

```
================================================================================
Complete RAG Pipeline: Data → Embeddings → Database → Retrieval
================================================================================

📂 Loading prepared data from output/processed_chunks.json...
   Loaded 61 chunks
   Sample chunk:
     Company: PTCL
     Period: 2024Q3
     Type: text_chunk
     Text length: 2456 chars

⚠️  Using first 20 chunks for demo (out of 61 total)

🤖 Generating embeddings with intfloat/e5-large-v2...
   Generated 20 embeddings
   Embedding dimension: 1024

🗄️  Initializing database schema...
   Schema initialized
   Documents in database: 0

📝 Inserting 20 documents into database...
Inserting documents: 100%|████████████████████| 20/20 [00:01<00:00]
   ✓ Inserted 20 documents

================================================================================
Testing Similarity Search
================================================================================

🔍 Searching for: 'What is the revenue for this quarter?'...'
   Found 3 similar documents:

   [1] Similarity: 0.8234
       Company: PTCL
       Period: 2024Q3
       Type: text_chunk
       Text: Revenue for the quarter ended September 30, 2024 was PKR 35.2 billion...

✓ Pipeline completed successfully!
```

---

## Troubleshooting

### Connection Errors

**Error**: `connection refused` or `could not connect to server`

**Solution**:
- Check your internet connection
- Verify Supabase project is active (not paused)
- Check host/port are correct in `.env`

---

**Error**: `password authentication failed`

**Solution**:
- Double-check password in `.env` file
- Ensure no extra spaces or quotes around password
- Reset database password in Supabase dashboard if needed

---

**Error**: `SSL connection required`

**Solution**:
- Add `SUPABASE_DB_SSLMODE=require` to `.env`
- Or append `?sslmode=require` to connection string

---

### Extension Errors

**Error**: `type "vector" does not exist`

**Solution**:
- Enable pgvector extension in Supabase dashboard
- Go to Database → Extensions → Enable "vector"

---

### Schema Errors

**Error**: `relation "financial_documents" does not exist`

**Solution**:
- Run schema initialization: `python init_database.py`
- Or set `force_recreate=True` in pipeline script

---

### Embedding Errors

**Error**: `Model not found` or `dimension mismatch`

**Solution**:
- Ensure sentence-transformers is installed: `pip install sentence-transformers==5.1.2`
- Model will download automatically (1.34GB) on first run
- Verify embedding dimension is 1024 (matches schema)

---

### Performance Tips

1. **Batch Size**: Adjust `batch_size` parameter for faster insertion
   ```python
   insert_documents(conn, embedded_chunks, batch_size=200)
   ```

2. **Parallel Processing**: Use multiple workers for embeddings
   ```python
   embedder = EmbeddingGenerator(model_name="...", device="cuda")  # Use GPU
   ```

3. **Index Tuning**: Adjust HNSW parameters in schema for speed/accuracy tradeoff
   ```sql
   -- Faster but less accurate
   CREATE INDEX ... USING hnsw ... WITH (m = 8, ef_construction = 32);
   
   -- Slower but more accurate (default)
   CREATE INDEX ... USING hnsw ... WITH (m = 16, ef_construction = 64);
   ```

---

## Database Schema Overview

The schema creates a single table with advanced features:

```
financial_documents
├── id (SERIAL PRIMARY KEY)
├── content (TEXT) - The actual text content
├── embedding (vector(1024)) - 1024-dimensional embedding
├── metadata (JSONB) - Flexible metadata storage
├── created_at (TIMESTAMP)
│
├── Generated columns (from metadata):
│   ├── company (TEXT)
│   ├── period (TEXT)
│   ├── content_type (TEXT)
│   └── table_name (TEXT)
│
├── Indexes:
│   ├── HNSW index on embedding (cosine distance)
│   └── GIN index on metadata (JSON queries)
│
└── Views:
    ├── text_chunks (filtered by content_type)
    └── table_rows (filtered by content_type)
```

---

## Next Steps

1. **Process More Data**: Remove the 20-chunk limit in pipeline script
2. **Add Tables**: Include table rows from `output/processed_tables.json`
3. **LLM Integration**: Use retrieved chunks for context-aware answers
4. **Advanced Retrieval**: Implement hybrid search (semantic + keyword)
5. **Production**: Add connection pooling, error handling, monitoring

---

## Useful Commands

```bash
# Test configuration
python -c "from core.database.config import get_config; get_config().print_info()"

# Check database connection
python -c "import psycopg2; from core.database.config import get_connection_string; conn = psycopg2.connect(get_connection_string()); print('✓ Connected'); conn.close()"

# Count documents in database
python -c "from core.database.schema import DatabaseSchema; from core.database.config import get_connection_string; import psycopg2; conn = psycopg2.connect(get_connection_string()); schema = DatabaseSchema(conn); print(schema.get_table_stats()); conn.close()"

# Test embedding generation
python -c "from core.embeddings.embedder import EmbeddingGenerator; emb = EmbeddingGenerator(); vec = emb.encode_single('test'); print(f'✓ Embedding dimension: {len(vec)}')"
```

---

## Resources

- [Supabase Documentation](https://supabase.com/docs)
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [sentence-transformers Documentation](https://www.sbert.net/)
- [E5 Embeddings Paper](https://arxiv.org/abs/2212.03533)

---

For more help, check:
- `example_complete_pipeline.py` - Full pipeline example
- `core/database/README.md` - Database module documentation
- `PROCESSING_GUIDE.md` - Overall project guide
