# Database Module - pgvector Integration

This module provides a complete PostgreSQL + pgvector integration for storing and retrieving financial document embeddings in a RAG pipeline.

## Overview

The database layer stores 1024-dimensional embeddings generated from financial documents (text chunks and table rows) and provides efficient similarity search using pgvector's HNSW indexing.

## Architecture

```
core/database/
├── config.py           # Database connection configuration
├── schema.py           # Schema definition and management
└── pgvector_store.py   # Document insertion and retrieval
```

## Features

- ✅ **1024-dimensional vector storage** using pgvector extension
- ✅ **HNSW indexing** for fast similarity search (cosine distance)
- ✅ **Flexible metadata** stored as JSONB with generated columns
- ✅ **Batch insertion** with progress tracking
- ✅ **Filtered search** by company, period, content type
- ✅ **SQL views** for text chunks and table rows
- ✅ **Supabase integration** with SSL support

## Quick Start

### 1. Install Dependencies

```bash
pip install psycopg2-binary==2.9.9 pgvector==0.2.4 python-dotenv==1.0.0
```

### 2. Configure Connection

Create `.env` file:
```env
SUPABASE_DB_HOST=db.xxxxx.supabase.co
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=your-password
SUPABASE_DB_SSLMODE=require
```

### 3. Initialize Schema

```bash
python init_database.py
```

### 4. Use in Code

```python
import psycopg2
from core.database.config import get_connection_string
from core.database.pgvector_store import PgVectorStore

# Connect
conn = psycopg2.connect(get_connection_string())

# Initialize store
store = PgVectorStore(conn)

# Insert documents
documents = [
    {
        "text": "Revenue increased by 15% this quarter",
        "embedding": [0.1, 0.2, ...],  # 1024 dimensions
        "metadata": {
            "company": "PTCL",
            "period": "2024Q3",
            "type": "text_chunk"
        }
    }
]
store.insert_documents(documents)

# Search
query_embedding = [0.15, 0.18, ...]  # 1024 dimensions
results = store.search_similar(
    query_embedding=query_embedding,
    limit=5,
    filters={"company": "PTCL"}
)
```

## Module Reference

### config.py

Manages database connection configuration from environment variables.

**Classes:**
- `DatabaseConfig`: Configuration manager
  - `get_connection_string()`: Returns psycopg2 connection string
  - `validate()`: Checks configuration completeness
  - `print_info()`: Displays connection details

**Functions:**
- `get_config()`: Get global config instance
- `get_connection_string()`: Get connection string (raises error if invalid)

**Environment Variables:**
```
SUPABASE_DB_HOST          # Database host
SUPABASE_DB_PORT          # Port (default: 5432)
SUPABASE_DB_NAME          # Database name (default: postgres)
SUPABASE_DB_USER          # Username (default: postgres)
SUPABASE_DB_PASSWORD      # Password (required)
SUPABASE_DB_SSLMODE       # SSL mode (default: require)
DATABASE_URL              # Alternative: full connection string
```

### schema.py

Defines and manages the database schema.

**Schema Structure:**
```sql
CREATE TABLE financial_documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1024),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Generated columns
    company TEXT GENERATED ALWAYS AS (metadata->>'company') STORED,
    period TEXT GENERATED ALWAYS AS (metadata->>'period') STORED,
    content_type TEXT GENERATED ALWAYS AS (metadata->>'type') STORED,
    table_name TEXT GENERATED ALWAYS AS (metadata->>'table_name') STORED
);

-- HNSW index for vector similarity
CREATE INDEX financial_documents_embedding_idx 
ON financial_documents 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- GIN index for metadata queries
CREATE INDEX financial_documents_metadata_idx 
ON financial_documents 
USING gin (metadata);
```

**Classes:**
- `DatabaseSchema(connection)`: Schema manager
  - `create_schema(drop_existing=False)`: Create tables and indexes
  - `get_table_stats()`: Get document counts and statistics
  - `drop_schema()`: Drop all tables

**Views:**
- `text_chunks`: Filtered view of text chunks
- `table_rows`: Filtered view of table rows

**Functions:**
- `search_similar_documents()`: SQL function for filtered similarity search

### pgvector_store.py

Handles document insertion and retrieval.

**Classes:**

#### `PgVectorStore(connection)`

**Insertion Methods:**
- `insert_documents(documents, batch_size=100)`: Insert list of documents
  - `documents`: List of dicts with `text`, `embedding`, `metadata`
  - Returns: Number of documents inserted
  
- `insert_chunks(embedded_chunks, batch_size=100)`: Insert text chunks
- `insert_table_rows(embedded_rows, batch_size=100)`: Insert table rows

**Search Methods:**
- `search_similar(query_embedding, limit=10, filters=None, min_similarity=0.0)`
  - `query_embedding`: 1024-dimensional vector
  - `filters`: Dict with `company`, `period`, `content_type`, `table_name`
  - Returns: List of dicts with `id`, `content`, `similarity`, metadata fields

**CRUD Methods:**
- `get_documents_by_company(company, limit=100)`: Get docs for company
- `get_documents_by_period(company, period, limit=100)`: Get docs for period
- `delete_by_company(company)`: Delete all docs for company
- `delete_by_period(company, period)`: Delete docs for period
- `count_documents(filters=None)`: Count documents with filters

## Database Schema Details

### Embedding Column

- **Type**: `vector(1024)` (pgvector type)
- **Indexing**: HNSW (Hierarchical Navigable Small World)
- **Distance metric**: Cosine distance
- **Parameters**: 
  - `m = 16`: Max connections per layer
  - `ef_construction = 64`: Size of candidate list during index build

### Metadata Schema

Stored as JSONB with the following standard fields:

```json
{
  "company": "PTCL",
  "period": "2024Q3",
  "type": "text_chunk",  // or "table_row"
  "source_file": "264237.pdf",
  "chunk_index": 0,
  "token_count": 500,
  "table_name": "income_statement",  // for table rows
  "row_index": 0  // for table rows
}
```

### Generated Columns

Extracted from metadata for efficient querying:
- `company`: Company name
- `period`: Time period (e.g., "2024Q3")
- `content_type`: "text_chunk" or "table_row"
- `table_name`: Table name (for table rows)

These columns are indexed and can be used in WHERE clauses.

## Performance Tuning

### Index Parameters

**Current settings** (balanced):
```sql
WITH (m = 16, ef_construction = 64)
```

**Fast search** (less accurate):
```sql
WITH (m = 8, ef_construction = 32)
```

**Accurate search** (slower):
```sql
WITH (m = 24, ef_construction = 128)
```

### Batch Sizes

Adjust based on your data:
- **Small batches (50-100)**: Better progress tracking, slower overall
- **Medium batches (200-500)**: Good balance
- **Large batches (1000+)**: Fastest, but uses more memory

### Connection Pooling

For production, use connection pooling:

```python
from psycopg2.pool import SimpleConnectionPool

pool = SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=get_connection_string()
)

conn = pool.getconn()
# ... use connection
pool.putconn(conn)
```

## Similarity Search Details

### Cosine Distance

The HNSW index uses cosine distance, which measures the angle between vectors:
- **1.0**: Completely different (180° apart)
- **0.5**: Somewhat similar (90° apart)
- **0.0**: Identical (0° apart)

We convert to similarity score:
```python
similarity = 1 - distance  # Higher is better
```

### Filtering

Filters are applied AFTER vector search for efficiency:

```python
results = store.search_similar(
    query_embedding=embedding,
    limit=10,
    filters={
        "company": "PTCL",
        "period": "2024Q3",
        "content_type": "text_chunk"
    }
)
```

### Minimum Similarity Threshold

Filter out low-quality results:

```python
results = store.search_similar(
    query_embedding=embedding,
    limit=10,
    min_similarity=0.7  # Only return results with similarity > 0.7
)
```

## Examples

### Complete Pipeline

See `example_complete_pipeline.py` for full example.

### Custom Queries

```python
# Search within specific company and period
results = store.search_similar(
    query_embedding=embedding,
    filters={
        "company": "PTCL",
        "period": "2024Q3"
    },
    limit=5
)

# Search only table rows
results = store.search_similar(
    query_embedding=embedding,
    filters={"content_type": "table_row"},
    limit=10
)

# Search specific table
results = store.search_similar(
    query_embedding=embedding,
    filters={
        "company": "PTCL",
        "table_name": "income_statement"
    },
    limit=5
)
```

### Direct SQL

For advanced use cases:

```python
cursor = conn.cursor()

# Custom similarity search
cursor.execute("""
    SELECT 
        id,
        content,
        1 - (embedding <=> %s::vector) AS similarity,
        metadata
    FROM financial_documents
    WHERE company = %s
    ORDER BY embedding <=> %s::vector
    LIMIT %s
""", (query_embedding, "PTCL", query_embedding, 5))

results = cursor.fetchall()
```

## Monitoring

### Table Statistics

```python
from core.database.schema import DatabaseSchema

schema = DatabaseSchema(conn)
stats = schema.get_table_stats()

print(f"Total documents: {stats['total_documents']}")
print(f"Text chunks: {stats['text_chunks']}")
print(f"Table rows: {stats['table_rows']}")
print(f"Companies: {stats['companies']}")
```

### Index Health

```sql
-- Check index size
SELECT pg_size_pretty(pg_relation_size('financial_documents_embedding_idx'));

-- Check index usage
SELECT * FROM pg_stat_user_indexes 
WHERE indexrelname = 'financial_documents_embedding_idx';
```

## Troubleshooting

### "type vector does not exist"

**Solution**: Enable pgvector extension
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

In Supabase: Database → Extensions → Enable "vector"

### "dimension mismatch"

**Solution**: Ensure embeddings are exactly 1024 dimensions
```python
assert len(embedding) == 1024, f"Expected 1024 dims, got {len(embedding)}"
```

### Slow queries

**Solutions**:
1. Check index exists: `\d financial_documents`
2. Analyze table: `ANALYZE financial_documents;`
3. Adjust HNSW parameters (see Performance Tuning)
4. Use filters to reduce search space

### Connection timeout

**Solutions**:
1. Check Supabase project is active (not paused)
2. Verify SSL mode: `SUPABASE_DB_SSLMODE=require`
3. Use connection pooling for production

## Migration from ChromaDB

If migrating from ChromaDB:

1. Export ChromaDB collections:
```python
import chromadb
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection("finance_documents")

# Get all documents
results = collection.get(include=["embeddings", "documents", "metadatas"])
```

2. Convert to pgvector format:
```python
documents = []
for i in range(len(results['ids'])):
    documents.append({
        "text": results['documents'][i],
        "embedding": results['embeddings'][i],
        "metadata": results['metadatas'][i]
    })
```

3. Insert into pgvector:
```python
store.insert_documents(documents)
```

## Resources

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [HNSW Algorithm](https://arxiv.org/abs/1603.09320)
- [Supabase Vector Docs](https://supabase.com/docs/guides/database/extensions/pgvector)
- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html)

## License

Part of the finance-llm-backend RAG pipeline project.
