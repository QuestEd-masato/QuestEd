# app/utils/rate_limiting.py
"""
レート制限ユーティリティ
"""
from functools import wraps
from flask import request, jsonify, current_app
from flask_login import current_user
from extensions import limiter

def ai_api_limit():
    """AI APIエンドポイント用のレート制限デコレータ"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # ログインしていないユーザーはより厳しい制限
            if not current_user.is_authenticated:
                # 匿名ユーザー: 1時間に5回まで
                return limiter.limit("5 per hour")(f)(*args, **kwargs)
            
            # ロール別の制限
            if current_user.role == 'admin':
                # 管理者: 制限なし
                return f(*args, **kwargs)
            elif current_user.role == 'teacher':
                # 教師: 1時間に30回まで
                return limiter.limit("30 per hour")(f)(*args, **kwargs)
            else:
                # 生徒: 1時間に10回まで
                return limiter.limit("10 per hour")(f)(*args, **kwargs)
        
        return decorated_function
    return decorator

def upload_limit():
    """ファイルアップロード用のレート制限デコレータ"""
    return limiter.limit("10 per minute", error_message="アップロード頻度が高すぎます。しばらく待ってから再試行してください。")

def auth_limit():
    """認証関連エンドポイント用のレート制限デコレータ"""
    return limiter.limit("5 per minute", error_message="ログイン試行回数が多すぎます。しばらく待ってから再試行してください。")

def api_limit():
    """一般的なAPI用のレート制限デコレータ"""
    return limiter.limit("100 per hour", error_message="APIの使用頻度が高すぎます。しばらく待ってから再試行してください。")

def critical_api_limit():
    """重要なAPIエンドポイント用の厳しいレート制限"""
    return limiter.limit("5 per hour", error_message="この機能の使用頻度が高すぎます。しばらく待ってから再試行してください。")

def get_user_key():
    """ユーザー別のキーを生成（ログインユーザーの場合）"""
    if current_user.is_authenticated:
        return f"user:{current_user.id}"
    return request.remote_addr

def user_based_limit(limit_string):
    """ユーザーベースのレート制限デコレータ"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return limiter.limit(limit_string, key_func=get_user_key)(f)(*args, **kwargs)
        return decorated_function
    return decorator

def smart_ai_limit():
    """賢いAI制限（ユーザーロール考慮 + ユーザーベース）"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                # 匿名ユーザー: IPベースで厳しい制限
                @limiter.limit("3 per hour")
                def anonymous_wrapper():
                    return f(*args, **kwargs)
                return anonymous_wrapper()
            
            # ユーザーベースの制限
            if current_user.role == 'admin':
                # 管理者: 緩い制限
                @limiter.limit("100 per hour", key_func=get_user_key)
                def admin_wrapper():
                    return f(*args, **kwargs)
                return admin_wrapper()
            elif current_user.role == 'teacher':
                # 教師: 中程度の制限
                @limiter.limit("50 per hour", key_func=get_user_key)
                def teacher_wrapper():
                    return f(*args, **kwargs)
                return teacher_wrapper()
            else:
                # 生徒: 厳しい制限
                @limiter.limit("20 per hour", key_func=get_user_key)
                def student_wrapper():
                    return f(*args, **kwargs)
                return student_wrapper()
        
        return decorated_function
    return decorator

class RateLimitExceeded(Exception):
    """レート制限例外"""
    def __init__(self, message="Rate limit exceeded"):
        self.message = message
        super().__init__(self.message)

def handle_rate_limit_error(e):
    """レート制限エラーハンドラー"""
    if request.is_json:
        return jsonify({
            'error': 'Rate limit exceeded',
            'message': 'リクエストが多すぎます。しばらく待ってから再試行してください。',
            'retry_after': getattr(e, 'retry_after', 3600)
        }), 429
    
    # HTMLレスポンスの場合
    return """
    <html>
    <head><title>レート制限エラー</title></head>
    <body>
        <h1>リクエストが多すぎます</h1>
        <p>しばらく待ってから再試行してください。</p>
        <script>setTimeout(function(){ history.back(); }, 3000);</script>
    </body>
    </html>
    """, 429

# アプリケーションレベルのエラーハンドラー登録用
def register_rate_limit_handlers(app):
    """レート制限エラーハンドラーを登録"""
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return handle_rate_limit_error(e)