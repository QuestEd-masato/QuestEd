#!/usr/bin/env python3
"""
Celery Worker起動スクリプト
"""
import os
import sys

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.tasks import make_celery

def create_celery_app():
    """Celeryアプリケーション作成"""
    flask_app = create_app()
    celery = make_celery(flask_app)
    
    # タスクをインポート
    from app.tasks import daily_report
    
    return celery

# Celeryアプリケーションを作成
celery = create_celery_app()

if __name__ == '__main__':
    # Celery Workerとして実行
    celery.start()