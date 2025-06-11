#!/bin/bash
# 定期メール送信のcronを設定するスクリプト

echo "Setting up daily email cron job..."

# スクリプトに実行権限を付与
chmod +x /var/www/quested/scripts/send_daily_summary.py

# 現在のcronジョブをバックアップ
crontab -l > /tmp/current_cron 2>/dev/null || true

# 新しいcronジョブを追加（重複チェック）
if ! grep -q "send_daily_summary.py" /tmp/current_cron; then
    echo "0 18 * * * cd /var/www/quested && /usr/bin/python3 scripts/send_daily_summary.py >> /var/log/quested/daily_email.log 2>&1" >> /tmp/current_cron
    crontab /tmp/current_cron
    echo "Cron job added successfully!"
else
    echo "Cron job already exists."
fi

# ログディレクトリの作成
sudo mkdir -p /var/log/quested
sudo chown $(whoami):$(whoami) /var/log/quested

echo "Setup completed!"
echo "The daily summary email will be sent at 18:00 every day."
echo "Logs will be saved to: /var/log/quested/daily_email.log"