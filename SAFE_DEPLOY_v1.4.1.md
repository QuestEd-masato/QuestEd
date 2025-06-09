# QuestEd v1.4.1 安全デプロイ手順書

## ⚠️ 重要な変更点とリスク

### 🔴 高リスク項目
1. **Celeryスケジュール形式変更**: `86400.0` → `crontab(hour=18, minute=0)`
2. **Import構造変更**: 循環インポート修正
3. **新規ファイル追加**: `app/utils/file_security.py`, `manage_celery.py`

### 🟡 中リスク項目
1. **ファイルアップロード変更**: ユーザー別ディレクトリ
2. **マイグレーション revision修正**: データベース整合性

## 🛡️ 事前チェックリスト

### STEP 1: 依存関係チェック
```bash
# EC2にSSH接続後
cd /var/www/QuestEd
source venv/bin/activate

# Celeryインストール確認
python3 -c "from celery.schedules import crontab; print('✅ Celery crontab OK')" || echo "❌ Celery導入必要"

# 新規ファイルの導入確認
python3 -c "
try:
    import imghdr
    print('✅ imghdr OK')
    import uuid
    print('✅ uuid OK')
    import hashlib
    print('✅ hashlib OK')
except ImportError as e:
    print(f'❌ Missing: {e}')
"
```

### STEP 2: バックアップ作成
```bash
# データベースバックアップ
mysqldump -h $DB_HOST -u $DB_USERNAME -p$DB_PASSWORD $DB_NAME > backup_pre_v1.4.1_$(date +%Y%m%d_%H%M%S).sql

# 設定ファイルバックアップ
cp .env .env.backup_$(date +%Y%m%d)
cp -r migrations migrations_backup_$(date +%Y%m%d)

# アプリケーションファイルバックアップ
tar -czf app_backup_pre_v1.4.1_$(date +%Y%m%d).tar.gz app/ config.py extensions.py
```

### STEP 3: Dry-Run テスト
```bash
# 新しいコードを別ディレクトリでテスト
cd /tmp
git clone https://github.com/QuestEd-masato/QuestEd.git quested_test
cd quested_test

# 仮想環境でテスト
python3 -m venv test_venv
source test_venv/bin/activate
pip install -r requirements.txt

# Import確認
python3 -c "
import sys
sys.path.append('.')
try:
    from app import create_app
    print('✅ App import OK')
    from app.utils.file_security import file_validator
    print('✅ FileValidator import OK')
    from config import Config
    print('✅ Config import OK')
except Exception as e:
    print(f'❌ Import error: {e}')
    exit(1)
"
```

## 🚀 段階的デプロイ手順

### PHASE 1: コード更新（アプリ停止なし）
```bash
cd /var/www/QuestEd

# 現在のブランチ確認
git branch -v

# 新しいコードを取得（まだ適用しない）
git fetch origin main
git log --oneline HEAD..origin/main  # 更新内容確認
```

### PHASE 2: 依存関係更新
```bash
# 仮想環境で依存関係確認
source venv/bin/activate
pip install -r requirements.txt  # 新規パッケージ確認

# Celery確認
python3 -c "from celery.schedules import crontab; print('Celery OK')"
```

### PHASE 3: アプリケーション停止・更新
```bash
# サービス停止（順序重要）
sudo systemctl stop quested-celery-beat
sudo systemctl stop quested-celery
sudo systemctl stop quested

# コード更新
git merge origin/main

# 新しいファイルの権限設定
chmod +x manage_celery.py
chown ec2-user:ec2-user app/utils/file_security.py
```

### PHASE 4: マイグレーション実行
```bash
# マイグレーション状態確認
export FLASK_APP=run.py
python3 -m flask db current
python3 -m flask db heads

# マイグレーション実行（revision修正済みのため）
python3 -m flask db upgrade
```

### PHASE 5: アップロードディレクトリ作成
```bash
# 新しいディレクトリ構造作成
mkdir -p uploads/
chmod 755 uploads/

# 既存ファイルがある場合の移行は手動で
# ls static/uploads/ 2>/dev/null || echo "No existing uploads"
```

### PHASE 6: 設定確認・サービス再起動
```bash
# 設定確認
python3 -c "
from config import Config
print('Config loaded successfully')
print(f'Celery schedule: {Config.CELERY_BEAT_SCHEDULE}')
"

# サービス再起動（順序重要）
sudo systemctl start quested
sleep 5
sudo systemctl status quested --no-pager

sudo systemctl start quested-celery
sleep 5
sudo systemctl status quested-celery --no-pager

sudo systemctl start quested-celery-beat
sleep 5
sudo systemctl status quested-celery-beat --no-pager
```

## 🧪 動作確認テスト

### TEST 1: アプリケーション基本動作
```bash
# ヘルスチェック
curl -f http://localhost:8001/ || echo "❌ App not responding"

# ログ確認
tail -n 20 /var/log/gunicorn/quested.log
```

### TEST 2: Celery動作確認
```bash
# Celeryワーカー状態
python3 manage_celery.py status

# 日次レポートテスト（実際には送信しない）
python3 -c "
from app.tasks.daily_report import DailyReportService
service = DailyReportService()
print('DailyReportService created successfully')
"
```

### TEST 3: ファイルアップロード確認
```bash
# ファイルセキュリティ確認
python3 -c "
from app.utils.file_security import file_validator
print('FileValidator imported successfully')
print(f'Available: {file_validator is not None}')
"
```

## 🚨 緊急時のロールバック手順

### EMERGENCY: アプリケーションエラーの場合
```bash
# サービス停止
sudo systemctl stop quested quested-celery quested-celery-beat

# 前のバージョンに戻す
git reset --hard HEAD~3  # v1.4.0に戻す
# または
git checkout 269c928  # v1.4.0の具体的コミット

# データベースロールバック（必要な場合のみ）
mysql -u $DB_USERNAME -p$DB_PASSWORD $DB_NAME < backup_pre_v1.4.1_[timestamp].sql

# サービス再起動
sudo systemctl start quested
sudo systemctl start quested-celery
sudo systemctl start quested-celery-beat
```

## 📋 成功確認チェックリスト

- [ ] アプリケーションが正常に起動している
- [ ] ログイン・基本操作が動作する
- [ ] Celeryワーカーが稼働している
- [ ] Celery Beatスケジューラーが稼働している
- [ ] ファイルアップロード機能が動作する
- [ ] エラーログに重大な問題がない
- [ ] 日次レポートが18:00にスケジュールされている

## 🔧 よくある問題と解決策

### 問題1: ImportError (循環インポート)
```bash
# 解決策: Pythonパスの確認
export PYTHONPATH=/var/www/QuestEd:$PYTHONPATH
cd /var/www/QuestEd
python3 -c "from app import create_app; print('OK')"
```

### 問題2: Celery設定エラー
```bash
# 解決策: 設定の手動確認
python3 -c "
import os
os.environ['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
from celery.schedules import crontab
print('Crontab import successful')
"
```

### 問題3: ファイルアップロードエラー
```bash
# 解決策: ディレクトリ権限確認
ls -la uploads/
chmod 755 uploads/
chown -R ec2-user:ec2-user uploads/
```

---

**実行前に必ず**: このチェックリストをすべて完了してからデプロイを実行してください。

**緊急連絡**: 問題が発生した場合は、すぐにロールバック手順を実行してください。