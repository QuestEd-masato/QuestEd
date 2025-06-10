"""
データベース操作のユーティリティとエラーハンドリング
"""
import logging
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from flask import flash, current_app
from extensions import db

def handle_db_errors(flash_messages=True):
    """
    データベース操作のエラーハンドリングデコレータ
    
    Args:
        flash_messages (bool): エラーメッセージをフラッシュメッセージとして表示するか
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except OperationalError as e:
                db.session.rollback()
                error_msg = "データベース接続エラーが発生しました。時間をおいて再試行してください。"
                logging.error(f"Database connection error in {func.__name__}: {str(e)}")
                if flash_messages:
                    flash(error_msg, 'error')
                return None
            except IntegrityError as e:
                db.session.rollback()
                error_msg = "データの整合性エラーが発生しました。入力内容を確認してください。"
                logging.error(f"Database integrity error in {func.__name__}: {str(e)}")
                if flash_messages:
                    flash(error_msg, 'error')
                return None
            except SQLAlchemyError as e:
                db.session.rollback()
                error_msg = "データベース操作でエラーが発生しました。"
                logging.error(f"Database error in {func.__name__}: {str(e)}")
                if flash_messages:
                    flash(error_msg, 'error')
                return None
            except Exception as e:
                db.session.rollback()
                error_msg = "予期しないエラーが発生しました。"
                logging.error(f"Unexpected error in {func.__name__}: {str(e)}")
                if flash_messages:
                    flash(error_msg, 'error')
                return None
        return wrapper
    return decorator

def safe_commit():
    """
    安全なコミット操作
    
    Returns:
        bool: コミットが成功したかどうか
    """
    try:
        db.session.commit()
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"Commit failed: {str(e)}")
        return False

def safe_add(instance):
    """
    安全なインスタンス追加
    
    Args:
        instance: 追加するインスタンス
        
    Returns:
        bool: 追加が成功したかどうか
    """
    try:
        db.session.add(instance)
        return True
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"Add failed: {str(e)}")
        return False

def get_db_health():
    """
    データベース接続の健全性チェック
    
    Returns:
        dict: 健全性の情報
    """
    try:
        # 簡単なクエリを実行してDB接続をテスト
        result = db.session.execute('SELECT 1').fetchone()
        return {
            'status': 'healthy',
            'message': 'Database connection is working',
            'result': result[0] if result else None
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'message': f'Database connection failed: {str(e)}',
            'result': None
        }