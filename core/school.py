# core/school.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from extensions import db
from app.models import School, SchoolYear

school_bp = Blueprint('school', __name__, url_prefix='/admin/schools')

@school_bp.route('/')
@login_required
def list_schools():
    if current_user.role != 'admin':
        flash('この機能は管理者のみ利用可能です。')
        return redirect(url_for('index'))
    
    schools = School.query.all()
    return render_template('admin/schools.html', schools=schools)

@school_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_school():
    if current_user.role != 'admin':
        flash('この機能は管理者のみ利用可能です。')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        address = request.form.get('address', '')
        contact_email = request.form.get('contact_email', '')
        
        if not name or not code:
            flash('学校名とコードは必須項目です。')
            return render_template('admin/create_school.html')
        
        # 学校コードの重複チェック
        existing_school = School.query.filter_by(code=code).first()
        if existing_school:
            flash('この学校コードは既に使用されています。')
            return render_template('admin/create_school.html')
        
        new_school = School(
            name=name,
            code=code,
            address=address,
            contact_email=contact_email
        )
        
        db.session.add(new_school)
        db.session.commit()
        
        flash('学校が正常に登録されました。')
        return redirect(url_for('school.list_schools'))
    
    return render_template('admin/create_school.html')