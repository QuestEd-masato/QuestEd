# app/student/__init__.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, session, Response, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import json
import io
import csv
import logging
import imghdr
import uuid
import traceback
from sqlalchemy import text, func

# ReportLabを条件付きでインポート（PDF生成用）
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logging.warning("ReportLab not available. PDF export will be disabled.")

from app.models import (
    db, User, Class, ClassEnrollment, MainTheme, InquiryTheme,
    InterestSurvey, PersonalitySurvey, ActivityLog, Todo, Goal,
    Milestone, Group, GroupMembership, ChatHistory
)
from app.ai import generate_personal_themes_with_ai
from app.utils.rate_limiting import upload_limit, api_limit
from app.utils.file_security import file_validator

student_bp = Blueprint('student', __name__)

# ファイルアップロード設定
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    """ファイル拡張子が許可されているか確認"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_image(stream):
    """画像ファイルのヘッダーを検証"""
    header = stream.read(512)
    stream.seek(0)
    format = imghdr.what(None, header)
    if not format:
        return None
    return '.' + format if format in ALLOWED_EXTENSIONS else None

def student_required(f):
    """学生権限を要求するデコレータ"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            flash('この機能は学生のみ利用可能です。')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@student_bp.route('/dashboard')
@student_bp.route('/student_dashboard')  # 両方のURLパターンをサポート
@login_required
@student_required
def dashboard():
    """生徒ダッシュボード - リアルタイム更新版"""
    
    # データベースキャッシュをクリア（重要）
    db.session.expire_all()
    db.session.commit()  # 未コミットのトランザクションをクリア
    
    # コンテキスト辞書を初期化
    context = {
        # 基本情報
        'current_user': current_user,
        
        # アンケート情報
        'interest_survey': None,
        'personality_survey': None,
        
        # テーマ情報
        'selected_theme': None,
        
        # 活動記録
        'recent_activities': [],
        'weekly_activities_count': 0,
        
        # ToDo/目標
        'pending_todos_count': 0,
        'active_goals_count': 0,
        'recent_todo': None,
        'recent_goal': None,
        'class_todos': [],  # クラスごとの最新ToDo
        'class_goals': [],  # クラスごとの最新目標
        
        # チャット使用状況
        'monthly_chat_count': 0,
        
        # ランキング
        'class_top_learners': [],
        'weekly_top_learners': [],
        'weekly_words_learned': 0,
        'weekly_target': 50,
        
        # クラス情報
        'class_info': None,
        
        # 複数クラステーマ
        'all_class_themes': [],
        
        # ベースビルダー情報
        'weekly_training_count': 0,
        'training_completion_rate': 0,
        'recent_training': None,
        'delivered_texts': [],
        'last_updated': datetime.now().strftime('%H:%M:%S')  # 更新時刻を追加
    }
    
    try:
        
        # アンケート情報の取得
        context['interest_survey'] = InterestSurvey.query.filter_by(
            student_id=current_user.id
        ).first()
        
        context['personality_survey'] = PersonalitySurvey.query.filter_by(
            student_id=current_user.id
        ).first()
        
        # 選択中のテーマ
        context['selected_theme'] = InquiryTheme.query.filter_by(
            student_id=current_user.id,
            is_selected=True
        ).first()
        
        # 最近の活動記録
        context['recent_activities'] = ActivityLog.query.filter_by(
            student_id=current_user.id
        ).order_by(ActivityLog.timestamp.desc()).limit(5).all()
        
        # 今週の活動数
        one_week_ago = datetime.now() - timedelta(days=7)
        context['weekly_activities_count'] = ActivityLog.query.filter(
            ActivityLog.student_id == current_user.id,
            ActivityLog.timestamp >= one_week_ago
        ).count()
        
        # クラス情報を取得（JOIN最適化）
        try:
            # ClassEnrollmentテーブルから現在のクラス情報を取得
            enrollment = ClassEnrollment.query.options(
                db.joinedload(ClassEnrollment.class_obj).joinedload(Class.teacher)
            ).filter_by(
                student_id=current_user.id,
                is_active=True
            ).first()
            
            if enrollment and enrollment.class_obj:
                class_obj = enrollment.class_obj
                context['class_info'] = {
                    'class_name': class_obj.name,
                    'teacher_name': class_obj.teacher.display_name if class_obj.teacher else None,
                    'subject_name': getattr(class_obj.subject, 'name', None) if hasattr(class_obj, 'subject') else None
                }
        except Exception as e:
            current_app.logger.warning(f"Could not fetch class info: {str(e)}")
        
        # word_proficiencyテーブルが存在するか確認
        has_word_proficiency = False
        try:
            # テーブルの存在確認（よりセキュアな方法）
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            has_word_proficiency = 'word_proficiency' in inspector.get_table_names()
        except Exception as e:
            current_app.logger.debug(f"Table existence check failed: {str(e)}")
            pass
        
        # ランキング機能（複数テーブル対応）
        try:
            # 現在のクラスメイトのIDリストを取得
            classmate_ids = []
            current_app.logger.info(f"Enrollment status: {enrollment is not None}")
            
            if enrollment:
                classmates = User.query.join(ClassEnrollment).filter(
                    ClassEnrollment.class_id == enrollment.class_id,
                    ClassEnrollment.is_active == True,
                    User.role == 'student'
                ).all()
                classmate_ids = [u.id for u in classmates]
                current_app.logger.info(f"Found {len(classmate_ids)} classmates in class {enrollment.class_id}")
            else:
                current_app.logger.warning("No enrollment found for current user")
            
            if classmate_ids:
                table_names = inspector.get_table_names()
                
                # word_proficiency_recordsテーブルを優先的に使用
                if 'word_proficiency_records' in table_names:
                    current_app.logger.info("Using word_proficiency_records for ranking")
                    
                    # 総合ランキング
                    ranking_query = text("""
                        SELECT 
                            u.id,
                            u.username,
                            u.full_name,
                            COUNT(DISTINCT CASE WHEN wpr.level >= 5 THEN wpr.problem_id END) as word_count
                        FROM users u
                        LEFT JOIN word_proficiency_records wpr ON u.id = wpr.student_id
                        WHERE u.id IN :user_ids
                        GROUP BY u.id, u.username, u.full_name
                        ORDER BY word_count DESC, u.username ASC
                        LIMIT 10
                    """)
                    
                    class_rankings_result = db.session.execute(
                        ranking_query,
                        {"user_ids": tuple(classmate_ids)}
                    ).fetchall()
                    
                    # 週間ランキング
                    one_week_ago = datetime.now() - timedelta(days=7)
                    weekly_query = text("""
                        SELECT 
                            u.id,
                            u.username,
                            u.full_name,
                            COUNT(DISTINCT wpr.problem_id) as word_count
                        FROM users u
                        LEFT JOIN word_proficiency_records wpr ON u.id = wpr.student_id
                        WHERE u.id IN :user_ids
                        AND wpr.level >= 5
                        AND wpr.last_updated >= :one_week_ago
                        GROUP BY u.id, u.username, u.full_name
                        ORDER BY word_count DESC, u.username ASC
                        LIMIT 10
                    """)
                    
                    weekly_rankings_result = db.session.execute(
                        weekly_query,
                        {"user_ids": tuple(classmate_ids), "one_week_ago": one_week_ago}
                    ).fetchall()
                    
                elif 'word_proficiency' in table_names:
                    current_app.logger.info("Using word_proficiency for ranking")
                    
                    # 総合ランキング（proficiency_level = 5の単語数）
                    ranking_query = text("""
                        SELECT 
                            u.id,
                            u.username,
                            u.full_name,
                            COUNT(DISTINCT CASE WHEN wp.proficiency_level = 5 THEN wp.word_id END) as word_count
                        FROM users u
                        LEFT JOIN word_proficiency wp ON u.id = wp.user_id
                        WHERE u.id IN :user_ids
                        GROUP BY u.id, u.username, u.full_name
                        ORDER BY word_count DESC, u.username ASC
                        LIMIT 10
                    """)
                    
                    class_rankings_result = db.session.execute(
                        ranking_query,
                        {"user_ids": tuple(classmate_ids)}
                    ).fetchall()
                    
                    # 週間ランキング（今週5/5になった単語数）
                    one_week_ago = datetime.now() - timedelta(days=7)
                    weekly_query = text("""
                        SELECT 
                            u.id,
                            u.username,
                            u.full_name,
                            COUNT(DISTINCT wp.word_id) as word_count
                        FROM users u
                        LEFT JOIN word_proficiency wp ON u.id = wp.user_id
                        WHERE u.id IN :user_ids
                        AND wp.proficiency_level = 5
                        AND wp.last_reviewed >= :one_week_ago
                        GROUP BY u.id, u.username, u.full_name
                        ORDER BY word_count DESC, u.username ASC
                        LIMIT 10
                    """)
                    
                    weekly_rankings_result = db.session.execute(
                        weekly_query,
                        {"user_ids": tuple(classmate_ids), "one_week_ago": one_week_ago}
                    ).fetchall()
                    
                else:
                    # テーブルがない場合はクラスメイトのみ表示
                    current_app.logger.info("No word proficiency tables found, showing classmates only")
                    class_rankings_result = [(u.id, u.username, u.full_name, 0) for u in classmates[:10]]
                    weekly_rankings_result = [(u.id, u.username, u.full_name, 0) for u in classmates[:10]]
            else:
                # クラスメイトがいない場合は自分だけを表示
                current_app.logger.info("No classmates found, showing current user only")
                class_rankings_result = [(current_user.id, current_user.username, current_user.full_name or current_user.username, 0)]
                weekly_rankings_result = [(current_user.id, current_user.username, current_user.full_name or current_user.username, 0)]
            
            # 結果をcontextに設定（classmate_idsの有無に関わらず）
            if 'class_rankings_result' in locals():
                class_top_learners = [
                    {
                        'id': r.id if hasattr(r, 'id') else r[0],
                        'username': r.username if hasattr(r, 'username') else r[1],
                        'full_name': r.full_name if hasattr(r, 'full_name') else r[2],
                        'word_count': r.word_count if hasattr(r, 'word_count') else r[3]
                    } for r in class_rankings_result
                ]
                context['class_top_learners'] = class_top_learners
            
            if 'weekly_rankings_result' in locals():
                weekly_top_learners = [
                    {
                        'id': r.id if hasattr(r, 'id') else r[0],
                        'username': r.username if hasattr(r, 'username') else r[1],
                        'full_name': r.full_name if hasattr(r, 'full_name') else r[2],
                        'word_count': r.word_count if hasattr(r, 'word_count') else r[3]
                    } for r in weekly_rankings_result
                ]
                context['weekly_top_learners'] = weekly_top_learners
                    
        except Exception as e:
            current_app.logger.warning(f"Could not fetch rankings: {str(e)}")
        
        # ToDoカウントと最新ToDo
        try:
            context['pending_todos_count'] = Todo.query.filter_by(
                student_id=current_user.id,
                is_completed=False
            ).count()
            
            # 最新の未完了ToDo（期限が近いものを優先）
            context['recent_todo'] = Todo.query.filter_by(
                student_id=current_user.id,
                is_completed=False
            ).order_by(
                Todo.due_date.asc().nullslast(),
                Todo.created_at.desc()
            ).first()
            
        except Exception as e:
            current_app.logger.debug(f"Could not fetch todo count: {str(e)}")
        
        # 目標カウントと最新目標
        try:
            context['active_goals_count'] = Goal.query.filter_by(
                student_id=current_user.id,
                is_completed=False
            ).count()
            
            # 最新の進行中目標（期限が近いものを優先）
            context['recent_goal'] = Goal.query.filter_by(
                student_id=current_user.id,
                is_completed=False
            ).order_by(
                Goal.due_date.asc().nullslast(),
                Goal.last_updated.desc()
            ).first()
            
        except Exception as e:
            current_app.logger.debug(f"Could not fetch goal count: {str(e)}")
        
        # チャット使用回数（今月）
        try:
            this_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            context['monthly_chat_count'] = ChatHistory.query.filter(
                ChatHistory.user_id == current_user.id,
                ChatHistory.timestamp >= this_month_start
            ).count()
        except Exception as e:
            current_app.logger.debug(f"Could not fetch chat count: {str(e)}")
        
        # 複数クラスのテーマ情報を取得
        try:
            # 所属している全クラスを取得
            all_enrollments = ClassEnrollment.query.options(
                db.joinedload(ClassEnrollment.class_obj)
            ).filter_by(
                student_id=current_user.id,
                is_active=True
            ).all()
            
            all_class_themes = []
            for enrollment in all_enrollments:
                class_obj = enrollment.class_obj
                if class_obj:
                    # このクラスで選択中のテーマを取得
                    selected_theme_for_class = InquiryTheme.query.filter_by(
                        student_id=current_user.id,
                        class_id=class_obj.id,
                        is_selected=True
                    ).first()
                    
                    all_class_themes.append({
                        'class_name': class_obj.name,
                        'class_id': class_obj.id,
                        'theme_title': selected_theme_for_class.title if selected_theme_for_class else None
                    })
            
            context['all_class_themes'] = all_class_themes
            
            # クラスごとの最新ToDo・目標を取得
            class_todos = []
            class_goals = []
            
            for enrollment in all_enrollments:
                class_obj = enrollment.class_obj
                if class_obj:
                    # このクラスの最新ToDo
                    latest_todo = Todo.query.filter_by(
                        student_id=current_user.id,
                        class_id=class_obj.id,
                        is_completed=False
                    ).order_by(
                        Todo.due_date.asc().nullslast(),
                        Todo.created_at.desc()
                    ).first()
                    
                    if latest_todo:
                        class_todos.append({
                            'class_name': class_obj.name,
                            'class_id': class_obj.id,
                            'todo': latest_todo
                        })
                    
                    # このクラスの最新目標
                    latest_goal = Goal.query.filter_by(
                        student_id=current_user.id,
                        class_id=class_obj.id,
                        is_completed=False
                    ).order_by(
                        Goal.due_date.asc().nullslast(),
                        Goal.last_updated.desc()
                    ).first()
                    
                    if latest_goal:
                        class_goals.append({
                            'class_name': class_obj.name,
                            'class_id': class_obj.id,
                            'goal': latest_goal
                        })
            
            context['class_todos'] = class_todos
            context['class_goals'] = class_goals
            
        except Exception as e:
            current_app.logger.debug(f"Could not fetch all class themes: {str(e)}")
        
        # ベースビルダー情報を取得
        try:
            # 今週のトレーニング回数
            one_week_ago = datetime.now() - timedelta(days=7)
            
            # ProficiencyRecordテーブルが存在するかチェック
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            table_names = inspector.get_table_names()
            
            if 'proficiency_record' in table_names:
                # 今週のトレーニング回数（ProficiencyRecordから）
                training_count_query = text("""
                    SELECT COUNT(*) as count 
                    FROM proficiency_record 
                    WHERE user_id = :user_id 
                    AND completed_at >= :one_week_ago
                """)
                
                result = db.session.execute(
                    training_count_query,
                    {"user_id": current_user.id, "one_week_ago": one_week_ago}
                ).first()
                
                context['weekly_training_count'] = result.count if result else 0
                
                # 最新のトレーニング記録
                recent_training_query = text("""
                    SELECT pr.*, bki.title as category 
                    FROM proficiency_record pr
                    LEFT JOIN basic_knowledge_item bki ON pr.item_id = bki.id
                    WHERE pr.user_id = :user_id 
                    ORDER BY pr.completed_at DESC 
                    LIMIT 1
                """)
                
                recent_result = db.session.execute(
                    recent_training_query,
                    {"user_id": current_user.id}
                ).first()
                
                if recent_result:
                    context['recent_training'] = {
                        'category': recent_result.category or 'トレーニング',
                        'completed_at': recent_result.completed_at
                    }
                
                # 達成率計算（今週の目標を10回と仮定）
                weekly_target = 10
                completion_rate = min(100, int((context['weekly_training_count'] / weekly_target) * 100)) if weekly_target > 0 else 0
                context['training_completion_rate'] = completion_rate
            
            # 配信されたテキスト情報を取得（キャッシュを使わない）
            if 'text_delivery' in table_names and 'text_set' in table_names:
                # 所属クラスを再取得（キャッシュを避ける）
                all_enrollments = db.session.query(ClassEnrollment).filter_by(
                    student_id=current_user.id,
                    is_active=True
                ).options(db.lazyload('*')).all()  # リレーションを遅延読み込み
                
                enrolled_class_ids = [e.class_id for e in all_enrollments]
                
                if enrolled_class_ids:
                    # 配信テキストを最新順で取得（FORCE INDEXヒント相当）
                    delivered_texts_query = text("""
                        SELECT DISTINCT
                            td.id as delivery_id,
                            ts.title as text_name,
                            ts.id as text_set_id,
                            td.delivered_at,
                            COALESCE(tpr.understanding_level, 0) as understanding_level,
                            tpr.completed_at,
                            td.last_updated
                        FROM text_delivery td
                        INNER JOIN text_set ts ON td.text_set_id = ts.id
                        LEFT JOIN text_proficiency_record tpr ON (
                            tpr.text_set_id = ts.id AND
                            tpr.user_id = :user_id
                        )
                        WHERE td.class_id IN :class_ids
                        AND td.is_active = 1
                        ORDER BY td.delivered_at DESC, td.last_updated DESC
                        LIMIT 5
                    """)
                    
                    # 新しいセッションで実行（キャッシュ回避）
                    with db.session.no_autoflush:
                        texts_result = db.session.execute(
                            delivered_texts_query,
                            {"user_id": current_user.id, "class_ids": tuple(enrolled_class_ids)}
                        ).fetchall()
                    
                    delivered_texts = []
                    for row in texts_result:
                        delivered_texts.append({
                            'text_name': row.text_name,
                            'text_set_id': row.text_set_id,
                            'delivered_at': row.delivered_at,
                            'understanding_level': int(row.understanding_level) if row.understanding_level else 0,
                            'completed_at': row.completed_at,
                            'is_completed': row.completed_at is not None,
                            'last_updated': row.last_updated  # 更新時刻を追加
                        })
                    
                    context['delivered_texts'] = delivered_texts
                    
                    # デバッグログ
                    current_app.logger.info(f"Delivered texts count: {len(delivered_texts)}")
                    
            # デフォルト値を設定
            context['total_mastered_words'] = 0
            context['weekly_words_learned'] = 0
            context['total_words_attempted'] = 0
            context['mastery_rate'] = 0
            context['weekly_target'] = 50
            
            # word_proficiency_recordsテーブルを優先的に使用
            if 'word_proficiency_records' in table_names:
                current_app.logger.info("Using word_proficiency_records table")
                
                # 総マスター単語数（レベル5）
                total_mastered_query = text("""
                    SELECT COUNT(DISTINCT problem_id) as count
                    FROM word_proficiency_records
                    WHERE student_id = :user_id
                    AND level >= 5
                """)
                
                result = db.session.execute(
                    total_mastered_query,
                    {"user_id": current_user.id}
                ).first()
                
                context['total_mastered_words'] = result.count if result and result.count else 0
                
                # 今週マスターした単語数
                one_week_ago = datetime.now() - timedelta(days=7)
                weekly_mastered_query = text("""
                    SELECT COUNT(DISTINCT problem_id) as count
                    FROM word_proficiency_records
                    WHERE student_id = :user_id
                    AND level >= 5
                    AND last_updated >= :week_ago
                """)
                
                result = db.session.execute(
                    weekly_mastered_query,
                    {"user_id": current_user.id, "week_ago": one_week_ago}
                ).first()
                
                context['weekly_words_learned'] = result.count if result and result.count else 0
                
                # 全単語数
                total_words_query = text("""
                    SELECT COUNT(DISTINCT problem_id) as count
                    FROM word_proficiency_records
                    WHERE student_id = :user_id
                """)
                
                result = db.session.execute(
                    total_words_query,
                    {"user_id": current_user.id}
                ).first()
                
                context['total_words_attempted'] = result.count if result and result.count else 0
                
            # word_proficiencyテーブルを使用
            elif 'word_proficiency' in table_names:
                current_app.logger.info("Using word_proficiency table")
                
                # 総マスター単語数（定着度5）
                total_mastered_query = text("""
                    SELECT COUNT(DISTINCT word_id) as count
                    FROM word_proficiency
                    WHERE user_id = :user_id
                    AND proficiency_level = 5
                """)
                
                total_result = db.session.execute(
                    total_mastered_query,
                    {"user_id": current_user.id}
                ).scalar()
                
                context['total_mastered_words'] = total_result or 0
                
                # 今週マスターした単語数
                one_week_ago = datetime.now() - timedelta(days=7)
                weekly_mastered_query = text("""
                    SELECT COUNT(DISTINCT word_id) as count
                    FROM word_proficiency
                    WHERE user_id = :user_id
                    AND proficiency_level = 5
                    AND last_reviewed >= :week_ago
                """)
                
                weekly_result = db.session.execute(
                    weekly_mastered_query,
                    {"user_id": current_user.id, "week_ago": one_week_ago}
                ).scalar()
                
                context['weekly_words_learned'] = weekly_result or 0
                
                # 全体の単語数を取得（定着度に関わらず）
                total_words_query = text("""
                    SELECT COUNT(DISTINCT word_id) as count
                    FROM word_proficiency
                    WHERE user_id = :user_id
                """)
                
                total_words_result = db.session.execute(
                    total_words_query,
                    {"user_id": current_user.id}
                ).scalar()
                
                context['total_words_attempted'] = total_words_result or 0
                
            # wordsテーブルから基礎単語の総数を取得（目標値として使用）
            elif 'words' in table_names:
                current_app.logger.info("Using words table for basic stats")
                
                # ユーザーの学習記録がない場合、基礎単語の総数を表示
                total_words_query = text("""
                    SELECT COUNT(*) as count
                    FROM words
                    WHERE is_active = 1
                """)
                
                result = db.session.execute(total_words_query).first()
                total_basic_words = result.count if result and result.count else 1000  # デフォルト1000語
                
                # 学習進捗をシミュレート（デモ用）
                context['total_words_attempted'] = 0
                context['total_mastered_words'] = 0
                context['weekly_words_learned'] = 0
                
                # メッセージとして総単語数を表示
                context['total_basic_words'] = total_basic_words
                
            # 達成率を計算
            if context['total_words_attempted'] > 0:
                context['mastery_rate'] = round(
                    (context['total_mastered_words'] / context['total_words_attempted']) * 100, 1
                )
            else:
                context['mastery_rate'] = 0
                
            # デバッグログ
            current_app.logger.info(
                f"Word stats for user {current_user.id}: "
                f"total_mastered={context['total_mastered_words']}, "
                f"weekly={context['weekly_words_learned']}, "
                f"total_attempted={context['total_words_attempted']}, "
                f"rate={context['mastery_rate']}%"
            )
                
        except Exception as e:
            current_app.logger.error(f"BaseBuilder fetch error: {str(e)}")
            # デフォルト値を設定
            context['total_mastered_words'] = 0
            context['weekly_words_learned'] = 0
            context['total_words_attempted'] = 0
            context['mastery_rate'] = 0
        
    except Exception as e:
        current_app.logger.error(f"Dashboard error: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        flash('一部のデータの読み込みに失敗しました。', 'warning')
    
    return render_template('student_dashboard.html', **context)


# エラーハンドリング用のフォールバックルート
@student_bp.route('/dashboard_minimal')
@login_required
@student_required
def dashboard_minimal():
    """最小限のダッシュボード（エラー時のフォールバック）"""
    return render_template('student/dashboard_minimal.html')

# アンケート関連
@student_bp.route('/surveys')
@login_required
@student_required
def surveys():
    """アンケート一覧"""
    # 各アンケートの完了状態を確認
    interest_survey = InterestSurvey.query.filter_by(student_id=current_user.id).first()
    personality_survey = PersonalitySurvey.query.filter_by(student_id=current_user.id).first()
    
    return render_template('surveys.html',
                         interest_completed=interest_survey is not None,
                         personality_completed=personality_survey is not None,
                         interest_survey=interest_survey,
                         personality_survey=personality_survey)

@student_bp.route('/interest_survey', methods=['GET', 'POST'])
@login_required
@student_required
def interest_survey():
    """興味関心アンケート"""
    existing_survey = InterestSurvey.query.filter_by(student_id=current_user.id).first()
    
    # 既存のアンケートがある場合は編集画面にリダイレクト
    if existing_survey:
        return redirect(url_for('student.interest_survey_edit'))
    
    if request.method == 'POST':
        responses = {
            'interests': request.form.getlist('interests'),
            'favorite_subjects': request.form.get('favorite_subjects'),
            'hobbies': request.form.get('hobbies'),
            'future_dreams': request.form.get('future_dreams'),
            'curious_topics': request.form.get('curious_topics')
        }
        
        new_survey = InterestSurvey(
            student_id=current_user.id,
            responses=json.dumps(responses, ensure_ascii=False)
        )
        
        db.session.add(new_survey)
        db.session.commit()
        
        flash('興味関心アンケートを提出しました。')
        return redirect(url_for('student.surveys'))
    
    return render_template('interest_survey.html')

@student_bp.route('/interest_survey/edit', methods=['GET', 'POST'])
@login_required
@student_required
def interest_survey_edit():
    """興味関心アンケート編集"""
    survey = InterestSurvey.query.filter_by(student_id=current_user.id).first()
    
    if not survey:
        flash('アンケートが見つかりません。新しく作成してください。')
        return redirect(url_for('student.interest_survey'))
    
    if request.method == 'POST':
        responses = {
            'interests': request.form.getlist('interests'),
            'favorite_subjects': request.form.get('favorite_subjects'),
            'hobbies': request.form.get('hobbies'),
            'future_dreams': request.form.get('future_dreams'),
            'curious_topics': request.form.get('curious_topics')
        }
        
        survey.responses = json.dumps(responses, ensure_ascii=False)
        survey.submitted_at = datetime.utcnow()
        db.session.commit()
        
        flash('興味関心アンケートを更新しました。')
        return redirect(url_for('student.surveys'))
    
    # 既存の回答を取得
    responses = json.loads(survey.responses) if survey.responses else {}
    
    return render_template('interest_survey_edit.html', responses=responses)

@student_bp.route('/personality_survey', methods=['GET', 'POST'])
@login_required
@student_required
def personality_survey():
    """性格・特性アンケート"""
    existing_survey = PersonalitySurvey.query.filter_by(student_id=current_user.id).first()
    
    # 既存のアンケートがある場合は編集画面にリダイレクト
    if existing_survey:
        return redirect(url_for('student.personality_survey_edit'))
    
    if request.method == 'POST':
        responses = {
            'personality_type': request.form.get('personality_type'),
            'work_style': request.form.get('work_style'),
            'strengths': request.form.get('strengths'),
            'weaknesses': request.form.get('weaknesses'),
            'learning_style': request.form.get('learning_style')
        }
        
        new_survey = PersonalitySurvey(
            student_id=current_user.id,
            responses=json.dumps(responses, ensure_ascii=False)
        )
        
        db.session.add(new_survey)
        db.session.commit()
        
        flash('性格・特性アンケートを提出しました。')
        return redirect(url_for('student.surveys'))
    
    return render_template('personality_survey.html')

@student_bp.route('/personality_survey/edit', methods=['GET', 'POST'])
@login_required
@student_required
def personality_survey_edit():
    """性格・特性アンケート編集"""
    survey = PersonalitySurvey.query.filter_by(student_id=current_user.id).first()
    
    if not survey:
        flash('アンケートが見つかりません。新しく作成してください。')
        return redirect(url_for('student.personality_survey'))
    
    if request.method == 'POST':
        responses = {
            'personality_type': request.form.get('personality_type'),
            'work_style': request.form.get('work_style'),
            'strengths': request.form.get('strengths'),
            'weaknesses': request.form.get('weaknesses'),
            'learning_style': request.form.get('learning_style')
        }
        
        survey.responses = json.dumps(responses, ensure_ascii=False)
        survey.submitted_at = datetime.utcnow()
        db.session.commit()
        
        flash('性格・特性アンケートを更新しました。')
        return redirect(url_for('student.surveys'))
    
    # 既存の回答を取得
    responses = json.loads(survey.responses) if survey.responses else {}
    
    return render_template('personality_survey_edit.html', responses=responses)

# 活動記録関連
@student_bp.route('/activities')
@login_required
@student_required
def activities():
    """クラス選択または活動記録一覧"""
    class_id = request.args.get('class_id', type=int)
    
    if not class_id:
        # 生徒が所属するクラス一覧を取得
        enrollments = db.session.query(ClassEnrollment, Class)\
            .join(Class, ClassEnrollment.class_id == Class.id)\
            .filter(ClassEnrollment.student_id == current_user.id)\
            .all()
        
        classes = [{'id': c.id, 'name': c.name, 'description': c.description, 
                   'enrolled_at': e.enrolled_at} for e, c in enrollments]
        
        # クラスに紐付かない活動記録の件数も取得
        unassigned_count = ActivityLog.query.filter_by(
            student_id=current_user.id,
            class_id=None
        ).count()
        
        return render_template('select_class_for_activities.html', 
                             classes=classes,
                             unassigned_count=unassigned_count)
    
    # クラスへの所属確認（class_id=0は「すべての活動」）
    if class_id != 0:
        enrollment = ClassEnrollment.query.filter_by(
            student_id=current_user.id,
            class_id=class_id
        ).first()
        
        if not enrollment:
            flash('このクラスにアクセスする権限がありません。')
            return redirect(url_for('student.activities'))
    
    # 活動記録を取得
    if class_id == 0:
        # すべての活動記録
        activity_logs = ActivityLog.query.filter_by(
            student_id=current_user.id
        ).order_by(ActivityLog.date.desc()).all()
        selected_class = None
        theme = None
    else:
        # 特定クラスの活動記録
        activity_logs = ActivityLog.query.filter_by(
            student_id=current_user.id,
            class_id=class_id
        ).order_by(ActivityLog.date.desc()).all()
        
        selected_class = Class.query.get_or_404(class_id)
        theme = InquiryTheme.query.filter_by(
            student_id=current_user.id,
            class_id=class_id,
            is_selected=True
        ).first()
    
    return render_template('activities.html',
                         activity_logs=activity_logs,
                         theme=theme,
                         selected_class=selected_class,
                         class_id=class_id)

@student_bp.route('/new_activity', methods=['GET', 'POST'])
@login_required
@student_required
@upload_limit()
def new_activity():
    """新規活動記録（クラスID必須）"""
    class_id = request.args.get('class_id', type=int)
    
    if not class_id:
        flash('クラスを選択してください。')
        return redirect(url_for('student.activities'))
    
    # 権限確認
    enrollment = ClassEnrollment.query.filter_by(
        student_id=current_user.id,
        class_id=class_id,
        is_active=True
    ).first()
    
    if not enrollment:
        flash('このクラスにアクセスする権限がありません。')
        return redirect(url_for('student.activities'))
    
    selected_class = Class.query.get_or_404(class_id)
    theme = InquiryTheme.query.filter_by(
        student_id=current_user.id,
        class_id=class_id,
        is_selected=True
    ).first()
    
    if request.method == 'POST':
        try:
            # POSTデータの処理
            title = request.form.get('title')
            date_str = request.form.get('date')
            activity = request.form.get('activity')
            content = request.form.get('content')
            reflection = request.form.get('reflection')
            tags = request.form.get('tags')
            
            # デバッグログ
            current_app.logger.info(f"Creating activity for user {current_user.id} in class {class_id}")
            
            new_log = ActivityLog(
                student_id=current_user.id,
                class_id=class_id,
                title=title,
                date=datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.now().date(),
                activity=activity,
                content=content,
                reflection=reflection,
                tags=tags,
                timestamp=datetime.now()
            )
            
            # 画像アップロード処理（セキュリティ強化版）
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '':
                    # 新しいセキュリティバリデーターを使用
                    is_valid, error_message, safe_filename = file_validator.validate_image(
                        file.stream, file.filename
                    )
                    
                    if not is_valid:
                        flash(f'画像アップロードエラー: {error_message}')
                        return redirect(url_for('student.new_activity', class_id=class_id))
                    
                    # セキュアなファイルパスを作成
                    filepath = file_validator.create_secure_path(safe_filename, current_user.id)
                    
                    # ファイルを保存
                    file.stream.seek(0)
                    file.save(filepath)
                    
                    # URLパスを保存（ユーザーIDディレクトリ付き）
                    new_log.image_url = f"/uploads/{current_user.id}/{safe_filename}"
        
            db.session.add(new_log)
            db.session.commit()
            
            flash('活動記録が作成されました。')
            return redirect(url_for('student.activities', class_id=class_id))
            
        except Exception as e:
            current_app.logger.error(f"Error creating activity: {str(e)}")
            db.session.rollback()
            flash('活動記録の作成中にエラーが発生しました。')
    
    return render_template('new_activity.html',
                         theme=theme,
                         selected_class=selected_class,
                         class_id=class_id,
                         now=datetime.now())

@student_bp.route('/activity/<int:log_id>/edit', methods=['GET', 'POST'])
@login_required
@student_required
def edit_activity(log_id):
    """活動記録編集"""
    log = ActivityLog.query.get_or_404(log_id)
    
    # 権限チェック
    if log.student_id != current_user.id:
        flash('この活動記録を編集する権限がありません。')
        return redirect(url_for('student.activities'))
    
    if request.method == 'POST':
        log.title = request.form.get('title', log.title)
        date_str = request.form.get('date')
        if date_str:
            try:
                log.date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('日付の形式が正しくありません。')
        
        log.content = request.form.get('content', log.content)
        log.reflection = request.form.get('reflection', log.reflection)
        log.tags = request.form.get('tags', log.tags)
        
        # 画像アップロード処理
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                # ファイルサイズチェック
                file.seek(0, 2)
                file_length = file.tell()
                file.seek(0)
                
                if file_length > MAX_FILE_SIZE:
                    flash('ファイルサイズが大きすぎます（最大5MB）')
                    return redirect(url_for('student.edit_activity', log_id=log_id))
                
                # ファイル拡張子チェック
                if not allowed_file(file.filename):
                    flash('許可されていないファイル形式です。PNG、JPG、JPEG、GIFのみアップロード可能です。')
                    return redirect(url_for('student.edit_activity', log_id=log_id))
                
                # ファイル内容の検証
                if not validate_image(file.stream):
                    flash('無効な画像ファイルです。')
                    return redirect(url_for('student.edit_activity', log_id=log_id))
                
                # 既存の画像を削除
                if log.image_url:
                    old_filename = log.image_url.split('/')[-1]
                    old_path = os.path.join(current_app.config.get('SECURE_UPLOAD_FOLDER', current_app.config['UPLOAD_FOLDER']), old_filename)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                # 新しい画像を保存
                original_filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
                
                upload_folder = current_app.config.get('SECURE_UPLOAD_FOLDER', current_app.config['UPLOAD_FOLDER'])
                filepath = os.path.join(upload_folder, unique_filename)
                file.save(filepath)
                
                log.image_url = f"/uploads/{unique_filename}"
        
        log.timestamp = datetime.utcnow()
        db.session.commit()
        
        flash('活動記録を更新しました。')
        return redirect(url_for('student.activities'))
    
    return render_template('edit_activity.html', log=log)

@student_bp.route('/activity/<int:log_id>/delete')
@login_required
@student_required
def delete_activity(log_id):
    """活動記録削除"""
    log = ActivityLog.query.get_or_404(log_id)
    
    # 権限チェック
    if log.student_id != current_user.id:
        flash('この活動記録を削除する権限がありません。')
        return redirect(url_for('student.activities'))
    
    # 画像ファイルも削除
    if log.image_url:
        file_path = os.path.join('static', log.image_url.lstrip('/'))
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logging.error(f"画像ファイル削除エラー: {e}")
    
    db.session.delete(log)
    db.session.commit()
    
    flash('活動記録を削除しました。')
    return redirect(url_for('student.activities'))

@student_bp.route('/activity/<int:activity_id>')
@login_required
def view_activity(activity_id):
    """活動記録詳細表示"""
    activity = ActivityLog.query.get_or_404(activity_id)
    
    # アクセス権限の確認
    if current_user.role == 'student':
        # 自分の活動記録のみ閲覧可能
        if activity.student_id != current_user.id:
            flash('この活動記録を閲覧する権限がありません。')
            return redirect(url_for('student.activities'))
    elif current_user.role == 'teacher':
        # 教師は自分のクラスの学生の活動記録のみ閲覧可能
        student_classes = ClassEnrollment.query.filter_by(student_id=activity.student_id).all()
        teacher_class_ids = [c.id for c in Class.query.filter_by(teacher_id=current_user.id).all()]
        
        # 学生が履修しているクラスと教師が担当するクラスに重複があるか確認
        student_class_ids = [e.class_id for e in student_classes]
        if not any(class_id in teacher_class_ids for class_id in student_class_ids):
            flash('この活動記録を閲覧する権限がありません。')
            return redirect(url_for('teacher.dashboard'))
    
    # 選択中のテーマを取得
    theme = InquiryTheme.query.filter_by(
        student_id=activity.student_id,
        is_selected=True
    ).first()
    
    # TODO: フィードバック機能の実装時にフィードバックデータを取得
    feedback = []
    
    return render_template('view_activity.html', 
                         activity=activity,
                         theme=theme,
                         feedback=feedback)

@student_bp.route('/activities/export/<format>')
@login_required
@student_required
def export_activities(format):
    """活動記録エクスポート"""
    if format not in ['pdf', 'csv']:
        flash('無効なフォーマットです。')
        return redirect(url_for('student.activities'))
    
    # class_idパラメータを取得
    class_id = request.args.get('class_id', type=int)
    
    # 活動記録を取得
    query = ActivityLog.query.filter_by(student_id=current_user.id)
    if class_id:
        query = query.filter_by(class_id=class_id)
    activities = query.order_by(ActivityLog.date.desc()).all()
    
    if format == 'pdf':
        # PDFエクスポート処理
        if not REPORTLAB_AVAILABLE:
            flash('PDF機能は現在利用できません。')
            return redirect(url_for('student.activities'))
        
        # PDFエクスポート用にtheme変数を定義
        theme = {
            'title': '学習活動記録',
            'description': f'{current_user.full_name or current_user.username}さんの活動記録'
        }
        
        # クラス情報を取得（必要に応じて）
        selected_class = None
        if class_id:
            selected_class = Class.query.get(class_id)
            if selected_class:
                theme['title'] = f'{selected_class.name} - 学習活動記録'
        
        return render_template('export_activities_pdf.html', 
                             activities=activities,
                             logs=activities,  # 互換性のため
                             theme=theme,
                             student=current_user,
                             current_user=current_user,
                             selected_class=selected_class,
                             export_date=datetime.now(),
                             now=datetime.now())
    
    elif format == 'csv':
        # StringIOを使用する方法に変更
        si = io.StringIO()
        
        # UTF-8 BOMを書き込む
        si.write('\ufeff')
        
        writer = csv.writer(si)
        
        # ヘッダー
        writer.writerow(['日付', 'タイトル', '活動内容', '振り返り', 'タグ'])
        
        # データ
        for activity in activities:
            writer.writerow([
                activity.date.strftime('%Y-%m-%d') if activity.date else '',
                activity.title or '',
                activity.content or '',
                activity.reflection or '',
                activity.tags or ''
            ])
        
        # BytesIOに変換
        output = io.BytesIO()
        output.write(si.getvalue().encode('utf-8-sig'))
        output.seek(0)
        
        return send_file(
            output,
            mimetype='text/csv; charset=utf-8',
            as_attachment=True,
            download_name='活動記録.csv'
        )

# To Do管理
@student_bp.route('/todos')
@login_required
@student_required
def todos():
    """To Do一覧"""
    todos = Todo.query.filter_by(student_id=current_user.id)\
        .order_by(Todo.is_completed, Todo.due_date, Todo.created_at.desc())\
        .all()
    
    # 選択中のテーマを取得（表示用）
    theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
    
    return render_template('todos.html', todos=todos, theme=theme)

@student_bp.route('/new_todo', methods=['GET', 'POST'])
@login_required
@student_required
def new_todo():
    """新規To Do作成"""
    # 選択中のテーマを取得（表示用）
    theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date', '')
        priority = request.form.get('priority', 'medium')
        
        if not title:
            flash('タイトルは必須項目です。')
            return render_template('new_todo.html', theme=theme)
        
        # 期限日の処理
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('日付の形式が正しくありません。')
                return render_template('new_todo.html', theme=theme)
        
        # 新しいTo Doを作成
        new_todo = Todo(
            student_id=current_user.id,
            title=title,
            description=description,
            due_date=due_date,
            priority=priority
        )
        
        db.session.add(new_todo)
        db.session.commit()
        
        flash('To Doを作成しました。')
        return redirect(url_for('student.todos'))
    
    return render_template('new_todo.html', theme=theme)

@student_bp.route('/todo/<int:todo_id>/edit', methods=['GET', 'POST'])
@login_required
@student_required
def edit_todo(todo_id):
    """To Do編集"""
    todo = Todo.query.get_or_404(todo_id)
    
    # 権限チェック
    if todo.student_id != current_user.id:
        flash('このTo Doを編集する権限がありません。')
        return redirect(url_for('student.todos'))
    
    # 選択中のテーマを取得（表示用）
    theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description', '')
        due_date_str = request.form.get('due_date', '')
        priority = request.form.get('priority', 'medium')
        is_completed = 'is_completed' in request.form
        
        if not title:
            flash('タイトルは必須項目です。')
            return render_template('edit_todo.html', todo=todo, theme=theme)
        
        # To Doを更新
        todo.title = title
        todo.description = description
        todo.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
        todo.priority = priority
        todo.is_completed = is_completed
        
        db.session.commit()
        
        flash('To Doが更新されました。')
        return redirect(url_for('student.todos'))
    
    return render_template('edit_todo.html', todo=todo, theme=theme)

@student_bp.route('/todo/<int:todo_id>/delete')
@login_required
@student_required
def delete_todo(todo_id):
    """To Do削除"""
    todo = Todo.query.get_or_404(todo_id)
    
    # 権限チェック
    if todo.student_id != current_user.id:
        flash('このTo Doを削除する権限がありません。')
        return redirect(url_for('student.todos'))
    
    db.session.delete(todo)
    db.session.commit()
    
    flash('To Doが削除されました。')
    return redirect(url_for('student.todos'))

@student_bp.route('/todo/<int:todo_id>/toggle')
@login_required
@student_required
def toggle_todo(todo_id):
    """To Do完了状態切り替え"""
    todo = Todo.query.get_or_404(todo_id)
    
    # 権限チェック
    if todo.student_id != current_user.id:
        flash('このTo Doを更新する権限がありません。')
        return redirect(url_for('student.todos'))
    
    # 完了状態を切り替え
    todo.is_completed = not todo.is_completed
    todo.last_updated = datetime.utcnow()
    db.session.commit()
    
    status = "完了" if todo.is_completed else "未完了"
    flash(f'To Do "{todo.title}" を{status}にしました。')
    
    return redirect(url_for('student.todos'))

# 目標管理
@student_bp.route('/goals')
@login_required
@student_required
def goals():
    """目標一覧"""
    goals = Goal.query.filter_by(student_id=current_user.id)\
        .order_by(Goal.is_completed, Goal.goal_type, Goal.due_date)\
        .all()
    
    # 選択中のテーマを取得（表示用）
    theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
    
    return render_template('goals.html', goals=goals, theme=theme)

@student_bp.route('/new_goal', methods=['GET', 'POST'])
@login_required
@student_required
def new_goal():
    """新規目標作成"""
    # 選択中のテーマを取得（表示用）
    theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description', '')
        goal_type = request.form.get('goal_type', 'medium')
        due_date_str = request.form.get('due_date', '')
        
        if not title:
            flash('タイトルは必須項目です。')
            return render_template('new_goal.html', theme=theme)
        
        # 期限日の処理
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('日付の形式が正しくありません。')
                return render_template('new_goal.html', theme=theme)
        
        # 新しい目標を作成
        new_goal = Goal(
            student_id=current_user.id,
            title=title,
            description=description,
            goal_type=goal_type,
            due_date=due_date
        )
        
        db.session.add(new_goal)
        db.session.commit()
        
        flash('目標を作成しました。')
        return redirect(url_for('student.goals'))
    
    return render_template('new_goal.html', theme=theme)

@student_bp.route('/goal/<int:goal_id>/edit', methods=['GET', 'POST'])
@login_required
@student_required
def edit_goal(goal_id):
    """目標編集"""
    goal = Goal.query.get_or_404(goal_id)
    
    # 権限チェック
    if goal.student_id != current_user.id:
        flash('この目標を編集する権限がありません。')
        return redirect(url_for('student.goals'))
    
    # 選択中のテーマを取得（表示用）
    theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description', '')
        goal_type = request.form.get('goal_type', 'medium')
        due_date_str = request.form.get('due_date', '')
        progress = request.form.get('progress', type=int, default=0)
        is_completed = 'is_completed' in request.form
        
        if not title:
            flash('タイトルは必須項目です。')
            return render_template('edit_goal.html', goal=goal, theme=theme)
        
        # 目標を更新
        goal.title = title
        goal.description = description
        goal.goal_type = goal_type
        goal.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
        goal.progress = max(0, min(100, progress))  # 0-100の範囲に制限
        goal.is_completed = is_completed
        
        db.session.commit()
        
        flash('目標が更新されました。')
        return redirect(url_for('student.goals'))
    
    return render_template('edit_goal.html', goal=goal, theme=theme)

@student_bp.route('/goal/<int:goal_id>/delete')
@login_required
@student_required
def delete_goal(goal_id):
    """目標削除"""
    goal = Goal.query.get_or_404(goal_id)
    
    # 権限チェック
    if goal.student_id != current_user.id:
        flash('この目標を削除する権限がありません。')
        return redirect(url_for('student.goals'))
    
    db.session.delete(goal)
    db.session.commit()
    
    flash('目標が削除されました。')
    return redirect(url_for('student.goals'))

@student_bp.route('/goal/<int:goal_id>/update_progress', methods=['POST'])
@login_required
@student_required
def update_goal_progress(goal_id):
    """目標進捗更新"""
    goal = Goal.query.get_or_404(goal_id)
    
    # 権限チェック
    if goal.student_id != current_user.id:
        flash('この目標を更新する権限がありません。')
        return redirect(url_for('student.goals'))
    
    progress = request.form.get('progress', type=int, default=0)
    goal.progress = max(0, min(100, progress))  # 0-100の範囲に制限
    
    # 100%になったら完了フラグを立てる
    if goal.progress >= 100:
        goal.is_completed = True
    
    goal.last_updated = datetime.utcnow()
    db.session.commit()
    
    flash(f'目標の進捗を{goal.progress}%に更新しました。')
    return redirect(url_for('student.goals'))

# テーマ関連
@student_bp.route('/themes')
@login_required
def view_themes():
    """個人テーマ一覧（クラス別）"""
    try:
        if current_user.role == 'student':
            class_id = request.args.get('class_id', type=int)
            
            # デバッグ: ユーザーとクラスIDを確認
            current_app.logger.info(f"=== THEMES DEBUG ===")
            current_app.logger.info(f"User ID: {current_user.id}, Username: {current_user.username}")
            current_app.logger.info(f"Class ID: {class_id}")
            
            if not class_id:
                # クラス選択画面
                enrollments = ClassEnrollment.query.filter_by(
                    student_id=current_user.id,
                    is_active=True
                ).all()
                classes = [e.class_obj for e in enrollments]
                return render_template('select_class_for_themes.html', 
                                     classes=classes,
                                     theme_type='personal')
            
            # 権限確認
            enrollment = ClassEnrollment.query.filter_by(
                student_id=current_user.id,
                class_id=class_id,
                is_active=True
            ).first()
            
            if not enrollment:
                flash('このクラスにアクセスする権限がありません。')
                return redirect(url_for('student.view_themes'))
            
            # 個人テーマを取得
            current_app.logger.info(f"Fetching themes for user_id={current_user.id}, class_id={class_id}")
            themes = InquiryTheme.query.filter_by(
                student_id=current_user.id,
                class_id=class_id
            ).order_by(InquiryTheme.created_at.desc()).all()
            
            current_app.logger.info(f"Found {len(themes)} personal themes")
            
            # デバッグ用：各テーマの情報をログ出力
            for theme in themes:
                current_app.logger.info(f"Theme: id={theme.id}, title={theme.title}, is_selected={theme.is_selected}, class_id={theme.class_id}, created_at={theme.created_at}")
            
            selected_theme = InquiryTheme.query.filter_by(
                student_id=current_user.id,
                class_id=class_id,
                is_selected=True
            ).first()
            
            if selected_theme:
                current_app.logger.info(f"Selected theme: {selected_theme.title}")
            else:
                current_app.logger.info("No selected theme found")
            
            # クラスと大テーマを取得
            class_obj = Class.query.get_or_404(class_id)
            current_app.logger.info(f"Class: {class_obj.name}")
            
            main_theme = MainTheme.query.filter_by(class_id=class_id).first()
            if main_theme:
                current_app.logger.info(f"Main theme found: ID={main_theme.id}, Title={main_theme.title}")
            else:
                current_app.logger.info("No main theme found for this class")
            
            # テンプレートが期待する形式でデータを準備
            themes_with_main = []
            for theme in themes:
                themes_with_main.append({
                    'theme': theme,
                    'main_theme': main_theme  # このクラスの大テーマを関連付け
                })
            
            # available_main_themesも準備（このクラスの大テーマのリスト）
            available_main_themes = [main_theme] if main_theme else []
            
            current_app.logger.info(f"Prepared {len(themes_with_main)} themes_with_main items")
            current_app.logger.info(f"Available main themes: {len(available_main_themes)}")
            
            # テンプレートに渡す前に確認
            current_app.logger.info(f"=== END THEMES DEBUG ===")
            
            return render_template('view_themes.html',
                                 themes_with_main=themes_with_main,
                                 available_main_themes=available_main_themes,
                                 selected_theme=selected_theme,
                                 class_obj=class_obj,
                                 main_theme=main_theme,
                                 class_id=class_id)
        else:
            flash('学生のみアクセス可能です。')
            return redirect(url_for('index'))
    except Exception as e:
        current_app.logger.error(f"Error in view_themes: {str(e)}")
        flash('テーマの表示中にエラーが発生しました。')
        return redirect(url_for('student.dashboard'))

@student_bp.route('/select_theme/<int:theme_id>', methods=['POST'])
@login_required
@student_required
def select_theme(theme_id):
    """テーマ選択"""
    theme = InquiryTheme.query.get_or_404(theme_id)
    
    # 権限チェック
    if theme.student_id != current_user.id:
        flash('このテーマを選択する権限がありません。')
        return redirect(url_for('student.view_themes'))
    
    # 生徒の現在のクラスを取得
    enrollment = ClassEnrollment.query.filter_by(
        student_id=current_user.id
    ).order_by(ClassEnrollment.enrolled_at.desc()).first()
    
    if enrollment:
        # 既存の選択を解除（同じクラス内）
        InquiryTheme.query.filter_by(
            student_id=current_user.id,
            class_id=enrollment.class_id,
            is_selected=True
        ).update({'is_selected': False})
        
        # class_idを設定
        theme.class_id = enrollment.class_id
    else:
        # 既存の選択を解除（後方互換性）
        InquiryTheme.query.filter_by(
            student_id=current_user.id,
            is_selected=True
        ).update({'is_selected': False})
    
    # 新しいテーマを選択
    theme.is_selected = True
    db.session.commit()
    
    flash(f'テーマ「{theme.title}」を選択しました。')
    return redirect(url_for('student.view_themes'))

@student_bp.route('/delete_theme/<int:theme_id>', methods=['POST'])
@login_required
@student_required
def delete_theme(theme_id):
    """個人テーマの削除"""
    theme = InquiryTheme.query.get_or_404(theme_id)
    
    # 権限確認
    if theme.student_id != current_user.id:
        flash('このテーマを削除する権限がありません。')
        return redirect(url_for('student.view_themes'))
    
    # 選択中のテーマは削除不可
    if theme.is_selected:
        flash('選択中のテーマは削除できません。')
        return redirect(url_for('student.view_themes', class_id=theme.class_id))
    
    class_id = theme.class_id
    theme_title = theme.title
    
    try:
        db.session.delete(theme)
        db.session.commit()
        flash(f'テーマ「{theme_title}」を削除しました。')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting theme: {str(e)}")
        flash('テーマの削除中にエラーが発生しました。')
    
    return redirect(url_for('student.view_themes', class_id=class_id))

@student_bp.route('/regenerate_themes', methods=['POST'])
@login_required
@student_required
def regenerate_themes():
    """テーマ再生成"""
    # アンケートが完了しているか確認
    if not current_user.has_completed_surveys():
        flash('テーマを生成するには、すべてのアンケートを完了する必要があります。')
        return redirect(url_for('student.surveys'))
    
    # 既存のAI生成テーマを削除
    InquiryTheme.query.filter_by(student_id=current_user.id, is_ai_generated=True).delete()
    
    # 新しいテーマを生成（実装は別途）
    flash('新しいテーマを生成しています...')
    # TODO: AI生成処理を実装
    
    db.session.commit()
    return redirect(url_for('student.view_themes'))

@student_bp.route('/main_themes')
@login_required
@student_required
def student_view_main_themes():
    """大テーマ一覧（クラス別）"""
    try:
        class_id = request.args.get('class_id', type=int)
        current_app.logger.info(f"student_view_main_themes: user={current_user.id}, class_id={class_id}")
        
        if not class_id:
            # クラス選択画面
            current_app.logger.info(f"No class_id provided, showing class selection")
            enrollments = ClassEnrollment.query.filter_by(
                student_id=current_user.id,
                is_active=True
            ).all()
            classes = [e.class_obj for e in enrollments]
            current_app.logger.info(f"Found {len(classes)} enrolled classes")
            return render_template('select_class_for_themes.html', 
                                 classes=classes,
                                 theme_type='main')
        
        # 選択されたクラスの大テーマを表示
        enrollment = ClassEnrollment.query.filter_by(
            student_id=current_user.id,
            class_id=class_id,
            is_active=True
        ).first()
        
        if not enrollment:
            flash('このクラスにアクセスする権限がありません。')
            return redirect(url_for('student.student_view_main_themes'))
        
        main_theme = MainTheme.query.filter_by(class_id=class_id).first()
        class_obj = Class.query.get_or_404(class_id)
        
        current_app.logger.info(f"Main theme found: {main_theme.title if main_theme else 'None'}")
        current_app.logger.info(f"Class: {class_obj.name}")
        
        return render_template('student_main_themes.html',
                             main_theme=main_theme,
                             class_obj=class_obj,
                             class_id=class_id)
    except Exception as e:
        current_app.logger.error(f"Error in student_view_main_themes: {str(e)}")
        flash('大テーマの表示中にエラーが発生しました。')
        return redirect(url_for('student.dashboard'))

@student_bp.route('/main_theme/<int:theme_id>/create_personal', methods=['GET', 'POST'])
@login_required
@student_required
def create_personal_theme(theme_id):
    """個人探究テーマ作成"""
    main_theme = MainTheme.query.get_or_404(theme_id)
    
    # 履修確認
    enrollment = ClassEnrollment.query.filter_by(
        class_id=main_theme.class_id,
        student_id=current_user.id
    ).first()
    
    if not enrollment:
        flash('このクラスを履修していません。')
        return redirect(url_for('student.student_view_main_themes'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        question = request.form.get('question')
        description = request.form.get('description')
        rationale = request.form.get('rationale')
        approach = request.form.get('approach')
        potential = request.form.get('potential')
        
        if not title or not question:
            flash('タイトルと問いは必須項目です。')
            return render_template('create_personal_theme.html', main_theme=main_theme)
        
        # 新しい個人テーマを作成（メインテーマからclass_idを継承）
        new_theme = InquiryTheme(
            student_id=current_user.id,
            class_id=main_theme.class_id,  # メインテーマのclass_idを設定
            main_theme_id=main_theme.id,
            is_ai_generated=False,
            title=title,
            question=question,
            description=description,
            rationale=rationale,
            approach=approach,
            potential=potential
        )
        
        db.session.add(new_theme)
        db.session.commit()
        
        flash('個人探究テーマを作成しました。')
        return redirect(url_for('student.view_themes'))
    
    return render_template('create_personal_theme.html', main_theme=main_theme)

@student_bp.route('/main_theme/<int:theme_id>/generate_theme', methods=['GET', 'POST'])
@login_required
@student_required
def generate_theme(theme_id):
    """AIによるテーマ生成"""
    main_theme = MainTheme.query.get_or_404(theme_id)
    
    # 履修確認
    enrollment = ClassEnrollment.query.filter_by(
        class_id=main_theme.class_id,
        student_id=current_user.id
    ).first()
    
    if not enrollment:
        flash('このクラスを履修していません。')
        return redirect(url_for('student.student_view_main_themes'))
    
    # アンケート完了確認
    if not current_user.has_completed_surveys():
        flash('テーマを生成するには、すべてのアンケートを完了する必要があります。')
        return redirect(url_for('student.surveys'))
    
    if request.method == 'POST':
        # アンケート回答を取得
        interest_survey = InterestSurvey.query.filter_by(student_id=current_user.id).first()
        personality_survey = PersonalitySurvey.query.filter_by(student_id=current_user.id).first()
        
        interest_responses = json.loads(interest_survey.responses) if interest_survey else {}
        personality_responses = json.loads(personality_survey.responses) if personality_survey else {}
        
        # AIでテーマを生成
        try:
            generated_themes = generate_personal_themes_with_ai(
                main_theme, 
                interest_responses, 
                personality_responses
            )
            
            # 生成されたテーマを保存
            for theme_data in generated_themes:
                new_theme = InquiryTheme(
                    student_id=current_user.id,
                    class_id=main_theme.class_id,  # メインテーマのclass_idを設定
                    main_theme_id=main_theme.id,
                    is_ai_generated=True,
                    title=theme_data['title'],
                    question=theme_data['question'],
                    description=theme_data['description'],
                    rationale=theme_data['rationale'],
                    approach=theme_data['approach'],
                    potential=theme_data['potential']
                )
                db.session.add(new_theme)
            
            db.session.commit()
            flash(f'{len(generated_themes)}個のテーマを生成しました。')
            return redirect(url_for('student.view_themes'))
            
        except Exception as e:
            logging.error(f"テーマ生成エラー: {e}")
            flash('テーマの生成に失敗しました。もう一度お試しください。')
    
    return render_template('generate_theme.html', main_theme=main_theme)

@student_bp.route('/create_personal_theme_new', methods=['POST'])
@login_required
@student_required
def create_personal_theme_new():
    """シンプルな個人テーマ作成"""
    class_id = request.form.get('class_id', type=int)
    main_theme_id = request.form.get('main_theme_id', type=int)
    theme_title = request.form.get('theme_title', '').strip()
    theme_description = request.form.get('theme_description', '').strip()
    question = request.form.get('question', '').strip()
    rationale = request.form.get('rationale', '').strip()
    approach = request.form.get('approach', '').strip()
    
    current_app.logger.info(f"Creating new theme - Title: {theme_title}, Class: {class_id}")
    
    if not class_id or not theme_title:
        flash('必要な情報が入力されていません。')
        return redirect(url_for('student.view_themes', class_id=class_id))
    
    # 権限確認
    enrollment = ClassEnrollment.query.filter_by(
        student_id=current_user.id,
        class_id=class_id,
        is_active=True
    ).first()
    
    if not enrollment:
        flash('このクラスにアクセスする権限がありません。')
        return redirect(url_for('student.view_themes'))
    
    try:
        # 既存のテーマの選択を解除
        InquiryTheme.query.filter_by(
            student_id=current_user.id,
            class_id=class_id,
            is_selected=True
        ).update({'is_selected': False})
        
        # 新しいテーマを作成
        new_theme = InquiryTheme(
            student_id=current_user.id,
            class_id=class_id,
            main_theme_id=main_theme_id,
            title=theme_title,
            description=theme_description,
            question=question if question else theme_title,  # 質問フィールドが空の場合はタイトルを使用
            rationale=rationale,
            approach=approach,
            is_selected=True,
            is_ai_generated=False
        )
        db.session.add(new_theme)
        db.session.commit()
        
        flash('新しいテーマを作成しました。')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating theme: {str(e)}")
        flash('テーマの作成中にエラーが発生しました。')
    
    return redirect(url_for('student.view_themes', class_id=class_id))

@student_bp.route('/generate_theme_ai', methods=['POST'])
@login_required
@student_required
def generate_theme_ai():
    """AIを使用したテーマ生成（シンプル版）"""
    class_id = request.form.get('class_id', type=int)
    main_theme_id = request.form.get('main_theme_id', type=int)
    interests = request.form.get('interests', '').strip()
    
    if not class_id:
        flash('クラス情報が不足しています。')
        return redirect(url_for('student.view_themes'))
    
    # 権限確認
    enrollment = ClassEnrollment.query.filter_by(
        student_id=current_user.id,
        class_id=class_id,
        is_active=True
    ).first()
    
    if not enrollment:
        flash('このクラスにアクセスする権限がありません。')
        return redirect(url_for('student.view_themes'))
    
    # アンケート完了確認
    if not current_user.has_completed_surveys():
        flash('AIテーマ生成にはすべてのアンケートを完了する必要があります。')
        return redirect(url_for('student.surveys'))
    
    try:
        # 大テーマを取得
        main_theme = MainTheme.query.get(main_theme_id) if main_theme_id else None
        
        # アンケート回答を取得（正しい引数名で）
        surveys = {
            'personality_survey': PersonalitySurvey.query.filter_by(student_id=current_user.id).first(),
            'interest_survey_responses': InterestSurvey.query.filter_by(student_id=current_user.id).first(),
            'learning_survey': None,  # 学習アンケートがある場合は実装
            'goal_survey': None  # 目標アンケートがある場合は実装
        }
        
        # オブジェクトを辞書に変換
        interest_data = {}
        interest_survey = surveys.get('interest_survey_responses')
        if interest_survey and hasattr(interest_survey, '__dict__'):
            # SQLAlchemyモデルの属性を辞書に変換
            for column in interest_survey.__table__.columns:
                if column.name not in ['id', 'student_id', 'created_at', 'last_updated']:
                    interest_data[column.name] = getattr(interest_survey, column.name)

        personality_data = {}
        personality_survey = surveys.get('personality_survey')
        if personality_survey and hasattr(personality_survey, '__dict__'):
            for column in personality_survey.__table__.columns:
                if column.name not in ['id', 'student_id', 'created_at', 'last_updated']:
                    personality_data[column.name] = getattr(personality_survey, column.name)

        # 既存のgenerate_personal_themes_with_ai関数を使用
        if main_theme:
            current_app.logger.info(f"Generating AI themes for main_theme: {main_theme.title}")
            themes = generate_personal_themes_with_ai(
                main_theme=main_theme,
                interest_responses=interest_data,
                personality_responses=personality_data
            )
            
            # 既存のテーマの選択を解除
            InquiryTheme.query.filter_by(
                student_id=current_user.id,
                class_id=class_id,
                is_selected=True
            ).update({'is_selected': False})
            
            # 生成されたテーマを保存
            for i, theme_data in enumerate(themes):
                theme = InquiryTheme(
                    student_id=current_user.id,
                    class_id=class_id,
                    main_theme_id=main_theme.id,
                    is_ai_generated=True,
                    is_selected=(i == 0),  # 最初のテーマを選択
                    title=theme_data['title'],
                    question=theme_data['question'],
                    description=theme_data.get('description', ''),
                    rationale=theme_data.get('rationale', ''),
                    approach=theme_data.get('approach', ''),
                    potential=theme_data.get('potential', '')
                )
                db.session.add(theme)
            
            db.session.commit()
            flash('AIがテーマを生成しました。生成されたテーマから選択してください。')
        else:
            flash('大テーマが見つかりません。')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error generating theme with AI: {str(e)}")
        flash('AIテーマ生成中にエラーが発生しました。')
    
    return redirect(url_for('student.view_themes', class_id=class_id))

@student_bp.route('/theme/<int:theme_id>/edit', methods=['GET', 'POST'])
@login_required
@student_required
def edit_theme(theme_id):
    """テーマ編集・作成"""
    
    if theme_id == 0:
        # New theme creation
        class_id = request.args.get('class_id', type=int)
        if not class_id:
            flash('クラスIDが指定されていません。')
            return redirect(url_for('student.view_themes'))
        
        # Check enrollment
        enrollment = ClassEnrollment.query.filter_by(
            student_id=current_user.id,
            class_id=class_id,
            is_active=True
        ).first()
        
        if not enrollment:
            flash('このクラスにアクセスする権限がありません。')
            return redirect(url_for('student.view_themes'))
        
        # Create empty theme
        theme = InquiryTheme()
        theme.id = 0
        theme.class_id = class_id
        theme.title = ''
        theme.question = ''
        theme.description = ''
        
        if request.method == 'GET':
            return render_template('edit_theme_simple.html', theme=theme, class_id=class_id)
        
        if request.method == 'POST':
            # Create new theme
            theme = InquiryTheme(
                student_id=current_user.id,
                class_id=request.form.get('class_id', type=int),
                title=request.form.get('title', ''),
                question=request.form.get('question', ''),
                description=request.form.get('description', ''),
                is_selected=True
            )
            db.session.add(theme)
            db.session.commit()
            flash('新しいテーマを作成しました。')
            return redirect(url_for('student.view_themes', class_id=theme.class_id))
    
    else:
        # Existing theme editing
        theme = InquiryTheme.query.get_or_404(theme_id)
        
        # 権限チェック
        if theme.student_id != current_user.id:
            flash('このテーマを編集する権限がありません。')
            return redirect(url_for('student.view_themes'))
        
        if request.method == 'POST':
            theme.title = request.form.get('title', theme.title)
            theme.question = request.form.get('question', theme.question)
            theme.description = request.form.get('description', theme.description)
            theme.rationale = request.form.get('rationale', theme.rationale)
            theme.approach = request.form.get('approach', theme.approach)
            theme.potential = request.form.get('potential', theme.potential)
            
            db.session.commit()
            flash('テーマを更新しました。')
            return redirect(url_for('student.view_themes'))
        
        return render_template('edit_theme_simple.html', theme=theme, class_id=getattr(theme, 'class_id', None))

# マイルストーン関連
@student_bp.route('/milestone/<int:milestone_id>')
@login_required
def view_milestone(milestone_id):
    """マイルストーン詳細"""
    milestone = Milestone.query.get_or_404(milestone_id)
    
    # アクセス権限の確認
    if current_user.role == 'student':
        enrollment = ClassEnrollment.query.filter_by(
            class_id=milestone.class_id,
            student_id=current_user.id
        ).first()
        if not enrollment:
            flash('このマイルストーンへのアクセス権限がありません。')
            return redirect(url_for('student.dashboard'))
    elif current_user.role == 'teacher':
        if milestone.class_obj.teacher_id != current_user.id:
            flash('このマイルストーンへのアクセス権限がありません。')
            return redirect(url_for('teacher.dashboard'))
    
    return render_template('view_milestone.html', milestone=milestone)

@student_bp.route('/milestone/<int:milestone_id>/submit', methods=['GET', 'POST'])
@login_required
@student_required
def submit_milestone(milestone_id):
    """マイルストーン提出"""
    milestone = Milestone.query.get_or_404(milestone_id)
    
    # 履修確認
    enrollment = ClassEnrollment.query.filter_by(
        class_id=milestone.class_id,
        student_id=current_user.id
    ).first()
    
    if not enrollment:
        flash('このマイルストーンに提出する権限がありません。')
        return redirect(url_for('student.dashboard'))
    
    if request.method == 'POST':
        # TODO: マイルストーン提出処理を実装
        flash('マイルストーンの提出機能は現在開発中です。')
        return redirect(url_for('student.view_milestone', milestone_id=milestone_id))
    
    return render_template('submit_milestone.html', milestone=milestone)

# グループ関連
@student_bp.route('/group/<int:group_id>')
@login_required
def view_group(group_id):
    """グループ詳細"""
    group = Group.query.get_or_404(group_id)
    
    # アクセス権限の確認
    if current_user.role == 'student':
        # 同じクラスの学生か確認
        enrollment = ClassEnrollment.query.filter_by(
            class_id=group.class_id,
            student_id=current_user.id
        ).first()
        if not enrollment:
            flash('このグループへのアクセス権限がありません。')
            return redirect(url_for('student.dashboard'))
    elif current_user.role == 'teacher':
        if group.class_obj.teacher_id != current_user.id:
            flash('このグループへのアクセス権限がありません。')
            return redirect(url_for('teacher.dashboard'))
    
    # メンバー一覧を取得
    members = []
    memberships = GroupMembership.query.filter_by(group_id=group_id).all()
    for membership in memberships:
        members.append(membership.student)
    
    # 現在のユーザーがメンバーか確認
    is_member = any(m.id == current_user.id for m in members)
    
    return render_template('view_group.html', 
                         group=group, 
                         members=members,
                         is_member=is_member)

@student_bp.route('/group/<int:group_id>/join')
@login_required
@student_required
def join_group(group_id):
    """グループ参加"""
    group = Group.query.get_or_404(group_id)
    
    # 同じクラスの学生か確認
    enrollment = ClassEnrollment.query.filter_by(
        class_id=group.class_id,
        student_id=current_user.id
    ).first()
    
    if not enrollment:
        flash('このグループに参加する権限がありません。')
        return redirect(url_for('student.dashboard'))
    
    # 既にメンバーか確認
    existing = GroupMembership.query.filter_by(
        group_id=group_id,
        student_id=current_user.id
    ).first()
    
    if existing:
        flash('既にこのグループのメンバーです。')
    else:
        # グループに参加
        membership = GroupMembership(
            group_id=group_id,
            student_id=current_user.id
        )
        db.session.add(membership)
        db.session.commit()
        flash(f'グループ「{group.name}」に参加しました。')
    
    return redirect(url_for('student.view_group', group_id=group_id))

@student_bp.route('/group/<int:group_id>/leave')
@login_required
@student_required
def leave_group(group_id):
    """グループ退出"""
    group = Group.query.get_or_404(group_id)
    
    # メンバーシップを確認
    membership = GroupMembership.query.filter_by(
        group_id=group_id,
        student_id=current_user.id
    ).first()
    
    if not membership:
        flash('このグループのメンバーではありません。')
    else:
        db.session.delete(membership)
        db.session.commit()
        flash(f'グループ「{group.name}」から退出しました。')
    
    return redirect(url_for('teacher.view_groups', class_id=group.class_id))

@student_bp.route('/group/<int:group_id>/edit', methods=['GET', 'POST'])
@login_required
@student_required
def edit_group(group_id):
    """グループ編集（作成者のみ）"""
    group = Group.query.get_or_404(group_id)
    
    # 権限チェック（グループ作成者のみ編集可能）
    if group.created_by != current_user.id:
        flash('このグループを編集する権限がありません。')
        return redirect(url_for('student.view_group', group_id=group_id))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        if not name:
            flash('グループ名は必須です。')
            return render_template('edit_group.html', group=group)
        
        # グループを更新
        group.name = name
        group.description = description
        
        db.session.commit()
        
        flash('グループが更新されました。')
        return redirect(url_for('student.view_group', group_id=group_id))
    
    return render_template('edit_group.html', group=group)

@student_bp.route('/group/<int:group_id>/delete')
@login_required
@student_required
def delete_group(group_id):
    """グループ削除（作成者のみ）"""
    group = Group.query.get_or_404(group_id)
    
    # 権限チェック（グループ作成者のみ削除可能）
    if group.created_by != current_user.id:
        flash('このグループを削除する権限がありません。')
        return redirect(url_for('student.view_group', group_id=group_id))
    
    # クラスIDを保存（削除後にリダイレクトするため）
    class_id = group.class_id
    
    # グループメンバーシップを削除
    GroupMembership.query.filter_by(group_id=group_id).delete()
    
    # グループを削除
    db.session.delete(group)
    db.session.commit()
    
    flash('グループが削除されました。')
    
    # クラスの詳細ページにリダイレクト
    class_obj = Class.query.get(class_id)
    if class_obj:
        # 学生が所属するクラスの一覧を取得
        enrollments = ClassEnrollment.query.filter_by(
            student_id=current_user.id,
            is_active=True
        ).all()
        enrolled_class_ids = [e.class_id for e in enrollments]
        
        if class_id in enrolled_class_ids:
            return redirect(url_for('student.class_details', class_id=class_id))
    
    return redirect(url_for('student.classes'))

@student_bp.route('/group/<int:group_id>/remove_member/<int:student_id>')
@login_required
@student_required
def remove_group_member(group_id, student_id):
    """グループメンバー削除（作成者のみ）"""
    group = Group.query.get_or_404(group_id)
    
    # 権限チェック（グループ作成者のみ削除可能）
    if group.created_by != current_user.id:
        flash('このグループから学生を削除する権限がありません。')
        return redirect(url_for('student.view_group', group_id=group_id))
    
    # グループ作成者は削除できない
    if student_id == group.created_by:
        flash('グループ作成者をグループから削除することはできません。')
        return redirect(url_for('student.view_group', group_id=group_id))
    
    # メンバーシップを取得
    membership = GroupMembership.query.filter_by(
        group_id=group_id, student_id=student_id).first_or_404()
    
    # グループからメンバーを削除
    db.session.delete(membership)
    db.session.commit()
    
    # 削除されたユーザーの名前を取得
    removed_user = User.query.get(student_id)
    flash(f'{removed_user.username}をグループから削除しました。')
    
    return redirect(url_for('student.view_group', group_id=group_id))

# チャット機能
@student_bp.route('/chat')
@login_required
def chat_page():
    """チャットページ（クラス別）"""
    current_app.logger.info(f"CHAT ACCESS - User: {current_user.username}, Role: '{current_user.role}', Type: {type(current_user.role)}")

    # Force string comparison with more robust handling
    user_role = str(current_user.role).strip().lower()
    current_app.logger.info(f"CHAT DEBUG - Normalized role: '{user_role}', Original role: '{current_user.role}'")
    
    # 学生の場合（studentを先にチェック）
    if user_role == 'student':
        current_app.logger.info(f"Student chat access - User: {current_user.username}")
        class_id = request.args.get('class_id', type=int)
        
        if not class_id:
            # クラス選択画面
            enrollments = ClassEnrollment.query.filter_by(
                student_id=current_user.id,
                is_active=True
            ).all()
            classes = [e.class_obj for e in enrollments]
            current_app.logger.info(f"Showing class selection - {len(classes)} classes found")
            return render_template('select_class_for_chat.html', classes=classes)
        
        # クラスが指定されている場合は所属確認
        enrollment = ClassEnrollment.query.filter_by(
            student_id=current_user.id,
            class_id=class_id
        ).first()
        
        if not enrollment:
            flash('このクラスのチャットにアクセスする権限がありません。')
            return redirect(url_for('student.chat_page'))
        
        # チャット履歴を取得
        current_app.logger.info(f"Chat history query: user_id={current_user.id}, class_id={class_id}")
        chat_history = ChatHistory.query.filter_by(
            user_id=current_user.id,
            class_id=class_id
        ).order_by(ChatHistory.timestamp.asc()).all()
        
        current_app.logger.info(f"Found {len(chat_history)} chat messages for user {current_user.id} in class {class_id}")
        
        # 学習ステップの定義
        learning_steps = [
        {
            'id': 'theme_explore',
            'name': 'テーマを探す',
            'description': '興味のあるテーマを見つけましょう',
            'functions': [
                {'id': 'brainstorm', 'name': 'アイデア出し'},
                {'id': 'research', 'name': 'リサーチ方法'},
                {'id': 'question', 'name': '問いの立て方'}
            ]
        },
        {
            'id': 'planning',
            'name': '計画を立てる',
            'description': '探究活動の計画を作成しましょう',
            'functions': [
                {'id': 'schedule', 'name': 'スケジュール作成'},
                {'id': 'resources', 'name': 'リソース探し'},
                {'id': 'methods', 'name': '方法の検討'}
            ]
        },
        {
            'id': 'research',
            'name': '調査・研究',
            'description': '実際に調査や研究を進めましょう',
            'functions': [
                {'id': 'data_collect', 'name': 'データ収集'},
                {'id': 'analysis', 'name': '分析方法'},
                {'id': 'interpret', 'name': '解釈のヒント'}
            ]
        },
        {
            'id': 'presentation',
            'name': '発表準備',
            'description': '成果を効果的に伝える準備をしましょう',
            'functions': [
                {'id': 'structure', 'name': '構成作り'},
                {'id': 'visual', 'name': 'ビジュアル作成'},
                {'id': 'practice', 'name': '発表練習'}
            ]
        },
        {
            'id': 'free',
            'name': '自由質問',
            'description': '何でも自由に質問してください',
            'functions': []
        }
    ]
        
        # 選択中のテーマを取得
        theme = InquiryTheme.query.filter_by(
            student_id=current_user.id,
            class_id=class_id,
            is_selected=True
        ).first()
        
        selected_class = Class.query.get(class_id)
    
        return render_template('chat.html',
                             chat_history=chat_history,
                             learning_steps=learning_steps,
                             theme=theme,
                             class_id=class_id,
                             selected_class=selected_class)
    
    # 教師の場合
    elif user_role == 'teacher':
        current_app.logger.info(f"Teacher chat access - User: {current_user.username}")
        
        # 教師のチャット履歴を取得（クラス指定なし）
        chat_history = ChatHistory.query.filter_by(
            user_id=current_user.id
        ).order_by(ChatHistory.timestamp.asc()).all()
        
        return render_template('chat.html',
                             chat_history=chat_history,
                             learning_steps=[],
                             theme=None,
                             class_id=None,
                             selected_class=None)
    
    # その他のロール（エラー処理）
    else:
        current_app.logger.error(f"Unknown role: {current_user.role} for user {current_user.username}")
        flash('アクセス権限がありません。')
        return redirect(url_for('index'))

# デバッグ用ルート
@student_bp.route('/debug_role')
@login_required
def debug_role():
    """ユーザー役割のデバッグ情報を返す"""
    from flask import jsonify
    return jsonify({
        'username': current_user.username,
        'role': current_user.role,
        'role_type': str(type(current_user.role)),
        'id': current_user.id
    })

@student_bp.route('/debug/routes')
@login_required
@student_required
def debug_routes():
    """利用可能なルートを表示（開発時のみ）"""
    if not current_app.debug:
        return redirect(url_for('student.dashboard'))
    
    routes = []
    for rule in current_app.url_map.iter_rules():
        if 'student' in rule.endpoint:
            routes.append({
                'endpoint': rule.endpoint,
                'methods': ', '.join(rule.methods),
                'path': str(rule)
            })
    
    return render_template('student/debug_routes.html', routes=routes)
