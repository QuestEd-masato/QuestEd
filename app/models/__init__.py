# app/models/__init__.py
from flask_login import UserMixin
from datetime import datetime
from extensions import db

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
    # メール認証・承認関連フィールド
    email_confirmed = db.Column(db.Boolean, default=False)
    email_token = db.Column(db.String(100), nullable=True)
    token_created_at = db.Column(db.DateTime, nullable=True)
    is_approved = db.Column(db.Boolean, default=False)
    
    # パスワードリセット関連フィールド
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_created_at = db.Column(db.DateTime, nullable=True)

    # リレーションシップの定義（カスケード削除を設定）
    classes_teaching = db.relationship('Class', backref='teacher', lazy=True, cascade='all, delete-orphan')
    interest_surveys = db.relationship('InterestSurvey', backref='student', lazy=True, cascade='all, delete-orphan')
    personality_surveys = db.relationship('PersonalitySurvey', backref='student', lazy=True, cascade='all, delete-orphan')
    inquiry_themes = db.relationship('InquiryTheme', backref='student', lazy=True, cascade='all, delete-orphan')
    activity_logs = db.relationship('ActivityLog', backref='student', lazy=True, cascade='all, delete-orphan')
    todos = db.relationship('Todo', backref='student', lazy=True, cascade='all, delete-orphan')
    goals = db.relationship('Goal', backref='student', lazy=True, cascade='all, delete-orphan')
    student_evaluations = db.relationship('StudentEvaluation', foreign_keys='StudentEvaluation.student_id', back_populates='student', lazy=True, cascade='all, delete-orphan')
    chat_histories = db.relationship('ChatHistory', back_populates='user', lazy=True, cascade='all, delete-orphan')
  
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

# 学校管理のモデル定義
class School(db.Model):
    __tablename__ = 'schools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=True)  # 学校コード
    address = db.Column(db.Text)
    contact_email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # リレーションシップの定義
    years = db.relationship('SchoolYear', backref='school', lazy=True)
    users = db.relationship('User', backref='school', lazy=True)
    classes = db.relationship('Class', backref='school', lazy=True)
    
    # BaseBuilderモジュールとの関係は動的に追加される

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
    teacher = db.relationship('User', backref=db.backref('class_groups_teaching', lazy=True, cascade='all, delete-orphan'))

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
    student = db.relationship('User', backref=db.backref('student_enrollments', lazy=True, cascade='all, delete-orphan'))
    school_year = db.relationship('SchoolYear', backref='student_enrollments', lazy=True)

# クラスモデル定義
class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True)
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
    is_active = db.Column(db.Boolean, default=True)
    
    # リレーションシップ
    student = db.relationship('User', foreign_keys=[student_id], backref=db.backref('class_enrollments', cascade='all, delete-orphan'))
    class_obj = db.relationship('Class', foreign_keys=[class_id], backref='enrollments')
    
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
    teacher = db.relationship('User', backref=db.backref('main_themes', lazy=True, cascade='all, delete-orphan'))
    class_obj = db.relationship('Class', backref=db.backref('main_themes', lazy=True))
    
    # このメインテーマに関連する個人テーマ
    personal_themes = db.relationship('InquiryTheme', backref='main_theme', lazy=True)

class InquiryTheme(db.Model):
    __tablename__ = 'inquiry_themes'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True)  # 追加
    main_theme_id = db.Column(db.Integer, db.ForeignKey('main_themes.id'), nullable=True)
    is_ai_generated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    title = db.Column(db.String(200))
    question = db.Column(db.Text)
    description = db.Column(db.Text)
    rationale = db.Column(db.Text)
    approach = db.Column(db.Text)
    potential = db.Column(db.Text)
    is_selected = db.Column(db.Boolean, default=False)
    
    # リレーションシップを追加
    class_obj = db.relationship('Class', backref=db.backref('inquiry_themes', lazy=True))

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
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True)  # 追加
    title = db.Column(db.String(200))
    date = db.Column(db.Date, default=datetime.utcnow().date())
    content = db.Column(db.Text)
    reflection = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    activity = db.Column(db.Text)  # 既存のフィールドを残す
    tags = db.Column(db.String(255))  # 新しいタグフィールドを追加
    
    # リレーションシップを追加
    class_obj = db.relationship('Class', backref=db.backref('activity_logs', lazy=True))

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
    student = db.relationship('User', back_populates='student_evaluations')
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
    teacher = db.relationship('User', backref=db.backref('created_curriculums', lazy=True, cascade='all, delete-orphan'))

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
    teacher = db.relationship('User', backref=db.backref('created_rubrics', lazy=True, cascade='all, delete-orphan'))

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
    creator = db.relationship('User', backref=db.backref('created_groups', lazy=True, cascade='all, delete-orphan'))
    members = db.relationship('User', secondary='group_memberships',
                             backref=db.backref('joined_groups', lazy='dynamic', cascade='all, delete'))

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
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    is_user = db.Column(db.Boolean, default=True)  # True=ユーザー, False=AI
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # userリレーションシップは1つだけにする
    user = db.relationship('User', back_populates='chat_histories')
    class_obj = db.relationship('Class', backref=db.backref('chat_histories', lazy=True))

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

# Import Subject model
from app.models.subject import Subject

# Export all models
__all__ = [
    'db', 'User', 'School', 'SchoolYear', 'ClassGroup', 'StudentEnrollment',
    'Class', 'ClassEnrollment', 'MainTheme', 'InquiryTheme', 'InterestSurvey',
    'PersonalitySurvey', 'ActivityLog', 'Todo', 'Goal', 'StudentEvaluation',
    'Curriculum', 'RubricTemplate', 'Group', 'GroupMembership', 'ChatHistory',
    'Milestone', 'Subject'
]