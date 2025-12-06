"""Ollama LLM client for Mistral 7.2B integration."""

import requests
import json
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
        
        try:
            # Call Ollama chat API
            response = requests.post(
                self.chat_url,
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 512
                    }
                },
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            answer = result.get('message', {}).get('content', '')
            logger.info(f"Generated answer of length: {len(answer)}")
            
            return answer.strip()
            
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            raise Exception("LLM request timed out. Please try again.")
        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to Ollama")
            raise Exception("Could not connect to LLM service. Is Ollama running?")
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
