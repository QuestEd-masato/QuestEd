#!/bin/bash
# deploy-production.sh - 本番環境デプロイスクリプト

set -e

echo "🚀 QuestEd 本番環境デプロイを開始します..."

# 設定確認
REQUIRED_VARS=(
    "DEPLOY_HOST"
    "DEPLOY_USER" 
    "SSH_KEY"
    "DOMAIN_NAME"
    "ADMIN_EMAIL"
    "RDS_ENDPOINT"
    "ELASTICACHE_REDIS_URL"
    "S3_BACKUP_BUCKET"
)

echo "📋 環境変数を確認しています..."
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ エラー: $var 環境変数が設定されていません"
        exit 1
    fi
    echo "✅ $var: ${!var}"
done

# 本番環境チェック
echo "⚠️  本番環境デプロイの確認"
echo "ホスト: $DEPLOY_HOST"
echo "ドメイン: $DOMAIN_NAME"
echo ""
read -p "本番環境にデプロイしますか？ (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "デプロイを中止しました"
    exit 1
fi

# SSH接続確認
echo "🔌 本番サーバーへの接続を確認しています..."
ssh -i "$SSH_KEY" -o ConnectTimeout=10 "$DEPLOY_USER@$DEPLOY_HOST" "echo '接続成功'" || {
    echo "❌ SSH接続に失敗しました"
    exit 1
}

# 事前チェック
echo "🔍 本番環境の事前チェックを実行しています..."
ssh -i "$SSH_KEY" "$DEPLOY_USER@$DEPLOY_HOST" "
    # Docker確認
    if ! command -v docker &> /dev/null; then
        echo '❌ Dockerがインストールされていません'
        exit 1
    fi
    
    # RDS接続確認
    if ! nc -z ${RDS_ENDPOINT/:*/} ${RDS_ENDPOINT/*:/}; then
        echo '❌ RDSに接続できません'
        exit 1
    fi
    
    # ElastiCache接続確認  
    if ! nc -z ${ELASTICACHE_REDIS_URL/redis:\/\//} 6379; then
        echo '❌ ElastiCacheに接続できません'
        exit 1
    fi
    
    echo '✅ 事前チェック完了'
"

# バックアップ作成
echo "💾 現在の環境をバックアップしています..."
BACKUP_NAME="backup-$(date +%Y%m%d_%H%M%S)"
ssh -i "$SSH_KEY" "$DEPLOY_USER@$DEPLOY_HOST" "
    if [ -d /opt/quested ]; then
        sudo tar -czf /tmp/$BACKUP_NAME.tar.gz /opt/quested/
        aws s3 cp /tmp/$BACKUP_NAME.tar.gz s3://$S3_BACKUP_BUCKET/backups/
        rm /tmp/$BACKUP_NAME.tar.gz
        echo '✅ バックアップ完了: s3://$S3_BACKUP_BUCKET/backups/$BACKUP_NAME.tar.gz'
    fi
"

# プロジェクトディレクトリ準備
echo "📁 本番環境ディレクトリを準備しています..."
ssh -i "$SSH_KEY" "$DEPLOY_USER@$DEPLOY_HOST" "
    sudo mkdir -p /opt/quested
    sudo chown $DEPLOY_USER:$DEPLOY_USER /opt/quested
    
    # 永続化ディレクトリ作成
    sudo mkdir -p /var/lib/quested/uploads
    sudo mkdir -p /var/log/quested
    sudo chown -R $DEPLOY_USER:$DEPLOY_USER /var/lib/quested
    sudo chown -R $DEPLOY_USER:$DEPLOY_USER /var/log/quested
"

# ファイル転送
echo "📤 アプリケーションファイルを転送しています..."
rsync -avz --progress \
    --exclude='venv/' \
    --exclude='__pycache__/' \
    --exclude='.git/' \
    --exclude='node_modules/' \
    --exclude='*.pyc' \
    --exclude='.env*' \
    --exclude='deployment/ssl/' \
    --delete \
    -e "ssh -i $SSH_KEY" \
    ./ "$DEPLOY_USER@$DEPLOY_HOST:/opt/quested/"

# 本番用環境設定
echo "🔧 本番用環境設定を行っています..."
ssh -i "$SSH_KEY" "$DEPLOY_USER@$DEPLOY_HOST" "
    cd /opt/quested
    
    # AWS Secrets Managerから環境変数を取得
    aws secretsmanager get-secret-value \
        --secret-id 'quested/production' \
        --query SecretString --output text > .env
    
    # 権限設定
    chmod 600 .env
    
    # Nginxプロキシ設定の更新
    sed -i 's/YOUR_DOMAIN/$DOMAIN_NAME/g' deployment/nginx.production.conf
"

# SSL証明書設定
echo "🔐 SSL証明書を設定しています..."
ssh -i "$SSH_KEY" "$DEPLOY_USER@$DEPLOY_HOST" "
    cd /opt/quested
    
    # 既存のNginx停止
    sudo systemctl stop nginx || true
    
    # Let's Encrypt証明書取得
    if [ ! -f /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem ]; then
        sudo certbot certonly --standalone \
            --email $ADMIN_EMAIL \
            --agree-tos \
            --no-eff-email \
            -d $DOMAIN_NAME
    fi
    
    # 証明書確認
    sudo certbot certificates
"

# Blue-Green デプロイメント準備
echo "🔄 Blue-Green デプロイメントを準備しています..."
ssh -i "$SSH_KEY" "$DEPLOY_USER@$DEPLOY_HOST" "
    cd /opt/quested
    
    # 新バージョン（Green）をビルド
    docker-compose -f docker-compose.production.yml -p quested-green build
    
    # ヘルスチェック用の一時サービス起動
    docker-compose -f docker-compose.production.yml -p quested-green up -d web
    
    # ヘルスチェック
    sleep 30
    for i in {1..10}; do
        if curl -f http://localhost:8000/health; then
            echo '✅ ヘルスチェック成功'
            break
        fi
        echo \"ヘルスチェック試行 \$i/10...\"
        sleep 10
    done
    
    # 一時サービス停止
    docker-compose -f docker-compose.production.yml -p quested-green down
"

# 本番デプロイ実行
echo "🚀 本番環境にデプロイしています..."
ssh -i "$SSH_KEY" "$DEPLOY_USER@$DEPLOY_HOST" "
    cd /opt/quested
    
    # 既存サービス停止（Blue）
    docker-compose -f docker-compose.production.yml -p quested-blue down || true
    
    # 新サービス起動（Green）
    docker-compose -f docker-compose.production.yml -p quested-green up -d
    
    # Nginx設定更新とリロード
    sudo cp deployment/nginx.production.conf /etc/nginx/sites-available/quested
    sudo ln -sf /etc/nginx/sites-available/quested /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t && sudo systemctl reload nginx
    
    # サービス起動確認
    sleep 60
    if docker-compose -f docker-compose.production.yml -p quested-green ps | grep -q 'Up'; then
        echo '✅ 本番デプロイ成功'
        
        # 古いコンテナ削除
        docker-compose -f docker-compose.production.yml -p quested-blue down --volumes || true
        docker image prune -f
        
        # サービス状況確認
        docker-compose -f docker-compose.production.yml -p quested-green ps
        
        # ヘルスチェック
        curl -f https://$DOMAIN_NAME/health
        
    else
        echo '❌ デプロイ失敗 - ロールバックしています'
        docker-compose -f docker-compose.production.yml -p quested-green down
        docker-compose -f docker-compose.production.yml -p quested-blue up -d
        exit 1
    fi
"

# デプロイ完了通知
echo "🎉 本番環境デプロイが完了しました！"
echo ""
echo "🌐 アクセス先: https://$DOMAIN_NAME"
echo "📊 監視: CloudWatch Logs"
echo "📝 ログ確認:"
echo "  ssh -i $SSH_KEY $DEPLOY_USER@$DEPLOY_HOST"
echo "  cd /opt/quested && docker-compose -f docker-compose.production.yml logs -f"
echo ""
echo "🔄 ロールバック方法（必要時）:"
echo "  ssh -i $SSH_KEY $DEPLOY_USER@$DEPLOY_HOST"
echo "  cd /opt/quested"
echo "  docker-compose -f docker-compose.production.yml -p quested-green down"
echo "  aws s3 cp s3://$S3_BACKUP_BUCKET/backups/$BACKUP_NAME.tar.gz /tmp/"
echo "  sudo tar -xzf /tmp/$BACKUP_NAME.tar.gz -C /"