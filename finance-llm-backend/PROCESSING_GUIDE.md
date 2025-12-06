# PDF Processing Pipeline - Quick Reference

## 🎯 Complete Processing Pipeline

```bash
python core/extractor/cleaner.py your_report.pdf ./output
```

## 📋 What Gets Processed

### ✅ Rule 1: Discard Non-English Translations
- **Detects**: Urdu/Arabic Unicode characters (0x0600-0x06FF ranges)
- **Threshold**: 15% non-ASCII characters in a page
- **Action**: Removes entire pages with Urdu translations
- **Impact**: Major efficiency gain for LLM

### ✅ Rule 2: Discard Redundant Financials
- **Detects**: Both Consolidated and Unconsolidated statements
- **Priority**: Always keeps Consolidated versions
- **Action**: Removes Unconsolidated sections when Consolidated exists
- **Statements Tracked**:
  - Statement of Financial Position
  - Statement of Profit or Loss
  - Statement of Cash Flows

### ✅ Rule 3: Discard Headers, Footers, Metadata
- **Removes**:
  - Page numbers (e.g., "Page 1 of 45")
  - Report titles (e.g., "Third Quarter Report 2025")
  - Company logos (text representations)
  - Repeated headers/footers
  - Date stamps
  - Audited/Unaudited labels

### ✅ Table Extraction & Separation
- **Extracts**: All tables as pandas DataFrames (using tabula-py)
- **Separates**: Table content from narrative text
- **Output**: 
  - Tables → `{pdf_name}_tables.txt` (for vector DB)
  - Text → `{pdf_name}_narrative.txt` (for LLM)

## 📊 Output Files

### 1. `{pdf_name}_tables.txt`
**Purpose**: Feed to Vector Database (ChromaDB)

**Contains**:
- All extracted tables in structured format
- Table dimensions (rows × columns)
- Financial statement metadata
- Segment information metadata

**Example**:
```
================================================================================
TABLE 1
================================================================================
Shape: 15 rows × 5 columns

Description                 Q3 2024    Q3 2023    Change %
Revenue                     1,234      1,156      6.7%
Operating Expenses          456        432        5.6%
...
```

### 2. `{pdf_name}_narrative.txt`
**Purpose**: Feed to LLM for Q&A

**Contains**:
- Cleaned narrative text (no tables)
- Directors' reports
- Management discussion
- Notes and explanations
- Business updates

**Excluded**:
- Urdu translations
- Unconsolidated financials
- Headers/footers
- Table data (moved to tables.txt)

### 3. `{pdf_name}_summary.txt`
**Purpose**: Processing metadata

**Contains**:
- Total pages processed
- Number of tables extracted
- Financial statements identified
- Segment information locations
- Processing statistics

## 🔍 Financial Statement Detection

### Patterns Recognized (Priority Order)

1. **Consolidated Statements** (Highest Priority)
   - "Consolidated Condensed Interim Statement of Financial Position"
   - "Consolidated Statement of Profit or Loss"
   - "Consolidated Statement of Cash Flows"

2. **Regular Statements** (Medium Priority)
   - "Statement of Financial Position"
   - "Statement of Profit or Loss"
   - "Cash Flow Statement"

3. **Unconsolidated** (Discarded if consolidated exists)
   - Any statement without "Consolidated" keyword

### Segment Information Patterns
- "Segment Information"
- "Operating Segment Results"
- "Segment Details"
- "Segmental Analysis"
- "Business Segment"

## 🛠️ Usage Examples

### Basic Usage
```bash
# Process single PDF
python core/extractor/cleaner.py financial_report_Q3_2024.pdf

# Output created in ./output/ by default
```

### Custom Output Directory
```bash
python core/extractor/cleaner.py report.pdf ./my_output_folder
```

### Programmatic Usage
```python
from core.extractor.pdf_reader import PDFReader
from core.extractor.cleaner import TextCleaner, export_to_text_files

# Extract
reader = PDFReader("report.pdf")
data = reader.extract_all(use_tabula=True)

# Clean with all rules
cleaner = TextCleaner()
cleaned_data = cleaner.clean_extracted_data(
    data,
    remove_urdu=True,              # Rule 1
    remove_unconsolidated=True,     # Rule 2
    extract_tables_from_text=True  # Rule 3 + separation
)

# Export
export_to_text_files(cleaned_data, "./output")
```

## 📈 Processing Statistics

Typical financial report (45 pages):
- **Input**: 45 pages
- **After Urdu Removal**: ~30 pages (33% reduction)
- **Tables Extracted**: 15-25 tables
- **Narrative Pages**: 25-30 pages
- **Processing Time**: 10-30 seconds

## 🚀 Next Steps

After processing:

1. **Tables** (`_tables.txt`) → 
   - Chunk into smaller pieces
   - Generate embeddings
   - Store in ChromaDB

2. **Narrative** (`_narrative.txt`) →
   - Chunk into 800-1000 tokens
   - Generate embeddings  
   - Store in ChromaDB with metadata

3. **Query Time** →
   - Retrieve relevant chunks from ChromaDB
   - Build context with Redis history
   - Send to Ollama LLM
   - Return answer to user

## 🔧 Configuration Options

### Urdu Detection Threshold
```python
cleaner.detect_urdu_content(text, threshold=0.15)  # 15% non-ASCII
```

### Table Extraction Method
```python
# Use tabula-py (recommended for financial PDFs)
data = reader.extract_all(use_tabula=True)

# Use pdfplumber (alternative)
data = reader.extract_all(use_tabula=False)
```

### Silent Mode (Suppress Java Warnings)
```python
tables = reader.extract_tables_tabula(silent=True)  # Default
```

## ❓ Troubleshooting

### Issue: UTF-8 Decode Error
**Solution**: Script automatically retries with latin-1 encoding

### Issue: No tables extracted
**Solution**: Check if PDF has actual tables (not images)

### Issue: Urdu pages not removed
**Solution**: Adjust threshold in `detect_urdu_content()`

### Issue: Java warnings from tabula
**Solution**: These are normal, use `silent=True` to suppress
