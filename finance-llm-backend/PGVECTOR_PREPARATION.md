# Data Preparation Layer for pgvector Migration

This implementation provides the data preparation layer for migrating from ChromaDB to pgvector. It structures text chunks and table rows so they can be passed to an embedding function, without performing the actual embedding.

## Overview

The system processes financial PDFs that have already been extracted into:
1. **cleaned_text** → Narrative text after table extraction
2. **tables** → Extracted pandas DataFrames (multiple per document)

## Architecture

### Core Components

#### 1. **Metadata Helpers** (`core/utils/metadata.py`)
Provides consistent metadata structures for both text chunks and table rows.

**Functions:**
- `text_metadata(company, year, doc_type)` - Creates metadata for text chunks
- `table_metadata(company, period, table_name, row_id, doc_type)` - Creates metadata for table rows
- `extract_company_from_text(text)` - Auto-extracts company name from document
- `extract_period_from_text(text)` - Auto-extracts reporting period (e.g., "2025Q3")
- `infer_table_name(df_name, page_context)` - Infers standardized table names

#### 2. **Text Chunking** (`core/extractor/chunker.py`)
Chunks narrative text into token-based segments with overlap.

**Key Classes:**
- `TextChunker` - Main chunking engine

**Configuration:**
- Chunk size: 500 tokens (default)
- Overlap: 100 tokens (default)
- Tokenizer: tiktoken `cl100k_base` (GPT-3.5/4 compatible)

**Output Format:**
```python
{
    "text": "<chunk_string>",
    "metadata": {
        "company": "<company_name>",
        "year": "<period>",
        "doc_type": "financial_report",
        "type": "text_chunk",
        "chunk_index": 0,
        "total_chunks": 10,
        "token_count": 500,
        "start_token": 0,
        "end_token": 500
    }
}
```

#### 3. **Table Serialization** (`core/embeddings/table_embeddings.py`)
Converts DataFrame rows into text representations row-by-row.

**Key Classes:**
- `TableRowSerializer` - Serializes table rows to text

**Serialization Formats:**
- `key_value` (default): "Column1: Value1, Column2: Value2, ..."
- `sentence`: "The Column1 is Value1. The Column2 is Value2. ..."
- `compact`: "Column1=Value1|Column2=Value2|..."

**Output Format:**
```python
{
    "text": "<serialized_row>",
    "metadata": {
        "company": "<company_name>",
        "period": "<period>",
        "table_name": "<table_name>",
        "row_id": 0,
        "doc_type": "financial_report",
        "type": "table_row"
    }
}
```

#### 4. **Enhanced Cleaner** (`core/extractor/cleaner.py`)
Updated to extract and include company name and period metadata.

**New Features:**
- Auto-extracts company name from document text
- Auto-extracts reporting period (quarter or year)
- Adds `metadata` field to cleaned data output

## Usage

### Basic Text Chunking

```python
from core.extractor.chunker import TextChunker

# Initialize chunker
chunker = TextChunker(chunk_size=500, overlap=100)

# Chunk text
chunks = chunker.chunk_text(
    text=cleaned_text,
    company="PTCL",
    year="2025Q3"
)

# Each chunk is ready for embedding
for chunk in chunks:
    print(f"Text: {chunk['text'][:100]}...")
    print(f"Metadata: {chunk['metadata']}")
```

### Basic Table Serialization

```python
from core.embeddings.table_embeddings import TableRowSerializer
import pandas as pd

# Initialize serializer
serializer = TableRowSerializer(serialization_format="key_value")

# Serialize a single DataFrame
rows = serializer.serialize_dataframe(
    df=income_statement_df,
    company="PTCL",
    period="2025Q3",
    table_name="income_statement"
)

# Each row is ready for embedding
for row in rows:
    print(f"Text: {row['text']}")
    print(f"Metadata: {row['metadata']}")
```

### Full Pipeline Example

```python
from core.extractor.pdf_reader import PDFReader
from core.extractor.cleaner import TextCleaner
from core.extractor.chunker import TextChunker
from core.embeddings.table_embeddings import TableRowSerializer

# 1. Extract PDF
reader = PDFReader("report.pdf")
data = reader.extract_all(use_tabula=True)

# 2. Clean data (includes metadata extraction)
cleaner = TextCleaner()
cleaned_data = cleaner.clean_extracted_data(
    data,
    remove_urdu=True,
    remove_unconsolidated=True,
    extract_tables_from_text=True,
    remove_front_matter=True
)

# 3. Extract metadata
company = cleaned_data['metadata']['company']
period = cleaned_data['metadata']['period']

# 4. Prepare text chunks
chunker = TextChunker(chunk_size=500, overlap=100)
combined_text = "\n\n".join(
    text for text in cleaned_data['text_by_page'].values() if text.strip()
)
text_chunks = chunker.chunk_text(combined_text, company, period)

# 5. Prepare table rows
serializer = TableRowSerializer(serialization_format="key_value")
table_rows = serializer.serialize_tables_by_page(
    tables_by_page=cleaned_data['tables_by_page'],
    company=company,
    period=period,
    page_contexts=cleaned_data['text_by_page']
)

# 6. All data is now ready for embedding
all_objects = text_chunks + table_rows
print(f"Total objects ready: {len(all_objects)}")
```

## Running the Example Script

A complete demonstration script is provided:

```bash
python example_prepare_for_pgvector.py path/to/report.pdf
```

This will:
1. Extract and clean the PDF
2. Prepare text chunks
3. Prepare table rows
4. Save outputs to JSON for inspection
5. Display statistics and sample data

## Output Structure

### Text Chunks
Each chunk contains:
- `text`: The actual text content
- `metadata`:
  - `company`: Company name
  - `year`: Reporting period
  - `doc_type`: Document type
  - `type`: "text_chunk"
  - `chunk_index`: Position in sequence
  - `total_chunks`: Total number of chunks
  - `token_count`: Number of tokens in chunk

### Table Rows
Each row contains:
- `text`: Serialized row content (e.g., "Revenue: 100000, COGS: 50000, Period: 2025Q3")
- `metadata`:
  - `company`: Company name
  - `period`: Reporting period
  - `table_name`: Standardized table name
  - `row_id`: Row index
  - `doc_type`: Document type
  - `type`: "table_row"

## Metadata Extraction

The system automatically extracts:

### Company Name
Patterns include:
- Board of Directors sections
- Corporate information headers
- Statement titles

Example: "PTCL" from "Pakistan Telecommunication Company Limited"

### Reporting Period
Patterns include:
- "nine months ended September 30, 2025" → "2025Q3"
- "year ended December 31, 2024" → "2024FY"
- "Report 2025" → "2025Q3"

## Next Steps: Embedding and pgvector Insertion

After using this preparation layer:

1. **Generate Embeddings:**
```python
from your_embedding_model import get_embedding

for obj in all_objects:
    embedding = get_embedding(obj['text'])
    obj['embedding'] = embedding
```

2. **Insert into pgvector:**
```python
import psycopg2
from pgvector.psycopg2 import register_vector

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

## Dependencies

Required packages:
- `tiktoken` - For token counting and chunking
- `pandas` - For DataFrame handling
- `psycopg2` - For PostgreSQL connection (embedding stage)
- `pgvector` - For vector operations (embedding stage)

Install with:
```bash
pip install tiktoken pandas psycopg2-binary pgvector
```

## File Structure

```
finance-llm-backend/
├── core/
│   ├── extractor/
│   │   ├── chunker.py          # Text chunking (NEW)
│   │   ├── cleaner.py          # Updated with metadata extraction
│   │   ├── pdf_reader.py       # PDF extraction
│   │   └── ...
│   ├── embeddings/
│   │   ├── table_embeddings.py # Table serialization (NEW)
│   │   └── ...
│   └── utils/
│       └── metadata.py         # Metadata helpers (NEW)
├── example_prepare_for_pgvector.py  # Example script (NEW)
└── requirements.txt
```

## Configuration Options

### Text Chunking
- `chunk_size`: Tokens per chunk (default: 500)
- `overlap`: Overlapping tokens (default: 100)
- `encoding_name`: Tokenizer (default: "cl100k_base")

### Table Serialization
- `serialization_format`: "key_value", "sentence", or "compact" (default: "key_value")

### Metadata
- `doc_type`: Document type (default: "financial_report")

## Testing

Test with existing output files:

```python
# Test text chunking
from core.extractor.chunker import TextChunker

with open('output/264237_narrative.txt', 'r') as f:
    text = f.read()

chunker = TextChunker()
chunks = chunker.chunk_text_with_auto_metadata(text)
print(f"Created {len(chunks)} chunks")
```

## Important Notes

1. **No Embedding Yet:** This layer only prepares data structures. Embedding happens in the next stage.

2. **No pgvector Insertion:** No database operations are performed. This is purely data preparation.

3. **Modular Design:** Each component can be used independently or as part of the full pipeline.

4. **Metadata Consistency:** All metadata follows the same structure via helper functions.

5. **Ready for Scale:** The output format is designed to work with batch embedding and bulk insertion.

## Troubleshooting

**Issue:** Company name not extracted
- **Solution:** Check if the PDF text contains standard headers. Manually provide company name if needed.

**Issue:** Period not extracted
- **Solution:** Look for date patterns in the document. Manually provide period if needed.

**Issue:** Tables not in DataFrame format
- **Solution:** Ensure `PDFReader.extract_all(use_tabula=True)` is used.

**Issue:** Empty chunks or rows
- **Solution:** Check that text cleaning preserved content. Adjust cleaning parameters if needed.
