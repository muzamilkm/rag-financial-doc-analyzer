"""
PostgreSQL/pgvector insertion module for embedded financial documents.

Handles insertion of text chunks and table rows with their embeddings
into the PostgreSQL database with pgvector extension.
"""

from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extensions import connection as Connection
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
import json
from tqdm import tqdm


class PgVectorStore:
    """
    Manages insertion and retrieval of embedded documents in PostgreSQL with pgvector.
    """
    
    def __init__(self, connection: Connection):
        """
        Initialize with a database connection.
        
        Args:
            connection: psycopg2 connection object
        """
        self.conn = connection
        
        # Ensure we're not in a transaction before setting autocommit
        try:
            # Commit any pending transaction
            if not self.conn.closed:
                self.conn.commit()
        except Exception:
            pass
        
        # Register pgvector type
        register_vector(self.conn)
    
    def insert_documents(self,
                        documents: List[Dict[str, Any]],
                        batch_size: int = 100,
                        show_progress: bool = True) -> int:
        """
        Insert embedded documents (chunks or table rows) into the database.
        
        Args:
            documents: List of document objects with 'text', 'embedding', 'metadata'
            batch_size: Number of documents to insert per batch
            show_progress: Whether to show progress bar
            
        Returns:
            Number of documents inserted
        """
        if not documents:
            return 0
        
        cursor = self.conn.cursor()
        total_inserted = 0
        
        try:
            # Prepare batches
            batches = [documents[i:i + batch_size] 
                      for i in range(0, len(documents), batch_size)]
            
            iterator = tqdm(batches, desc="Inserting documents") if show_progress else batches
            
            for batch in iterator:
                # Prepare values for insertion
                values = []
                for doc in batch:
                    content = doc.get('text', '')
                    embedding = doc.get('embedding', [])
                    metadata = doc.get('metadata', {})
                    
                    # Ensure metadata is a dict
                    if not isinstance(metadata, dict):
                        metadata = {}
                    
                    values.append((
                        content,
                        embedding,
                        json.dumps(metadata)
                    ))
                
                # Insert batch
                execute_values(
                    cursor,
                    """
                    INSERT INTO financial_documents (content, embedding, metadata)
                    VALUES %s
                    """,
                    values,
                    template="(%s, %s, %s::jsonb)"
                )
                
                total_inserted += len(batch)
            
            self.conn.commit()
            return total_inserted
            
        except Exception as e:
            self.conn.rollback()
            print(f"\n❌ Error inserting documents: {e}")
            raise
        finally:
            cursor.close()
    
    def insert_chunks(self,
                     chunks: List[Dict[str, Any]],
                     batch_size: int = 100,
                     show_progress: bool = True) -> int:
        """
        Insert text chunks specifically.
        
        Args:
            chunks: List of chunk objects
            batch_size: Batch size for insertion
            show_progress: Show progress bar
            
        Returns:
            Number of chunks inserted
        """
        print(f"\n📝 Inserting {len(chunks)} text chunks...")
        count = self.insert_documents(chunks, batch_size, show_progress)
        print(f"✓ Inserted {count} text chunks")
        return count
    
    def insert_table_rows(self,
                         rows: List[Dict[str, Any]],
                         batch_size: int = 100,
                         show_progress: bool = True) -> int:
        """
        Insert table rows specifically.
        
        Args:
            rows: List of table row objects
            batch_size: Batch size for insertion
            show_progress: Show progress bar
            
        Returns:
            Number of rows inserted
        """
        print(f"\n📊 Inserting {len(rows)} table rows...")
        count = self.insert_documents(rows, batch_size, show_progress)
        print(f"✓ Inserted {count} table rows")
        return count
    
    def search_similar(self,
                      query_embedding: List[float],
                      limit: int = 10,
                      company: Optional[str] = None,
                      period: Optional[str] = None,
                      content_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for similar documents using vector similarity.
        
        Args:
            query_embedding: Query embedding vector (1024 dims)
            limit: Maximum number of results
            company: Optional company filter
            period: Optional period filter
            content_type: Optional content type filter ('text_chunk' or 'table_row')
            
        Returns:
            List of matching documents with similarity scores
        """
        cursor = self.conn.cursor()
        
        try:
            # Use the database function for search
            cursor.execute(
                """
                SELECT * FROM search_similar_documents(
                    %s::vector(1024),
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (query_embedding, limit, company, period, content_type)
            )
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'content': row[1],
                    'metadata': row[2],
                    'company': row[3],
                    'period': row[4],
                    'content_type': row[5],
                    'similarity': row[6]
                })
            
            return results
            
        finally:
            cursor.close()
    
    def get_document_by_id(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by its ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document dict or None if not found
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                SELECT id, content, metadata, company, period, content_type, created_at
                FROM financial_documents
                WHERE id = %s
            """, (doc_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'content': row[1],
                    'metadata': row[2],
                    'company': row[3],
                    'period': row[4],
                    'content_type': row[5],
                    'created_at': row[6]
                }
            return None
            
        finally:
            cursor.close()
    
    def get_documents_by_company(self,
                                company: str,
                                limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all documents for a specific company.
        
        Args:
            company: Company name
            limit: Optional limit on results
            
        Returns:
            List of documents
        """
        cursor = self.conn.cursor()
        
        try:
            query = """
                SELECT id, content, metadata, company, period, content_type, created_at
                FROM financial_documents
                WHERE company = %s
                ORDER BY created_at DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query, (company,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'content': row[1],
                    'metadata': row[2],
                    'company': row[3],
                    'period': row[4],
                    'content_type': row[5],
                    'created_at': row[6]
                })
            
            return results
            
        finally:
            cursor.close()
    
    def delete_by_company(self, company: str) -> int:
        """
        Delete all documents for a specific company.
        
        Args:
            company: Company name
            
        Returns:
            Number of documents deleted
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM financial_documents
                WHERE company = %s
            """, (company,))
            
            deleted = cursor.rowcount
            self.conn.commit()
            return deleted
            
        except Exception as e:
            self.conn.rollback()
            raise
        finally:
            cursor.close()
    
    def delete_by_period(self, company: str, period: str) -> int:
        """
        Delete all documents for a specific company and period.
        
        Args:
            company: Company name
            period: Period (e.g., '2024Q3')
            
        Returns:
            Number of documents deleted
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM financial_documents
                WHERE company = %s AND period = %s
            """, (company, period))
            
            deleted = cursor.rowcount
            self.conn.commit()
            return deleted
            
        except Exception as e:
            self.conn.rollback()
            raise
        finally:
            cursor.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored documents.
        
        Returns:
            Dictionary with statistics
        """
        from core.database.schema import DatabaseSchema
        
        schema = DatabaseSchema(self.conn)
        return schema.get_table_stats()


def insert_embedded_data(connection_string: str,
                        chunks: Optional[List[Dict[str, Any]]] = None,
                        table_rows: Optional[List[Dict[str, Any]]] = None,
                        batch_size: int = 100) -> Dict[str, int]:
    """
    Convenience function to insert embedded data from connection string.
    
    Args:
        connection_string: PostgreSQL connection string
        chunks: Optional list of text chunks to insert
        table_rows: Optional list of table rows to insert
        batch_size: Batch size for insertion
        
    Returns:
        Dictionary with counts of inserted documents
    """
    conn = psycopg2.connect(connection_string)
    register_vector(conn)
    
    try:
        store = PgVectorStore(conn)
        
        counts = {
            'chunks': 0,
            'rows': 0,
            'total': 0
        }
        
        if chunks:
            counts['chunks'] = store.insert_chunks(chunks, batch_size=batch_size)
        
        if table_rows:
            counts['rows'] = store.insert_table_rows(table_rows, batch_size=batch_size)
        
        counts['total'] = counts['chunks'] + counts['rows']
        
        return counts
        
    finally:
        conn.close()
