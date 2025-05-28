#!/usr/bin/env python
"""Test imports to debug the issue"""

import sys
import os

print("Python executable:", sys.executable)
print("Python version:", sys.version)
print("Current directory:", os.getcwd())

print("\nTrying imports...")

try:
    import flask
    print("OK: flask imported successfully")
except ImportError as e:
    print(f"ERROR: flask import failed: {e}")

try:
    import flask_admin
    print("OK: flask_admin imported successfully")
except ImportError as e:
    print(f"ERROR: flask_admin import failed: {e}")

try:
    from config import get_config
    print("OK: config imported successfully")
except ImportError as e:
    print(f"ERROR: config import failed: {e}")

print("\nDone.")