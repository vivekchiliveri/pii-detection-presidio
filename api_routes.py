"""
Flask API routes for PII detection application
Handles all HTTP endpoints for text analysis, file processing, and anonymization
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

from pii_analyzer import get_analyzer
from file_processor import get_file_processor
from config import Config

# Set up logging
logger = logging.getLogger(__name__)

# Create Blueprint
api = Blueprint('api', __name__, url_prefix='/api')


def validate_request_data(required_fields: List[str], data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate required fields in request data"""
    errors = []
    for field in required_fields:
        if field not in data or data[field] is None:
            errors.append(f"Missing required field: {field}")
    
    if errors:
        return {"error": "Validation failed", "details": errors}
    return {}


def handle_error(error_message: str, status_code: int = 400) -> tuple:
    """Standard error response handler"""
    logger.error(error_message)
    return jsonify({
        "success": False,
        "error": error_message,
        "timestamp": datetime.now().isoformat()
    }), status_code


@api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        analyzer = get_analyzer()
        return jsonify({
            "success": True,
            "status": "healthy",
            "version": "1.0.0",
            "supported_entities": analyzer.get_supported_entities(),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return handle_error(f"Health check failed: {str(e)}", 503)


@api.route('/analyze', methods=['POST'])
def analyze_text():
    """Analyze text for PII entities"""
    try:
        data = request.get_json()
        if not data:
            return handle_error("No JSON data provided")
        
        # Validate required fields
        validation_error = validate_request_data(['text'], data)
        if validation_error:
            return handle_error(validation_error['error'])
        
        text = data['text']
        if not isinstance(text, str) or not text.strip():
            return handle_error("Text must be a non-empty string")
        
        # Get optional parameters
        entities = data.get('entities', None)
        language = data.get('language', 'en')
        score_threshold = data.get('score_threshold', Config.CONFIDENCE_THRESHOLD)
        
        # Validate entities if provided
        analyzer = get_analyzer()
        if entities:
            entities = analyzer.validate_entities(entities)
        
        # Perform analysis
        results = analyzer.analyze_text(
            text=text,
            entities=entities,
            language=language,
            score_threshold=score_threshold
        )
        
        # Generate statistics
        statistics = analyzer.get_statistics(results)
        
        return jsonify({
            "success": True,
            "results": results,
            "statistics": statistics,
            "metadata": {
                "text_length": len(text),
                "entities_requested": entities or analyzer.entities,
                "language": language,
                "score_threshold": score_threshold
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return handle_error(f"Analysis failed: {str(e)}")


@api.route('/anonymize', methods=['POST'])
def anonymize_text():
    """Anonymize text based on PII detection"""
    try:
        data = request.get_json()
        if not data:
            return handle_error("No JSON data provided")
        
        # Validate required fields
        validation_error = validate_request_data(['text'], data)
        if validation_error:
            return handle_error(validation_error['error'])
        
        text = data['text']
        if not isinstance(text, str) or not text.strip():
            return handle_error("Text must be a non-empty string")
        
        # Get optional parameters
        analyzer_results = data.get('analyzer_results', None)
        anonymization_config = data.get('anonymization_config', None)
        entities = data.get('entities', None)
        score_threshold = data.get('score_threshold', Config.CONFIDENCE_THRESHOLD)
        
        analyzer = get_analyzer()
        
        # If no pre-analyzed results, perform analysis first
        if not analyzer_results:
            if entities:
                entities = analyzer.validate_entities(entities)
            
            analyzer_results = analyzer.analyze_text(
                text=text,
                entities=entities,
                score_threshold=score_threshold
            )
        
        # Perform anonymization
        anonymized_result = analyzer.anonymize_text(
            text=text,
            analyzer_results=analyzer_results,
            anonymization_config=anonymization_config
        )
        
        return jsonify({
            "success": True,
            "original_text": text,
            "anonymized_text": anonymized_result['text'],
            "anonymized_items": anonymized_result['items'],
            "detected_entities": analyzer_results,
            "statistics": analyzer.get_statistics(analyzer_results),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return handle_error(f"Anonymization failed: {str(e)}")


@api.route('/analyze-file', methods=['POST'])
def analyze_file():
    """Analyze uploaded file for PII"""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return handle_error("No file uploaded")
        
        file = request.files['file']
        if file.filename == '':
            return handle_error("No file selected")
        
        # Get optional parameters from form data
        entities = request.form.get('entities', None)
        if entities:
            try:
                entities = entities.split(',') if isinstance(entities, str) else entities
            except:
                entities = None
        
        score_threshold = float(request.form.get('score_threshold', Config.CONFIDENCE_THRESHOLD))
        language = request.form.get('language', 'en')
        
        # Validate file
        processor = get_file_processor()
        if not processor.is_supported_file(file.filename):
            return handle_error(f"Unsupported file type: {processor.get_file_type(file.filename)}")
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        temp_filename = f"{file_id}_{filename}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], temp_filename)
        
        try:
            file.save(file_path)
            
            # Process file
            file_data = processor.process_file(file_path, filename)
            
            # Analyze extracted content
            analyzer = get_analyzer()
            if entities:
                entities = analyzer.validate_entities(entities)
            
            results = analyzer.analyze_text(
                text=file_data['content'],
                entities=entities,
                language=language,
                score_threshold=score_threshold
            )
            
            # Generate statistics
            statistics = analyzer.get_statistics(results)
            
            return jsonify({
                "success": True,
                "file_info": {
                    "filename": file_data['filename'],
                    "file_type": file_data['file_type'],
                    "metadata": file_data['metadata']
                },
                "content_preview": file_data['content'][:500] + ('...' if len(file_data['content']) > 500 else ''),
                "results": results,
                "statistics": statistics,
                "analysis_metadata": {
                    "content_length": len(file_data['content']),
                    "entities_requested": entities or analyzer.entities,
                    "language": language,
                    "score_threshold": score_threshold
                },
                "timestamp": datetime.now().isoformat()
            })
            
        finally:
            # Clean up temporary file
            processor.cleanup_file(file_path)
            
    except RequestEntityTooLarge:
        return handle_error("File too large", 413)
    except Exception as e:
        return handle_error(f"File analysis failed: {str(e)}")


@api.route('/anonymize-file', methods=['POST'])
def anonymize_file():
    """Anonymize uploaded file"""
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return handle_error("No file uploaded")
        
        file = request.files['file']
        if file.filename == '':
            return handle_error("No file selected")
        
        # Get optional parameters
        entities = request.form.get('entities', None)
        if entities:
            try:
                entities = entities.split(',') if isinstance(entities, str) else entities
            except:
                entities = None
        
        score_threshold = float(request.form.get('score_threshold', Config.CONFIDENCE_THRESHOLD))
        language = request.form.get('language', 'en')
        
        # Parse anonymization config if provided
        anonymization_config = None
        config_str = request.form.get('anonymization_config', None)
        if config_str:
            try:
                import json
                anonymization_config = json.loads(config_str)
            except:
                logger.warning("Invalid anonymization config provided, using defaults")
        
        # Validate file
        processor = get_file_processor()
        if not processor.is_supported_file(file.filename):
            return handle_error(f"Unsupported file type: {processor.get_file_type(file.filename)}")
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        temp_filename = f"{file_id}_{filename}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], temp_filename)
        
        try:
            file.save(file_path)
            
            # Process file
            file_data = processor.process_file(file_path, filename)
            
            # Analyze and anonymize content
            analyzer = get_analyzer()
            if entities:
                entities = analyzer.validate_entities(entities)
            
            # First analyze
            analysis_results = analyzer.analyze_text(
                text=file_data['content'],
                entities=entities,
                language=language,
                score_threshold=score_threshold
            )
            
            # Then anonymize
            anonymized_result = analyzer.anonymize_text(
                text=file_data['content'],
                analyzer_results=analysis_results,
                anonymization_config=anonymization_config
            )
            
            return jsonify({
                "success": True,
                "file_info": {
                    "filename": file_data['filename'],
                    "file_type": file_data['file_type'],
                    "metadata": file_data['metadata']
                },
                "original_content": file_data['content'],
                "anonymized_content": anonymized_result['text'],
                "anonymized_items": anonymized_result['items'],
                "detected_entities": analysis_results,
                "statistics": analyzer.get_statistics(analysis_results),
                "timestamp": datetime.now().isoformat()
            })
            
        finally:
            # Clean up temporary file
            processor.cleanup_file(file_path)
            
    except RequestEntityTooLarge:
        return handle_error("File too large", 413)
    except Exception as e:
        return handle_error(f"File anonymization failed: {str(e)}")


@api.route('/entities', methods=['GET'])
def get_supported_entities():
    """Get list of supported PII entities"""
    try:
        analyzer = get_analyzer()
        entities = analyzer.get_supported_entities()
        
        return jsonify({
            "success": True,
            "entities": entities,
            "count": len(entities),
            "default_entities": Config.DEFAULT_PII_ENTITIES,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return handle_error(f"Failed to get entities: {str(e)}")


@api.route('/config', methods=['GET'])
def get_configuration():
    """Get current application configuration"""
    try:
        return jsonify({
            "success": True,
            "config": {
                "supported_file_types": list(Config.ALLOWED_EXTENSIONS),
                "max_file_size_mb": Config.MAX_CONTENT_LENGTH / (1024 * 1024),
                "default_language": Config.DEFAULT_LANGUAGE,
                "default_confidence_threshold": Config.CONFIDENCE_THRESHOLD,
                "default_entities": Config.DEFAULT_PII_ENTITIES,
                "anonymization_strategies": Config.ANONYMIZATION_STRATEGIES,
                "default_anonymization_config": Config.DEFAULT_ANONYMIZATION_CONFIG
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return handle_error(f"Failed to get configuration: {str(e)}")


@api.route('/batch-analyze', methods=['POST'])
def batch_analyze():
    """Analyze multiple texts in batch"""
    try:
        data = request.get_json()
        if not data:
            return handle_error("No JSON data provided")
        
        # Validate required fields
        validation_error = validate_request_data(['texts'], data)
        if validation_error:
            return handle_error(validation_error['error'])
        
        texts = data['texts']
        if not isinstance(texts, list) or not texts:
            return handle_error("Texts must be a non-empty list")
        
        # Get optional parameters
        entities = data.get('entities', None)
        language = data.get('language', 'en')
        score_threshold = data.get('score_threshold', Config.CONFIDENCE_THRESHOLD)
        
        analyzer = get_analyzer()
        if entities:
            entities = analyzer.validate_entities(entities)
        
        # Process each text
        batch_results = []
        total_entities = 0
        
        for i, text in enumerate(texts):
            if not isinstance(text, str):
                batch_results.append({
                    "index": i,
                    "error": "Text must be a string",
                    "results": [],
                    "statistics": {}
                })
                continue
            
            try:
                results = analyzer.analyze_text(
                    text=text,
                    entities=entities,
                    language=language,
                    score_threshold=score_threshold
                )
                
                statistics = analyzer.get_statistics(results)
                total_entities += len(results)
                
                batch_results.append({
                    "index": i,
                    "text_preview": text[:100] + ('...' if len(text) > 100 else ''),
                    "results": results,
                    "statistics": statistics
                })
                
            except Exception as e:
                batch_results.append({
                    "index": i,
                    "error": str(e),
                    "results": [],
                    "statistics": {}
                })
        
        return jsonify({
            "success": True,
            "batch_results": batch_results,
            "batch_statistics": {
                "total_texts": len(texts),
                "total_entities_found": total_entities,
                "successful_analyses": len([r for r in batch_results if 'error' not in r]),
                "failed_analyses": len([r for r in batch_results if 'error' in r])
            },
            "metadata": {
                "entities_requested": entities or analyzer.entities,
                "language": language,
                "score_threshold": score_threshold
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return handle_error(f"Batch analysis failed: {str(e)}")


# Error handlers
@api.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    return handle_error("File too large", 413)


@api.errorhandler(404)
def handle_not_found(e):
    return handle_error("Endpoint not found", 404)


@api.errorhandler(405)
def handle_method_not_allowed(e):
    return handle_error("Method not allowed", 405)


@api.errorhandler(500)
def handle_internal_error(e):
    return handle_error("Internal server error", 500)