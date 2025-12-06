# Quick Reference Guide: Data Preparation for pgvector

## Quick Start

### 1. Process an existing output file
```bash
python example_process_existing.py
```
This will:
- Load `output/264237_narrative.txt`
- Extract metadata automatically
- Chunk into 500-token segments
- Save to `output/processed_chunks.json`

### 2. Process a new PDF
```bash
python example_prepare_for_pgvector.py path/to/report.pdf
```

### 3. Run tests
```bash
python test_data_preparation.py
```

## Code Snippets

### Import Everything You Need
```python
from core.extractor.chunker import TextChunker
from core.embeddings.table_embeddings import TableRowSerializer
from core.utils.metadata import text_metadata, table_metadata
```

### Chunk Text (Basic)
```python
chunker = TextChunker(chunk_size=500, overlap=100)
chunks = chunker.chunk_text(text, company="PTCL", year="2025Q3")
```

### Chunk Text (Auto-metadata)
```python
chunker = TextChunker()
chunks = chunker.chunk_text_with_auto_metadata(text)
```

### Serialize Table (Single DataFrame)
```python
serializer = TableRowSerializer()
rows = serializer.serialize_dataframe(
    df=dataframe,
    company="PTCL",
    period="2025Q3",
    table_name="income_statement"
)
```

### Serialize Tables (Dictionary)
```python
tables = {
    "income_statement": df1,
    "balance_sheet": df2
}
serializer = TableRowSerializer()
rows = serializer.serialize_dataframe_dict(tables, "PTCL", "2025Q3")
```

### Full Pipeline
```python
# After cleaning with TextCleaner
company = cleaned_data['metadata']['company']
period = cleaned_data['metadata']['period']

# Text chunks
chunker = TextChunker()
text = "\n\n".join(cleaned_data['text_by_page'].values())
chunks = chunker.chunk_text(text, company, period)

# Table rows
serializer = TableRowSerializer()
rows = serializer.serialize_tables_by_page(
    cleaned_data['tables_by_page'],
    company,
    period,
    cleaned_data['text_by_page']
)

# Ready for embedding!
all_objects = chunks + rows
```

## Output Structure

Every object has:
```python
{
    "text": "actual content here...",
    "metadata": {
        "company": "PTCL",
        "year": "2025Q3",  # or "period" for tables
        "type": "text_chunk",  # or "table_row"
        # ... additional fields ...
    }
}
```

## Configuration Options

### Text Chunking
```python
TextChunker(
    chunk_size=500,      # tokens per chunk
    overlap=100,         # overlapping tokens
    encoding_name="cl100k_base"  # tokenizer
)
```

### Table Serialization
```python
TableRowSerializer(
    serialization_format="key_value"  # or "sentence" or "compact"
)
```

## Common Patterns

### Load and Chunk Existing File
```python
with open('output/264237_narrative.txt', 'r') as f:
    text = f.read()

chunker = TextChunker()
chunks = chunker.chunk_text_with_auto_metadata(text)
```

### Process with Manual Metadata
```python
chunks = chunker.chunk_text(
    text="...",
    company="PTCL",
    year="2025Q3"
)
```

### Save Results to JSON
```python
import json

with open('chunks.json', 'w', encoding='utf-8') as f:
    json.dump(chunks, f, indent=2, ensure_ascii=False)
```

### Load Results from JSON
```python
import json

with open('chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)
```

## Next Stage: Embedding

After preparation, embed each text field:

```python
# Pseudocode - use your actual embedding model
for obj in all_objects:
    # Generate embedding
    embedding = your_model.embed(obj['text'])
    
    # Add to object
    obj['embedding'] = embedding
    
    # Now ready for pgvector insertion
```

## Next Stage: pgvector Insertion

After embedding, insert into database:

```python
import psycopg2
from pgvector.psycopg2 import register_vector
import json

conn = psycopg2.connect(database="your_db")
register_vector(conn)
cur = conn.cursor()

for obj in all_objects:
    cur.execute(
        """
        INSERT INTO documents (text, embedding, metadata)
        VALUES (%s, %s, %s)
        """,
        (
            obj['text'],
            obj['embedding'],
            json.dumps(obj['metadata'])
        )
    )

conn.commit()
```

## File Locations

- **Main code**: `core/extractor/chunker.py`, `core/embeddings/table_embeddings.py`
- **Helpers**: `core/utils/metadata.py`
- **Examples**: `example_prepare_for_pgvector.py`, `example_process_existing.py`
- **Tests**: `test_data_preparation.py`
- **Docs**: `PGVECTOR_PREPARATION.md`, `IMPLEMENTATION_SUMMARY.md`

## Troubleshooting

**Issue**: ModuleNotFoundError: No module named 'tiktoken'  
**Fix**: `pip install tiktoken`

**Issue**: Company/period not extracted  
**Fix**: Pass manually to `chunk_text()` or `serialize_dataframe()`

**Issue**: Tables not in DataFrame format  
**Fix**: Use `PDFReader.extract_all(use_tabula=True)`

## Help

For detailed documentation:
- Read `PGVECTOR_PREPARATION.md`
- Read `IMPLEMENTATION_SUMMARY.md`
- Run `python test_data_preparation.py`
- Check example scripts

For questions about specific functions:
- All functions have docstrings
- Check the test file for usage examples
