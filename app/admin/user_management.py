# app/admin/user_management.py
"""
ユーザー管理関連のルート
"""
from flask import render_template, redirect, url_for, flash, request, send_file, make_response
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
import csv
import io
import string
import secrets
from app.models import User, db
from app.admin import admin_bp, admin_required
from app.auth.password_validator import generate_secure_password
from app.utils.file_security import file_validator
from app.utils.email_sender import send_confirmation_email
import logging

# CSVファイルの拡張子チェック用関数
def allowed_csv_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'

# ランダムなパスワード生成関数（セキュア版）
def generate_random_password(length=16):
    """
    セキュアなランダムパスワードを生成
    
    Args:
        length (int): パスワードの長さ（最小12文字）
        
    Returns:
        str: 生成されたパスワード
    """
    return generate_secure_password(max(12, length))

# ユーザー一括インポート
@admin_bp.route('/import_users', methods=['GET', 'POST'])
@login_required
@admin_required
def import_users():
    """ユーザー一括インポート"""
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('CSVファイルが選択されていません。')
            return redirect(request.url)
        
        file = request.files['csv_file']
        
        if file.filename == '':
            flash('CSVファイルが選択されていません。')
            return redirect(request.url)
        
        # 新しいセキュリティバリデーターを使用
        is_valid, error_message, csv_content = file_validator.validate_csv(
            file.stream, file.filename
        )
        
        if not is_valid:
            flash(f'CSVファイルエラー: {error_message}')
            return redirect(request.url)
        
        if is_valid:
            try:
                # CSVファイルを読み込む
                stream = io.StringIO(csv_content)
                csv_reader = csv.DictReader(stream)
                
                # ヘッダー情報をログに出力
                current_app.logger.info(f"CSV fieldnames: {csv_reader.fieldnames}")
                flash(f"CSVヘッダー: {csv_reader.fieldnames}", 'info')  # デバッグ用
                
                # 成功と失敗のカウンター
                success_count = 0
                error_count = 0
                error_messages = []
                
                # CSVの各行を処理
                for row_num, row in enumerate(csv_reader, start=2):  # ヘッダーを飛ばして2行目から
                    try:
                        # デバッグ: 元のrow内容を出力
                        current_app.logger.debug(f"Row {row_num} original: {row}")
                        
                        # カラム名の正規化（空白除去、小文字化）
                        normalized_row = {}
                        for key, value in row.items():
                            if key:  # Noneキーを除外
                                normalized_key = key.strip().lower().replace(' ', '_')
                                normalized_row[normalized_key] = value.strip() if value else ''
                        
                        current_app.logger.debug(f"Row {row_num} normalized: {normalized_row}")
                        
                        # 正規化されたキーで取得
                        username = str(normalized_row.get('username', '')).strip()
                        full_name = normalized_row.get('full_name', '').strip()
                        email = normalized_row.get('email', '').strip()
                        password = normalized_row.get('password', '').strip()
                        role = normalized_row.get('role', 'student').strip()
                        school_id = normalized_row.get('school_id', '').strip()
                        
                        # 必須項目の確認
                        if not username or not email or not role:
                            error_count += 1
                            error_messages.append(f"行: {row_num} - ユーザー名、メールアドレス、ロールは必須です。")
                            continue
                        
                        # 数値ユーザー名の文字列変換
                        username = str(username)
                        
                        # 既存ユーザーのチェック
                        existing_user = User.query.filter(
                            (User.username == username) | (User.email == email)
                        ).first()
                        
                        if existing_user:
                            error_count += 1
                            error_messages.append(f"行: {row_num} - ユーザー名またはメールアドレスが既に使用されています: {username}, {email}")
                            continue
                        
                        # 学校IDの処理
                        try:
                            school_id = int(school_id) if school_id else None
                        except ValueError:
                            school_id = None
                        
                        # パスワードの生成または取得
                        if not password:
                            password = generate_random_password()
                        
                        # ユーザー作成
                        new_user = User(
                            username=username,
                            full_name=full_name or username,  # full_nameがない場合はusernameを使用
                            email=email,
                            password=generate_password_hash(password),
                            role=role,
                            school_id=school_id,
                            email_confirmed=True,  # CSV登録ユーザーは確認済み
                            is_approved=(role != 'student')  # 学生以外は自動承認
                        )
                        
                        db.session.add(new_user)
                        db.session.flush()  # ユーザーIDを取得するため
                        
                        # 確認メール送信を試行
                        try:
                            token = secrets.token_urlsafe(32)
                            send_confirmation_email(
                                new_user.email, 
                                new_user.id, 
                                token, 
                                new_user.username
                            )
                        except Exception as e:
                            logging.warning(f"Failed to send confirmation email to {new_user.email}: {str(e)}")
                        
                        success_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        error_messages.append(f"行: {row_num} - エラー: {str(e)}")
                        db.session.rollback()  # エラー時はロールバック
                
                # 変更をコミット
                if success_count > 0:
                    try:
                        db.session.commit()
                        flash(f'{success_count}人のユーザーを正常にインポートしました。', 'success')
                    except Exception as e:
                        db.session.rollback()
                        flash(f'データベースへの保存中にエラーが発生しました: {str(e)}', 'error')
                        return redirect(url_for('admin_panel.import_users'))
                
                if error_count > 0:
                    flash(f'{error_count}件のエラーが発生しました。', 'warning')
                    for msg in error_messages[:10]:  # 最初の10件のエラーのみ表示
                        flash(msg, 'error')
                    if len(error_messages) > 10:
                        flash(f'他に{len(error_messages) - 10}件のエラーがあります。', 'warning')
                
                return redirect(url_for('admin_panel.users'))
                
            except Exception as e:
                flash(f'CSVファイルの処理中にエラーが発生しました: {str(e)}')
                return redirect(request.url)
        else:
            flash('CSVファイルの形式が正しくありません。')
            return redirect(request.url)
    
    # GETリクエスト処理（フォーム表示）
    return render_template('admin/import_users.html')

# ユーザーインポート用CSVテンプレートダウンロード
@admin_bp.route('/download_user_template')
@login_required
@admin_required
def download_user_template():
    """ユーザーインポート用CSVテンプレートダウンロード"""
    # CSVデータを作成
    csv_data = io.StringIO()
    csv_writer = csv.writer(csv_data)
    
    # ヘッダー行
    csv_writer.writerow(['username', 'full_name', 'email', 'password', 'role', 'school_id'])
    
    # サンプル行
    csv_writer.writerow(['taro_yamada', '山田太郎', 'taro@example.com', 'password123', 'student', '1'])
    csv_writer.writerow(['hanako_tanaka', '田中花子', 'hanako@example.com', 'password456', 'teacher', '1'])
    csv_writer.writerow(['admin_user', '管理者', 'admin@example.com', 'adminpass', 'admin', ''])
    
    # CSVデータを取得
    csv_data.seek(0)
    output = make_response(csv_data.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=user_import_template.csv"
    output.headers["Content-type"] = "text/csv"
    
    return output

# 管理者アクセスページ
@admin_bp.route('/access')
def admin_access():
    """管理者アクセスページ（管理者以外もアクセス可能）"""
    return render_template('admin/access.html')