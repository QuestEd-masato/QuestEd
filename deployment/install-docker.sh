#!/bin/bash
# install-docker.sh - EC2にDockerをインストール

set -e

echo "🚀 Docker環境をセットアップしています..."

# Dockerの公式GPGキーを追加
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Dockerリポジトリを追加
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Dockerをインストール
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Dockerグループにユーザーを追加
sudo usermod -aG docker $USER

# Docker Composeをインストール
DOCKER_COMPOSE_VERSION="v2.23.0"
sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Dockerサービスを有効化・開始
sudo systemctl enable docker
sudo systemctl start docker

# インストール確認
echo "✅ Docker バージョン:"
docker --version

echo "✅ Docker Compose バージョン:"
docker-compose --version

echo "🎉 Docker環境のセットアップが完了しました！"
echo "⚠️  ログアウトして再ログインしてください（Dockerグループの反映のため）"