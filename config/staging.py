# config/staging.py - ステージング環境設定
import os
from datetime import timedelta
from config_secure import Config

class StagingConfig(Config):
    """ステージング環境設定 - 本番環境に近い設定でテスト"""
    
    # 環境識別
    ENV = 'staging'
    DEBUG = False
    TESTING = False
    
    # データベース（ステージング用）
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{Config.DB_USERNAME}:{Config.DB_PASSWORD}@{os.getenv('STAGING_DB_HOST', 'staging-db.internal')}/{Config.DB_NAME}_staging?charset=utf8mb4&ssl_disabled=false"
    
    # セッション設定（本番同等）
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_SSL_STRICT = True
    PREFERRED_URL_SCHEME = 'https'
    
    # Redis（ステージング用）
    CELERY_BROKER_URL = os.getenv('STAGING_REDIS_URL', 'redis://staging-redis.internal:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('STAGING_REDIS_URL', 'redis://staging-redis.internal:6379/0')
    RATELIMIT_STORAGE_URL = os.getenv('STAGING_REDIS_URL', 'redis://staging-redis.internal:6379/1')
    
    # ログ設定
    LOG_LEVEL = 'INFO'
    LOG_FILE = '/var/log/quested/staging.log'
    
    # メール設定（ステージング用 - テストメール送信）
    MAIL_SERVER = os.getenv('STAGING_MAIL_SERVER', 'smtp.mailtrap.io')
    MAIL_PORT = 587
    MAIL_USERNAME = os.getenv('STAGING_MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('STAGING_MAIL_PASSWORD')
    
    # ファイルアップロード（S3ステージングバケット）
    UPLOAD_FOLDER = 's3://quested-staging-uploads'
    
    # セキュリティヘッダー（本番同等）
    SECURITY_HEADERS = Config.SECURITY_HEADERS.copy()
    
    # ステージング環境用の識別ヘッダー
    SECURITY_HEADERS['X-Environment'] = 'staging'
    
    # OpenAI（ステージング用キー）
    OPENAI_API_KEY = os.getenv('STAGING_OPENAI_API_KEY')
    
    # 監視・アラート
    SENTRY_DSN = os.getenv('STAGING_SENTRY_DSN')
    
    # キャッシュ設定
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = os.getenv('STAGING_REDIS_URL', 'redis://staging-redis.internal:6379/2')
    CACHE_DEFAULT_TIMEOUT = 300