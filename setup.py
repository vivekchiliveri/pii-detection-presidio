#!/usr/bin/env python3
"""
Setup script for PII Detection Application
Handles installation, model downloads, and initial configuration
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_step(step, message):
    """Print formatted step message"""
    print(f"\n{'='*60}")
    print(f"STEP {step}: {message}")
    print(f"{'='*60}")

def run_command(command, description):
    """Run shell command with error handling"""
    print(f"Running: {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed:")
        print(f"Command: {command}")
        print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    print_step(1, "Checking Python Version")
    
    if sys.version_info < (3, 8):
        print(f"✗ Python 3.8+ is required. Current version: {sys.version}")
        return False
    
    print(f"✓ Python version: {sys.version}")
    return True

def install_dependencies():
    """Install Python dependencies"""
    print_step(2, "Installing Dependencies")
    
    # Upgrade pip first
    if not run_command(f"{sys.executable} -m pip install --upgrade pip", "Upgrading pip"):
        return False
    
    # Install requirements
    if not run_command(f"{sys.executable} -m pip install -r requirements.txt", "Installing requirements"):
        return False
    
    return True

def download_spacy_model():
    """Download and install spaCy model"""
    print_step(3, "Downloading spaCy Model")
    
    # Download English model
    if not run_command(f"{sys.executable} -m spacy download en_core_web_sm", "Downloading en_core_web_sm"):
        return False
    
    # Try to download large model (optional)
    print("Attempting to download large model (optional)...")
    run_command(f"{sys.executable} -m spacy download en_core_web_lg", "Downloading en_core_web_lg (optional)")
    
    return True

def create_directories():
    """Create necessary directories"""
    print_step(4, "Creating Directories")
    
    directories = [
        'uploads',
        'logs',
        'temp',
        'static/css',
        'static/js',
        'static/images',
        'templates'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")
    
    return True

def create_env_file():
    """Create environment configuration file"""
    print_step(5, "Creating Environment Configuration")
    
    env_content = """# PII Detection Application Configuration

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
SECRET_KEY=your-secret-key-change-this-in-production

# Upload Configuration
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216  # 16MB in bytes

# Analysis Configuration
CONFIDENCE_THRESHOLD=0.5
DEFAULT_LANGUAGE=en

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/pii_detector.log

# Production Settings (uncomment for production)
# FLASK_ENV=production
# FLASK_DEBUG=False
# SECRET_KEY=generate-a-secure-secret-key
"""
    
    env_file = Path('.env')
    if not env_file.exists():
        env_file.write_text(env_content)
        print("✓ Created .env file with default configuration")
    else:
        print("✓ .env file already exists, skipping")
    
    return True

def test_installation():
    """Test the installation by importing key modules"""
    print_step(6, "Testing Installation")
    
    test_imports = [
        ('presidio_analyzer', 'Microsoft Presidio Analyzer'),
        ('presidio_anonymizer', 'Microsoft Presidio Anonymizer'),
        ('spacy', 'spaCy NLP library'),
        ('flask', 'Flask web framework'),
        ('pandas', 'Pandas data processing'),
        ('docx', 'Python-docx document processing'),
    ]
    
    all_passed = True
    
    for module_name, description in test_imports:
        try:
            __import__(module_name)
            print(f"✓ {description} imported successfully")
        except ImportError as e:
            print(f"✗ Failed to import {description}: {e}")
            all_passed = False
    
    # Test spaCy model
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        print("✓ spaCy English model loaded successfully")
    except OSError as e:
        print(f"✗ Failed to load spaCy model: {e}")
        all_passed = False
    
    # Test Presidio
    try:
        from presidio_analyzer import AnalyzerEngine
        analyzer = AnalyzerEngine()
        test_result = analyzer.analyze("Test text", language='en')
        print("✓ Presidio analyzer initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize Presidio: {e}")
        all_passed = False
    
    return all_passed

def create_run_scripts():
    """Create convenient run scripts"""
    print_step(7, "Creating Run Scripts")
    
    # Development script
    dev_script = """#!/bin/bash
# Development server startup script

echo "Starting PII Detection Application in development mode..."

export FLASK_ENV=development
export FLASK_DEBUG=True

python run.py
"""
    
    # Production script
    prod_script = """#!/bin/bash
# Production server startup script

echo "Starting PII Detection Application in production mode..."

export FLASK_ENV=production
export FLASK_DEBUG=False
export SERVER_TYPE=production

python run.py
"""
    
    # Windows batch files
    win_dev_script = """@echo off
echo Starting PII Detection Application in development mode...

set FLASK_ENV=development
set FLASK_DEBUG=True

python run.py
pause
"""
    
    win_prod_script = """@echo off
echo Starting PII Detection Application in production mode...

set FLASK_ENV=production
set FLASK_DEBUG=False
set SERVER_TYPE=production

python run.py
pause
"""
    
    scripts = [
        ('start_dev.sh', dev_script),
        ('start_prod.sh', prod_script),
        ('start_dev.bat', win_dev_script),
        ('start_prod.bat', win_prod_script)
    ]
    
    for filename, content in scripts:
        script_path = Path(filename)
        script_path.write_text(content)
        
        # Make shell scripts executable on Unix systems
        if filename.endswith('.sh') and os.name != 'nt':
            os.chmod(script_path, 0o755)
        
        print(f"✓ Created script: {filename}")
    
    return True

def display_success_message():
    """Display success message and instructions"""
    print_step("COMPLETE", "Installation Successful!")
    
    print("""
🎉 PII Detection Application has been successfully installed!

📋 Quick Start Guide:

1. Development Mode:
   - Linux/Mac: ./start_dev.sh
   - Windows:   start_dev.bat
   - Manual:    python run.py

2. Production Mode:
   - Linux/Mac: ./start_prod.sh  
   - Windows:   start_prod.bat
   - Manual:    FLASK_ENV=production python run.py

3. Access the application:
   - Web Interface: http://localhost:5000
   - API Documentation: http://localhost:5000/docs
   - Health Check: http://localhost:5000/api/health

📁 Directory Structure:
   - uploads/     - Temporary file uploads
   - logs/        - Application logs
   - templates/   - HTML templates
   - static/      - CSS, JS, images

⚙️ Configuration:
   - Edit .env file for custom settings
   - Check config.py for advanced options

🔧 Testing:
   - Run: python -m pytest (if tests are added)
   - Manual test: python app.py test-analyzer

📚 Documentation:
   - API docs available at /docs endpoint
   - README.md for detailed usage

🚀 You're all set! Start the application and begin detecting PII!
    """)

def main():
    """Main setup function"""
    print("🔧 PII Detection Application Setup")
    print("=" * 60)
    
    try:
        # Run setup steps
        steps = [
            check_python_version,
            install_dependencies,
            download_spacy_model,
            create_directories,
            create_env_file,
            test_installation,
            create_run_scripts
        ]
        
        for step_func in steps:
            if not step_func():
                print(f"\n❌ Setup failed at step: {step_func.__name__}")
                print("Please check the errors above and try again.")
                sys.exit(1)
        
        display_success_message()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()