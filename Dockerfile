# Dockerfile - QuestEd アプリケーション
FROM python:3.9-slim

# セキュリティ: root以外のユーザーで実行
RUN groupadd -r quested && useradd -r -g quested quested

# 作業ディレクトリ設定
WORKDIR /app

# システムパッケージの更新とセキュリティパッチ
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 依存関係ファイルをコピー（キャッシュ効率化）
COPY requirements-secure.txt .

# Python依存関係のインストール
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-secure.txt

# アプリケーションコードをコピー
COPY . .

# ログディレクトリ作成
RUN mkdir -p /var/log/quested && \
    chown -R quested:quested /var/log/quested

# アップロードディレクトリ作成
RUN mkdir -p /app/uploads && \
    chown -R quested:quested /app/uploads

# ファイル権限設定
RUN chown -R quested:quested /app

# 非rootユーザーに切り替え
USER quested

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ポート公開
EXPOSE 8000

# 環境変数のデフォルト値
ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# アプリケーション起動
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "30", "--keep-alive", "2", "--max-requests", "1000", "--max-requests-jitter", "100", "run:app"]