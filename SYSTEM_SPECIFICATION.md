# QuestEd システム仕様書 v1.4.1

## 1. システム概要

### 1.1 目的
QuestEdは、中学・高校における探究学習を支援する教育プラットフォームです。AI技術を活用し、生徒の個別最適化された学習体験と教師の指導支援を提供します。

### 1.2 主要機能
- **多役割管理**: 管理者、教師、生徒の3つの役割に対応
- **AI支援学習**: 教科別プロンプトによる個別指導
- **学校管理**: 学校単位でのユーザー・クラス管理
- **探究学習支援**: テーマ設定、活動記録、進捗管理
- **自動レポート**: 日次学習レポートの自動生成・配信
- **評価システム**: ルーブリック評価とAI支援評価

### 1.3 技術的特徴
- **教科機能**: 6教科対応（理科、数学、国語、社会、英語、総合）
- **セキュリティ**: XSS対策、CSRF保護、役割ベースアクセス制御
- **スケーラビリティ**: Celeryによる非同期処理対応
- **メール統合**: SMTP/Gmail API両対応

## 2. アーキテクチャ

### 2.1 技術スタック

#### Backend
- **Framework**: Flask 2.x
- **ORM**: SQLAlchemy
- **Database**: MySQL 8.0 (PyMySQL)
- **Task Queue**: Celery + Redis
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF (CSRF protection)
- **Admin**: Flask-Admin
- **Migration**: Flask-Migrate

#### Frontend
- **CSS Framework**: Bootstrap 5.x
- **JavaScript**: Vanilla JS + jQuery
- **Icons**: Font Awesome
- **Templates**: Jinja2

#### AI & External Services
- **AI**: OpenAI GPT-4/GPT-3.5-turbo
- **Email**: Gmail API / SMTP
- **File Storage**: Local filesystem (将来: AWS S3)

#### Infrastructure
- **Server**: AWS EC2 t3a.medium
- **Database**: AWS RDS MySQL
- **Cache/Queue**: Redis
- **Reverse Proxy**: Nginx
- **Process Manager**: Gunicorn

### 2.2 システム構成図

```
[Browser] ←→ [Nginx] ←→ [Gunicorn] ←→ [Flask App]
                                        ↓
                                    [MySQL DB]
                                        ↓
                                   [Redis Cache]
                                        ↓
                                 [Celery Workers]
                                        ↓
                              [Email Service (Gmail)]
                                        ↓
                               [OpenAI API (GPT-4)]
```

### 2.3 プロジェクト構造

```
QuestEd/
├── app/                      # メインアプリケーション
│   ├── __init__.py          # アプリケーションファクトリー
│   ├── models/              # データベースモデル
│   │   ├── __init__.py      # 全モデル定義
│   │   └── subject.py       # 教科モデル
│   ├── auth/                # 認証システム
│   ├── admin/               # 管理機能
│   ├── teacher/             # 教師機能
│   ├── student/             # 生徒機能
│   ├── api/                 # REST API
│   ├── ai/                  # AI統合
│   ├── tasks/               # Celeryタスク
│   ├── utils/               # ユーティリティ
│   ├── scripts/             # 管理スクリプト
│   └── version.py           # バージョン管理
├── templates/               # Jinja2テンプレート
├── static/                  # 静的ファイル
├── migrations/              # データベースマイグレーション
├── basebuilder/             # 基礎学習モジュール
├── core/                    # コア機能
├── config.py                # 設定ファイル
├── extensions.py            # Flask拡張
├── run.py                   # アプリケーション起動
├── celery_worker.py         # Celeryワーカー
└── requirements.txt         # 依存関係
```

## 3. データベース設計

### 3.1 主要テーブル

#### User System
```sql
users (
    id INT PRIMARY KEY,
    username VARCHAR(50) UNIQUE,
    email VARCHAR(100) UNIQUE,
    password VARCHAR(255),
    role ENUM('admin', 'teacher', 'student'),
    school_id INT,
    email_confirmed BOOLEAN DEFAULT FALSE,
    is_approved BOOLEAN DEFAULT FALSE,
    created_at DATETIME
)
```

#### School Management
```sql
schools (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    code VARCHAR(20) UNIQUE,
    address TEXT,
    contact_info JSON,
    created_at DATETIME
)

school_years (
    id INT PRIMARY KEY,
    school_id INT,
    year_name VARCHAR(50),
    start_date DATE,
    end_date DATE
)

class_groups (
    id INT PRIMARY KEY,
    school_id INT,
    school_year_id INT,
    name VARCHAR(50),
    grade_level INT
)
```

#### Subject System (v1.3.0+)
```sql
subjects (
    id INT PRIMARY KEY,
    name VARCHAR(50),
    code VARCHAR(20) UNIQUE,
    ai_system_prompt TEXT,
    learning_objectives TEXT,
    assessment_criteria TEXT,
    grade_level VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME,
    updated_at DATETIME
)
```

#### Class Management
```sql
classes (
    id INT PRIMARY KEY,
    teacher_id INT,
    school_id INT,
    subject_id INT,           -- v1.3.0で追加
    name VARCHAR(100),
    description TEXT,
    schedule VARCHAR(200),
    location VARCHAR(200),
    created_at DATETIME
)

class_enrollments (
    id INT PRIMARY KEY,
    class_id INT,
    student_id INT,
    enrolled_at DATETIME,
    is_active BOOLEAN DEFAULT TRUE
)
```

#### Learning Content
```sql
main_themes (
    id INT PRIMARY KEY,
    class_id INT,
    title VARCHAR(200),
    description TEXT,
    created_by INT,
    created_at DATETIME
)

inquiry_themes (
    id INT PRIMARY KEY,
    student_id INT,
    class_id INT,
    title VARCHAR(200),
    question TEXT,
    description TEXT,
    is_selected BOOLEAN DEFAULT FALSE,
    created_at DATETIME
)
```

#### Chat System
```sql
chat_history (
    id INT PRIMARY KEY,
    user_id INT,
    class_id INT,
    subject_id INT,           -- v1.3.0で追加
    message TEXT,
    is_user BOOLEAN DEFAULT TRUE,
    timestamp DATETIME DEFAULT NOW()
)
```

### 3.2 ER図の主要関係

```
School (1) ←→ (n) User
School (1) ←→ (n) Class
User (1) ←→ (n) Class (teacher_id)
Class (1) ←→ (n) ClassEnrollment ←→ (1) User (student)
Subject (1) ←→ (n) Class
Subject (1) ←→ (n) ChatHistory
User (1) ←→ (n) ChatHistory
```

## 4. API仕様

### 4.1 認証API

#### POST /auth/login
```json
{
    "username": "string",
    "password": "string"
}
```

**Response:**
```json
{
    "status": "success",
    "user": {
        "id": 1,
        "username": "teacher01",
        "role": "teacher",
        "school_id": 1
    }
}
```

#### POST /auth/register
```json
{
    "username": "string",
    "email": "string",
    "password": "string",
    "role": "student",
    "school_code": "string"
}
```

### 4.2 Chat API

#### POST /api/chat
```json
{
    "message": "光合成について教えて",
    "class_id": 1,
    "step": "science_inquiry",
    "function": ""
}
```

**Response:**
```json
{
    "message": "光合成は植物が太陽エネルギーを使って...",
    "status": "success"
}
```

### 4.3 管理API

#### GET /api/stats
**Response:**
```json
{
    "total_users": 150,
    "total_students": 120,
    "total_teachers": 25,
    "total_classes": 30,
    "pending_approvals": 5
}
```

## 5. セキュリティ仕様

### 5.1 認証・認可

#### 認証方式
- **セッションベース認証**: Flask-Login使用
- **パスワードハッシュ化**: bcryptライブラリ
- **メール認証**: トークンベース認証
- **パスワードリセット**: タイムリミット付きトークン

#### 役割ベースアクセス制御
```python
# デコレータによる権限管理
@login_required
@teacher_required
def teacher_dashboard():
    pass

@admin_required
def admin_panel():
    pass
```

### 5.2 データ保護

#### XSS対策
- **テンプレート自動エスケープ**: Jinja2デフォルト
- **CSPヘッダー**: Content Security Policy設定
- **危険フィルタ削除**: `|safe`フィルタの制限的使用

#### CSRF対策
```python
# 全フォームでCSRF保護
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = 3600  # 1時間
```

#### SQLインジェクション対策
- **SQLAlchemy ORM**: パラメータ化クエリ
- **入力値検証**: Flask-WTFによるバリデーション

### 5.3 セッション管理
```python
PERMANENT_SESSION_LIFETIME = 1800  # 30分
SESSION_COOKIE_SECURE = True       # HTTPS必須
SESSION_COOKIE_HTTPONLY = True     # XSS対策
SESSION_COOKIE_SAMESITE = 'Lax'    # CSRF対策
```

### 5.4 ファイルアップロードセキュリティ (v1.4.1+)

#### FileSecurityValidator クラス
```python
# 包括的ファイル検証システム
class FileSecurityValidator:
    def validate_image(self, file_stream, filename, max_size=5MB)
    def validate_csv(self, file_stream, filename, max_size=2MB)
    def create_secure_path(self, filename, user_id=None)
```

#### セキュリティ機能
- **MIMEタイプ検証**: python-magic使用（フォールバック: imghdr）
- **ファイルサイズ制限**: 画像5MB、CSV2MB
- **ユーザー分離**: ユーザー別ディレクトリ構造
- **拡張子検証**: 許可された形式のみ受け入れ
- **XSS防止**: CSVファイル内容のスクリプトタグ検出
- **パストラバーサル対策**: 危険な文字列の検出と拒否

#### 対応ファイル形式
```python
# 画像ファイル
ALLOWED_IMAGE_TYPES = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif']
}

# CSVファイル
ALLOWED_CSV_TYPES = {
    'text/csv': ['.csv'],
    'text/plain': ['.csv'],
    'application/csv': ['.csv']
}
```

## 6. 教科機能仕様

### 6.1 対応教科

| 教科ID | 教科名 | コード | 特徴 |
|--------|--------|--------|------|
| 1 | 理科 | science | 実験・観察重視、安全性配慮 |
| 2 | 数学 | math | 論理的思考、段階的解決 |
| 3 | 国語 | japanese | 読解力・表現力向上 |
| 4 | 社会 | social | 多角的視点、批判的思考 |
| 5 | 英語 | english | コミュニケーション重視 |
| 6 | 総合 | integrated | 横断的・総合的学習 |

### 6.2 教科別AIプロンプト例

#### 理科
```
科学的思考を促進し、仮説・実験・結論のプロセスを重視してください。
生徒の疑問に対して、観察や実験を通じた探究的な学習を促してください。
安全性に配慮し、実験の際の注意事項も含めてください。
```

#### 数学
```
論理的思考と段階的な問題解決を支援してください。
公式の暗記ではなく、なぜその公式が成り立つのかを理解させてください。
実生活での応用例を示し、数学の有用性を伝えてください。
```

### 6.3 教科機能の技術実装

```python
# Subjectモデル
class Subject(db.Model):
    def get_ai_prompt(self):
        base_prompt = "あなたは優秀な教育AIアシスタントです。"
        if self.ai_system_prompt:
            return f"{base_prompt}\n{self.ai_system_prompt}"
        return base_prompt

# AIチャット処理
def generate_chat_response(message, context=None, subject=None):
    system_prompt = "基本プロンプト"
    if subject and subject.ai_system_prompt:
        system_prompt += f"\n\n【教科特性】\n{subject.ai_system_prompt}"
    # OpenAI API呼び出し
```

## 7. 日次レポート機能

### 7.1 概要
毎日18:00に自動実行され、生徒と教師に学習活動レポートをメール送信する機能。

### 7.2 技術仕様

#### Celeryタスク設定
```python
CELERYBEAT_SCHEDULE = {
    'daily-reports': {
        'task': 'app.tasks.daily_report.generate_daily_reports',
        'schedule': 86400.0,  # 24時間ごと
    },
}
```

#### レポート生成フロー
1. **データ収集**: 当日の学習活動を集計
2. **AI要約**: 教科別の学習内容をGPT-4で要約
3. **テンプレート生成**: HTMLメールテンプレート作成
4. **メール送信**: EmailSenderクラスで送信

### 7.3 レポート内容

#### 生徒向けレポート
- 教科別質問数と内容要約
- 活動記録の概要
- 完了したタスク
- 進行中の目標

#### 教師向けレポート
- クラス全体の活動統計
- アクティブ生徒一覧
- 参加率の計算
- 指導のヒント

## 8. 運用仕様

### 8.1 デプロイメント

#### 本番環境
- **サーバー**: AWS EC2 t3a.medium
- **OS**: Amazon Linux 2
- **Python**: 3.9+
- **Webサーバー**: Nginx + Gunicorn
- **プロセス管理**: systemd

#### デプロイ手順
```bash
# 1. コード更新
git pull origin main

# 2. マイグレーション実行
python3 -m flask db upgrade

# 3. アプリケーション再起動
sudo systemctl restart quested

# 4. Celeryワーカー再起動
sudo systemctl restart quested-celery
```

#### Celery管理ツール (v1.4.1+)
```bash
# 統合管理スクリプト
python3 manage_celery.py --help

# Celeryワーカー起動
python3 manage_celery.py worker

# スケジューラー起動
python3 manage_celery.py beat

# 状態確認
python3 manage_celery.py status

# 日次レポートテスト
python3 manage_celery.py test-daily-report

# systemdサービス生成
python3 manage_celery.py install-service
```

### 8.2 バックアップ

#### データベースバックアップ
```bash
# 日次バックアップ (cron)
0 2 * * * mysqldump -h $DB_HOST -u $DB_USER -p$DB_PASS $DB_NAME > /backup/quested_$(date +\%Y\%m\%d).sql
```

#### 設定ファイルバックアップ
- `.env`ファイル
- Nginx設定
- systemdサービス設定

### 8.3 監視

#### ログ監視
```bash
# アプリケーションログ
tail -f /var/log/quested/app.log

# Gunicornログ
tail -f /var/log/gunicorn/quested.log

# Celeryログ
tail -f /var/log/celery/worker.log
```

#### メトリクス監視
- CPU使用率
- メモリ使用率
- データベース接続数
- レスポンス時間

## 9. 環境設定

### 9.1 必要な環境変数

```bash
# Flask設定
SECRET_KEY=your-secret-key
FLASK_ENV=production
FLASK_DEBUG=false

# データベース設定
DB_USERNAME=quested_user
DB_PASSWORD=secure_password
DB_HOST=localhost
DB_NAME=quested

# OpenAI設定
OPENAI_API_KEY=sk-...

# メール設定
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=info@quested.jp
SMTP_PASSWORD=app_specific_password

# Celery設定
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 9.2 依存関係

```
Flask==2.3.3
SQLAlchemy==2.0.21
PyMySQL==1.1.0
Flask-Login==0.6.3
Flask-WTF==1.1.1
Flask-Migrate==4.0.5
openai==1.3.0
celery==5.3.4
redis==5.0.1
gunicorn==21.2.0
```

## 10. トラブルシューティング

### 10.1 よくある問題

#### マイグレーションエラー
```bash
# 解決方法
python3 -m flask db stamp head
python3 -m flask db migrate
python3 -m flask db upgrade
```

#### OpenAI APIエラー
- APIキーの確認
- 使用量制限のチェック
- リクエスト形式の確認

#### メール送信エラー
- SMTP設定の確認
- Gmailアプリパスワードの確認
- ファイアウォール設定の確認

### 10.2 パフォーマンス最適化

#### データベース最適化
```sql
-- インデックス追加
CREATE INDEX idx_chat_history_user_date ON chat_history(user_id, timestamp);
CREATE INDEX idx_users_school_role ON users(school_id, role);
```

#### Celeryパフォーマンス
```python
# ワーカー数の調整
celery -A celery_worker.celery worker --loglevel=info --concurrency=4
```

## 11. 今後の開発計画

### 11.1 短期計画 (v1.5.0)
- [ ] リアルタイムチャット機能
- [ ] ファイルアップロード改善
- [ ] モバイルアプリ対応

### 11.2 中期計画 (v2.0.0)
- [ ] マイクロサービス化
- [ ] AWS S3統合
- [ ] 高度な分析機能

### 11.3 長期計画 (v3.0.0)
- [ ] 機械学習による学習予測
- [ ] 国際化対応
- [ ] オープンソース化

---

**最終更新**: 2025年1月10日  
**バージョン**: 1.4.1  
**作成者**: QuestEd開発チーム