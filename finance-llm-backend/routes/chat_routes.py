"""Chat and query endpoints for RAG system."""

from flask import Blueprint, request, jsonify
from typing import List, Dict, Any, Optional

from config import config
from core.rag.retriever import SemanticRetriever
from core.rag.llm_client import OllamaClient
from core.memory.postgres_memory import PostgresChatMemory
from core.utils.logger import setup_logger

logger = setup_logger(__name__)

chat_bp = Blueprint('chat', __name__)

# Initialize PostgreSQL chat memory
chat_memory = PostgresChatMemory()

# Initialize retriever and LLM client (singleton pattern)
retriever = SemanticRetriever()
llm_client = OllamaClient()


@chat_bp.route('/chat', methods=['POST'])
def chat():
    """
    Process user query and return AI-generated answer.

    Expected JSON body:
        {
            "query": "User question",
            "chat_id": "uuid-of-chat-session" (optional, creates new if not provided),
            "company": "Company name" (optional filter),
            "period": "2024Q3" (optional filter),
            "top_k": 5 (optional, number of chunks to retrieve)
        }

    Returns:
        JSON with answer, sources, and chat_id
    """
    try:
        # Parse request
        data = request.get_json()

        if not data or 'query' not in data:
            return jsonify({'error': 'No query provided'}), 400

        query = data['query'].strip()
        if not query:
            return jsonify({'error': 'Empty query'}), 400

        # Get or create chat session
        chat_id = data.get('chat_id')
        if not chat_id:
            # Create new chat session with first query as title
            title = query[:50] + '...' if len(query) > 50 else query
            chat_id = chat_memory.create_chat_session(title=title)
            logger.info(f"Created new chat session: {chat_id}")
        else:
            # Verify chat exists
            existing_chat = chat_memory.get_chat_session(chat_id)
            if not existing_chat:
                return jsonify({'error': f'Chat session {chat_id} not found'}), 404

        company_filter = data.get('company')
        period_filter = data.get('period')
        top_k = data.get('top_k', config.RETRIEVAL_TOP_K)

        logger.info(f"Processing query from chat {chat_id}: {query[:100]}...")

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
                answer = "I couldn't find any relevant information in the documents to answer your question."
                sources = []
            else:
                logger.info(
                    f"Retrieved {len(relevant_chunks)} relevant chunks")

                # Step 2: Get chat history for context
                chat_history = chat_memory.get_chat_history(chat_id)

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

                # Prepare sources metadata
                sources = []
                for chunk in relevant_chunks:
                    sources.append({
                        'company': chunk.get('company'),
                        'period': chunk.get('period'),
                        'content_type': chunk.get('content_type'),
                        'similarity': round(chunk.get('similarity', 0), 3),
                        'snippet': chunk.get('content', '')[:200] + '...' if len(chunk.get('content', '')) > 200 else chunk.get('content', '')
                    })

        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return jsonify({
                'error': 'Retrieval failed',
                'message': str(e)
            }), 500

        # Step 4: Save messages to database
        try:
            chat_memory.add_message(chat_id, 'user', query)
            chat_memory.add_message(
                chat_id, 'assistant', answer, sources=sources)
        except Exception as e:
            logger.error(f"Error saving messages: {e}")
            # Continue anyway, return response

        # Return response
        return jsonify({
            'chat_id': chat_id,
            'answer': answer,
            'sources': sources,
            'metadata': {
                'chunks_retrieved': len(relevant_chunks) if relevant_chunks else 0,
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


@chat_bp.route('/chats', methods=['GET'])
def get_all_chats():
    """
    Get all chat sessions.

    Returns:
        JSON with list of all chat sessions
    """
    try:
        sessions = chat_memory.get_all_chat_sessions()

        return jsonify({
            'chats': sessions,
            'count': len(sessions)
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving chats: {e}")
        return jsonify({
            'error': 'Failed to retrieve chats',
            'message': str(e)
        }), 500


@chat_bp.route('/chats/<chat_id>', methods=['GET'])
def get_single_chat(chat_id: str):
    """
    Get a specific chat session with all messages.

    Args:
        chat_id: UUID of the chat session

    Returns:
        JSON with chat session and messages
    """
    try:
        chat = chat_memory.get_chat_session(chat_id)

        if not chat:
            return jsonify({
                'error': 'Chat not found',
                'message': f'Chat session {chat_id} does not exist'
            }), 404

        return jsonify(chat), 200

    except Exception as e:
        logger.error(f"Error retrieving chat: {e}")
        return jsonify({
            'error': 'Failed to retrieve chat',
            'message': str(e)
        }), 500


@chat_bp.route('/chats/<chat_id>', methods=['DELETE'])
def delete_single_chat(chat_id: str):
    """
    Delete a specific chat session.

    Args:
        chat_id: UUID of the chat session

    Returns:
        JSON with success status
    """
    try:
        success = chat_memory.delete_chat_session(chat_id)

        if not success:
            return jsonify({
                'error': 'Chat not found',
                'message': f'Chat session {chat_id} does not exist'
            }), 404

        return jsonify({
            'success': True,
            'message': f'Chat session {chat_id} deleted successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error deleting chat: {e}")
        return jsonify({
            'error': 'Failed to delete chat',
            'message': str(e)
        }), 500


@chat_bp.route('/chats', methods=['DELETE'])
def delete_all_chats():
    """
    Delete all chat sessions.

    Returns:
        JSON with number of deleted sessions
    """
    try:
        count = chat_memory.delete_all_chat_sessions()

        return jsonify({
            'success': True,
            'message': f'Deleted {count} chat sessions',
            'count': count
        }), 200

    except Exception as e:
        logger.error(f"Error deleting all chats: {e}")
        return jsonify({
            'error': 'Failed to delete chats',
            'message': str(e)
        }), 500


@chat_bp.route('/chats/<chat_id>/title', methods=['PUT'])
def update_chat_title(chat_id: str):
    """
    Update the title of a chat session.

    Args:
        chat_id: UUID of the chat session

    Expected JSON body:
        {
            "title": "New title"
        }

    Returns:
        JSON with success status
    """
    try:
        data = request.get_json()

        if not data or 'title' not in data:
            return jsonify({'error': 'No title provided'}), 400

        title = data['title'].strip()
        if not title:
            return jsonify({'error': 'Empty title'}), 400

        success = chat_memory.update_chat_title(chat_id, title)

        if not success:
            return jsonify({
                'error': 'Chat not found',
                'message': f'Chat session {chat_id} does not exist'
            }), 404

        return jsonify({
            'success': True,
            'message': 'Chat title updated successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error updating chat title: {e}")
        return jsonify({
            'error': 'Failed to update title',
            'message': str(e)
        }), 500
