# config.py - アプリケーション設定
import os
from dotenv import load_dotenv

# Celeryスケジュールを条件付きでインポート
try:
    from celery.schedules import crontab
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    # Celeryが利用できない場合のダミー関数
    def crontab(*args, **kwargs):
        return 86400.0  # 24時間ごとのフォールバック

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # データベース設定（デフォルト値付き）
    DB_USERNAME = os.getenv('DB_USERNAME', 'quested_user')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'quested_password')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_NAME = os.getenv('DB_NAME', 'quested')
    
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
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
    
    # Celery configuration
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    
    # Celery beat schedule (日次レポート)
    CELERY_BEAT_SCHEDULE = {
        'daily-reports': {
            'task': 'app.tasks.daily_report.generate_daily_reports',
            'schedule': crontab(hour=18, minute=0),  # 毎日18:00に実行
            'options': {'queue': 'default'}
        },
    }
    CELERY_TIMEZONE = 'Asia/Tokyo'
    CELERY_ENABLE_UTC = True
    
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