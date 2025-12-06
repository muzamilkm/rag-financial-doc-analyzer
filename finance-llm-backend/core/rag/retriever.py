"""Semantic retrieval module for RAG pipeline."""

import psycopg2
from typing import List, Dict, Any, Optional
from config import config
from core.database.pgvector_store import PgVectorStore
from core.embeddings.embedder import EmbeddingGenerator
from core.utils.logger import setup_logger

logger = setup_logger(__name__)

class SemanticRetriever:
    """Retriever for semantic search using pgvector."""
    
    def __init__(self, 
                 connection_string: str = None,
                 embedding_model: str = None):
        """Initialize retriever.
        
        Args:
            connection_string: PostgreSQL connection string
            embedding_model: Embedding model name
        """
        self.connection_string = connection_string or config.get_db_connection_string()
        self.embedding_model = embedding_model or config.EMBEDDING_MODEL
        
        # Initialize embedder (lazy loading)
        self._embedder = None
        
        # Connection will be created per request
        self._conn = None
        
        logger.info(f"Initialized retriever with model: {self.embedding_model}")
    
    @property
    def embedder(self) -> EmbeddingGenerator:
        """Lazy load embedding generator."""
        if self._embedder is None:
            logger.info("Loading embedding model...")
            self._embedder = EmbeddingGenerator(model_name=self.embedding_model)
        return self._embedder
    
    def retrieve(self,
                query: str,
                top_k: int = None,
                company: Optional[str] = None,
                period: Optional[str] = None,
                content_type: Optional[str] = None,
                min_similarity: float = None) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks for a query.
        
        Args:
            query: User query text
            top_k: Number of results to return
            company: Filter by company name
            period: Filter by period
            content_type: Filter by content type ('text_chunk' or 'table_row')
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of relevant chunks with metadata
        """
        top_k = top_k or config.RETRIEVAL_TOP_K
        min_similarity = min_similarity or config.RETRIEVAL_MIN_SIMILARITY
        
        try:
            # Generate query embedding
            logger.info(f"Generating embedding for query: {query[:100]}...")
            query_embedding = self.embedder.encode_single(query)
            
            # Connect to database
            conn = psycopg2.connect(self.connection_string)
            store = PgVectorStore(conn)
            
            # Search similar documents
            logger.info(f"Searching for top {top_k} similar documents")
            results = store.search_similar(
                query_embedding=query_embedding,
                limit=top_k * 2,  # Get more to filter by similarity
                company=company,
                period=period,
                content_type=content_type
            )
            
            # Filter by minimum similarity
            filtered_results = [
                r for r in results 
                if r.get('similarity', 0) >= min_similarity
            ][:top_k]
            
            logger.info(f"Retrieved {len(filtered_results)} relevant chunks")
            
            # Close connection
            conn.close()
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            if self._conn:
                self._conn.close()
            raise Exception(f"Retrieval failed: {str(e)}")
    
    def retrieve_by_metadata(self,
                            company: str,
                            period: Optional[str] = None,
                            limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve documents by metadata only (no semantic search).
        
        Args:
            company: Company name
            period: Optional period filter
            limit: Maximum results
            
        Returns:
            List of documents
        """
        try:
            conn = psycopg2.connect(self.connection_string)
            store = PgVectorStore(conn)
            
            if period:
                results = store.get_documents_by_period(company, period, limit)
            else:
                results = store.get_documents_by_company(company, limit)
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving by metadata: {e}")
            raise Exception(f"Metadata retrieval failed: {str(e)}")
    
    def check_health(self) -> bool:
        """Check if retriever can connect to database.
        
        Returns:
            True if healthy
        """
        try:
            conn = psycopg2.connect(self.connection_string)
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Retriever health check failed: {e}")
            return False
