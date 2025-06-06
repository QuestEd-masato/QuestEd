# basebuilder/models.py
from datetime import datetime
from extensions import db

# 問題カテゴリモデル → 単語カテゴリモデルに変更
class ProblemCategory(db.Model):
    __tablename__ = 'problem_categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('problem_categories.id'), nullable=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # リレーションシップ - 文字列参照を使用
    problems = db.relationship('BasicKnowledgeItem', backref='category', lazy=True)
    subcategories = db.relationship('ProblemCategory', backref=db.backref('parent', remote_side=[id]))
    creator = db.relationship('User', backref=db.backref('created_categories', lazy=True, cascade='all, delete-orphan'))
    text_sets = db.relationship('TextSet', backref='category', lazy=True)
    # school_ref = db.relationship('School', back_populates='problem_categories', lazy=True)
    
# テキスト配信モデル
class TextDelivery(db.Model):
    __tablename__ = 'text_deliveries'
    id = db.Column(db.Integer, primary_key=True)
    text_set_id = db.Column(db.Integer, db.ForeignKey('text_sets.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    delivered_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    delivered_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.Date, nullable=True)
    
    # リレーションシップ - 文字列参照を使用
    deliverer = db.relationship('User', backref=db.backref('delivered_texts', cascade='all, delete-orphan'))
    # Classとのリレーションシップを文字列で参照して循環インポートを回避
    delivered_class = db.relationship('Class', backref='text_deliveries')
    text_set = db.relationship('TextSet', backref='deliveries')

# 基礎知識問題モデル → 単語モデルに変更
class BasicKnowledgeItem(db.Model):
    __tablename__ = 'basic_knowledge_items'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('problem_categories.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)  # 単語
    question = db.Column(db.Text, nullable=False)      # 意味
    answer_type = db.Column(db.String(20), nullable=False, default='text')
    correct_answer = db.Column(db.Text, nullable=False) # 別の表記など
    choices = db.Column(db.Text)  # 例文をJSONとして保存
    explanation = db.Column(db.Text)  # 発音記号や追加情報
    difficulty = db.Column(db.Integer, default=2)  # 1-5のスケール
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    text_set_id = db.Column(db.Integer, db.ForeignKey('text_sets.id'), nullable=True)
    order_in_text = db.Column(db.Integer, nullable=True)  # テキスト内での順序
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=True)
    
    # リレーションシップ
    creator = db.relationship('User', backref=db.backref('created_problems', lazy=True, cascade='all, delete-orphan'))
    answer_records = db.relationship('AnswerRecord', backref='problem', lazy=True)
    theme_relations = db.relationship('KnowledgeThemeRelation', backref='problem', lazy=True)
    # school_ref = db.relationship('School', back_populates='basic_knowledge_items', lazy=True)

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
    # themeは文字列で参照して循環インポートを回避
    theme = db.relationship('InquiryTheme', backref=db.backref('knowledge_relations', lazy=True))
    creator = db.relationship('User', backref=db.backref('created_relations', lazy=True, cascade='all, delete-orphan'))

# 解答履歴モデル → 単語学習記録モデルに変更
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
    student = db.relationship('User', backref=db.backref('answer_records', lazy=True, cascade='all, delete-orphan'))

# 熟練度記録モデル → 単語熟練度記録モデルに変更
class ProficiencyRecord(db.Model):
    __tablename__ = 'proficiency_records'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('problem_categories.id'), nullable=False)
    level = db.Column(db.Integer, default=0)  # 0-5のスケール → ポイントとして使用
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    review_date = db.Column(db.Date)  # 次回復習日を追加
    last_reviewed = db.Column(db.DateTime, default=datetime.utcnow)  # 最後に復習した日時
    
    # リレーションシップ
    student = db.relationship('User', backref=db.backref('proficiency_records', lazy=True, cascade='all, delete-orphan'))
    category = db.relationship('ProblemCategory', backref=db.backref('proficiency_records', lazy=True))
    
    @property
    def adjusted_proficiency(self):
        """2週間経過で1ポイント減少する定着度を計算"""
        if not self.last_reviewed:
            return self.level
        
        days_passed = (datetime.utcnow() - self.last_reviewed).days
        decay_points = days_passed // 14  # 14日ごとに1ポイント減少
        
        return max(0, self.level - decay_points)
    
    def update_review_date(self):
        """復習日を更新"""
        self.last_reviewed = datetime.utcnow()
        from extensions import db
        db.session.commit()
    
    # ユニーク制約（学生+カテゴリの組み合わせは一意）
    __table_args__ = (db.UniqueConstraint('student_id', 'category_id'),)

# テキスト熟練度記録モデル（新規）
class TextProficiencyRecord(db.Model):
    __tablename__ = 'text_proficiency_records'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    text_set_id = db.Column(db.Integer, db.ForeignKey('text_sets.id'), nullable=False)
    level = db.Column(db.Integer, default=0)  # 0-100のパーセント
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # リレーションシップ
    student = db.relationship('User', backref=db.backref('text_proficiency_records', lazy=True, cascade='all, delete-orphan'))
    text_set = db.relationship('TextSet', backref=db.backref('proficiency_records', lazy=True))
    
    # ユニーク制約（学生+テキストの組み合わせは一意）
    __table_args__ = (db.UniqueConstraint('student_id', 'text_set_id'),)

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
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=True)
    
    # リレーションシップ
    creator = db.relationship('User', backref=db.backref('created_paths', lazy=True, cascade='all, delete-orphan'))
    assignments = db.relationship('PathAssignment', backref='path', lazy=True)
    # school_ref = db.relationship('School', back_populates='learning_paths', lazy=True)
    
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
    student = db.relationship('User', foreign_keys=[student_id], backref=db.backref('assigned_paths', lazy=True, cascade='all, delete-orphan'))
    assigner = db.relationship('User', foreign_keys=[assigned_by], backref=db.backref('assigned_to_others', lazy=True, cascade='all, delete-orphan'))
    
    # ユニーク制約（学生+パスの組み合わせは一意）
    __table_args__ = (db.UniqueConstraint('path_id', 'student_id'),)

# 単語ごとの熟練度モデル
class WordProficiency(db.Model):
    __tablename__ = 'word_proficiency_records'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    problem_id = db.Column(db.Integer, db.ForeignKey('basic_knowledge_items.id'), nullable=False)
    level = db.Column(db.Integer, default=0)  # 0-5のスケール → ポイントとして使用
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    review_date = db.Column(db.Date, default=datetime.now().date())  # 次回復習日
    
    # リレーションシップ
    student = db.relationship('User', backref=db.backref('word_proficiency_records', lazy=True, cascade='all, delete-orphan'))
    problem = db.relationship('BasicKnowledgeItem', backref=db.backref('word_proficiency_records', lazy=True))
    
    # ユニーク制約（学生+問題の組み合わせは一意）
    __table_args__ = (db.UniqueConstraint('student_id', 'problem_id'),)

# テキストセットモデル
class TextSet(db.Model):
    __tablename__ = 'text_sets'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('problem_categories.id'), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # リレーションシップ
    problems = db.relationship('BasicKnowledgeItem', backref='text_set', lazy=True)
    creator = db.relationship('User', backref=db.backref('created_text_sets', lazy=True, cascade='all, delete-orphan'))
    # school_ref = db.relationship('School', back_populates='text_sets', lazy=True)