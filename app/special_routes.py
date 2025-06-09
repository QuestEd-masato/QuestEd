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
    
    @app.route('/uploads/<path:filepath>')
    @login_required
    def secure_uploads(filepath):
        """セキュアなファイル配信エンドポイント（ユーザーディレクトリ対応）"""
        # ファイルパスの検証
        if not filepath or '..' in filepath:
            abort(403)
        
        # パスを分割（user_id/filename または filename）
        path_parts = filepath.split('/')
        if len(path_parts) == 2:
            user_id, filename = path_parts
            try:
                user_id = int(user_id)
            except ValueError:
                abort(403)
        elif len(path_parts) == 1:
            user_id = None
            filename = path_parts[0]
        else:
            abort(403)
        
        # ファイル名の追加検証
        if not filename or '/' in filename or '\\' in filename:
            abort(403)
        
        # ユーザーの権限チェック
        from app.models import ActivityLog
        
        if current_user.role == 'student':
            # 学生は自分のディレクトリの画像のみアクセス可能
            if user_id != current_user.id:
                abort(403)
            
            # 自分がアップロードした画像か確認
            activity = ActivityLog.query.filter(
                ActivityLog.student_id == current_user.id,
                ActivityLog.image_url.like(f'%{filename}')
            ).first()
            if not activity:
                abort(403)
        elif current_user.role not in ['teacher', 'admin']:
            abort(403)
        
        # ファイルパスの構築
        upload_folder = app.config.get('SECURE_UPLOAD_FOLDER', app.config['UPLOAD_FOLDER'])
        if user_id:
            file_path = os.path.join(upload_folder, str(user_id), filename)
        else:
            file_path = os.path.join(upload_folder, filename)
        
        if not os.path.exists(file_path):
            abort(404)
        
        # セキュリティヘッダーを追加
        response = make_response(send_from_directory(
            os.path.dirname(file_path), 
            os.path.basename(file_path)
        ))
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Disposition'] = 'inline'
        
        return response
    
    @app.route('/admin_access')
    @login_required
    def admin_access():
        """管理者アクセス確認"""
        if current_user.role == 'admin':
            return redirect(url_for('admin_panel.dashboard'))
        else:
            return f"あなたは管理者ではありません。現在のロール: {current_user.role}, ID: {current_user.id}"