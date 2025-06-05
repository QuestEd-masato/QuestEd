# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Flask-Adminを条件付きでインポート
try:
    from flask_admin import Admin
    admin = Admin(name='QuestEd Admin', template_mode='bootstrap4')
except ImportError:
    print("Warning: Flask-Admin not available. Admin interface will be disabled.")
    admin = None

# 共有インスタンスを作成
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# ログイン設定
login_manager.login_view = 'auth.login'
login_manager.login_message = 'この機能を使用するにはログインしてください'

# これらのインスタンスはアプリケーション初期化時に使用される
def init_app(app):
    """アプリケーションに拡張機能を初期化する"""
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    if admin:
        admin.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    
    # dbオブジェクトをアプリケーションのグローバル属性として設定
    app.db = db
    if admin:
        app.admin = admin
    
    return app