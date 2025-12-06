"""PDF upload and ingestion endpoints."""

import os
import json
import psycopg2
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from config import config
from core.extractor.pdf_reader import PDFReader
from core.extractor.cleaner import TextCleaner
from core.extractor.chunker import TextChunker
from core.embeddings.embedder import EmbeddingGenerator
from core.embeddings.table_embeddings import TableRowSerializer
from core.database.pgvector_store import PgVectorStore
from core.utils.logger import setup_logger

logger = setup_logger(__name__)

pdf_bp = Blueprint('pdf', __name__)

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

@pdf_bp.route('/upload', methods=['POST'])
def upload_pdf():
    """
    Upload and process PDF file.
    
    Expected form data:
        - file: PDF file
        - company: Company name (optional, will be extracted)
        - period: Reporting period (optional, will be extracted)
    
    Returns:
        JSON with ingestion status and statistics
    """
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Only PDF files are allowed'}), 400
        
        # Get optional metadata from form
        company = request.form.get('company')
        period = request.form.get('period')
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        logger.info(f"Processing PDF: {filename}")
        
        # Step 1: Extract text and tables from PDF
        logger.info("Step 1: Extracting content from PDF...")
        pdf_reader = PDFReader()
        extracted_data = pdf_reader.extract_with_structure(filepath)
        
        full_text = extracted_data['full_text']
        tables = extracted_data['tables']
        
        # Step 2: Clean and extract metadata
        logger.info("Step 2: Cleaning text and extracting metadata...")
        cleaner = TextCleaner()
        cleaned_text, metadata = cleaner.clean_and_extract_metadata(full_text)
        
        # Use extracted or provided metadata
        final_company = company or metadata.get('company', 'Unknown')
        final_period = period or metadata.get('period', 'Unknown')
        
        logger.info(f"Extracted metadata - Company: {final_company}, Period: {final_period}")
        
        # Step 3: Chunk the cleaned text
        logger.info("Step 3: Chunking text...")
        chunker = TextChunker(
            chunk_size=config.CHUNK_SIZE,
            overlap=config.CHUNK_OVERLAP
        )
        text_chunks = chunker.chunk_text(
            text=cleaned_text,
            company=final_company,
            year=final_period,
            doc_type="financial_report"
        )
        
        logger.info(f"Created {len(text_chunks)} text chunks")
        
        # Step 4: Serialize table rows
        logger.info("Step 4: Serializing table rows...")
        table_chunks = []
        if tables:
            serializer = TableRowSerializer()
            for table_name, df in tables.items():
                if not df.empty:
                    rows = serializer.serialize_dataframe(
                        df=df,
                        company=final_company,
                        period=final_period,
                        table_name=table_name
                    )
                    table_chunks.extend(rows)
        
        logger.info(f"Created {len(table_chunks)} table row chunks")
        
        # Step 5: Generate embeddings
        logger.info("Step 5: Generating embeddings...")
        embedder = EmbeddingGenerator(model_name=config.EMBEDDING_MODEL)
        
        # Embed text chunks
        embedded_text_chunks = embedder.embed_prepared_objects(text_chunks)
        logger.info(f"Generated embeddings for {len(embedded_text_chunks)} text chunks")
        
        # Embed table chunks if any
        embedded_table_chunks = []
        if table_chunks:
            embedded_table_chunks = embedder.embed_prepared_objects(table_chunks)
            logger.info(f"Generated embeddings for {len(embedded_table_chunks)} table chunks")
        
        # Combine all embedded chunks
        all_embedded_chunks = embedded_text_chunks + embedded_table_chunks
        
        # Step 6: Store in database
        logger.info("Step 6: Storing in vector database...")
        conn = psycopg2.connect(config.get_db_connection_string())
        store = PgVectorStore(conn)
        
        inserted_count = store.insert_documents(all_embedded_chunks, batch_size=100)
        
        conn.close()
        logger.info(f"Successfully inserted {inserted_count} documents")
        
        # Clean up uploaded file
        try:
            os.remove(filepath)
        except Exception as e:
            logger.warning(f"Could not remove uploaded file: {e}")
        
        # Return success response with statistics
        return jsonify({
            'success': True,
            'message': 'PDF processed and ingested successfully',
            'statistics': {
                'filename': filename,
                'company': final_company,
                'period': final_period,
                'text_chunks': len(embedded_text_chunks),
                'table_chunks': len(embedded_table_chunks),
                'total_chunks': inserted_count,
                'embedding_dimension': config.EMBEDDING_DIMENSION
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing PDF: {e}", exc_info=True)
        
        # Clean up file on error
        try:
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)
        except:
            pass
        
        return jsonify({
            'success': False,
            'error': 'PDF processing failed',
            'message': str(e)
        }), 500

@pdf_bp.route('/documents', methods=['GET'])
def list_documents():
    """
    List all ingested documents with metadata.
    
    Query parameters:
        - company: Filter by company (optional)
        - limit: Maximum results (default: 100)
    
    Returns:
        JSON with list of documents
    """
    try:
        company = request.args.get('company')
        limit = int(request.args.get('limit', 100))
        
        conn = psycopg2.connect(config.get_db_connection_string())
        store = PgVectorStore(conn)
        
        if company:
            documents = store.get_documents_by_company(company, limit)
        else:
            # Get count and list of companies
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT company 
                FROM financial_documents 
                WHERE company IS NOT NULL
                ORDER BY company
            """)
            companies = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("""
                SELECT COUNT(*) FROM financial_documents
            """)
            total_count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'total_documents': total_count,
                'companies': companies
            }), 200
        
        conn.close()
        
        return jsonify({
            'documents': documents,
            'count': len(documents)
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return jsonify({
            'error': 'Failed to list documents',
            'message': str(e)
        }), 500
