#!/usr/bin/env python
"""Simple run script to test the refactored application"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variable
os.environ.setdefault('FLASK_ENV', 'development')

# Import and run
from app_factory import create_app

app = create_app()

if __name__ == '__main__':
    print("Starting Flask application...")
    print(f"Debug mode: {app.config.get('DEBUG', False)}")
    app.run(host='0.0.0.0', port=5000, debug=app.config.get('DEBUG', False))