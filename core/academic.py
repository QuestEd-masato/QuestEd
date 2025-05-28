# core/academic.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from core.models import School, SchoolYear, ClassGroup
from datetime import datetime

academic_bp = Blueprint('academic', __name__, url_prefix='/admin/academic')

@academic_bp.route('/years/<int:school_id>')
@login_required
def list_years(school_id):
    if current_user.role != 'admin':
        flash('この機能は管理者のみ利用可能です。')
        return redirect(url_for('index'))
    
    school = School.query.get_or_404(school_id)
    years = SchoolYear.query.filter_by(school_id=school_id).order_by(SchoolYear.year.desc()).all()
    
    return render_template('admin/school_years.html', school=school, years=years)

@academic_bp.route('/years/create/<int:school_id>', methods=['GET', 'POST'])
@login_required
def create_year(school_id):
    if current_user.role != 'admin':
        flash('この機能は管理者のみ利用可能です。')
        return redirect(url_for('index'))
    
    school = School.query.get_or_404(school_id)
    
    if request.method == 'POST':
        year = request.form.get('year')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        is_current = 'is_current' in request.form
        
        if not year or not start_date or not end_date:
            flash('年度名、開始日、終了日は必須項目です。')
            return render_template('admin/create_school_year.html', school=school)
        
        # 年度の重複チェック
        existing_year = SchoolYear.query.filter_by(school_id=school_id, year=year).first()
        if existing_year:
            flash('この年度は既に登録されています。')
            return render_template('admin/create_school_year.html', school=school)
        
        # 日付文字列をDateオブジェクトに変換
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            flash('日付形式が正しくありません。')
            return render_template('admin/create_school_year.html', school=school)
        
        # 現在の年度を設定する場合、他の年度を非現在に設定
        if is_current:
            SchoolYear.query.filter_by(school_id=school_id, is_current=True).update({'is_current': False})
        
        new_year = SchoolYear(
            school_id=school_id,
            year=year,
            start_date=start_date,
            end_date=end_date,
            is_current=is_current
        )
        
        db.session.add(new_year)
        db.session.commit()
        
        flash('年度が正常に登録されました。')
        return redirect(url_for('academic.list_years', school_id=school_id))
    
    return render_template('admin/create_school_year.html', school=school)