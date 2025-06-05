# QuestEd 環境セットアップ手順

## 前提条件

Blueprint移行は完了していますが、実行環境のセットアップが必要です。

## 環境セットアップ

### 1. 必要なシステムパッケージのインストール

```bash
# Ubuntu/Debian系
sudo apt update
sudo apt install python3-pip python3-venv python3-dev

# CentOS/RHEL系
sudo yum install python3-pip python3-venv python3-devel

# または dnf
sudo dnf install python3-pip python3-venv python3-devel
```

### 2. 仮想環境の作成と有効化

```bash
# QuestEdプロジェクトディレクトリで実行
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate     # Windows
```

### 3. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数の設定

`.env`ファイルを作成して以下を設定：

```env
SECRET_KEY=your-secret-key-here
DB_USERNAME=your-db-username
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_NAME=questedo
OPENAI_API_KEY=your-openai-api-key
FLASK_ENV=development
FLASK_DEBUG=true
```

### 5. データベースの初期化

```bash
# マイグレーションの実行
flask db upgrade

# または初回セットアップの場合
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 6. アプリケーションの起動

```bash
# 開発サーバー
python run.py

# または
flask run

# 本番環境（Gunicorn）
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## 移行完了の確認

Blueprint移行は以下の通り完了しています：

### ✅ 移行済み機能
- **teacher_bp**: 36ルート（カリキュラム管理含む）
- **student_bp**: 42ルート（グループ管理含む）
- **auth_bp**: 11ルート（認証機能）
- **admin_bp**: 3ルート（管理機能）
- **api_bp**: 7ルート（API機能）

### ✅ ファイル構成
- `app.py`: 最小構成（13行）
- `app.py.backup_*`: 元ファイルのバックアップ
- `templates/interest_survey_edit.html`: 新規作成済み

## トラブルシューティング

### 依存関係エラーの場合
```bash
# 仮想環境の確認
which python
pip list

# 再インストール
pip install --upgrade -r requirements.txt
```

### データベース接続エラーの場合
```bash
# MySQLサービスの確認
sudo systemctl status mysql

# データベースの存在確認
mysql -u root -p -e "SHOW DATABASES;"
```

### ルート確認
```bash
# 移行後のルート一覧（環境セットアップ後）
python test_routes_migration.py
```

## 注意事項

1. **後方互換性**: 旧app.pyへの参照は新しいBlueprint構造に自動転送されます
2. **URL変更なし**: エンドユーザーからのURL変更はありません
3. **権限維持**: 全ての権限チェックが適切に移行されています

環境セットアップ完了後、正常にアプリケーションが起動することを確認してください。