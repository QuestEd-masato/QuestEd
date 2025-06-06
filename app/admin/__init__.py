# app/admin/__init__.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime
import os
import csv
import io
import random
import string
import logging
from functools import wraps
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models import (
    db, User, School, SchoolYear, ClassGroup, StudentEnrollment,
    Class, ClassEnrollment, ActivityLog
)

admin_bp = Blueprint('admin_panel', __name__, url_prefix='/admin')

def admin_required(f):
    """管理者権限を要求するデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('この機能は管理者のみ利用可能です。')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """管理者ダッシュボード"""
    # ダッシュボード情報を取得
    user_count = User.query.count()
    class_count = Class.query.count()
    school_count = School.query.count()
    teacher_count = User.query.filter_by(role='teacher').count()
    
    return render_template('admin/dashboard.html', 
                          user_count=user_count, 
                          class_count=class_count,
                          school_count=school_count,
                          teacher_count=teacher_count)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """ユーザー一覧（学校情報含む）"""
    # ユーザーと学校情報をJOINして取得
    users = User.query.outerjoin(School, User.school_id == School.id).add_columns(
        User.id,
        User.username,
        User.email,
        User.role,
        User.created_at,
        User.is_approved,
        School.name.label('school_name'),
        School.code.label('school_code')
    ).all()
    
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """ユーザー削除"""
    # 削除対象のユーザーを取得
    user = User.query.get_or_404(user_id)
    
    # 自分自身は削除できないようにする
    if user.id == current_user.id:
        flash('自分自身を削除することはできません。')
        return redirect(url_for('admin_panel.users'))
    
    try:
        # 関連データの削除
        # ユーザーが教師の場合、教えているクラスを削除
        if user.role == 'teacher':
            classes = Class.query.filter_by(teacher_id=user.id).all()
            for class_obj in classes:
                db.session.delete(class_obj)
        
        # ユーザーが生徒の場合、関連データを削除
        if user.role == 'student':
            # アクティビティログに関連する画像ファイルを削除
            activity_logs = ActivityLog.query.filter_by(student_id=user.id).all()
            for log in activity_logs:
                if log.image_url:
                    # ファイルパスを構築
                    file_path = os.path.join('static', log.image_url.lstrip('/'))
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except Exception as e:
                            logging.error(f"画像ファイル削除エラー: {e}")
        
        # ユーザーを削除（関連データはカスケード削除される）
        db.session.delete(user)
        db.session.commit()
        
        flash(f'ユーザー "{user.username}" を削除しました。')
    except IntegrityError as e:
        db.session.rollback()
        logging.error(f"ユーザー削除時の整合性エラー: {e}")
        
        error_message = str(e.orig) if hasattr(e, 'orig') else str(e)
        if 'foreign key constraint' in error_message.lower() or 'cannot delete' in error_message.lower():
            flash(f'ユーザー "{user.username}" を削除できません。このユーザーに関連付けられたデータが存在します。先に関連データを削除してください。', 'error')
        else:
            flash(f'ユーザー "{user.username}" を削除できません。データベースの整合性制約に違反しています。', 'error')
    
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"ユーザー削除時のデータベースエラー: {e}")
        flash(f'ユーザー "{user.username}" の削除中にデータベースエラーが発生しました。', 'error')
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"ユーザー削除時の予期しないエラー: {e}")
        flash(f'ユーザー "{user.username}" の削除中に予期しないエラーが発生しました。', 'error')
    
    return redirect(url_for('admin_panel.users'))

# 学校関連のルートはschool_managementモジュールに移動









# ユーザー管理関連のルートはuser_managementモジュールに移動



# admin_accessルートはuser_managementモジュールに移動

# 追加のルートをインポート
from . import school_management
from . import user_management
from . import analytics