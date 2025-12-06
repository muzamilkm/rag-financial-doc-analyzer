"""
Embedding generation module using SentenceTransformer.

Generates embeddings for prepared text chunks and table rows using
the intfloat/e5-large-v2 model from sentence-transformers.
"""

from typing import List, Dict, Any, Optional, Union
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


class EmbeddingGenerator:
    """
    Generates embeddings for text using SentenceTransformer models.
    
    Uses intfloat/e5-large-v2 by default, which produces high-quality embeddings
    for semantic search and retrieval tasks.
    """
    
    def __init__(self, 
                 model_name: str = "intfloat/e5-large-v2",
                 device: Optional[str] = None,
                 batch_size: int = 32):
        """
        Initialize the embedding generator.
        
        Args:
            model_name: Name of the sentence-transformers model
            device: Device to use ('cuda', 'cpu', or None for auto)
            batch_size: Batch size for encoding (affects speed/memory)
        """
        self.model_name = model_name
        self.batch_size = batch_size
        
        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name, device=device)
        print(f"✓ Model loaded on device: {self.model.device}")
        
        # Get embedding dimension
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        print(f"✓ Embedding dimension: {self.embedding_dim}")
    
    def encode_single(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text string.
        
        Args:
            text: Input text
            
        Returns:
            Numpy array of shape (embedding_dim,)
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding
    
    def encode_batch(self, 
                    texts: List[str],
                    show_progress: bool = True) -> np.ndarray:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of input texts
            show_progress: Whether to show progress bar
            
        Returns:
            Numpy array of shape (len(texts), embedding_dim)
        """
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        return embeddings
    
    def embed_prepared_objects(self,
                              objects: List[Dict[str, Any]],
                              text_field: str = "text",
                              show_progress: bool = True) -> List[Dict[str, Any]]:
        """
        Generate embeddings for prepared data objects (chunks or table rows).
        
        Takes objects with structure:
        {
            "text": "content...",
            "metadata": {...}
        }
        
        And adds embedding:
        {
            "text": "content...",
            "metadata": {...},
            "embedding": [0.123, 0.456, ...]
        }
        
        Args:
            objects: List of prepared objects from chunker/serializer
            text_field: Field name containing text to embed
            show_progress: Whether to show progress bar
            
        Returns:
            Same objects with "embedding" field added
        """
        if not objects:
            return []
        
        # Extract texts
        texts = [obj[text_field] for obj in objects]
        
        # Generate embeddings
        print(f"\nGenerating embeddings for {len(texts)} objects...")
        embeddings = self.encode_batch(texts, show_progress=show_progress)
        
        # Add embeddings to objects
        for obj, embedding in zip(objects, embeddings):
            obj["embedding"] = embedding.tolist()  # Convert to list for JSON serialization
        
        print(f"✓ Generated {len(embeddings)} embeddings")
        return objects
    
    def compute_similarity(self,
                          embeddings1: Union[np.ndarray, List[float]],
                          embeddings2: Union[np.ndarray, List[float]]) -> np.ndarray:
        """
        Compute cosine similarity between embeddings.
        
        Args:
            embeddings1: First set of embeddings (n, dim) or single embedding (dim,)
            embeddings2: Second set of embeddings (m, dim) or single embedding (dim,)
            
        Returns:
            Similarity matrix of shape (n, m) or scalar if both inputs are 1D
        """
        # Convert to numpy if needed
        if isinstance(embeddings1, list):
            embeddings1 = np.array(embeddings1)
        if isinstance(embeddings2, list):
            embeddings2 = np.array(embeddings2)
        
        # Use model's similarity function
        similarities = self.model.similarity(embeddings1, embeddings2)
        return similarities.numpy()
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim,
            "device": str(self.model.device),
            "batch_size": self.batch_size,
            "max_seq_length": self.model.max_seq_length
        }


def embed_text(text: str, model_name: str = "intfloat/e5-large-v2") -> np.ndarray:
    """
    Convenience function to embed a single text.
    
    Args:
        text: Input text
        model_name: SentenceTransformer model name
        
    Returns:
        Embedding as numpy array
    """
    generator = EmbeddingGenerator(model_name=model_name)
    return generator.encode_single(text)


def embed_texts(texts: List[str], 
               model_name: str = "intfloat/e5-large-v2",
               batch_size: int = 32) -> np.ndarray:
    """
    Convenience function to embed multiple texts.
    
    Args:
        texts: List of input texts
        model_name: SentenceTransformer model name
        batch_size: Batch size for encoding
        
    Returns:
        Embeddings as numpy array of shape (len(texts), embedding_dim)
    """
    generator = EmbeddingGenerator(model_name=model_name, batch_size=batch_size)
    return generator.encode_batch(texts)
