# pgvector Quick Reference

## Setup (One-Time)

```bash
# 1. Install dependencies
pip install psycopg2-binary pgvector python-dotenv

# 2. Create .env file
cp .env.example .env
# Edit .env with your Supabase credentials

# 3. Initialize database
python init_database.py

# 4. Test connection
python -c "from core.database.config import get_config; get_config().print_info()"
```

## Basic Usage

### Connect to Database

```python
import psycopg2
from core.database import get_connection_string

conn = psycopg2.connect(get_connection_string())
```

### Insert Documents

```python
from core.database import PgVectorStore

store = PgVectorStore(conn)

documents = [{
    "text": "Document content here",
    "embedding": [0.1, 0.2, ...],  # 1024 dims
    "metadata": {
        "company": "PTCL",
        "period": "2024Q3",
        "type": "text_chunk"
    }
}]

store.insert_documents(documents, batch_size=100)
```

### Search Similar Documents

```python
from core.embeddings.embedder import EmbeddingGenerator

# Generate query embedding
embedder = EmbeddingGenerator()
query_embedding = embedder.encode_single("What is the revenue?")

# Search
results = store.search_similar(
    query_embedding=query_embedding,
    limit=5,
    filters={"company": "PTCL"}
)

# Use results
for result in results:
    print(f"[{result['similarity']:.2f}] {result['content'][:100]}...")
```

## Common Operations

### Get Documents by Company

```python
docs = store.get_documents_by_company("PTCL", limit=50)
```

### Get Documents by Period

```python
docs = store.get_documents_by_period("PTCL", "2024Q3", limit=50)
```

### Count Documents

```python
total = store.count_documents()
ptcl_docs = store.count_documents(filters={"company": "PTCL"})
```

### Delete Documents

```python
# Delete all documents for a company
store.delete_by_company("PTCL")

# Delete documents for specific period
store.delete_by_period("PTCL", "2024Q3")
```

## Filtered Search

### By Company

```python
results = store.search_similar(
    query_embedding=embedding,
    limit=10,
    filters={"company": "PTCL"}
)
```

### By Content Type

```python
# Only text chunks
results = store.search_similar(
    query_embedding=embedding,
    filters={"content_type": "text_chunk"}
)

# Only table rows
results = store.search_similar(
    query_embedding=embedding,
    filters={"content_type": "table_row"}
)
```

### By Table Name

```python
results = store.search_similar(
    query_embedding=embedding,
    filters={"table_name": "income_statement"}
)
```

### Multiple Filters

```python
results = store.search_similar(
    query_embedding=embedding,
    filters={
        "company": "PTCL",
        "period": "2024Q3",
        "content_type": "text_chunk"
    }
)
```

### Minimum Similarity

```python
results = store.search_similar(
    query_embedding=embedding,
    limit=20,
    min_similarity=0.7  # Only highly relevant results
)
```

## Schema Management

### Create Schema

```python
from core.database import DatabaseSchema

schema = DatabaseSchema(conn)
schema.create_schema(drop_existing=False)
```

### Get Statistics

```python
stats = schema.get_table_stats()
print(f"Total: {stats['total_documents']}")
print(f"Text chunks: {stats['text_chunks']}")
print(f"Table rows: {stats['table_rows']}")
print(f"Companies: {stats['companies']}")
```

### Drop Schema (Careful!)

```python
schema.drop_schema()  # Deletes all data!
```

## Environment Variables

```env
# Option 1: Individual credentials
SUPABASE_DB_HOST=db.xxxxx.supabase.co
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=your-password
SUPABASE_DB_SSLMODE=require

# Option 2: Connection string
DATABASE_URL=postgresql://user:pass@host:port/db
```

## Command-Line Tools

```bash
# Initialize database
python init_database.py

# Recreate database (deletes existing data!)
python init_database.py --recreate

# Run complete pipeline
python example_complete_pipeline.py

# Test configuration
python -c "from core.database.config import get_config; get_config().print_info()"

# Check connection
python -c "import psycopg2; from core.database import get_connection_string; conn = psycopg2.connect(get_connection_string()); print('✓ Connected'); conn.close()"

# Count documents
python -c "import psycopg2; from core.database import get_connection_string, DatabaseSchema; conn = psycopg2.connect(get_connection_string()); print(DatabaseSchema(conn).get_table_stats()); conn.close()"
```

## Troubleshooting

### Connection Failed

```bash
# Check configuration
python -c "from core.database.config import get_config; get_config().print_info()"

# Verify Supabase project is active
# Check firewall/network settings
```

### Extension Not Found

```sql
-- In Supabase SQL Editor:
CREATE EXTENSION IF NOT EXISTS vector;
```

### Dimension Mismatch

```python
# Verify embedding dimension
embedding = embedder.encode_single("test")
print(f"Dimension: {len(embedding)}")  # Should be 1024
```

## Performance Tips

```python
# Use larger batches for speed
store.insert_documents(docs, batch_size=500)

# Use GPU for embeddings (if available)
embedder = EmbeddingGenerator(device="cuda")

# Add minimum similarity to reduce results
results = store.search_similar(
    query_embedding=embedding,
    limit=50,
    min_similarity=0.6  # Filter low-quality results
)
```

## Important Files

- `core/database/config.py` - Configuration
- `core/database/schema.py` - Schema definition
- `core/database/pgvector_store.py` - Vector operations
- `init_database.py` - Initialize schema
- `example_complete_pipeline.py` - Complete example
- `DATABASE_SETUP.md` - Detailed setup guide
- `core/database/README.md` - Full documentation

## Getting Help

1. Check `DATABASE_SETUP.md` for setup issues
2. See `core/database/README.md` for API details
3. Run `example_complete_pipeline.py` for working example
4. Check troubleshooting section in DATABASE_SETUP.md
