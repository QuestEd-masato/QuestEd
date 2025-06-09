# app/auth/__init__.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
import logging

from app.models import db, User, School
from app.auth.password_validator import validate_password, generate_secure_password
from app.utils.rate_limiting import auth_limit, api_limit
from app.utils.email_sender import send_confirmation_email, send_reset_password_email

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
@auth_limit()
def login():
    """ログイン処理"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            # メール確認状態をチェック
            if not user.email_confirmed:
                flash('アカウントが確認されていません。メールに送信された確認リンクをクリックしてください。')
                return redirect(url_for('auth.verify_email', user_id=user.id))
                
            # 承認状態をチェック（学生のみ）
            if user.role == 'student' and not user.is_approved:
                flash('アカウントはまだ承認されていません。教師の承認をお待ちください。')
                return redirect(url_for('auth.awaiting_approval'))
            
            # ログイン処理
            login_user(user)
            
            # ユーザーのロールに応じて適切なダッシュボードにリダイレクト
            if user.role == 'student':
                return redirect(url_for('student.dashboard'))
            elif user.role == 'teacher':
                return redirect(url_for('teacher.dashboard'))
            elif user.role == 'admin':
                return redirect(url_for('admin_panel.dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('ユーザー名またはパスワードが正しくありません。')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """ログアウト処理"""
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
@auth_limit()
def register():
    """新規登録処理"""
    try:
        if request.method == 'POST':
            username = request.form.get('username')
            full_name = request.form.get('full_name')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            email = request.form.get('email')
            role = request.form.get('role', 'student')
            school_code = request.form.get('school_code')
            
            # 入力検証
            if password != confirm_password:
                flash('パスワードが一致しません。')
                return render_template('register.html')
            
            # 既存ユーザー/メールチェック
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('そのユーザー名は既に使用されています。')
                return render_template('register.html')
            
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                flash('そのメールアドレスは既に使用されています。')
                return render_template('register.html')
            
            # 学校コードのチェック
            if not school_code:
                flash('学校コードは必須です。')
                return render_template('register.html')
                
            try:
                school = School.query.filter_by(code=school_code).first()
                if not school:
                    flash('入力された学校コードが見つかりません。')
                    return render_template('register.html')
                school_id = school.id
            except Exception as e:
                logging.error(f"学校情報取得エラー: {e}")
                flash('学校情報の取得に失敗しました。管理者にお問い合わせください。')
                return render_template('register.html')
            
            # パスワード強度チェック
            is_valid, password_errors = validate_password(password)
            if not is_valid:
                for error in password_errors:
                    flash(error)
                return render_template('register.html')
            
            # MVPモード: メール確認をバイパス
            new_user = User(
                username=username,
                full_name=full_name,
                password=generate_password_hash(password),
                email=email,
                role=role,
                school_id=school_id,
                email_confirmed=True,  # メール確認をスキップ
                email_token=None,
                token_created_at=None,
                is_approved=(role != 'student')  # 教師/管理者は自動承認
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            # オプションとしてメール送信を試み、失敗してもユーザー作成は続行
            try:
                # 確認用トークンを生成（念のため）
                token = secrets.token_urlsafe(32)
                
                # メール送信試行（送信エラーでも続行）
                send_confirmation_email(email, new_user.id, token, username)
                
                flash('登録が完了しました。ログインしてください。')
            except Exception as e:
                # メール送信失敗しても登録は完了
                logging.error(f"メール送信エラー: {e}")
                flash('登録は完了しましたが、確認メールの送信に失敗しました。ログインしてください。')
            
            # 学生の場合は承認待ち、それ以外はログインページへ
            if role == 'student' and not new_user.is_approved:
                return redirect(url_for('auth.awaiting_approval'))
            else:
                return redirect(url_for('auth.login'))
            
        return render_template('register.html')
        
    except Exception as e:
        logging.error(f"登録処理中に予期せぬエラーが発生しました: {e}")
        flash('処理中にエラーが発生しました。後でもう一度お試しいただくか、管理者にお問い合わせください。')
        return render_template('register.html')

@auth_bp.route('/verify_email/<int:user_id>')
def verify_email(user_id):
    """メール確認ページ"""
    user = User.query.get_or_404(user_id)
    return render_template('verify_email.html', user=user)

@auth_bp.route('/resend_verification/<int:user_id>')
@login_required
def resend_verification(user_id):
    """確認メール再送信"""
    if current_user.id != user_id:
        flash('権限がありません。')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    
    if user.email_confirmed:
        flash('このアカウントは既に確認済みです。')
        return redirect(url_for('auth.login'))
    
    try:
        # 新しいトークンを生成
        token = secrets.token_urlsafe(32)
        user.email_token = token
        user.token_created_at = datetime.utcnow()
        db.session.commit()
        
        # メール送信
        send_confirmation_email(user.email, user.id, token, user.username)
        
        flash('確認メールを再送信しました。メールボックスをご確認ください。')
    except Exception as e:
        logging.error(f"確認メール再送信エラー: {e}")
        flash('メールの送信に失敗しました。後でもう一度お試しください。')
    
    return redirect(url_for('auth.verify_email', user_id=user_id))

@auth_bp.route('/confirm_email/<int:user_id>/<token>')
def confirm_email(user_id, token):
    """メールアドレス確認処理"""
    user = User.query.get_or_404(user_id)
    
    # 既に確認済みの場合
    if user.email_confirmed:
        flash('このアカウントは既に確認済みです。')
        return redirect(url_for('auth.login'))
    
    # トークンの検証
    if not user.email_token or user.email_token != token:
        flash('無効または期限切れの確認リンクです。')
        return redirect(url_for('auth.verify_email', user_id=user_id))
    
    # トークンの有効期限をチェック（24時間）
    if user.token_created_at:
        token_age = datetime.utcnow() - user.token_created_at
        if token_age > timedelta(hours=24):
            flash('確認リンクの有効期限が切れています。新しいリンクを送信してください。')
            return redirect(url_for('auth.verify_email', user_id=user_id))
    
    # メール確認を完了
    user.email_confirmed = True
    user.email_token = None  # トークンをクリア
    user.token_created_at = None
    db.session.commit()
    
    flash('メールアドレスが確認されました！')
    
    # 学生で承認待ちの場合
    if user.role == 'student' and not user.is_approved:
        flash('アカウントは教師の承認待ちです。承認されるまでお待ちください。')
        return redirect(url_for('auth.awaiting_approval'))
    
    # ログインページへリダイレクト
    flash('ログインしてください。')
    return redirect(url_for('auth.login'))

@auth_bp.route('/awaiting_approval')
def awaiting_approval():
    """承認待ちページ"""
    return render_template('awaiting_approval.html')

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
@auth_limit()
def forgot_password():
    """パスワードリセットリクエスト"""
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # リセットトークンを生成
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_created_at = datetime.utcnow()
            db.session.commit()
            
            try:
                # パスワードリセットメールを送信
                send_reset_password_email(user.email, user.id, token, user.username)
                flash('パスワードリセット用のメールを送信しました。メールボックスをご確認ください。')
            except Exception as e:
                logging.error(f"パスワードリセットメール送信エラー: {e}")
                flash('メールの送信に失敗しました。後でもう一度お試しください。')
        else:
            # セキュリティのため、ユーザーが存在しない場合も同じメッセージを表示
            flash('パスワードリセット用のメールを送信しました。メールボックスをご確認ください。')
        
        return redirect(url_for('auth.login'))
    
    return render_template('forgot_password.html')

@auth_bp.route('/reset_password/<int:user_id>/<token>', methods=['GET', 'POST'])
@auth_limit()
def reset_password(user_id, token):
    """パスワードリセット処理"""
    user = User.query.get_or_404(user_id)
    
    # トークンの検証
    if not user.reset_token or user.reset_token != token:
        flash('無効または期限切れのリセットリンクです。')
        return redirect(url_for('auth.forgot_password'))
    
    # トークンの有効期限をチェック（1時間）
    if user.reset_token_created_at:
        token_age = datetime.utcnow() - user.reset_token_created_at
        if token_age > timedelta(hours=1):
            flash('リセットリンクの有効期限が切れています。もう一度お試しください。')
            return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('パスワードが一致しません。')
            return render_template('reset_password.html', user_id=user_id, token=token)
        
        # パスワード強度チェック
        is_valid, password_errors = validate_password(password)
        if not is_valid:
            for error in password_errors:
                flash(error)
            return render_template('reset_password.html', user_id=user_id, token=token)
        
        # パスワードを更新
        user.password = generate_password_hash(password)
        user.reset_token = None  # トークンをクリア
        user.reset_token_created_at = None
        db.session.commit()
        
        flash('パスワードが正常にリセットされました。新しいパスワードでログインしてください。')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', user_id=user_id, token=token)

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """パスワード変更処理"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # 現在のパスワードの確認
        if not check_password_hash(current_user.password, current_password):
            flash('現在のパスワードが正しくありません。')
            return render_template('change_password.html')
        
        # 新しいパスワードの検証
        if new_password != confirm_password:
            flash('新しいパスワードが一致しません。')
            return render_template('change_password.html')
        
        # パスワード強度チェック
        is_valid, password_errors = validate_password(new_password)
        if not is_valid:
            for error in password_errors:
                flash(error)
            return render_template('change_password.html')
        
        # パスワードを更新
        current_user.password = generate_password_hash(new_password)
        db.session.commit()
        
        flash('パスワードが正常に変更されました。')
        
        # ロールに応じて適切なダッシュボードにリダイレクト
        if current_user.role == 'student':
            return redirect(url_for('student.dashboard'))
        elif current_user.role == 'teacher':
            return redirect(url_for('teacher.dashboard'))
        elif current_user.role == 'admin':
            return redirect(url_for('admin_panel.dashboard'))
        else:
            return redirect(url_for('index'))
    
    return render_template('change_password.html')

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """ユーザープロフィール表示・編集"""
    if request.method == 'POST':
        # フォームデータ取得
        username = request.form.get('username')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        
        # 入力検証
        if not username or not email:
            flash('ユーザー名とメールアドレスは必須です。')
            return render_template('profile.html', user=current_user)
        
        # 他のユーザーとの重複チェック（自分以外）
        existing_user = User.query.filter(
            User.username == username,
            User.id != current_user.id
        ).first()
        if existing_user:
            flash('そのユーザー名は既に使用されています。')
            return render_template('profile.html', user=current_user)
        
        existing_email = User.query.filter(
            User.email == email,
            User.id != current_user.id
        ).first()
        if existing_email:
            flash('そのメールアドレスは既に使用されています。')
            return render_template('profile.html', user=current_user)
        
        try:
            # ユーザー情報を更新
            current_user.username = username
            current_user.full_name = full_name
            current_user.email = email
            db.session.commit()
            
            flash('プロフィールが更新されました。')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"プロフィール更新エラー: {e}")
            flash('プロフィールの更新に失敗しました。')
            return render_template('profile.html', user=current_user)
    
    # GETリクエスト: プロフィール表示
    return render_template('profile.html', user=current_user)