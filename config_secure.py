# config_secure.py - セキュリティ強化版アプリケーション設定
import os
from datetime import timedelta
from dotenv import load_dotenv

# Celeryスケジュールを条件付きでインポート
try:
    from celery.schedules import crontab
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    def crontab(*args, **kwargs):
        return 86400.0  # 24時間ごとのフォールバック

load_dotenv()

class Config:
    """基本設定クラス - セキュリティ強化版"""
    
    # === セキュリティ設定 ===
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        import secrets
        SECRET_KEY = secrets.token_hex(32)
        import logging
        logging.critical("SECRET_KEY not set! Generated temporary key. Set SECRET_KEY for production!")
    
    # セッション設定（セキュリティ強化）
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)  # 8時間でセッションタイムアウト
    SESSION_COOKIE_SECURE = True  # HTTPS必須
    SESSION_COOKIE_HTTPONLY = True  # JavaScript経由でのCookieアクセス無効
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF攻撃対策
    SESSION_COOKIE_NAME = 'quested_session'  # デフォルト名を変更
    
    # CSRF設定（強化）
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1時間でCSRFトークンを無効化
    WTF_CSRF_SSL_STRICT = True  # HTTPSでのみCSRF有効
    
    # === データベース設定 ===
    DB_USERNAME = os.getenv('DB_USERNAME', 'quested_user')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_NAME = os.getenv('DB_NAME', 'quested')
    
    if not DB_PASSWORD:
        raise ValueError("DB_PASSWORD environment variable is required")
    
    # SSL接続を強制
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?charset=utf8mb4&ssl_disabled=false"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_timeout': 20,
        'pool_recycle': 1800,  # 30分でコネクション再利用
        'pool_pre_ping': True,  # 接続確認
        'connect_args': {
            'connect_timeout': 10,
            'ssl_disabled': False
        }
    }
    
    # === ファイルアップロード設定 ===
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')  # Webルート外
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB制限
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    
    # === セキュリティヘッダー ===
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Content-Security-Policy': (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdnjs.cloudflare.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
    }
    
    # === Rate Limiting ===
    RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/1')
    RATELIMIT_DEFAULT = "100 per hour"
    RATELIMIT_HEADERS_ENABLED = True
    
    # === Celery設定 ===
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    CELERY_BEAT_SCHEDULE = {
        'daily-reports': {
            'task': 'app.tasks.daily_report.generate_daily_reports',
            'schedule': crontab(hour=17, minute=0),
            'options': {'queue': 'default'}
        },
    }
    CELERY_TIMEZONE = 'Asia/Tokyo'
    CELERY_ENABLE_UTC = True
    
    # === ログ設定 ===
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/quested.log')
    
    # === メール設定 ===
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    
    # === 外部API設定 ===
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # === その他の設定 ===
    DEBUG = False
    TESTING = False
    PREFERRED_URL_SCHEME = 'https'
    
    # パスワード設定
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGITS = True
    PASSWORD_REQUIRE_SPECIAL = True

class DevelopmentConfig(Config):
    """開発環境設定"""
    DEBUG = True
    
    # 開発環境では一部セキュリティ設定を緩和
    SESSION_COOKIE_SECURE = False  # HTTP接続を許可
    WTF_CSRF_SSL_STRICT = False
    PREFERRED_URL_SCHEME = 'http'
    
    # 開発用データベース
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{Config.DB_USERNAME}:{Config.DB_PASSWORD}@{Config.DB_HOST}/quested_dev?charset=utf8mb4"
    
    # CSP を緩和（開発用）
    SECURITY_HEADERS = Config.SECURITY_HEADERS.copy()
    SECURITY_HEADERS['Content-Security-Policy'] = (
        "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' https://cdnjs.cloudflare.com;"
    )

class TestingConfig(Config):
    """テスト環境設定"""
    TESTING = True
    WTF_CSRF_ENABLED = False  # テスト時はCSRF無効
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    RATELIMIT_ENABLED = False  # テスト時はレート制限無効
    
    # テスト用の短いタイムアウト
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=5)

class ProductionConfig(Config):
    """本番環境設定"""
    DEBUG = False
    TESTING = False
    
    # 本番環境では強制的にセキュア設定
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_SSL_STRICT = True
    PREFERRED_URL_SCHEME = 'https'
    
    # 本番データベース（レプリケーション設定）
    SQLALCHEMY_BINDS = {
        'read': f"mysql+pymysql://{Config.DB_USERNAME}:{Config.DB_PASSWORD}@{os.getenv('DB_READ_HOST', Config.DB_HOST)}/{Config.DB_NAME}?charset=utf8mb4&ssl_disabled=false"
    }
    
    # 本番環境での厳格なCSP
    SECURITY_HEADERS = Config.SECURITY_HEADERS.copy()
    SECURITY_HEADERS['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' https://cdnjs.cloudflare.com; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    
    # ログレベルを WARNING に
    LOG_LEVEL = 'WARNING'

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
    config_class = config_by_name.get(env, config_by_name['default'])
    
    # 必須環境変数のチェック
    if env == 'production':
        required_vars = ['SECRET_KEY', 'DB_PASSWORD', 'OPENAI_API_KEY']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return config_class