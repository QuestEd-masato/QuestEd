from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import json
from datetime import datetime
from extensions import db
from app import User, InquiryTheme
from basebuilder.models import (
    ProblemCategory, BasicKnowledgeItem, KnowledgeThemeRelation,
    AnswerRecord, ProficiencyRecord, LearningPath, PathAssignment
)

basebuilder = Blueprint('basebuilder_module', __name__, url_prefix='/basebuilder')

# BaseBuilder ホームページ
@basebuilder.route('/basebuilder')
@login_required
def index():
    if current_user.role == 'student':
        # 学生向けダッシュボード
        
        # 学生の熟練度記録を取得
        proficiency_records = ProficiencyRecord.query.filter_by(student_id=current_user.id).all()
        
        # カテゴリごとの熟練度を整理
        category_proficiency = {}
        for record in proficiency_records:
            category_proficiency[record.category.name] = record.level
        
        # 学生の解答記録を最新の10件取得
        recent_answers = AnswerRecord.query.filter_by(
            student_id=current_user.id
        ).order_by(AnswerRecord.timestamp.desc()).limit(10).all()
        
        # 学生の選択した探究テーマを取得
        theme = InquiryTheme.query.filter_by(student_id=current_user.id, is_selected=True).first()
        
        # テーマに関連する問題を取得
        related_problems = []
        if theme:
            theme_relations = KnowledgeThemeRelation.query.filter_by(theme_id=theme.id).all()
            related_problem_ids = [relation.problem_id for relation in theme_relations]
            related_problems = BasicKnowledgeItem.query.filter(
                BasicKnowledgeItem.id.in_(related_problem_ids),
                BasicKnowledgeItem.is_active == True
            ).all()
        
        # 学生に割り当てられた学習パスを取得
        assigned_paths = PathAssignment.query.filter_by(
            student_id=current_user.id,
            completed=False
        ).all()
        
        return render_template(
            'basebuilder/student_dashboard.html',
            category_proficiency=category_proficiency,
            recent_answers=recent_answers,
            related_problems=related_problems,
            assigned_paths=assigned_paths,
            theme=theme
        )
    
    elif current_user.role == 'teacher':
        # 教師向けダッシュボード
        
        # 教師が作成した問題の数を取得
        problem_count = BasicKnowledgeItem.query.filter_by(created_by=current_user.id).count()
        
        # 教師が作成したカテゴリの数を取得
        category_count = ProblemCategory.query.filter_by(created_by=current_user.id).count()
        
        # 教師が作成した学習パスの数を取得
        path_count = LearningPath.query.filter_by(created_by=current_user.id).count()
        
        # 教師が担当するクラスを取得
        classes = User.classes_teaching
        
        # 最近の問題を取得
        recent_problems = BasicKnowledgeItem.query.filter_by(
            created_by=current_user.id
        ).order_by(BasicKnowledgeItem.created_at.desc()).limit(5).all()
        
        return render_template(
            'basebuilder/teacher_dashboard.html',
            problem_count=problem_count,
            category_count=category_count,
            path_count=path_count,
            classes=classes,
            recent_problems=recent_problems
        )
    
    # その他のロールの場合
    return redirect(url_for('index'))

# 問題カテゴリ一覧
@basebuilder.route('/basebuilder/categories')
@login_required
def categories():
    # トップレベルのカテゴリを取得
    top_categories = ProblemCategory.query.filter_by(parent_id=None).all()
    
    return render_template(
        'basebuilder/categories.html',
        top_categories=top_categories
    )

# カテゴリの作成と編集
@basebuilder.route('/basebuilder/category/create', methods=['GET', 'POST'])
@login_required
def create_category():
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder.index'))
    
    # 親カテゴリの選択肢を取得
    parent_categories = ProblemCategory.query.all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        parent_id = request.form.get('parent_id')
        
        if not name:
            flash('カテゴリ名は必須です。')
            return render_template(
                'basebuilder/create_category.html',
                parent_categories=parent_categories
            )
        
        # 親カテゴリIDがあれば整数に変換
        if parent_id:
            try:
                parent_id = int(parent_id)
            except ValueError:
                parent_id = None
        else:
            parent_id = None
        
        # 新しいカテゴリを作成
        new_category = ProblemCategory(
            name=name,
            description=description,
            parent_id=parent_id,
            created_by=current_user.id
        )
        
        db.session.add(new_category)
        db.session.commit()
        
        flash('カテゴリが作成されました。')
        return redirect(url_for('basebuilder.categories'))
    
    return render_template(
        'basebuilder/create_category.html',
        parent_categories=parent_categories
    )

@basebuilder.route('/basebuilder/category/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder.index'))
    
    # カテゴリを取得
    category = ProblemCategory.query.get_or_404(category_id)
    
    # 親カテゴリの選択肢を取得（自分自身を除く）
    parent_categories = ProblemCategory.query.filter(
        ProblemCategory.id != category_id
    ).all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        parent_id = request.form.get('parent_id')
        
        if not name:
            flash('カテゴリ名は必須です。')
            return render_template(
                'basebuilder/edit_category.html',
                category=category,
                parent_categories=parent_categories
            )
        
        # 親カテゴリIDがあれば整数に変換
        if parent_id:
            try:
                parent_id = int(parent_id)
            except ValueError:
                parent_id = None
        else:
            parent_id = None
        
        # カテゴリを更新
        category.name = name
        category.description = description
        category.parent_id = parent_id
        
        db.session.commit()
        
        flash('カテゴリが更新されました。')
        return redirect(url_for('basebuilder.categories'))
    
    return render_template(
        'basebuilder/edit_category.html',
        category=category,
        parent_categories=parent_categories
    )

# 問題一覧
@basebuilder.route('/basebuilder/problems')
@login_required
def problems():
    # クエリパラメータからフィルタリング条件を取得
    category_id = request.args.get('category_id', type=int)
    difficulty = request.args.get('difficulty', type=int)
    search = request.args.get('search', '')
    
    # 基本クエリ
    query = BasicKnowledgeItem.query
    
    # フィルタリング条件の適用
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    
    if search:
        query = query.filter(
            (BasicKnowledgeItem.title.like(f'%{search}%')) |
            (BasicKnowledgeItem.question.like(f'%{search}%'))
        )
    
    # 問題の取得
    problems = query.order_by(BasicKnowledgeItem.created_at.desc()).all()
    
    # カテゴリの取得
    categories = ProblemCategory.query.all()
    
    return render_template(
        'basebuilder/problems.html',
        problems=problems,
        categories=categories,
        selected_category_id=category_id,
        selected_difficulty=difficulty,
        search=search
    )

# 問題の作成と編集
@basebuilder.route('/basebuilder/problem/create', methods=['GET', 'POST'])
@login_required
def create_problem():
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder.index'))
    
    # カテゴリの選択肢を取得
    categories = ProblemCategory.query.all()
    
    if request.method == 'POST':
        category_id = request.form.get('category_id', type=int)
        title = request.form.get('title')
        question = request.form.get('question')
        answer_type = request.form.get('answer_type')
        correct_answer = request.form.get('correct_answer')
        choices = request.form.get('choices', '')
        explanation = request.form.get('explanation', '')
        difficulty = request.form.get('difficulty', type=int, default=2)
        
        # 入力チェック
        if not all([category_id, title, question, answer_type, correct_answer]):
            flash('必須項目が入力されていません。')
            return render_template(
                'basebuilder/create_problem.html',
                categories=categories
            )
        
        # 選択肢がJSONとして有効かチェック
        if answer_type == 'multiple_choice' and choices:
            try:
                choices_json = json.loads(choices)
            except json.JSONDecodeError:
                flash('選択肢が正しいJSON形式ではありません。')
                return render_template(
                    'basebuilder/create_problem.html',
                    categories=categories
                )
        
        # 新しい問題を作成
        new_problem = BasicKnowledgeItem(
            category_id=category_id,
            title=title,
            question=question,
            answer_type=answer_type,
            correct_answer=correct_answer,
            choices=choices,
            explanation=explanation,
            difficulty=difficulty,
            created_by=current_user.id
        )
        
        db.session.add(new_problem)
        db.session.commit()
        
        flash('問題が作成されました。')
        return redirect(url_for('basebuilder.problems'))
    
    return render_template(
        'basebuilder/create_problem.html',
        categories=categories
    )

@basebuilder.route('/basebuilder/problem/<int:problem_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_problem(problem_id):
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder.index'))
    
    # 問題を取得
    problem = BasicKnowledgeItem.query.get_or_404(problem_id)
    
    # カテゴリの選択肢を取得
    categories = ProblemCategory.query.all()
    
    if request.method == 'POST':
        category_id = request.form.get('category_id', type=int)
        title = request.form.get('title')
        question = request.form.get('question')
        answer_type = request.form.get('answer_type')
        correct_answer = request.form.get('correct_answer')
        choices = request.form.get('choices', '')
        explanation = request.form.get('explanation', '')
        difficulty = request.form.get('difficulty', type=int, default=2)
        is_active = 'is_active' in request.form
        
        # 入力チェック
        if not all([category_id, title, question, answer_type, correct_answer]):
            flash('必須項目が入力されていません。')
            return render_template(
                'basebuilder/edit_problem.html',
                problem=problem,
                categories=categories
            )
        
        # 選択肢がJSONとして有効かチェック
        if answer_type == 'multiple_choice' and choices:
            try:
                choices_json = json.loads(choices)
            except json.JSONDecodeError:
                flash('選択肢が正しいJSON形式ではありません。')
                return render_template(
                    'basebuilder/edit_problem.html',
                    problem=problem,
                    categories=categories
                )
        
        # 問題を更新
        problem.category_id = category_id
        problem.title = title
        problem.question = question
        problem.answer_type = answer_type
        problem.correct_answer = correct_answer
        problem.choices = choices
        problem.explanation = explanation
        problem.difficulty = difficulty
        problem.is_active = is_active
        
        db.session.commit()
        
        flash('問題が更新されました。')
        return redirect(url_for('basebuilder.problems'))
    
    return render_template(
        'basebuilder/edit_problem.html',
        problem=problem,
        categories=categories
    )

# 問題を解く
@basebuilder.route('/basebuilder/problem/<int:problem_id>/solve', methods=['GET'])
@login_required
def solve_problem(problem_id):
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('basebuilder.index'))
    
    # 問題を取得
    problem = BasicKnowledgeItem.query.get_or_404(problem_id)
    
    return render_template(
        'basebuilder/solve_problem.html',
        problem=problem
    )

@basebuilder.route('/basebuilder/problem/<int:problem_id>/submit', methods=['POST'])
@login_required
def submit_answer(problem_id):
    if current_user.role != 'student':
        return jsonify({'error': 'この機能は学生のみ利用可能です。'}), 403
    
    # 問題を取得
    problem = BasicKnowledgeItem.query.get_or_404(problem_id)
    
    # フォームデータから回答を取得
    answer = request.form.get('answer')
    answer_time = request.form.get('answer_time', type=int, default=0)
    
    # 回答必須
    if not answer:
        return jsonify({'error': '回答が入力されていません。'}), 400
    
    # 回答が正しいかチェック
    is_correct = False
    
    if problem.answer_type == 'multiple_choice':
        is_correct = (answer == problem.correct_answer)
    elif problem.answer_type == 'text':
        # テキスト回答の場合、正規化して比較
        student_answer = answer.strip().lower()
        correct_answer = problem.correct_answer.strip().lower()
        is_correct = (student_answer == correct_answer)
    elif problem.answer_type == 'true_false':
        is_correct = (answer == problem.correct_answer)
    
    # 解答レコードを作成
    answer_record = AnswerRecord(
        student_id=current_user.id,
        problem_id=problem_id,
        student_answer=answer,
        is_correct=is_correct,
        answer_time=answer_time
    )
    
    db.session.add(answer_record)
    
    # 熟練度を更新
    update_proficiency(current_user.id, problem.category_id, is_correct)
    
    db.session.commit()
    
    # フィードバックを返す
    return jsonify({
        'is_correct': is_correct,
        'correct_answer': problem.correct_answer,
        'explanation': problem.explanation
    })

# 熟練度を更新する関数
def update_proficiency(student_id, category_id, is_correct):
    # 既存の熟練度レコードを取得
    proficiency = ProficiencyRecord.query.filter_by(
        student_id=student_id,
        category_id=category_id
    ).first()
    
    # 熟練度レコードがなければ作成
    if not proficiency:
        proficiency = ProficiencyRecord(
            student_id=student_id,
            category_id=category_id,
            level=0
        )
        db.session.add(proficiency)
    
    # 熟練度を更新
    if is_correct:
        # 正解の場合は熟練度を上げる（上限は100）
        proficiency.level = min(100, proficiency.level + 5)
    else:
        # 不正解の場合は熟練度を下げる（下限は0）
        proficiency.level = max(0, proficiency.level - 3)
    
    proficiency.last_updated = datetime.utcnow()

# 熟練度の表示
@basebuilder.route('/basebuilder/proficiency')
@login_required
def view_proficiency():
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('basebuilder.index'))
    
    # 学生の熟練度記録を取得
    proficiency_records = ProficiencyRecord.query.filter_by(
        student_id=current_user.id
    ).all()
    
    # カテゴリ別の熟練度を整理
    category_proficiency = {}
    for record in proficiency_records:
        category_proficiency[record.category.id] = {
            'category': record.category,
            'level': record.level,
            'last_updated': record.last_updated
        }
    
    # すべてのカテゴリを取得
    all_categories = ProblemCategory.query.all()
    
    # カテゴリごとの問題数を取得
    category_counts = {}
    for category in all_categories:
        count = BasicKnowledgeItem.query.filter_by(
            category_id=category.id,
            is_active=True
        ).count()
        category_counts[category.id] = count
    
    return render_template(
        'basebuilder/proficiency.html',
        proficiency_records=proficiency_records,
        category_proficiency=category_proficiency,
        all_categories=all_categories,
        category_counts=category_counts
    )

# 学習履歴の表示
@basebuilder.route('/basebuilder/history')
@login_required
def view_history():
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('basebuilder.index'))
    
    # 学生の解答履歴を取得
    answer_records = AnswerRecord.query.filter_by(
        student_id=current_user.id
    ).order_by(AnswerRecord.timestamp.desc()).all()
    
    # カテゴリ別の正解率を計算
    category_stats = {}
    for record in answer_records:
        category_id = record.problem.category_id
        
        if category_id not in category_stats:
            category_stats[category_id] = {
                'category': record.problem.category,
                'total': 0,
                'correct': 0,
                'incorrect': 0
            }
        
        category_stats[category_id]['total'] += 1
        if record.is_correct:
            category_stats[category_id]['correct'] += 1
        else:
            category_stats[category_id]['incorrect'] += 1
    
    # 正解率を計算
    for stats in category_stats.values():
        stats['accuracy'] = (stats['correct'] / stats['total']) * 100 if stats['total'] > 0 else 0
    
    return render_template(
        'basebuilder/history.html',
        answer_records=answer_records,
        category_stats=category_stats
    )

# 教師向け分析ページ
@basebuilder.route('/basebuilder/analysis')
@login_required
def analysis():
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder.index'))
    
    # 教師が担当するクラスを取得
    classes = current_user.classes_teaching
    
    # クエリパラメータからクラスIDを取得
    class_id = request.args.get('class_id', type=int)
    selected_class = None
    class_students = []
    
    if class_id and classes:
        # 選択されたクラスを取得
        for class_obj in classes:
            if class_obj.id == class_id:
                selected_class = class_obj
                break
        
        if selected_class:
            # クラスの学生を取得
            class_students = selected_class.students.all()
    
    return render_template(
        'basebuilder/analysis.html',
        classes=classes,
        selected_class=selected_class,
        class_students=class_students
    )

# 生徒別の詳細分析
@basebuilder.route('/basebuilder/analysis/student/<int:student_id>')
@login_required
def student_analysis(student_id):
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder.index'))
    
    # 学生を取得
    student = User.query.get_or_404(student_id)
    
    # 学生がクラスに所属しているか確認
    student_in_class = False
    for class_obj in current_user.classes_teaching:
        if student in class_obj.students:
            student_in_class = True
            break
    
    if not student_in_class:
        flash('この学生の情報を閲覧する権限がありません。')
        return redirect(url_for('basebuilder.analysis'))
    
    # 学生の熟練度記録を取得
    proficiency_records = ProficiencyRecord.query.filter_by(
        student_id=student_id
    ).all()
    
    # 学生の解答履歴を取得
    answer_records = AnswerRecord.query.filter_by(
        student_id=student_id
    ).order_by(AnswerRecord.timestamp.desc()).limit(20).all()
    
    # カテゴリ別の正解率を計算
    category_stats = {}
    for record in answer_records:
        category_id = record.problem.category_id
        
        if category_id not in category_stats:
            category_stats[category_id] = {
                'category': record.problem.category,
                'total': 0,
                'correct': 0
            }
        
        category_stats[category_id]['total'] += 1
        if record.is_correct:
            category_stats[category_id]['correct'] += 1
    
    # 正解率を計算
    for stats in category_stats.values():
        stats['accuracy'] = (stats['correct'] / stats['total']) * 100 if stats['total'] > 0 else 0
    
    return render_template(
        'basebuilder/student_analysis.html',
        student=student,
        proficiency_records=proficiency_records,
        answer_records=answer_records,
        category_stats=category_stats
    )

# テーマと問題の関連付けを管理
@basebuilder.route('/basebuilder/theme_relations')
@login_required
def theme_relations():
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder.index'))
    
    # すべてのテーマを取得
    themes = InquiryTheme.query.all()
    
    # すべての問題を取得
    problems = BasicKnowledgeItem.query.filter_by(is_active=True).all()
    
    # 既存の関連付けを取得
    existing_relations = KnowledgeThemeRelation.query.all()
    
    # テーマ別の関連問題を整理
    theme_problems = {}
    for relation in existing_relations:
        if relation.theme_id not in theme_problems:
            theme_problems[relation.theme_id] = []
        theme_problems[relation.theme_id].append({
            'problem': relation.problem,
            'relevance': relation.relevance
        })
    
    return render_template(
        'basebuilder/theme_relations.html',
        themes=themes,
        problems=problems,
        theme_problems=theme_problems
    )

@basebuilder.route('/basebuilder/theme_relation/create', methods=['POST'])
@login_required
def create_theme_relation():
    if current_user.role != 'teacher':
        return jsonify({'error': 'この機能は教師のみ利用可能です。'}), 403
    
    theme_id = request.form.get('theme_id', type=int)
    problem_id = request.form.get('problem_id', type=int)
    relevance = request.form.get('relevance', type=int, default=3)
    
    if not theme_id or not problem_id:
        return jsonify({'error': 'テーマと問題は必須です。'}), 400
    
    # 既に関連付けが存在するか確認
    existing = KnowledgeThemeRelation.query.filter_by(
        theme_id=theme_id,
        problem_id=problem_id
    ).first()
    
    if existing:
        # 関連性のみ更新
        existing.relevance = relevance
        db.session.commit()
        return jsonify({'success': True, 'message': '関連性が更新されました。'})
    
    # 新しい関連付けを作成
    new_relation = KnowledgeThemeRelation(
        theme_id=theme_id,
        problem_id=problem_id,
        relevance=relevance,
        created_by=current_user.id
    )
    
    db.session.add(new_relation)
    db.session.commit()
    
    return jsonify({'success': True, 'message': '関連付けが作成されました。'})

@basebuilder.route('/basebuilder/theme_relation/delete', methods=['POST'])
@login_required
def delete_theme_relation():
    if current_user.role != 'teacher':
        return jsonify({'error': 'この機能は教師のみ利用可能です。'}), 403
    
    theme_id = request.form.get('theme_id', type=int)
    problem_id = request.form.get('problem_id', type=int)
    
    if not theme_id or not problem_id:
        return jsonify({'error': 'テーマと問題は必須です。'}), 400
    
    # 関連付けを取得
    relation = KnowledgeThemeRelation.query.filter_by(
        theme_id=theme_id,
        problem_id=problem_id
    ).first_or_404()
    
    # 関連付けを削除
    db.session.delete(relation)
    db.session.commit()
    
    return jsonify({'success': True, 'message': '関連付けが削除されました。'})

# 問題を削除
@basebuilder.route('/basebuilder/problem/<int:problem_id>/delete', methods=['POST'])
@login_required
def delete_problem(problem_id):
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder.index'))
    
    # 問題を取得
    problem = BasicKnowledgeItem.query.get_or_404(problem_id)
    
    # 作成者本人か確認
    if problem.created_by != current_user.id:
        flash('この問題を削除する権限がありません。')
        return redirect(url_for('basebuilder.problems'))
    
    # 問題に関連する解答記録を削除（外部キー制約がある場合）
    AnswerRecord.query.filter_by(problem_id=problem_id).delete()
    
    # 問題に関連する関連付けを削除
    KnowledgeThemeRelation.query.filter_by(problem_id=problem_id).delete()
    
    # 問題を削除
    db.session.delete(problem)
    db.session.commit()
    
    flash('問題が削除されました。')
    return redirect(url_for('basebuilder.problems'))

# 学習パスの管理
@basebuilder.route('/basebuilder/learning_paths')
@login_required
def learning_paths():
    if current_user.role == 'student':
        # 学生向け - 割り当てられた学習パスを表示
        assigned_paths = PathAssignment.query.filter_by(
            student_id=current_user.id
        ).all()
        
        return render_template(
            'basebuilder/student_learning_paths.html',
            assigned_paths=assigned_paths
        )
    
    elif current_user.role == 'teacher':
        # 教師向け - 作成した学習パスを表示
        paths = LearningPath.query.filter_by(
            created_by=current_user.id
        ).all()
        
        return render_template(
            'basebuilder/teacher_learning_paths.html',
            paths=paths
        )
    
    # その他のロールの場合
    return redirect(url_for('basebuilder.index'))

@basebuilder.route('/basebuilder/learning_path/create', methods=['GET', 'POST'])
@login_required
def create_learning_path():
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder.index'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description', '')
        steps = request.form.get('steps', '[]')
        
        if not title:
            flash('タイトルは必須です。')
            return render_template('basebuilder/create_learning_path.html')
        
        # ステップがJSONとして有効かチェック
        try:
            steps_json = json.loads(steps)
        except json.JSONDecodeError:
            flash('ステップが正しいJSON形式ではありません。')
            return render_template('basebuilder/create_learning_path.html')
        
        # 新しい学習パスを作成
        new_path = LearningPath(
            title=title,
            description=description,
            steps=steps,
            created_by=current_user.id
        )
        
        db.session.add(new_path)
        db.session.commit()
        
        flash('学習パスが作成されました。')
        return redirect(url_for('basebuilder.learning_paths'))
    
    # 問題カテゴリを取得（ステップ作成用）
    categories = ProblemCategory.query.all()
    
    return render_template(
        'basebuilder/create_learning_path.html',
        categories=categories
    )

@basebuilder.route('/basebuilder/learning_path/<int:path_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_learning_path(path_id):
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder.index'))
    
    # 学習パスを取得
    path = LearningPath.query.get_or_404(path_id)
    
    # 作成者本人か確認
    if path.created_by != current_user.id:
        flash('この学習パスを編集する権限がありません。')
        return redirect(url_for('basebuilder.learning_paths'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description', '')
        steps = request.form.get('steps', '[]')
        is_active = 'is_active' in request.form
        
        if not title:
            flash('タイトルは必須です。')
            return render_template('basebuilder/edit_learning_path.html', path=path)
        
        # ステップがJSONとして有効かチェック
        try:
            steps_json = json.loads(steps)
        except json.JSONDecodeError:
            flash('ステップが正しいJSON形式ではありません。')
            return render_template('basebuilder/edit_learning_path.html', path=path)
        
        # 学習パスを更新
        path.title = title
        path.description = description
        path.steps = steps
        path.is_active = is_active
        
        db.session.commit()
        
        flash('学習パスが更新されました。')
        return redirect(url_for('basebuilder.learning_paths'))
    
    # 問題カテゴリを取得（ステップ作成用）
    categories = ProblemCategory.query.all()
    
    return render_template(
        'basebuilder/edit_learning_path.html',
        path=path,
        categories=categories
    )

@basebuilder.route('/basebuilder/learning_path/<int:path_id>/assign', methods=['GET', 'POST'])
@login_required
def assign_learning_path(path_id):
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder.index'))
    
    # 学習パスを取得
    path = LearningPath.query.get_or_404(path_id)
    
    # 教師のクラスを取得
    classes = current_user.classes_teaching
    
    if request.method == 'POST':
        class_id = request.form.get('class_id', type=int)
        student_ids = request.form.getlist('student_ids')
        due_date_str = request.form.get('due_date', '')
        
        if not class_id or not student_ids:
            flash('クラスと学生は必須です。')
            return render_template(
                'basebuilder/assign_learning_path.html',
                path=path,
                classes=classes
            )
        
        # 日付文字列をdateオブジェクトに変換
        due_date = None
        if due_date_str:
            from datetime import datetime
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        
        # 選択した学生に学習パスを割り当て
        for student_id_str in student_ids:
            try:
                student_id = int(student_id_str)
                
                # 既に割り当てられているか確認
                existing = PathAssignment.query.filter_by(
                    path_id=path_id,
                    student_id=student_id
                ).first()
                
                if existing:
                    # 既存の割り当てを更新
                    existing.due_date = due_date
                    existing.assigned_by = current_user.id
                    existing.assigned_at = datetime.utcnow()
                else:
                    # 新しい割り当てを作成
                    assignment = PathAssignment(
                        path_id=path_id,
                        student_id=student_id,
                        assigned_by=current_user.id,
                        due_date=due_date
                    )
                    db.session.add(assignment)
            
            except ValueError:
                continue
        
        db.session.commit()
        
        flash('学習パスが割り当てられました。')
        return redirect(url_for('basebuilder.learning_paths'))
    
    return render_template(
        'basebuilder/assign_learning_path.html',
        path=path,
        classes=classes
    )

# 学習パスを開始・進行する
@basebuilder.route('/basebuilder/learning_path/<int:assignment_id>/start')
@login_required
def start_learning_path(assignment_id):
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('basebuilder.index'))
    
    # 割り当てを取得
    assignment = PathAssignment.query.get_or_404(assignment_id)
    
    # 自分の割り当てか確認
    if assignment.student_id != current_user.id:
        flash('この学習パスを開始する権限がありません。')
        return redirect(url_for('basebuilder.learning_paths'))
    
    # 学習パスを取得
    path = assignment.path
    
    # 進行状況を計算
    progress = assignment.progress
    
    # 学習パスのステップを取得
    steps = json.loads(path.steps)
    
    # 現在のステップを決定
    current_step_index = int(len(steps) * (progress / 100)) if steps else 0
    current_step = steps[current_step_index] if current_step_index < len(steps) else None
    
    return render_template(
        'basebuilder/start_learning_path.html',
        assignment=assignment,
        path=path,
        steps=steps,
        current_step_index=current_step_index,
        current_step=current_step,
        progress=progress
    )

@basebuilder.route('/basebuilder/learning_path/<int:assignment_id>/update_progress', methods=['POST'])
@login_required
def update_path_progress(assignment_id):
    if current_user.role != 'student':
        return jsonify({'error': 'この機能は学生のみ利用可能です。'}), 403
    
    # 割り当てを取得
    assignment = PathAssignment.query.get_or_404(assignment_id)
    
    # 自分の割り当てか確認
    if assignment.student_id != current_user.id:
        return jsonify({'error': 'この学習パスの進捗を更新する権限がありません。'}), 403
    
    # 進捗を更新
    progress = request.form.get('progress', type=int, default=0)
    completed = request.form.get('completed', type=bool, default=False)
    
    # 値の範囲を確認
    progress = max(0, min(100, progress))
    
    # 進捗を更新
    assignment.progress = progress
    assignment.completed = completed or (progress == 100)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'progress': progress,
        'completed': assignment.completed
    })