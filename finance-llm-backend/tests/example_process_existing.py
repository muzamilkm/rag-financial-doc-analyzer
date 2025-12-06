"""
Quick example: Process existing output files from the output/ folder.

This demonstrates how to use the data preparation components
with already-extracted PDF data.
"""

from pathlib import Path
from core.extractor.chunker import TextChunker
from core.embeddings.table_embeddings import TableRowSerializer
from core.utils.metadata import extract_company_from_text, extract_period_from_text
import json


def process_existing_output():
    """Process existing narrative.txt and tables.txt files."""
    
    # Use one of the existing output files
    output_dir = Path("output")
    narrative_file = output_dir / "264237_narrative.txt"
    
    if not narrative_file.exists():
        print(f"❌ File not found: {narrative_file}")
        print("Please run PDF extraction first to generate output files.")
        return
    
    print("="*80)
    print("PROCESSING EXISTING OUTPUT FILES")
    print("="*80)
    
    # Read narrative text
    with open(narrative_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    print(f"\n✓ Loaded: {narrative_file}")
    print(f"  Text length: {len(text)} characters")
    
    # Extract metadata automatically
    print("\n📋 Extracting metadata...")
    company = extract_company_from_text(text)
    period = extract_period_from_text(text)
    
    print(f"  Company: {company or 'Could not extract'}")
    print(f"  Period: {period or 'Could not extract'}")
    
    # If extraction failed, use manual values
    if not company:
        company = "PTCL"  # Manual fallback
        print(f"  → Using manual company: {company}")
    
    if not period:
        period = "2025Q3"  # Manual fallback
        print(f"  → Using manual period: {period}")
    
    # Chunk the text
    print("\n📝 Chunking text...")
    chunker = TextChunker(chunk_size=500, overlap=100)
    chunks = chunker.chunk_text(text, company, period)
    
    print(f"  Created {len(chunks)} chunks")
    
    # Show sample
    if chunks:
        print(f"\n  Sample chunk:")
        print(f"    Index: {chunks[0]['metadata']['chunk_index']}")
        print(f"    Tokens: {chunks[0]['metadata']['token_count']}")
        print(f"    Text preview: {chunks[0]['text'][:150]}...")
    
    # Save chunks
    chunks_output = output_dir / "processed_chunks.json"
    with open(chunks_output, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved chunks to: {chunks_output}")
    
    # Summary
    print("\n" + "="*80)
    print("PROCESSING COMPLETE")
    print("="*80)
    print(f"\n✓ Total text chunks: {len(chunks)}")
    print(f"✓ Output file: {chunks_output}")
    print("\n💡 These chunks are ready to be passed to an embedding model!")
    print("\nNext steps:")
    print("  1. Load chunks from JSON")
    print("  2. For each chunk, generate embedding: embedding = model.embed(chunk['text'])")
    print("  3. Insert into pgvector with chunk['metadata']")


if __name__ == "__main__":
    process_existing_output()
