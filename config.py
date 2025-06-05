# config.py - アプリケーション設定
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    SECURE_UPLOAD_FOLDER = 'uploads'  # Webルート外のアップロードフォルダ
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 最大16MB
    
    # CSRF設定（セキュリティ強化）
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1時間でCSRFトークンを無効化
    
    # セッション設定
    PERMANENT_SESSION_LIFETIME = 1800  # 30分でセッションタイムアウト
    SESSION_COOKIE_SECURE = True  # HTTPS必須
    SESSION_COOKIE_HTTPONLY = True  # JavaScript経由でのCookieアクセス無効
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF攻撃対策
    
    # 追加の設定（必要に応じて）
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    TESTING = False
    
class DevelopmentConfig(Config):
    DEBUG = True
    # 開発環境ではHTTPS不要
    SESSION_COOKIE_SECURE = False
    
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    # 本番環境では強制的にDEBUGをFalseに
    @property
    def DEBUG(self):
        return False
    
# 環境に基づいて設定を選択
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """環境変数に基づいて設定を返す"""
    env = os.getenv('FLASK_ENV', 'development')
    return config_by_name.get(env, config_by_name['default'])