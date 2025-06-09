# app/tasks/__init__.py
from celery import Celery
import os

def make_celery(app):
    """Celeryインスタンスを作成してFlaskアプリと統合"""
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        """タスク実行時にFlaskアプリケーションコンテキストを作成"""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

# グローバルCeleryインスタンス（後でapp作成時に初期化）
celery = None