#!/usr/bin/env python
# app_fixed.py - CSRFエラーを修正したバージョン

from flask import Flask, redirect, url_for, render_template
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import os

# .envファイルを読み込む
load_dotenv()

# アプリケーションを作成
app = Flask(__name__)

# 設定
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['WTF_CSRF_ENABLED'] = True  # 明示的に設定

# 拡張機能を初期化
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
csrf = CSRFProtect(app)

# ログイン設定
login_manager.login_view = 'auth.login'
login_manager.login_message = 'この機能を使用するにはログインしてください。'

# デバッグ情報を出力
print(f"SECRET_KEY is set: {bool(app.config.get('SECRET_KEY'))}")
print(f"SECRET_KEY value: {app.config.get('SECRET_KEY', 'NOT SET')[:10]}...")
print(f"WTF_CSRF_ENABLED: {app.config.get('WTF_CSRF_ENABLED', True)}")

# Blueprintを登録
from app.auth import auth_bp
from app.admin import admin_bp
from app.teacher import teacher_bp
from app.student import student_bp
from app.api import api_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(teacher_bp)
app.register_blueprint(student_bp)
app.register_blueprint(api_bp)

# ルートURL
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_panel.dashboard'))
        elif current_user.role == 'teacher':
            return redirect(url_for('teacher.dashboard'))
        elif current_user.role == 'student':
            return redirect(url_for('student.dashboard'))
    return redirect(url_for('auth.login'))

# デバッグ用エンドポイント
@app.route('/debug-csrf')
def debug_csrf():
    return {
        'SECRET_KEY_SET': bool(app.config.get('SECRET_KEY')),
        'WTF_CSRF_ENABLED': app.config.get('WTF_CSRF_ENABLED', True),
        'extensions': list(app.extensions.keys())
    }

# ユーザーローダー
@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))

if __name__ == '__main__':
    # アップロードフォルダを作成
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # BaseBuilderモジュールを初期化
    try:
        from basebuilder import init_app as init_basebuilder
        init_basebuilder(app)
    except ImportError:
        print("BaseBuilder module not available")
    
    app.run(debug=True)