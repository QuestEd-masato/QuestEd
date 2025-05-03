# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_admin import Admin
from flask_wtf.csrf import CSRFProtect

# 共有インスタンスを作成
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
admin = Admin(name='QuestEd Admin', template_mode='bootstrap4')
csrf = CSRFProtect()

# ログイン設定
login_manager.login_view = 'auth.login'
login_manager.login_message = 'この機能を使用するにはログインしてください'

# これらのインスタンスはアプリケーション初期化時に使用される
def init_app(app):
    """アプリケーションに拡張機能を初期化する"""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    admin.init_app(app)
    csrf.init_app(app)
    
    # dbとadminオブジェクトをアプリケーションのグローバル属性として設定
    app.db = db
    app.admin = admin
    
    return app