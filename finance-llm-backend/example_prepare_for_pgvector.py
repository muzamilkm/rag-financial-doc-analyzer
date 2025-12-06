"""
Example script demonstrating the data preparation pipeline for pgvector.

This script shows how to:
1. Process cleaned narrative text into chunks
2. Process extracted tables into serialized rows
3. Prepare data structures ready for embedding and pgvector insertion

Run this after PDF extraction and cleaning to prepare data for the embedding stage.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.extractor.pdf_reader import PDFReader
from core.extractor.cleaner import TextCleaner
from core.extractor.chunker import TextChunker
from core.embeddings.table_embeddings import TableRowSerializer
import json


def prepare_text_chunks(cleaned_data: dict) -> list:
    """
    Prepare text chunks from cleaned narrative content.
    
    Args:
        cleaned_data: Output from TextCleaner.clean_extracted_data()
        
    Returns:
        List of chunk objects ready for embedding
    """
    print("\n" + "="*80)
    print("PREPARING TEXT CHUNKS")
    print("="*80)
    
    # Extract metadata
    company = cleaned_data['metadata']['company']
    period = cleaned_data['metadata']['period']
    
    print(f"\nCompany: {company}")
    print(f"Period: {period}")
    
    # Combine all cleaned text
    all_text = []
    for page_num in sorted(cleaned_data['text_by_page'].keys()):
        text = cleaned_data['text_by_page'][page_num]
        if text.strip():
            all_text.append(text)
    
    combined_text = "\n\n".join(all_text)
    print(f"\nTotal narrative text length: {len(combined_text)} characters")
    
    # Initialize chunker
    chunker = TextChunker(chunk_size=500, overlap=100)
    
    # Chunk the text
    chunks = chunker.chunk_text(
        text=combined_text,
        company=company,
        year=period
    )
    
    print(f"\nCreated {len(chunks)} text chunks")
    
    # Show sample chunks
    if chunks:
        print("\nSample chunks:")
        for i, chunk in enumerate(chunks[:3], 1):
            print(f"\n--- Chunk {i} ---")
            print(f"Metadata: {json.dumps(chunk['metadata'], indent=2)}")
            print(f"Text preview: {chunk['text'][:200]}...")
    
    return chunks


def prepare_table_rows(cleaned_data: dict) -> list:
    """
    Prepare table rows from extracted DataFrames.
    
    Args:
        cleaned_data: Output from TextCleaner.clean_extracted_data()
        
    Returns:
        List of row objects ready for embedding
    """
    print("\n" + "="*80)
    print("PREPARING TABLE ROWS")
    print("="*80)
    
    # Extract metadata
    company = cleaned_data['metadata']['company']
    period = cleaned_data['metadata']['period']
    
    print(f"\nCompany: {company}")
    print(f"Period: {period}")
    
    # Check table format
    table_format = cleaned_data.get('table_format', 'list')
    print(f"Table format: {table_format}")
    
    if table_format != 'dataframe':
        print("\n⚠ Warning: Tables are not in DataFrame format.")
        print("The table_embeddings module requires DataFrames.")
        print("Ensure PDFReader.extract_all(use_tabula=True) was used.")
        return []
    
    # Initialize serializer
    serializer = TableRowSerializer(serialization_format="key_value")
    
    # Serialize tables
    all_rows = serializer.serialize_tables_by_page(
        tables_by_page=cleaned_data['tables_by_page'],
        company=company,
        period=period,
        page_contexts=cleaned_data['text_by_page']
    )
    
    print(f"\nCreated {len(all_rows)} table row objects")
    
    # Show sample rows
    if all_rows:
        print("\nSample table rows:")
        for i, row in enumerate(all_rows[:5], 1):
            print(f"\n--- Row {i} ---")
            print(f"Metadata: {json.dumps(row['metadata'], indent=2)}")
            print(f"Text: {row['text'][:300]}...")
    
    return all_rows


def save_prepared_data(chunks: list, table_rows: list, output_dir: str = "./output"):
    """
    Save prepared data to JSON files for inspection or later use.
    
    Args:
        chunks: List of text chunk objects
        table_rows: List of table row objects
        output_dir: Directory to save output files
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Save chunks
    chunks_file = output_path / "prepared_text_chunks.json"
    with open(chunks_file, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved {len(chunks)} chunks to: {chunks_file}")
    
    # Save table rows
    rows_file = output_path / "prepared_table_rows.json"
    with open(rows_file, 'w', encoding='utf-8') as f:
        json.dump(table_rows, f, indent=2, ensure_ascii=False)
    print(f"✓ Saved {len(table_rows)} table rows to: {rows_file}")


def main():
    """Main function demonstrating the preparation pipeline."""
    if len(sys.argv) < 2:
        print("Usage: python example_prepare_for_pgvector.py <path_to_pdf>")
        print("\nExample: python example_prepare_for_pgvector.py sample_report.pdf")
        print("\nThis script will:")
        print("  1. Extract text and tables from PDF")
        print("  2. Clean the extracted data")
        print("  3. Prepare text chunks for embedding")
        print("  4. Prepare table rows for embedding")
        print("  5. Save prepared data to JSON files")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    try:
        print("="*80)
        print("DATA PREPARATION PIPELINE FOR PGVECTOR")
        print("="*80)
        
        # Step 1: Extract PDF data
        print("\n[1/4] Extracting PDF data...")
        reader = PDFReader(pdf_path)
        data = reader.extract_all(use_tabula=True)
        print(f"✓ Extracted from {data['total_pages']} pages")
        print(f"✓ Found {len(data['tables_by_page'])} tables")
        
        # Step 2: Clean extracted data
        print("\n[2/4] Cleaning extracted data...")
        cleaner = TextCleaner()
        cleaned_data = cleaner.clean_extracted_data(
            data,
            remove_urdu=True,
            remove_unconsolidated=True,
            extract_tables_from_text=True,
            remove_front_matter=True
        )
        print(f"✓ Cleaned {len(cleaned_data['text_by_page'])} pages of text")
        print(f"✓ Cleaned {len(cleaned_data['tables_by_page'])} tables")
        
        # Step 3: Prepare text chunks
        print("\n[3/4] Preparing text chunks...")
        chunks = prepare_text_chunks(cleaned_data)
        
        # Step 4: Prepare table rows
        print("\n[4/4] Preparing table rows...")
        table_rows = prepare_table_rows(cleaned_data)
        
        # Save prepared data
        print("\n" + "="*80)
        print("SAVING PREPARED DATA")
        print("="*80)
        save_prepared_data(chunks, table_rows)
        
        # Summary
        print("\n" + "="*80)
        print("PREPARATION COMPLETE")
        print("="*80)
        print(f"\n✓ Total text chunks: {len(chunks)}")
        print(f"✓ Total table rows: {len(table_rows)}")
        print(f"✓ Total objects ready for embedding: {len(chunks) + len(table_rows)}")
        
        print("\n📊 Next steps:")
        print("  1. Pass these objects to your embedding model")
        print("  2. Generate embeddings for each text field")
        print("  3. Insert into pgvector with metadata")
        
        print("\n💡 Example embedding workflow:")
        print("  for chunk in chunks:")
        print("      embedding = embedding_model.embed(chunk['text'])")
        print("      pgvector.insert(embedding, chunk['metadata'])")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
