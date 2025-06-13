# EC2 テストデプロイ手順

## 1. EC2インスタンス作成

### 推奨スペック
- **インスタンスタイプ**: t3.medium (2 vCPU, 4GB RAM)
- **OS**: Ubuntu 22.04 LTS
- **ストレージ**: 20GB gp3
- **セキュリティグループ**: 
  - SSH (22): 自分のIPアドレスのみ
  - HTTP (80): 0.0.0.0/0
  - HTTPS (443): 0.0.0.0/0
  - App (8000): 0.0.0.0/0 (テスト用)

### セキュリティグループ設定
```bash
# セキュリティグループ作成
aws ec2 create-security-group \
    --group-name quested-test-sg \
    --description "QuestEd Test Environment"

# SSH (自分のIPのみ)
aws ec2 authorize-security-group-ingress \
    --group-name quested-test-sg \
    --protocol tcp \
    --port 22 \
    --cidr YOUR_IP/32

# HTTP/HTTPS
aws ec2 authorize-security-group-ingress \
    --group-name quested-test-sg \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
    --group-name quested-test-sg \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0

# アプリケーション (テスト用)
aws ec2 authorize-security-group-ingress \
    --group-name quested-test-sg \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0
```

## 2. インスタンス初期設定

### SSH接続
```bash
ssh -i your-key.pem ubuntu@ec2-xxx-xxx-xxx-xxx.region.compute.amazonaws.com
```

### 基本パッケージ更新
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git htop nginx certbot python3-certbot-nginx
```

## 3. 自動デプロイ実行

### 環境変数設定
```bash
export DEPLOY_HOST=ec2-xxx-xxx-xxx-xxx.region.compute.amazonaws.com
export DEPLOY_USER=ubuntu
export SSH_KEY=~/.ssh/your-key.pem
```

### デプロイ実行
```bash
# リポジトリをクローン
git clone https://github.com/your-username/QuestEd.git
cd QuestEd

# デプロイスクリプト実行
./deployment/deploy-ec2.sh
```

## 4. 手動セットアップ（詳細）

### Docker環境セットアップ
```bash
# EC2にSSH接続
ssh -i your-key.pem ubuntu@your-ec2-host

# Dockerインストール
wget https://raw.githubusercontent.com/your-repo/QuestEd/main/deployment/install-docker.sh
chmod +x install-docker.sh
./install-docker.sh

# 一度ログアウト・ログインしてDockerグループを反映
exit
ssh -i your-key.pem ubuntu@your-ec2-host
```

### アプリケーションセットアップ
```bash
# プロジェクトクローン
git clone https://github.com/your-username/QuestEd.git
cd QuestEd

# 環境変数設定
cp .env.example .env
nano .env  # 必要な値を設定

# SSL証明書用ディレクトリ作成
mkdir -p deployment/ssl

# テスト用自己署名証明書作成
openssl req -x509 -newkey rsa:4096 -keyout deployment/ssl/key.pem -out deployment/ssl/cert.pem -days 365 -nodes \
    -subj '/C=JP/ST=Tokyo/L=Tokyo/O=QuestEd/CN=localhost'

# デプロイ実行
docker-compose -f docker-compose.ec2.yml up -d
```

## 5. SSL証明書設定（本番用）

### Let's Encrypt証明書取得
```bash
# ドメイン名とメールアドレスを指定してSSLセットアップ
./deployment/setup-ssl.sh your-domain.com admin@your-domain.com
```

## 6. 監視とメンテナンス

### ログ確認
```bash
# アプリケーションログ
docker-compose -f docker-compose.ec2.yml logs -f web

# Nginxログ
docker-compose -f docker-compose.ec2.yml logs -f nginx

# データベースログ
docker-compose -f docker-compose.ec2.yml logs -f db
```

### ヘルスチェック
```bash
# サービス状況確認
docker-compose -f docker-compose.ec2.yml ps

# システムリソース確認
htop
df -h
free -h
```

### バックアップ
```bash
# データベースバックアップ
docker-compose -f docker-compose.ec2.yml exec db mysqldump -u root -p quested_ec2 > backup-$(date +%Y%m%d).sql

# アップロードファイルバックアップ
tar -czf uploads-backup-$(date +%Y%m%d).tar.gz static/uploads/
```

## 7. トラブルシューティング

### 一般的な問題

1. **Docker権限エラー**
   ```bash
   # Dockerグループに追加後、再ログインが必要
   sudo usermod -aG docker $USER
   exit  # ログアウト
   # 再ログイン
   ```

2. **ポート競合**
   ```bash
   # 使用中のポート確認
   sudo netstat -tlnp | grep :80
   sudo netstat -tlnp | grep :443
   ```

3. **SSL証明書エラー**
   ```bash
   # 証明書確認
   sudo certbot certificates
   
   # 手動更新
   sudo certbot renew --force-renewal
   ```

4. **データベース接続エラー**
   ```bash
   # データベースログ確認
   docker-compose -f docker-compose.ec2.yml logs db
   
   # データベース接続テスト
   docker-compose -f docker-compose.ec2.yml exec db mysql -u quested_user -p quested_ec2
   ```