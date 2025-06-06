# app/__init__.py
from flask import Flask, redirect, url_for, send_from_directory, abort, make_response
from flask_login import current_user, login_required
import os

from config import get_config
from extensions import db, migrate, login_manager, admin, csrf, limiter

# Flask-Admin関連のインポートを条件付きに
if admin:
    from flask_admin import AdminIndexView
    from flask_admin.contrib.sqla import ModelView
    
    class AdminModelView(ModelView):
        """管理画面のカスタムビュー"""
        def is_accessible(self):
            return current_user.is_authenticated and current_user.role == 'teacher'
        
        def inaccessible_callback(self, name, **kwargs):
            return redirect(url_for('auth.login'))

    class CustomAdminIndexView(AdminIndexView):
        """管理画面のインデックスビュー"""
        def is_accessible(self):
            return current_user.is_authenticated and current_user.role == 'teacher'
        
        def inaccessible_callback(self, name, **kwargs):
            return redirect(url_for('auth.login'))
else:
    AdminModelView = None
    CustomAdminIndexView = None


def create_app(config_object=None):
    """アプリケーションファクトリー"""
    # テンプレートフォルダを親ディレクトリに設定
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # 設定を読み込む
    config = config_object or get_config()
    app.config.from_object(config)
    
    # アップロードフォルダの作成
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # 拡張機能を初期化
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'この機能を使用するにはログインしてください。'
    
    # 管理画面を初期化
    if admin:
        admin.init_app(app)
    
    csrf.init_app(app)
    limiter.init_app(app)
    
    # テンプレートフィルターを登録
    register_template_filters(app)
    
    with app.app_context():
        # モデルをインポート
        from app.models import (
            User, School, SchoolYear, ClassGroup, StudentEnrollment,
            Class, ClassEnrollment, MainTheme, InquiryTheme, InterestSurvey,
            PersonalitySurvey, ActivityLog, Todo, Goal, StudentEvaluation,
            Curriculum, RubricTemplate, Group, GroupMembership, ChatHistory,
            Milestone
        )
        
        # ユーザーローダーを設定
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))
        
        # 管理画面にモデルを登録
        register_admin_views()
        
        # Blueprintを登録
        register_blueprints(app)
        
        # 特殊なルートを登録
        from app.special_routes import register_special_routes
        register_special_routes(app)
        
        # BaseBuilderモジュールを初期化
        from basebuilder import init_app as init_basebuilder
        init_basebuilder(app)
        
        # シェルコンテキストプロセッサを登録
        register_shell_context(app)
    
    return app


def register_template_filters(app):
    """テンプレートフィルターを登録"""
    import json
    
    @app.template_filter('nl2br')
    def nl2br(value):
        """改行をHTMLのbrタグに変換するフィルター（XSS対策付き）"""
        if not value:
            return value
        
        # bleachでサニタイズ（HTMLタグを除去）
        import bleach
        import markupsafe
        
        # 許可するタグを制限（brタグのみ）
        allowed_tags = ['br']
        cleaned = bleach.clean(str(value), tags=allowed_tags, strip=True)
        
        # エスケープしてから改行を<br>に変換
        escaped = markupsafe.escape(cleaned)
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


def register_admin_views():
    """管理画面にモデルビューを登録"""
    if not admin or not AdminModelView:
        return
        
    from app.models import (
        User, School, SchoolYear, ClassGroup, StudentEnrollment,
        Class, ClassEnrollment, MainTheme, InquiryTheme, InterestSurvey,
        PersonalitySurvey, ActivityLog, Todo, Goal, StudentEvaluation,
        Curriculum, RubricTemplate, Group, GroupMembership, ChatHistory,
        Milestone, db
    )
    
    # モデルを管理画面に登録
    admin.add_view(AdminModelView(User, db.session, name='ユーザー'))
    admin.add_view(AdminModelView(School, db.session, name='学校'))
    admin.add_view(AdminModelView(SchoolYear, db.session, name='学校年度'))
    admin.add_view(AdminModelView(ClassGroup, db.session, name='クラスグループ'))
    admin.add_view(AdminModelView(StudentEnrollment, db.session, name='生徒登録'))
    admin.add_view(AdminModelView(Class, db.session, name='クラス'))
    admin.add_view(AdminModelView(ClassEnrollment, db.session, name='クラス履修'))
    admin.add_view(AdminModelView(MainTheme, db.session, name='メインテーマ'))
    admin.add_view(AdminModelView(InquiryTheme, db.session, name='探究テーマ'))
    admin.add_view(AdminModelView(InterestSurvey, db.session, name='興味関心調査'))
    admin.add_view(AdminModelView(PersonalitySurvey, db.session, name='性格調査'))
    admin.add_view(AdminModelView(ActivityLog, db.session, name='活動記録'))
    admin.add_view(AdminModelView(Todo, db.session, name='To Do'))
    admin.add_view(AdminModelView(Goal, db.session, name='目標'))
    admin.add_view(AdminModelView(StudentEvaluation, db.session, name='生徒評価'))
    admin.add_view(AdminModelView(Curriculum, db.session, name='カリキュラム'))
    admin.add_view(AdminModelView(RubricTemplate, db.session, name='ルーブリック'))
    admin.add_view(AdminModelView(Group, db.session, name='グループ'))
    admin.add_view(AdminModelView(GroupMembership, db.session, name='グループメンバー'))
    admin.add_view(AdminModelView(ChatHistory, db.session, name='チャット履歴'))
    admin.add_view(AdminModelView(Milestone, db.session, name='マイルストーン'))


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
        from app.models import (
            User, School, SchoolYear, ClassGroup, StudentEnrollment,
            Class, ClassEnrollment, MainTheme, InquiryTheme, InterestSurvey,
            PersonalitySurvey, ActivityLog, Todo, Goal, StudentEvaluation,
            Curriculum, RubricTemplate, Group, GroupMembership, ChatHistory,
            Milestone, db
        )
        return {
            'db': db,
            'User': User,
            'School': School,
            'SchoolYear': SchoolYear,
            'ClassGroup': ClassGroup,
            'StudentEnrollment': StudentEnrollment,
            'Class': Class,
            'ClassEnrollment': ClassEnrollment,
            'MainTheme': MainTheme,
            'InquiryTheme': InquiryTheme,
            'InterestSurvey': InterestSurvey,
            'PersonalitySurvey': PersonalitySurvey,
            'ActivityLog': ActivityLog,
            'Todo': Todo,
            'Goal': Goal,
            'StudentEvaluation': StudentEvaluation,
            'Curriculum': Curriculum,
            'RubricTemplate': RubricTemplate,
            'Group': Group,
            'GroupMembership': GroupMembership,
            'ChatHistory': ChatHistory,
            'Milestone': Milestone
        }