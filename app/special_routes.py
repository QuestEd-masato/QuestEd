# app/special_routes.py
"""
特殊なルート（管理者アクセスなど）
"""
from flask import redirect, url_for
from flask_login import login_required, current_user

def register_special_routes(app):
    """特殊なルートを登録"""
    
    @app.route('/admin_access')
    @login_required
    def admin_access():
        """管理者アクセス確認"""
        if current_user.role == 'admin':
            return redirect(url_for('admin_panel.dashboard'))
        else:
            return f"あなたは管理者ではありません。現在のロール: {current_user.role}, ID: {current_user.id}"