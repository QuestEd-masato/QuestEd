# config/production.py - 本番環境設定
import os
from datetime import timedelta
from config_secure import Config

class ProductionConfig(Config):
    """本番環境設定 - 最高レベルのセキュリティと可用性"""
    
    # 環境識別
    ENV = 'production'
    DEBUG = False
    TESTING = False
    
    # 本番環境では強制的にセキュア設定
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_SSL_STRICT = True
    PREFERRED_URL_SCHEME = 'https'
    
    # データベース（本番用 - 読み書き分離）
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{Config.DB_USERNAME}:{Config.DB_PASSWORD}@{os.getenv('PROD_DB_WRITE_HOST')}/{Config.DB_NAME}?charset=utf8mb4&ssl_disabled=false&ssl_verify_cert=true"
    
    SQLALCHEMY_BINDS = {
        'read': f"mysql+pymysql://{Config.DB_USERNAME}:{Config.DB_PASSWORD}@{os.getenv('PROD_DB_READ_HOST')}/{Config.DB_NAME}?charset=utf8mb4&ssl_disabled=false&ssl_verify_cert=true"
    }
    
    # 本番用データベース設定（高パフォーマンス）
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'max_overflow': 30,
        'pool_timeout': 30,
        'pool_recycle': 1800,
        'pool_pre_ping': True,
        'connect_args': {
            'connect_timeout': 10,
            'ssl_disabled': False,
            'ssl_verify_cert': True,
            'ssl_ca': '/etc/ssl/certs/ca-certificates.crt'
        }
    }
    
    # Redis（本番用クラスター）
    CELERY_BROKER_URL = os.getenv('PROD_REDIS_CLUSTER_URL')
    CELERY_RESULT_BACKEND = os.getenv('PROD_REDIS_CLUSTER_URL')
    RATELIMIT_STORAGE_URL = os.getenv('PROD_REDIS_CLUSTER_URL')
    
    # ログ設定（本番用）
    LOG_LEVEL = 'WARNING'
    LOG_FILE = '/var/log/quested/production.log'
    
    # 本番用ログ追加設定
    LOG_BACKUP_COUNT = 30  # 30日分保持
    LOG_MAX_BYTES = 100 * 1024 * 1024  # 100MB
    
    # メール設定（本番用）
    MAIL_SERVER = os.getenv('PROD_MAIL_SERVER')
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('PROD_MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('PROD_MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = ('QuestEd System', os.getenv('PROD_MAIL_USERNAME'))
    
    # ファイルアップロード（S3本番バケット + CloudFront）
    UPLOAD_FOLDER = 's3://quested-production-uploads'
    CDN_DOMAIN = os.getenv('PROD_CDN_DOMAIN', 'cdn.quest-ed.jp')
    
    # 本番環境での厳格なCSP
    SECURITY_HEADERS = Config.SECURITY_HEADERS.copy()
    SECURITY_HEADERS.update({
        'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
        'Content-Security-Policy': (
            "default-src 'self'; "
            f"script-src 'self' https://{os.getenv('PROD_CDN_DOMAIN', 'cdn.quest-ed.jp')} https://cdn.jsdelivr.net; "
            f"style-src 'self' https://{os.getenv('PROD_CDN_DOMAIN', 'cdn.quest-ed.jp')} https://cdn.jsdelivr.net; "
            f"img-src 'self' data: https://{os.getenv('PROD_CDN_DOMAIN', 'cdn.quest-ed.jp')} https:; "
            "font-src 'self' https://cdnjs.cloudflare.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "upgrade-insecure-requests;"
        ),
        'X-Environment': 'production'
    })
    
    # OpenAI（本番用キー）
    OPENAI_API_KEY = os.getenv('PROD_OPENAI_API_KEY')
    
    # 監視・アラート（本番用）
    SENTRY_DSN = os.getenv('PROD_SENTRY_DSN')
    SENTRY_ENVIRONMENT = 'production'
    SENTRY_RELEASE = os.getenv('APP_VERSION', '1.0.0')
    
    # 本番用パフォーマンス設定
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = os.getenv('PROD_REDIS_CLUSTER_URL')
    CACHE_DEFAULT_TIMEOUT = 3600  # 1時間
    
    # セッション設定（本番用）
    PERMANENT_SESSION_LIFETIME = timedelta(hours=4)  # 4時間でタイムアウト
    
    # レート制限（本番用 - より厳格）
    RATELIMIT_DEFAULT = "50 per hour"
    RATELIMIT_LOGIN = "10 per minute"
    RATELIMIT_API = "1000 per hour"
    
    # 本番用セキュリティ設定
    PASSWORD_MIN_LENGTH = 12  # より厳格
    PASSWORD_HISTORY_CHECK = True  # パスワード履歴チェック
    
    # バックアップ設定
    BACKUP_ENABLED = True
    BACKUP_S3_BUCKET = os.getenv('PROD_BACKUP_BUCKET')
    BACKUP_SCHEDULE = "0 2 * * *"  # 毎日午前2時
    
    # 本番用必須環境変数チェック
    REQUIRED_ENV_VARS = [
        'SECRET_KEY',
        'PROD_DB_WRITE_HOST',
        'PROD_DB_READ_HOST', 
        'DB_PASSWORD',
        'PROD_REDIS_CLUSTER_URL',
        'PROD_OPENAI_API_KEY',
        'PROD_SENTRY_DSN',
        'PROD_MAIL_SERVER',
        'PROD_MAIL_USERNAME',
        'PROD_MAIL_PASSWORD'
    ]
    
    def __init__(self):
        # 本番環境の必須環境変数チェック
        missing_vars = [var for var in self.REQUIRED_ENV_VARS if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"本番環境で必須の環境変数が設定されていません: {', '.join(missing_vars)}")