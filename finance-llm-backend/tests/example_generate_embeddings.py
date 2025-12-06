"""
Example: Generate embeddings from prepared data.

This script demonstrates how to:
1. Load prepared chunks/rows from JSON
2. Generate embeddings using SentenceTransformer
3. Save embedded data ready for pgvector insertion

Run after data preparation step.
"""

import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.embeddings.embedding_pipeline import EmbeddingPipeline
import json


def example_basic():
    """Basic example: Embed prepared chunks."""
    print("="*80)
    print("EXAMPLE 1: BASIC EMBEDDING")
    print("="*80)
    
    # Check if prepared data exists
    chunks_file = Path("output/processed_chunks.json")
    if not chunks_file.exists():
        print(f"\n❌ File not found: {chunks_file}")
        print("Please run example_process_existing.py first to prepare data.")
        return
    
    # Initialize pipeline
    pipeline = EmbeddingPipeline(
        model_name="intfloat/e5-large-v2",
        batch_size=32
    )
    
    # Load and process
    embedded_data = pipeline.process_from_json(
        chunks_file=str(chunks_file)
    )
    
    # Save results
    saved_files = pipeline.save_embedded_data(
        embedded_data,
        output_dir="output",
        prefix="embedded"
    )
    
    # Show statistics
    stats = pipeline.get_statistics(embedded_data)
    print("\n" + "="*80)
    print("STATISTICS")
    print("="*80)
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Show sample embedded chunk
    if embedded_data['chunks']:
        chunk = embedded_data['chunks'][0]
        print("\n" + "="*80)
        print("SAMPLE EMBEDDED CHUNK")
        print("="*80)
        print(f"Text preview: {chunk['text'][:150]}...")
        print(f"\nMetadata: {json.dumps(chunk['metadata'], indent=2)}")
        print(f"\nEmbedding shape: ({len(chunk['embedding'])},)")
        print(f"Embedding preview (first 10 dims): {chunk['embedding'][:10]}")


def example_with_tables():
    """Example with both text chunks and table rows."""
    print("\n" + "="*80)
    print("EXAMPLE 2: EMBEDDING CHUNKS AND TABLES")
    print("="*80)
    
    # These would be your prepared data files
    chunks_file = Path("output/prepared_text_chunks.json")
    rows_file = Path("output/prepared_table_rows.json")
    
    if not chunks_file.exists():
        print(f"\n⚠ Chunks file not found: {chunks_file}")
        print("Skipping this example.")
        return
    
    # Initialize pipeline
    pipeline = EmbeddingPipeline(model_name="intfloat/e5-large-v2")
    
    # Process both
    embedded_data = pipeline.process_from_json(
        chunks_file=str(chunks_file) if chunks_file.exists() else None,
        rows_file=str(rows_file) if rows_file.exists() else None
    )
    
    # Save
    pipeline.save_embedded_data(embedded_data, prefix="complete_embedded")
    
    # Statistics
    stats = pipeline.get_statistics(embedded_data)
    print("\n" + "="*80)
    print("COMPLETE PIPELINE STATISTICS")
    print("="*80)
    for key, value in stats.items():
        print(f"  {key}: {value}")


def example_similarity_check():
    """Example: Check similarity between embeddings."""
    print("\n" + "="*80)
    print("EXAMPLE 3: SIMILARITY CALCULATION")
    print("="*80)
    
    from core.embeddings.embedder import EmbeddingGenerator
    
    # Initialize generator
    generator = EmbeddingGenerator(model_name="intfloat/e5-large-v2")
    
    # Sample financial texts
    texts = [
        "Revenue increased by 15% year-over-year to reach Rs. 188.3 billion",
        "The company recorded an impressive 15% increase in revenue compared to last year",
        "Operating profit rose by 57% to Rs. 12.9 billion",
        "Cash flow from operations showed strong performance"
    ]
    
    print(f"\nEmbedding {len(texts)} sample texts...")
    embeddings = generator.encode_batch(texts, show_progress=False)
    
    print("\nComputing similarity matrix...")
    similarities = generator.compute_similarity(embeddings, embeddings)
    
    print("\nSimilarity Matrix:")
    print("(Values closer to 1.0 indicate higher similarity)\n")
    
    # Print matrix with labels
    print("     ", end="")
    for i in range(len(texts)):
        print(f"Text{i+1:2d}", end="  ")
    print()
    
    for i in range(len(texts)):
        print(f"Text{i+1:2d}", end="  ")
        for j in range(len(texts)):
            print(f"{similarities[i][j]:6.3f}", end="  ")
        print()
    
    # Highlight similar pairs
    print("\n📊 Key Observations:")
    print(f"  • Text 1 and Text 2 similarity: {similarities[0][1]:.3f}")
    print("    (Both about revenue growth - should be high)")
    print(f"  • Text 1 and Text 3 similarity: {similarities[0][2]:.3f}")
    print("    (Different metrics - should be lower)")


def main():
    """Run all examples."""
    try:
        # Example 1: Basic embedding
        example_basic()
        
        # Example 2: With tables (if available)
        example_with_tables()
        
        # Example 3: Similarity check
        example_similarity_check()
        
        print("\n" + "="*80)
        print("ALL EXAMPLES COMPLETED!")
        print("="*80)
        print("\n📊 What happened:")
        print("  1. Loaded prepared text chunks")
        print("  2. Generated embeddings using intfloat/e5-large-v2")
        print("  3. Saved embedded data to output/embedded_chunks.json")
        print("  4. Demonstrated similarity calculation")
        
        print("\n🎯 Next steps:")
        print("  1. Use embedded data for pgvector insertion")
        print("  2. Build retrieval system")
        print("  3. Connect to LLM for question answering")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
