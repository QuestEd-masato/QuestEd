from datetime import datetime
from app import db

# 問題カテゴリモデル
class ProblemCategory(db.Model):
    __tablename__ = 'problem_categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('problem_categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # リレーションシップ
    problems = db.relationship('BasicKnowledgeItem', backref='category', lazy=True)
    subcategories = db.relationship('ProblemCategory', backref=db.backref('parent', remote_side=[id]))
    creator = db.relationship('User', backref=db.backref('created_categories', lazy=True))

# 基礎知識問題モデル
class BasicKnowledgeItem(db.Model):
    __tablename__ = 'basic_knowledge_items'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('problem_categories.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer_type = db.Column(db.String(20), nullable=False)  # 'multiple_choice', 'text', 'true_false'
    correct_answer = db.Column(db.Text, nullable=False)
    choices = db.Column(db.Text)  # JSONとして選択肢を保存（multiple_choiceの場合）
    explanation = db.Column(db.Text)
    difficulty = db.Column(db.Integer, default=2)  # 1-5のスケール
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # リレーションシップ
    creator = db.relationship('User', backref=db.backref('created_problems', lazy=True))
    answer_records = db.relationship('AnswerRecord', backref='problem', lazy=True)
    theme_relations = db.relationship('KnowledgeThemeRelation', backref='problem', lazy=True)

# 問題と探究テーマの関連付けモデル
class KnowledgeThemeRelation(db.Model):
    __tablename__ = 'knowledge_theme_relations'
    id = db.Column(db.Integer, primary_key=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('basic_knowledge_items.id'), nullable=False)
    theme_id = db.Column(db.Integer, db.ForeignKey('inquiry_themes.id'), nullable=False)
    relevance = db.Column(db.Integer, default=3)  # 1-5のスケール（関連性の強さ）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # リレーションシップ
    theme = db.relationship('InquiryTheme', backref=db.backref('knowledge_relations', lazy=True))
    creator = db.relationship('User', backref=db.backref('created_relations', lazy=True))

# 解答履歴モデル
class AnswerRecord(db.Model):
    __tablename__ = 'answer_records'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    problem_id = db.Column(db.Integer, db.ForeignKey('basic_knowledge_items.id'), nullable=False)
    student_answer = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    answer_time = db.Column(db.Integer)  # 回答にかかった時間（秒）
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # リレーションシップ
    student = db.relationship('User', backref=db.backref('answer_records', lazy=True))

# 熟練度記録モデル
class ProficiencyRecord(db.Model):
    __tablename__ = 'proficiency_records'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('problem_categories.id'), nullable=False)
    level = db.Column(db.Integer, default=0)  # 0-100のスケール
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # リレーションシップ
    student = db.relationship('User', backref=db.backref('proficiency_records', lazy=True))
    category = db.relationship('ProblemCategory', backref=db.backref('proficiency_records', lazy=True))
    
    # ユニーク制約（学生+カテゴリの組み合わせは一意）
    __table_args__ = (db.UniqueConstraint('student_id', 'category_id'),)

# 学習パスモデル
class LearningPath(db.Model):
    __tablename__ = 'learning_paths'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    steps = db.Column(db.Text)  # JSONとして学習ステップを保存
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # リレーションシップ
    creator = db.relationship('User', backref=db.backref('created_paths', lazy=True))
    assignments = db.relationship('PathAssignment', backref='path', lazy=True)

# 学習パス割り当てモデル
class PathAssignment(db.Model):
    __tablename__ = 'path_assignments'
    id = db.Column(db.Integer, primary_key=True)
    path_id = db.Column(db.Integer, db.ForeignKey('learning_paths.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.Date)
    completed = db.Column(db.Boolean, default=False)
    progress = db.Column(db.Integer, default=0)  # 0-100のスケール
    
    # リレーションシップ
    student = db.relationship('User', foreign_keys=[student_id], backref=db.backref('assigned_paths', lazy=True))
    assigner = db.relationship('User', foreign_keys=[assigned_by], backref=db.backref('assigned_to_others', lazy=True))
    
    # ユニーク制約（学生+パスの組み合わせは一意）
    __table_args__ = (db.UniqueConstraint('path_id', 'student_id'),)