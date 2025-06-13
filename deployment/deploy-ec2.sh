#!/bin/bash
# deploy-ec2.sh - EC2自動デプロイスクリプト

set -e

echo "🚀 QuestEd EC2デプロイを開始します..."

# 設定読み込み
DEPLOY_USER=${DEPLOY_USER:-ubuntu}
DEPLOY_HOST=${DEPLOY_HOST}
SSH_KEY=${SSH_KEY:-~/.ssh/id_rsa}
PROJECT_DIR="/home/$DEPLOY_USER/quested"

if [ -z "$DEPLOY_HOST" ]; then
    echo "❌ エラー: DEPLOY_HOST環境変数を設定してください"
    echo "例: export DEPLOY_HOST=ec2-xxx-xxx-xxx-xxx.region.compute.amazonaws.com"
    exit 1
fi

echo "📋 デプロイ設定:"
echo "  ホスト: $DEPLOY_HOST"
echo "  ユーザー: $DEPLOY_USER"
echo "  プロジェクトディレクトリ: $PROJECT_DIR"

# SSH接続確認
echo "🔌 SSH接続を確認しています..."
ssh -i "$SSH_KEY" -o ConnectTimeout=10 "$DEPLOY_USER@$DEPLOY_HOST" "echo '接続成功'" || {
    echo "❌ SSH接続に失敗しました"
    exit 1
}

# プロジェクトディレクトリ作成
echo "📁 プロジェクトディレクトリを準備しています..."
ssh -i "$SSH_KEY" "$DEPLOY_USER@$DEPLOY_HOST" "
    sudo mkdir -p $PROJECT_DIR
    sudo chown $DEPLOY_USER:$DEPLOY_USER $PROJECT_DIR
    cd $PROJECT_DIR
    pwd
"

# ファイル転送
echo "📤 ファイルを転送しています..."
rsync -avz --progress \
    --exclude='venv/' \
    --exclude='__pycache__/' \
    --exclude='.git/' \
    --exclude='node_modules/' \
    --exclude='*.pyc' \
    --exclude='.env' \
    -e "ssh -i $SSH_KEY" \
    ./ "$DEPLOY_USER@$DEPLOY_HOST:$PROJECT_DIR/"

# .envファイル確認
echo "🔧 環境設定を確認しています..."
ssh -i "$SSH_KEY" "$DEPLOY_USER@$DEPLOY_HOST" "
    cd $PROJECT_DIR
    if [ ! -f .env ]; then
        echo '⚠️  .envファイルが見つかりません。.env.exampleからコピーして設定してください:'
        echo '  cp .env.example .env'
        echo '  nano .env'
        exit 1
    else
        echo '✅ .envファイルが見つかりました'
    fi
"

# Docker環境確認
echo "🐳 Docker環境を確認しています..."
ssh -i "$SSH_KEY" "$DEPLOY_USER@$DEPLOY_HOST" "
    cd $PROJECT_DIR
    if ! command -v docker &> /dev/null; then
        echo '📦 Dockerをインストールしています...'
        bash deployment/install-docker.sh
        echo '🔄 Dockerグループの反映のため、ログアウト・ログインが必要です'
        echo '   以下のコマンドを実行してデプロイを続行してください:'
        echo '   ./deployment/deploy-ec2.sh'
        exit 1
    else
        echo '✅ Docker is installed'
        docker --version
    fi
"

# SSL証明書ディレクトリ作成
echo "🔐 SSL証明書ディレクトリを準備しています..."
ssh -i "$SSH_KEY" "$DEPLOY_USER@$DEPLOY_HOST" "
    cd $PROJECT_DIR
    mkdir -p deployment/ssl
    
    # 自己署名証明書作成（テスト用）
    if [ ! -f deployment/ssl/cert.pem ]; then
        echo '🔑 テスト用自己署名証明書を作成しています...'
        sudo apt-get update
        sudo apt-get install -y openssl
        openssl req -x509 -newkey rsa:4096 -keyout deployment/ssl/key.pem -out deployment/ssl/cert.pem -days 365 -nodes \
            -subj '/C=JP/ST=Tokyo/L=Tokyo/O=QuestEd/CN=localhost'
        echo '✅ 自己署名証明書を作成しました（本番環境では Let\s Encrypt を使用してください）'
    fi
"

# デプロイ実行
echo "🚀 アプリケーションをデプロイしています..."
ssh -i "$SSH_KEY" "$DEPLOY_USER@$DEPLOY_HOST" "
    cd $PROJECT_DIR
    
    # 既存コンテナを停止・削除
    docker-compose -f docker-compose.ec2.yml down --remove-orphans || true
    
    # イメージをビルド
    docker-compose -f docker-compose.ec2.yml build --no-cache
    
    # コンテナを起動
    docker-compose -f docker-compose.ec2.yml up -d
    
    # 起動確認
    echo '⏳ サービスの起動を待機しています...'
    sleep 30
    
    # ヘルスチェック
    if docker-compose -f docker-compose.ec2.yml ps | grep -q 'Up'; then
        echo '✅ デプロイが成功しました！'
        echo '📊 サービス状況:'
        docker-compose -f docker-compose.ec2.yml ps
        echo ''
        echo '🌐 アクセス方法:'
        echo \"  HTTP:  http://$DEPLOY_HOST\"
        echo \"  HTTPS: https://$DEPLOY_HOST\"
        echo \"  App:   http://$DEPLOY_HOST:8000\"
        echo ''
        echo '📝 ログ確認:'
        echo '  docker-compose -f docker-compose.ec2.yml logs -f'
    else
        echo '❌ デプロイに失敗しました'
        echo '📋 サービス状況:'
        docker-compose -f docker-compose.ec2.yml ps
        echo '📝 エラーログ:'
        docker-compose -f docker-compose.ec2.yml logs
        exit 1
    fi
"

echo "🎉 EC2デプロイが完了しました！"