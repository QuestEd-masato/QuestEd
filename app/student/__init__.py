# app/student/__init__.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, session, Response, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import json
import io
import csv
import logging

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

student_bp = Blueprint('student', __name__)

def student_required(f):
    """学生権限を要求するデコレータ"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            flash('この機能は学生のみ利用可能です。')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@student_bp.route('/student_dashboard')
@login_required
@student_required
def dashboard():
    """学生ダッシュボード"""
    # 学生が履修しているクラスを取得
    enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
    classes = [enrollment.class_obj for enrollment in enrollments]
    
    # アンケート完了状態をチェック
    has_completed_surveys = current_user.has_completed_surveys()
    
    # 選択中のテーマを取得
    selected_theme = InquiryTheme.query.filter_by(
        student_id=current_user.id,
        is_selected=True
    ).first()
    
    # 最新のマイルストーンを取得
    upcoming_milestones = []
    for class_obj in classes:
        milestones = Milestone.query.filter_by(class_id=class_obj.id)\
            .filter(Milestone.due_date >= datetime.utcnow().date())\
            .order_by(Milestone.due_date).limit(3).all()
        for milestone in milestones:
            upcoming_milestones.append({
                'milestone': milestone,
                'class': class_obj
            })
    
    # 期限日でソート
    upcoming_milestones.sort(key=lambda x: x['milestone'].due_date)
    
    # 未完了のTo Doを取得
    pending_todos = Todo.query.filter_by(
        student_id=current_user.id,
        is_completed=False
    ).order_by(Todo.due_date).limit(5).all()
    
    # 進行中の目標を取得
    active_goals = Goal.query.filter_by(
        student_id=current_user.id,
        is_completed=False
    ).order_by(Goal.due_date).limit(3).all()
    
    return render_template('student_dashboard.html',
                         classes=classes,
                         has_completed_surveys=has_completed_surveys,
                         selected_theme=selected_theme,
                         upcoming_milestones=upcoming_milestones,
                         pending_todos=pending_todos,
                         active_goals=active_goals)

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
    
    if existing_survey:
        flash('既に興味関心アンケートを提出しています。編集する場合は編集ボタンを使用してください。')
        return redirect(url_for('student.surveys'))
    
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
        flash('編集するアンケートが見つかりません。')
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
    
    if existing_survey:
        flash('既に性格・特性アンケートを提出しています。編集する場合は編集ボタンを使用してください。')
        return redirect(url_for('student.surveys'))
    
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
        flash('編集するアンケートが見つかりません。')
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
    """活動記録一覧"""
    activity_logs = ActivityLog.query.filter_by(student_id=current_user.id)\
        .order_by(ActivityLog.date.desc())\
        .all()
    
    return render_template('activities.html', activity_logs=activity_logs)

@student_bp.route('/new_activity', methods=['GET', 'POST'])
@login_required
@student_required
def new_activity():
    """新規活動記録"""
    # 選択中のテーマを取得（表示用）
    theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
    
    if request.method == 'POST':
        title = request.form.get('title')
        date_str = request.form.get('date')
        content = request.form.get('content', '')
        reflection = request.form.get('reflection', '')
        tags = request.form.get('tags', '')
        
        # 日付の変換
        try:
            activity_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('日付の形式が正しくありません。')
            return render_template('new_activity.html', theme=theme)
        
        # 新しい活動記録を作成
        new_log = ActivityLog(
            student_id=current_user.id,
            title=title,
            date=activity_date,
            content=content,
            reflection=reflection,
            tags=tags
        )
        
        # 画像アップロード処理
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                # ファイル名を安全にする
                filename = secure_filename(file.filename)
                # タイムスタンプを追加してユニークにする
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{timestamp}_{filename}"
                
                # 保存パスを作成
                from flask import current_app
                upload_folder = current_app.config['UPLOAD_FOLDER']
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                
                # URLパスを保存
                new_log.image_url = f"/static/uploads/{filename}"
        
        db.session.add(new_log)
        db.session.commit()
        
        flash('活動記録を追加しました。')
        return redirect(url_for('student.activities'))
    
    return render_template('new_activity.html', theme=theme)

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
                # 既存の画像を削除
                if log.image_url:
                    old_path = os.path.join('static', log.image_url.lstrip('/'))
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                # 新しい画像を保存
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{timestamp}_{filename}"
                
                upload_folder = current_app.config['UPLOAD_FOLDER']
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                
                log.image_url = f"/static/uploads/{filename}"
        
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
    
    # 活動記録を取得
    logs = ActivityLog.query.filter_by(student_id=current_user.id)\
        .order_by(ActivityLog.date.desc())\
        .all()
    
    if format == 'pdf':
        # PDFエクスポート処理
        if not REPORTLAB_AVAILABLE:
            flash('PDF機能は現在利用できません。')
            return redirect(url_for('student.activities'))
        
        return render_template('export_activities_pdf.html', 
                             logs=logs, 
                             student=current_user,
                             export_date=datetime.now())
    
    elif format == 'csv':
        # CSVエクスポート処理
        output = io.StringIO()
        writer = csv.writer(output)
        
        # ヘッダー
        writer.writerow(['日付', 'タイトル', '内容', 'ふりかえり', 'タグ'])
        
        # データ
        for log in logs:
            writer.writerow([
                log.date.strftime('%Y-%m-%d'),
                log.title,
                log.content,
                log.reflection,
                log.tags
            ])
        
        # レスポンス作成
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=activities_{datetime.now().strftime("%Y%m%d")}.csv',
                'Content-Type': 'text/csv; charset=utf-8-sig'
            }
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
    todo.updated_at = datetime.utcnow()
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
    
    goal.updated_at = datetime.utcnow()
    db.session.commit()
    
    flash(f'目標の進捗を{goal.progress}%に更新しました。')
    return redirect(url_for('student.goals'))

# テーマ関連
@student_bp.route('/themes')
@login_required
def view_themes():
    """テーマ一覧"""
    if current_user.role == 'student':
        # 学生の場合、自分のテーマを表示
        themes = InquiryTheme.query.filter_by(student_id=current_user.id).all()
        selected_theme = next((t for t in themes if t.is_selected), None)
        
        # 利用可能なメインテーマを取得
        enrolled_classes = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
        main_themes = []
        for enrollment in enrolled_classes:
            class_themes = MainTheme.query.filter_by(class_id=enrollment.class_id).all()
            main_themes.extend(class_themes)
        
        return render_template('view_themes.html', 
                             themes=themes, 
                             selected_theme=selected_theme,
                             main_themes=main_themes)
    else:
        flash('学生のみアクセス可能です。')
        return redirect(url_for('index'))

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
    
    # 既存の選択を解除
    InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True)\
        .update({'is_selected': False})
    
    # 新しいテーマを選択
    theme.is_selected = True
    db.session.commit()
    
    flash(f'テーマ「{theme.title}」を選択しました。')
    return redirect(url_for('student.view_themes'))

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
    """学生用メインテーマ一覧"""
    # 履修しているクラスのメインテーマを取得
    enrolled_classes = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
    
    class_themes = []
    for enrollment in enrolled_classes:
        themes = MainTheme.query.filter_by(class_id=enrollment.class_id).all()
        if themes:
            class_themes.append({
                'class': enrollment.class_obj,
                'themes': themes
            })
    
    return render_template('student_main_themes.html', class_themes=class_themes)

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
        
        # 新しい個人テーマを作成
        new_theme = InquiryTheme(
            student_id=current_user.id,
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

@student_bp.route('/theme/<int:theme_id>/edit', methods=['GET', 'POST'])
@login_required
@student_required
def edit_theme(theme_id):
    """テーマ編集"""
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
    
    return render_template('edit_theme.html', theme=theme)

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

# チャット機能
@student_bp.route('/chat')
@login_required
def chat_page():
    """チャットページ"""
    # ユーザーの役割に応じて適切なチャット履歴を取得
    chat_history = ChatHistory.query.filter_by(user_id=current_user.id)\
        .order_by(ChatHistory.timestamp)\
        .all()
    
    return render_template('chat.html', chat_history=chat_history)