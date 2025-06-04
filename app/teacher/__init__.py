# app/teacher/__init__.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, jsonify, session, current_app
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime
import json
import csv
import io
import os
import logging

from app.models import (
    db, User, Class, ClassEnrollment, MainTheme, InquiryTheme,
    Milestone, StudentEvaluation, Curriculum, RubricTemplate,
    Group, GroupMembership, School, InterestSurvey, PersonalitySurvey,
    ActivityLog, Goal, Todo
)
from app.ai import generate_student_evaluation, generate_curriculum_with_ai

# Conditional import to avoid circular imports
try:
    from app.ai.helpers import generate_activity_summary
except ImportError:
    def generate_activity_summary(*args, **kwargs):
        return "活動概要の生成に失敗しました。"
from app.models import ChatHistory

# Conditional import for PDF generator
try:
    from .pdf_generator import generate_student_report_pdf
except ImportError:
    def generate_student_report_pdf(*args, **kwargs):
        return None

teacher_bp = Blueprint('teacher', __name__)

def teacher_required(f):
    """教師権限を要求するデコレータ"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'teacher':
            flash('この機能は教師のみ利用可能です。')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@teacher_bp.route('/teacher_dashboard')
@login_required
@teacher_required
def dashboard():
    """教師ダッシュボード"""
    # 教師が担当するクラスを取得
    classes = Class.query.filter_by(teacher_id=current_user.id).all()
    
    # 各クラスの生徒数と統計情報を計算
    class_info = []
    for class_obj in classes:
        # 生徒数を取得
        enrollments = ClassEnrollment.query.filter_by(class_id=class_obj.id).all()
        student_count = len(enrollments)
        
        # アンケート完了数を計算
        survey_completed = 0
        theme_selected = 0
        
        for enrollment in enrollments:
            student = enrollment.student
            # アンケート完了確認
            if student.has_completed_surveys():
                survey_completed += 1
            
            # テーマ選択確認
            selected_theme = InquiryTheme.query.filter_by(
                student_id=student.id,
                is_selected=True
            ).first()
            if selected_theme:
                theme_selected += 1
        
        # 次回のマイルストーンを取得
        next_milestone = Milestone.query.filter_by(class_id=class_obj.id)\
            .filter(Milestone.due_date >= datetime.utcnow().date())\
            .order_by(Milestone.due_date).first()
        
        class_info.append({
            'class': class_obj,
            'student_count': student_count,
            'survey_completed': survey_completed,
            'theme_selected': theme_selected,
            'next_milestone': next_milestone
        })
    
    # 承認待ちの学生数を取得
    pending_students_count = 0
    if current_user.school_id:
        pending_students_count = User.query.filter_by(
            role='student',
            school_id=current_user.school_id,
            email_confirmed=True,
            is_approved=False
        ).count()
    
    return render_template('teacher_dashboard.html', 
                         classes=class_info,  # テンプレートはclassesを期待している
                         pending_students_count=pending_students_count)

@teacher_bp.route('/teacher/pending_users')
@login_required
@teacher_required
def pending_users():
    """承認待ちユーザー一覧"""
    # 同じ学校の承認待ち学生を取得
    pending_students = User.query.filter_by(
        role='student',
        school_id=current_user.school_id,
        email_confirmed=True,
        is_approved=False
    ).all()
    
    return render_template('teacher/pending_users.html', pending_students=pending_students)

@teacher_bp.route('/teacher/approve_user/<int:user_id>', methods=['POST'])
@login_required
@teacher_required
def approve_user(user_id):
    """ユーザー承認"""
    user = User.query.get_or_404(user_id)
    
    # 同じ学校の学生のみ承認可能
    if user.school_id != current_user.school_id or user.role != 'student':
        flash('このユーザーを承認する権限がありません。')
        return redirect(url_for('teacher.pending_users'))
    
    user.is_approved = True
    db.session.commit()
    
    flash(f'{user.username} を承認しました。')
    return redirect(url_for('teacher.pending_users'))

# クラス管理
@teacher_bp.route('/classes')
@login_required
def classes():
    """クラス一覧"""
    if current_user.role == 'teacher':
        # 教師の場合は自分が担当するクラスのみ表示
        classes = Class.query.filter_by(teacher_id=current_user.id).all()
        return render_template('teacher_classes.html', classes=classes)
    elif current_user.role == 'student':
        # 生徒の場合は履修しているクラスを表示
        enrollments = ClassEnrollment.query.filter_by(student_id=current_user.id).all()
        classes = [enrollment.class_obj for enrollment in enrollments]
        return render_template('student_classes.html', classes=classes)
    else:
        flash('アクセス権限がありません。')
        return redirect(url_for('index'))

@teacher_bp.route('/create_class', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_class():
    """クラス作成"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        schedule = request.form.get('schedule')
        location = request.form.get('location')
        
        # 必須フィールドの確認
        if not name:
            flash('クラス名は必須です。')
            return render_template('create_class.html')
        
        # 新しいクラスを作成
        new_class = Class(
            teacher_id=current_user.id,
            school_id=current_user.school_id,
            name=name,
            description=description,
            schedule=schedule,
            location=location
        )
        
        db.session.add(new_class)
        db.session.commit()
        
        flash('クラスが作成されました。')
        return redirect(url_for('teacher.class_details', class_id=new_class.id))
    
    return render_template('create_class.html')

@teacher_bp.route('/class/<int:class_id>')
@login_required
def class_details(class_id):
    """クラス詳細"""
    class_obj = Class.query.get_or_404(class_id)
    
    # アクセス権限の確認
    if current_user.role == 'teacher' and class_obj.teacher_id != current_user.id:
        flash('このクラスへのアクセス権限がありません。')
        return redirect(url_for('teacher.classes'))
    elif current_user.role == 'student':
        enrollment = ClassEnrollment.query.filter_by(
            class_id=class_id,
            student_id=current_user.id
        ).first()
        if not enrollment:
            flash('このクラスへのアクセス権限がありません。')
            return redirect(url_for('teacher.classes'))
    
    # 生徒一覧を詳細情報と共に取得
    enrollments = ClassEnrollment.query.filter_by(class_id=class_id).all()
    students_info = []
    
    for enrollment in enrollments:
        student = enrollment.student
        
        # 学生の選択したテーマを取得
        selected_theme = InquiryTheme.query.filter_by(
            student_id=student.id,
            is_selected=True
        ).first()
        
        # 最新の活動記録を取得
        latest_activity = ActivityLog.query.filter_by(
            student_id=student.id
        ).order_by(ActivityLog.timestamp.desc()).first()
        
        # 学生の情報をまとめる
        student_info = {
            'student': student,
            'enrollment': enrollment,
            'selected_theme': selected_theme,
            'latest_activity': latest_activity
        }
        students_info.append(student_info)
    
    # メインテーマを取得
    main_themes = MainTheme.query.filter_by(class_id=class_id).all()
    
    # マイルストーンを取得
    milestones = Milestone.query.filter_by(class_id=class_id).order_by(Milestone.due_date).all()
    
    return render_template('class_details.html', 
                         class_obj=class_obj, 
                         students_info=students_info,
                         main_themes=main_themes,
                         milestones=milestones,
                         today=datetime.now().date())

@teacher_bp.route('/view_class/<int:class_id>')
@login_required
def view_class(class_id):
    """クラス詳細表示（リダイレクト用）"""
    return redirect(url_for('teacher.class_details', class_id=class_id))

@teacher_bp.route('/class/<int:class_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_class(class_id):
    """クラス編集"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスを編集する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    if request.method == 'POST':
        class_obj.name = request.form.get('name', class_obj.name)
        class_obj.description = request.form.get('description', class_obj.description)
        class_obj.schedule = request.form.get('schedule', class_obj.schedule)
        class_obj.location = request.form.get('location', class_obj.location)
        
        db.session.commit()
        flash('クラス情報が更新されました。')
        return redirect(url_for('teacher.class_details', class_id=class_id))
    
    return render_template('edit_class.html', class_obj=class_obj)

@teacher_bp.route('/class/<int:class_id>/delete')
@login_required
@teacher_required
def delete_class(class_id):
    """クラス削除"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスを削除する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    # 関連データも含めて削除
    db.session.delete(class_obj)
    db.session.commit()
    
    flash('クラスが削除されました。')
    return redirect(url_for('teacher.classes'))

@teacher_bp.route('/class/<int:class_id>/add_students', methods=['GET', 'POST'])
@login_required
@teacher_required
def add_students(class_id):
    """クラスに生徒を追加"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスに生徒を追加する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    if request.method == 'POST':
        added_count = 0
        error_count = 0
        
        # CSVファイルアップロードの処理
        if 'csv_file' in request.files:
            file = request.files['csv_file']
            if file and file.filename.endswith('.csv'):
                try:
                    # CSVファイルを読み込む
                    import csv
                    import io
                    stream = io.StringIO(file.stream.read().decode('utf-8'))
                    csv_reader = csv.DictReader(stream)
                    
                    for row in csv_reader:
                        username = row.get('username', '').strip()
                        if username:
                            student = User.query.filter_by(username=username, role='student').first()
                            if student and student.school_id == current_user.school_id:
                                # 既に登録されていないか確認
                                existing = ClassEnrollment.query.filter_by(
                                    class_id=class_id,
                                    student_id=student.id
                                ).first()
                                
                                if not existing:
                                    enrollment = ClassEnrollment(
                                        class_id=class_id,
                                        student_id=student.id
                                    )
                                    db.session.add(enrollment)
                                    added_count += 1
                            else:
                                error_count += 1
                except Exception as e:
                    flash(f'CSVファイルの処理中にエラーが発生しました: {str(e)}')
                    return redirect(url_for('teacher.add_students', class_id=class_id))
        
        # テキスト入力での処理（フォールバック）
        elif 'student_usernames' in request.form:
            student_usernames = request.form.get('student_usernames', '').split(',')
            
            for username in student_usernames:
                username = username.strip()
                if username:
                    student = User.query.filter_by(username=username, role='student').first()
                    if student and student.school_id == current_user.school_id:
                        # 既に登録されていないか確認
                        existing = ClassEnrollment.query.filter_by(
                            class_id=class_id,
                            student_id=student.id
                        ).first()
                        
                        if not existing:
                            enrollment = ClassEnrollment(
                                class_id=class_id,
                                student_id=student.id
                            )
                            db.session.add(enrollment)
                            added_count += 1
        
        db.session.commit()
        
        if added_count > 0:
            flash(f'{added_count}名の生徒をクラスに追加しました。')
        if error_count > 0:
            flash(f'{error_count}名の生徒が見つからないか、追加できませんでした。')
        if added_count == 0 and error_count == 0:
            flash('生徒が追加されませんでした。CSVファイルまたはユーザー名を確認してください。')
        
        return redirect(url_for('teacher.class_details', class_id=class_id))
    
    # 未登録の生徒一覧を取得
    enrolled_student_ids = [e.student_id for e in ClassEnrollment.query.filter_by(class_id=class_id).all()]
    available_students = User.query.filter_by(
        role='student',
        school_id=current_user.school_id,
        is_approved=True
    ).filter(~User.id.in_(enrolled_student_ids)).all()
    
    return render_template('add_students.html', class_obj=class_obj, available_students=available_students)

@teacher_bp.route('/download_student_template')
@login_required
@teacher_required
def download_student_template():
    """生徒追加用CSVテンプレートダウンロード"""
    from flask import make_response
    
    # CSVデータを作成
    csv_data = io.StringIO()
    csv_writer = csv.writer(csv_data)
    
    # ヘッダー行
    csv_writer.writerow(['username'])
    
    # サンプル行
    csv_writer.writerow(['taro_yamada'])
    csv_writer.writerow(['hanako_tanaka'])
    csv_writer.writerow(['jiro_suzuki'])
    
    # CSVデータを取得
    csv_data.seek(0)
    output = make_response(csv_data.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=student_add_template.csv"
    output.headers["Content-type"] = "text/csv; charset=utf-8"
    
    return output

@teacher_bp.route('/class/<int:class_id>/remove_student/<int:student_id>', methods=['POST'])
@login_required
@teacher_required
def remove_student(class_id, student_id):
    """クラスから生徒を削除"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    enrollment = ClassEnrollment.query.filter_by(
        class_id=class_id,
        student_id=student_id
    ).first()
    
    if enrollment:
        db.session.delete(enrollment)
        db.session.commit()
        flash('生徒をクラスから削除しました。')
    
    return redirect(url_for('teacher.class_details', class_id=class_id))

# メインテーマ管理
@teacher_bp.route('/class/<int:class_id>/main_themes')
@login_required
@teacher_required
def view_main_themes(class_id):
    """メインテーマ一覧"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスのテーマを表示する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    main_themes = MainTheme.query.filter_by(class_id=class_id).all()
    
    return render_template('main_themes.html', class_obj=class_obj, main_themes=main_themes)

@teacher_bp.route('/class/<int:class_id>/main_themes/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_main_theme(class_id):
    """メインテーマ作成"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスにテーマを作成する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        
        if not title:
            flash('タイトルは必須です。')
            return render_template('create_main_theme.html', class_obj=class_obj)
        
        new_theme = MainTheme(
            teacher_id=current_user.id,
            class_id=class_id,
            title=title,
            description=description
        )
        
        db.session.add(new_theme)
        db.session.commit()
        
        flash('メインテーマが作成されました。')
        return redirect(url_for('teacher.view_main_themes', class_id=class_id))
    
    return render_template('create_main_theme.html', class_obj=class_obj)

@teacher_bp.route('/main_theme/<int:theme_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_main_theme(theme_id):
    """メインテーマ編集"""
    theme = MainTheme.query.get_or_404(theme_id)
    
    # 権限チェック
    if theme.teacher_id != current_user.id:
        flash('このテーマを編集する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    if request.method == 'POST':
        theme.title = request.form.get('title', theme.title)
        theme.description = request.form.get('description', theme.description)
        theme.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('メインテーマが更新されました。')
        return redirect(url_for('teacher.view_main_themes', class_id=theme.class_id))
    
    return render_template('edit_main_theme.html', theme=theme)

@teacher_bp.route('/main_theme/<int:theme_id>/delete')
@login_required
@teacher_required
def delete_main_theme(theme_id):
    """メインテーマ削除"""
    theme = MainTheme.query.get_or_404(theme_id)
    
    # 権限チェック
    if theme.teacher_id != current_user.id:
        flash('このテーマを削除する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    class_id = theme.class_id
    db.session.delete(theme)
    db.session.commit()
    
    flash('メインテーマが削除されました。')
    return redirect(url_for('teacher.view_main_themes', class_id=class_id))

# マイルストーン管理
@teacher_bp.route('/create_milestone/<int:class_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_milestone(class_id):
    """マイルストーン作成"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスにマイルストーンを作成する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        due_date_str = request.form.get('due_date')
        
        if not title or not due_date_str:
            flash('タイトルと期限日は必須です。')
            return render_template('create_milestone.html', class_obj=class_obj)
        
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('日付の形式が正しくありません。')
            return render_template('create_milestone.html', class_obj=class_obj)
        
        new_milestone = Milestone(
            class_id=class_id,
            title=title,
            description=description,
            due_date=due_date
        )
        
        db.session.add(new_milestone)
        db.session.commit()
        
        flash('マイルストーンが作成されました。')
        return redirect(url_for('teacher.class_details', class_id=class_id))
    
    return render_template('create_milestone.html', class_obj=class_obj)

@teacher_bp.route('/edit_milestone/<int:milestone_id>', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_milestone(milestone_id):
    """マイルストーン編集"""
    milestone = Milestone.query.get_or_404(milestone_id)
    class_obj = milestone.class_obj
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このマイルストーンを編集する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    if request.method == 'POST':
        milestone.title = request.form.get('title', milestone.title)
        milestone.description = request.form.get('description', milestone.description)
        
        due_date_str = request.form.get('due_date')
        if due_date_str:
            try:
                milestone.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('日付の形式が正しくありません。')
                return render_template('edit_milestone.html', milestone=milestone)
        
        db.session.commit()
        flash('マイルストーンが更新されました。')
        return redirect(url_for('teacher.class_details', class_id=class_obj.id))
    
    return render_template('edit_milestone.html', milestone=milestone)

@teacher_bp.route('/delete_milestone/<int:milestone_id>')
@login_required
@teacher_required
def delete_milestone(milestone_id):
    """マイルストーン削除"""
    milestone = Milestone.query.get_or_404(milestone_id)
    class_obj = milestone.class_obj
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このマイルストーンを削除する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    db.session.delete(milestone)
    db.session.commit()
    
    flash('マイルストーンが削除されました。')
    return redirect(url_for('teacher.class_details', class_id=class_obj.id))

# 評価関連
@teacher_bp.route('/class/<int:class_id>/generate_evaluations', methods=['GET', 'POST'])
@login_required
@teacher_required
def generate_evaluations(class_id):
    """生徒評価生成"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスの評価を生成する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    # 生徒一覧を取得
    enrollments = ClassEnrollment.query.filter_by(class_id=class_id).all()
    students = [enrollment.student for enrollment in enrollments]
    
    # カリキュラムを取得
    curriculum = Curriculum.query.filter_by(class_id=class_id).first()
    
    # ルーブリックテンプレートを取得
    rubric = RubricTemplate.query.filter_by(class_id=class_id).first()
    
    if request.method == 'POST':
        selected_student_ids = request.form.getlist('student_ids')
        
        if not selected_student_ids:
            flash('評価する生徒を選択してください。')
            return render_template('evaluate_students.html', 
                                 class_obj=class_obj, 
                                 students=students,
                                 curriculum=curriculum,
                                 rubric=rubric)
        
        evaluations = []
        
        for student_id in selected_student_ids:
            student = User.query.get(int(student_id))
            if not student:
                continue
            
            # 生徒の探究テーマを取得
            theme = InquiryTheme.query.filter_by(
                student_id=student.id,
                is_selected=True
            ).first()
            
            # 生徒の目標を取得
            goals = Goal.query.filter_by(student_id=student.id).all()
            
            # 生徒の活動記録を取得
            activity_logs = ActivityLog.query.filter_by(student_id=student.id).all()
            
            # カリキュラムとルーブリックのデータを準備
            curriculum_data = json.loads(curriculum.content) if curriculum and curriculum.content else None
            rubric_data = json.loads(rubric.content) if rubric and rubric.content else None
            
            # AI評価を生成
            evaluation_text = generate_student_evaluation(
                student, theme, goals, activity_logs, curriculum_data, rubric_data
            )
            
            # 評価を保存
            existing_eval = StudentEvaluation.query.filter_by(
                student_id=student.id,
                class_id=class_id
            ).first()
            
            if existing_eval:
                existing_eval.evaluation_text = evaluation_text
                existing_eval.updated_at = datetime.utcnow()
            else:
                new_eval = StudentEvaluation(
                    student_id=student.id,
                    class_id=class_id,
                    evaluation_text=evaluation_text
                )
                db.session.add(new_eval)
            
            evaluations.append({
                'student': student,
                'evaluation': evaluation_text
            })
        
        db.session.commit()
        
        # 評価をセッションに保存（エクスポート用）
        import json
        session['evaluations'] = json.dumps([
            {
                'student_name': eval['student'].username,
                'evaluation': eval['evaluation']
            } for eval in evaluations
        ])
        session['class_name'] = class_obj.name
        session['class_id'] = class_id
        
        flash(f'{len(evaluations)}名の評価を生成しました。')
        return render_template('evaluation_results.html', 
                             evaluations=evaluations,
                             class_obj=class_obj)
    
    return render_template('evaluate_students.html', 
                         class_obj=class_obj, 
                         students=students,
                         curriculum=curriculum,
                         rubric=rubric)

# カリキュラム管理
@teacher_bp.route('/class/<int:class_id>/curriculums')
@login_required
@teacher_required
def view_curriculums(class_id):
    """カリキュラム一覧"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスのカリキュラムを表示する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    curriculums = Curriculum.query.filter_by(class_id=class_id).all()
    
    return render_template('curriculums.html', 
                         class_obj=class_obj, 
                         curriculums=curriculums)

@teacher_bp.route('/class/<int:class_id>/curriculum/create')
@login_required
@teacher_required
def create_curriculum_form(class_id):
    """カリキュラム作成フォーム"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスのカリキュラムを作成する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    # メインテーマを取得
    main_themes = MainTheme.query.filter_by(class_id=class_id).all()
    
    return render_template('create_curriculum.html', 
                         class_obj=class_obj,
                         main_themes=main_themes)

@teacher_bp.route('/class/<int:class_id>/curriculum/generate', methods=['POST'])
@login_required
@teacher_required
def generate_curriculum(class_id):
    """カリキュラムAI生成"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        return jsonify({'error': '権限がありません'}), 403
    
    # フォームデータを取得
    data = request.get_json()
    
    # AIでカリキュラムを生成
    try:
        curriculum_content = generate_curriculum_with_ai(data)
        
        # カリキュラムを保存
        new_curriculum = Curriculum(
            class_id=class_id,
            teacher_id=current_user.id,
            title=data.get('title', f'{class_obj.name}のカリキュラム'),
            description=data.get('description', ''),
            total_hours=int(data.get('total_hours', 35)),
            has_fieldwork=data.get('has_fieldwork', False),
            fieldwork_count=int(data.get('fieldwork_count', 0)),
            has_presentation=data.get('has_presentation', True),
            presentation_format=data.get('presentation_format', 'プレゼンテーション'),
            group_work_level=data.get('group_work_level', 'ハイブリッド'),
            external_collaboration=data.get('external_collaboration', False),
            content=json.dumps(curriculum_content, ensure_ascii=False)
        )
        
        db.session.add(new_curriculum)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'curriculum_id': new_curriculum.id,
            'content': curriculum_content
        })
        
    except Exception as e:
        logging.error(f"カリキュラム生成エラー: {e}")
        return jsonify({'error': 'カリキュラムの生成に失敗しました'}), 500

# グループ管理
@teacher_bp.route('/class/<int:class_id>/groups')
@login_required
@teacher_required
def view_groups(class_id):
    """グループ一覧"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスのグループを表示する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    groups = Group.query.filter_by(class_id=class_id).all()
    
    return render_template('view_groups.html', 
                         class_obj=class_obj, 
                         groups=groups)

@teacher_bp.route('/class/<int:class_id>/groups/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_group(class_id):
    """グループ作成"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスにグループを作成する権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        if not name:
            flash('グループ名は必須です。')
            return render_template('create_group.html', class_obj=class_obj)
        
        new_group = Group(
            name=name,
            description=description,
            class_id=class_id,
            created_by=current_user.id
        )
        
        db.session.add(new_group)
        db.session.commit()
        
        flash('グループが作成されました。')
        return redirect(url_for('teacher.view_groups', class_id=class_id))
    
    return render_template('create_group.html', class_obj=class_obj)

# 生徒インポート
def process_student_csv(file, class_id, current_user):
    """CSVファイルから生徒情報を処理"""
    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_reader = csv.DictReader(stream)
    
    results = {
        'created': [],
        'enrolled': [],
        'errors': []
    }
    
    for row_num, row in enumerate(csv_reader, 2):
        try:
            # 必須フィールドの確認
            username = row.get('username', '').strip()
            email = row.get('email', '').strip()
            student_number = row.get('student_number', '').strip()
            
            if not username or not email:
                results['errors'].append(f"行 {row_num}: ユーザー名とメールアドレスは必須です")
                continue
            
            # 既存ユーザーチェック
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                # 既存ユーザーをクラスに登録
                if existing_user.role == 'student' and existing_user.school_id == current_user.school_id:
                    existing_enrollment = ClassEnrollment.query.filter_by(
                        class_id=class_id,
                        student_id=existing_user.id
                    ).first()
                    
                    if not existing_enrollment:
                        enrollment = ClassEnrollment(
                            class_id=class_id,
                            student_id=existing_user.id
                        )
                        db.session.add(enrollment)
                        results['enrolled'].append(username)
                    else:
                        results['errors'].append(f"行 {row_num}: {username} は既にクラスに登録されています")
                else:
                    results['errors'].append(f"行 {row_num}: {username} は生徒ではないか、異なる学校に所属しています")
            else:
                # 新規ユーザー作成
                existing_email = User.query.filter_by(email=email).first()
                if existing_email:
                    results['errors'].append(f"行 {row_num}: メール {email} は既に使用されています")
                    continue
                
                # パスワード生成
                import random
                import string
                password = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
                
                new_user = User(
                    username=username,
                    email=email,
                    password=generate_password_hash(password),
                    role='student',
                    school_id=current_user.school_id,
                    email_confirmed=True,
                    is_approved=True
                )
                
                db.session.add(new_user)
                db.session.flush()  # IDを取得
                
                # クラスに登録
                enrollment = ClassEnrollment(
                    class_id=class_id,
                    student_id=new_user.id
                )
                db.session.add(enrollment)
                
                results['created'].append({
                    'username': username,
                    'password': password
                })
                
        except Exception as e:
            results['errors'].append(f"行 {row_num}: エラー - {str(e)}")
    
    return results

@teacher_bp.route('/class/<int:class_id>/students/import', methods=['GET', 'POST'])
@login_required
@teacher_required
def import_students(class_id):
    """生徒一括インポート"""
    class_obj = Class.query.get_or_404(class_id)
    
    # 権限チェック
    if class_obj.teacher_id != current_user.id:
        flash('このクラスに生徒をインポートする権限がありません。')
        return redirect(url_for('teacher.classes'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('ファイルが選択されていません。')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('ファイルが選択されていません。')
            return redirect(request.url)
        
        if not file.filename.endswith('.csv'):
            flash('CSVファイルを選択してください。')
            return redirect(request.url)
        
        try:
            results = process_student_csv(file, class_id, current_user)
            
            # コミット
            db.session.commit()
            
            # 結果メッセージ
            if results['created']:
                flash(f"{len(results['created'])}名の新規生徒を作成しました。")
            if results['enrolled']:
                flash(f"{len(results['enrolled'])}名の既存生徒をクラスに追加しました。")
            if results['errors']:
                for error in results['errors'][:5]:  # 最初の5件のエラーを表示
                    flash(error, 'error')
                if len(results['errors']) > 5:
                    flash(f"... 他 {len(results['errors']) - 5} 件のエラー", 'error')
            
            # 作成されたアカウント情報を表示
            if results['created']:
                return render_template('import_results.html', 
                                     created_accounts=results['created'],
                                     class_obj=class_obj)
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"生徒インポートエラー: {e}")
            flash(f'インポート中にエラーが発生しました: {str(e)}', 'error')
        
        return redirect(url_for('teacher.class_details', class_id=class_id))
    
    return render_template('teacher_import_students.html', class_obj=class_obj)

# テーマ管理
@teacher_bp.route('/teacher_themes')
@login_required
@teacher_required
def teacher_themes():
    """教師のテーマ管理ページ"""
    # 教師が担当するクラスを取得
    classes = Class.query.filter_by(teacher_id=current_user.id).all()
    
    # 各クラスのメインテーマを取得
    classes_with_themes = []  # 変数名をテンプレートに合わせて変更
    for class_obj in classes:
        main_themes = MainTheme.query.filter_by(class_id=class_obj.id).all()  # themesをmain_themesに変更
        classes_with_themes.append({
            'class': class_obj,
            'main_themes': main_themes  # キー名をmain_themesに変更
        })
    
    return render_template('teacher_themes.html', classes_with_themes=classes_with_themes)  # 変数名を変更

# 最初のクラスを取得するAPI
@teacher_bp.route('/api/teacher/first_class')
@login_required
@teacher_required
def api_teacher_first_class():
    """教師の最初のクラスを取得"""
    first_class = Class.query.filter_by(teacher_id=current_user.id).first()
    if first_class:
        return jsonify({'class_id': first_class.id})
    else:
        return jsonify({'class_id': None})

# チャット機能
@teacher_bp.route('/teacher_chat')
@login_required
def chat_page():
    """チャットページ"""
    # デバッグ用ログ
    current_app.logger.info(f"Teacher chat access by user: {current_user.username}, role: {current_user.role}")
    
    # チャット履歴を取得
    from app.models import ChatHistory
    chat_history = ChatHistory.query.filter_by(user_id=current_user.id)\
        .order_by(ChatHistory.timestamp)\
        .all()
    
    return render_template('chat.html', chat_history=chat_history)

@teacher_bp.route('/class/<int:class_id>/student/<int:student_id>/generate_report', methods=['POST'])
@login_required
@teacher_required
def generate_student_report(class_id, student_id):
    """学生の活動報告PDFを生成"""
    # 権限確認
    class_obj = Class.query.get_or_404(class_id)
    if class_obj.teacher_id != current_user.id:
        flash('このクラスにアクセスする権限がありません。')
        return redirect(url_for('teacher.dashboard'))
    
    # 学生情報取得
    student = User.query.get_or_404(student_id)
    enrollment = ClassEnrollment.query.filter_by(
        student_id=student_id,
        class_id=class_id,
        is_active=True
    ).first()
    
    if not enrollment:
        flash('この学生はクラスに所属していません。')
        return redirect(url_for('teacher.class_details', class_id=class_id))
    
    try:
        # 探究テーマを取得
        theme = InquiryTheme.query.filter_by(
            student_id=student_id,
            class_id=class_id,
            is_selected=True
        ).first()
        
        # 活動記録を取得（最新50件）
        activities = ActivityLog.query.filter_by(
            student_id=student_id,
            class_id=class_id
        ).order_by(ActivityLog.timestamp.desc()).limit(50).all()
        
        # チャット履歴を取得（最新100件）
        chat_histories = ChatHistory.query.filter_by(
            user_id=student_id,
            class_id=class_id
        ).order_by(ChatHistory.timestamp.desc()).limit(100).all()
        
        # AI要約を生成
        activity_texts = [a.content for a in activities if a.content]
        chat_texts = [c.message for c in chat_histories if c.is_user and c.message]
        ai_summary = generate_activity_summary(activity_texts, chat_texts)
        
        # PDF生成
        pdf_buffer = generate_student_report_pdf(
            student, class_obj, activities, chat_histories, theme, ai_summary
        )
        
        # レスポンス作成（メモリから直接送信、保存しない）
        from flask import make_response
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=report_{student.username}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        current_app.logger.info(f"PDF generated for student {student.username} in class {class_obj.name}")
        return response
        
    except Exception as e:
        current_app.logger.error(f"PDF generation error: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        flash('PDF生成中にエラーが発生しました。')
        return redirect(url_for('teacher.class_details', class_id=class_id))