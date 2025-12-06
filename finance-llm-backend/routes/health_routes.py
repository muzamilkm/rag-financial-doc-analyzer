"""Health check endpoints."""

import psycopg2
from flask import Blueprint, jsonify

from config import config
from core.rag.llm_client import OllamaClient
from core.rag.retriever import SemanticRetriever
from core.utils.logger import setup_logger

logger = setup_logger(__name__)

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Comprehensive health check for all services.
    
    Returns:
        JSON with health status of all components
    """
    health_status = {
        'status': 'healthy',
        'services': {}
    }
    
    # Check database connection
    try:
        conn = psycopg2.connect(config.get_db_connection_string())
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        health_status['services']['database'] = {'status': 'healthy'}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status['services']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'degraded'
    
    # Check Ollama/LLM service
    try:
        llm_client = OllamaClient()
        if llm_client.check_health():
            health_status['services']['llm'] = {
                'status': 'healthy',
                'model': config.OLLAMA_MODEL
            }
        else:
            health_status['services']['llm'] = {
                'status': 'unhealthy',
                'error': 'Model not available'
            }
            health_status['status'] = 'degraded'
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        health_status['services']['llm'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'degraded'
    
    # Check retriever (embedding model)
    try:
        retriever = SemanticRetriever()
        if retriever.check_health():
            health_status['services']['retriever'] = {
                'status': 'healthy',
                'embedding_model': config.EMBEDDING_MODEL
            }
        else:
            health_status['services']['retriever'] = {
                'status': 'unhealthy',
                'error': 'Cannot connect to database'
            }
            health_status['status'] = 'degraded'
    except Exception as e:
        logger.error(f"Retriever health check failed: {e}")
        health_status['services']['retriever'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'degraded'
    
    # Overall status code
    status_code = 200 if health_status['status'] == 'healthy' else 503
    
    return jsonify(health_status), status_code

@health_bp.route('/ping', methods=['GET'])
def ping():
    """Simple ping endpoint."""
    return jsonify({'status': 'ok'}), 200
