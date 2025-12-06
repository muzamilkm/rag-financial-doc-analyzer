"""
Text chunking with metadata for pgvector preparation.

Chunks narrative text from financial reports into token-based segments
with metadata for downstream embedding and vector storage.
"""

from typing import List, Dict, Any
import tiktoken
from core.utils.metadata import text_metadata


class TextChunker:
    """
    Chunks text into overlapping segments based on token count.
    
    Prepares text for embedding without actually performing embedding,
    returning structured objects ready for pgvector insertion.
    """
    
    def __init__(self, 
                 chunk_size: int = 500, 
                 overlap: int = 100,
                 encoding_name: str = "cl100k_base"):
        """
        Initialize the text chunker.
        
        Args:
            chunk_size: Number of tokens per chunk
            overlap: Number of overlapping tokens between chunks
            encoding_name: Tokenizer encoding to use (default: cl100k_base for GPT-3.5/4)
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        
        # Initialize tokenizer
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception as e:
            print(f"Warning: Failed to load encoding '{encoding_name}': {e}")
            print("Falling back to cl100k_base encoding")
            self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text string.
        
        Args:
            text: Input text
            
        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))
    
    def chunk_text(self, 
                   text: str, 
                   company: str, 
                   year: str,
                   doc_type: str = "financial_report") -> List[Dict[str, Any]]:
        """
        Chunk text into overlapping segments with metadata.
        
        Args:
            text: Cleaned narrative text to chunk
            company: Company name for metadata
            year: Year or reporting period (e.g., "2025", "2025Q3")
            doc_type: Document type for metadata
            
        Returns:
            List of dictionaries with structure:
            {
                "text": <chunk_string>,
                "metadata": {
                    "company": <company>,
                    "year": <year>,
                    "doc_type": <doc_type>,
                    "type": "text_chunk",
                    "chunk_index": <index>,
                    "total_chunks": <total>
                }
            }
        """
        if not text or not text.strip():
            return []
        
        # Encode text to tokens
        tokens = self.encoding.encode(text)
        total_tokens = len(tokens)
        
        # Calculate number of chunks
        if total_tokens <= self.chunk_size:
            # Text fits in one chunk
            chunks = [{
                "text": text,
                "metadata": {
                    **text_metadata(company, year, doc_type),
                    "chunk_index": 0,
                    "total_chunks": 1,
                    "token_count": total_tokens
                }
            }]
            return chunks
        
        # Create overlapping chunks
        chunks = []
        start_idx = 0
        chunk_index = 0
        
        while start_idx < total_tokens:
            # Calculate end index
            end_idx = min(start_idx + self.chunk_size, total_tokens)
            
            # Extract chunk tokens
            chunk_tokens = tokens[start_idx:end_idx]
            
            # Decode back to text
            chunk_text = self.encoding.decode(chunk_tokens)
            
            # Create chunk object with metadata
            chunk_obj = {
                "text": chunk_text,
                "metadata": {
                    **text_metadata(company, year, doc_type),
                    "chunk_index": chunk_index,
                    "total_chunks": -1,  # Will update after loop
                    "token_count": len(chunk_tokens),
                    "start_token": start_idx,
                    "end_token": end_idx
                }
            }
            
            chunks.append(chunk_obj)
            chunk_index += 1
            
            # Move start index forward (with overlap)
            start_idx += self.chunk_size - self.overlap
        
        # Update total_chunks in all chunk metadata
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk["metadata"]["total_chunks"] = total_chunks
        
        return chunks
    
    def chunk_text_from_file(self,
                            file_path: str,
                            company: str,
                            year: str,
                            doc_type: str = "financial_report") -> List[Dict[str, Any]]:
        """
        Read and chunk text from a file.
        
        Args:
            file_path: Path to text file
            company: Company name for metadata
            year: Year or reporting period
            doc_type: Document type for metadata
            
        Returns:
            List of chunk dictionaries
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        return self.chunk_text(text, company, year, doc_type)
    
    def chunk_text_with_auto_metadata(self,
                                     text: str,
                                     company: str = None,
                                     year: str = None) -> List[Dict[str, Any]]:
        """
        Chunk text with automatic metadata extraction if not provided.
        
        Args:
            text: Text to chunk
            company: Company name (if None, will try to extract)
            year: Year/period (if None, will try to extract)
            
        Returns:
            List of chunk dictionaries
        """
        from core.utils.metadata import extract_company_from_text, extract_period_from_text
        
        # Auto-extract metadata if not provided
        if company is None:
            company = extract_company_from_text(text)
            if company is None:
                company = "Unknown Company"
        
        if year is None:
            year = extract_period_from_text(text)
            if year is None:
                year = "Unknown Period"
        
        return self.chunk_text(text, company, year)


def chunk_narrative_text(cleaned_text: str,
                        company: str,
                        year: str,
                        chunk_size: int = 500,
                        overlap: int = 100) -> List[Dict[str, Any]]:
    """
    Convenience function to chunk narrative text.
    
    Args:
        cleaned_text: Cleaned narrative text
        company: Company name
        year: Reporting period
        chunk_size: Tokens per chunk
        overlap: Overlapping tokens
        
    Returns:
        List of chunk objects ready for embedding
    """
    chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)
    return chunker.chunk_text(cleaned_text, company, year)
