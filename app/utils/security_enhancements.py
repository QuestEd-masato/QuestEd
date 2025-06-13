# app/utils/security_enhancements.py
"""
セキュリティ強化機能
認証・セッション管理・入力検証の強化
"""

import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Tuple, Dict
from flask import request, session, current_app, abort, g
from flask_login import current_user
import re

class SecurityManager:
    """セキュリティ管理クラス"""
    
    # ブルートフォース攻撃対策
    login_attempts = {}  # {ip: [timestamp, ...]}
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION = 300  # 5分
    
    @classmethod
    def is_ip_locked(cls, ip_address: str) -> bool:
        """IPアドレスがロックされているかチェック"""
        if ip_address not in cls.login_attempts:
            return False
        
        # 期限切れの試行を削除
        cutoff_time = time.time() - cls.LOCKOUT_DURATION
        cls.login_attempts[ip_address] = [
            attempt for attempt in cls.login_attempts[ip_address]
            if attempt > cutoff_time
        ]
        
        # ロック判定
        return len(cls.login_attempts[ip_address]) >= cls.MAX_LOGIN_ATTEMPTS
    
    @classmethod
    def record_login_attempt(cls, ip_address: str, success: bool = False):
        """ログイン試行を記録"""
        if success:
            # 成功時はIPの記録をクリア
            cls.login_attempts.pop(ip_address, None)
        else:
            # 失敗時は記録に追加
            if ip_address not in cls.login_attempts:
                cls.login_attempts[ip_address] = []
            cls.login_attempts[ip_address].append(time.time())
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """セキュアなトークン生成"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_token(token: str, salt: str = None) -> str:
        """トークンのハッシュ化"""
        if salt is None:
            salt = current_app.config.get('SECRET_KEY', 'default_salt')
        return hashlib.sha256((token + salt).encode()).hexdigest()
    
    @staticmethod
    def verify_csrf_token(token: str) -> bool:
        """CSRFトークンの検証"""
        expected_token = session.get('csrf_token')
        if not expected_token or not token:
            return False
        return hmac.compare_digest(expected_token, token)

class InputValidator:
    """入力検証クラス"""
    
    # 安全な文字パターン
    SAFE_USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_.-]{3,50}$')
    SAFE_EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    SAFE_SCHOOL_CODE_PATTERN = re.compile(r'^[A-Z0-9]{3,10}$')
    
    @classmethod
    def validate_username(cls, username: str) -> Tuple[bool, str]:
        """ユーザー名検証"""
        if not username:
            return False, "ユーザー名は必須です"
        
        if not cls.SAFE_USERNAME_PATTERN.match(username):
            return False, "ユーザー名は3-50文字の英数字、ハイフン、アンダースコア、ピリオドのみ使用可能です"
        
        return True, ""
    
    @classmethod
    def validate_email(cls, email: str) -> Tuple[bool, str]:
        """メールアドレス検証"""
        if not email:
            return False, "メールアドレスは必須です"
        
        if not cls.SAFE_EMAIL_PATTERN.match(email):
            return False, "有効なメールアドレスを入力してください"
        
        if len(email) > 254:  # RFC 5321
            return False, "メールアドレスが長すぎます"
        
        return True, ""
    
    @classmethod
    def validate_school_code(cls, school_code: str) -> Tuple[bool, str]:
        """学校コード検証"""
        if not school_code:
            return False, "学校コードは必須です"
        
        if not cls.SAFE_SCHOOL_CODE_PATTERN.match(school_code.upper()):
            return False, "学校コードは3-10文字の英数字である必要があります"
        
        return True, ""
    
    @classmethod
    def sanitize_input(cls, text: str, max_length: int = 1000) -> str:
        """入力文字列のサニタイズ"""
        if not text:
            return ""
        
        # 制御文字を除去
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        # 長さ制限
        if len(text) > max_length:
            text = text[:max_length]
        
        return text.strip()

class SessionManager:
    """セッション管理クラス"""
    
    @staticmethod
    def regenerate_session_id():
        """セッションID再生成（セッションハイジャック対策）"""
        if 'user_id' in session:
            user_id = session['user_id']
            session.clear()
            session['user_id'] = user_id
            session.permanent = True
    
    @staticmethod
    def set_secure_session(user_id: int):
        """セキュアなセッション設定"""
        session.clear()
        session['user_id'] = user_id
        session['login_time'] = datetime.utcnow().isoformat()
        session['ip_address'] = request.remote_addr
        session['csrf_token'] = SecurityManager.generate_secure_token()
        session.permanent = True
    
    @staticmethod
    def validate_session() -> bool:
        """セッション検証"""
        if not current_user.is_authenticated:
            return False
        
        # IPアドレスチェック（セッションハイジャック対策）
        session_ip = session.get('ip_address')
        current_ip = request.remote_addr
        
        if session_ip and session_ip != current_ip:
            current_app.logger.warning(
                f"Session hijacking attempt detected: session IP {session_ip}, current IP {current_ip}"
            )
            return False
        
        # セッション有効期限チェック
        login_time_str = session.get('login_time')
        if login_time_str:
            login_time = datetime.fromisoformat(login_time_str)
            if datetime.utcnow() - login_time > timedelta(hours=8):  # 8時間でタイムアウト
                return False
        
        return True

def require_secure_auth(f):
    """セキュア認証デコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # ブルートフォース攻撃チェック
        if SecurityManager.is_ip_locked(request.remote_addr):
            current_app.logger.warning(f"Blocked request from locked IP: {request.remote_addr}")
            abort(429)  # Too Many Requests
        
        # セッション検証
        if not SessionManager.validate_session():
            current_app.logger.warning(f"Invalid session detected from IP: {request.remote_addr}")
            abort(401)  # Unauthorized
        
        return f(*args, **kwargs)
    
    return decorated_function

def validate_csrf_token_required(f):
    """CSRF トークン検証デコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            
            if not SecurityManager.verify_csrf_token(token):
                current_app.logger.warning(f"CSRF token validation failed from IP: {request.remote_addr}")
                abort(403)  # Forbidden
        
        return f(*args, **kwargs)
    
    return decorated_function

def rate_limit_by_user(max_requests: int = 100, window_minutes: int = 60):
    """ユーザー別レート制限デコレータ"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return f(*args, **kwargs)
            
            # シンプルなインメモリレート制限（本番では Redis を推奨）
            cache_key = f"rate_limit_{current_user.id}_{request.endpoint}"
            
            if not hasattr(g, 'rate_limit_cache'):
                g.rate_limit_cache = {}
            
            now = time.time()
            window_start = now - (window_minutes * 60)
            
            if cache_key not in g.rate_limit_cache:
                g.rate_limit_cache[cache_key] = []
            
            # 期限切れのリクエストを削除
            g.rate_limit_cache[cache_key] = [
                timestamp for timestamp in g.rate_limit_cache[cache_key]
                if timestamp > window_start
            ]
            
            # リクエスト数チェック
            if len(g.rate_limit_cache[cache_key]) >= max_requests:
                current_app.logger.warning(
                    f"Rate limit exceeded for user {current_user.id} on {request.endpoint}"
                )
                abort(429)  # Too Many Requests
            
            # 現在のリクエストを記録
            g.rate_limit_cache[cache_key].append(now)
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

class PasswordSecurity:
    """パスワードセキュリティ強化"""
    
    # よく使われる危険なパスワードリスト
    COMMON_PASSWORDS = {
        'password', '123456', '123456789', 'qwerty', 'abc123',
        'password123', 'admin', 'letmein', 'welcome', 'monkey',
        'football', 'iloveyou', 'charlie', 'superman', 'michael'
    }
    
    @classmethod
    def validate_password_strength(cls, password: str) -> Tuple[bool, list]:
        """パスワード強度検証"""
        errors = []
        
        # 長さチェック
        if len(password) < 8:
            errors.append("パスワードは8文字以上である必要があります")
        
        if len(password) > 128:
            errors.append("パスワードは128文字以下である必要があります")
        
        # 複雑性チェック
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
        
        complexity_count = sum([has_lower, has_upper, has_digit, has_special])
        
        if complexity_count < 3:
            errors.append("パスワードは英小文字、英大文字、数字、特殊文字のうち3種類以上を含む必要があります")
        
        # よく使われるパスワードチェック
        if password.lower() in cls.COMMON_PASSWORDS:
            errors.append("このパスワードは一般的すぎるため使用できません")
        
        # 連続文字チェック
        if cls._has_sequential_chars(password):
            errors.append("連続した文字や数字は使用できません")
        
        return len(errors) == 0, errors
    
    @classmethod
    def _has_sequential_chars(cls, password: str) -> bool:
        """連続文字のチェック"""
        for i in range(len(password) - 2):
            # 3文字以上の連続をチェック
            if (ord(password[i+1]) == ord(password[i]) + 1 and 
                ord(password[i+2]) == ord(password[i]) + 2):
                return True
        return False

def log_security_event(event_type: str, details: Dict, user_id: Optional[int] = None):
    """セキュリティイベントのログ記録"""
    log_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', ''),
        'user_id': user_id or (current_user.id if current_user.is_authenticated else None),
        'details': details
    }
    
    current_app.logger.warning(f"Security Event: {event_type}", extra=log_data)