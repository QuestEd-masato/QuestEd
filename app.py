import os
import re
import json
from flask import Response
import io
import csv
import random
import string
import jinja2 #追加分
import markupsafe #追加分
from datetime import datetime
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from openai import OpenAI
import pymysql
pymysql.install_as_MySQLdb()
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

# 環境変数のロード
load_dotenv()

# OpenAIクライアントの初期化
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# アプリケーション初期化
app = Flask(__name__)
csrf = CSRFProtect(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 最大16MB

# アップロードフォルダの作成
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# CSRF保護の初期化
csrf = CSRFProtect(app)

# データベース初期化
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ログイン管理の初期化
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'この機能を使用するにはログインしてください'

# 管理画面の初期化
admin = Admin(app, name='QuestEd Admin', template_mode='bootstrap4')

@app.template_filter('nl2br')
def nl2br(value):
    if value:
        value = markupsafe.escape(value)
        value = value.replace('\n', markupsafe.Markup('<br>'))
    return markupsafe.Markup(value)

@app.template_filter('fromjson')
def fromjson_filter(value):
    """JSON文字列をPythonオブジェクトに変換"""
    import json
    if not value:
        return []
    try:
        # 文字列が単一引用符を使用している場合、二重引用符に置換
        if isinstance(value, str) and "'" in value and '"' not in value:
            value = value.replace("'", '"')
        return json.loads(value)
    except json.JSONDecodeError:
        print(f"JSONパースエラー: {value}")
        return []

# 管理者専用のModelViewクラスを作成
class AdminModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'teacher'
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login'))

# モデル定義
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    role = db.Column(db.String(10), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
    classes_teaching = db.relationship('Class', backref='teacher', lazy=True)
    interest_surveys = db.relationship('InterestSurvey', backref='student', lazy=True)
    personality_surveys = db.relationship('PersonalitySurvey', backref='student', lazy=True)
    inquiry_themes = db.relationship('InquiryTheme', backref='student', lazy=True)
    activity_logs = db.relationship('ActivityLog', backref='student', lazy=True)
    todos = db.relationship('Todo', backref='student', lazy=True)
    goals = db.relationship('Goal', backref='student', lazy=True)
  
    def has_completed_surveys(self):
        """学生がすべてのアンケートを完了しているかチェック"""
        if self.role != 'student':
            return False
        interest_completed = InterestSurvey.query.filter_by(student_id=self.id).first() is not None
        personality_completed = PersonalitySurvey.query.filter_by(student_id=self.id).first() is not None
        return interest_completed and personality_completed

    def has_selected_theme(self):
        """学生が探究テーマを選択しているかチェック"""
        if self.role != 'student':
            return False
        return InquiryTheme.query.filter_by(student_id=self.id, is_selected=True).first() is not None

# BaseBuilderモデルのインポート
from basebuilder.models import (
    ProblemCategory, BasicKnowledgeItem, KnowledgeThemeRelation,
    AnswerRecord, ProficiencyRecord, LearningPath, PathAssignment
)

# 学校管理のモデル定義
class School(db.Model):
    __tablename__ = 'schools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)  # 学校コード
    address = db.Column(db.Text)
    contact_email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # 修正後:
    problem_categories = db.relationship('ProblemCategory', back_populates='school_ref', lazy=True)
    years = db.relationship('SchoolYear', backref='school', lazy=True)
    users = db.relationship('User', backref='school', lazy=True)
    classes = db.relationship('Class', backref='school', lazy=True)
    text_sets = db.relationship('TextSet', back_populates='school_ref', lazy=True)
    learning_paths = db.relationship('LearningPath', back_populates='school_ref', lazy=True)
    basic_knowledge_items = db.relationship('BasicKnowledgeItem', back_populates='school_ref', lazy=True)

class SchoolYear(db.Model):
    __tablename__ = 'school_years'
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    year = db.Column(db.String(20), nullable=False)  # 例: '2023-2024'
    is_current = db.Column(db.Boolean, default=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    
    # ユニーク制約 (同じ学校で同じ年度は一つだけ)
    __table_args__ = (db.UniqueConstraint('school_id', 'year'),)
    
    # リレーションシップ
    class_groups = db.relationship('ClassGroup', backref='school_year', lazy=True)

class ClassGroup(db.Model):
    __tablename__ = 'class_groups'
    id = db.Column(db.Integer, primary_key=True)
    school_year_id = db.Column(db.Integer, db.ForeignKey('school_years.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # 例: '1年A組'
    description = db.Column(db.Text)
    grade = db.Column(db.String(20))  # 例: '1年', '2年'など
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # リレーションシップ
    enrollments = db.relationship('StudentEnrollment', backref='class_group', lazy=True)
    teacher = db.relationship('User', backref='class_groups_teaching', lazy=True)

class StudentEnrollment(db.Model):
    __tablename__ = 'student_enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    class_group_id = db.Column(db.Integer, db.ForeignKey('class_groups.id'), nullable=False)
    school_year_id = db.Column(db.Integer, db.ForeignKey('school_years.id'), nullable=False)
    student_number = db.Column(db.Integer)  # 出席番号
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # ユニーク制約 (同じ生徒は同じ年度・クラスに一度だけ登録可能)
    __table_args__ = (db.UniqueConstraint('student_id', 'class_group_id', 'school_year_id'),)
    
    # リレーションシップ
    student = db.relationship('User', backref='student_enrollments', lazy=True)
    school_year = db.relationship('SchoolYear', backref='student_enrollments', lazy=True)

# 他のモデルの定義（必要に応じてフィールドを拡張してください）
# Class モデルの定義を拡張
class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)  # 追加
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    schedule = db.Column(db.String(200))
    location = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # クラスと学生の関連付け（多対多の関係）
    students = db.relationship('User', 
                             secondary='class_enrollments',
                             backref=db.backref('enrolled_classes', lazy='dynamic'),
                             lazy='dynamic')

# クラスと学生の中間テーブル（多対多の関連付け）
class ClassEnrollment(db.Model):
    __tablename__ = 'class_enrollments'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # ユニーク制約（同じ学生が同じクラスに複数回登録されないように）
    __table_args__ = (db.UniqueConstraint('class_id', 'student_id'),)

class MainTheme(db.Model):
    __tablename__ = 'main_themes'
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーションシップ
    teacher = db.relationship('User', backref=db.backref('main_themes', lazy=True))
    class_obj = db.relationship('Class', backref=db.backref('main_themes', lazy=True))
    
    # このメインテーマに関連する個人テーマ
    personal_themes = db.relationship('InquiryTheme', backref='main_theme', lazy=True)

class InquiryTheme(db.Model):
    __tablename__ = 'inquiry_themes'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    main_theme_id = db.Column(db.Integer, db.ForeignKey('main_themes.id'), nullable=True)  # 追加
    is_ai_generated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    title = db.Column(db.String(200))
    question = db.Column(db.Text)
    description = db.Column(db.Text)
    rationale = db.Column(db.Text)
    approach = db.Column(db.Text)
    potential = db.Column(db.Text)
    is_selected = db.Column(db.Boolean, default=False)

class InterestSurvey(db.Model):
    __tablename__ = 'interest_surveys'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    responses = db.Column(db.Text)
    # submitted_at フィールドを追加
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

class PersonalitySurvey(db.Model):
    __tablename__ = 'personality_surveys'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    responses = db.Column(db.Text)
    # submitted_at フィールドを追加
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200))
    date = db.Column(db.Date, default=datetime.utcnow().date())
    content = db.Column(db.Text)
    reflection = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    activity = db.Column(db.Text)  # 既存のフィールドを残す
    tags = db.Column(db.String(255))  # 新しいタグフィールドを追加

class Todo(db.Model):
    __tablename__ = 'todos'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    priority = db.Column(db.String(20))  # 'high', 'medium', 'low'
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # ユーザーとの関連付け
    #student = db.relationship('User', backref=db.backref('todos', lazy=True))
class Goal(db.Model):
    __tablename__ = 'goals'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    goal_type = db.Column(db.String(20))  # 'long', 'medium', 'short'
    due_date = db.Column(db.Date)
    progress = db.Column(db.Integer, default=0)  # 0-100
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class StudentEvaluation(db.Model):
    __tablename__ = 'student_evaluations'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    evaluation_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーションシップ
    student = db.relationship('User', backref=db.backref('evaluations', lazy=True))
    class_obj = db.relationship('Class', backref=db.backref('evaluations', lazy=True))

class Curriculum(db.Model):
    __tablename__ = 'curriculums'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    total_hours = db.Column(db.Integer, default=35)
    has_fieldwork = db.Column(db.Boolean, default=False)
    fieldwork_count = db.Column(db.Integer, default=0)
    has_presentation = db.Column(db.Boolean, default=True)
    presentation_format = db.Column(db.String(50), default='プレゼンテーション')
    group_work_level = db.Column(db.String(50), default='ハイブリッド')
    external_collaboration = db.Column(db.Boolean, default=False)
    content = db.Column(db.Text)  # JSONとして保存されたカリキュラム内容
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーションシップ
    class_obj = db.relationship('Class', backref=db.backref('curriculums', lazy=True))
    teacher = db.relationship('User', backref=db.backref('created_curriculums', lazy=True))

class RubricTemplate(db.Model):
    __tablename__ = 'rubric_templates'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text)  # JSONとして保存されたルーブリック
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーションシップ
    class_obj = db.relationship('Class', backref=db.backref('rubric_templates', lazy=True))
    teacher = db.relationship('User', backref=db.backref('created_rubrics', lazy=True))

class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # リレーションシップ
    class_obj = db.relationship('Class', backref=db.backref('groups', lazy=True))
    creator = db.relationship('User', backref=db.backref('created_groups', lazy=True))
    members = db.relationship('User', secondary='group_memberships',
                             backref=db.backref('joined_groups', lazy='dynamic'))

class GroupMembership(db.Model):
    __tablename__ = 'group_memberships'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ユニーク制約
    __table_args__ = (db.UniqueConstraint('group_id', 'student_id'),)

class ChatHistory(db.Model):
    __tablename__ = 'chat_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_user = db.Column(db.Boolean, default=True)  # True=ユーザー, False=AI
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # userリレーションシップは1つだけにする
    user = db.relationship('User', backref=db.backref('chat_histories', lazy=True))

class Milestone(db.Model):
    __tablename__ = 'milestones'
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # クラスとの関連付け
    class_obj = db.relationship('Class', backref=db.backref('milestones', lazy=True))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# モデルを管理画面に登録
admin.add_view(AdminModelView(User, db.session))
admin.add_view(AdminModelView(Class, db.session))
admin.add_view(AdminModelView(InterestSurvey, db.session))
admin.add_view(AdminModelView(PersonalitySurvey, db.session))
admin.add_view(AdminModelView(InquiryTheme, db.session))
admin.add_view(AdminModelView(ActivityLog, db.session))
admin.add_view(AdminModelView(Milestone, db.session))
admin.add_view(AdminModelView(Todo, db.session))
admin.add_view(AdminModelView(Goal, db.session))
admin.add_view(AdminModelView(MainTheme, db.session))
admin.add_view(AdminModelView(ChatHistory, db.session))
admin.add_view(AdminModelView(Group, db.session))
admin.add_view(AdminModelView(GroupMembership, db.session))
admin.add_view(AdminModelView(Curriculum, db.session))
admin.add_view(AdminModelView(RubricTemplate, db.session))
admin.add_view(AdminModelView(StudentEvaluation, db.session))
# 学校管理モデルを管理画面に追加
admin.add_view(AdminModelView(School, db.session))
admin.add_view(AdminModelView(SchoolYear, db.session))
admin.add_view(AdminModelView(ClassGroup, db.session))
admin.add_view(AdminModelView(StudentEnrollment, db.session))

# その後、BaseBuilderモジュールを初期化
from basebuilder import init_app as init_basebuilder
init_basebuilder(app)

# ルート定義例
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            # 管理者は管理画面へリダイレクト
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('view_themes'))
    return redirect(url_for('login'))

# app.py に追加または既存のルートを修正
@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('この機能は管理者のみ利用可能です。')
        return redirect(url_for('index'))
    
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':  # または専用の admin ロールを作成
        flash('この機能は管理者のみ利用可能です。')
        return redirect(url_for('index'))
    
    # ダッシュボード情報を取得
    user_count = User.query.count()
    class_count = Class.query.count()
    
    return render_template('admin/dashboard.html', 
                          user_count=user_count, 
                          class_count=class_count)

# 学校詳細表示
@app.route('/admin/school/<int:school_id>')
@login_required
def admin_school_detail(school_id):
    if current_user.role != 'admin':
        flash('この機能は管理者のみ利用可能です。')
        return redirect(url_for('index'))
    
    school = School.query.get_or_404(school_id)
    school_years = SchoolYear.query.filter_by(school_id=school_id).all()
    
    return render_template('admin/school_detail.html', 
                           school=school, 
                           school_years=school_years)

# 学校作成
@app.route('/admin/school/create', methods=['GET', 'POST'])
@login_required
def admin_create_school():
    if current_user.role != 'admin':
        flash('この機能は管理者のみ利用可能です。')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        address = request.form.get('address', '')
        contact_email = request.form.get('contact_email', '')
        
        if not name or not code:
            flash('学校名と学校コードは必須です。')
            return render_template('admin/create_school.html')
        
        # コードが既に使われていないか確認
        existing_school = School.query.filter_by(code=code).first()
        if existing_school:
            flash('この学校コードは既に使われています。')
            return render_template('admin/create_school.html')
        
        # 学校を作成
        new_school = School(
            name=name,
            code=code,
            address=address,
            contact_email=contact_email
        )
        
        db.session.add(new_school)
        db.session.commit()
        
        flash('学校が作成されました。')
        return redirect(url_for('admin_schools'))
    
    return render_template('admin/create_school.html')

# 学校年度作成
@app.route('/admin/school/<int:school_id>/year/create', methods=['GET', 'POST'])
@login_required
def admin_create_school_year(school_id):
    if current_user.role != 'admin':
        flash('この機能は管理者のみ利用可能です。')
        return redirect(url_for('index'))
    
    school = School.query.get_or_404(school_id)
    
    if request.method == 'POST':
        year = request.form.get('year')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        is_current = 'is_current' in request.form
        
        if not year:
            flash('年度は必須です。')
            return render_template('admin/create_school_year.html', school=school)
        
        # 年度が既に存在するか確認
        existing_year = SchoolYear.query.filter_by(school_id=school_id, year=year).first()
        if existing_year:
            flash('この学校の年度は既に存在します。')
            return render_template('admin/create_school_year.html', school=school)
        
        # 日付文字列をdateオブジェクトに変換
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        
        # 現在のフラグを設定する場合、他の年度のフラグをリセット
        if is_current:
            SchoolYear.query.filter_by(school_id=school_id, is_current=True).update({'is_current': False})
        
        # 年度を作成
        new_year = SchoolYear(
            school_id=school_id,
            year=year,
            start_date=start_date,
            end_date=end_date,
            is_current=is_current
        )
        
        db.session.add(new_year)
        db.session.commit()
        
        flash('学校年度が作成されました。')
        return redirect(url_for('admin_school_detail', school_id=school_id))
    
    return render_template('admin/create_school_year.html', school=school)

# クラスグループ作成
@app.route('/admin/school_year/<int:school_year_id>/class_group/create', methods=['GET', 'POST'])
@login_required
def admin_create_class_group(school_year_id):
    if current_user.role != 'admin':
        flash('この機能は管理者のみ利用可能です。')
        return redirect(url_for('index'))
    
    school_year = SchoolYear.query.get_or_404(school_year_id)
    
    # 教師一覧を取得
    teachers = User.query.filter_by(role='teacher').all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        teacher_id = request.form.get('teacher_id', type=int)
        description = request.form.get('description', '')
        grade = request.form.get('grade', '')
        
        if not name or not teacher_id:
            flash('クラス名と担任教師は必須です。')
            return render_template('admin/create_class_group.html', 
                                  school_year=school_year,
                                  teachers=teachers)
        
        # クラスグループを作成
        new_class_group = ClassGroup(
            school_year_id=school_year_id,
            teacher_id=teacher_id,
            name=name,
            description=description,
            grade=grade
        )
        
        db.session.add(new_class_group)
        db.session.commit()
        
        flash('クラスグループが作成されました。')
        return redirect(url_for('admin_school_detail', school_id=school_year.school_id))
    
    return render_template('admin/create_class_group.html', 
                          school_year=school_year,
                          teachers=teachers)

# クラスグループ詳細
@app.route('/admin/class_group/<int:class_group_id>')
@login_required
def admin_class_group_detail(class_group_id):
    if current_user.role != 'admin':
        flash('この機能は管理者のみ利用可能です。')
        return redirect(url_for('index'))
    
    class_group = ClassGroup.query.get_or_404(class_group_id)
    
    # クラスに所属する学生を取得
    enrollments = StudentEnrollment.query.filter_by(class_group_id=class_group_id).all()
    students = []
    for enrollment in enrollments:
        student = User.query.get(enrollment.student_id)
        students.append({
            'id': student.id,
            'username': student.username,
            'student_number': enrollment.student_number,
            'enrollment_id': enrollment.id
        })
    
    # 学生を出席番号順に並べ替え
    students.sort(key=lambda x: x['student_number'] or 9999)
    
    return render_template('admin/class_group_detail.html', 
                          class_group=class_group,
                          students=students)

# クラスグループに学生を追加
@app.route('/admin/class_group/<int:class_group_id>/add_students', methods=['GET', 'POST'])
@login_required
def admin_class_group_add_students(class_group_id):
    if current_user.role != 'admin':
        flash('この機能は管理者のみ利用可能です。')
        return redirect(url_for('index'))
    
    class_group = ClassGroup.query.get_or_404(class_group_id)
    
    # クラスに既に所属している学生のIDを取得
    enrolled_student_ids = db.session.query(StudentEnrollment.student_id).filter_by(
        class_group_id=class_group_id
    ).all()
    enrolled_student_ids = [id[0] for id in enrolled_student_ids]
    
    # 追加可能な学生（まだクラスに所属していない学生）を取得
    available_students = User.query.filter(
        User.role == 'student',
        ~User.id.in_(enrolled_student_ids) if enrolled_student_ids else True
    ).all()
    
    if request.method == 'POST':
        student_ids = request.form.getlist('student_ids')
        
        if not student_ids:
            flash('学生が選択されていません。')
            return render_template('admin/class_group_add_students.html', 
                                  class_group=class_group,
                                  available_students=available_students)
        
        # 選択された学生をクラスに追加
        for student_id in student_ids:
            # 学生番号を取得
            student_number = request.form.get(f'student_number_{student_id}', type=int)
            
            # 登録レコードを作成
            enrollment = StudentEnrollment(
                student_id=int(student_id),
                class_group_id=class_group_id,
                school_year_id=class_group.school_year_id,
                student_number=student_number
            )
            db.session.add(enrollment)
        
        db.session.commit()
        flash(f'{len(student_ids)}人の学生をクラスに追加しました。')
        return redirect(url_for('admin_class_group_detail', class_group_id=class_group_id))
    
    return render_template('admin/class_group_add_students.html', 
                          class_group=class_group,
                          available_students=available_students)

# クラスグループから学生を削除
@app.route('/admin/enrollment/<int:enrollment_id>/delete', methods=['POST'])
@login_required
def admin_delete_enrollment(enrollment_id):
    if current_user.role != 'admin':
        flash('この機能は管理者のみ利用可能です。')
        return redirect(url_for('index'))
    
    # 在籍レコードを取得
    enrollment = StudentEnrollment.query.get_or_404(enrollment_id)
    class_group_id = enrollment.class_group_id
    
    # 在籍レコードを削除
    db.session.delete(enrollment)
    db.session.commit()
    
    flash('学生がクラスから削除されました。')
    return redirect(url_for('admin_class_group_detail', class_group_id=class_group_id))

# app.py に以下を追加
@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Class': Class, 'InterestSurvey': InterestSurvey}
# 他のモデル用に同様のルートを追加

@app.route('/login', methods=['GET', 'POST'])
def login():
    # ログイン処理の実装
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            
            # ユーザーのロールに応じて適切なダッシュボードにリダイレクト
            if user.role == 'student':
                return redirect(url_for('student_dashboard'))
            elif user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                # その他のロール（管理者など）の場合
                return redirect(url_for('index'))
        else:
            flash('ユーザー名またはパスワードが正しくありません。')
    return render_template('login.html')

@app.route('/teacher_dashboard')
@login_required
def teacher_dashboard():
    # 教師ロールのみアクセス可能にする
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('view_themes'))
    
    # 教師が担当しているクラスを取得
    classes_raw = Class.query.filter_by(teacher_id=current_user.id).all()
    
    # 現在の日付を取得
    today = datetime.now().date()
    
    # 各クラスに必要なデータを追加
    classes = []
    for class_obj in classes_raw:
        # クラスに所属する学生数を取得
        student_count = class_obj.students.count()
        
        # アンケート完了した学生数を取得
        survey_completed = 0
        for student in class_obj.students:
            if student.has_completed_surveys():
                survey_completed += 1
        
        # テーマを選択した学生数を取得
        theme_selected = InquiryTheme.query.join(
            User, User.id == InquiryTheme.student_id
        ).filter(
            InquiryTheme.is_selected == True,
            User.id.in_([s.id for s in class_obj.students])
        ).count()
        
        # クラスの次回のマイルストーンを取得
        next_milestone = Milestone.query.filter(
            Milestone.class_id == class_obj.id,
            Milestone.due_date >= today
        ).order_by(Milestone.due_date).first()
        
        class_data = {
            'name': class_obj.name,
            'id': class_obj.id,
            'student_count': student_count,
            'survey_completed': survey_completed,
            'theme_selected': theme_selected,
            'next_milestone': next_milestone
        }
        classes.append(class_data)
    # BaseBuilderデータの追加
    problem_count = 0
    category_count = 0
    
    try:
        from models_basebuilder import BasicKnowledgeItem, ProblemCategory
        
        # 教師が作成した問題とカテゴリの数を取得
        problem_count = BasicKnowledgeItem.query.filter_by(created_by=current_user.id).count()
        category_count = ProblemCategory.query.filter_by(created_by=current_user.id).count()
    except:
        # BaseBuilderモジュールがロードできない場合は何もしない
        pass
    
    return render_template('teacher_dashboard.html', 
                          classes=classes,
                          # BaseBuilder関連データを追加
                          problem_count=problem_count,
                          category_count=category_count)
   
@app.route('/class/<int:class_id>/generate_evaluations', methods=['GET', 'POST'])
@login_required
def generate_evaluations(class_id):
    # 教師のみアクセス可能
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    # クラスを取得
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスの評価を生成する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    # クラスに所属する学生を取得
    students = class_obj.students.all()
    
    # カリキュラムとルーブリックの取得
    curriculums = Curriculum.query.filter_by(class_id=class_id).all()
    selected_curriculum_id = request.args.get('curriculum_id', type=int)
    
    # 選択されたカリキュラムがある場合、そのルーブリック情報を取得
    curriculum_data = None
    rubric_data = None
    if selected_curriculum_id:
        selected_curriculum = Curriculum.query.get(selected_curriculum_id)
        if selected_curriculum:
            curriculum_data = json.loads(selected_curriculum.content)
            # ルーブリック情報を取得
            if 'rubric_suggestion' in curriculum_data:
                rubric_data = curriculum_data['rubric_suggestion']
    
    # 評価結果の初期化
    evaluations = []
    
    if request.method == 'POST':
        # フォームから選択された学生のIDを取得
        student_ids = request.form.getlist('student_ids')
    
        # 選択した学生のリストを取得
        selected_students = User.query.filter(User.id.in_(student_ids)).all()
    
        # 評価結果のリストを初期化
        evaluations = []
    
        for student in selected_students:
            # 学生の探究テーマを取得
            theme = InquiryTheme.query.filter_by(student_id=student.id, is_selected=True).first()
        
            # 学生の目標を取得
            goals = Goal.query.filter_by(student_id=student.id).all()
        
            # 学生の学習記録を最新の5件取得
            activity_logs = ActivityLog.query.filter_by(student_id=student.id).order_by(ActivityLog.date.desc()).limit(5).all()
        
            # AIを使用して評価を生成
            evaluation_text = generate_student_evaluation(student, theme, goals, activity_logs, curriculum_data, rubric_data)
        
            # 既存の評価を確認
            existing_evaluation = StudentEvaluation.query.filter_by(
                student_id=student.id, 
                class_id=class_id
            ).first()
        
            if existing_evaluation:
                # 既存の評価を更新
                existing_evaluation.evaluation_text = evaluation_text
                existing_evaluation.updated_at = datetime.utcnow()
            else:
                # 新しい評価を作成
                new_evaluation = StudentEvaluation(
                    student_id=student.id,
                    class_id=class_id,
                    evaluation_text=evaluation_text
                )
                db.session.add(new_evaluation)
        
             # 結果をリストに追加
            evaluations.append({
                 'student_id': student.id,
                 'student_name': student.username,
                 'evaluation': evaluation_text
            })
    
        # 変更をコミット
        db.session.commit()
    
        # 評価結果をセッションに保存
        session['stored_evaluations'] = evaluations

    
    # CSV出力の要求があれば処理
    if request.args.get('format') == 'csv':
        # 新しい評価結果がある場合はそれを使用
        if evaluations:
            return export_evaluations_csv(evaluations, class_obj.name)
        # セッションに保存されている評価結果がある場合はそれを使用
        elif session.get('stored_evaluations'):
            return export_evaluations_csv(session.get('stored_evaluations'), class_obj.name)
        # どちらもない場合はデータベースから取得
        else:
            return export_evaluations_csv([], class_obj.name, class_id)

    return render_template(
        'evaluate_students.html',
        class_obj=class_obj,
        students=students,
        curriculums=curriculums,
        selected_curriculum_id=selected_curriculum_id,
        evaluations=evaluations
    )

def generate_student_evaluation(student, theme, goals, activity_logs, curriculum_data, rubric_data):
    """
    OpenAI APIを使用して学生の評価を生成する
    
    Args:
        student: 学生のUserオブジェクト
        theme: 選択中の探究テーマ
        goals: 設定された目標のリスト
        activity_logs: 学習記録のリスト
        curriculum_data: カリキュラムデータ
        rubric_data: ルーブリックデータ
        
    Returns:
        生成された評価文字列
    """
    # プロンプトの作成
    prompt = f"以下の情報に基づいて、学生 {student.username} の探究学習の評価を100〜150文字で生成してください。\n\n"
    
    # テーマ情報の追加
    if theme:
        prompt += f"【探究テーマ】\n"
        prompt += f"タイトル: {theme.title}\n"
        prompt += f"探究の問い: {theme.question}\n"
        if theme.description:
            prompt += f"説明: {theme.description}\n"
    else:
        prompt += "【探究テーマ】\n探究テーマは未選択です。\n"
    
    # 目標情報の追加
    prompt += "\n【設定された目標】\n"
    if goals:
        for goal in goals:
            prompt += f"- {goal.title}: 進捗 {goal.progress}%"
            if goal.is_completed:
                prompt += " (完了)"
            prompt += "\n"
    else:
        prompt += "設定された目標はありません。\n"
    
    # 学習記録の追加
    prompt += "\n【最近の学習記録】\n"
    if activity_logs:
        for log in activity_logs:
            prompt += f"- {log.date.strftime('%Y-%m-%d')} {log.title if log.title else '（タイトルなし）'}\n"
            prompt += f"  {log.content[:100]}{'...' if len(log.content) > 100 else ''}\n"
    else:
        prompt += "学習記録はありません。\n"
    
    # ルーブリック情報の追加
    if rubric_data:
        prompt += "\n【評価ルーブリック】\n"
        for rubric in rubric_data:
            prompt += f"- {rubric['category']}: {rubric['description']}\n"
            for level in rubric['levels']:
                prompt += f"  - {level['level']}: {level['description']}\n"
    
    # 指示の追加
    prompt += "\n以下の点を考慮した評価を生成してください：\n"
    prompt += "1. 探究テーマへの取り組み方や深さ\n"
    prompt += "2. 目標達成に向けての進捗\n"
    prompt += "3. 学習記録の内容と質\n"
    prompt += "4. ルーブリックの基準に照らした評価\n"
    prompt += "5. 今後の改善点や期待\n\n"
    prompt += "評価は100〜150字程度に収め、客観的かつ建設的な内容にしてください。"
    
    try:
        # OpenAI APIの呼び出し
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは教師として、探究学習における生徒の評価を行います。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        # 生成された評価を取得
        evaluation = response.choices[0].message.content.strip()
        return evaluation
        
    except Exception as e:
        print(f"評価生成エラー: {str(e)}")
        return "評価の生成中にエラーが発生しました。"

def export_evaluations_csv(evaluations, class_name, class_id=None):
    """
    評価をCSVファイルとしてエクスポートする
    
    Args:
        evaluations: 評価データのリスト
        class_name: クラス名
        class_id: クラスID（evaluationsが空の場合に使用）
        
    Returns:
        CSVファイルのレスポンス
    """
    try:
        # 評価データが空で、クラスIDがある場合はデータベースから取得
        if not evaluations and class_id:
            # データベースから評価を取得
            db_evaluations = StudentEvaluation.query.filter_by(class_id=class_id).all()
            
            # 評価データをリスト形式に変換
            evaluations = []
            for eval_obj in db_evaluations:
                student = User.query.get(eval_obj.student_id)
                evaluations.append({
                    'student_id': student.id,
                    'student_name': student.username,
                    'evaluation': eval_obj.evaluation_text
                })
        
        # それでも評価データがない場合はエラーメッセージを表示
        if not evaluations:
            flash('エクスポートするデータがありません。まず評価を生成してください。')
            if class_id:
                return redirect(url_for('generate_evaluations', class_id=class_id))
            return redirect(url_for('teacher_dashboard'))
        
        # CSVフォーマットでエクスポート
        csv_content = io.StringIO()
        csv_writer = csv.writer(csv_content)
        
        # ヘッダー行
        csv_writer.writerow(['学生名', '評価'])
        
        # データ行
        for evaluation in evaluations:
            csv_writer.writerow([
                evaluation['student_name'],
                evaluation['evaluation']
            ])
        
        # BOMを追加して文字化けを防止
        response_data = '\ufeff' + csv_content.getvalue()
        
        # ファイル名の作成（現在日時を含む）
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"{class_name}_評価_{timestamp}.csv"
        
        # レスポンスを作成
        response = Response(
            response_data,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )
        return response
    except Exception as e:
        print(f"CSVエクスポートエラー: {str(e)}")
        flash(f'CSVエクスポート中にエラーが発生しました: {str(e)}')
        if class_id:
            return redirect(url_for('generate_evaluations', class_id=class_id))
        return redirect(url_for('teacher_dashboard'))


@app.route('/create_milestone/<int:class_id>', methods=['GET', 'POST'])
@login_required
def create_milestone(class_id):
    # 教師のみアクセス可能
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    # クラスオブジェクトを取得
    class_ = Class.query.get_or_404(class_id)
    
    # 教師がクラスの所有者でない場合はアクセス制限
    if class_.teacher_id != current_user.id:
        flash('このクラスのマイルストーンを作成する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        due_date_str = request.form.get('due_date')
        
        if not title or not due_date_str:
            flash('タイトルと期限日は必須項目です。')
            return render_template('create_milestone.html', class_=class_, now=datetime.now())
        
        # 日付文字列をdateオブジェクトに変換
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        
        # 新しいマイルストーンを作成
        new_milestone = Milestone(
            class_id=class_id,
            title=title,
            description=description,
            due_date=due_date
        )
        
        db.session.add(new_milestone)
        db.session.commit()
        
        flash('マイルストーンが作成されました。')
        return redirect(url_for('view_details', class_id=class_id))
    
    return render_template('create_milestone.html', class_=class_, now=datetime.now())

@app.route('/edit_milestone/<int:milestone_id>', methods=['GET', 'POST'])
@login_required
def edit_milestone(milestone_id):
    # 教師のみアクセス可能
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    # マイルストーンを取得
    milestone = Milestone.query.get_or_404(milestone_id)
    
    # クラスを取得
    class_ = Class.query.get_or_404(milestone.class_id)
    
    # 教師がクラスの所有者でない場合はアクセス制限
    if class_.teacher_id != current_user.id:
        flash('このマイルストーンを編集する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        due_date_str = request.form.get('due_date')
        
        if not title or not due_date_str:
            flash('タイトルと期限日は必須項目です。')
            return render_template('edit_milestone.html', milestone=milestone, class_=class_, now=datetime.now())
        
        # 日付文字列をdateオブジェクトに変換
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        
        # マイルストーンを更新
        milestone.title = title
        milestone.description = description
        milestone.due_date = due_date
        
        db.session.commit()
        
        flash('マイルストーンが更新されました。')
        return redirect(url_for('view_class', class_id=class_.id))
    
    return render_template('edit_milestone.html', milestone=milestone, class_=class_, now=datetime.now())

@app.route('/delete_milestone/<int:milestone_id>')
@login_required
def delete_milestone(milestone_id):
    # 教師のみアクセス可能
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    # マイルストーンを取得
    milestone = Milestone.query.get_or_404(milestone_id)
    
    # クラスを取得
    class_ = Class.query.get_or_404(milestone.class_id)
    
    # 教師がクラスの所有者でない場合はアクセス制限
    if class_.teacher_id != current_user.id:
        flash('このマイルストーンを削除する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    # マイルストーンを削除
    db.session.delete(milestone)
    db.session.commit()
    
    flash('マイルストーンが削除されました。')
    return redirect(url_for('view_class', class_id=class_.id))

# クラス詳細画面で使用するview_classルートの追加（存在しなければ）
@app.route('/view_class/<int:class_id>')
@login_required
def view_class(class_id):
    # クラスオブジェクトを取得
    class_obj = Class.query.get_or_404(class_id)
    
    # 教師がクラスの所有者でない場合はアクセス制限（教師ユーザーの場合のみ）
    if current_user.role == 'teacher' and class_obj.teacher_id != current_user.id:
        flash('このクラスの詳細を閲覧する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    # クラスに関連するマイルストーンを取得
    milestones = Milestone.query.filter_by(class_id=class_id).order_by(Milestone.due_date).all()
    
    # 学生リストを取得（クラスに所属する全学生）
    students = class_obj.students.all()
    
    # 各学生の追加情報を集める
    students_info = []
    for student in students:
        # 学生の選択中テーマを取得
        selected_theme = InquiryTheme.query.filter_by(
            student_id=student.id, 
            is_selected=True
        ).first()
        
        # 学生の最新の活動記録を取得
        latest_activity = ActivityLog.query.filter_by(
            student_id=student.id
        ).order_by(ActivityLog.date.desc()).first()
        
        # 学生情報を辞書にまとめる
        student_info = {
            'student': student,
            'selected_theme': selected_theme,
            'latest_activity': latest_activity
        }
        students_info.append(student_info)
    
    # 教師かどうかを判定
    is_teacher = (current_user.role == 'teacher' and class_obj.teacher_id == current_user.id)
    
    # 現在の日付を取得
    now = datetime.now()
    
    # テンプレートをレンダリング
    return render_template('view_class.html', 
                          class_=class_obj, 
                          milestones=milestones, 
                          students=students_info,  # 修正: 詳細情報を含む学生リスト
                          is_teacher=is_teacher, 
                          now=now)

@app.route('/student_dashboard')
@login_required
def student_dashboard():
    # 学生ロールのみアクセス可能にする
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # 選択されているテーマの取得
    selected_theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
    
    # 最近の活動ログの取得
    recent_activities = ActivityLog.query.filter_by(student_id=current_user.id).order_by(ActivityLog.timestamp.desc()).limit(5).all()
    
    # None値のチェックと修正
    for activity in recent_activities:
        if activity.content is None:
            activity.content = activity.activity or ""
    
    # アンケート状況の取得
    interest_survey = InterestSurvey.query.filter_by(student_id=current_user.id).first()
    personality_survey = PersonalitySurvey.query.filter_by(student_id=current_user.id).first()
    
    # submitted_atがNoneの場合の対策
    if interest_survey and interest_survey.submitted_at is None:
        interest_survey.submitted_at = datetime.utcnow()
        db.session.commit()
    
    if personality_survey and personality_survey.submitted_at is None:
        personality_survey.submitted_at = datetime.utcnow()
        db.session.commit()
    
    # 学生が所属するクラスを取得
    enrolled_classes = current_user.enrolled_classes.all()
    
    # 今後のマイルストーンを取得
    upcoming_milestones = []
    today = datetime.now().date()
    
    # 各クラスのマイルストーンを確認
    for class_ in enrolled_classes:
        class_milestones = Milestone.query.filter(
            Milestone.class_id == class_.id,
            Milestone.due_date >= today
        ).order_by(Milestone.due_date).all()
        
        # マイルストーンに追加情報をつける
        for milestone in class_milestones:
            upcoming_milestones.append({
                'id': milestone.id,
                'title': milestone.title,
                'description': milestone.description,
                'due_date': milestone.due_date,
                'class_name': class_.name,
                'class_id': class_.id,
                # 期限までの日数を計算
                'days_remaining': (milestone.due_date - today).days
            })
    
    # 期限が近い順に並べ替え
    upcoming_milestones = sorted(upcoming_milestones, key=lambda x: x['due_date'])
    
    # 未完了のTo Doを取得（期限が近い順）
    todos = Todo.query.filter_by(
        student_id=current_user.id,
        is_completed=False
    ).order_by(Todo.due_date.asc()).limit(5).all()
    
    # 今日の日付
    today = datetime.now().date()
    
    return render_template('student_dashboard.html', 
                          selected_theme=selected_theme, 
                          recent_activities=recent_activities,
                          interest_survey=interest_survey,
                          personality_survey=personality_survey,
                          upcoming_milestones=upcoming_milestones,
                          classes=enrolled_classes,
                          todos=todos,
                          today=today)

@app.route('/milestone/<int:milestone_id>')
@login_required
def view_milestone(milestone_id):
    # マイルストーンを取得
    milestone = Milestone.query.get_or_404(milestone_id)
    
    # クラスを取得
    class_ = Class.query.get_or_404(milestone.class_id)
    
    # 学生が所属していないクラスのマイルストーンを見ようとしている場合
    if current_user.role == 'student':
        enrolled_class_ids = [c.id for c in current_user.enrolled_classes]
        if class_.id not in enrolled_class_ids:
            flash('このマイルストーンを閲覧する権限がありません。')
            return redirect(url_for('student_dashboard'))
    
    # 教師でクラスの担当者でない場合
    elif current_user.role == 'teacher' and class_.teacher_id != current_user.id:
        flash('このマイルストーンを閲覧する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    return render_template('view_milestone.html', milestone=milestone, class_=class_)

@app.route('/surveys')
@login_required
def surveys():
    # 学生ロールのみアクセス可能にする
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # アンケートの回答状況を確認
    interest_survey = InterestSurvey.query.filter_by(student_id=current_user.id).first()
    personality_survey = PersonalitySurvey.query.filter_by(student_id=current_user.id).first()
    
    return render_template('surveys.html', 
                          interest_survey=interest_survey,
                          personality_survey=personality_survey)

@app.route('/activities')
@login_required
def activities():
    # 学生ロールのみアクセス可能にする
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # すべての活動ログを取得
    activity_logs = ActivityLog.query.filter_by(student_id=current_user.id).order_by(ActivityLog.timestamp.desc()).all()
    
    # 選択中のテーマを取得
    theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
    
    return render_template('activities.html', activity_logs=activity_logs, theme=theme)

@app.route('/activity/<int:log_id>/delete')
@login_required
def delete_activity(log_id):
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    activity = ActivityLog.query.get_or_404(log_id)
    
    if activity.student_id != current_user.id:
        flash('この学習記録を削除する権限がありません。')
        return redirect(url_for('activities'))
    
    # 画像ファイルが存在する場合は削除
    if activity.image_url:
        try:
            # 画像URLからファイルパスを取得
            image_filename = activity.image_url.split('/')[-1]
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            print(f"画像ファイル削除エラー: {str(e)}")
    
    # 活動記録を削除
    db.session.delete(activity)
    db.session.commit()
    
    flash('学習記録が削除されました。')
    return redirect(url_for('activities'))

@app.route('/activities/export/<format>')
@login_required
def export_activities(format):
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # 選択中のテーマを取得
    theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
    
    if not theme:
        flash('エクスポートするには選択中のテーマが必要です。')
        return redirect(url_for('activities'))
    
    # テーマに関連する学習記録を取得
    activities = ActivityLog.query.filter_by(student_id=current_user.id).order_by(ActivityLog.date.desc()).all()
    
    if not activities:
        flash('エクスポートする学習記録がありません。')
        return redirect(url_for('activities'))
    
    if format == 'csv':
        # CSVフォーマットでエクスポート
        csv_content = io.StringIO()
        csv_writer = csv.writer(csv_content)
        
        # ヘッダー行
        csv_writer.writerow(['日付', 'タイトル', 'タグ', '学習内容', '振り返り'])
        
        # データ行
        for activity in activities:
            csv_writer.writerow([
                activity.date.strftime('%Y-%m-%d'),
                activity.title,
                activity.tags or '',
                activity.content,
                activity.reflection or ''
            ])
        
        # BOMを追加して文字化けを防止
        response_data = '\ufeff' + csv_content.getvalue()
        
        # レスポンスを作成
        response = Response(
            response_data,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=learning_records_{datetime.now().strftime("%Y%m%d")}.csv'
            }
        )
        return response
        
    elif format == 'pdf':
        # PDF出力のためのサードパーティライブラリが必要
        # ここでは簡易的な実装として、テンプレートをレンダリングしてブラウザのPDF機能に任せる
        return render_template(
            'export_activities_pdf.html',
            activities=activities,
            theme=theme,
            current_user=current_user,
            now=datetime.now()
        )
    
    flash('サポートされていないフォーマットです。')
    return redirect(url_for('activities'))

@app.route('/todos')
@login_required
def todos():
    # 学生ロールのみアクセス可能にする
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # ログイン中の学生のTo Doリストを取得
    todos = Todo.query.filter_by(student_id=current_user.id).order_by(Todo.due_date, Todo.priority).all()
    
    # 選択中のテーマを取得（表示用）
    theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
    
    # 今日の日付
    today = datetime.now().date()
    
    return render_template('todos.html', todos=todos, theme=theme, today=today)

@app.route('/new_todo', methods=['GET', 'POST'])
@login_required
def new_todo():
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # 選択中のテーマを取得（表示用）
    theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date', '')
        priority = request.form.get('priority', 'medium')
        
        if not title:
            flash('タイトルは必須項目です。')
            return render_template('new_todo.html', theme=theme)
        
        # 新しいTo Doを作成
        new_todo = Todo(
            student_id=current_user.id,
            title=title,
            description=description,
            due_date=datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None,
            priority=priority
        )
        
        db.session.add(new_todo)
        db.session.commit()
        
        flash('新しいTo Doが追加されました。')
        return redirect(url_for('todos'))
    
    return render_template('new_todo.html', theme=theme)

@app.route('/todo/<int:todo_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_todo(todo_id):
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # To Doを取得
    todo = Todo.query.get_or_404(todo_id)
    
    # 権限チェック
    if todo.student_id != current_user.id:
        flash('このTo Doを編集する権限がありません。')
        return redirect(url_for('todos'))
    
    # 選択中のテーマを取得（表示用）
    theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date', '')
        priority = request.form.get('priority', 'medium')
        is_completed = 'is_completed' in request.form
        
        if not title:
            flash('タイトルは必須項目です。')
            return render_template('edit_todo.html', todo=todo, theme=theme)
        
        # To Doを更新
        todo.title = title
        todo.description = description
        todo.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
        todo.priority = priority
        todo.is_completed = is_completed
        
        db.session.commit()
        
        flash('To Doが更新されました。')
        return redirect(url_for('todos'))
    
    return render_template('edit_todo.html', todo=todo, theme=theme)

@app.route('/todo/<int:todo_id>/delete')
@login_required
def delete_todo(todo_id):
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # To Doを取得
    todo = Todo.query.get_or_404(todo_id)
    
    # 権限チェック
    if todo.student_id != current_user.id:
        flash('このTo Doを削除する権限がありません。')
        return redirect(url_for('todos'))
    
    # To Doを削除
    db.session.delete(todo)
    db.session.commit()
    
    flash('To Doが削除されました。')
    return redirect(url_for('todos'))

@app.route('/todo/<int:todo_id>/toggle')
@login_required
def toggle_todo(todo_id):
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # To Doを取得
    todo = Todo.query.get_or_404(todo_id)
    
    # 権限チェック
    if todo.student_id != current_user.id:
        flash('このTo Doを更新する権限がありません。')
        return redirect(url_for('todos'))
    
    # 完了状態を反転
    todo.is_completed = not todo.is_completed
    db.session.commit()
    
    return redirect(url_for('todos'))

# ==== 目標管理関連のルート =====
@app.route('/goals')
@login_required
def goals():
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # ログイン中の学生の目標リストを取得
    goals = Goal.query.filter_by(student_id=current_user.id).order_by(Goal.goal_type, Goal.due_date).all()
    
    # 選択中のテーマを取得（表示用）
    theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
    
    # 今日の日付
    today = datetime.now().date()
    
    return render_template('goals.html', goals=goals, theme=theme, today=today)

@app.route('/new_goal', methods=['GET', 'POST'])
@login_required
def new_goal():
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # 選択中のテーマを取得（表示用）
    theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description', '')
        goal_type = request.form.get('goal_type', 'medium')
        due_date_str = request.form.get('due_date', '')
        
        if not title:
            flash('タイトルは必須項目です。')
            return render_template('new_goal.html', theme=theme)
        
        # 新しい目標を作成
        new_goal = Goal(
            student_id=current_user.id,
            title=title,
            description=description,
            goal_type=goal_type,
            due_date=datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None,
            progress=0,
            is_completed=False
        )
        
        db.session.add(new_goal)
        db.session.commit()
        
        flash('新しい目標が追加されました。')
        return redirect(url_for('goals'))
    
    return render_template('new_goal.html', theme=theme)

@app.route('/goal/<int:goal_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_goal(goal_id):
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # 目標を取得
    goal = Goal.query.get_or_404(goal_id)
    
    # 権限チェック
    if goal.student_id != current_user.id:
        flash('この目標を編集する権限がありません。')
        return redirect(url_for('goals'))
    
    # 選択中のテーマを取得（表示用）
    theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description', '')
        goal_type = request.form.get('goal_type', 'medium')
        due_date_str = request.form.get('due_date', '')
        progress = int(request.form.get('progress', 0))
        is_completed = 'is_completed' in request.form
        
        if not title:
            flash('タイトルは必須項目です。')
            return render_template('edit_goal.html', goal=goal, theme=theme)
        
        # 目標を更新
        goal.title = title
        goal.description = description
        goal.goal_type = goal_type
        goal.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
        goal.progress = progress
        goal.is_completed = is_completed
        
        db.session.commit()
        
        flash('目標が更新されました。')
        return redirect(url_for('goals'))
    
    return render_template('edit_goal.html', goal=goal, theme=theme)

@app.route('/goal/<int:goal_id>/delete')
@login_required
def delete_goal(goal_id):
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # 目標を取得
    goal = Goal.query.get_or_404(goal_id)
    
    # 権限チェック
    if goal.student_id != current_user.id:
        flash('この目標を削除する権限がありません。')
        return redirect(url_for('goals'))
    
    # 目標を削除
    db.session.delete(goal)
    db.session.commit()
    
    flash('目標が削除されました。')
    return redirect(url_for('goals'))

@app.route('/goal/<int:goal_id>/update_progress', methods=['POST'])
@login_required
def update_goal_progress(goal_id):
    if current_user.role != 'student':
        return jsonify({'error': 'Permission denied'}), 403
    
    # 目標を取得
    goal = Goal.query.get_or_404(goal_id)
    
    # 権限チェック
    if goal.student_id != current_user.id:
        return jsonify({'error': 'Permission denied'}), 403
    
    # 進捗を更新
    data = request.get_json()
    progress = data.get('progress', 0)
    
    # 値の範囲を確認
    progress = max(0, min(100, progress))
    
    # 進捗が100%なら完了フラグも設定
    goal.progress = progress
    goal.is_completed = (progress == 100)
    
    db.session.commit()
    
    return jsonify({'success': True, 'progress': progress, 'is_completed': goal.is_completed})

@app.route('/chat', methods=['GET'])
@login_required
def chat_page():
    # チャット履歴の取得
    chat_history = ChatHistory.query.filter_by(user_id=current_user.id).order_by(ChatHistory.timestamp.desc()).limit(20).all()
    
    # 選択中のテーマを取得（表示用）
    theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first() if current_user.role == 'student' else None
    
    # ai_helpers から学習ステップと教師機能を取得
    from ai_helpers import LEARNING_STEPS, TEACHER_FUNCTIONS
    
    return render_template('chat.html', 
                          chat_history=chat_history, 
                          theme=theme,
                          learning_steps=LEARNING_STEPS,
                          teacher_functions=TEACHER_FUNCTIONS)

@app.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    """チャットAPIエンドポイント - AIチャット応答を生成"""
    try:
        # デバッグ用にリクエスト情報を出力
        print("Request headers:", request.headers)
        print("Content type:", request.content_type)
        print("Is JSON:", request.is_json)
        
        # リクエストの形式を判定（JSONかフォームデータか）
        if request.is_json:
            data = request.get_json()
            print("JSON data:", data)
            message = data.get('message', '')
            step_id = data.get('step', '')
            function_id = data.get('function', '')
        else:
            # フォームデータの場合
            print("Form data:", request.form)
            message = request.form.get('message', '')
            step_id = request.form.get('step', '')
            function_id = request.form.get('function', '')
        
        print(f"Processed data: message='{message}', step='{step_id}', function='{function_id}'")
        
        # メッセージが空でないことを確認
        if not message:
            return jsonify({"error": "メッセージが空です"}), 400
            
        # 選択中のテーマを取得（学生の場合）
        context = {}
        if current_user.role == 'student':
            theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
            if theme:
                context['theme'] = theme
        
        # ai_helpers を使用してプロンプトを生成
        from ai_helpers import generate_system_prompt, call_openai_api
        
        # システムプロンプトを生成
        system_prompt = generate_system_prompt(
            user=current_user,
            step_id=step_id if step_id else None,
            function_id=function_id if function_id else None,
            context=context
        )
        
        # チャット履歴の取得（新しい順に10件）
        chat_history = ChatHistory.query.filter_by(user_id=current_user.id).order_by(
            ChatHistory.timestamp.desc()).limit(10).all()
        
        # 古い順に並べ直す
        chat_history = chat_history[::-1]
        
        # メッセージの構築
        messages = [{"role": "system", "content": system_prompt}]
        
        for chat in chat_history:
            messages.append({"role": "user" if chat.is_user else "assistant", "content": chat.message})
        
        messages.append({"role": "user", "content": message})
        
        # APIを呼び出し
        api_key = os.getenv('OPENAI_API_KEY')
        ai_response = call_openai_api(messages, api_key)
        
        # ユーザーのメッセージを保存
        user_chat = ChatHistory(user_id=current_user.id, message=message, is_user=True)
        db.session.add(user_chat)
        
        # AIの返答を保存
        ai_chat = ChatHistory(user_id=current_user.id, message=ai_response, is_user=False)
        db.session.add(ai_chat)
        
        db.session.commit()
        
        return jsonify({"response": ai_response})
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"チャットAPI エラー: {str(e)}\n{error_details}")
        return jsonify({"error": str(e)}), 500

@app.route('/classes')
@login_required
def classes():
    if current_user.role == 'teacher':
        # 教師向けのクラス管理ページ - 自分の学校のクラスのみ表示
        if current_user.school_id:
            classes = Class.query.filter_by(
                teacher_id=current_user.id,
                school_id=current_user.school_id  # 同じ学校のクラスのみ
            ).all()
        else:
            classes = []  # 学校に所属していない場合は空リスト
            
        return render_template('teacher_classes.html', classes=classes)
    else:
        # 学生向けのクラス閲覧ページ - 自分の学校のクラスのみ表示
        if current_user.school_id:
            classes = Class.query.filter_by(
                school_id=current_user.school_id  # 同じ学校のクラスのみ
            ).all()
        else:
            classes = []  # 学校に所属していない場合は空リスト
            
        return render_template('student_classes.html', classes=classes)

@app.route('/class/<int:class_id>/add_students', methods=['GET', 'POST'])
@login_required
def add_students(class_id):
    # 教師のみアクセス可能
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    # クラスオブジェクトを取得
    class_obj = Class.query.get_or_404(class_id)
    
    # 教師がクラスの所有者でない場合はアクセス制限
    if class_obj.teacher_id != current_user.id:
        flash('このクラスを編集する権限がありません。')
        return redirect(url_for('classes'))
    
    # このクラスに既に所属している学生のIDを取得
    enrolled_student_ids = [student.id for student in class_obj.students]
    
    # 追加可能な学生（まだクラスに所属していない学生かつ同じ学校に所属している学生）を取得
    # 修正: 同じschool_idの学生のみを対象にする
    available_students = User.query.filter(
        User.role == 'student',
        ~User.id.in_(enrolled_student_ids) if enrolled_student_ids else True,
        User.school_id == class_obj.school_id  # 同じ学校IDの学生のみに限定
    ).all()
    
    if request.method == 'POST':
        student_ids = request.form.getlist('student_ids')
        
        if not student_ids:
            flash('学生が選択されていません。')
            return render_template('add_students.html', class_obj=class_obj, available_students=available_students)
        
        # 選択された学生をクラスに追加
        for student_id in student_ids:
            # 学校IDの再確認（セキュリティのため）
            student = User.query.get(int(student_id))
            
            # 学生が存在し、同じ学校に所属していることを確認
            if student and student.school_id == class_obj.school_id:
                # 既に登録されていないことを確認
                if int(student_id) not in enrolled_student_ids:
                    enrollment = ClassEnrollment(
                        class_id=class_id,
                        student_id=int(student_id)
                    )
                    db.session.add(enrollment)
            else:
                flash(f'学生 ID:{student_id} は同じ学校に所属していないため追加できません。', 'error')
        
        db.session.commit()
        flash(f'{len(student_ids)}人の学生をクラスに追加しました。')
        return redirect(url_for('view_class', class_id=class_id))
    
    return render_template('add_students.html', class_obj=class_obj, available_students=available_students)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/themes')
@login_required
def view_themes():
    if current_user.role == 'student':
        # 学生の場合
        # ログイン中の学生の探究テーマを取得
        themes = InquiryTheme.query.filter_by(student_id=current_user.id).all()
        
        # テーマごとに関連する大テーマの情報を取得
        themes_with_main = []
        for theme in themes:
            main_theme = None
            if theme.main_theme_id:
                main_theme = MainTheme.query.get(theme.main_theme_id)
            
            themes_with_main.append({
                'theme': theme,
                'main_theme': main_theme
            })
        
        # 学生が所属するクラスの大テーマを取得（新規作成用）
        enrolled_classes = current_user.enrolled_classes.all()
        class_ids = [c.id for c in enrolled_classes]
        available_main_themes = MainTheme.query.filter(MainTheme.class_id.in_(class_ids)).all()
        
        return render_template('view_themes.html', 
                             themes_with_main=themes_with_main, 
                             available_main_themes=available_main_themes)
    
    elif current_user.role == 'teacher':
        # 教師の場合、担当クラスと各クラスの大テーマを表示
        classes = Class.query.filter_by(teacher_id=current_user.id).all()
        
        classes_with_themes = []
        for class_obj in classes:
            main_themes = MainTheme.query.filter_by(class_id=class_obj.id).all()
            classes_with_themes.append({
                'class': class_obj,
                'main_themes': main_themes
            })
        
        return render_template('teacher_themes.html', classes_with_themes=classes_with_themes)
    
    elif current_user.role == 'admin':
        # 管理者の場合は管理画面にリダイレクト
        return redirect(url_for('admin_schools'))
    
    # その他のロールの場合
    return redirect(url_for('index'))

@app.route('/select_theme/<int:theme_id>', methods=['POST'])
@login_required
def select_theme(theme_id):
    # 既に選択中のテーマがあれば解除
    InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).update({'is_selected': False})
    # 選択されたテーマを取得して更新
    theme = InquiryTheme.query.filter_by(id=theme_id, student_id=current_user.id).first_or_404()
    theme.is_selected = True
    db.session.commit()
    flash('テーマを選択しました。')
    return redirect(url_for('view_themes'))

@app.route('/regenerate_themes', methods=['POST'])
@login_required
def regenerate_themes():
    # 既存のテーマを削除
    InquiryTheme.query.filter_by(student_id=current_user.id).delete()
    db.session.commit()

    # 学生がアンケートに回答済みか確認
    if not current_user.has_completed_surveys():
        flash('テーマを生成するには、まずすべてのアンケートに回答してください。')
        return redirect(url_for('surveys'))
    
    # 興味関心アンケートと思考特性アンケートの回答を取得
    interest_survey = InterestSurvey.query.filter_by(student_id=current_user.id).first()
    personality_survey = PersonalitySurvey.query.filter_by(student_id=current_user.id).first()
    
    if not interest_survey or not personality_survey:
        flash('テーマを生成するには、まずすべてのアンケートに回答してください。')
        return redirect(url_for('surveys'))
    
    # アンケート回答からJSONを解析
    interest_responses = json.loads(interest_survey.responses)
    personality_responses = json.loads(personality_survey.responses)
    
    # 実際の実装ではここでOpenAI APIを使ってテーマを生成
    # 今回はサンプルとして3つのテーマを生成
    themes = [
        {
            "title": "持続可能なコミュニティ開発",
            "question": "地域の文化や自然環境を保全しながら、どうすれば持続可能な地域社会を構築できるか？",
            "description": "地域社会の課題と資源を調査し、持続可能なコミュニティ開発のモデルを提案する。",
            "rationale": "あなたは地域社会や文化保全に関心があり、コミュニケーション能力を活かして社会課題の解決に取り組みたいようです。",
            "approach": "地域の人々へのインタビュー、成功事例の調査、協働プロジェクトの計画と実施などを通じて探究を進めるとよいでしょう。",
            "potential": "地域活性化プロジェクトの立案や、持続可能な地域開発モデルの提案につながる可能性があります。"
        },
        {
            "title": "デジタル技術を活用した学習格差の解消",
            "question": "デジタル技術をどのように活用すれば、教育機会の格差を効果的に減らすことができるか？",
            "description": "デジタル技術を用いた教育アクセス改善の方法を調査し、実践的なソリューションを開発する。",
            "rationale": "あなたは教育問題や技術革新に関心があり、分析的思考を活かして社会課題の解決に取り組みたいようです。",
            "approach": "既存の教育テクノロジーの効果分析、アクセス格差の要因調査、プロトタイプの開発とテストなどを通じて探究を進めるとよいでしょう。",
            "potential": "教育アプリの開発や、デジタル教育プログラムの提案につながる可能性があります。"
        },
        {
            "title": "気候変動への若者の意識と行動",
            "question": "若者の間で気候変動への意識を高め、具体的な行動を促すにはどのような方法が有効か？",
            "description": "若者の環境意識と行動の関係を調査し、効果的な啓発・行動変容プログラムを提案する。",
            "rationale": "あなたは環境問題や社会活動に関心があり、創造的思考を活かして社会課題の解決に取り組みたいようです。",
            "approach": "若者の環境意識調査、既存のキャンペーン分析、プロトタイププログラムの開発と効果測定などを通じて探究を進めるとよいでしょう。",
            "potential": "環境教育プログラムの開発や、若者主導の環境活動モデルの提案につながる可能性があります。"
        }
    ]
    
    # データベースに新しいテーマを追加
    for theme in themes:
        new_theme = InquiryTheme(
            student_id=current_user.id,
            title=theme["title"],
            question=theme["question"],
            description=theme["description"],
            rationale=theme["rationale"],
            approach=theme["approach"],
            potential=theme["potential"]
        )
        db.session.add(new_theme)
    
    db.session.commit()
    flash('新しい探究テーマが生成されました。')
    return redirect(url_for('view_themes'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email')
        role = request.form.get('role', 'student')
        school_code = request.form.get('school_code')  # 学校コードを取得
        
        # パスワード確認のチェック
        if password != confirm_password:
            flash('パスワードが一致しません。')
            return render_template('register.html')
        
        # 既存のユーザー名チェック
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('そのユーザー名は既に使用されています。')
            return render_template('register.html')
        
        # 既存のメールアドレスチェック
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('そのメールアドレスは既に使用されています。')
            return render_template('register.html')
        
        # 学校コードのチェック
        if school_code:
            school = School.query.filter_by(code=school_code).first()
            if not school:
                flash('入力された学校コードが見つかりません。')
                return render_template('register.html')
            school_id = school.id
        else:
            school_id = None
        
        # 新しいユーザーの作成
        new_user = User(
            username=username,
            password=generate_password_hash(password),
            email=email,
            role=role,
            school_id=school_id
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash('登録が完了しました。ログインしてください。')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# クラス関連のルート
@app.route('/create_class', methods=['GET', 'POST'])
@login_required
def create_class():
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    # 学校IDがなければアクセスできない
    if not current_user.school_id:
        flash('クラスを作成するには学校に所属している必要があります。')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        class_name = request.form.get('class_name')
        
        if not class_name or class_name.strip() == '':
            flash('クラス名を入力してください。')
            return render_template('create_class.html')
        
        class_name = class_name.strip()
        
        new_class = Class(
            teacher_id=current_user.id,
            school_id=current_user.school_id,  # 教師の学校IDを設定
            name=class_name
        )
        
        try:
            db.session.add(new_class)
            db.session.commit()
            flash('クラスが作成されました。')
            return redirect(url_for('classes'))
        except Exception as e:
            db.session.rollback()
            print(f"Error creating class: {str(e)}")
            flash('クラス作成中にエラーが発生しました。')
            return render_template('create_class.html')
    
    return render_template('create_class.html')

@app.route('/class/<int:class_id>')
@login_required
def class_details(class_id):
     # リダイレクトを追加する
    return redirect(url_for('view_class', class_id=class_id))
    # クラスオブジェクトを取得
    class_obj = Class.query.get_or_404(class_id)
    
    # 教師がクラスの所有者でない場合はアクセス制限（教師ユーザーの場合のみ）
    if current_user.role == 'teacher' and class_obj.teacher_id != current_user.id:
        flash('このクラスの詳細を閲覧する権限がありません。')
        return redirect(url_for('classes'))
    
    # 学生リストを取得（クラスに所属する全学生）
    students = class_obj.students.all()
    
    # 各学生の追加情報を集める
    students_info = []
    for student in students:
        # 学生の選択中テーマを取得
        selected_theme = InquiryTheme.query.filter_by(
            student_id=student.id, 
            is_selected=True
        ).first()
        
        # 学生の最新の活動記録を取得
        latest_activity = ActivityLog.query.filter_by(
            student_id=student.id
        ).order_by(ActivityLog.date.desc()).first()
        
        # 学生情報を辞書にまとめる
        student_info = {
            'student': student,
            'selected_theme': selected_theme,
            'latest_activity': latest_activity
        }
        students_info.append(student_info)
    
    # テンプレートをレンダリング
    return render_template('class_details.html', 
                          class_obj=class_obj, 
                          students=students_info)

@app.route('/class/<int:class_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_class(class_id):
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    class_obj = Class.query.get_or_404(class_id)
    
    if class_obj.teacher_id != current_user.id:
        flash('このクラスを編集する権限がありません。')
        return redirect(url_for('classes'))
    
    if request.method == 'POST':
        class_name = request.form.get('class_name')
        
        if not class_name:
            flash('クラス名を入力してください。')
            return render_template('edit_class.html', class_obj=class_obj)
        
        class_obj.name = class_name
        db.session.commit()
        
        flash('クラス情報が更新されました。')
        return redirect(url_for('view_class', class_id=class_id))
    
    return render_template('edit_class.html', class_obj=class_obj)

@app.route('/class/<int:class_id>/delete')
@login_required
def delete_class(class_id):
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    class_obj = Class.query.get_or_404(class_id)
    
    if class_obj.teacher_id != current_user.id:
        flash('このクラスを削除する権限がありません。')
        return redirect(url_for('classes'))
    
    db.session.delete(class_obj)
    db.session.commit()
    
    flash('クラスが削除されました。')
    return redirect(url_for('classes'))

# 大テーマ一覧を表示するルート
@app.route('/class/<int:class_id>/main_themes')
@login_required
def view_main_themes(class_id):
    # 教師のみアクセス可能
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    # クラスオブジェクトを取得
    class_obj = Class.query.get_or_404(class_id)
    
    # 教師がクラスの所有者でない場合はアクセス制限
    if class_obj.teacher_id != current_user.id:
        flash('このクラスの大テーマを管理する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    # クラスに関連する大テーマを取得
    main_themes = MainTheme.query.filter_by(class_id=class_id).all()
    
    return render_template('main_themes.html', class_obj=class_obj, main_themes=main_themes)

# 大テーマを作成するルート
@app.route('/class/<int:class_id>/main_themes/create', methods=['GET', 'POST'])
@login_required
def create_main_theme(class_id):
    # 教師のみアクセス可能
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    # クラスオブジェクトを取得
    class_obj = Class.query.get_or_404(class_id)
    
    # 教師がクラスの所有者でない場合はアクセス制限
    if class_obj.teacher_id != current_user.id:
        flash('このクラスの大テーマを作成する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description', '')
        
        if not title:
            flash('タイトルは必須項目です。')
            return render_template('create_main_theme.html', class_obj=class_obj)
        
        # 新しい大テーマを作成
        new_theme = MainTheme(
            teacher_id=current_user.id,
            class_id=class_id,
            title=title,
            description=description
        )
        
        db.session.add(new_theme)
        db.session.commit()
        
        flash('新しい大テーマが作成されました。')
        return redirect(url_for('view_main_themes', class_id=class_id))
    
    return render_template('create_main_theme.html', class_obj=class_obj)

# 大テーマを編集するルート
@app.route('/main_theme/<int:theme_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_main_theme(theme_id):
    # 教師のみアクセス可能
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    # 大テーマを取得
    main_theme = MainTheme.query.get_or_404(theme_id)
    
    # 教師がテーマの所有者でない場合はアクセス制限
    if main_theme.teacher_id != current_user.id:
        flash('この大テーマを編集する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description', '')
        
        if not title:
            flash('タイトルは必須項目です。')
            return render_template('edit_main_theme.html', main_theme=main_theme)
        
        # 大テーマを更新
        main_theme.title = title
        main_theme.description = description
        main_theme.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('大テーマが更新されました。')
        return redirect(url_for('view_main_themes', class_id=main_theme.class_id))
    
    return render_template('edit_main_theme.html', main_theme=main_theme)

# 大テーマを削除するルート
@app.route('/main_theme/<int:theme_id>/delete')
@login_required
def delete_main_theme(theme_id):
    # 教師のみアクセス可能
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    # 大テーマを取得
    main_theme = MainTheme.query.get_or_404(theme_id)
    
    # 教師がテーマの所有者でない場合はアクセス制限
    if main_theme.teacher_id != current_user.id:
        flash('この大テーマを削除する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    # 関連する個人テーマの main_theme_id を NULL に設定
    InquiryTheme.query.filter_by(main_theme_id=theme_id).update({'main_theme_id': None})
    
    # 大テーマを削除
    class_id = main_theme.class_id
    db.session.delete(main_theme)
    db.session.commit()
    
    flash('大テーマが削除されました。')
    return redirect(url_for('view_main_themes', class_id=class_id))

# 大テーマ一覧を表示するルート（学生向け）
@app.route('/main_themes')
@login_required
def student_view_main_themes():
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # 学生が所属するクラスを取得
    enrolled_classes = current_user.enrolled_classes.all()
    class_ids = [c.id for c in enrolled_classes]
    
    # 所属クラスに関連する大テーマを取得
    main_themes = MainTheme.query.filter(MainTheme.class_id.in_(class_ids)).all()
    
    # 各大テーマに関連するクラス名を取得
    themes_with_classes = []
    for theme in main_themes:
        class_name = Class.query.get(theme.class_id).name
        themes_with_classes.append({
            'theme': theme,
            'class_name': class_name
        })
    
    return render_template('student_main_themes.html', themes_with_classes=themes_with_classes)

# 大テーマに基づいて自分で個人テーマを作成するルート
@app.route('/main_theme/<int:theme_id>/create_personal', methods=['GET', 'POST'])
@login_required
def create_personal_theme(theme_id):
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # 大テーマを取得
    main_theme = MainTheme.query.get_or_404(theme_id)
    
    # 学生がそのクラスに所属しているか確認
    enrolled_class_ids = [c.id for c in current_user.enrolled_classes]
    if main_theme.class_id not in enrolled_class_ids:
        flash('このテーマにアクセスする権限がありません。')
        return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        question = request.form.get('question')
        description = request.form.get('description', '')
        
        if not title or not question:
            flash('タイトルと探究の問いは必須項目です。')
            return render_template('create_personal_theme.html', main_theme=main_theme)
        
        # 既存の選択中テーマを解除
        InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).update({'is_selected': False})
        
        # 新しい個人テーマを作成
        new_theme = InquiryTheme(
            student_id=current_user.id,
            main_theme_id=theme_id,
            title=title,
            question=question,
            description=description,
            is_selected=True,
            is_ai_generated=False
        )
        
        db.session.add(new_theme)
        db.session.commit()
        
        flash('個人テーマが作成されました。')
        return redirect(url_for('view_themes'))
    
    return render_template('create_personal_theme.html', main_theme=main_theme)

# AIに個人テーマを提案してもらうルート
@app.route('/main_theme/<int:theme_id>/generate_theme', methods=['GET', 'POST'])
@login_required
def generate_theme(theme_id):
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # 大テーマを取得
    main_theme = MainTheme.query.get_or_404(theme_id)
    
    # 学生がそのクラスに所属しているか確認
    enrolled_class_ids = [c.id for c in current_user.enrolled_classes]
    if main_theme.class_id not in enrolled_class_ids:
        flash('このテーマにアクセスする権限がありません。')
        return redirect(url_for('student_dashboard'))
    
    # 学生がアンケートに回答済みか確認
    if not current_user.has_completed_surveys():
        flash('テーマを生成するには、まずすべてのアンケートに回答してください。')
        return redirect(url_for('surveys'))
    
    # 興味関心アンケートと思考特性アンケートの回答を取得
    interest_survey = InterestSurvey.query.filter_by(student_id=current_user.id).first()
    personality_survey = PersonalitySurvey.query.filter_by(student_id=current_user.id).first()
    
    if not interest_survey or not personality_survey:
        flash('テーマを生成するには、まずすべてのアンケートに回答してください。')
        return redirect(url_for('surveys'))
    
    if request.method == 'POST':
        # アンケート回答からJSONを解析
        interest_responses = json.loads(interest_survey.responses)
        personality_responses = json.loads(personality_survey.responses)
        
        # OpenAI APIを使って個人テーマを生成
        try:
            themes = generate_personal_themes_with_ai(main_theme, interest_responses, personality_responses)
            
            # 既存の選択中テーマを解除
            InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).update({'is_selected': False})
            
            # データベースに新しいテーマを追加
            for i, theme in enumerate(themes):
                new_theme = InquiryTheme(
                    student_id=current_user.id,
                    main_theme_id=theme_id,
                    title=theme["title"],
                    question=theme["question"],
                    description=theme["description"],
                    rationale=theme["rationale"],
                    approach=theme["approach"],
                    potential=theme["potential"],
                    is_ai_generated=True,
                    is_selected=(i == 0)  # 最初のテーマを選択状態にする
                )
                db.session.add(new_theme)
            
            db.session.commit()
            
            flash('AIによる個人テーマの提案が完了しました。')
            return redirect(url_for('view_themes'))
            
        except Exception as e:
            flash(f'テーマの生成中にエラーが発生しました: {str(e)}')
            return render_template('generate_theme.html', main_theme=main_theme)
    
    return render_template('generate_theme.html', main_theme=main_theme)

# AIテーマを修正するルート
@app.route('/theme/<int:theme_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_theme(theme_id):
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # 個人テーマを取得
    theme = InquiryTheme.query.get_or_404(theme_id)
    
    # 権限チェック
    if theme.student_id != current_user.id:
        flash('このテーマを編集する権限がありません。')
        return redirect(url_for('view_themes'))
    
    # 関連する大テーマを取得（存在する場合）
    main_theme = None
    if theme.main_theme_id:
        main_theme = MainTheme.query.get(theme.main_theme_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        question = request.form.get('question')
        description = request.form.get('description', '')
        
        if not title or not question:
            flash('タイトルと探究の問いは必須項目です。')
            return render_template('edit_theme.html', theme=theme, main_theme=main_theme)
        
        # テーマを更新
        theme.title = title
        theme.question = question
        theme.description = description
        
        db.session.commit()
        
        flash('テーマが更新されました。')
        return redirect(url_for('view_themes'))
    
    return render_template('edit_theme.html', theme=theme, main_theme=main_theme)

# アンケート関連のルート
@app.route('/interest_survey', methods=['GET', 'POST'])
@login_required
def interest_survey():
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # 既に回答しているか確認
    existing_survey = InterestSurvey.query.filter_by(student_id=current_user.id).first()
    if existing_survey:
        return redirect(url_for('interest_survey_edit'))
    
    if request.method == 'POST':
        # アンケート回答の処理
        responses = {}
        for key, value in request.form.items():
            if key.startswith('question_'):
                responses[key] = value
        
        new_survey = InterestSurvey(
            student_id=current_user.id,
            responses=json.dumps(responses)
        )
        db.session.add(new_survey)
        db.session.commit()
        
        flash('興味関心アンケートが保存されました。')
        return redirect(url_for('surveys'))
    
    return render_template('interest_survey.html')

@app.route('/interest_survey/edit', methods=['GET', 'POST'])
@login_required
def interest_survey_edit():
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    survey = InterestSurvey.query.filter_by(student_id=current_user.id).first_or_404()
    responses = json.loads(survey.responses)
    
    if request.method == 'POST':
        # アンケート回答の更新処理
        updated_responses = {}
        for key, value in request.form.items():
            if key.startswith('question_'):
                updated_responses[key] = value
        
        survey.responses = json.dumps(updated_responses)
        db.session.commit()
        
        flash('興味関心アンケートが更新されました。')
        return redirect(url_for('surveys'))
    
    return render_template('interest_survey_edit.html', responses=responses)

@app.route('/personality_survey', methods=['GET', 'POST'])
@login_required
def personality_survey():
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # 既に回答しているか確認
    existing_survey = PersonalitySurvey.query.filter_by(student_id=current_user.id).first()
    if existing_survey:
        return redirect(url_for('personality_survey_edit'))
    
    if request.method == 'POST':
        # アンケート回答の処理
        responses = {}
        for key, value in request.form.items():
            if key.startswith('question_'):
                responses[key] = value
        
        new_survey = PersonalitySurvey(
            student_id=current_user.id,
            responses=json.dumps(responses)
        )
        db.session.add(new_survey)
        db.session.commit()
        
        flash('思考特性アンケートが保存されました。')
        return redirect(url_for('surveys'))
    
    return render_template('personality_survey.html')

@app.route('/personality_survey/edit', methods=['GET', 'POST'])
@login_required
def personality_survey_edit():
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    survey = PersonalitySurvey.query.filter_by(student_id=current_user.id).first_or_404()
    responses = json.loads(survey.responses)
    
    if request.method == 'POST':
        # アンケート回答の更新処理
        updated_responses = {}
        for key, value in request.form.items():
            if key.startswith('question_'):
                updated_responses[key] = value
        
        survey.responses = json.dumps(updated_responses)
        db.session.commit()
        
        flash('思考特性アンケートが更新されました。')
        return redirect(url_for('surveys'))
    
    return render_template('personality_survey_edit.html', responses=responses)

# 活動記録関連のルート
@app.route('/new_activity', methods=['GET', 'POST'])
@login_required
def new_activity():
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    # 選択中のテーマを取得
    theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
    
    if request.method == 'POST':
        title = request.form.get('title')
        date_str = request.form.get('date')
        
        # 変更：None 対策 - contentとreflectionにデフォルト値を設定
        content = request.form.get('content') or ""  # 481行目を修正
        reflection = request.form.get('reflection') or ""  # 482行目を修正
        
        if not content:
            flash('活動内容を入力してください。')
            return render_template('new_activity.html', theme=theme)
        
        # 新しい活動ログを作成
        new_log = ActivityLog(
            student_id=current_user.id,
            title=title,
            date=datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.utcnow().date(),
            content=content,
            reflection=reflection,
            activity=content  # 互換性のために既存フィールドも設定
        )
        
        # 画像のアップロード処理
        if 'image' in request.files and request.files['image'].filename != '':
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # タイムスタンプを加えて一意のファイル名にする
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                # 保存したファイルのURLをデータベースに保存
                new_log.image_url = url_for('static', filename=f'uploads/{filename}')
        
        db.session.add(new_log)
        db.session.commit()
        
        flash('活動が記録されました。')
        return redirect(url_for('activities'))
    
    return render_template('new_activity.html', theme=theme, now=datetime.now())

@app.route('/activity/<int:log_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_activity(log_id):
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('index'))
    
    activity = ActivityLog.query.get_or_404(log_id)
    
    if activity.student_id != current_user.id:
        flash('この活動記録を編集する権限がありません。')
        return redirect(url_for('activities'))
    
    # 選択中のテーマを取得
    theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
    
    if request.method == 'POST':
        title = request.form.get('title')
        date_str = request.form.get('date')
        
        # 変更：None 対策 - contentとreflectionにデフォルト値を設定
        content = request.form.get('content') or ""  # 527行目を修正
        reflection = request.form.get('reflection') or ""  # 528行目を修正
        
        if not content:
            flash('活動内容を入力してください。')
            return render_template('edit_activity.html', activity=activity, theme=theme)
        
        activity.title = title
        # 日付文字列をdateオブジェクトに変換
        activity.date = datetime.strptime(date_str, '%Y-%m-%d').date()
        activity.content = content
        activity.reflection = reflection
        activity.activity = content  # 互換性のために既存フィールドも更新
        
        # 画像のアップロード処理
        if 'image' in request.files and request.files['image'].filename != '':
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # タイムスタンプを加えて一意のファイル名にする
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                # 保存したファイルのURLをデータベースに保存
                activity.image_url = url_for('static', filename=f'uploads/{filename}')
        
        db.session.commit()
        
        flash('活動記録が更新されました。')
        return redirect(url_for('activities'))
    
    return render_template('edit_activity.html', activity=activity, theme=theme)

    # 新しいテーマを生成（ここでは仮の実装例）
    new_theme = InquiryTheme(
        student_id=current_user.id,
        title="新しい探究テーマ",
        question="あなたの探究の問いは何ですか？",
        description="テーマの概要説明。",
        rationale="このテーマを選んだ理由。",
        approach="取り組み方のアドバイス。",
        potential="発展の可能性。"
    )
    db.session.add(new_theme)
    db.session.commit()
    flash('新しいテーマを生成しました。')
    return redirect(url_for('view_themes'))

if __name__ == '__main__':
    app.run(debug=True)

# 画像アップロード用のヘルパー関数
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# app.pyの末尾付近に追加
@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Class': Class, 'InterestSurvey': InterestSurvey, 'Goal': Goal}

# AIを使って個人テーマを生成する関数
def generate_personal_themes_with_ai(main_theme, interest_responses, personality_responses):
    """
    OpenAI APIを使用して、大テーマと学生のアンケート回答に基づく個人テーマを生成する
    
    Args:
        main_theme: 大テーマのオブジェクト
        interest_responses: 興味関心アンケートの回答
        personality_responses: 思考特性アンケートの回答
        
    Returns:
        生成されたテーマのリスト（辞書形式）
    """
    # システムプロンプトの構築
    system_prompt = """
    あなたは教育AIアシスタントで、高校生の探究学習テーマ提案を担当しています。
    生徒の興味関心と思考特性に合わせて、与えられた大テーマに即した個人テーマを3つ提案してください。
    提案するテーマは、高校生が1年間かけて取り組むのに適切な範囲と難易度にしてください。
    
    各テーマには以下の要素を含めてください：
    1. タイトル（簡潔かつ具体的に）
    2. 探究の問い（具体的でオープンエンドな問いかけ）
    3. テーマの概要説明（100字程度）
    4. 選定理由（この生徒に合っている理由）
    5. アプローチ方法（調査や実験の進め方のアドバイス）
    6. 発展可能性（深掘りできる方向性）
    
    重要：提案するテーマは必ず大テーマの範囲内に収まるようにしてください。
    """

    # ユーザープロンプトの構築
    user_prompt = f"""
    【大テーマ】
    タイトル：{main_theme.title}
    説明：{main_theme.description}
    
    【生徒の興味関心アンケート回答】
    {format_survey_responses(interest_responses)}
    
    【生徒の思考特性アンケート回答】
    {format_survey_responses(personality_responses)}
    
    この生徒に合った、大テーマに即した個人テーマを3つ提案してください。
    回答はJSON形式で返してください：
    
    [
      {{
        "title": "テーマタイトル",
        "question": "探究の問い",
        "description": "テーマの概要説明", 
        "rationale": "選定理由",
        "approach": "アプローチ方法",
        "potential": "発展可能性"
      }},
      ...
    ]
    """
    
    try:
        # 新しいOpenAIのAPIの呼び出し方法
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))  # 環境変数から直接APIキーを取得
        
        response = client.chat.completions.create(
            model="gpt-4",  # もしくはgpt-3.5-turboなど利用可能なモデル
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        # APIレスポンスからテーマを抽出 - 新APIでのアクセス方法
        content = response.choices[0].message.content
        
        # JSON部分を抽出（テキスト中からJSONを見つける）
        json_match = re.search(r'\[\s*{.*}\s*\]', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            themes = json.loads(json_str)
        else:
            # JSONの抽出に失敗した場合、全体をJSONとして解析
            themes = json.loads(content)
        
        return themes
        
    except Exception as e:
        print(f"Error generating themes: {str(e)}")
        # エラー時はダミーテーマを返す
        return [
            {
                "title": "大テーマに関連する個人テーマ例",
                "question": f"{main_theme.title}に関して、どのような方法で探究できるか？",
                "description": f"{main_theme.title}に関連する個人的な探究テーマ。", 
                "rationale": "あなたの興味と関心に基づいています。",
                "approach": "文献調査と実地調査を組み合わせて進めるとよいでしょう。",
                "potential": "さらに専門的な視点や実践的な応用に発展させることができます。"
            }
        ]

# アンケート回答をテキスト形式にフォーマットする関数
def format_survey_responses(responses):
    """
    アンケート回答を読みやすいテキスト形式に変換する
    
    Args:
        responses: アンケート回答の辞書
        
    Returns:
        フォーマットされたテキスト
    """
    formatted = []
    for key, value in responses.items():
        # question_1, question_2 などから番号を抽出
        match = re.search(r'question_(\d+)', key)
        if match:
            question_num = match.group(1)
            formatted.append(f"質問{question_num}: {value}")
    
    return "\n".join(formatted)

# グループ一覧表示
@app.route('/class/<int:class_id>/groups')
@login_required
def view_groups(class_id):
    # クラスオブジェクトを取得
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if current_user.role == 'teacher' and class_obj.teacher_id != current_user.id:
        flash('このクラスのグループを表示する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    if current_user.role == 'student':
        enrolled_class_ids = [c.id for c in current_user.enrolled_classes]
        if class_id not in enrolled_class_ids:
            flash('このクラスのグループを表示する権限がありません。')
            return redirect(url_for('student_dashboard'))
    
    # クラスのグループを取得
    groups = Group.query.filter_by(class_id=class_id).all()
    
    # 各グループのメンバー数を取得
    groups_with_counts = []
    for group in groups:
        member_count = GroupMembership.query.filter_by(group_id=group.id).count()
        is_member = False
        if current_user.role == 'student':
            is_member = GroupMembership.query.filter_by(
                group_id=group.id, student_id=current_user.id).first() is not None
        
        groups_with_counts.append({
            'group': group,
            'member_count': member_count,
            'is_member': is_member
        })
    
    return render_template('view_groups.html', 
                           class_obj=class_obj, 
                           groups=groups_with_counts,
                           is_teacher=(current_user.role == 'teacher'))

# グループ作成
@app.route('/class/<int:class_id>/groups/create', methods=['GET', 'POST'])
@login_required
def create_group(class_id):
    # クラスオブジェクトを取得
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if current_user.role == 'teacher' and class_obj.teacher_id != current_user.id:
        flash('このクラスにグループを作成する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    if current_user.role == 'student':
        enrolled_class_ids = [c.id for c in current_user.enrolled_classes]
        if class_id not in enrolled_class_ids:
            flash('このクラスにグループを作成する権限がありません。')
            return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        if not name:
            flash('グループ名は必須です。')
            return render_template('create_group.html', class_obj=class_obj)
        
        # 新しいグループを作成
        new_group = Group(
            name=name,
            description=description,
            class_id=class_id,
            created_by=current_user.id
        )
        
        db.session.add(new_group)
        db.session.commit()
        
        # 作成者を自動的にメンバーに追加（学生の場合）
        if current_user.role == 'student':
            membership = GroupMembership(
                group_id=new_group.id,
                student_id=current_user.id
            )
            db.session.add(membership)
            db.session.commit()
        
        flash('グループが作成されました。')
        return redirect(url_for('view_groups', class_id=class_id))
    
    return render_template('create_group.html', class_obj=class_obj)

# グループ詳細表示
@app.route('/group/<int:group_id>')
@login_required
def view_group(group_id):
    # グループを取得
    group = Group.query.get_or_404(group_id)
    
    # クラスを取得
    class_obj = Class.query.get_or_404(group.class_id)
    
    # 権限チェック
    if current_user.role == 'teacher' and class_obj.teacher_id != current_user.id:
        flash('このグループを表示する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    if current_user.role == 'student':
        enrolled_class_ids = [c.id for c in current_user.enrolled_classes]
        if class_obj.id not in enrolled_class_ids:
            flash('このグループを表示する権限がありません。')
            return redirect(url_for('student_dashboard'))
    
    # グループメンバーを取得
    memberships = GroupMembership.query.filter_by(group_id=group_id).all()
    members = [User.query.get(membership.student_id) for membership in memberships]
    
    # グループ作成者の情報を取得 (この行を追加)
    creator = User.query.get(group.created_by)
    # 現在のユーザーがメンバーかどうか確認
    is_member = False
    if current_user.role == 'student':
        is_member = current_user.id in [member.id for member in members]
    
    # グループの作成者かどうか確認
    is_creator = (group.created_by == current_user.id)
    
    return render_template('view_group.html', 
                          group=group, 
                          class_obj=class_obj, 
                          members=members,
                          creator=creator,
                          is_member=is_member,
                          is_creator=is_creator,
                          is_teacher=(current_user.role == 'teacher'))

# グループ編集
@app.route('/group/<int:group_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_group(group_id):
    # グループを取得
    group = Group.query.get_or_404(group_id)
    
    # 権限チェック（教師またはグループ作成者のみ編集可能）
    if current_user.role == 'teacher' and Class.query.get(group.class_id).teacher_id != current_user.id:
        flash('このグループを編集する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    if current_user.role == 'student' and group.created_by != current_user.id:
        flash('このグループを編集する権限がありません。')
        return redirect(url_for('view_group', group_id=group_id))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        if not name:
            flash('グループ名は必須です。')
            return render_template('edit_group.html', group=group)
        
        # グループを更新
        group.name = name
        group.description = description
        
        db.session.commit()
        
        flash('グループが更新されました。')
        return redirect(url_for('view_group', group_id=group_id))
    
    return render_template('edit_group.html', group=group)

# グループ削除
@app.route('/group/<int:group_id>/delete')
@login_required
def delete_group(group_id):
    # グループを取得
    group = Group.query.get_or_404(group_id)
    
    # 権限チェック（教師またはグループ作成者のみ削除可能）
    if current_user.role == 'teacher' and Class.query.get(group.class_id).teacher_id != current_user.id:
        flash('このグループを削除する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    if current_user.role == 'student' and group.created_by != current_user.id:
        flash('このグループを削除する権限がありません。')
        return redirect(url_for('view_group', group_id=group_id))
    
    # クラスIDを保存（削除後にリダイレクトするため）
    class_id = group.class_id
    
    # グループメンバーシップを削除
    GroupMembership.query.filter_by(group_id=group_id).delete()
    
    # グループを削除
    db.session.delete(group)
    db.session.commit()
    
    flash('グループが削除されました。')
    return redirect(url_for('view_groups', class_id=class_id))

# グループに参加
@app.route('/group/<int:group_id>/join')
@login_required
def join_group(group_id):
    if current_user.role != 'student':
        flash('学生のみがグループに参加できます。')
        return redirect(url_for('view_group', group_id=group_id))
    
    # グループを取得
    group = Group.query.get_or_404(group_id)
    
    # 学生がそのクラスに所属しているか確認
    enrolled_class_ids = [c.id for c in current_user.enrolled_classes]
    if group.class_id not in enrolled_class_ids:
        flash('このグループに参加する権限がありません。')
        return redirect(url_for('student_dashboard'))
    
    # 既にメンバーでないことを確認
    existing_membership = GroupMembership.query.filter_by(
        group_id=group_id, student_id=current_user.id).first()
    
    if existing_membership:
        flash('あなたは既にこのグループのメンバーです。')
        return redirect(url_for('view_group', group_id=group_id))
    
    # グループに参加
    membership = GroupMembership(
        group_id=group_id,
        student_id=current_user.id
    )
    
    db.session.add(membership)
    db.session.commit()
    
    flash('グループに参加しました。')
    return redirect(url_for('view_group', group_id=group_id))

# グループから脱退
@app.route('/group/<int:group_id>/leave')
@login_required
def leave_group(group_id):
    if current_user.role != 'student':
        flash('学生のみがグループから脱退できます。')
        return redirect(url_for('view_group', group_id=group_id))
    
    # グループを取得
    group = Group.query.get_or_404(group_id)
    
    # メンバーシップを取得
    membership = GroupMembership.query.filter_by(
        group_id=group_id, student_id=current_user.id).first_or_404()
    
    # グループ作成者は脱退できない
    if group.created_by == current_user.id:
        flash('あなたはこのグループの作成者であるため、脱退できません。')
        return redirect(url_for('view_group', group_id=group_id))
    
    # グループから脱退
    db.session.delete(membership)
    db.session.commit()
    
    flash('グループから脱退しました。')
    return redirect(url_for('view_groups', class_id=group.class_id))

# メンバーをグループから削除（教師またはグループ作成者のみ）
@app.route('/group/<int:group_id>/remove_member/<int:student_id>')
@login_required
def remove_group_member(group_id, student_id):
    # グループを取得
    group = Group.query.get_or_404(group_id)
    
    # 権限チェック
    if current_user.role == 'teacher' and Class.query.get(group.class_id).teacher_id != current_user.id:
        flash('このグループから学生を削除する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    if current_user.role == 'student' and group.created_by != current_user.id:
        flash('このグループから学生を削除する権限がありません。')
        return redirect(url_for('view_group', group_id=group_id))
    
    # グループ作成者は削除できない
    if student_id == group.created_by:
        flash('グループ作成者をグループから削除することはできません。')
        return redirect(url_for('view_group', group_id=group_id))
    
    # メンバーシップを取得
    membership = GroupMembership.query.filter_by(
        group_id=group_id, student_id=student_id).first_or_404()
    
    # グループからメンバーを削除
    db.session.delete(membership)
    db.session.commit()
    
    flash('メンバーをグループから削除しました。')
    return redirect(url_for('view_group', group_id=group_id))

@app.route('/class/<int:class_id>/remove_student/<int:student_id>', methods=['POST'])
@login_required
def remove_student(class_id, student_id):
    # 教師のみアクセス可能
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    # クラスオブジェクトを取得
    class_obj = Class.query.get_or_404(class_id)
    
    # 教師がクラスの所有者でない場合はアクセス制限
    if class_obj.teacher_id != current_user.id:
        flash('このクラスの学生を削除する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    # 学生をクラスから削除
    enrollment = ClassEnrollment.query.filter_by(
        class_id=class_id,
        student_id=student_id
    ).first_or_404()
    
    db.session.delete(enrollment)
    db.session.commit()
    
    flash('学生がクラスから削除されました。')
    return redirect(url_for('view_class', class_id=class_id))

# CSVからユーザーを一括インポートするルート
@app.route('/admin/import_users', methods=['GET', 'POST'])
@login_required
def import_users():
    # 教師のみアクセス可能
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('CSVファイルが選択されていません。')
            return redirect(request.url)
        
        file = request.files['csv_file']
        
        if file.filename == '':
            flash('CSVファイルが選択されていません。')
            return redirect(request.url)
        
        if file and allowed_csv_file(file.filename):
            try:
                # CSVファイルを読み込む
                stream = io.StringIO(file.stream.read().decode('utf-8'))
                csv_reader = csv.DictReader(stream)
                
                # 成功と失敗のカウンター
                success_count = 0
                error_count = 0
                error_messages = []
                
                # CSVの各行を処理
                for row in csv_reader:
                    try:
                        # 必須項目の確認
                        if not row.get('username') or not row.get('email') or not row.get('role'):
                            error_count += 1
                            error_messages.append(f"行: {csv_reader.line_num} - ユーザー名、メールアドレス、ロールは必須です。")
                            continue
                        
                        # 既存ユーザーのチェック
                        existing_user = User.query.filter(
                            (User.username == row['username']) | (User.email == row['email'])
                        ).first()
                        
                        if existing_user:
                            error_count += 1
                            error_messages.append(f"行: {csv_reader.line_num} - ユーザー名またはメールアドレスが既に使用されています: {row['username']}, {row['email']}")
                            continue
                        
                        # パスワードの生成または取得
                        password = row.get('password')
                        if not password:
                            # パスワードが指定されていない場合はランダムなパスワードを生成
                            password = generate_random_password()
                        
                        # ユーザー作成
                        new_user = User(
                            username=row['username'],
                            email=row['email'],
                            password=generate_password_hash(password),
                            role=row['role']
                        )
                        
                        db.session.add(new_user)
                        success_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        error_messages.append(f"行: {csv_reader.line_num} - エラー: {str(e)}")
                
                # 変更をコミット
                db.session.commit()
                
                # 結果の表示
                if success_count > 0:
                    flash(f'{success_count}人のユーザーを正常にインポートしました。')
                
                if error_count > 0:
                    flash(f'{error_count}件のエラーが発生しました。')
                    for msg in error_messages:
                        flash(msg, 'error')
                
                return redirect(url_for('admin_users'))
                
            except Exception as e:
                flash(f'CSVファイルの処理中にエラーが発生しました: {str(e)}')
                return redirect(request.url)
        else:
            flash('CSVファイルの形式が正しくありません。')
            return redirect(request.url)
    
    return render_template('admin/import_users.html')

# CSVファイルの拡張子チェック用関数
def allowed_csv_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'

# ランダムなパスワード生成関数
def generate_random_password(length=10):
    characters = string.ascii_letters + string.digits + '!@#$%^&*()'
    return ''.join(random.choice(characters) for _ in range(length))

def parse_curriculum_csv(csv_content):
    """
    カリキュラムCSVの内容を解析してデータ構造に変換する
    
    Args:
        csv_content: CSVの内容（文字列）
        
    Returns:
        dict: カリキュラムデータ（フェーズとルーブリックを含む）
    """
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)
    
    # カリキュラムデータの初期化
    curriculum_data = {
        "phases": [],
        "rubric_suggestion": []
    }
    
    # フェーズとルーブリックの区切りを見つける
    rubric_start_idx = None
    for i, row in enumerate(rows):
        if len(row) > 0 and "ルーブリック評価項目" in row[0]:
            rubric_start_idx = i
            break
    
    # フェーズと週の情報を解析
    current_phase = None
    phase_index = -1
    
    if rubric_start_idx is None:
        curriculum_rows = rows[1:]  # ヘッダー行をスキップ
    else:
        curriculum_rows = rows[1:rubric_start_idx]  # ヘッダー行からルーブリック開始行の前までをカリキュラムと見なす
    
    for row in curriculum_rows:
        if len(row) < 7 or not any(row):  # 空行や不正な行はスキップ
            continue
        
        phase_name = row[0].strip()
        week = row[1].strip()
        hours_str = row[2].strip()
        theme = row[3].strip()
        activities = row[4].strip()
        teacher_support = row[5].strip()
        evaluation = row[6].strip()
        
        # 新しいフェーズの開始
        if phase_name:
            if current_phase != phase_name:
                current_phase = phase_name
                phase_index += 1
                curriculum_data["phases"].append({
                    "phase": current_phase,
                    "weeks": []
                })
        
        # 時間数を整数に変換（数値でない場合は2とする）
        try:
            hours = int(hours_str)
        except (ValueError, TypeError):
            hours = 2
        
        # 週の情報を追加
        if phase_index >= 0 and week:
            week_data = {
                "week": week,
                "hours": hours,
                "theme": theme,
                "activities": activities,
                "teacher_support": teacher_support,
                "evaluation": evaluation
            }
            curriculum_data["phases"][phase_index]["weeks"].append(week_data)
    
    # ルーブリック情報を解析
    if rubric_start_idx is not None and rubric_start_idx + 2 < len(rows):
        # カテゴリごとにルーブリックをグループ化
        rubric_categories = {}
        
        for row in rows[rubric_start_idx + 2:]:  # ヘッダー行をスキップ
            if len(row) < 4 or not any(row):  # 空行や不正な行はスキップ
                continue
            
            category = row[0].strip()
            description = row[1].strip()
            level = row[2].strip()
            level_description = row[3].strip()
            
            if not category or not level:
                continue
            
            if category not in rubric_categories:
                rubric_categories[category] = {
                    "category": category,
                    "description": description,
                    "levels": []
                }
            
            # 同じカテゴリでも説明が埋まっていない場合は更新
            if not rubric_categories[category]["description"] and description:
                rubric_categories[category]["description"] = description
            
            # レベルを追加
            rubric_categories[category]["levels"].append({
                "level": level,
                "description": level_description
            })
        
        # カテゴリごとのルーブリックをリストに変換
        curriculum_data["rubric_suggestion"] = list(rubric_categories.values())
    
    return curriculum_data

# CSVテンプレートダウンロード用ルート
@app.route('/admin/download_user_template')
@login_required
def download_user_template():
    # 教師のみアクセス可能
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    # CSVテンプレートの内容を作成
    template_content = "username,email,password,role\n"
    template_content += "student1,student1@example.com,password123,student\n"
    template_content += "teacher1,teacher1@example.com,secure456,teacher\n"
    
    # レスポンスを作成
    response = Response(
        template_content,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=user_template.csv"}
    )
    
    return response

# カリキュラム一覧表示
@app.route('/class/<int:class_id>/curriculums')
@login_required
def view_curriculums(class_id):
    # 教師のみアクセス可能
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    # クラスを取得
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスのカリキュラムを閲覧する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    # クラスのカリキュラムを取得
    curriculums = Curriculum.query.filter_by(class_id=class_id).all()
    
    return render_template('curriculums.html', 
                          class_obj=class_obj, 
                          curriculums=curriculums)

# カリキュラム作成フォーム表示
@app.route('/class/<int:class_id>/curriculum/create', methods=['GET'])
@login_required
def create_curriculum_form(class_id):
    # 教師のみアクセス可能
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    # クラスを取得
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスのカリキュラムを作成する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    # クラスに関連付けられた大テーマを取得
    main_themes = MainTheme.query.filter_by(class_id=class_id).all()
    
    return render_template('create_curriculum.html', 
                          class_obj=class_obj,
                          main_themes=main_themes)

@app.route('/class/<int:class_id>/curriculum/import', methods=['GET', 'POST'])
@login_required
def import_curriculum(class_id):
    # 教師のみアクセス可能
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    # クラスを取得
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスのカリキュラムを作成する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    if request.method == 'POST':
        # フォームからデータを取得
        title = request.form.get('title')
        description = request.form.get('description', '')
        total_hours = int(request.form.get('total_hours', 35))
        has_fieldwork = 'has_fieldwork' in request.form
        fieldwork_count = int(request.form.get('fieldwork_count', 0)) if has_fieldwork else 0
        has_presentation = 'has_presentation' in request.form
        presentation_format = request.form.get('presentation_format', 'プレゼンテーション')
        group_work_level = request.form.get('group_work_level', 'ハイブリッド')
        external_collaboration = 'external_collaboration' in request.form
        
        # 入力チェック
        if not title:
            flash('タイトルは必須項目です。')
            return redirect(request.url)
        
        # CSVファイルのチェック
        if 'csv_file' not in request.files:
            flash('CSVファイルが選択されていません。')
            return redirect(request.url)
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('CSVファイルが選択されていません。')
            return redirect(request.url)
        
        if file and allowed_csv_file(file.filename):
            try:
                # CSVファイルを読み込む
                # BOMを考慮してデコード
                content = file.read().decode('utf-8-sig')
                csv_data = parse_curriculum_csv(content)
                
                # カリキュラムデータをJSONとして保存
                content_json = json.dumps(csv_data, ensure_ascii=False)
                
                # データベースに保存
                new_curriculum = Curriculum(
                    class_id=class_id,
                    teacher_id=current_user.id,
                    title=title,
                    description=description,
                    total_hours=total_hours,
                    has_fieldwork=has_fieldwork,
                    fieldwork_count=fieldwork_count,
                    has_presentation=has_presentation,
                    presentation_format=presentation_format,
                    group_work_level=group_work_level,
                    external_collaboration=external_collaboration,
                    content=content_json
                )
                
                db.session.add(new_curriculum)
                db.session.commit()
                
                flash('カリキュラムがインポートされました。')
                return redirect(url_for('view_curriculum', curriculum_id=new_curriculum.id))
                
            except Exception as e:
                flash(f'CSVファイルの処理中にエラーが発生しました: {str(e)}')
                print(f"エラー詳細: {str(e)}")
                return redirect(request.url)
        else:
            flash('CSVファイルの形式が正しくありません。')
            return redirect(request.url)
    
    return render_template('upload_curriculum.html', class_obj=class_obj)
# カリキュラムAI生成処理
@app.route('/class/<int:class_id>/curriculum/generate', methods=['POST'])
@login_required
def generate_curriculum(class_id):
    # 教師のみアクセス可能
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    # クラスを取得
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスのカリキュラムを作成する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    # フォームからデータを取得
    title = request.form.get('title')
    description = request.form.get('description', '')
    main_theme_id = request.form.get('main_theme_id')
    total_hours = int(request.form.get('total_hours', 35))
    has_fieldwork = 'has_fieldwork' in request.form
    fieldwork_count = int(request.form.get('fieldwork_count', 0)) if has_fieldwork else 0
    has_presentation = 'has_presentation' in request.form
    presentation_format = request.form.get('presentation_format', 'プレゼンテーション')
    group_work_level = request.form.get('group_work_level', 'ハイブリッド')
    external_collaboration = 'external_collaboration' in request.form
    
    # 入力チェック
    if not title:
        flash('タイトルは必須項目です。')
        return redirect(url_for('create_curriculum_form', class_id=class_id))
    
    # 大テーマの情報を取得
    main_theme = None
    main_theme_title = ''
    main_theme_description = ''
    
    if main_theme_id:
        main_theme = MainTheme.query.get(main_theme_id)
        if main_theme:
            main_theme_title = main_theme.title
            main_theme_description = main_theme.description
    
    # クラス情報の構築
    class_details = {
        'name': class_obj.name,
        'main_theme': main_theme_title,
        'main_theme_description': main_theme_description
    }
    
    # カリキュラム設定の構築
    curriculum_settings = {
        'total_hours': total_hours,
        'has_fieldwork': has_fieldwork,
        'fieldwork_count': fieldwork_count,
        'has_presentation': has_presentation,
        'presentation_format': presentation_format,
        'group_work_level': group_work_level,
        'external_collaboration': external_collaboration
    }
    
    try:
        # AIを使ってカリキュラムを生成
        from ai_curriculum_helpers import generate_curriculum_with_ai
        
        curriculum_data = generate_curriculum_with_ai(class_details, curriculum_settings)
        
        # カリキュラムデータをJSONとして保存
        content_json = json.dumps(curriculum_data, ensure_ascii=False)
        
        # データベースに保存
        new_curriculum = Curriculum(
            class_id=class_id,
            teacher_id=current_user.id,
            title=title,
            description=description,
            total_hours=total_hours,
            has_fieldwork=has_fieldwork,
            fieldwork_count=fieldwork_count,
            has_presentation=has_presentation,
            presentation_format=presentation_format,
            group_work_level=group_work_level,
            external_collaboration=external_collaboration,
            content=content_json
        )
        
        db.session.add(new_curriculum)
        db.session.commit()
        
        flash('カリキュラムが正常に生成されました。')
        return redirect(url_for('view_curriculum', curriculum_id=new_curriculum.id))
        
    except Exception as e:
        flash(f'カリキュラム生成中にエラーが発生しました: {str(e)}')
        return redirect(url_for('create_curriculum_form', class_id=class_id))

# カリキュラム表示
@app.route('/curriculum/<int:curriculum_id>')
@login_required
def view_curriculum(curriculum_id):
    # カリキュラムを取得
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # クラスを取得
    class_obj = Class.query.get_or_404(curriculum.class_id)
    
    # 権限チェック
    if current_user.role == 'teacher' and class_obj.teacher_id != current_user.id:
        flash('このカリキュラムを閲覧する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    if current_user.role == 'student':
        enrolled_class_ids = [c.id for c in current_user.enrolled_classes]
        if class_obj.id not in enrolled_class_ids:
            flash('このカリキュラムを閲覧する権限がありません。')
            return redirect(url_for('student_dashboard'))
    
    # カリキュラム内容をJSONから解析
    curriculum_data = json.loads(curriculum.content)
    
    return render_template('view_curriculum.html', 
                          curriculum=curriculum,
                          class_obj=class_obj,
                          curriculum_data=curriculum_data)

# カリキュラム編集
@app.route('/curriculum/<int:curriculum_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_curriculum(curriculum_id):
    # 教師のみアクセス可能
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    # カリキュラムを取得
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # クラスを取得
    class_obj = Class.query.get_or_404(curriculum.class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このカリキュラムを編集する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    if request.method == 'POST':
        # 基本情報の更新
        curriculum.title = request.form.get('title')
        curriculum.description = request.form.get('description', '')
        curriculum.total_hours = int(request.form.get('total_hours', 35))
        curriculum.has_fieldwork = 'has_fieldwork' in request.form
        curriculum.fieldwork_count = int(request.form.get('fieldwork_count', 0))
        curriculum.has_presentation = 'has_presentation' in request.form
        curriculum.presentation_format = request.form.get('presentation_format', '')
        curriculum.group_work_level = request.form.get('group_work_level', '')
        curriculum.external_collaboration = 'external_collaboration' in request.form
        
        # カリキュラム内容の更新
        content_data = json.loads(curriculum.content)
        
        # フェーズ情報の更新
        phases = []
        phase_count = int(request.form.get('phase_count', 0))
        
        for p in range(phase_count):
            phase_name = request.form.get(f'phase_{p}_name', '')
            week_count = int(request.form.get(f'phase_{p}_week_count', 0))
            
            weeks = []
            for w in range(week_count):
                week = {
                    'week': request.form.get(f'phase_{p}_week_{w}_number', ''),
                    'hours': int(request.form.get(f'phase_{p}_week_{w}_hours', 0)),
                    'theme': request.form.get(f'phase_{p}_week_{w}_theme', ''),
                    'activities': request.form.get(f'phase_{p}_week_{w}_activities', ''),
                    'teacher_support': request.form.get(f'phase_{p}_week_{w}_support', ''),
                    'evaluation': request.form.get(f'phase_{p}_week_{w}_evaluation', '')
                }
                weeks.append(week)
            
            phase = {
                'phase': phase_name,
                'weeks': weeks
            }
            phases.append(phase)
        
        # ルーブリック情報の更新
        rubrics = []
        rubric_count = int(request.form.get('rubric_count', 0))
        
        for r in range(rubric_count):
            category = request.form.get(f'rubric_{r}_category', '')
            description = request.form.get(f'rubric_{r}_description', '')
            level_count = int(request.form.get(f'rubric_{r}_level_count', 0))
            
            levels = []
            for l in range(level_count):
                level = {
                    'level': request.form.get(f'rubric_{r}_level_{l}_name', ''),
                    'description': request.form.get(f'rubric_{r}_level_{l}_description', '')
                }
                levels.append(level)
            
            rubric = {
                'category': category,
                'description': description,
                'levels': levels
            }
            rubrics.append(rubric)
        
        # 更新されたカリキュラムデータを作成
        updated_content = {
            'phases': phases,
            'rubric_suggestion': rubrics
        }
        
        # JSONとして保存
        curriculum.content = json.dumps(updated_content, ensure_ascii=False)
        
        db.session.commit()
        flash('カリキュラムが更新されました。')
        return redirect(url_for('view_curriculum', curriculum_id=curriculum_id))
    
    # カリキュラム内容をJSONから解析
    curriculum_data = json.loads(curriculum.content)
    
    return render_template('edit_curriculum.html', 
                          curriculum=curriculum,
                          class_obj=class_obj,
                          curriculum_data=curriculum_data)

# カリキュラム削除
@app.route('/curriculum/<int:curriculum_id>/delete')
@login_required
def delete_curriculum(curriculum_id):
    # 教師のみアクセス可能
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    # カリキュラムを取得
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if curriculum.teacher_id != current_user.id:
        flash('このカリキュラムを削除する権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    # クラスIDを保存（削除後のリダイレクト用）
    class_id = curriculum.class_id
    
    # カリキュラムを削除
    db.session.delete(curriculum)
    db.session.commit()
    
    flash('カリキュラムが削除されました。')
    return redirect(url_for('view_curriculums', class_id=class_id))

# カリキュラムCSVエクスポート
@app.route('/curriculum/<int:curriculum_id>/export')
@login_required
def export_curriculum(curriculum_id):
    # カリキュラムを取得
    curriculum = Curriculum.query.get_or_404(curriculum_id)
    
    # 権限チェック
    if current_user.role == 'teacher' and curriculum.teacher_id != current_user.id:
        flash('このカリキュラムをエクスポートする権限がありません。')
        return redirect(url_for('teacher_dashboard'))
    
    # カリキュラム内容をJSONから解析
    curriculum_data = json.loads(curriculum.content)
    
    # CSVに変換
    from ai_curriculum_helpers import generate_curriculum_csv
    csv_content = generate_curriculum_csv(curriculum_data)
    
    # BOMを追加して文字化けを防止
    csv_content_with_bom = '\ufeff' + csv_content

    # レスポンスを作成
    response = Response(
        csv_content_with_bom,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=curriculum_{curriculum_id}.csv",}
    )
    
    return response

@app.route('/curriculum/download_template')
@login_required
def download_curriculum_template():
    # 教師のみアクセス可能
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    # テンプレート内容を作成
    template_content = '\ufeff'  # BOMを追加
    template_content += "フェーズ,週,時間数,テーマ,活動内容,教師のサポート,評価方法\n"
    template_content += "準備期,第1週,2,オリエンテーション,探究学習の全体像の理解、グループ分け,学習目標と評価基準の説明,活動記録の確認\n"
    template_content += "準備期,第2週,2,テーマ探索,関心のある分野についてのブレインストーミング,発想法の紹介、資料提供,アイデアの多様性\n"
    template_content += ",,,,,,,\n"  # 空行
    template_content += "ルーブリック評価項目,,,,,,,\n"
    template_content += "カテゴリ,説明,レベル,達成基準,,,,\n"
    template_content += "問いの設定,探究の問いを設定する力,S,独創的で深い問いを設定できる,,,,\n"
    template_content += "問いの設定,探究の問いを設定する力,A,適切な問いを設定できる,,,,\n"
    template_content += "問いの設定,探究の問いを設定する力,B,基本的な問いを設定できる,,,,\n"
    
    # レスポンスを作成
    response = Response(
        template_content,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-disposition": "attachment; filename=curriculum_template.csv"}
    )
    
    return response

# アプリケーション起動時のみ実行される部分
if __name__ == '__main__':
    # BaseBuilder機能の初期化
    try:
        from basebuilder import init_app
        init_app(app)
        print("BaseBuilder機能が正常に初期化されました。")
    except ImportError:
        print("BaseBuilderモジュールを読み込めませんでした。機能は無効化されています。")
    except Exception as e:
        print(f"BaseBuilder初期化エラー: {str(e)}")
    
    app.run(debug=True)

@app.route('/admin/schools')
@login_required
def admin_schools():
    # 管理者権限チェック
    if current_user.role != 'admin':
        flash('この機能は管理者のみ利用可能です。')
        return redirect(url_for('index'))
    
    schools = School.query.all()
    return render_template('admin/schools.html', schools=schools)

@app.route('/admin/schools/create', methods=['GET', 'POST'])
@login_required
def create_school():
    # 管理者権限チェック
    if current_user.role != 'admin':
        flash('この機能は管理者のみ利用可能です。')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address', '')
        contact_email = request.form.get('contact_email', '')
        
        if not name:
            flash('学校名は必須です。')
            return render_template('admin/create_school.html')
        
        # ランダムなコードを生成
        import random
        import string
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        # 新しい学校を作成
        new_school = School(
            name=name,
            code=code,
            address=address,
            contact_email=contact_email
        )
        db.session.add(new_school)
        db.session.commit()
        
        flash(f'学校が作成されました。学校コード: {code}')
        return redirect(url_for('admin_schools'))
    
    return render_template('admin/create_school.html')

@app.route('/admin/schools/<int:school_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_school(school_id):
    # 管理者権限チェック
    if current_user.role != 'admin':
        flash('この機能は管理者のみ利用可能です。')
        return redirect(url_for('index'))
    
    school = School.query.get_or_404(school_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address', '')
        contact_email = request.form.get('contact_email', '')
        code = request.form.get('code')
        
        if not name or not code:
            flash('学校名と学校コードは必須です。')
            return render_template('admin/edit_school.html', school=school)
        
        # 既存のコードとの重複チェック
        existing_school = School.query.filter(School.code == code, School.id != school_id).first()
        if existing_school:
            flash('この学校コードは既に使用されています。')
            return render_template('admin/edit_school.html', school=school)
        
        # 学校情報を更新
        school.name = name
        school.code = code
        school.address = address
        school.contact_email = contact_email
        
        db.session.commit()
        
        flash('学校情報が更新されました。')
        return redirect(url_for('admin_schools'))
    
    return render_template('admin/edit_school.html', school=school)

@app.route('/admin/schools/<int:school_id>/delete', methods=['POST'])
@login_required
def delete_school(school_id):
    # 管理者権限チェック
    if not current_user.is_admin and current_user.role != 'admin':
        flash('この機能は管理者のみ利用可能です。')
        return redirect(url_for('index'))
    
    school = School.query.get_or_404(school_id)
    
    # ユーザーが所属している場合は削除不可
    if User.query.filter_by(school_id=school_id).first():
        flash('この学校にはユーザーが所属しているため削除できません。')
        return redirect(url_for('admin_schools'))
    
    # 関連するデータを確認
    resources = []
    resources.append(f'クラス: {Class.query.filter_by(school_id=school_id).count()}件')
    resources.append(f'カテゴリ: {ProblemCategory.query.filter_by(school_id=school_id).count()}件')
    resources.append(f'テキスト: {TextSet.query.filter_by(school_id=school_id).count()}件')
    
    # 削除確認画面を表示
    if 'confirm' not in request.form:
        return render_template(
            'admin/confirm_delete_school.html',
            school=school,
            resources=resources
        )
    
    # 学校を削除
    db.session.delete(school)
    db.session.commit()
    
    flash(f'学校「{school.name}」を削除しました。')
    return redirect(url_for('admin_schools'))

@app.route('/admin_access')
@login_required
def admin_access():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        return f"あなたは管理者ではありません。現在のロール: {current_user.role}, ID: {current_user.id}"

@app.route('/api/teacher/first_class')
@login_required
def api_teacher_first_class():
    """教師の最初のクラスIDを返すAPI"""
    if current_user.role != 'teacher':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # 教師の最初のクラスを取得
    first_class = Class.query.filter_by(teacher_id=current_user.id).first()
    if first_class:
        return jsonify({'class_id': first_class.id})
    else:
        return jsonify({'class_id': None})