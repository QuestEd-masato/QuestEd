# app/auth/secure_auth.py
"""
セキュリティ強化版認証システム
ブルートフォース攻撃対策、セッションハイジャック対策、CSRF対策を含む
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
import logging

from app.models import db, User, School
from app.auth.password_validator import validate_password
from app.utils.security_enhancements import (
    SecurityManager, InputValidator, SessionManager, PasswordSecurity,
    require_secure_auth, validate_csrf_token_required, rate_limit_by_user,
    log_security_event
)
from app.utils.rate_limiting import auth_limit
from app.utils.email_sender import send_confirmation_email, send_reset_password_email

secure_auth_bp = Blueprint('secure_auth', __name__)

@secure_auth_bp.route('/login', methods=['GET', 'POST'])
@auth_limit()
@validate_csrf_token_required
def secure_login():
    """セキュリティ強化版ログイン処理"""
    
    # ブルートフォース攻撃チェック
    if SecurityManager.is_ip_locked(request.remote_addr):
        log_security_event('brute_force_blocked', {
            'ip': request.remote_addr,
            'endpoint': 'login'
        })
        flash('アクセスが一時的に制限されています。しばらく後でお試しください。')
        return render_template('login.html'), 429
    
    if request.method == 'POST':
        # 入力値の取得とサニタイズ
        username = InputValidator.sanitize_input(request.form.get('username', ''), 50)
        password = request.form.get('password', '')
        
        # 入力検証
        is_valid_username, username_error = InputValidator.validate_username(username)
        if not is_valid_username:
            flash(username_error)
            SecurityManager.record_login_attempt(request.remote_addr, False)
            return render_template('login.html')
        
        # ユーザー検索
        user = User.query.filter_by(username=username).first()
        
        # パスワード検証
        if user and check_password_hash(user.password_hash, password):
            # メール確認チェック
            if not user.email_verified:
                log_security_event('login_attempt_unverified', {
                    'username': username,
                    'user_id': user.id
                })
                flash('アカウントが確認されていません。メールに送信された確認リンクをクリックしてください。')
                return redirect(url_for('secure_auth.verify_email', user_id=user.id))
            
            # 承認状態チェック（学生のみ）
            if user.role == 'student' and not user.is_approved:
                log_security_event('login_attempt_unapproved', {
                    'username': username,
                    'user_id': user.id
                })
                flash('アカウントはまだ承認されていません。教師の承認をお待ちください。')
                return redirect(url_for('secure_auth.awaiting_approval'))
            
            # セキュアなログイン処理
            login_user(user, remember=False)  # remember機能は無効化
            SessionManager.set_secure_session(user.id)
            
            # 成功ログ
            log_security_event('login_success', {
                'username': username,
                'user_id': user.id,
                'role': user.role
            })
            
            # ブルートフォース記録をクリア
            SecurityManager.record_login_attempt(request.remote_addr, True)
            
            # 最終ログイン時刻を更新
            user.last_login_at = datetime.utcnow()
            user.last_login_ip = request.remote_addr
            db.session.commit()
            
            # ロール別リダイレクト
            if user.role == 'student':
                return redirect(url_for('student.dashboard'))
            elif user.role == 'teacher':
                return redirect(url_for('teacher.dashboard'))
            elif user.role == 'admin':
                return redirect(url_for('admin_panel.dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            # ログイン失敗
            log_security_event('login_failure', {
                'username': username,
                'reason': 'invalid_credentials'
            })
            
            SecurityManager.record_login_attempt(request.remote_addr, False)
            flash('ユーザー名またはパスワードが正しくありません。')
    
    # CSRFトークンをセッションに設定
    session['csrf_token'] = SecurityManager.generate_secure_token()
    
    return render_template('login.html', csrf_token=session['csrf_token'])

@secure_auth_bp.route('/logout')
@login_required
@require_secure_auth
def secure_logout():
    """セキュアなログアウト処理"""
    user_id = current_user.id
    
    log_security_event('logout', {
        'user_id': user_id
    })
    
    # セッションを完全にクリア
    session.clear()
    logout_user()
    
    flash('ログアウトしました。')
    return redirect(url_for('secure_auth.secure_login'))

@secure_auth_bp.route('/register', methods=['GET', 'POST'])
@auth_limit()
@validate_csrf_token_required
def secure_register():
    """セキュリティ強化版新規登録処理"""
    
    if request.method == 'POST':
        # 入力値の取得とサニタイズ
        username = InputValidator.sanitize_input(request.form.get('username', ''), 50)
        full_name = InputValidator.sanitize_input(request.form.get('full_name', ''), 100)
        email = InputValidator.sanitize_input(request.form.get('email', ''), 254)
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'student')
        school_code = InputValidator.sanitize_input(request.form.get('school_code', ''), 10).upper()
        
        # 包括的入力検証
        validation_errors = []
        
        is_valid_username, username_error = InputValidator.validate_username(username)
        if not is_valid_username:
            validation_errors.append(username_error)
        
        is_valid_email, email_error = InputValidator.validate_email(email)
        if not is_valid_email:
            validation_errors.append(email_error)
        
        is_valid_school_code, school_error = InputValidator.validate_school_code(school_code)
        if not is_valid_school_code:
            validation_errors.append(school_error)
        
        if not full_name:
            validation_errors.append("氏名は必須です")
        
        # パスワード検証
        if password != confirm_password:
            validation_errors.append("パスワードが一致しません")
        
        is_strong_password, password_errors = PasswordSecurity.validate_password_strength(password)
        if not is_strong_password:
            validation_errors.extend(password_errors)
        
        # ロール検証
        if role not in ['student', 'teacher']:
            validation_errors.append("無効なロールです")
        
        # 検証エラーがある場合
        if validation_errors:
            for error in validation_errors:
                flash(error)
            return render_template('register.html', csrf_token=session.get('csrf_token'))
        
        # 重複チェック
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            log_security_event('registration_attempt_duplicate_username', {
                'username': username,
                'email': email
            })
            flash('そのユーザー名は既に使用されています。')
            return render_template('register.html', csrf_token=session.get('csrf_token'))
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            log_security_event('registration_attempt_duplicate_email', {
                'username': username,
                'email': email
            })
            flash('そのメールアドレスは既に使用されています。')
            return render_template('register.html', csrf_token=session.get('csrf_token'))
        
        # 学校存在確認
        school = School.query.filter_by(school_code=school_code).first()
        if not school:
            log_security_event('registration_attempt_invalid_school', {
                'username': username,
                'school_code': school_code
            })
            flash('入力された学校コードが見つかりません。')
            return render_template('register.html', csrf_token=session.get('csrf_token'))
        
        try:
            # メール確認トークンを生成
            email_token = SecurityManager.generate_secure_token()
            
            # 新規ユーザー作成
            new_user = User(
                username=username,
                full_name=full_name,
                password_hash=generate_password_hash(password),
                email=email,
                role=role,
                school_id=school.id,
                email_verified=False,  # メール確認必須
                email_token=SecurityManager.hash_token(email_token),  # ハッシュ化して保存
                token_created_at=datetime.utcnow(),
                is_approved=(role == 'teacher'),  # 教師は自動承認、学生は要承認
                created_at=datetime.utcnow(),
                created_ip=request.remote_addr
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            # 成功ログ
            log_security_event('registration_success', {
                'username': username,
                'email': email,
                'role': role,
                'user_id': new_user.id
            })
            
            # 確認メール送信
            try:
                send_confirmation_email(email, new_user.id, email_token, username)
                flash('登録が完了しました。メールに送信された確認リンクをクリックしてアカウントを有効化してください。')
            except Exception as e:
                logging.error(f"確認メール送信エラー: {e}")
                flash('登録は完了しましたが、確認メールの送信に失敗しました。管理者にお問い合わせください。')
            
            return redirect(url_for('secure_auth.verify_email', user_id=new_user.id))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"ユーザー登録エラー: {e}")
            log_security_event('registration_error', {
                'username': username,
                'error': str(e)
            })
            flash('登録処理中にエラーが発生しました。後でもう一度お試しください。')
            return render_template('register.html', csrf_token=session.get('csrf_token'))
    
    # CSRFトークン設定
    session['csrf_token'] = SecurityManager.generate_secure_token()
    return render_template('register.html', csrf_token=session['csrf_token'])

@secure_auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
@require_secure_auth
@rate_limit_by_user(max_requests=10, window_minutes=60)
@validate_csrf_token_required
def secure_change_password():
    """セキュアなパスワード変更処理"""
    
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # 現在のパスワード確認
        if not check_password_hash(current_user.password_hash, current_password):
            log_security_event('password_change_invalid_current', {
                'user_id': current_user.id
            })
            flash('現在のパスワードが正しくありません。')
            return render_template('change_password.html', csrf_token=session.get('csrf_token'))
        
        # 新しいパスワードの検証
        if new_password != confirm_password:
            flash('新しいパスワードが一致しません。')
            return render_template('change_password.html', csrf_token=session.get('csrf_token'))
        
        # パスワード強度チェック
        is_strong, password_errors = PasswordSecurity.validate_password_strength(new_password)
        if not is_strong:
            for error in password_errors:
                flash(error)
            return render_template('change_password.html', csrf_token=session.get('csrf_token'))
        
        # 現在のパスワードと同じかチェック
        if check_password_hash(current_user.password_hash, new_password):
            flash('新しいパスワードは現在のパスワードと異なる必要があります。')
            return render_template('change_password.html', csrf_token=session.get('csrf_token'))
        
        try:
            # パスワード更新
            current_user.password_hash = generate_password_hash(new_password)
            current_user.password_changed_at = datetime.utcnow()
            db.session.commit()
            
            log_security_event('password_change_success', {
                'user_id': current_user.id
            })
            
            # セッション再生成（セキュリティ強化）
            SessionManager.regenerate_session_id()
            
            flash('パスワードが正常に変更されました。')
            
            # ロール別リダイレクト
            if current_user.role == 'student':
                return redirect(url_for('student.dashboard'))
            elif current_user.role == 'teacher':
                return redirect(url_for('teacher.dashboard'))
            elif current_user.role == 'admin':
                return redirect(url_for('admin_panel.dashboard'))
            else:
                return redirect(url_for('index'))
                
        except Exception as e:
            db.session.rollback()
            logging.error(f"パスワード変更エラー: {e}")
            log_security_event('password_change_error', {
                'user_id': current_user.id,
                'error': str(e)
            })
            flash('パスワードの変更に失敗しました。')
    
    # CSRFトークン設定
    session['csrf_token'] = SecurityManager.generate_secure_token()
    return render_template('change_password.html', csrf_token=session['csrf_token'])

@secure_auth_bp.route('/verify_email/<int:user_id>')
def verify_email(user_id):
    """メール確認ページ"""
    user = User.query.get_or_404(user_id)
    
    if user.email_verified:
        flash('このアカウントは既に確認済みです。')
        return redirect(url_for('secure_auth.secure_login'))
    
    return render_template('verify_email.html', user=user)

@secure_auth_bp.route('/confirm_email/<int:user_id>/<token>')
@auth_limit()
def confirm_email(user_id, token):
    """メールアドレス確認処理"""
    user = User.query.get_or_404(user_id)
    
    # 既に確認済みの場合
    if user.email_verified:
        flash('このアカウントは既に確認済みです。')
        return redirect(url_for('secure_auth.secure_login'))
    
    # トークンの検証
    expected_token_hash = SecurityManager.hash_token(token)
    if not user.email_token or user.email_token != expected_token_hash:
        log_security_event('email_confirmation_invalid_token', {
            'user_id': user_id,
            'provided_token_hash': SecurityManager.hash_token(token)[:10]  # 最初の10文字のみログ
        })
        flash('無効または期限切れの確認リンクです。')
        return redirect(url_for('secure_auth.verify_email', user_id=user_id))
    
    # トークンの有効期限チェック（24時間）
    if user.token_created_at:
        token_age = datetime.utcnow() - user.token_created_at
        if token_age > timedelta(hours=24):
            log_security_event('email_confirmation_expired_token', {
                'user_id': user_id
            })
            flash('確認リンクの有効期限が切れています。新しいリンクを送信してください。')
            return redirect(url_for('secure_auth.verify_email', user_id=user_id))
    
    # メール確認を完了
    user.email_verified = True
    user.email_token = None
    user.token_created_at = None
    user.email_verified_at = datetime.utcnow()
    db.session.commit()
    
    log_security_event('email_confirmation_success', {
        'user_id': user_id
    })
    
    flash('メールアドレスが確認されました！')
    
    # 学生で承認待ちの場合
    if user.role == 'student' and not user.is_approved:
        flash('アカウントは教師の承認待ちです。承認されるまでお待ちください。')
        return redirect(url_for('secure_auth.awaiting_approval'))
    
    flash('ログインしてください。')
    return redirect(url_for('secure_auth.secure_login'))

@secure_auth_bp.route('/awaiting_approval')
def awaiting_approval():
    """承認待ちページ"""
    return render_template('awaiting_approval.html')