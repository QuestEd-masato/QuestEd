# app_simple.py - 簡易版アプリケーション（Flask-Adminなし）
from flask import Flask, redirect, url_for
from flask_login import current_user
import os
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

from config import get_config
from extensions import db, migrate, login_manager, csrf


def create_app_simple(config_object=None):
    """簡易版アプリケーションファクトリー（管理画面なし）"""
    app = Flask(__name__)
    
    # 設定を読み込む
    config = config_object or get_config()
    app.config.from_object(config)
    
    # SECRET_KEYが設定されているか確認
    if not app.config.get('SECRET_KEY'):
        print("WARNING: SECRET_KEY is not set!")
        # 開発環境用のデフォルトキーを設定
        app.config['SECRET_KEY'] = 'dev-secret-key-please-change-in-production'
    else:
        print(f"SECRET_KEY is set: {app.config['SECRET_KEY'][:10]}...")
    
    # アップロードフォルダの作成
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # 拡張機能を初期化（adminを除く）
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'この機能を使用するにはログインしてください。'
    
    # CSRFを初期化（SECRET_KEYが確実に設定された後）
    csrf.init_app(app)
    print(f"CSRF initialized with app config: SECRET_KEY exists = {bool(app.config.get('SECRET_KEY'))}")
    
    # テンプレートフィルターを登録
    register_template_filters(app)
    
    with app.app_context():
        # モデルをインポート
        from app.models import User
        
        # ユーザーローダーを設定
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))
        
        # Blueprintを登録
        register_blueprints(app)
        
        # BaseBuilderモジュールを初期化
        try:
            from basebuilder import init_app as init_basebuilder
            init_basebuilder(app)
        except ImportError:
            print("Warning: BaseBuilder module not found")
        
        # シェルコンテキストプロセッサを登録
        register_shell_context(app)
    
    return app


def register_template_filters(app):
    """テンプレートフィルターを登録"""
    import json
    
    @app.template_filter('nl2br')
    def nl2br(value):
        """改行をHTMLのbrタグに変換するフィルター"""
        if not value:
            return value
        import markupsafe
        escaped = markupsafe.escape(value)
        return markupsafe.Markup(str(escaped).replace('\n', '<br>\n'))
    
    @app.template_filter('fromjson')
    def fromjson_filter(value):
        """JSON文字列をPythonオブジェクトに変換するフィルター"""
        if not value:
            return {}
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}


def register_blueprints(app):
    """Blueprintを登録"""
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
    
    # ルートURLのハンドラー
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


def register_shell_context(app):
    """シェルコンテキストプロセッサを登録"""
    @app.shell_context_processor
    def make_shell_context():
        from app.models import db, User
        return {
            'db': db,
            'User': User
        }


# 実行
if __name__ == '__main__':
    app = create_app_simple()
    print("Starting Flask application (simplified version)...")
    print(f"Debug mode: {app.config.get('DEBUG', False)}")
    app.run(host='0.0.0.0', port=5000, debug=app.config.get('DEBUG', False))