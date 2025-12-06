"""Flask application entry point for PDF RAG system."""

import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from routes.pdf_routes import pdf_bp
from routes.chat_routes import chat_bp
from routes.health_routes import health_bp
from core.utils.logger import setup_logger

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB default
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', './uploads')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Enable CORS for React frontend
CORS(app, resources={
    r"/api/*": {
        "origins": os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(','),
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Register blueprints
app.register_blueprint(health_bp, url_prefix='/api')
app.register_blueprint(pdf_bp, url_prefix='/api')
app.register_blueprint(chat_bp, url_prefix='/api')

# Global error handlers
@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error."""
    return jsonify({
        'error': 'File too large',
        'message': 'The uploaded file exceeds the maximum size limit'
    }), 413

@app.errorhandler(500)
def internal_server_error(error):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'error': 'Not found',
        'message': 'The requested resource was not found'
    }), 404

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'production') == 'development'
    
    logger.info(f"Starting Flask application on port {port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
