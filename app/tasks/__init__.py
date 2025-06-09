# app/tasks/__init__.py
import os
import logging

# Celeryを条件付きでインポート
try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    logging.warning("Celery not available. Background tasks will be disabled.")

def make_celery(app=None):
    """Celeryインスタンスを作成してFlaskアプリと統合"""
    if not CELERY_AVAILABLE:
        logging.warning("Celery not available - returning None")
        return None
        
    if not app:
        # アプリが提供されていない場合の基本設定
        broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
        result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
        
        celery = Celery(
            'quested_tasks',
            broker=broker_url,
            backend=result_backend
        )
    else:
        celery = Celery(
            app.import_name,
            backend=app.config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
            broker=app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
        )
        celery.conf.update(app.config)

        class ContextTask(celery.Task):
            """タスク実行時にFlaskアプリケーションコンテキストを作成"""
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask
    
    # 基本設定
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Asia/Tokyo',
        enable_utc=True,
        task_track_started=True,
        task_reject_on_worker_lost=True,
        result_expires=3600,  # 1時間後に結果を削除
    )
    
    return celery

# グローバルCeleryインスタンス
celery = make_celery() if CELERY_AVAILABLE else None