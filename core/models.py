# core/models.py
from app import db
from datetime import datetime

class School(db.Model):
    __tablename__ = 'schools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.Text)
    contact_email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # リレーションシップ
    years = db.relationship('SchoolYear', backref='school', lazy=True)
    users = db.relationship('User', backref='school', lazy=True)

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
    student = db.relationship('User', backref='enrollments', lazy=True)
    school_year = db.relationship('SchoolYear', backref='enrollments', lazy=True)