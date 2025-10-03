"""
Main Flask application for PII Detection using Microsoft Presidio
Entry point for the web application
"""

import os
import logging
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge

from config import config
from api_routes import api
from pii_analyzer import get_analyzer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pii_detector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def create_app(config_name=None):
    """Application factory function"""
    
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration
    config_name = config_name or os.environ.get('FLASK_CONFIG', 'default')
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Enable CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Register blueprints
    app.register_blueprint(api)
    
    # Initialize analyzer (warm up the models)
    with app.app_context():
        try:
            logger.info("Initializing PII analyzer...")
            analyzer = get_analyzer()
            # Test with a simple text to warm up the models
            analyzer.analyze_text("This is a test text to warm up the models.")
            logger.info("PII analyzer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PII analyzer: {str(e)}")
    
    # Main web interface routes
    @app.route('/')
    def index():
        """Main application page"""
        return render_template('index.html')
    
    @app.route('/upload')
    def upload_page():
        """File upload page"""
        return render_template('upload.html')
    
    @app.route('/batch')
    def batch_page():
        """Batch processing page"""
        return render_template('batch.html')
    
    @app.route('/docs')
    def documentation():
        """API documentation page"""
        return render_template('docs.html')
    
    # Error handlers
    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(e):
        """Handle file upload size limit exceeded"""
        return jsonify({
            "success": False,
            "error": f"File too large. Maximum size: {app.config['MAX_CONTENT_LENGTH'] // (1024*1024)}MB"
        }), 413
    
    @app.errorhandler(404)
    def handle_not_found(e):
        """Handle 404 errors"""
        if request.path.startswith('/api/'):
            return jsonify({
                "success": False,
                "error": "API endpoint not found"
            }), 404
        return render_template('error.html', error="Page not found"), 404
    
    @app.errorhandler(500)
    def handle_internal_error(e):
        """Handle internal server errors"""
        logger.error(f"Internal server error: {str(e)}")
        if request.path.startswith('/api/'):
            return jsonify({
                "success": False,
                "error": "Internal server error"
            }), 500
        return render_template('error.html', error="Internal server error"), 500
    
    # Context processors for templates
    @app.context_processor
    def inject_config():
        """Inject configuration into templates"""
        return {
            'app_name': 'PII Detection System',
            'version': '1.0.0',
            'supported_file_types': list(app.config['ALLOWED_EXTENSIONS']),
            'max_file_size': app.config['MAX_CONTENT_LENGTH'] // (1024*1024)
        }
    
    # Custom CLI commands
    @app.cli.command('init-db')
    def init_db():
        """Initialize the database (placeholder for future use)"""
        logger.info("Database initialization placeholder")
    
    @app.cli.command('test-analyzer')
    def test_analyzer():
        """Test the PII analyzer functionality"""
        try:
            analyzer = get_analyzer()
            
            # Test texts
            test_texts = [
                "My name is John Smith and my email is john.smith@example.com",
                "Call me at 555-123-4567 or visit http://example.com",
                "My SSN is 123-45-6789 and credit card is 4532-1234-5678-9012"
            ]
            
            print("\n=== PII Analyzer Test ===")
            for i, text in enumerate(test_texts, 1):
                print(f"\nTest {i}: {text}")
                results = analyzer.analyze_text(text)
                
                if results:
                    for result in results:
                        print(f"  Found: {result['entity_type']} - '{result['text']}' (confidence: {result['score']:.3f})")
                else:
                    print("  No PII detected")
            
            print(f"\nSupported entities: {len(analyzer.get_supported_entities())}")
            print("Test completed successfully!")
            
        except Exception as e:
            print(f"Test failed: {str(e)}")
    
    return app


# Create the app instance
app = create_app()


if __name__ == '__main__':
    # Development server
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info("Starting PII Detection Application")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Port: {port}")
    
    try:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=debug,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise