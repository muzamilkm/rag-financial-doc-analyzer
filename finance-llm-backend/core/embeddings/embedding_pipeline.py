"""
Full embedding pipeline for prepared data.

Takes prepared chunks/rows from the data preparation layer and generates
embeddings, creating objects ready for pgvector insertion.
"""

from typing import List, Dict, Any, Optional
import json
from pathlib import Path
from core.embeddings.embedder import EmbeddingGenerator
import time


class EmbeddingPipeline:
    """
    Pipeline to generate embeddings for prepared text chunks and table rows.
    
    Handles the full workflow from prepared objects to embedded objects
    ready for database insertion.
    """
    
    def __init__(self,
                 model_name: str = "intfloat/e5-large-v2",
                 batch_size: int = 32,
                 device: Optional[str] = None):
        """
        Initialize the embedding pipeline.
        
        Args:
            model_name: SentenceTransformer model to use
            batch_size: Batch size for embedding generation
            device: Device to use ('cuda', 'cpu', or None for auto)
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.device = device
        
        # Initialize generator (loads model)
        self.generator = EmbeddingGenerator(
            model_name=model_name,
            batch_size=batch_size,
            device=device
        )
    
    def process_chunks(self,
                      chunks: List[Dict[str, Any]],
                      show_progress: bool = True) -> List[Dict[str, Any]]:
        """
        Generate embeddings for text chunks.
        
        Args:
            chunks: List of chunk objects from TextChunker
            show_progress: Whether to show progress bar
            
        Returns:
            Chunks with embeddings added
        """
        print("\n" + "="*80)
        print("PROCESSING TEXT CHUNKS")
        print("="*80)
        print(f"Chunks to process: {len(chunks)}")
        
        start_time = time.time()
        embedded_chunks = self.generator.embed_prepared_objects(
            chunks,
            text_field="text",
            show_progress=show_progress
        )
        elapsed = time.time() - start_time
        
        print(f"✓ Completed in {elapsed:.2f} seconds")
        print(f"✓ Average: {elapsed/len(chunks):.3f} sec/chunk")
        
        return embedded_chunks
    
    def process_table_rows(self,
                          rows: List[Dict[str, Any]],
                          show_progress: bool = True) -> List[Dict[str, Any]]:
        """
        Generate embeddings for table rows.
        
        Args:
            rows: List of row objects from TableRowSerializer
            show_progress: Whether to show progress bar
            
        Returns:
            Rows with embeddings added
        """
        print("\n" + "="*80)
        print("PROCESSING TABLE ROWS")
        print("="*80)
        print(f"Rows to process: {len(rows)}")
        
        start_time = time.time()
        embedded_rows = self.generator.embed_prepared_objects(
            rows,
            text_field="text",
            show_progress=show_progress
        )
        elapsed = time.time() - start_time
        
        print(f"✓ Completed in {elapsed:.2f} seconds")
        print(f"✓ Average: {elapsed/len(rows):.3f} sec/row")
        
        return embedded_rows
    
    def process_all(self,
                   chunks: List[Dict[str, Any]],
                   table_rows: List[Dict[str, Any]],
                   show_progress: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """
        Process both text chunks and table rows.
        
        Args:
            chunks: List of chunk objects
            table_rows: List of row objects
            show_progress: Whether to show progress bar
            
        Returns:
            Dictionary with 'chunks' and 'rows' keys
        """
        results = {}
        
        if chunks:
            results['chunks'] = self.process_chunks(chunks, show_progress)
        else:
            results['chunks'] = []
        
        if table_rows:
            results['rows'] = self.process_table_rows(table_rows, show_progress)
        else:
            results['rows'] = []
        
        return results
    
    def process_from_json(self,
                         chunks_file: Optional[str] = None,
                         rows_file: Optional[str] = None,
                         show_progress: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load prepared data from JSON files and generate embeddings.
        
        Args:
            chunks_file: Path to JSON file with prepared chunks
            rows_file: Path to JSON file with prepared table rows
            show_progress: Whether to show progress bar
            
        Returns:
            Dictionary with embedded chunks and rows
        """
        chunks = []
        rows = []
        
        # Load chunks
        if chunks_file and Path(chunks_file).exists():
            print(f"\nLoading chunks from: {chunks_file}")
            with open(chunks_file, 'r', encoding='utf-8') as f:
                chunks = json.load(f)
            print(f"✓ Loaded {len(chunks)} chunks")
        
        # Load rows
        if rows_file and Path(rows_file).exists():
            print(f"\nLoading rows from: {rows_file}")
            with open(rows_file, 'r', encoding='utf-8') as f:
                rows = json.load(f)
            print(f"✓ Loaded {len(rows)} rows")
        
        # Process
        return self.process_all(chunks, rows, show_progress)
    
    def save_embedded_data(self,
                          embedded_data: Dict[str, List[Dict[str, Any]]],
                          output_dir: str = "./output",
                          prefix: str = "embedded") -> Dict[str, Path]:
        """
        Save embedded data to JSON files.
        
        Args:
            embedded_data: Dictionary with 'chunks' and 'rows'
            output_dir: Directory to save files
            prefix: Prefix for output filenames
            
        Returns:
            Dictionary with paths to saved files
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        saved_files = {}
        
        # Save chunks
        if embedded_data.get('chunks'):
            chunks_file = output_path / f"{prefix}_chunks.json"
            with open(chunks_file, 'w', encoding='utf-8') as f:
                json.dump(embedded_data['chunks'], f, indent=2, ensure_ascii=False)
            saved_files['chunks'] = chunks_file
            print(f"\n✓ Saved {len(embedded_data['chunks'])} embedded chunks to: {chunks_file}")
        
        # Save rows
        if embedded_data.get('rows'):
            rows_file = output_path / f"{prefix}_rows.json"
            with open(rows_file, 'w', encoding='utf-8') as f:
                json.dump(embedded_data['rows'], f, indent=2, ensure_ascii=False)
            saved_files['rows'] = rows_file
            print(f"✓ Saved {len(embedded_data['rows'])} embedded rows to: {rows_file}")
        
        return saved_files
    
    def get_statistics(self,
                      embedded_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Get statistics about embedded data.
        
        Args:
            embedded_data: Dictionary with 'chunks' and 'rows'
            
        Returns:
            Dictionary with statistics
        """
        chunks = embedded_data.get('chunks', [])
        rows = embedded_data.get('rows', [])
        
        stats = {
            'total_chunks': len(chunks),
            'total_rows': len(rows),
            'total_objects': len(chunks) + len(rows),
            'embedding_dim': self.generator.embedding_dim,
            'model_name': self.model_name,
            'batch_size': self.batch_size
        }
        
        # Calculate total text length
        if chunks:
            stats['total_chunk_chars'] = sum(len(c['text']) for c in chunks)
            stats['avg_chunk_chars'] = stats['total_chunk_chars'] / len(chunks)
        
        if rows:
            stats['total_row_chars'] = sum(len(r['text']) for r in rows)
            stats['avg_row_chars'] = stats['total_row_chars'] / len(rows)
        
        return stats


def embed_prepared_data(chunks_file: str,
                       rows_file: Optional[str] = None,
                       output_dir: str = "./output",
                       model_name: str = "intfloat/e5-large-v2",
                       batch_size: int = 32) -> Dict[str, Path]:
    """
    Convenience function to embed prepared data from files.
    
    Args:
        chunks_file: Path to prepared chunks JSON
        rows_file: Optional path to prepared rows JSON
        output_dir: Directory for output files
        model_name: SentenceTransformer model name
        batch_size: Batch size for encoding
        
    Returns:
        Dictionary with paths to embedded data files
    """
    pipeline = EmbeddingPipeline(
        model_name=model_name,
        batch_size=batch_size
    )
    
    embedded_data = pipeline.process_from_json(
        chunks_file=chunks_file,
        rows_file=rows_file
    )
    
    saved_files = pipeline.save_embedded_data(
        embedded_data,
        output_dir=output_dir
    )
    
    # Print statistics
    stats = pipeline.get_statistics(embedded_data)
    print("\n" + "="*80)
    print("EMBEDDING STATISTICS")
    print("="*80)
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    return saved_files
