#!/usr/bin/env python
# verify_setup.py - 設定を確認するスクリプト

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath('.'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

print("=== 環境変数の確認 ===")
print(f"SECRET_KEY: {os.getenv('SECRET_KEY', 'NOT SET')[:10]}..." if os.getenv('SECRET_KEY') else "SECRET_KEY: NOT SET")
print(f"DB_HOST: {os.getenv('DB_HOST', 'NOT SET')}")
print(f"DB_NAME: {os.getenv('DB_NAME', 'NOT SET')}")
print(f"FLASK_ENV: {os.getenv('FLASK_ENV', 'NOT SET')}")

print("\n=== アプリケーション設定の確認 ===")
try:
    from config import Config
    config = Config()
    print(f"Config.SECRET_KEY: {'SET' if config.SECRET_KEY else 'NOT SET'}")
    print(f"Config.WTF_CSRF_ENABLED: {getattr(config, 'WTF_CSRF_ENABLED', 'NOT SET')}")
    print(f"Config.DEBUG: {config.DEBUG}")
except Exception as e:
    print(f"Error loading config: {e}")

print("\n=== Flask拡張機能の確認 ===")
try:
    from app import create_app
    app = create_app()
    print(f"App created successfully")
    print(f"App.config['SECRET_KEY']: {'SET' if app.config.get('SECRET_KEY') else 'NOT SET'}")
    print(f"App.config['WTF_CSRF_ENABLED']: {app.config.get('WTF_CSRF_ENABLED', 'NOT SET')}")
    print(f"Extensions: {list(app.extensions.keys())}")
    print(f"Blueprints: {list(app.blueprints.keys())}")
except Exception as e:
    print(f"Error creating app: {e}")
    import traceback
    traceback.print_exc()

print("\n=== テスト完了 ===")
print("上記の情報を確認して、設定が正しく読み込まれているか確認してください。")