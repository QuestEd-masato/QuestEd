# app/special_routes.py
"""
特殊なルート（管理者アクセスなど）
"""
from flask import redirect, url_for, send_from_directory, abort, make_response
from flask_login import login_required, current_user
import os
import bleach

def register_special_routes(app):
    """特殊なルートを登録"""
    
    @app.after_request
    def set_security_headers(response):
        """セキュリティヘッダーを設定"""
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self'"
        )
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response
    
    @app.route('/uploads/<filename>')
    @login_required
    def secure_uploads(filename):
        """セキュアなファイル配信エンドポイント"""
        # ファイル名の検証
        if not filename or '..' in filename or '/' in filename:
            abort(403)
        
        # ユーザーの権限チェック（学生は自分の画像のみアクセス可能）
        from app.models import ActivityLog
        
        if current_user.role == 'student':
            # 学生は自分がアップロードした画像のみアクセス可能
            activity = ActivityLog.query.filter(
                ActivityLog.student_id == current_user.id,
                ActivityLog.image_url.like(f'%{filename}')
            ).first()
            if not activity:
                abort(403)
        elif current_user.role not in ['teacher', 'admin']:
            abort(403)
        
        upload_folder = app.config.get('SECURE_UPLOAD_FOLDER', app.config['UPLOAD_FOLDER'])
        file_path = os.path.join(upload_folder, filename)
        
        if not os.path.exists(file_path):
            abort(404)
        
        return send_from_directory(upload_folder, filename)
    
    @app.route('/admin_access')
    @login_required
    def admin_access():
        """管理者アクセス確認"""
        if current_user.role == 'admin':
            return redirect(url_for('admin_panel.dashboard'))
        else:
            return f"あなたは管理者ではありません。現在のロール: {current_user.role}, ID: {current_user.id}"