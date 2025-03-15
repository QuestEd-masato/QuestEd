# extensions.py - Flask拡張
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_admin import Admin
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
admin = Admin(name='QuestEd Admin', template_mode='bootstrap4')
csrf = CSRFProtect()

login_manager.login_view = 'auth.login'
login_manager.login_message = 'この機能を使用するにはログインしてください'