"""
セキュリティユーティリティ
"""
import secrets
import hashlib
import re
from urllib.parse import urlparse, urljoin
from flask import request, url_for, current_app
import logging

class SecurityUtils:
    """セキュリティ関連のユーティリティクラス"""
    
    @staticmethod
    def generate_secure_token(length=32):
        """
        セキュアなトークンを生成
        
        Args:
            length (int): トークンの長さ
            
        Returns:
            str: セキュアなトークン
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_csrf_token():
        """
        CSRFトークンを生成
        
        Returns:
            str: CSRFトークン
        """
        return secrets.token_hex(16)
    
    @staticmethod
    def validate_password_strength(password):
        """
        パスワード強度を検証
        
        Args:
            password (str): 検証するパスワード
            
        Returns:
            tuple: (is_valid, errors)
        """
        errors = []
        
        if len(password) < 12:
            errors.append("パスワードは12文字以上である必要があります")
        
        if not re.search(r'[A-Z]', password):
            errors.append("パスワードには大文字が含まれている必要があります")
        
        if not re.search(r'[a-z]', password):
            errors.append("パスワードには小文字が含まれている必要があります")
        
        if not re.search(r'\d', password):
            errors.append("パスワードには数字が含まれている必要があります")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("パスワードには特殊文字が含まれている必要があります")
        
        # 連続する同じ文字をチェック
        if re.search(r'(.)\1{2,}', password):
            errors.append("パスワードに同じ文字を3回以上連続して使用することはできません")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def hash_sensitive_data(data, salt=None):
        """
        機密データをハッシュ化
        
        Args:
            data (str): ハッシュ化するデータ
            salt (str, optional): ソルト
            
        Returns:
            str: ハッシュ化されたデータ
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        combined = f"{salt}{data}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    @staticmethod
    def sanitize_filename(filename):
        """
        ファイル名をサニタイズ
        
        Args:
            filename (str): 元のファイル名
            
        Returns:
            str: サニタイズされたファイル名
        """
        # 危険な文字を除去
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # ドットで始まるファイル名を防止
        if filename.startswith('.'):
            filename = '_' + filename[1:]
        
        # 長すぎるファイル名を制限
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:250] + ('.' + ext if ext else '')
        
        return filename
    
    @staticmethod
    def is_safe_url(target):
        """
        リダイレクト先URLが安全かチェック
        
        Args:
            target (str): チェックするURL
            
        Returns:
            bool: 安全なURLかどうか
        """
        ref_url = urlparse(request.host_url)
        test_url = urlparse(urljoin(request.host_url, target))
        return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc
    
    @staticmethod
    def validate_email_format(email):
        """
        メールアドレス形式を検証
        
        Args:
            email (str): 検証するメールアドレス
            
        Returns:
            bool: 有効なメールアドレス形式かどうか
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def log_security_event(event_type, user_id=None, details=None):
        """
        セキュリティイベントをログに記録
        
        Args:
            event_type (str): イベントタイプ
            user_id (int, optional): ユーザーID
            details (str, optional): 詳細情報
        """
        log_entry = f"SECURITY_EVENT: {event_type}"
        
        if user_id:
            log_entry += f" | User ID: {user_id}"
        
        if details:
            log_entry += f" | Details: {details}"
        
        log_entry += f" | IP: {request.remote_addr if request else 'Unknown'}"
        
        logging.warning(log_entry)
    
    @staticmethod
    def check_rate_limit_exceeded(user_id, action, limit=10, window=3600):
        """
        レート制限をチェック（簡易版）
        
        Args:
            user_id (int): ユーザーID
            action (str): アクション名
            limit (int): 制限回数
            window (int): 時間窓（秒）
            
        Returns:
            bool: レート制限を超えているかどうか
        """
        # 実装が必要：Redisやメモリストアを使用したレート制限
        # 現在は常にFalseを返す（レート制限なし）
        return False

def setup_security_headers(app):
    """
    セキュリティヘッダーを設定
    
    Args:
        app: Flaskアプリケーション
    """
    @app.after_request
    def set_security_headers(response):
        # XSS保護
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # HTTPS強制（本番環境のみ）
        if app.config.get('ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # コンテンツセキュリティポリシー
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdn.jsdelivr.net"
        )
        
        return response