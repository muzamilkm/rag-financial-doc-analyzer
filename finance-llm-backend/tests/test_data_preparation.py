"""
Quick test script to verify the data preparation components work correctly.

Tests:
1. Metadata extraction functions
2. Text chunking
3. Table row serialization
"""

import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from core.utils.metadata import (
    text_metadata, 
    table_metadata,
    extract_company_from_text,
    extract_period_from_text,
    infer_table_name
)
from core.extractor.chunker import TextChunker
from core.embeddings.table_embeddings import TableRowSerializer


def test_metadata_helpers():
    """Test metadata helper functions."""
    print("\n" + "="*80)
    print("TEST 1: Metadata Helpers")
    print("="*80)
    
    # Test text metadata
    text_meta = text_metadata("PTCL", "2025Q3")
    print(f"\nText metadata: {text_meta}")
    assert text_meta['type'] == 'text_chunk'
    assert text_meta['company'] == 'PTCL'
    print("✓ text_metadata works")
    
    # Test table metadata
    table_meta = table_metadata("PTCL", "2025Q3", "income_statement", 5)
    print(f"\nTable metadata: {table_meta}")
    assert table_meta['type'] == 'table_row'
    assert table_meta['row_id'] == 5
    print("✓ table_metadata works")
    
    # Test company extraction
    sample_text = """
    Chairman, Board of Directors PTCL
    President & Group Chief Executive Officer
    Report 2025
    """
    company = extract_company_from_text(sample_text)
    print(f"\nExtracted company: {company}")
    print("✓ extract_company_from_text works")
    
    # Test period extraction
    period = extract_period_from_text(sample_text)
    print(f"Extracted period: {period}")
    print("✓ extract_period_from_text works")
    
    # Test table name inference
    table_name = infer_table_name(page_context="Statement of Profit or Loss")
    print(f"\nInferred table name: {table_name}")
    assert table_name == "income_statement"
    print("✓ infer_table_name works")
    
    print("\n✅ All metadata tests passed!")


def test_text_chunking():
    """Test text chunking functionality."""
    print("\n" + "="*80)
    print("TEST 2: Text Chunking")
    print("="*80)
    
    # Create sample text
    sample_text = """
    Pakistan Telecommunication Company Limited (PTCL) is the leading telecom operator
    in Pakistan. The company provides a comprehensive range of services including fixed line,
    mobile, and data services across the country. PTCL continues to invest in infrastructure
    and technology to enhance service quality and expand its reach.
    
    During the nine months ended September 30, 2025, PTCL achieved significant milestones
    in its digital transformation journey. The company upgraded its network infrastructure,
    expanded its fiber optic coverage, and launched new digital services for customers.
    
    Financial performance remained strong with revenue growth across all business segments.
    The company's focus on operational efficiency and cost management contributed to improved
    profitability. Investment in innovation and customer experience initiatives continued
    to drive market leadership and customer satisfaction.
    """ * 5  # Repeat to create enough text for multiple chunks
    
    # Initialize chunker
    chunker = TextChunker(chunk_size=200, overlap=50)  # Smaller for testing
    
    # Chunk the text
    chunks = chunker.chunk_text(sample_text, "PTCL", "2025Q3")
    
    print(f"\nCreated {len(chunks)} chunks")
    print(f"Chunk size: 200 tokens, Overlap: 50 tokens")
    
    # Verify chunks
    assert len(chunks) > 0, "Should create at least one chunk"
    assert all('text' in chunk for chunk in chunks), "All chunks should have text"
    assert all('metadata' in chunk for chunk in chunks), "All chunks should have metadata"
    
    # Show first chunk
    if chunks:
        print(f"\nFirst chunk metadata:")
        for key, val in chunks[0]['metadata'].items():
            print(f"  {key}: {val}")
        print(f"\nFirst chunk text preview:")
        print(f"  {chunks[0]['text'][:150]}...")
    
    print("\n✅ Text chunking tests passed!")
    return chunks


def test_table_serialization():
    """Test table row serialization."""
    print("\n" + "="*80)
    print("TEST 3: Table Row Serialization")
    print("="*80)
    
    # Create sample DataFrame (income statement)
    data = {
        'Item': ['Revenue', 'Cost of Sales', 'Gross Profit', 'Operating Expenses', 'Net Profit'],
        'Q3_2025': [89596109, -63388362, 26207747, -10000000, 16207747],
        'Q3_2024': [79535667, -59426675, 20108992, -9000000, 11108992]
    }
    df = pd.DataFrame(data)
    
    print("\nSample DataFrame:")
    print(df)
    
    # Initialize serializer
    serializer = TableRowSerializer(serialization_format="key_value")
    
    # Serialize the DataFrame
    rows = serializer.serialize_dataframe(
        df=df,
        company="PTCL",
        period="2025Q3",
        table_name="income_statement"
    )
    
    print(f"\nCreated {len(rows)} serialized rows")
    
    # Verify rows
    assert len(rows) == len(df), "Should have one row object per DataFrame row"
    assert all('text' in row for row in rows), "All rows should have text"
    assert all('metadata' in row for row in rows), "All rows should have metadata"
    
    # Show sample rows
    if rows:
        print(f"\nFirst row:")
        print(f"  Metadata: {rows[0]['metadata']}")
        print(f"  Text: {rows[0]['text']}")
        
        print(f"\nSecond row:")
        print(f"  Metadata: {rows[1]['metadata']}")
        print(f"  Text: {rows[1]['text']}")
    
    print("\n✅ Table serialization tests passed!")
    return rows


def test_full_pipeline():
    """Test the full pipeline with mock data."""
    print("\n" + "="*80)
    print("TEST 4: Full Pipeline Integration")
    print("="*80)
    
    # Simulate cleaned data structure
    cleaned_data = {
        'metadata': {
            'company': 'PTCL',
            'period': '2025Q3'
        },
        'text_by_page': {
            1: "PTCL reported strong financial results for the nine months ended September 30, 2025.",
            2: "Revenue increased by 12% year-over-year driven by growth in all business segments.",
            3: "The company continued to invest in network infrastructure and digital services."
        },
        'tables_by_page': {
            1: pd.DataFrame({
                'Item': ['Revenue', 'Expenses'],
                '2025': [100000, 60000],
                '2024': [90000, 55000]
            })
        },
        'table_format': 'dataframe'
    }
    
    # Process text
    combined_text = " ".join(cleaned_data['text_by_page'].values())
    chunker = TextChunker(chunk_size=100, overlap=20)
    text_chunks = chunker.chunk_text(
        combined_text,
        cleaned_data['metadata']['company'],
        cleaned_data['metadata']['period']
    )
    
    # Process tables
    serializer = TableRowSerializer()
    table_rows = serializer.serialize_tables_by_page(
        cleaned_data['tables_by_page'],
        cleaned_data['metadata']['company'],
        cleaned_data['metadata']['period'],
        cleaned_data['text_by_page']
    )
    
    # Combine
    all_objects = text_chunks + table_rows
    
    print(f"\nPipeline Results:")
    print(f"  Text chunks: {len(text_chunks)}")
    print(f"  Table rows: {len(table_rows)}")
    print(f"  Total objects: {len(all_objects)}")
    
    # Verify all objects have required structure
    for obj in all_objects:
        assert 'text' in obj, "Missing text field"
        assert 'metadata' in obj, "Missing metadata field"
        assert 'type' in obj['metadata'], "Missing type in metadata"
        assert 'company' in obj['metadata'], "Missing company in metadata"
    
    print(f"\n✅ Full pipeline integration test passed!")
    print(f"✅ All {len(all_objects)} objects are ready for embedding!")


def main():
    """Run all tests."""
    print("="*80)
    print("DATA PREPARATION COMPONENTS TEST SUITE")
    print("="*80)
    
    try:
        # Run tests
        test_metadata_helpers()
        test_text_chunking()
        test_table_serialization()
        test_full_pipeline()
        
        # Summary
        print("\n" + "="*80)
        print("ALL TESTS PASSED! ✅")
        print("="*80)
        print("\nThe data preparation layer is working correctly.")
        print("You can now use these components to prepare data for pgvector.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
