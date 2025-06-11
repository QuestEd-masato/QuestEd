#!/bin/bash
# ローカル環境用の定期メール送信のcronを設定するスクリプト

echo "Setting up daily email cron job for local environment..."

# プロジェクトディレクトリ
PROJECT_DIR="/home/masat/claude-projects/QuestEd"

# スクリプトに実行権限を付与
chmod +x $PROJECT_DIR/scripts/send_daily_summary.py

# 現在のcronジョブをバックアップ
crontab -l > /tmp/current_cron 2>/dev/null || true

# 新しいcronジョブを追加（重複チェック）
if ! grep -q "send_daily_summary.py" /tmp/current_cron; then
    echo "0 18 * * * cd $PROJECT_DIR && $PROJECT_DIR/venv/bin/python scripts/send_daily_summary.py >> /tmp/quested_daily_email.log 2>&1" >> /tmp/current_cron
    crontab /tmp/current_cron
    echo "Cron job added successfully!"
else
    echo "Cron job already exists."
fi

echo "Setup completed!"
echo "The daily summary email will be sent at 18:00 every day."
echo "Logs will be saved to: /tmp/quested_daily_email.log"