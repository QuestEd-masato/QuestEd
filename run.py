#!/usr/bin/env python
# run.py - アプリケーション実行スクリプト
"""
新しいBlueprint構造でアプリケーションを実行するスクリプト

使用方法:
    python run.py
    
環境変数:
    FLASK_ENV: development/production (デフォルト: development)
    FLASK_DEBUG: デバッグモード (デフォルト: FLASK_ENV=developmentの場合True)
"""

from app import create_app
import os

# 環境変数の設定
os.environ.setdefault('FLASK_ENV', 'development')

# アプリケーションを作成
app = create_app()

if __name__ == '__main__':
    # デバッグモードは設定から取得
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config['DEBUG']
    )