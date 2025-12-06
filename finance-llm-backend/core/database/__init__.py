"""
Database module for pgvector storage.

Provides PostgreSQL + pgvector integration for storing and retrieving
1024-dimensional embeddings from financial documents.

Main classes:
    - DatabaseSchema: Schema management
    - PgVectorStore: Document insertion and retrieval
    - DatabaseConfig: Connection configuration

Usage:
    from core.database import PgVectorStore, get_connection_string
    import psycopg2
    
    conn = psycopg2.connect(get_connection_string())
    store = PgVectorStore(conn)
    store.insert_documents(embedded_chunks)
"""

from .config import (
    DatabaseConfig,
    get_config,
    get_connection_string,
    create_env_template
)
from .schema import DatabaseSchema
from .pgvector_store import PgVectorStore

__all__ = [
    'DatabaseConfig',
    'get_config',
    'get_connection_string',
    'create_env_template',
    'DatabaseSchema',
    'PgVectorStore',
]
