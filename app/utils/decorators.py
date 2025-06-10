"""
共通デコレータユーティリティ
"""
from functools import wraps
from flask import redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required
import logging
from app.utils.database import handle_db_errors

def role_required(*allowed_roles):
    """
    ロールベースのアクセス制御デコレータ
    
    Args:
        *allowed_roles: 許可されるロールのリスト
    """
    def decorator(func):
        @wraps(func)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role not in allowed_roles:
                flash(f'この機能は{"/".join(allowed_roles)}のみ利用可能です。', 'error')
                logging.warning(f"Unauthorized access attempt by {current_user.username} (role: {current_user.role}) to {func.__name__}")
                return redirect(url_for('index'))
            return func(*args, **kwargs)
        return wrapper
    return decorator

def admin_required(func):
    """管理者権限を要求するデコレータ"""
    return role_required('admin')(func)

def teacher_required(func):
    """教師権限を要求するデコレータ"""
    return role_required('teacher', 'admin')(func)

def student_required(func):
    """学生権限を要求するデコレータ"""
    return role_required('student', 'teacher', 'admin')(func)

def approval_required(func):
    """
    承認済みユーザーのみアクセス可能にするデコレータ
    """
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role == 'student' and not current_user.is_approved:
            flash('アカウントがまだ承認されていません。教師の承認をお待ちください。', 'warning')
            return redirect(url_for('auth.awaiting_approval'))
        return func(*args, **kwargs)
    return wrapper

def email_confirmed_required(func):
    """
    メール確認済みユーザーのみアクセス可能にするデコレータ
    """
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.email_confirmed:
            flash('メールアドレスの確認が必要です。', 'warning')
            return redirect(url_for('auth.verify_email', user_id=current_user.id))
        return func(*args, **kwargs)
    return wrapper

def ajax_required(func):
    """
    AJAX リクエストのみを許可するデコレータ
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not request.is_json and not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            flash('無効なリクエストです。', 'error')
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    return wrapper

def log_access(func):
    """
    アクセスログを記録するデコレータ
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_info = f"User: {current_user.username} (ID: {current_user.id})" if current_user.is_authenticated else "Anonymous"
        logging.info(f"Access: {func.__name__} by {user_info} from {request.remote_addr}")
        return func(*args, **kwargs)
    return wrapper

def validate_school_access(func):
    """
    学校に所属するユーザーのみアクセス可能にするデコレータ
    """
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.school_id:
            flash('学校への所属が必要です。管理者にお問い合わせください。', 'error')
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    return wrapper

def safe_operation(flash_on_error=True):
    """
    安全な操作のためのデコレータ（データベースエラーハンドリング付き）
    """
    def decorator(func):
        @wraps(func)
        @handle_db_errors(flash_messages=flash_on_error)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator