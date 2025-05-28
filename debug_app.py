#!/usr/bin/env python
# debug_app.py - アプリケーションのデバッグ

from app import create_app
from flask import jsonify
import os

app = create_app()

@app.route('/debug-info')
def debug_info():
    """デバッグ情報を表示"""
    return jsonify({
        'SECRET_KEY_SET': bool(app.config.get('SECRET_KEY')),
        'SECRET_KEY_VALUE': app.config.get('SECRET_KEY', 'NOT SET')[:10] + '...' if app.config.get('SECRET_KEY') else 'NOT SET',
        'WTF_CSRF_ENABLED': app.config.get('WTF_CSRF_ENABLED', True),
        'WTF_CSRF_TIME_LIMIT': app.config.get('WTF_CSRF_TIME_LIMIT'),
        'WTF_CSRF_SSL_STRICT': app.config.get('WTF_CSRF_SSL_STRICT', True),
        'extensions': list(app.extensions.keys()),
        'blueprints': list(app.blueprints.keys()),
        'env_vars': {
            'SECRET_KEY_FROM_ENV': os.getenv('SECRET_KEY', 'NOT SET')[:10] + '...' if os.getenv('SECRET_KEY') else 'NOT SET',
            'FLASK_ENV': os.getenv('FLASK_ENV', 'NOT SET'),
            'FLASK_DEBUG': os.getenv('FLASK_DEBUG', 'NOT SET')
        }
    })

if __name__ == '__main__':
    print("\n=== アプリケーションデバッグ情報 ===")
    print(f"SECRET_KEY is set: {bool(app.config.get('SECRET_KEY'))}")
    print(f"SECRET_KEY value: {app.config.get('SECRET_KEY', 'NOT SET')[:10]}..." if app.config.get('SECRET_KEY') else "SECRET_KEY: NOT SET")
    print(f"WTF_CSRF_ENABLED: {app.config.get('WTF_CSRF_ENABLED', True)}")
    print(f"Extensions loaded: {list(app.extensions.keys())}")
    print(f"Blueprints registered: {list(app.blueprints.keys())}")
    print("\nStarting debug server on http://localhost:5002/debug-info")
    app.run(debug=True, port=5002)