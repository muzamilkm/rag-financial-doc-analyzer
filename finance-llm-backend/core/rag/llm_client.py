"""Ollama LLM client for Mistral 7.2B integration."""

import requests
import json
import time
from typing import List, Dict, Any, Optional
from config import config
from core.utils.logger import setup_logger

logger = setup_logger(__name__)

class OllamaClient:
    """Client for interacting with Ollama's Mistral 7.2B model."""
    
    # System prompt for financial document assistant
    SYSTEM_PROMPT = """You are a financial-document assistant. Your job is to answer questions about company reports, including financial statements, cash flow, and management discussion.

Key Guidelines:
1. Always prioritize accuracy and refer to the retrieved context provided below
2. If data is numerical, summarize it clearly with proper formatting
3. If the answer is not present in the retrieved documents, explicitly state: "I cannot find this information in the provided documents"
4. When citing financial figures, include the reporting period if available
5. Be concise but comprehensive in your responses
6. If asked about trends, compare data across periods when available
7. Always maintain a professional, factual tone

Retrieved Context:
{context}

Based on the above context, please answer the following question:"""
    
    def __init__(self, 
                 base_url: str = None,
                 model: str = None,
                 timeout: int = None):
        """Initialize Ollama client.
        
        Args:
            base_url: Ollama API base URL
            model: Model name (e.g., 'mistral:7b')
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or config.OLLAMA_BASE_URL
        self.model = model or config.OLLAMA_MODEL
        self.timeout = timeout or config.OLLAMA_TIMEOUT
        self.generate_url = f"{self.base_url}/api/generate"
        self.chat_url = f"{self.base_url}/api/chat"
        
        logger.info(f"Initialized Ollama client: {self.base_url}, model: {self.model}")
    
    def generate_answer(self,
                       user_query: str,
                       context_chunks: List[Dict[str, Any]],
                       chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Generate answer using RAG pipeline.
        
        Args:
            user_query: User's question
            context_chunks: Retrieved relevant chunks from vector DB
            chat_history: Optional chat history for context
            
        Returns:
            Generated answer from LLM
        """
        # Format context from retrieved chunks
        context = self._format_context(context_chunks)
        
        # Build full prompt with system prompt and context
        system_message = self.SYSTEM_PROMPT.format(context=context)
        
        # Prepare messages for chat API
        messages = [{"role": "system", "content": system_message}]
        
        # Add chat history if available
        if chat_history:
            for msg in chat_history[-config.REDIS_MAX_HISTORY:]:
                messages.append(msg)
        
        # Add user query
        messages.append({"role": "user", "content": user_query})
        
        # Log detailed request information
        logger.info(f"Sending request to Ollama LLM:")
        logger.info(f"  - Model: {self.model}")
        logger.info(f"  - URL: {self.chat_url}")
        logger.info(f"  - Timeout: {self.timeout}s")
        logger.info(f"  - Total messages: {len(messages)}")
        logger.info(f"  - System message length: {len(system_message)} chars")
        logger.info(f"  - Context chunks: {len(context_chunks)}")
        logger.info(f"  - Chat history messages: {len(chat_history) if chat_history else 0}")
        logger.info(f"  - User query: {user_query[:200]}{'...' if len(user_query) > 200 else ''}")
        
        # Log message structure (truncate long content for readability)
        for i, msg in enumerate(messages):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            content_preview = content[:300] + '...' if len(content) > 300 else content
            logger.info(f"  - Message {i+1} ({role}): {len(content)} chars - {content_preview}")
        
        # Prepare request payload
        request_payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": 4096  # Increased from 512 to allow longer responses
            }
        }
        
        logger.info(f"  - Request payload size: ~{len(json.dumps(request_payload))} bytes")
        logger.info(f"  - Options: temperature=0.7, top_p=0.9, num_predict=4096")
        
        try:
            # Call Ollama chat API
            start_time = time.time()
            logger.info(f"Making POST request to Ollama...")
            response = requests.post(
                self.chat_url,
                json=request_payload,
                timeout=self.timeout
            )
            elapsed_time = time.time() - start_time
            logger.info(f"Ollama request completed in {elapsed_time:.2f}s (status: {response.status_code})")
            
            # Check for HTTP errors and extract error message from response
            if not response.ok:
                try:
                    error_data = response.json()
                    error_message = error_data.get('error', response.text)
                    logger.error(f"Ollama API error ({response.status_code}): {error_message}")
                    raise Exception(f"LLM service error: {error_message}")
                except (ValueError, KeyError):
                    # If response is not JSON, use status text
                    logger.error(f"Ollama API error ({response.status_code}): {response.text}")
                    response.raise_for_status()
            
            result = response.json()
            
            # Check if response contains an error field
            if 'error' in result:
                error_message = result.get('error', 'Unknown error from Ollama')
                logger.error(f"Ollama returned error: {error_message}")
                raise Exception(f"LLM service error: {error_message}")
            
            answer = result.get('message', {}).get('content', '')
            if not answer:
                logger.warning("Ollama returned empty answer")
                answer = "I apologize, but I couldn't generate a response. Please try again."
            
            logger.info(f"Generated answer of length: {len(answer)}")
            
            return answer.strip()
            
        except requests.exceptions.Timeout:
            logger.error(f"Ollama request timed out after {self.timeout}s")
            logger.error(f"Request details: model={self.model}, messages={len(messages)}, context_chunks={len(context_chunks)}")
            raise Exception(f"LLM request timed out after {self.timeout} seconds. The model may need more time to process. Please try again or consider using a smaller model.")
        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to Ollama")
            raise Exception("Could not connect to LLM service. Is Ollama running?")
        except requests.exceptions.HTTPError as e:
            # This should not be reached due to our error handling above, but keep as fallback
            logger.error(f"HTTP error from Ollama: {e}")
            raise Exception(f"LLM service HTTP error: {str(e)}")
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            raise Exception(f"Error generating answer: {str(e)}")
    
    def _format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks into context string.
        
        Args:
            chunks: Retrieved chunks with content and metadata
            
        Returns:
            Formatted context string
        """
        if not chunks:
            return "No relevant context found."
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            company = chunk.get('company', 'Unknown')
            period = chunk.get('period', 'Unknown')
            content_type = chunk.get('content_type', 'text')
            similarity = chunk.get('similarity', 0.0)
            content = chunk.get('content', '')
            
            context_parts.append(
                f"[Document {i}] (Company: {company}, Period: {period}, Type: {content_type}, Relevance: {similarity:.2f})\n"
                f"{content}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    def check_health(self) -> bool:
        """Check if Ollama service is running and model is available.
        
        Returns:
            True if service is healthy
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            
            models = response.json().get('models', [])
            model_names = [m.get('name', '') for m in models]
            
            if self.model not in model_names:
                logger.warning(f"Model {self.model} not found in Ollama")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
