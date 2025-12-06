"""
PostgreSQL schema for financial document embeddings with pgvector.

This module defines and creates the database schema for storing:
- Text chunks from financial narratives
- Table rows from financial statements
- Embeddings (1024 dimensions) for semantic search
- Metadata for filtering and retrieval

Schema Design:
--------------
1. Single unified table for both text chunks and table rows
2. JSONB metadata for flexible filtering
3. pgvector extension for similarity search
4. Indexes for performance
"""

from typing import Optional, Dict, Any
import psycopg2
from psycopg2.extensions import connection as Connection
from psycopg2 import sql


# Schema definition as a constant for reference
SCHEMA_DEFINITION = """
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Main table for all embedded documents (chunks and table rows)
CREATE TABLE IF NOT EXISTS financial_documents (
    id BIGSERIAL PRIMARY KEY,
    
    -- Content
    content TEXT NOT NULL,
    
    -- Embedding (1024 dimensions for intfloat/e5-large-v2)
    embedding vector(1024) NOT NULL,
    
    -- Metadata (stored as JSONB for flexible querying)
    metadata JSONB NOT NULL,
    
    -- Extracted fields from metadata for faster filtering
    company TEXT GENERATED ALWAYS AS (metadata->>'company') STORED,
    period TEXT GENERATED ALWAYS AS (metadata->>'year') STORED,  -- 'year' field contains period like 2024Q3
    content_type TEXT GENERATED ALWAYS AS (metadata->>'type') STORED,  -- 'text_chunk' or 'table_row'
    doc_type TEXT GENERATED ALWAYS AS (metadata->>'doc_type') STORED,
    
    -- Table-specific fields (NULL for text chunks)
    table_name TEXT GENERATED ALWAYS AS (metadata->>'table_name') STORED,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast retrieval
CREATE INDEX IF NOT EXISTS idx_financial_documents_company ON financial_documents(company);
CREATE INDEX IF NOT EXISTS idx_financial_documents_period ON financial_documents(period);
CREATE INDEX IF NOT EXISTS idx_financial_documents_content_type ON financial_documents(content_type);
CREATE INDEX IF NOT EXISTS idx_financial_documents_table_name ON financial_documents(table_name) WHERE table_name IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_financial_documents_created_at ON financial_documents(created_at DESC);

-- HNSW index for vector similarity search (faster than IVFFlat for most use cases)
-- Using cosine distance as it works well with sentence-transformers embeddings
CREATE INDEX IF NOT EXISTS idx_financial_documents_embedding 
ON financial_documents 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- GIN index on metadata for JSON queries
CREATE INDEX IF NOT EXISTS idx_financial_documents_metadata ON financial_documents USING GIN (metadata);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically update updated_at
DROP TRIGGER IF EXISTS update_financial_documents_updated_at ON financial_documents;
CREATE TRIGGER update_financial_documents_updated_at
    BEFORE UPDATE ON financial_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- View for text chunks only
CREATE OR REPLACE VIEW text_chunks AS
SELECT 
    id,
    content,
    embedding,
    metadata,
    company,
    period,
    doc_type,
    created_at,
    updated_at
FROM financial_documents
WHERE content_type = 'text_chunk';

-- View for table rows only
CREATE OR REPLACE VIEW table_rows AS
SELECT 
    id,
    content,
    embedding,
    metadata,
    company,
    period,
    table_name,
    doc_type,
    created_at,
    updated_at
FROM financial_documents
WHERE content_type = 'table_row';

-- Function for semantic search
CREATE OR REPLACE FUNCTION search_similar_documents(
    query_embedding vector(1024),
    match_count int DEFAULT 10,
    filter_company text DEFAULT NULL,
    filter_period text DEFAULT NULL,
    filter_content_type text DEFAULT NULL
)
RETURNS TABLE (
    id bigint,
    content text,
    metadata jsonb,
    company text,
    period text,
    content_type text,
    similarity float
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        fd.id,
        fd.content,
        fd.metadata,
        fd.company,
        fd.period,
        fd.content_type,
        1 - (fd.embedding <=> query_embedding) AS similarity
    FROM financial_documents fd
    WHERE 
        (filter_company IS NULL OR fd.company = filter_company)
        AND (filter_period IS NULL OR fd.period = filter_period)
        AND (filter_content_type IS NULL OR fd.content_type = filter_content_type)
    ORDER BY fd.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;
"""


class DatabaseSchema:
    """
    Manages database schema creation and initialization.
    """
    
    def __init__(self, connection: Connection):
        """
        Initialize with a database connection.
        
        Args:
            connection: psycopg2 connection object
        """
        self.conn = connection
        self.conn.autocommit = False  # Use transactions
    
    def create_schema(self, drop_existing: bool = False) -> None:
        """
        Create the complete database schema.
        
        Args:
            drop_existing: If True, drop existing table first (WARNING: data loss)
        """
        cursor = self.conn.cursor()
        
        try:
            if drop_existing:
                print("⚠️  Dropping existing table (if exists)...")
                cursor.execute("DROP TABLE IF EXISTS financial_documents CASCADE")
            
            print("Creating database schema...")
            
            # Execute schema creation
            cursor.execute(SCHEMA_DEFINITION)
            
            self.conn.commit()
            print("✓ Schema created successfully!")
            
            # Verify pgvector extension
            self._verify_pgvector(cursor)
            
            # Print schema info
            self._print_schema_info(cursor)
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error creating schema: {e}")
            raise
        finally:
            cursor.close()
    
    def _verify_pgvector(self, cursor) -> None:
        """Verify pgvector extension is installed."""
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            )
        """)
        has_pgvector = cursor.fetchone()[0]
        
        if has_pgvector:
            print("✓ pgvector extension verified")
        else:
            raise Exception("pgvector extension not found! Install it first.")
    
    def _print_schema_info(self, cursor) -> None:
        """Print information about the created schema."""
        # Get table info
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'financial_documents'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        print("\n📋 Table: financial_documents")
        print("Columns:")
        for col_name, data_type, nullable in columns:
            null_str = "NULL" if nullable == "YES" else "NOT NULL"
            print(f"  • {col_name}: {data_type} ({null_str})")
        
        # Get index info
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'financial_documents'
        """)
        indexes = cursor.fetchall()
        
        print("\nIndexes:")
        for idx_name, idx_def in indexes:
            print(f"  • {idx_name}")
    
    def table_exists(self) -> bool:
        """Check if the financial_documents table exists."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'financial_documents'
                )
            """)
            return cursor.fetchone()[0]
        finally:
            cursor.close()
    
    def get_table_stats(self) -> Dict[str, Any]:
        """Get statistics about the financial_documents table."""
        cursor = self.conn.cursor()
        try:
            stats = {}
            
            # Total count
            cursor.execute("SELECT COUNT(*) FROM financial_documents")
            stats['total_documents'] = cursor.fetchone()[0]
            
            # Count by content type
            cursor.execute("""
                SELECT content_type, COUNT(*)
                FROM financial_documents
                GROUP BY content_type
            """)
            stats['by_type'] = dict(cursor.fetchall())
            
            # Count by company
            cursor.execute("""
                SELECT company, COUNT(*)
                FROM financial_documents
                GROUP BY company
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """)
            stats['by_company'] = dict(cursor.fetchall())
            
            # Count by period
            cursor.execute("""
                SELECT period, COUNT(*)
                FROM financial_documents
                GROUP BY period
                ORDER BY period DESC
                LIMIT 10
            """)
            stats['by_period'] = dict(cursor.fetchall())
            
            return stats
        finally:
            cursor.close()
    
    def drop_all(self) -> None:
        """Drop all schema objects (WARNING: data loss)."""
        cursor = self.conn.cursor()
        try:
            print("⚠️  Dropping all schema objects...")
            cursor.execute("DROP TABLE IF EXISTS financial_documents CASCADE")
            self.conn.commit()
            print("✓ All schema objects dropped")
        except Exception as e:
            self.conn.rollback()
            raise
        finally:
            cursor.close()


def create_database_schema(connection_string: str, drop_existing: bool = False) -> None:
    """
    Convenience function to create schema from connection string.
    
    Args:
        connection_string: PostgreSQL connection string
        drop_existing: Whether to drop existing table
    """
    conn = psycopg2.connect(connection_string)
    try:
        schema = DatabaseSchema(conn)
        schema.create_schema(drop_existing=drop_existing)
    finally:
        conn.close()


def print_schema_documentation():
    """Print human-readable documentation of the schema."""
    print("="*80)
    print("FINANCIAL DOCUMENTS SCHEMA DOCUMENTATION")
    print("="*80)
    
    print("\n📊 TABLE: financial_documents")
    print("\nStores both text chunks and table rows with embeddings for semantic search.")
    
    print("\n🔑 Key Columns:")
    print("  • id: Primary key (auto-increment)")
    print("  • content: The actual text content")
    print("  • embedding: 1024-dimensional vector for similarity search")
    print("  • metadata: JSONB with flexible metadata")
    
    print("\n🏷️ Extracted Metadata Columns (for fast filtering):")
    print("  • company: Company name (e.g., 'PTCL')")
    print("  • period: Reporting period (e.g., '2024Q3', '2025FY')")
    print("  • content_type: 'text_chunk' or 'table_row'")
    print("  • doc_type: Document type (e.g., 'financial_report')")
    print("  • table_name: Table name (only for table_row type)")
    
    print("\n📅 Timestamps:")
    print("  • created_at: When the record was inserted")
    print("  • updated_at: When the record was last updated")
    
    print("\n🔍 Indexes:")
    print("  • HNSW index on embedding for fast similarity search")
    print("  • B-tree indexes on company, period, content_type")
    print("  • GIN index on metadata JSONB")
    
    print("\n👁️ Views:")
    print("  • text_chunks: Only text chunk records")
    print("  • table_rows: Only table row records")
    
    print("\n🔧 Functions:")
    print("  • search_similar_documents(): Semantic search with filters")
    print("    Parameters:")
    print("      - query_embedding: The query vector")
    print("      - match_count: Number of results (default 10)")
    print("      - filter_company: Optional company filter")
    print("      - filter_period: Optional period filter")
    print("      - filter_content_type: Optional type filter")
    
    print("\n💡 Usage Example:")
    print("""
    -- Search for similar documents
    SELECT * FROM search_similar_documents(
        query_embedding := '[0.1, 0.2, ...]'::vector(1024),
        match_count := 5,
        filter_company := 'PTCL',
        filter_period := '2024Q3'
    );
    
    -- Get all text chunks for a company
    SELECT * FROM text_chunks WHERE company = 'PTCL';
    
    -- Get table rows by table name
    SELECT * FROM table_rows WHERE table_name = 'income_statement';
    """)
    
    print("\n" + "="*80)
