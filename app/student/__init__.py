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
    """学生ダッシュボード（クラス別テーマ表示）"""
    # 生徒が所属するクラスとテーマを取得
    class_themes = []
    enrollments = ClassEnrollment.query.filter_by(
        student_id=current_user.id,
        is_active=True
    ).all()
    
    for enrollment in enrollments:
        class_obj = enrollment.class_obj
        main_theme = MainTheme.query.filter_by(class_id=class_obj.id).first()
        personal_theme = InquiryTheme.query.filter_by(
            student_id=current_user.id,
            class_id=class_obj.id,
            is_selected=True
        ).first()
        
        class_themes.append({
            'class': class_obj,
            'main_theme': main_theme,
            'personal_theme': personal_theme
        })
    
    # 学生が履修しているクラスを取得（既存コードの互換性のため）
    classes = [enrollment.class_obj for enrollment in enrollments]
    
    # アンケートデータを個別に取得（テンプレートで参照されるため）
    interest_survey = InterestSurvey.query.filter_by(
        student_id=current_user.id
    ).order_by(InterestSurvey.submitted_at.desc()).first()
    
    personality_survey = PersonalitySurvey.query.filter_by(
        student_id=current_user.id
    ).order_by(PersonalitySurvey.submitted_at.desc()).first()
    
    # アンケート完了状態をチェック（後方互換性のため）
    has_completed_surveys = bool(interest_survey and personality_survey)
    
    # 選択中のテーマを取得
    selected_theme = InquiryTheme.query.filter_by(
        student_id=current_user.id,
        is_selected=True
    ).first()
    
    # 最新のマイルストーンを取得
    upcoming_milestones = []
    today = datetime.utcnow().date()
    
    for class_obj in classes:
        milestones = Milestone.query.filter_by(class_id=class_obj.id)\
            .filter(Milestone.due_date >= today)\
            .order_by(Milestone.due_date).limit(3).all()
        for milestone in milestones:
            days_remaining = (milestone.due_date - today).days
            upcoming_milestones.append({
                'id': milestone.id,
                'title': milestone.title,
                'due_date': milestone.due_date,
                'days_remaining': days_remaining,
                'class_name': class_obj.name,
                'milestone': milestone,
                'class': class_obj
            })
    
    # 期限日でソート
    upcoming_milestones.sort(key=lambda x: x['due_date'])
    
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
    
    # 最近の活動記録を取得
    recent_activities = ActivityLog.query.filter_by(
        student_id=current_user.id
    ).order_by(ActivityLog.timestamp.desc()).limit(5).all()
    
    # 基礎学力トレーニングデータの取得
    # BaseBuilderのインポートを試みる
    try:
        from basebuilder.models import TextDelivery, TextSet, TextProficiencyRecord
        
        # 配信されたテキストを取得
        delivered_texts = []
        for class_obj in classes:
            deliveries = db.session.query(TextDelivery, TextSet)\
                .join(TextSet, TextDelivery.text_set_id == TextSet.id)\
                .filter(TextDelivery.class_id == class_obj.id)\
                .order_by(TextDelivery.delivered_at.desc())\
                .limit(5).all()
            
            for delivery, text_set in deliveries:
                # 生徒の熟練度を取得
                proficiency = TextProficiencyRecord.query.filter_by(
                    student_id=current_user.id,
                    text_set_id=text_set.id
                ).first()
                
                delivered_texts.append({
                    'delivery': delivery,
                    'text_set': text_set,
                    'proficiency': proficiency,
                    'class': class_obj
                })
        
        # 配信日でソート（最新順）
        delivered_texts.sort(key=lambda x: x['delivery'].delivered_at, reverse=True)
        delivered_texts = delivered_texts[:5]  # 最新5件のみ
        
    except ImportError:
        # BaseBuilderモジュールが利用できない場合
        delivered_texts = []
    
    return render_template('student_dashboard.html',
                         class_themes=class_themes,
                         classes=classes,
                         has_completed_surveys=has_completed_surveys,
                         interest_survey=interest_survey,
                         personality_survey=personality_survey,
                         selected_theme=selected_theme,
                         upcoming_milestones=upcoming_milestones,
                         pending_todos=pending_todos,
                         todos=pending_todos,  # テンプレートがtodosを期待している
                         active_goals=active_goals,
                         recent_activities=recent_activities,
                         delivered_texts=delivered_texts,
                         today=datetime.utcnow().date())

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
                    upload_folder = current_app.config['UPLOAD_FOLDER']
                    if not os.path.exists(upload_folder):
                        os.makedirs(upload_folder)
                    
                    filepath = os.path.join(upload_folder, filename)
                    file.save(filepath)
                    
                    # URLパスを保存
                    new_log.image_url = f"/static/uploads/{filename}"
        
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
            themes = InquiryTheme.query.filter_by(
                student_id=current_user.id,
                class_id=class_id
            ).all()
            
            current_app.logger.info(f"Found {len(themes)} personal themes")
            for theme in themes:
                current_app.logger.info(f"Theme ID: {theme.id}, Title: {theme.title}, Is Selected: {theme.is_selected}")
            
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
            question=theme_title,  # 質問フィールドにもタイトルを設定
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
        
        # アンケート回答を取得
        interest_survey = InterestSurvey.query.filter_by(student_id=current_user.id).first()
        personality_survey = PersonalitySurvey.query.filter_by(student_id=current_user.id).first()
        
        # 既存のgenerate_personal_themes_with_ai関数を使用
        if main_theme:
            themes = generate_personal_themes_with_ai(
                main_theme=main_theme,
                interest_survey=interest_survey,
                personality_survey=personality_survey,
                additional_interests=interests
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
    """チャットページ（クラス別）"""
    # 教師の場合は別の処理
    if current_user.role == 'teacher':
        current_app.logger.info(f"Teacher chat access by user: {current_user.username}, role: {current_user.role}")
        # 教師は直接チャットページへ
        chat_history = ChatHistory.query.filter_by(
            user_id=current_user.id
        ).order_by(ChatHistory.timestamp.asc()).all()
        selected_class = None
        theme = None
        learning_steps = []
        return render_template('chat.html', 
                             chat_history=chat_history,
                             learning_steps=learning_steps,
                             theme=theme,
                             class_id=None,
                             selected_class=selected_class)
    
    # 学生の場合はクラス選択が必要
    class_id = request.args.get('class_id', type=int)
    
    if not class_id:
        # クラス選択画面
        enrollments = ClassEnrollment.query.filter_by(
            student_id=current_user.id,
            is_active=True
        ).all()
        classes = [e.class_obj for e in enrollments]
        return render_template('select_class_for_chat.html', classes=classes)
    
    # クラスが指定されている場合は所属確認
    enrollment = ClassEnrollment.query.filter_by(
        student_id=current_user.id,
        class_id=class_id
    ).first()
    
    if not enrollment:
        flash('このクラスのチャットにアクセスする権限がありません。')
        return redirect(url_for('student.chat_page'))
    
    # デバッグ用ログ
    current_app.logger.info(f"Student chat access by user: {current_user.username}, role: {current_user.role}, class_id: {class_id}")
    
    # チャット履歴を取得
    if class_id:
        current_app.logger.info(f"Getting chat history for class_id: {class_id}")
        chat_history = ChatHistory.query.filter_by(
            user_id=current_user.id,
            class_id=class_id
        ).order_by(ChatHistory.timestamp.asc()).all()
        current_app.logger.info(f"Found {len(chat_history)} chat messages")
    else:
        chat_history = ChatHistory.query.filter_by(
            user_id=current_user.id,
            class_id=None
        ).order_by(ChatHistory.timestamp.asc()).all()
    
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
    
    # 選択中のテーマを取得（学生の場合）
    theme = None
    selected_class = None
    if current_user.role == 'student':
        if class_id:
            theme = InquiryTheme.query.filter_by(
                student_id=current_user.id,
                class_id=class_id,
                is_selected=True
            ).first()
            selected_class = Class.query.get(class_id)
        else:
            theme = InquiryTheme.query.filter_by(
                student_id=current_user.id,
                is_selected=True
            ).first()
    
    return render_template('chat.html', 
                         chat_history=chat_history,
                         learning_steps=learning_steps,
                         theme=theme,
                         class_id=class_id,
                         selected_class=selected_class)