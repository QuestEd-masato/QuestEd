# QuestEd デプロイメントガイド v1.4.0

## 目次
1. [前提条件](#前提条件)
2. [初回セットアップ](#初回セットアップ)
3. [日常のデプロイ手順](#日常のデプロイ手順)
4. [Celery設定](#celery設定)
5. [メール設定](#メール設定)
6. [監視とメンテナンス](#監視とメンテナンス)
7. [トラブルシューティング](#トラブルシューティング)

## 前提条件

### システム要件
- **OS**: Amazon Linux 2 / Ubuntu 20.04+
- **Python**: 3.9+
- **Database**: MySQL 8.0+
- **Cache**: Redis 6.0+
- **Memory**: 4GB以上推奨
- **Storage**: 20GB以上

### 必要なソフトウェア
```bash
# Amazon Linux 2の場合
sudo yum update -y
sudo yum install python3 python3-pip mysql-community-server redis git nginx -y

# Ubuntu の場合  
sudo apt update
sudo apt install python3 python3-pip mysql-server redis-server git nginx -y
```

## 初回セットアップ

### 1. プロジェクトのクローン
```bash
cd /var/www
sudo git clone https://github.com/QuestEd-masato/QuestEd.git
sudo chown -R $USER:$USER QuestEd
cd QuestEd
```

### 2. Python環境の構築
```bash
# 仮想環境作成
python3 -m venv venv
source venv/bin/activate

# パッケージインストール
pip install --upgrade pip
pip install -r requirements.txt

# Celery用パッケージ（必要に応じて）
pip install celery redis flower
```

### 3. 環境変数設定
```bash
# .envファイル作成
cp .env.example .env
nano .env
```

**.env設定例:**
```bash
# Flask設定
SECRET_KEY=your-very-secure-secret-key-here
FLASK_ENV=production
FLASK_DEBUG=false

# データベース設定
DB_USERNAME=quested_user
DB_PASSWORD=your_secure_db_password
DB_HOST=localhost
DB_NAME=quested

# OpenAI設定
OPENAI_API_KEY=sk-your-openai-api-key

# メール設定
EMAIL_METHOD=smtp
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=info@quested.jp
SMTP_PASSWORD=your_gmail_app_password

# Celery設定
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# テスト用
TEST_EMAIL=admin@yourschool.jp
```

### 4. データベースセットアップ
```bash
# MySQL設定
sudo mysql -u root -p

# データベース作成
CREATE DATABASE quested CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'quested_user'@'localhost' IDENTIFIED BY 'your_secure_db_password';
GRANT ALL PRIVILEGES ON quested.* TO 'quested_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;

# マイグレーション実行
export FLASK_APP=run.py
python3 -m flask db upgrade

# 教科初期データ投入
python3 app/scripts/init_subjects.py
```

### 5. Gunicorn設定
```bash
# Gunicorn設定ファイル作成
cat > gunicorn.conf.py << 'EOF'
bind = "127.0.0.1:8001"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 600
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
user = "ec2-user"
group = "ec2-user"
tmp_upload_dir = None
logfile = "/var/log/gunicorn/quested.log"
loglevel = "info"
access_logfile = "/var/log/gunicorn/access.log"
access_logformat = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
EOF

# ログディレクトリ作成
sudo mkdir -p /var/log/gunicorn
sudo chown $USER:$USER /var/log/gunicorn
```

### 6. systemdサービス設定
```bash
# QuestEdアプリケーションサービス
sudo tee /etc/systemd/system/quested.service > /dev/null << 'EOF'
[Unit]
Description=QuestEd Flask Application
After=network.target

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/var/www/QuestEd
Environment=PATH=/var/www/QuestEd/venv/bin
ExecStart=/var/www/QuestEd/venv/bin/gunicorn --config gunicorn.conf.py run:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Celeryワーカーサービス
sudo tee /etc/systemd/system/quested-celery.service > /dev/null << 'EOF'
[Unit]
Description=QuestEd Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=ec2-user
Group=ec2-user
WorkingDirectory=/var/www/QuestEd
Environment=PATH=/var/www/QuestEd/venv/bin
ExecStart=/var/www/QuestEd/venv/bin/celery -A celery_worker.celery worker --detach --loglevel=info --logfile=/var/log/celery/worker.log --pidfile=/var/run/celery/worker.pid
ExecStop=/bin/kill -s TERM $MAINPID
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Celery Beatサービス（日次レポート用）
sudo tee /etc/systemd/system/quested-celery-beat.service > /dev/null << 'EOF'
[Unit]
Description=QuestEd Celery Beat Scheduler
After=network.target redis.service

[Service]
Type=forking
User=ec2-user
Group=ec2-user
WorkingDirectory=/var/www/QuestEd
Environment=PATH=/var/www/QuestEd/venv/bin
ExecStart=/var/www/QuestEd/venv/bin/celery -A celery_worker.celery beat --detach --loglevel=info --logfile=/var/log/celery/beat.log --pidfile=/var/run/celery/beat.pid
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# ログディレクトリとPIDディレクトリ作成
sudo mkdir -p /var/log/celery /var/run/celery
sudo chown $USER:$USER /var/log/celery /var/run/celery

# サービス有効化
sudo systemctl daemon-reload
sudo systemctl enable quested quested-celery quested-celery-beat
```

### 7. Nginx設定
```bash
# Nginx設定ファイル作成
sudo tee /etc/nginx/sites-available/quested > /dev/null << 'EOF'
server {
    listen 80;
    server_name quest-ed.jp www.quest-ed.jp;

    # セキュリティヘッダー
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com; font-src 'self' fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-src 'none';" always;

    # ファイルサイズ制限
    client_max_body_size 16M;

    # 静的ファイル
    location /static {
        alias /var/www/QuestEd/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # アプリケーション
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }

    # ログ設定
    access_log /var/log/nginx/quested_access.log;
    error_log /var/log/nginx/quested_error.log;
}
EOF

# サイト有効化
sudo ln -sf /etc/nginx/sites-available/quested /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 日常のデプロイ手順

### 標準デプロイ手順
```bash
#!/bin/bash
# deploy.sh - デプロイスクリプト

set -e  # エラー時に停止

echo "🚀 Starting QuestEd deployment..."

# 1. コード更新
echo "📥 Pulling latest code..."
git pull origin main

# 2. 依存関係更新（必要時）
echo "📦 Updating dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# 3. マイグレーション実行
echo "🗄️ Running database migrations..."
export FLASK_APP=run.py
python3 -m flask db upgrade

# 4. 静的ファイル更新（必要時）
echo "📁 Updating static files..."
# 将来的にAsset管理を追加する場合

# 5. サービス再起動
echo "🔄 Restarting services..."
sudo systemctl restart quested
sudo systemctl restart quested-celery
sudo systemctl restart quested-celery-beat

# 6. 動作確認
echo "✅ Checking service status..."
sudo systemctl status quested --no-pager -l
sudo systemctl status quested-celery --no-pager -l

echo "🎉 Deployment completed successfully!"
```

### ホットフィックス手順
```bash
# 緊急修正の場合
git checkout main
git pull origin main
sudo systemctl restart quested
```

## Celery設定

### Redis設定確認
```bash
# Redis動作確認
redis-cli ping
# 期待される応答: PONG

# Redis設定（/etc/redis/redis.conf）
sudo nano /etc/redis/redis.conf

# 推奨設定
maxmemory 256mb
maxmemory-policy allkeys-lru
```

### Celeryタスクテスト
```bash
# ワーカー状態確認
celery -A celery_worker.celery status

# タスク送信テスト
python3 -c "
from app.tasks.daily_report import generate_daily_reports
result = generate_daily_reports.delay()
print(f'Task ID: {result.id}')
"

# Flower監視（オプション）
celery -A celery_worker.celery flower --port=5555
```

### 日次レポート手動実行
```bash
# 手動でレポート生成
python3 app/tasks/daily_report.py

# または
python3 -c "
from app.tasks.daily_report import DailyReportService
service = DailyReportService()
success, message = service.generate_all_reports()
print(f'Success: {success}, Message: {message}')
"
```

## メール設定

### Gmail SMTP設定
1. Gmailアカウントで2段階認証を有効化
2. アプリパスワードを生成
3. .envファイルに設定

```bash
# Gmail設定テスト
python3 -c "
from app.utils.email_sender import test_email_configuration
success = test_email_configuration()
print(f'Email test result: {success}')
"
```

### メール送信ログ確認
```bash
# アプリケーションログ
tail -f /var/log/gunicorn/quested.log | grep -i email

# Celeryワーカーログ
tail -f /var/log/celery/worker.log | grep -i report
```

## 監視とメンテナンス

### ログ監視
```bash
# 全体ログ監視
sudo journalctl -f -u quested -u quested-celery

# エラーログ監視
sudo tail -f /var/log/nginx/quested_error.log
sudo tail -f /var/log/gunicorn/quested.log | grep ERROR
```

### パフォーマンス監視
```bash
# システムリソース
htop
df -h
free -m

# MySQL監視
mysql -u root -p -e "SHOW PROCESSLIST;"
mysql -u root -p -e "SHOW STATUS LIKE 'Threads_connected';"

# Redis監視
redis-cli info stats
```

### バックアップ
```bash
# データベースバックアップ
mysqldump -h $DB_HOST -u $DB_USERNAME -p$DB_PASSWORD $DB_NAME > backup_$(date +%Y%m%d_%H%M%S).sql

# 設定ファイルバックアップ
tar -czf config_backup_$(date +%Y%m%d).tar.gz .env gunicorn.conf.py /etc/systemd/system/quested*.service
```

### 定期メンテナンス
```bash
# 週次タスク
sudo logrotate -f /etc/logrotate.conf
sudo apt update && sudo apt upgrade -y  # Ubuntu
sudo yum update -y  # Amazon Linux

# 月次タスク
# ログファイル清理
find /var/log -name "*.log" -mtime +30 -delete
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. アプリケーションが起動しない
```bash
# ログ確認
sudo journalctl -u quested -n 50

# 一般的な原因
# - .env設定ミス
# - データベース接続エラー
# - ポート競合

# 解決方法
sudo systemctl stop quested
source venv/bin/activate
python3 run.py  # 直接実行でエラー確認
```

#### 2. データベース接続エラー
```bash
# データベース接続確認
mysql -h $DB_HOST -u $DB_USERNAME -p$DB_PASSWORD $DB_NAME

# 接続権限確認
mysql -u root -p -e "SHOW GRANTS FOR 'quested_user'@'localhost';"
```

#### 3. マイグレーションエラー
```bash
# マイグレーション状態確認
python3 -m flask db current
python3 -m flask db heads

# 強制的なマイグレーション修復
python3 -m flask db stamp head
python3 -m flask db migrate
python3 -m flask db upgrade
```

#### 4. Celeryタスクが実行されない
```bash
# Celeryワーカー状態確認
celery -A celery_worker.celery inspect active
celery -A celery_worker.celery inspect scheduled

# Redis接続確認
redis-cli -h localhost -p 6379 ping

# ワーカー再起動
sudo systemctl restart quested-celery quested-celery-beat
```

#### 5. メール送信エラー
```bash
# SMTP設定確認
python3 -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
print('SMTP connection successful')
server.quit()
"

# Gmail認証確認
# - 2段階認証が有効か
# - アプリパスワードが正しいか
```

### デバッグモード
```bash
# 開発者向けデバッグ実行
export FLASK_DEBUG=true
export FLASK_ENV=development
python3 run.py
```

### 緊急時の対応
```bash
# サービス停止
sudo systemctl stop quested quested-celery quested-celery-beat

# バックアップからの復旧
mysql -u $DB_USERNAME -p$DB_PASSWORD $DB_NAME < backup_20250109_120000.sql

# 前のバージョンに戻す
git checkout [previous_commit_hash]
sudo systemctl restart quested
```

## セキュリティチェックリスト

- [ ] `.env`ファイルの権限確認（600）
- [ ] データベースユーザー権限の最小化
- [ ] Nginxセキュリティヘッダーの設定
- [ ] Firewallの設定（必要なポートのみ開放）
- [ ] SSL証明書の設定（Let's Encrypt推奨）
- [ ] ログファイルの定期ローテーション
- [ ] バックアップの定期実行確認

---

**最終更新**: 2025年1月9日  
**バージョン**: 1.4.0  
**対象環境**: AWS EC2, Amazon Linux 2