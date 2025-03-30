# core/enrollment.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db, User
from core.models import School, SchoolYear, ClassGroup, StudentEnrollment
from werkzeug.security import generate_password_hash
import csv
import io
import random
import string
from utils.email import send_invitation_email

enrollment_bp = Blueprint('enrollment', __name__, url_prefix='/admin/enrollment')

@enrollment_bp.route('/students/<int:class_id>')
@login_required
def list_students(class_id):
    if current_user.role != 'admin' and current_user.role != 'teacher':
        flash('この機能は管理者と教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    class_group = ClassGroup.query.get_or_404(class_id)
    
    # 教師の場合、自分の担当クラスかチェック
    if current_user.role == 'teacher' and class_group.teacher_id != current_user.id:
        flash('このクラスにアクセスする権限がありません。')
        return redirect(url_for('index'))
    
    # クラスに所属する生徒を取得
    enrollments = StudentEnrollment.query.filter_by(class_group_id=class_id).order_by(StudentEnrollment.student_number).all()
    
    return render_template('admin/student_enrollment.html', 
                          class_group=class_group, 
                          enrollments=enrollments)

@enrollment_bp.route('/students/import/<int:class_id>', methods=['GET', 'POST'])
@login_required
def import_students(class_id):
    if current_user.role != 'admin' and current_user.role != 'teacher':
        flash('この機能は管理者と教師のみ利用可能です。')
        return redirect(url_for('index'))
    
    class_group = ClassGroup.query.get_or_404(class_id)
    school_year = SchoolYear.query.get(class_group.school_year_id)
    
    # 教師の場合、自分の担当クラスかチェック
    if current_user.role == 'teacher' and class_group.teacher_id != current_user.id:
        flash('このクラスにアクセスする権限がありません。')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('CSVファイルが選択されていません。')
            return redirect(request.url)
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('CSVファイルが選択されていません。')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            try:
                # CSVファイルを読み込む
                stream = io.StringIO(file.stream.read().decode('utf-8-sig'))  # BOMを考慮
                csv_reader = csv.DictReader(stream)
                
                # 成功と失敗のカウンター
                success_count = 0
                error_count = 0
                
                # CSVの各行を処理
                for row in csv_reader:
                    try:
                        # 必須項目の確認
                        if not row.get('name') or not row.get('email'):
                            error_count += 1
                            flash(f"行: {csv_reader.line_num} - 名前とメールアドレスは必須です。", 'error')
                            continue
                        
                        name = row.get('name')
                        email = row.get('email')
                        student_number = row.get('student_number', '')
                        
                        # 出席番号を整数に変換
                        try:
                            student_number = int(student_number) if student_number else None
                        except ValueError:
                            student_number = None
                        
                        # 既存のユーザーを確認
                        existing_user = User.query.filter_by(email=email).first()
                        
                        if existing_user:
                            # 既存のユーザーの場合、クラスに登録するだけ
                            user_id = existing_user.id
                            
                            # すでにこのクラスに登録されているか確認
                            existing_enrollment = StudentEnrollment.query.filter_by(
                                student_id=user_id,
                                class_group_id=class_id,
                                school_year_id=school_year.id
                            ).first()
                            
                            if existing_enrollment:
                                # 出席番号のみ更新
                                if student_number:
                                    existing_enrollment.student_number = student_number
                                    db.session.commit()
                                    
                                success_count += 1
                                continue
                        else:
                            # ランダムなパスワードを生成
                            password = generate_random_password()
                            
                            # 新規ユーザーを作成
                            new_user = User(
                                username=email.split('@')[0],  # メールアドレスのユーザー部分をユーザー名に
                                email=email,
                                password=generate_password_hash(password),
                                role='student',
                                school_id=school_year.school_id
                            )
                            
                            db.session.add(new_user)
                            db.session.flush()  # IDを取得するためにフラッシュ
                            
                            user_id = new_user.id
                            
                            # 招待メールを送信
                            try:
                                send_invitation_email(
                                    name=name,
                                    email=email,
                                    username=new_user.username,
                                    password=password,
                                    school_name=school_year.school.name,
                                    class_name=class_group.name
                                )
                            except Exception as e:
                                flash(f"招待メールの送信に失敗しました: {str(e)}", 'warning')
                        
                        # クラスに登録
                        enrollment = StudentEnrollment(
                            student_id=user_id,
                            class_group_id=class_id,
                            school_year_id=school_year.id,
                            student_number=student_number
                        )
                        
                        db.session.add(enrollment)
                        success_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        flash(f"行: {csv_reader.line_num} - エラー: {str(e)}", 'error')
                
                db.session.commit()
                
                flash(f'{success_count}人の生徒をインポートしました。{error_count}件のエラーが発生しました。')
                return redirect(url_for('enrollment.list_students', class_id=class_id))
                
            except Exception as e:
                flash(f'CSVファイルの処理中にエラーが発生しました: {str(e)}')
                return redirect(request.url)
        else:
            flash('CSVファイルの形式が正しくありません。')
            return redirect(request.url)
    
    return render_template('admin/import_students.html', class_group=class_group)

# ランダムなパスワード生成関数
def generate_random_password(length=10):
    characters = string.ascii_letters + string.digits + '!@#$%^&*()'
    return ''.join(random.choice(characters) for _ in range(length))