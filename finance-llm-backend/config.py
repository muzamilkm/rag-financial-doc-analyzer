"""Configuration module for Flask application."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration."""
    
    # Flask
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Upload settings
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', './uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    ALLOWED_EXTENSIONS = {'pdf'}
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # Ollama/LLM settings
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'mistral:7b')
    OLLAMA_TIMEOUT = int(os.getenv('OLLAMA_TIMEOUT', 120))  # seconds
    
    # Embedding settings
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'intfloat/e5-large-v2')
    EMBEDDING_DIMENSION = 1024
    
    # Chunking settings
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 500))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 100))
    
    # Retrieval settings
    RETRIEVAL_TOP_K = int(os.getenv('RETRIEVAL_TOP_K', 5))
    RETRIEVAL_MIN_SIMILARITY = float(os.getenv('RETRIEVAL_MIN_SIMILARITY', 0.5))
    
    # Redis settings (for session memory)
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
    REDIS_SESSION_TTL = int(os.getenv('REDIS_SESSION_TTL', 3600))  # 1 hour
    REDIS_MAX_HISTORY = int(os.getenv('REDIS_MAX_HISTORY', 10))
    
    # Database settings
    SUPABASE_DB_HOST = os.getenv('SUPABASE_DB_HOST', 'localhost')
    SUPABASE_DB_PORT = int(os.getenv('SUPABASE_DB_PORT', 5432))
    SUPABASE_DB_NAME = os.getenv('SUPABASE_DB_NAME', 'postgres')
    SUPABASE_DB_USER = os.getenv('SUPABASE_DB_USER', 'postgres')
    SUPABASE_DB_PASSWORD = os.getenv('SUPABASE_DB_PASSWORD', '')
    SUPABASE_DB_SSLMODE = os.getenv('SUPABASE_DB_SSLMODE', 'disable')
    
    @staticmethod
    def get_db_connection_string() -> str:
        """Get PostgreSQL connection string."""
        return (
            f"host={Config.SUPABASE_DB_HOST} "
            f"port={Config.SUPABASE_DB_PORT} "
            f"dbname={Config.SUPABASE_DB_NAME} "
            f"user={Config.SUPABASE_DB_USER} "
            f"password={Config.SUPABASE_DB_PASSWORD} "
            f"sslmode={Config.SUPABASE_DB_SSLMODE}"
        )
    
    @staticmethod
    def validate() -> bool:
        """Validate required configuration."""
        required = [
            Config.SUPABASE_DB_HOST,
            Config.SUPABASE_DB_NAME,
            Config.SUPABASE_DB_USER,
            Config.SUPABASE_DB_PASSWORD
        ]
        return all(required)

# Export config instance
config = Config()
