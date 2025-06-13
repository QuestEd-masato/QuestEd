import pytest
from app import create_app, db
from app.models import User, School
from config import TestingConfig

@pytest.fixture
def app():
    """テスト用アプリケーションインスタンス"""
    app = create_app(TestingConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """テストクライアント"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """テストランナー"""
    return app.test_cli_runner()

@pytest.fixture
def auth_headers(client):
    """認証済みヘッダー"""
    # テスト用ユーザー作成
    user = User(email='test@example.com', role='teacher')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    
    # ログイン
    response = client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    })
    
    return {'Authorization': f'Bearer {response.json.get("token")}'}

@pytest.fixture
def sample_school():
    """テスト用学校データ"""
    school = School(name='テスト学校', school_code='TEST001')
    db.session.add(school)
    db.session.commit()
    return school

@pytest.fixture
def sample_users(sample_school):
    """テスト用ユーザーデータ"""
    users = []
    
    # 管理者
    admin = User(
        email='admin@test.com',
        role='admin',
        full_name='管理者',
        school_id=sample_school.id,
        is_approved=True,
        email_verified=True
    )
    admin.set_password('admin123')
    users.append(admin)
    
    # 教師
    teacher = User(
        email='teacher@test.com', 
        role='teacher',
        full_name='教師',
        school_id=sample_school.id,
        is_approved=True,
        email_verified=True
    )
    teacher.set_password('teacher123')
    users.append(teacher)
    
    # 生徒
    student = User(
        email='student@test.com',
        role='student', 
        full_name='生徒',
        school_id=sample_school.id,
        is_approved=True,
        email_verified=True
    )
    student.set_password('student123')
    users.append(student)
    
    for user in users:
        db.session.add(user)
    
    db.session.commit()
    return users