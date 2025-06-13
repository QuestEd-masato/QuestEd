import pytest
from app.models import User, School, Class
from app import db

class TestUserModel:
    """ユーザーモデルのテスト"""
    
    def test_password_hashing(self, app):
        """パスワードハッシュ化のテスト"""
        with app.app_context():
            user = User(email='test@example.com')
            user.set_password('password123')
            
            assert user.password_hash is not None
            assert user.password_hash != 'password123'
            assert user.check_password('password123') is True
            assert user.check_password('wrongpassword') is False
    
    def test_user_creation(self, app, sample_school):
        """ユーザー作成のテスト"""
        with app.app_context():
            user = User(
                email='new@example.com',
                role='student',
                full_name='新規ユーザー',
                school_id=sample_school.id
            )
            db.session.add(user)
            db.session.commit()
            
            assert user.id is not None
            assert user.email == 'new@example.com'
            assert user.role == 'student'
            assert user.school_id == sample_school.id
    
    def test_user_roles(self, app):
        """ロール検証のテスト"""
        with app.app_context():
            admin = User(email='admin@test.com', role='admin')
            teacher = User(email='teacher@test.com', role='teacher')
            student = User(email='student@test.com', role='student')
            
            assert admin.is_admin() is True
            assert teacher.is_teacher() is True
            assert student.is_student() is True
            
            assert admin.is_teacher() is False
            assert teacher.is_student() is False
            assert student.is_admin() is False

class TestSchoolModel:
    """学校モデルのテスト"""
    
    def test_school_creation(self, app):
        """学校作成のテスト"""
        with app.app_context():
            school = School(
                name='テスト高校',
                school_code='TEST002',
                address='東京都渋谷区',
                contact_email='contact@test-school.jp'
            )
            db.session.add(school)
            db.session.commit()
            
            assert school.id is not None
            assert school.name == 'テスト高校'
            assert school.school_code == 'TEST002'
    
    def test_school_user_relationship(self, app, sample_school, sample_users):
        """学校とユーザーの関係テスト"""
        with app.app_context():
            # 学校に所属するユーザーを確認
            users = User.query.filter_by(school_id=sample_school.id).all()
            assert len(users) == 3  # admin, teacher, student
            
            # 各ユーザーの学校情報を確認
            for user in users:
                assert user.school.name == sample_school.name