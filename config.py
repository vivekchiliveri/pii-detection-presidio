"""
Configuration settings for PII Detection Application
"""
import os
from typing import List, Dict, Any

class Config:
    """Base configuration class"""
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    PORT = int(os.environ.get('FLASK_PORT', 5000))
    
    # File upload configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'xlsx', 'csv', 'json'}
    
    # Presidio configuration
    DEFAULT_LANGUAGE = 'en'
    CONFIDENCE_THRESHOLD = float(os.environ.get('CONFIDENCE_THRESHOLD', 0.5))
    
    # Supported PII entities
    DEFAULT_PII_ENTITIES = [
        'CREDIT_CARD',
        'CRYPTO',
        'DATE_TIME',
        'EMAIL_ADDRESS',
        'IBAN_CODE',
        'IP_ADDRESS',
        'NRP',
        'LOCATION',
        'PERSON',
        'PHONE_NUMBER',
        'MEDICAL_LICENSE',
        'URL',
        'US_BANK_NUMBER',
        'US_DRIVER_LICENSE',
        'US_ITIN',
        'US_PASSPORT',
        'US_SSN'
    ]
    
    # Anonymization strategies
    ANONYMIZATION_STRATEGIES = {
        'REPLACE': 'replace',
        'REDACT': 'redact', 
        'HASH': 'hash',
        'MASK': 'mask',
        'ENCRYPT': 'encrypt',
        'CUSTOM': 'custom'
    }
    
    # Default anonymization mapping
    DEFAULT_ANONYMIZATION_CONFIG = {
        'PERSON': {'type': 'replace', 'new_value': '[PERSON]'},
        'EMAIL_ADDRESS': {'type': 'replace', 'new_value': '[EMAIL]'},
        'PHONE_NUMBER': {'type': 'replace', 'new_value': '[PHONE]'},
        'CREDIT_CARD': {'type': 'replace', 'new_value': '[CREDIT_CARD]'},
        'US_SSN': {'type': 'replace', 'new_value': '[SSN]'},
        'LOCATION': {'type': 'replace', 'new_value': '[LOCATION]'},
        'DATE_TIME': {'type': 'replace', 'new_value': '[DATE]'},
        'IP_ADDRESS': {'type': 'replace', 'new_value': '[IP_ADDRESS]'},
        'URL': {'type': 'replace', 'new_value': '[URL]'},
        'US_DRIVER_LICENSE': {'type': 'replace', 'new_value': '[DRIVER_LICENSE]'},
        'US_PASSPORT': {'type': 'replace', 'new_value': '[PASSPORT]'},
        'MEDICAL_LICENSE': {'type': 'replace', 'new_value': '[MEDICAL_LICENSE]'},
        'US_BANK_NUMBER': {'type': 'replace', 'new_value': '[BANK_NUMBER]'},
        'CRYPTO': {'type': 'replace', 'new_value': '[CRYPTO_ADDRESS]'},
        'IBAN_CODE': {'type': 'replace', 'new_value': '[IBAN]'},
        'US_ITIN': {'type': 'replace', 'new_value': '[ITIN]'},
        'NRP': {'type': 'replace', 'new_value': '[NRP]'}
    }
    
    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'pii_detector.log')
    
    @classmethod
    def init_app(cls, app):
        """Initialize app with configuration"""
        app.config.from_object(cls)
        
        # Create upload directory if it doesn't exist
        os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Production-specific initialization
        pass


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}