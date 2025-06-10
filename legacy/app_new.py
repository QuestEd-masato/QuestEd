# app_new.py - 新しいメインアプリケーションファイル
from app import create_app

# アプリケーションを作成
app = create_app()

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])