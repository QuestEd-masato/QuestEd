# app/admin/school_management.py
"""
学校、年度、クラス管理関連のルート
"""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime
from app.models import School, SchoolYear, ClassGroup, StudentEnrollment, User, db
from app.admin import admin_bp, admin_required

# 学校一覧
@admin_bp.route('/schools')
@login_required
@admin_required
def admin_schools():
    """学校一覧"""
    schools = School.query.all()
    return render_template('admin/schools.html', schools=schools)

# 学校詳細
@admin_bp.route('/school/<int:school_id>')
@login_required
@admin_required
def admin_school_detail(school_id):
    """学校詳細"""
    school = School.query.get_or_404(school_id)
    years = SchoolYear.query.filter_by(school_id=school_id).order_by(SchoolYear.year.desc()).all()
    return render_template('admin/school_detail.html', school=school, years=years)

# 学校年度一覧
@admin_bp.route('/school/<int:school_id>/years')
@login_required
@admin_required
def admin_school_years(school_id):
    """学校年度一覧"""
    school = School.query.get_or_404(school_id)
    years = SchoolYear.query.filter_by(school_id=school_id).order_by(SchoolYear.year.desc()).all()
    return render_template('admin/school_years.html', school=school, years=years)

# 学校年度作成
@admin_bp.route('/school/<int:school_id>/year/create', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_create_school_year(school_id):
    """学校年度作成"""
    school = School.query.get_or_404(school_id)
    
    if request.method == 'POST':
        year = request.form.get('year')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        is_current = 'is_current' in request.form
        
        if not year:
            flash('年度は必須です。')
            return render_template('admin/create_school_year.html', school=school)
        
        # 年度が既に存在するか確認
        existing_year = SchoolYear.query.filter_by(school_id=school_id, year=year).first()
        if existing_year:
            flash('この学校の年度は既に存在します。')
            return render_template('admin/create_school_year.html', school=school)
        
        # 日付文字列をdateオブジェクトに変換
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        
        # 現在のフラグを設定する場合、他の年度のフラグをリセット
        if is_current:
            SchoolYear.query.filter_by(school_id=school_id, is_current=True).update({'is_current': False})
        
        # 年度を作成
        new_year = SchoolYear(
            school_id=school_id,
            year=year,
            start_date=start_date,
            end_date=end_date,
            is_current=is_current
        )
        
        db.session.add(new_year)
        db.session.commit()
        
        flash('学校年度が作成されました。')
        return redirect(url_for('admin_panel.admin_school_detail', school_id=school_id))
    
    return render_template('admin/create_school_year.html', school=school)

# 学校年度編集
@admin_bp.route('/school_year/<int:year_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_school_year(year_id):
    """学校年度編集"""
    school_year = SchoolYear.query.get_or_404(year_id)
    
    if request.method == 'POST':
        school_year.year = request.form.get('year')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        is_current = 'is_current' in request.form
        
        # 日付文字列をdateオブジェクトに変換
        school_year.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        school_year.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        
        # 現在のフラグを設定する場合、他の年度のフラグをリセット
        if is_current and not school_year.is_current:
            SchoolYear.query.filter_by(school_id=school_year.school_id, is_current=True).update({'is_current': False})
        
        school_year.is_current = is_current
        
        db.session.commit()
        flash('学校年度が更新されました。')
        return redirect(url_for('admin_panel.admin_school_years', school_id=school_year.school_id))
    
    return render_template('admin/edit_school_year.html', school_year=school_year)

# 現在年度設定
@admin_bp.route('/school_year/<int:year_id>/set_current', methods=['POST'])
@login_required
@admin_required
def admin_set_current_year(year_id):
    """現在年度設定"""
    school_year = SchoolYear.query.get_or_404(year_id)
    
    # 他の年度のフラグをリセット
    SchoolYear.query.filter_by(school_id=school_year.school_id, is_current=True).update({'is_current': False})
    
    # 現在の年度を設定
    school_year.is_current = True
    db.session.commit()
    
    flash(f'{school_year.year}年度を現在の年度に設定しました。')
    return redirect(url_for('admin_panel.admin_school_years', school_id=school_year.school_id))

# クラスグループ一覧
@admin_bp.route('/school_year/<int:year_id>/classes')
@login_required
@admin_required
def admin_class_groups(year_id):
    """クラスグループ一覧"""
    school_year = SchoolYear.query.get_or_404(year_id)
    classes = ClassGroup.query.filter_by(school_year_id=year_id).all()
    return render_template('admin/class_groups.html', school_year=school_year, classes=classes)

# クラスグループ作成
@admin_bp.route('/school_year/<int:year_id>/class_group/create', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_create_class_group(year_id):
    """クラスグループ作成"""
    school_year = SchoolYear.query.get_or_404(year_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        grade = request.form.get('grade')
        teacher_id = request.form.get('teacher_id')
        description = request.form.get('description')
        
        if not name:
            flash('クラス名は必須です。')
            teachers = User.query.filter_by(role='teacher', school_id=school_year.school_id).all()
            return render_template('admin/create_class_group.html', school_year=school_year, teachers=teachers)
        
        # クラスグループを作成
        new_class = ClassGroup(
            school_year_id=year_id,
            name=name,
            grade=grade,
            teacher_id=teacher_id if teacher_id else None,
            description=description
        )
        
        db.session.add(new_class)
        db.session.commit()
        
        flash('クラスが作成されました。')
        return redirect(url_for('admin_panel.admin_class_groups', year_id=year_id))
    
    # 教師一覧を取得
    teachers = User.query.filter_by(role='teacher', school_id=school_year.school_id).all()
    return render_template('admin/create_class_group.html', school_year=school_year, teachers=teachers)

# 生徒登録管理
@admin_bp.route('/class_group/<int:class_id>/students')
@login_required
@admin_required
def admin_student_enrollment(class_id):
    """生徒登録管理"""
    class_group = ClassGroup.query.get_or_404(class_id)
    enrollments = StudentEnrollment.query.filter_by(class_group_id=class_id).all()
    
    # 登録可能な生徒を取得（同じ学校の生徒で、まだこのクラスに登録されていない生徒）
    enrolled_student_ids = [e.student_id for e in enrollments]
    available_students = User.query.filter(
        User.role == 'student',
        User.school_id == class_group.school_year.school_id,
        ~User.id.in_(enrolled_student_ids) if enrolled_student_ids else True
    ).all()
    
    return render_template('admin/student_enrollment.html', 
                         class_group=class_group, 
                         enrollments=enrollments,
                         available_students=available_students)

# 生徒登録追加
@admin_bp.route('/class_group/<int:class_id>/enroll_student', methods=['POST'])
@login_required
@admin_required
def admin_enroll_student(class_id):
    """生徒をクラスに登録"""
    class_group = ClassGroup.query.get_or_404(class_id)
    student_id = request.form.get('student_id')
    
    if not student_id:
        flash('生徒を選択してください。')
        return redirect(url_for('admin_panel.admin_student_enrollment', class_id=class_id))
    
    # 既に登録されているか確認
    existing = StudentEnrollment.query.filter_by(
        class_group_id=class_id,
        student_id=student_id
    ).first()
    
    if existing:
        flash('この生徒は既にクラスに登録されています。')
    else:
        enrollment = StudentEnrollment(
            class_group_id=class_id,
            student_id=student_id
        )
        db.session.add(enrollment)
        db.session.commit()
        flash('生徒をクラスに登録しました。')
    
    return redirect(url_for('admin_panel.admin_student_enrollment', class_id=class_id))

# 生徒登録削除
@admin_bp.route('/enrollment/<int:enrollment_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_enrollment(enrollment_id):
    """生徒登録削除"""
    enrollment = StudentEnrollment.query.get_or_404(enrollment_id)
    class_id = enrollment.class_group_id
    
    db.session.delete(enrollment)
    db.session.commit()
    
    flash('生徒をクラスから削除しました。')
    return redirect(url_for('admin_panel.admin_student_enrollment', class_id=class_id))

# 学校作成
@admin_bp.route('/schools/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_school():
    """学校作成"""
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        address = request.form.get('address')
        phone = request.form.get('phone')
        email = request.form.get('email')
        
        if not name:
            flash('学校名は必須です。')
            return render_template('admin/create_school.html')
        
        # 学校コードの重複チェック
        if code:
            existing = School.query.filter_by(code=code).first()
            if existing:
                flash('この学校コードは既に使用されています。')
                return render_template('admin/create_school.html')
        
        # 学校を作成
        new_school = School(
            name=name,
            code=code,
            address=address,
            phone=phone,
            email=email
        )
        
        db.session.add(new_school)
        db.session.commit()
        
        flash('学校が作成されました。')
        return redirect(url_for('admin_panel.admin_schools'))
    
    return render_template('admin/create_school.html')

# 学校編集
@admin_bp.route('/schools/<int:school_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_school(school_id):
    """学校編集"""
    school = School.query.get_or_404(school_id)
    
    if request.method == 'POST':
        school.name = request.form.get('name')
        school.code = request.form.get('code')
        school.address = request.form.get('address')
        school.phone = request.form.get('phone')
        school.email = request.form.get('email')
        
        if not school.name:
            flash('学校名は必須です。')
            return render_template('admin/edit_school.html', school=school)
        
        # 学校コードの重複チェック（自分以外）
        if school.code:
            existing = School.query.filter(
                School.code == school.code,
                School.id != school_id
            ).first()
            if existing:
                flash('この学校コードは既に使用されています。')
                return render_template('admin/edit_school.html', school=school)
        
        db.session.commit()
        flash('学校情報が更新されました。')
        return redirect(url_for('admin_panel.admin_school_detail', school_id=school_id))
    
    return render_template('admin/edit_school.html', school=school)

# 学校削除
@admin_bp.route('/schools/<int:school_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_school(school_id):
    """学校削除"""
    school = School.query.get_or_404(school_id)
    
    # 学校に関連するユーザーがいるか確認
    users_count = User.query.filter_by(school_id=school_id).count()
    if users_count > 0:
        flash(f'この学校には{users_count}人のユーザーが所属しているため、削除できません。')
        return redirect(url_for('admin_panel.admin_school_detail', school_id=school_id))
    
    # 学校年度を削除
    SchoolYear.query.filter_by(school_id=school_id).delete()
    
    # 学校を削除
    db.session.delete(school)
    db.session.commit()
    
    flash('学校が削除されました。')
    return redirect(url_for('admin_panel.admin_schools'))

# クラスグループ詳細
@admin_bp.route('/class_group/<int:class_group_id>')
@login_required
@admin_required
def admin_class_group_detail(class_group_id):
    """クラスグループ詳細"""
    class_group = ClassGroup.query.get_or_404(class_group_id)
    enrollments = StudentEnrollment.query.filter_by(class_group_id=class_group_id).all()
    
    return render_template('admin/class_group_detail.html', 
                         class_group=class_group,
                         enrollments=enrollments)

# クラスグループに生徒追加（複数）
@admin_bp.route('/class_group/<int:class_group_id>/add_students', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_students_to_class(class_group_id):
    """クラスグループに生徒を追加"""
    class_group = ClassGroup.query.get_or_404(class_group_id)
    
    if request.method == 'POST':
        student_ids = request.form.getlist('student_ids')
        
        if not student_ids:
            flash('追加する生徒を選択してください。')
        else:
            added_count = 0
            for student_id in student_ids:
                # 既に登録されているか確認
                existing = StudentEnrollment.query.filter_by(
                    class_group_id=class_group_id,
                    student_id=student_id
                ).first()
                
                if not existing:
                    enrollment = StudentEnrollment(
                        class_group_id=class_group_id,
                        student_id=student_id
                    )
                    db.session.add(enrollment)
                    added_count += 1
            
            db.session.commit()
            flash(f'{added_count}人の生徒をクラスに追加しました。')
            return redirect(url_for('admin_panel.admin_class_group_detail', class_group_id=class_group_id))
    
    # 登録可能な生徒を取得
    enrolled_student_ids = [e.student_id for e in StudentEnrollment.query.filter_by(class_group_id=class_group_id).all()]
    available_students = User.query.filter(
        User.role == 'student',
        User.school_id == class_group.school_year.school_id,
        ~User.id.in_(enrolled_student_ids) if enrolled_student_ids else True
    ).all()
    
    return render_template('admin/add_students_to_class.html',
                         class_group=class_group,
                         available_students=available_students)