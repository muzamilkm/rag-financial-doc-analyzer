"""
Test script for embedding generation.

Verifies that the embedding components work correctly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
from core.embeddings.embedder import EmbeddingGenerator
from core.embeddings.embedding_pipeline import EmbeddingPipeline


def test_basic_embedding():
    """Test basic embedding generation."""
    print("\n" + "="*80)
    print("TEST 1: Basic Embedding Generation")
    print("="*80)
    
    # Initialize generator
    generator = EmbeddingGenerator(model_name="intfloat/e5-large-v2")
    
    # Test single text
    text = "This is a test sentence for embedding generation."
    embedding = generator.encode_single(text)
    
    print(f"\nInput text: {text}")
    print(f"Embedding shape: {embedding.shape}")
    print(f"Embedding dtype: {embedding.dtype}")
    print(f"Embedding preview (first 5): {embedding[:5]}")
    
    # Verify
    assert embedding.shape[0] == generator.embedding_dim, "Wrong embedding dimension"
    assert isinstance(embedding, np.ndarray), "Should return numpy array"
    print("\n✅ Basic embedding test passed!")


def test_batch_embedding():
    """Test batch embedding generation."""
    print("\n" + "="*80)
    print("TEST 2: Batch Embedding")
    print("="*80)
    
    generator = EmbeddingGenerator(model_name="intfloat/e5-large-v2")
    
    # Test batch
    texts = [
        "First test sentence",
        "Second test sentence",
        "Third test sentence",
        "Fourth test sentence"
    ]
    
    embeddings = generator.encode_batch(texts, show_progress=False)
    
    print(f"\nInput: {len(texts)} texts")
    print(f"Output shape: {embeddings.shape}")
    print(f"Expected: ({len(texts)}, {generator.embedding_dim})")
    
    # Verify
    assert embeddings.shape == (len(texts), generator.embedding_dim), "Wrong batch shape"
    assert isinstance(embeddings, np.ndarray), "Should return numpy array"
    print("\n✅ Batch embedding test passed!")


def test_prepared_objects():
    """Test embedding prepared objects."""
    print("\n" + "="*80)
    print("TEST 3: Embedding Prepared Objects")
    print("="*80)
    
    generator = EmbeddingGenerator(model_name="intfloat/e5-large-v2")
    
    # Mock prepared objects (like from chunker/serializer)
    objects = [
        {
            "text": "Revenue increased by 15% year-over-year",
            "metadata": {
                "company": "PTCL",
                "year": "2025Q3",
                "type": "text_chunk"
            }
        },
        {
            "text": "Operating profit rose to Rs. 12.9 billion",
            "metadata": {
                "company": "PTCL",
                "year": "2025Q3",
                "type": "text_chunk"
            }
        }
    ]
    
    # Embed
    embedded_objects = generator.embed_prepared_objects(objects, show_progress=False)
    
    print(f"\nProcessed {len(embedded_objects)} objects")
    
    # Verify structure
    for i, obj in enumerate(embedded_objects):
        assert "text" in obj, "Missing text field"
        assert "metadata" in obj, "Missing metadata field"
        assert "embedding" in obj, "Missing embedding field"
        assert isinstance(obj["embedding"], list), "Embedding should be list for JSON"
        assert len(obj["embedding"]) == generator.embedding_dim, "Wrong embedding length"
        print(f"\nObject {i+1}:")
        print(f"  Text: {obj['text'][:50]}...")
        print(f"  Metadata: {obj['metadata']}")
        print(f"  Embedding length: {len(obj['embedding'])}")
    
    print("\n✅ Prepared objects embedding test passed!")


def test_similarity():
    """Test similarity computation."""
    print("\n" + "="*80)
    print("TEST 4: Similarity Computation")
    print("="*80)
    
    generator = EmbeddingGenerator(model_name="intfloat/e5-large-v2")
    
    # Similar texts
    texts = [
        "The company reported strong financial results",
        "The firm announced excellent financial performance",
        "It rained heavily yesterday"
    ]
    
    embeddings = generator.encode_batch(texts, show_progress=False)
    similarities = generator.compute_similarity(embeddings, embeddings)
    
    print(f"\nSimilarity matrix shape: {similarities.shape}")
    print("\nSimilarity Matrix:")
    print(similarities)
    
    # Verify
    assert similarities.shape == (3, 3), "Wrong similarity matrix shape"
    
    # Similar texts should have high similarity
    sim_1_2 = similarities[0, 1]
    sim_1_3 = similarities[0, 2]
    
    print(f"\nSimilarity between text 1 and 2 (similar): {sim_1_2:.3f}")
    print(f"Similarity between text 1 and 3 (different): {sim_1_3:.3f}")
    
    assert sim_1_2 > sim_1_3, "Similar texts should have higher similarity"
    print("\n✅ Similarity test passed!")


def test_pipeline():
    """Test the full pipeline."""
    print("\n" + "="*80)
    print("TEST 5: Full Pipeline")
    print("="*80)
    
    # Create mock data
    chunks = [
        {
            "text": "Test chunk 1 with some financial content",
            "metadata": {"company": "Test", "year": "2025Q3", "type": "text_chunk"}
        },
        {
            "text": "Test chunk 2 with more financial information",
            "metadata": {"company": "Test", "year": "2025Q3", "type": "text_chunk"}
        }
    ]
    
    rows = [
        {
            "text": "Revenue: 100000, COGS: 50000",
            "metadata": {"company": "Test", "period": "2025Q3", "type": "table_row"}
        }
    ]
    
    # Initialize pipeline
    pipeline = EmbeddingPipeline(model_name="intfloat/e5-large-v2")
    
    # Process
    result = pipeline.process_all(chunks, rows, show_progress=False)
    
    print(f"\nProcessed chunks: {len(result['chunks'])}")
    print(f"Processed rows: {len(result['rows'])}")
    
    # Verify
    assert len(result['chunks']) == len(chunks), "Wrong number of chunks"
    assert len(result['rows']) == len(rows), "Wrong number of rows"
    
    # Check embeddings exist
    for chunk in result['chunks']:
        assert 'embedding' in chunk, "Chunk missing embedding"
    
    for row in result['rows']:
        assert 'embedding' in row, "Row missing embedding"
    
    # Get statistics
    stats = pipeline.get_statistics(result)
    print("\nPipeline Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n✅ Pipeline test passed!")


def main():
    """Run all tests."""
    print("="*80)
    print("EMBEDDING GENERATION TEST SUITE")
    print("="*80)
    
    try:
        test_basic_embedding()
        test_batch_embedding()
        test_prepared_objects()
        test_similarity()
        test_pipeline()
        
        print("\n" + "="*80)
        print("ALL TESTS PASSED! ✅")
        print("="*80)
        print("\nThe embedding generation system is working correctly.")
        print("You can now generate embeddings for your prepared data.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
