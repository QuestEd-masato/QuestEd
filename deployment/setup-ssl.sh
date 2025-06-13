#!/bin/bash
# setup-ssl.sh - Let's Encrypt SSL証明書セットアップ

set -e

# 設定
DOMAIN=${1:-}
EMAIL=${2:-}

if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "使用方法: $0 <ドメイン名> <メールアドレス>"
    echo "例: $0 example.com admin@example.com"
    exit 1
fi

echo "🔐 SSL証明書をセットアップしています..."
echo "ドメイン: $DOMAIN"
echo "メール: $EMAIL"

# Certbot がインストールされているか確認
if ! command -v certbot &> /dev/null; then
    echo "📦 Certbot をインストールしています..."
    sudo apt-get update
    sudo apt-get install -y certbot python3-certbot-nginx
fi

# Nginx設定ファイルの一時的な変更（HTTP のみ）
echo "🔧 一時的にHTTP設定に変更しています..."
sudo tee /etc/nginx/sites-available/quested-temp > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# サイトを有効化
sudo ln -sf /etc/nginx/sites-available/quested-temp /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# Certbot用ディレクトリ作成
sudo mkdir -p /var/www/certbot

# SSL証明書取得
echo "📜 SSL証明書を取得しています..."
sudo certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

# 証明書のパスを確認
CERT_PATH="/etc/letsencrypt/live/$DOMAIN"
if [ ! -f "$CERT_PATH/fullchain.pem" ]; then
    echo "❌ SSL証明書の取得に失敗しました"
    exit 1
fi

# QuestEd用のNginx設定に変更
echo "🔧 QuestEd用のNginx設定に変更しています..."
sudo tee /etc/nginx/sites-available/quested > /dev/null <<EOF
# HTTPからHTTPSへのリダイレクト
server {
    listen 80;
    server_name $DOMAIN;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://\$host\$request_uri;
    }
}

# HTTPS設定
server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    # SSL証明書
    ssl_certificate $CERT_PATH/fullchain.pem;
    ssl_certificate_key $CERT_PATH/privkey.pem;
    
    # SSL設定
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # セキュリティヘッダー
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # アプリケーションへのプロキシ
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # タイムアウト設定
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # 静的ファイル配信
    location /static/ {
        alias /home/ubuntu/quested/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /uploads/ {
        alias /home/ubuntu/quested/static/uploads/;
        expires 1d;
        add_header Cache-Control "public";
    }
}
EOF

# サイトを有効化
sudo ln -sf /etc/nginx/sites-available/quested /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/quested-temp
sudo nginx -t && sudo systemctl reload nginx

# 証明書自動更新の設定
echo "🔄 証明書自動更新を設定しています..."
sudo crontab -l 2>/dev/null > /tmp/crontab || true
echo "0 12 * * * /usr/bin/certbot renew --quiet && /usr/bin/systemctl reload nginx" >> /tmp/crontab
sudo crontab /tmp/crontab
rm /tmp/crontab

echo "✅ SSL証明書のセットアップが完了しました！"
echo "🌐 アクセス先: https://$DOMAIN"
echo "🔄 証明書は毎日12:00に自動更新チェックされます"

# 証明書の有効期限確認
echo "📅 証明書情報:"
sudo certbot certificates