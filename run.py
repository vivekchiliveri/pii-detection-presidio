#!/usr/bin/env python3
"""
Production-ready application runner for PII Detection System
Handles environment setup, logging, and graceful shutdown
"""

import os
import sys
import signal
import logging
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from app import create_app
from config import config

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pii_detector.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class PIIDetectionServer:
    """Production server wrapper for PII Detection application"""
    
    def __init__(self):
        self.app = None
        self.server = None
        self.is_running = False
        
    def setup_directories(self):
        """Create necessary directories"""
        directories = ['logs', 'uploads', 'temp']
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
            logger.info(f"Ensured directory exists: {directory}")
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def validate_environment(self):
        """Validate environment and dependencies"""
        logger.info("Validating environment...")
        
        # Check Python version
        if sys.version_info < (3, 8):
            raise RuntimeError("Python 3.8 or higher is required")
        
        # Check required environment variables
        env_config = os.environ.get('FLASK_CONFIG', 'production')
        if env_config not in config:
            raise RuntimeError(f"Invalid FLASK_CONFIG: {env_config}")
        
        # Test import of critical dependencies
        try:
            import presidio_analyzer
            import presidio_anonymizer
            import spacy
            import flask
        except ImportError as e:
            raise RuntimeError(f"Missing required dependency: {e}")
        
        logger.info("Environment validation passed")
    
    def create_application(self):
        """Create and configure Flask application"""
        env_config = os.environ.get('FLASK_CONFIG', 'production')
        self.app = create_app(env_config)
        logger.info(f"Created application with config: {env_config}")
        return self.app
    
    def start_development_server(self):
        """Start development server"""
        if not self.app:
            self.create_application()
        
        host = self.app.config.get('HOST', '127.0.0.1')
        port = self.app.config.get('PORT', 5000)
        debug = self.app.config.get('DEBUG', False)
        
        logger.info(f"Starting development server on {host}:{port}")
        logger.info(f"Debug mode: {debug}")
        
        try:
            self.is_running = True
            self.app.run(
                host=host,
                port=port,
                debug=debug,
                threaded=True,
                use_reloader=False  # Disable reloader in production
            )
        except Exception as e:
            logger.error(f"Failed to start development server: {e}")
            raise
    
    def start_production_server(self):
        """Start production server using gunicorn"""
        try:
            import gunicorn.app.wsgiapp
            
            if not self.app:
                self.create_application()
            
            # Gunicorn configuration
            gunicorn_config = {
                'bind': f"{self.app.config.get('HOST', '0.0.0.0')}:{self.app.config.get('PORT', 5000)}",
                'workers': int(os.environ.get('WORKERS', 4)),
                'worker_class': 'sync',
                'worker_connections': 1000,
                'max_requests': 1000,
                'max_requests_jitter': 100,
                'timeout': 30,
                'keepalive': 2,
                'preload_app': True,
                'access_logfile': 'logs/access.log',
                'error_logfile': 'logs/error.log',
                'log_level': 'info',
                'capture_output': True
            }
            
            logger.info("Starting production server with gunicorn")
            logger.info(f"Configuration: {gunicorn_config}")
            
            # Create gunicorn application
            from gunicorn.app.base import BaseApplication
            
            class StandaloneApplication(BaseApplication):
                def __init__(self, app, options=None):
                    self.options = options or {}
                    self.application = app
                    super().__init__()
                
                def load_config(self):
                    for key, value in self.options.items():
                        if key in self.cfg.settings and value is not None:
                            self.cfg.set(key.lower(), value)
                
                def load(self):
                    return self.application
            
            self.is_running = True
            StandaloneApplication(self.app, gunicorn_config).run()
            
        except ImportError:
            logger.warning("Gunicorn not available, falling back to development server")
            self.start_development_server()
        except Exception as e:
            logger.error(f"Failed to start production server: {e}")
            raise
    
    def shutdown(self):
        """Graceful shutdown"""
        if self.is_running:
            logger.info("Shutting down PII Detection Server...")
            self.is_running = False
            
            # Cleanup temporary files
            import tempfile
            import shutil
            temp_dir = Path('temp')
            if temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                    logger.info("Cleaned up temporary files")
                except Exception as e:
                    logger.warning(f"Error cleaning temp files: {e}")
            
            logger.info("Shutdown complete")
    
    def run(self):
        """Main entry point"""
        try:
            logger.info("Starting PII Detection Server...")
            
            # Setup
            self.setup_directories()
            self.setup_signal_handlers()
            self.validate_environment()
            
            # Determine server type
            server_type = os.environ.get('SERVER_TYPE', 'auto')
            is_development = os.environ.get('FLASK_ENV') == 'development'
            
            if server_type == 'development' or is_development:
                self.start_development_server()
            elif server_type == 'production':
                self.start_production_server()
            else:
                # Auto-detect
                if os.environ.get('FLASK_CONFIG') == 'development':
                    self.start_development_server()
                else:
                    self.start_production_server()
                    
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.error(f"Server failed to start: {e}")
            sys.exit(1)
        finally:
            self.shutdown()


def main():
    """Main function"""
    server = PIIDetectionServer()
    server.run()


if __name__ == '__main__':
    main()