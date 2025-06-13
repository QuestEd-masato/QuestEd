# QuestEd 技術仕様書

## 1. システム概要

### 1.1 プロジェクト概要
QuestEd は Flask ベースの教育プラットフォームで、探究型学習を支援する包括的なシステムです。

### 1.2 技術スタック
- **バックエンド**: Python 3.8+, Flask 2.2.3
- **データベース**: MySQL 8.0+
- **フロントエンド**: HTML5, CSS3, JavaScript (ES6), Bootstrap 4
- **認証**: Flask-Login, Flask-WTF
- **ORM**: SQLAlchemy (Flask-SQLAlchemy)
- **マイグレーション**: Flask-Migrate (Alembic)
- **タスクキュー**: Celery + Redis
- **AI統合**: OpenAI GPT-4 API
- **メール**: SMTP + Gmail API

### 1.3 アーキテクチャパターン
- **MVC アーキテクチャ**: Model-View-Controller パターン
- **Blueprint パターン**: モジュール分割
- **Factory パターン**: アプリケーション作成
- **Repository パターン**: データアクセス層

## 2. システム構成

### 2.1 ディレクトリ構造
```
QuestEd/
├── app/                    # メインアプリケーション
│   ├── __init__.py        # アプリケーションファクトリ
│   ├── models/            # データモデル
│   ├── admin/             # 管理者機能
│   ├── teacher/           # 教師機能
│   ├── student/           # 生徒機能
│   ├── auth/              # 認証機能
│   ├── api/               # REST API
│   ├── ai/                # AI統合
│   └── utils/             # ユーティリティ
├── basebuilder/           # 学習管理システム
├── core/                  # コア機能
├── templates/             # HTMLテンプレート
├── static/                # 静的ファイル
├── migrations/            # データベースマイグレーション
└── scripts/               # 運用スクリプト
```

### 2.2 主要コンポーネント

#### 2.2.1 認証システム
```python
# app/auth/routes.py
@auth.route('/login', methods=['GET', 'POST'])
def login():
    # メールアドレス・パスワード認証
    # セッション管理
    # 2FA対応準備
```

#### 2.2.2 ロールベースアクセス制御
```python
# 権限レベル
ROLES = {
    'admin': 100,      # システム管理者
    'teacher': 50,     # 教師
    'student': 10      # 生徒
}
```

## 3. データベース設計

### 3.1 主要テーブル

#### 3.1.1 ユーザー管理
```sql
-- users テーブル
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
    full_name VARCHAR(100),
    is_approved BOOLEAN DEFAULT FALSE,
    email_verified BOOLEAN DEFAULT FALSE,
    school_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (school_id) REFERENCES schools(id)
);

-- schools テーブル  
CREATE TABLE schools (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    school_code VARCHAR(20) UNIQUE,
    address TEXT,
    contact_email VARCHAR(120),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 3.1.2 クラス管理
```sql
-- class_groups テーブル
CREATE TABLE class_groups (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    school_year_id INTEGER,
    teacher_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (school_year_id) REFERENCES school_years(id),
    FOREIGN KEY (teacher_id) REFERENCES users(id)
);

-- student_enrollment テーブル
CREATE TABLE student_enrollment (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL,
    class_group_id INTEGER NOT NULL,
    enrolled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users(id),
    FOREIGN KEY (class_group_id) REFERENCES class_groups(id)
);
```

#### 3.1.3 学習管理
```sql
-- inquiry_themes テーブル
CREATE TABLE inquiry_themes (
    id INTEGER PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    student_id INTEGER,
    class_id INTEGER,
    is_approved BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users(id),
    FOREIGN KEY (class_id) REFERENCES classes(id)
);

-- activity_logs テーブル
CREATE TABLE activity_logs (
    id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    image_filename VARCHAR(255),
    theme_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users(id),
    FOREIGN KEY (theme_id) REFERENCES inquiry_themes(id)
);
```

### 3.2 BaseBuilder モジュール
```sql
-- 問題カテゴリ
CREATE TABLE problem_categories (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 基礎知識問題
CREATE TABLE basic_knowledge_items (
    id INTEGER PRIMARY KEY,
    category_id INTEGER,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    answer TEXT,
    choices JSON,  -- 選択肢（4択問題用）
    difficulty_level INTEGER DEFAULT 1,
    FOREIGN KEY (category_id) REFERENCES problem_categories(id)
);

-- 習熟度記録
CREATE TABLE proficiency_records (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    knowledge_item_id INTEGER NOT NULL,
    mastery_level FLOAT DEFAULT 0.0,
    last_reviewed DATETIME,
    review_count INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (knowledge_item_id) REFERENCES basic_knowledge_items(id)
);
```

## 4. API設計

### 4.1 REST API エンドポイント

#### 4.1.1 認証API
```python
# POST /api/auth/login
{
    "email": "user@example.com",
    "password": "password123"
}
# Response: {"token": "jwt_token", "user": {...}}

# POST /api/auth/logout
# Response: {"message": "ログアウトしました"}
```

#### 4.1.2 ユーザー管理API
```python
# GET /api/users
# Response: {"users": [...], "total": 100}

# POST /api/users
{
    "email": "new@example.com",
    "password": "password123",
    "role": "student",
    "full_name": "山田太郎"
}

# PUT /api/users/{id}
# DELETE /api/users/{id}
```

#### 4.1.3 BaseBuilder API
```python
# GET /api/problems
# Response: {"problems": [...], "categories": [...]}

# POST /api/problems/{id}/submit
{
    "answer": "選択した答え",
    "time_spent": 120  # 秒
}
# Response: {"correct": true, "explanation": "..."}
```

### 4.2 GraphQL API（将来拡張）
```graphql
type User {
    id: ID!
    email: String!
    role: Role!
    fullName: String
    school: School
    classes: [Class!]!
}

type Query {
    user(id: ID!): User
    users(filter: UserFilter): [User!]!
    classes(teacherId: ID): [Class!]!
}
```

## 5. セキュリティ設計

### 5.1 認証・認可
```python
# パスワードハッシュ化
from werkzeug.security import generate_password_hash, check_password_hash

def set_password(self, password):
    self.password_hash = generate_password_hash(password)

def check_password(self, password):
    return check_password_hash(self.password_hash, password)
```

### 5.2 CSRF保護
```python
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
csrf.init_app(app)

# フォームでのCSRFトークン
{{ csrf_token() }}
```

### 5.3 XSS対策
```python
from markupsafe import Markup

# 安全なHTMLレンダリング
def safe_render(content):
    return Markup(escape(content))
```

### 5.4 ファイルアップロードセキュリティ
```python
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
```

## 6. パフォーマンス設計

### 6.1 データベース最適化
```sql
-- インデックス設計
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_activity_logs_student_date ON activity_logs(student_id, created_at);
CREATE INDEX idx_proficiency_user_item ON proficiency_records(user_id, knowledge_item_id);
```

### 6.2 キャッシュ戦略
```python
from flask_caching import Cache

cache = Cache()
cache.init_app(app)

@cache.memoize(timeout=300)  # 5分キャッシュ
def get_user_classes(user_id):
    # 重い処理をキャッシュ
    pass
```

### 6.3 非同期処理
```python
# Celery タスク
@celery.task
def send_daily_report():
    # 日次レポート生成・送信
    pass

@celery.task  
def process_ai_request(user_id, prompt):
    # OpenAI API呼び出し
    pass
```

## 7. AI統合設計

### 7.1 OpenAI API統合
```python
import openai

class AIHelper:
    def __init__(self, api_key):
        openai.api_key = api_key
    
    def generate_curriculum(self, subject, grade, requirements):
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたは教育カリキュラム作成の専門家です。"},
                {"role": "user", "content": f"{subject}の{grade}年生向けカリキュラムを作成してください。"}
            ]
        )
        return response.choices[0].message.content
```

### 7.2 AI機能
- **カリキュラム生成**: 科目・学年に応じた学習計画
- **テーマ提案**: 生徒の興味に基づく探究テーマ
- **評価支援**: 生徒の活動に対する評価コメント
- **チャットサポート**: 学習に関する質問応答

## 8. 運用・監視設計

### 8.1 ログ設計
```python
import logging
from logging.handlers import RotatingFileHandler

# アプリケーションログ
app.logger.setLevel(logging.INFO)
handler = RotatingFileHandler('logs/quested.log', maxBytes=10000000, backupCount=10)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
app.logger.addHandler(handler)
```

### 8.2 エラー監視
```python
# Sentry統合（推奨）
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn="YOUR_SENTRY_DSN",
    integrations=[FlaskIntegration()],
    traces_sample_rate=1.0
)
```

### 8.3 ヘルスチェック
```python
@app.route('/health')
def health_check():
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': app.config.get('VERSION', '1.0.0')
    }
```

## 9. デプロイメント設計

### 9.1 Docker化
```dockerfile
FROM python:3.8-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]
```

### 9.2 環境設定
```python
# config.py
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
class DevelopmentConfig(Config):
    DEBUG = True
    
class ProductionConfig(Config):
    DEBUG = False
```

## 10. 今後の技術的拡張

### 10.1 マイクロサービス化
- ユーザー管理サービス
- 学習管理サービス  
- AI処理サービス
- 通知サービス

### 10.2 新技術導入
- **GraphQL**: より柔軟なAPI
- **WebSocket**: リアルタイム通信
- **Machine Learning**: 学習分析
- **Mobile App**: React Native/Flutter

### 10.3 スケーラビリティ
- **読み書き分離**: マスター・スレーブ構成
- **CDN**: 静的ファイル配信
- **ロードバランシング**: 複数サーバー構成
- **キャッシュクラスター**: Redis Cluster