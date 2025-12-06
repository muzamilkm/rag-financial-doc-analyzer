"""
Complete pipeline example: Data Preparation → Embedding → Database Storage → Retrieval

This script demonstrates the full RAG pipeline:
1. Load prepared chunks/tables from JSON
2. Generate embeddings using sentence-transformers
3. Initialize database schema
4. Insert documents into pgvector
5. Perform similarity search

Usage:
    python example_complete_pipeline.py
"""

import json
import psycopg2
from pathlib import Path
from typing import List, Dict, Any

# Import our modules
from core.embeddings.embedder import EmbeddingGenerator
from core.database.config import get_connection_string, create_env_template
from core.database.schema import DatabaseSchema
from core.database.pgvector_store import PgVectorStore


def load_prepared_data(chunks_file: str = "output/processed_chunks.json") -> List[Dict[str, Any]]:
    """
    Load prepared chunks from JSON file.
    
    Args:
        chunks_file: Path to processed chunks JSON
        
    Returns:
        List of chunk dictionaries
    """
    print(f"\n📂 Loading prepared data from {chunks_file}...")
    
    with open(chunks_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"   Loaded {len(data)} chunks")
    
    # Show sample
    if data:
        sample = data[0]
        print(f"   Sample chunk:")
        print(f"     Company: {sample['metadata'].get('company')}")
        print(f"     Period: {sample['metadata'].get('period')}")
        print(f"     Type: {sample['metadata'].get('type')}")
        print(f"     Text length: {len(sample['text'])} chars")
    
    return data


def generate_embeddings(chunks: List[Dict[str, Any]], 
                       model_name: str = "intfloat/e5-large-v2") -> List[Dict[str, Any]]:
    """
    Generate embeddings for all chunks.
    
    Args:
        chunks: List of prepared chunks
        model_name: Sentence-transformer model name
        
    Returns:
        List of chunks with embeddings added
    """
    print(f"\n🤖 Generating embeddings with {model_name}...")
    
    # Initialize embedding generator
    embedder = EmbeddingGenerator(model_name=model_name)
    
    # Generate embeddings
    embedded_chunks = embedder.embed_prepared_objects(chunks)
    
    print(f"   Generated {len(embedded_chunks)} embeddings")
    print(f"   Embedding dimension: {len(embedded_chunks[0]['embedding'])}")
    
    return embedded_chunks


def initialize_database(connection_string: str, 
                       force_recreate: bool = False) -> psycopg2.extensions.connection:
    """
    Initialize database schema.
    
    Args:
        connection_string: PostgreSQL connection string
        force_recreate: Whether to drop and recreate schema
        
    Returns:
        Database connection
    """
    print(f"\n🗄️  Initializing database schema...")
    
    # Connect to database
    conn = psycopg2.connect(connection_string)
    
    # Create schema
    schema = DatabaseSchema(conn)
    schema.create_schema(drop_existing=force_recreate)
    
    # Show stats
    stats = schema.get_table_stats()
    print(f"   Schema initialized")
    print(f"   Documents in database: {stats['total_documents']}")
    
    # Ensure any transaction is committed
    conn.commit()
    
    return conn


def insert_documents(conn: psycopg2.extensions.connection,
                    embedded_chunks: List[Dict[str, Any]],
                    batch_size: int = 100) -> None:
    """
    Insert embedded documents into database.
    
    Args:
        conn: Database connection
        embedded_chunks: Chunks with embeddings
        batch_size: Batch size for insertion
    """
    print(f"\n📝 Inserting {len(embedded_chunks)} documents into database...")
    
    # Initialize store
    store = PgVectorStore(conn)
    
    # Insert documents
    inserted = store.insert_documents(embedded_chunks, batch_size=batch_size)
    
    print(f"   ✓ Inserted {inserted} documents")


def perform_similarity_search(conn: psycopg2.extensions.connection,
                             embedder: EmbeddingGenerator,
                             query_text: str,
                             limit: int = 5,
                             filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Perform similarity search.
    
    Args:
        conn: Database connection
        embedder: EmbeddingGenerator instance
        query_text: Query text to search for
        limit: Maximum number of results
        filters: Optional metadata filters
        
    Returns:
        List of similar documents with scores
    """
    print(f"\n🔍 Searching for: '{query_text[:100]}...'")
    
    # Generate query embedding
    query_embedding = embedder.encode_single(query_text)
    
    # Search database
    store = PgVectorStore(conn)
    
    # Extract filter parameters
    company = filters.get('company') if filters else None
    period = filters.get('period') if filters else None
    content_type = filters.get('content_type') if filters else None
    
    results = store.search_similar(
        query_embedding=query_embedding,
        limit=limit,
        company=company,
        period=period,
        content_type=content_type
    )
    
    # Display results
    print(f"   Found {len(results)} similar documents:\n")
    
    for i, result in enumerate(results, 1):
        print(f"   [{i}] Similarity: {result['similarity']:.4f}")
        print(f"       Company: {result['company']}")
        print(f"       Period: {result['period']}")
        print(f"       Type: {result['content_type']}")
        print(f"       Text: {result['content'][:150]}...")
        print()
    
    return results


def main():
    """
    Run complete pipeline example.
    """
    print("=" * 80)
    print("Complete RAG Pipeline: Data → Embeddings → Database → Retrieval")
    print("=" * 80)
    
    # Step 1: Load prepared data
    chunks = load_prepared_data("output/processed_chunks.json")
    
    # For demo, use only first 20 chunks (to save time)
    if len(chunks) > 20:
        print(f"\n⚠️  Using first 20 chunks for demo (out of {len(chunks)} total)")
        chunks = chunks[:20]
    
    # Step 2: Generate embeddings
    model_name = "intfloat/e5-large-v2"
    embedder = EmbeddingGenerator(model_name=model_name)
    embedded_chunks = generate_embeddings(chunks, model_name)
    
    # Step 3: Initialize database
    try:
        connection_string = get_connection_string()
    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease create a .env file with your Supabase credentials.")
        print("Run: python -c 'from core.database.config import create_env_template; create_env_template()'")
        return
    
    # Connect and initialize
    conn = initialize_database(connection_string, force_recreate=False)
    
    # Step 4: Insert documents
    insert_documents(conn, embedded_chunks, batch_size=50)
    
    # Step 5: Perform similarity searches
    print("\n" + "=" * 80)
    print("Testing Similarity Search")
    print("=" * 80)
    
    # Example queries
    queries = [
        "What is the revenue for this quarter?",
        "Tell me about operating expenses",
        "What are the key financial metrics?"
    ]
    
    for query in queries:
        results = perform_similarity_search(
            conn=conn,
            embedder=embedder,
            query_text=query,
            limit=3,
            filters={"company": "PTCL"}  # Filter by company
        )
    
    # Close connection
    conn.close()
    
    print("\n" + "=" * 80)
    print("✓ Pipeline completed successfully!")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Use more chunks by removing the 20-chunk limit")
    print("  2. Add table rows from output/processed_tables.json")
    print("  3. Integrate with LLM for question answering")
    print("  4. Add more sophisticated filtering and ranking")


if __name__ == "__main__":
    main()
