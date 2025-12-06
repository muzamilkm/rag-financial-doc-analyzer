"""Chat and query endpoints for RAG system."""

import redis
import json
from flask import Blueprint, request, jsonify
from typing import List, Dict, Any, Optional

from config import config
from core.rag.retriever import SemanticRetriever
from core.rag.llm_client import OllamaClient
from core.utils.logger import setup_logger

logger = setup_logger(__name__)

chat_bp = Blueprint('chat', __name__)

# Initialize Redis client for session management
try:
    redis_client = redis.Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB,
        password=config.REDIS_PASSWORD if config.REDIS_PASSWORD else None,
        decode_responses=True
    )
    # Test connection
    redis_client.ping()
    logger.info("Redis client initialized successfully")
except Exception as e:
    logger.warning(f"Redis not available: {e}. Chat history will be disabled.")
    redis_client = None

# Initialize retriever and LLM client (singleton pattern)
retriever = SemanticRetriever()
llm_client = OllamaClient()

def get_chat_history(session_id: str) -> List[Dict[str, str]]:
    """Get chat history from Redis for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        List of chat messages
    """
    if not redis_client:
        return []
    
    try:
        history_key = f"chat_history:{session_id}"
        history_json = redis_client.get(history_key)
        
        if history_json:
            return json.loads(history_json)
        return []
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        return []

def save_chat_history(session_id: str, history: List[Dict[str, str]]) -> None:
    """Save chat history to Redis.
    
    Args:
        session_id: Session identifier
        history: Chat history to save
    """
    if not redis_client:
        return
    
    try:
        history_key = f"chat_history:{session_id}"
        
        # Keep only last N messages
        history = history[-config.REDIS_MAX_HISTORY:]
        
        # Save with TTL
        redis_client.setex(
            history_key,
            config.REDIS_SESSION_TTL,
            json.dumps(history)
        )
    except Exception as e:
        logger.error(f"Error saving chat history: {e}")

@chat_bp.route('/chat', methods=['POST'])
def chat():
    """
    Process user query and return AI-generated answer.
    
    Expected JSON body:
        {
            "query": "User question",
            "session_id": "unique-session-id" (optional),
            "company": "Company name" (optional filter),
            "period": "2024Q3" (optional filter),
            "top_k": 5 (optional, number of chunks to retrieve)
        }
    
    Returns:
        JSON with answer and metadata
    """
    try:
        # Parse request
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({'error': 'No query provided'}), 400
        
        query = data['query'].strip()
        if not query:
            return jsonify({'error': 'Empty query'}), 400
        
        session_id = data.get('session_id', 'default')
        company_filter = data.get('company')
        period_filter = data.get('period')
        top_k = data.get('top_k', config.RETRIEVAL_TOP_K)
        
        logger.info(f"Processing query from session {session_id}: {query[:100]}...")
        
        # Step 1: Retrieve relevant chunks from vector database
        logger.info("Step 1: Retrieving relevant context...")
        try:
            relevant_chunks = retriever.retrieve(
                query=query,
                top_k=top_k,
                company=company_filter,
                period=period_filter,
                content_type=None  # Allow both text and table chunks
            )
            
            if not relevant_chunks:
                logger.warning("No relevant chunks found")
                return jsonify({
                    'answer': "I couldn't find any relevant information in the documents to answer your question.",
                    'sources': [],
                    'metadata': {
                        'chunks_retrieved': 0,
                        'session_id': session_id
                    }
                }), 200
            
            logger.info(f"Retrieved {len(relevant_chunks)} relevant chunks")
            
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return jsonify({
                'error': 'Retrieval failed',
                'message': str(e)
            }), 500
        
        # Step 2: Get chat history for context
        chat_history = get_chat_history(session_id)
        
        # Step 3: Generate answer using LLM
        logger.info("Step 2: Generating answer with LLM...")
        try:
            answer = llm_client.generate_answer(
                user_query=query,
                context_chunks=relevant_chunks,
                chat_history=chat_history
            )
            
            logger.info(f"Generated answer of length: {len(answer)}")
            
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return jsonify({
                'error': 'Answer generation failed',
                'message': str(e)
            }), 500
        
        # Step 4: Update chat history
        chat_history.append({"role": "user", "content": query})
        chat_history.append({"role": "assistant", "content": answer})
        save_chat_history(session_id, chat_history)
        
        # Step 5: Prepare sources metadata
        sources = []
        for chunk in relevant_chunks:
            sources.append({
                'company': chunk.get('company'),
                'period': chunk.get('period'),
                'content_type': chunk.get('content_type'),
                'similarity': round(chunk.get('similarity', 0), 3),
                'snippet': chunk.get('content', '')[:200] + '...' if len(chunk.get('content', '')) > 200 else chunk.get('content', '')
            })
        
        # Return response
        return jsonify({
            'answer': answer,
            'sources': sources,
            'metadata': {
                'chunks_retrieved': len(relevant_chunks),
                'session_id': session_id,
                'model': config.OLLAMA_MODEL,
                'filters_applied': {
                    'company': company_filter,
                    'period': period_filter
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}", exc_info=True)
        return jsonify({
            'error': 'Chat processing failed',
            'message': str(e)
        }), 500

@chat_bp.route('/chat/history/<session_id>', methods=['GET'])
def get_history(session_id: str):
    """
    Get chat history for a session.
    
    Args:
        session_id: Session identifier
    
    Returns:
        JSON with chat history
    """
    try:
        history = get_chat_history(session_id)
        
        return jsonify({
            'session_id': session_id,
            'history': history,
            'message_count': len(history)
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving history: {e}")
        return jsonify({
            'error': 'Failed to retrieve history',
            'message': str(e)
        }), 500

@chat_bp.route('/chat/history/<session_id>', methods=['DELETE'])
def clear_history(session_id: str):
    """
    Clear chat history for a session.
    
    Args:
        session_id: Session identifier
    
    Returns:
        JSON with success status
    """
    try:
        if redis_client:
            history_key = f"chat_history:{session_id}"
            redis_client.delete(history_key)
        
        return jsonify({
            'success': True,
            'message': f'History cleared for session {session_id}'
        }), 200
        
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        return jsonify({
            'error': 'Failed to clear history',
            'message': str(e)
        }), 500
