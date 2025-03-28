from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response, session
from flask_login import login_required, current_user
import json
import random
from datetime import datetime, timedelta
from app import db, User, InquiryTheme
from basebuilder import exporters
from sqlalchemy import func

from basebuilder.models import (
    ProblemCategory, BasicKnowledgeItem, KnowledgeThemeRelation,
    AnswerRecord, ProficiencyRecord, LearningPath, PathAssignment,
    TextSet, TextDelivery, TextProficiencyRecord, WordProficiency  # 追加
)

# Blueprint名をbasebuilderに変更
basebuilder_module = Blueprint('basebuilder_module', __name__, url_prefix='/basebuilder')

# BaseBuilder ホームページ
# basebuilder/routes.py の index 関数（学生向け部分）を修正
@basebuilder_module.route('/')
@login_required
def index():
    if current_user.role == 'student':
        # 学生向けダッシュボード
        
        # 今日の日付
        today = datetime.now().date()
        
        # 学生の熟練度記録を取得
        proficiency_records = ProficiencyRecord.query.filter_by(
            student_id=current_user.id
        ).all()
        
        # 今日学習すべき単語数を取得
        today_words = ProficiencyRecord.query.filter(
            ProficiencyRecord.student_id == current_user.id,
            ProficiencyRecord.review_date <= today
        ).count()
        
        # 熟練度レベル別の単語数をカウント
        proficiency_counts = {
            'mastered': 0,  # レベル5
            'learning': 0,  # レベル1-4
            'new': 0        # レベル0
        }
        
        for record in proficiency_records:
            if record.level == 5:
                proficiency_counts['mastered'] += 1
            elif record.level > 0:
                proficiency_counts['learning'] += 1
            else:
                proficiency_counts['new'] += 1
        
        # カテゴリごとの熟練度を整理
        category_proficiency = {}
        for record in proficiency_records:
            category_proficiency[record.category.name] = record.level
        
        # 学生の最近の解答履歴を取得（最新10件）
        recent_answers = AnswerRecord.query.filter_by(
            student_id=current_user.id
        ).order_by(AnswerRecord.timestamp.desc()).limit(10).all()
        
        # 学生の選択した探究テーマを取得
        theme = InquiryTheme.query.filter_by(
            student_id=current_user.id, 
            is_selected=True
        ).first()
        
        # テーマに関連する問題を取得
        related_problems = []
        if theme:
            theme_relations = KnowledgeThemeRelation.query.filter_by(
                theme_id=theme.id
            ).all()
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
        
        # 学生に配信されたテキストを取得
        enrolled_class_ids = [c.id for c in current_user.enrolled_classes]
        delivered_texts = TextDelivery.query.filter(
            TextDelivery.class_id.in_(enrolled_class_ids)
        ).order_by(TextDelivery.delivered_at.desc()).limit(5).all()

        # テキストごとの進捗状況を計算
        text_progress = {}
        for delivery in delivered_texts:
            # テキストの問題総数
            problems = BasicKnowledgeItem.query.filter_by(
                text_set_id=delivery.text_set_id
            ).all()
            
            total_problems = len(problems)
            
            # 解答済みの問題数
            answered_count = 0
            for problem in problems:
                answer = AnswerRecord.query.filter_by(
                    student_id=current_user.id,
                    problem_id=problem.id
                ).first()
                
                if answer:
                    answered_count += 1
            
            # 進捗率を計算
            if total_problems > 0:
                progress_percent = int((answered_count / total_problems) * 100)
            else:
                progress_percent = 0
            
            text_progress[delivery.text_set_id] = {
                'answered': answered_count,
                'total': total_problems,
                'percent': progress_percent
            }
        
        return render_template(
            'basebuilder/student_dashboard.html',
            category_proficiency=category_proficiency,
            recent_answers=recent_answers,
            related_problems=related_problems,
            assigned_paths=assigned_paths,
            theme=theme,
            today_words=today_words,
            proficiency_counts=proficiency_counts,
            today=today,
            delivered_texts=delivered_texts,
            text_progress=text_progress
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
        classes = getattr(current_user, 'classes_teaching', [])
        
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
@basebuilder_module.route('/categories')
@login_required
def categories():
    # トップレベルのカテゴリを取得
    top_categories = ProblemCategory.query.filter_by(parent_id=None).all()
    
    return render_template(
        'basebuilder/categories.html',
        top_categories=top_categories
    )

# カテゴリの作成と編集
@basebuilder_module.route('/category/create', methods=['GET', 'POST'])
@login_required
def create_category():
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
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
        return redirect(url_for('basebuilder_module.categories'))
    
    return render_template(
        'basebuilder/create_category.html',
        parent_categories=parent_categories
    )

@basebuilder_module.route('/category/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
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
        return redirect(url_for('basebuilder_module.categories'))
    
    return render_template(
        'basebuilder/edit_category.html',
        category=category,
        parent_categories=parent_categories
    )

@basebuilder_module.route('/category/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # カテゴリを取得
    category = ProblemCategory.query.get_or_404(category_id)
    
    try:
        # このカテゴリに関連する問題を取得
        problems = BasicKnowledgeItem.query.filter_by(category_id=category_id).all()
        
        # 各問題に関連する解答記録・関連付けを削除
        for problem in problems:
            # 解答記録の削除
            AnswerRecord.query.filter_by(problem_id=problem.id).delete()
            
            # テーマとの関連付けを削除
            KnowledgeThemeRelation.query.filter_by(problem_id=problem.id).delete()
            
            # 問題を削除
            db.session.delete(problem)
        
        # カテゴリの熟練度記録を削除
        ProficiencyRecord.query.filter_by(category_id=category_id).delete()
        
        # カテゴリを削除
        db.session.delete(category)
        db.session.commit()
        
        flash(f'カテゴリ"{category.name}"とそれに含まれる全ての問題が削除されました。')
    except Exception as e:
        db.session.rollback()
        flash(f'カテゴリの削除中にエラーが発生しました: {str(e)}')
    
    return redirect(url_for('basebuilder_module.categories'))

# 問題一覧
@basebuilder_module.route('/problems')
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
@basebuilder_module.route('/problem/create', methods=['GET', 'POST'])
@login_required
def create_problem():
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
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
        return redirect(url_for('basebuilder_module.problems'))
    
    return render_template(
        'basebuilder/create_problem.html',
        categories=categories
    )

@basebuilder_module.route('/problem/<int:problem_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_problem(problem_id):
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
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
        return redirect(url_for('basebuilder_module.problems'))
    
    return render_template(
        'basebuilder/edit_problem.html',
        problem=problem,
        categories=categories
    )

# 問題を解く
@basebuilder_module.route('/problem/<int:problem_id>/solve', methods=['GET'])
@login_required
def solve_problem(problem_id):
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # 問題を取得
    problem = BasicKnowledgeItem.query.get_or_404(problem_id)
    
    # 学生の熟練度レコードを取得
    proficiency_record = ProficiencyRecord.query.filter_by(
        student_id=current_user.id,
        category_id=problem.category_id
    ).first()
    
    # 熟練度レコードがなければ作成
    if not proficiency_record:
        proficiency_record = ProficiencyRecord(
            student_id=current_user.id,
            category_id=problem.category_id,
            level=0,
            review_date=datetime.now().date()
        )
        db.session.add(proficiency_record)
        db.session.commit()
    
    # 熟練度に応じて問題形式を決定（0-2: 選択式、3-5: 入力式）
    is_choice_mode = proficiency_record.level < 3
    
    # 選択式の場合はダミー選択肢を用意
    dummy_choices = []
    all_choices = []
    correct_index = 0
    
    if is_choice_mode:
        # 同じカテゴリから3つのダミー選択肢を取得
        dummy_words = BasicKnowledgeItem.query.filter(
            BasicKnowledgeItem.category_id == problem.category_id,
            BasicKnowledgeItem.id != problem_id,
            BasicKnowledgeItem.is_active == True
        ).order_by(func.random()).limit(3).all()
        
        dummy_choices = [word.title for word in dummy_words]
        
        # ダミー選択肢が足りない場合は他のカテゴリから取得
        if len(dummy_choices) < 3:
            other_words = BasicKnowledgeItem.query.filter(
                BasicKnowledgeItem.category_id != problem.category_id,
                BasicKnowledgeItem.id != problem_id,
                BasicKnowledgeItem.is_active == True
            ).order_by(func.random()).limit(3 - len(dummy_choices)).all()
            
            dummy_choices.extend([word.title for word in other_words])
        
        # それでも足りない場合は固定の選択肢を追加
        while len(dummy_choices) < 3:
            dummy_choices.append(f"選択肢{len(dummy_choices)+1}")
        
        # 選択肢をランダムに並べ替え
        all_choices = [problem.title] + dummy_choices
        random.shuffle(all_choices)
        
        # 正解が配列の何番目にあるかを確認
        correct_index = all_choices.index(problem.title)
        
        # ダミー選択肢を更新（正解を除外）
        dummy_choices = [choice for choice in all_choices if choice != problem.title]
    
    # セッション関連の確認
    in_session = False
    learning_session = None
    if 'learning_session' in session:
        learning_session = session['learning_session']
        in_session = (learning_session.get('current_problem_id') == problem_id)
    
    return render_template(
        'basebuilder/solve_problem.html',
        problem=problem,
        proficiency_record=proficiency_record,
        dummy_choices=dummy_choices,
        all_choices=all_choices if is_choice_mode else None,
        correct_index=correct_index if is_choice_mode else None,
        is_choice_mode=is_choice_mode,
        in_session=in_session,
        learning_session=learning_session  # 追加: learning_session 変数をテンプレートに渡す
    )
# basebuilder/routes.py に追加する関数
@basebuilder_module.route('/category/<int:category_id>/texts')
@login_required
def category_texts(category_id):
    """カテゴリ内の問題をテキストに分割して表示する"""
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # カテゴリを取得
    category = ProblemCategory.query.get_or_404(category_id)
    
    # カテゴリ内の問題を取得
    problems = BasicKnowledgeItem.query.filter_by(
        category_id=category_id,
        is_active=True
    ).all()
    
    # 既存のテキストセットを取得
    text_sets = TextSet.query.filter_by(category_id=category_id).all()
    
    # 各テキストセットの問題数をカウント
    text_problem_counts = {}
    for text_set in text_sets:
        count = BasicKnowledgeItem.query.filter_by(text_set_id=text_set.id).count()
        text_problem_counts[text_set.id] = count
    
    return render_template(
        'basebuilder/category_texts.html',
        category=category,
        text_sets=text_sets,
        text_problem_counts=text_problem_counts,
        total_problems=len(problems)
    )

@basebuilder_module.route('/text_sets/delete', methods=['POST'])
@login_required
def delete_text_sets():
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    text_ids = request.form.getlist('text_ids')
    
    if not text_ids:
        flash('削除するテキストが選択されていません。')
        return redirect(url_for('basebuilder_module.text_sets'))
    
    deleted_count = 0
    
    for text_id in text_ids:
        try:
            text_id = int(text_id)
            text_set = TextSet.query.get(text_id)
            
            # 作成者本人のみ削除可能
            if text_set and text_set.created_by == current_user.id:
                # テキストに含まれる問題を取得
                problems = BasicKnowledgeItem.query.filter_by(text_set_id=text_id).all()
                
                # 各問題に関連する解答記録・関連付けを削除
                for problem in problems:
                    # 解答記録の削除
                    AnswerRecord.query.filter_by(problem_id=problem.id).delete()
                    
                    # 熟練度記録の削除
                    WordProficiency.query.filter_by(problem_id=problem.id).delete()
                    
                    # テーマとの関連付けを削除
                    KnowledgeThemeRelation.query.filter_by(problem_id=problem.id).delete()
                    
                    # 問題を削除
                    db.session.delete(problem)
                
                # テキストの熟練度記録を削除
                TextProficiencyRecord.query.filter_by(text_set_id=text_id).delete()
                
                # テキスト配信を削除
                TextDelivery.query.filter_by(text_set_id=text_id).delete()
                
                # テキストを削除
                db.session.delete(text_set)
                deleted_count += 1
        
        except Exception as e:
            db.session.rollback()
            flash(f'テキストID {text_id} の削除中にエラーが発生しました: {str(e)}')
            return redirect(url_for('basebuilder_module.text_sets'))
    
    try:
        db.session.commit()
        flash(f'選択した {deleted_count} 件のテキストが削除されました。')
    except Exception as e:
        db.session.rollback()
        flash(f'テキストの削除中にエラーが発生しました: {str(e)}')
    
    return redirect(url_for('basebuilder_module.text_sets'))

@basebuilder_module.route('/problem/<int:problem_id>/submit', methods=['POST'])
@login_required
def submit_answer(problem_id):
    if current_user.role != 'student':
        # AJAX/通常フォーム送信を区別
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'この機能は学生のみ利用可能です。'}), 403
        else:
            flash('この機能は学生のみ利用可能です。')
            return redirect(url_for('basebuilder_module.index'))
    
    # 問題を取得
    problem = BasicKnowledgeItem.query.get_or_404(problem_id)
    
    # フォームデータから回答を取得
    answer = request.form.get('answer')
    answer_time = request.form.get('answer_time', type=int, default=0)
    
    # 解答必須
    if not answer:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': '解答が入力されていません。'}), 400
        else:
            flash('解答を入力してください。')
            return redirect(url_for('basebuilder_module.solve_problem', problem_id=problem_id))
    
    # 解答が正しいかチェック
    is_correct = False
    
    # 問題タイプに応じた正解チェック
    if problem.answer_type == 'multiple_choice':
        # 選択肢問題の場合、まず直接問題のタイトルと比較
        if answer.strip().lower() == problem.title.strip().lower():
            is_correct = True
        # 次にcorrect_answerと比較
        elif answer.strip().lower() == problem.correct_answer.strip().lower():
            is_correct = True
        # 最後に選択肢データがあれば確認
        elif problem.choices:
            try:
                choices = json.loads(problem.choices)
                for choice in choices:
                    if choice.get('isCorrect') and answer == choice.get('value'):
                        is_correct = True
                        break
            except:
                pass
    elif problem.answer_type == 'true_false':
        # 真偽問題の場合
        is_correct = (answer.strip().lower() == problem.correct_answer.strip().lower())
    else:
        # テキスト入力問題の場合
        student_answer = answer.strip().lower()
        correct_answer = problem.correct_answer.strip().lower()
        
        # 複数の正解パターンがあればカンマで区切られていることを想定
        correct_answers = [ans.strip().lower() for ans in correct_answer.split(',')]
        is_correct = (student_answer in correct_answers or student_answer == problem.title.strip().lower())
    
    # 解答レコードを作成
    answer_record = AnswerRecord(
        student_id=current_user.id,
        problem_id=problem_id,
        student_answer=answer,
        is_correct=is_correct,
        answer_time=answer_time
    )
    
    db.session.add(answer_record)
    db.session.commit()  # 忘れずにコミット
    
    # 単語の熟練度を更新
    word_proficiency = update_word_proficiency(current_user.id, problem_id, is_correct)
    
    # カテゴリの熟練度も更新 - カテゴリの熟練度は単語の熟練度から計算
    category_proficiency = update_category_proficiency(current_user.id, problem.category_id)
    
    # セッション情報を更新
    next_url = None
    if 'learning_session' in session:
        learning_session = session['learning_session']
        
        # 現在の問題がセッションの問題と一致する場合
        if learning_session.get('current_problem_id') == problem_id:
            # 解答回数をカウントアップ
            learning_session['current_attempt'] += 1
            
            # 完了した問題リストに追加（まだなければ）
            if problem_id not in learning_session.get('completed_problems', []):
                if 'completed_problems' not in learning_session:
                    learning_session['completed_problems'] = []
                learning_session['completed_problems'].append(problem_id)
            
            session['learning_session'] = learning_session
            
            # 次の問題へのURLを設定
            next_url = url_for('basebuilder_module.next_problem')
    
    # AJAXリクエストとフォーム送信を区別して応答
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # AJAXリクエストの場合はJSONを返す
        return jsonify({
            'is_correct': is_correct,
            'correct_answer': problem.title,  # 問題のタイトルを正解として返す
            'explanation': problem.explanation,
            'next_url': next_url,
            'proficiency_level': proficiency.level if proficiency else 0
        })
    else:
        # 通常のフォーム送信の場合はリダイレクト
        if is_correct:
            flash('正解です！ 定着度が上がりました。')
        else:
            flash(f'不正解です。正解は: {problem.title}')
        
        # セッション中なら次の問題へ、そうでなければ問題一覧へ
        if next_url:
            return redirect(next_url)
        else:
            return redirect(url_for('basebuilder_module.problems'))

@basebuilder_module.route('/start_session')
@login_required
def start_session():
    """新しい学習セッションを開始する"""
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # 今日復習すべき問題を取得
    today = datetime.now().date()
    word_proficiencies = WordProficiency.query.filter(
        WordProficiency.student_id == current_user.id,
        WordProficiency.review_date <= today
    ).all()
    
    # 復習すべき問題のIDを取得
    problem_ids = [wp.problem_id for wp in word_proficiencies]
    
    # 問題がなければ、熟練度が低い問題から取得
    if not problem_ids:
        # 熟練度が最大でない問題を取得
        low_proficiency_problems = WordProficiency.query.filter(
            WordProficiency.student_id == current_user.id,
            WordProficiency.level < 5
        ).order_by(WordProficiency.level).limit(20).all()
        
        problem_ids = [wp.problem_id for wp in low_proficiency_problems]
    
    # まだ問題がなければ、全問題から取得
    if not problem_ids:
        problem_ids_query = db.session.query(BasicKnowledgeItem.id).filter(
            BasicKnowledgeItem.is_active == True
        ).all()
        problem_ids = [id[0] for id in problem_ids_query]
    
    # セッション情報を初期化
    session['learning_session'] = {
        'problem_ids': problem_ids,  # 問題IDのリスト
        'total_problems': len(problem_ids),  # 全問題数
        'max_attempts': 15,    # 最大解答回数
        'current_attempt': 0,  # 現在の解答回数
        'completed_problems': [],  # 完了した問題ID
        'current_problem_id': None,  # 現在の問題ID
        'session_start': datetime.now().isoformat()  # セッション開始時間
    }
    
    # 最初の問題を選択
    return redirect(url_for('basebuilder_module.next_problem'))

# ここに追加 - カテゴリごとのセッション開始
@basebuilder_module.route('/category/<int:category_id>/start_session')
@login_required
def start_category_session(category_id):
    """カテゴリ内の問題でセッションを開始する"""
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # カテゴリを取得
    category = ProblemCategory.query.get_or_404(category_id)
    
    # カテゴリ内の問題のIDを取得
    problem_ids = db.session.query(BasicKnowledgeItem.id).filter_by(
        category_id=category_id,
        is_active=True
    ).all()
    problem_ids = [id[0] for id in problem_ids]
    
    if not problem_ids:
        flash('このカテゴリには学習できる問題がありません。')
        return redirect(url_for('basebuilder_module.category_texts', category_id=category_id))
    
    # セッション情報を初期化
    session['learning_session'] = {
        'category_id': category_id,
        'problem_ids': problem_ids,  # すべての問題IDをリストで保持
        'total_problems': min(10, len(problem_ids)),  # 最大10問
        'max_attempts': 15,         # 最大解答回数
        'current_attempt': 0,       # 現在の解答回数
        'completed_problems': [],   # 完了した問題ID
        'current_problem_id': None, # 現在の問題ID
        'session_start': datetime.now().isoformat()  # セッション開始時間
    }
    
    # 最初の問題を選択
    return redirect(url_for('basebuilder_module.next_problem'))

@basebuilder_module.route('/text/<int:text_id>/start_session')
@login_required
def start_text_session(text_id):
    """テキスト内の問題でセッションを開始する"""
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # テキストを取得
    text_set = TextSet.query.get_or_404(text_id)
    
    # テキスト内の問題のIDを取得
    problem_ids = db.session.query(BasicKnowledgeItem.id).filter_by(
        text_set_id=text_id,
        is_active=True
    ).all()
    problem_ids = [id[0] for id in problem_ids]
    
    if not problem_ids:
        flash('このテキストには学習できる問題がありません。')
        return redirect(url_for('basebuilder_module.category_texts', category_id=text_set.category_id))
    
    # セッション情報を初期化
    session['learning_session'] = {
        'text_id': text_id,
        'category_id': text_set.category_id,
        'problem_ids': problem_ids,  # すべての問題IDをリストで保持
        'total_problems': min(10, len(problem_ids)),  # 最大10問
        'max_attempts': 15,         # 最大解答回数
        'current_attempt': 0,       # 現在の解答回数
        'completed_problems': [],   # 完了した問題ID
        'current_problem_id': None, # 現在の問題ID
        'session_start': datetime.now().isoformat()  # セッション開始時間
    }
    
    # 最初の問題を選択
    return redirect(url_for('basebuilder_module.next_problem'))

@basebuilder_module.route('/next_problem')
@login_required
def next_problem():
    """学習セッション内で次の問題を選択して表示する"""
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # セッションがない場合は新しいセッションを開始
    if 'learning_session' not in session:
        return redirect(url_for('basebuilder_module.start_session'))
    
    learning_session = session['learning_session']
    
    # 最大解答回数に達したかチェック
    if learning_session['current_attempt'] >= learning_session['max_attempts']:
        flash('学習セッションが終了しました。お疲れ様でした！')
        return redirect(url_for('basebuilder_module.session_summary'))
    
    # すべての単語の熟練度がMAXになったかチェック
    problem_ids = learning_session.get('problem_ids', [])
    if problem_ids:
        all_mastered = True
        for pid in problem_ids:
            prof = WordProficiency.query.filter_by(
                student_id=current_user.id,
                problem_id=pid
            ).first()
            if not prof or prof.level < 5:
                all_mastered = False
                break
        
        if all_mastered:
            flash('すべての単語の熟練度が最大になりました。お疲れ様でした！')
            return redirect(url_for('basebuilder_module.session_summary'))
        
    # 利用可能な問題ID (problem_idsキーが存在しない場合の対応)
    available_problem_ids = learning_session.get('problem_ids', [])
    
    # 問題IDがない場合は全体から取得
    if not available_problem_ids:
        problem_ids_query = db.session.query(BasicKnowledgeItem.id).filter(
            BasicKnowledgeItem.is_active == True
        ).limit(20).all()
        available_problem_ids = [id[0] for id in problem_ids_query]
        learning_session['problem_ids'] = available_problem_ids
    
    # 問題がまだない場合はエラーメッセージ
    if not available_problem_ids:
        flash('学習可能な問題がありません。問題を追加してください。')
        return redirect(url_for('basebuilder_module.index'))
    
    # 問題が少ない場合、completed_problemsをリセット
    if len(available_problem_ids) <= learning_session['total_problems'] and len(learning_session['completed_problems']) >= len(available_problem_ids):
        learning_session['completed_problems'] = []
    
    # まだ解いていない問題
    unfinished_problems = [pid for pid in available_problem_ids if pid not in learning_session['completed_problems']]
    
    if unfinished_problems:
        # 未解答問題の熟練度を確認して、低い順にソート
        problem_proficiencies = {}
        for pid in unfinished_problems:
            prof = WordProficiency.query.filter_by(
                student_id=current_user.id,
                problem_id=pid
            ).first()
            problem_proficiencies[pid] = prof.level if prof else 0
        
                # 熟練度が低い問題を優先（20%の確率でランダム選択）
        if random.random() < 0.8:  # 80%の確率で熟練度ベースの選択
            sorted_problems = sorted(problem_proficiencies.items(), key=lambda x: x[1])
            problem_id = sorted_problems[0][0]  # 最も熟練度が低い問題を選択
        else:
            # ランダム選択（完全にランダムに選ぶことで多様性を確保）
            problem_id = random.choice(unfinished_problems)
    else:
        # すべての問題が終わった場合は、熟練度が低い順に再度出題
        proficiencies = {}
        for pid in available_problem_ids:
            prof = WordProficiency.query.filter_by(
                student_id=current_user.id,
                problem_id=pid
            ).first()
            proficiencies[pid] = prof.level if prof else 0
        
        # 熟練度が最大（5）でない問題のみ選択
        incomplete_problems = [pid for pid, level in proficiencies.items() if level < 5]
        
        if incomplete_problems:
            # 熟練度が低い問題を優先
            sorted_problems = sorted([(pid, proficiencies[pid]) for pid in incomplete_problems], 
                                     key=lambda x: x[1])
            problem_id = sorted_problems[0][0]
        else:
            # すべての問題が最大熟練度に達したか、または問題がない場合はランダムに選択
            problem_id = random.choice(available_problem_ids)
    
    # 選択した問題をセッションに記録
    learning_session['current_problem_id'] = problem_id
    session['learning_session'] = learning_session
    
    # 問題解答ページにリダイレクト
    return redirect(url_for('basebuilder_module.solve_problem', problem_id=problem_id))

@basebuilder_module.route('/session_summary')
@login_required
def session_summary():
    """学習セッションのサマリーを表示"""
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # セッション情報がない場合
    if 'learning_session' not in session:
        flash('学習セッションのデータがありません。')
        return redirect(url_for('basebuilder_module.index'))
    
    learning_session = session.pop('learning_session')  # セッション情報を取得して削除
    
    # 学習した問題の情報を取得
    completed_problems = BasicKnowledgeItem.query.filter(
        BasicKnowledgeItem.id.in_(learning_session['completed_problems'])
    ).all()
    
    # セッション開始時間を正しく変換
    session_start = datetime.fromisoformat(learning_session['session_start'])
    
    # 解答履歴を取得 - セッション開始時間以降のみを取得
    answer_records = AnswerRecord.query.filter(
        AnswerRecord.student_id == current_user.id,
        AnswerRecord.problem_id.in_(learning_session['completed_problems']),
        AnswerRecord.timestamp >= session_start
    ).order_by(AnswerRecord.timestamp).all()
    
    # 問題IDごとに最新の解答記録を取得
    latest_records = {}
    for record in answer_records:
        latest_records[record.problem_id] = record
    
    # 正解数・不正解数をカウント
    correct_count = sum(1 for record in latest_records.values() if record.is_correct)
    incorrect_count = len(latest_records) - correct_count
    
    # 各カテゴリの熟練度を取得
    proficiency_records = ProficiencyRecord.query.filter_by(
        student_id=current_user.id
    ).all()
    
    return render_template(
        'basebuilder/session_summary.html',
        completed_problems=completed_problems,
        answer_records=latest_records,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        total_attempts=learning_session['current_attempt'],
        max_attempts=learning_session['max_attempts'],
        proficiency_records=proficiency_records
    )

# 熟練度を更新する関数
def update_proficiency(student_id, category_id, is_correct):
   """
   学生の熟練度を更新する関数。
   スペースド・リピティションのための復習日も設定する。
   
   Args:
       student_id: 学生ID
       category_id: カテゴリID
       is_correct: 正解かどうか
       
   Returns:
       更新された熟練度レコード
   """
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
   
   # 現在の日付を取得
   today = datetime.now().date()
   
   # 正解・不正解に応じてポイントを更新
   if is_correct:
       # 正解の場合は+1ポイント（最大5ポイント）
       new_level = min(5, proficiency.level + 1)
   else:
       # 不正解の場合は-1ポイント（最小0ポイント）
       new_level = max(0, proficiency.level - 1)
   
   # ポイントに応じて次回復習日を設定
   if new_level == 0:
       # 0ポイント：今日
       next_review = today
   elif new_level == 1:
       # 1ポイント：1日後
       next_review = today + timedelta(days=1)
   elif new_level == 2:
       # 2ポイント：3日後
       next_review = today + timedelta(days=3)
   elif new_level == 3:
       # 3ポイント：1週間後
       next_review = today + timedelta(days=7)
   elif new_level == 4:
       # 4ポイント：2週間後
       next_review = today + timedelta(days=14)
   else:  # 5ポイント
       # 5ポイント：1ヶ月後
       next_review = today + timedelta(days=30)
   
   # 熟練度と次回復習日を更新
   proficiency.level = new_level
   proficiency.review_date = next_review
   proficiency.last_updated = datetime.utcnow()
   
   # 変更をコミット
   db.session.commit()
   
   return proficiency

def update_word_proficiency(student_id, problem_id, is_correct):
    """
    単語ごとの熟練度を更新する関数
    
    Args:
        student_id: 学生ID
        problem_id: 問題ID
        is_correct: 正解かどうか
        
    Returns:
        更新された熟練度レコード
    """
    # 問題を取得
    problem = BasicKnowledgeItem.query.get(problem_id)
    
    # 既存の熟練度レコードを取得
    proficiency = WordProficiency.query.filter_by(
        student_id=student_id,
        problem_id=problem_id
    ).first()
    
    # 熟練度レコードがなければ作成
    if not proficiency:
        proficiency = WordProficiency(
            student_id=student_id,
            problem_id=problem_id,
            level=0
        )
        db.session.add(proficiency)
    
    # 現在の日付を取得
    today = datetime.now().date()
    
    # 正解・不正解に応じてポイントを更新
    if is_correct:
        # 正解の場合は+1ポイント（最大5ポイント）
        new_level = min(5, proficiency.level + 1)
    else:
        # 不正解の場合は-1ポイント（最小0ポイント）
        new_level = max(0, proficiency.level - 1)
    
    # ポイントに応じて次回復習日を設定（既存ロジックと同様）
    if new_level == 0:
        next_review = today
    elif new_level == 1:
        next_review = today + timedelta(days=1)
    elif new_level == 2:
        next_review = today + timedelta(days=3)
    elif new_level == 3:
        next_review = today + timedelta(days=7)
    elif new_level == 4:
        next_review = today + timedelta(days=14)
    else:  # 5ポイント
        next_review = today + timedelta(days=30)
    
    # 熟練度と次回復習日を更新
    proficiency.level = new_level
    proficiency.review_date = next_review
    proficiency.last_updated = datetime.utcnow()
    
    # 変更をコミット
    db.session.commit()
    
    return proficiency

# basebuilder/routes.py に追加

def update_category_proficiency(student_id, category_id):
    """
    カテゴリの熟練度を単語の熟練度から計算して更新する
    
    Args:
        student_id: 学生ID
        category_id: カテゴリID
        
    Returns:
        更新された熟練度レコード
    """
    # カテゴリに属する問題のIDを取得
    problem_ids = [p.id for p in BasicKnowledgeItem.query.filter_by(category_id=category_id).all()]
    
    if not problem_ids:
        return None
    
    # カテゴリ内の単語の熟練度を取得
    word_proficiencies = WordProficiency.query.filter(
        WordProficiency.student_id == student_id,
        WordProficiency.problem_id.in_(problem_ids)
    ).all()
    
    # 熟練度レコードがない場合、デフォルト値は0
    total_level = sum(wp.level for wp in word_proficiencies) if word_proficiencies else 0
    avg_level = total_level / len(problem_ids)
    
    # カテゴリの熟練度を更新
    proficiency = ProficiencyRecord.query.filter_by(
        student_id=student_id,
        category_id=category_id
    ).first()
    
    if not proficiency:
        proficiency = ProficiencyRecord(
            student_id=student_id,
            category_id=category_id,
            level=0,
            review_date=datetime.now().date()
        )
        db.session.add(proficiency)
    
    # 熟練度は平均値を整数に切り捨て
    proficiency.level = int(avg_level)
    proficiency.last_updated = datetime.utcnow()
    
    # 次回復習日は最も早い単語の復習日
    if word_proficiencies:
        earliest_review = min(wp.review_date for wp in word_proficiencies)
        proficiency.review_date = earliest_review
    
    db.session.commit()
    
    return proficiency

# 熟練度の表示
@basebuilder_module.route('/proficiency')
@login_required
def view_proficiency():
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
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
@basebuilder_module.route('/history')
@login_required
def view_history():
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
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
@basebuilder_module.route('/analysis')
@basebuilder_module.route('/analysis/<int:class_id>')
@login_required
def analysis(class_id=None):
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # 教師が担当するクラスを取得
    classes = getattr(current_user, 'classes_teaching', [])
    
    selected_class = None
    class_students = []
    student_progress = {}
    student_last_activity = {}
    
    if class_id and classes:
        # 選択されたクラスを取得
        for class_obj in classes:
            if class_obj.id == class_id:
                selected_class = class_obj
                break
        
        if selected_class:
            # クラスの学生を取得
            class_students = selected_class.students.all()
            
            # 各学生の進捗率とアクティビティを計算
            for student in class_students:
                # 学生の熟練度記録を取得
                proficiency_records = ProficiencyRecord.query.filter_by(
                    student_id=student.id
                ).all()
                
                # 総合進捗率を計算（カテゴリごとの熟練度の平均）
                if proficiency_records:
                    total_level = sum(record.level for record in proficiency_records)
                    avg_level = total_level / len(proficiency_records)
                    # 5段階を100%に変換
                    progress = (avg_level / 5) * 100
                    student_progress[student.id] = round(progress)
                else:
                    student_progress[student.id] = 0
                
                # 最後の活動日時を取得
                last_answer = AnswerRecord.query.filter_by(
                    student_id=student.id
                ).order_by(AnswerRecord.timestamp.desc()).first()
                
                if last_answer:
                    student_last_activity[student.id] = last_answer.timestamp
    
    return render_template(
        'basebuilder/analysis.html',
        classes=classes,
        selected_class=selected_class,
        class_students=class_students,
        student_progress=student_progress,
        student_last_activity=student_last_activity
    )

# 生徒別の詳細分析
@basebuilder_module.route('/analysis/student/<int:student_id>')
@login_required
def student_analysis(student_id):
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
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
        return redirect(url_for('basebuilder_module.analysis'))
    
    # 学生の熟練度記録を取得
    proficiency_records = ProficiencyRecord.query.filter_by(
        student_id=student_id
    ).all()
    
    # 学生の解答履歴を取得（最新20件）
    answer_records = AnswerRecord.query.filter_by(
        student_id=student_id
    ).order_by(AnswerRecord.timestamp.desc()).limit(20).all()
    
    # 総合熟練度を計算
    avg_proficiency = 0
    if proficiency_records:
        total_level = sum(record.level for record in proficiency_records)
        avg_proficiency = (total_level / len(proficiency_records) / 5) * 100
    
    # 解答数と正解率を計算
    all_answers = AnswerRecord.query.filter_by(student_id=student_id).all()
    answer_count = len(all_answers)
    correct_count = sum(1 for answer in all_answers if answer.is_correct)
    correct_rate = (correct_count / answer_count * 100) if answer_count > 0 else 0
    
    # 最後の活動日時
    last_activity = answer_records[0].timestamp if answer_records else None
    
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
        stats['accuracy'] = (stats['correct'] / stats['total'] * 100) if stats['total'] > 0 else 0
    
    return render_template(
        'basebuilder/student_analysis.html',
        student=student,
        proficiency_records=proficiency_records,
        answer_records=answer_records,
        avg_proficiency=avg_proficiency,
        correct_rate=correct_rate,
        answer_count=answer_count,
        last_activity=last_activity,
        category_stats=category_stats
    )

# テーマと問題の関連付けを管理
@basebuilder_module.route('/theme_relations')
@login_required
def theme_relations():
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
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

@basebuilder_module.route('/theme_relation/create', methods=['POST'])
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

@basebuilder_module.route('/theme_relation/delete', methods=['POST'])
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
@basebuilder_module.route('/problem/<int:problem_id>/delete', methods=['POST'])
@login_required
def delete_problem(problem_id):
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # 問題を取得
    problem = BasicKnowledgeItem.query.get_or_404(problem_id)
    
    # 作成者本人か確認
    if problem.created_by != current_user.id:
        flash('この問題を削除する権限がありません。')
        return redirect(url_for('basebuilder_module.problems'))
    
    # 問題に関連する解答記録を削除（外部キー制約がある場合）
    AnswerRecord.query.filter_by(problem_id=problem_id).delete()
    
    # 問題に関連する関連付けを削除
    KnowledgeThemeRelation.query.filter_by(problem_id=problem_id).delete()
    
    # 問題を削除
    db.session.delete(problem)
    db.session.commit()
    
    flash('問題が削除されました。')
    return redirect(url_for('basebuilder_module.problems'))

# 学習パスの管理
@basebuilder_module.route('/learning_paths')
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
    return redirect(url_for('basebuilder_module.index'))

@basebuilder_module.route('/learning_path/create', methods=['GET', 'POST'])
@login_required
def create_learning_path():
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
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
        return redirect(url_for('basebuilder_module.learning_paths'))
    
    # 問題カテゴリを取得（ステップ作成用）
    categories = ProblemCategory.query.all()
    
    return render_template(
        'basebuilder/create_learning_path.html',
        categories=categories
    )

@basebuilder_module.route('/learning_path/<int:path_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_learning_path(path_id):
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # 学習パスを取得
    path = LearningPath.query.get_or_404(path_id)
    
    # 作成者本人か確認
    if path.created_by != current_user.id:
        flash('この学習パスを編集する権限がありません。')
        return redirect(url_for('basebuilder_module.learning_paths'))
    
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
        return redirect(url_for('basebuilder_module.learning_paths'))
    
    # 問題カテゴリを取得（ステップ作成用）
    categories = ProblemCategory.query.all()
    
    return render_template(
        'basebuilder/edit_learning_path.html',
        path=path,
        categories=categories
    )

@basebuilder_module.route('/learning_path/<int:path_id>/assign', methods=['GET', 'POST'])
@login_required
def assign_learning_path(path_id):
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # 学習パスを取得
    path = LearningPath.query.get_or_404(path_id)
    
    # 教師のクラスを取得
    classes = getattr(current_user, 'classes_teaching', [])
    
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
        return redirect(url_for('basebuilder_module.learning_paths'))
    
    return render_template(
        'basebuilder/assign_learning_path.html',
        path=path,
        classes=classes
    )

# 学習パスを開始・進行する
@basebuilder_module.route('/learning_path/<int:assignment_id>/start')
@login_required
def start_learning_path(assignment_id):
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # 割り当てを取得
    assignment = PathAssignment.query.get_or_404(assignment_id)
    
    # 自分の割り当てか確認
    if assignment.student_id != current_user.id:
        flash('この学習パスを開始する権限がありません。')
        return redirect(url_for('basebuilder_module.learning_paths'))
    
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

@basebuilder_module.route('/learning_path/<int:assignment_id>/update_progress', methods=['POST'])
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

@basebuilder_module.route('/api/category/<int:category_id>/problems')
@login_required
def api_category_problems(category_id):
    """カテゴリの問題を提供するAPIエンドポイント"""
    if current_user.role != 'student':
        return jsonify({'error': '権限がありません'}), 403
    
    # リクエストパラメータ
    count = request.args.get('count', type=int, default=5)
    skip = request.args.get('skip', type=int, default=0)
    
    # 学習パスのセッション情報を確認
    learning_session = session.get('learning_session', {})
    path_id = learning_session.get('path_id')
    
    if path_id:
        # 学習パスの場合、現在のステップを確認
        path = LearningPath.query.get_or_404(path_id)
        
        try:
            steps = json.loads(path.steps)
            current_step_index = learning_session.get('current_step_index', 0)
            
            if current_step_index < len(steps):
                current_step = steps[current_step_index]
                
                # カテゴリステップの場合のみ許可
                if current_step.get('type') == 'category' and str(current_step.get('category_id')) == str(category_id):
                    # カテゴリに含まれる問題を取得（アクティブなもののみ）
                    problems = BasicKnowledgeItem.query.filter_by(
                        category_id=category_id,
                        is_active=True
                    ).order_by(func.random()).offset(skip).limit(count).all()
                    
                    # 解答済みの問題を確認
                    completed = {}
                    for problem in problems:
                        answer = AnswerRecord.query.filter_by(
                            student_id=current_user.id,
                            problem_id=problem.id
                        ).order_by(AnswerRecord.timestamp.desc()).first()
                        
                        completed[problem.id] = answer and answer.is_correct
                    
                    # 問題データを整形
                    problem_data = []
                    for problem in problems:
                        data = {
                            'id': problem.id,
                            'title': problem.title,
                            'question': problem.question,
                            'answer_type': problem.answer_type,
                            'choices': json.loads(problem.choices) if problem.choices else [],
                            'difficulty': problem.difficulty,
                            'category': {
                                'id': problem.category_id,
                                'name': problem.category.name
                            },
                            'completed': completed.get(problem.id, False)
                        }
                        problem_data.append(data)
                    
                    return jsonify({
                        'problems': problem_data,
                        'completed': all(completed.values()) if completed else False
                    })
        except Exception as e:
            return jsonify({'error': f'学習パスデータの処理中にエラーが発生しました: {str(e)}'}), 500
    
    # 通常の問題閲覧または不正なアクセスの場合は拒否
    return jsonify({'error': '指定されたカテゴリの問題にアクセスする権限がありません'}), 403

# 問題テンプレートのダウンロード用ルート
@basebuilder_module.route('/problems/template/<template_type>')
@login_required
def download_problem_template(template_type):
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # template_typeに応じたテンプレートを生成
    if template_type == 'example':
        csv_content = exporters.generate_problem_csv_template()
        filename = 'problem_template_with_examples.csv'
    else:
        csv_content = exporters.generate_problem_csv_empty_template()
        filename = 'problem_template.csv'
    
    # BOMを追加してExcelでの文字化けを防止
    csv_content_with_bom = '\ufeff' + csv_content
    
    # レスポンスを作成
    response = Response(
        csv_content_with_bom,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )
    
    return response

@basebuilder_module.route('/problems/import', methods=['GET', 'POST'])
@login_required
def import_problems():
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    if request.method == 'POST':
        # CSVファイルがアップロードされたか確認
        if 'csv_file' not in request.files:
            flash('CSVファイルが選択されていません。')
            return redirect(request.url)
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('CSVファイルが選択されていません。')
            return redirect(request.url)
        
        # 自動分割オプションを取得
        auto_split = 'auto_split' in request.form
        
        if file and file.filename.endswith('.csv'):
            try:
                # ファイルを読み込む
                csv_content = file.read().decode('utf-8-sig')  # BOMを考慮
                
                # 問題をインポート (TextSetモデルも渡す)
                from basebuilder import importers
                from basebuilder.models import TextSet
                
                success_count, error_count, errors = importers.import_problems_from_csv(
                    csv_content, db, ProblemCategory, BasicKnowledgeItem, current_user.id,
                    TextSet=TextSet if auto_split else None
                )
                
                # 結果を表示
                if auto_split:
                    flash(f'{success_count}個の問題がインポートされ、10個ずつテキストに自動分割されました。')
                else:
                    flash(f'{success_count}個の問題がインポートされました。')
                
                if error_count > 0:
                    for error in errors:
                        flash(error, 'error')
                
                return redirect(url_for('basebuilder_module.problems'))
            
            except Exception as e:
                flash(f'CSVファイルの処理中にエラーが発生しました: {str(e)}')
                return redirect(request.url)
        else:
            flash('CSVファイルの形式が正しくありません。')
            return redirect(request.url)
    
    # GETリクエストの場合、インポートフォームを表示
    return render_template('basebuilder/import_problems.html')

# ここに追加 - テキストセットとしてインポート
@basebuilder_module.route('/text_set/import', methods=['GET', 'POST'])
@login_required
def import_text_set():
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # カテゴリの選択肢を取得
    categories = ProblemCategory.query.all()
    
    if request.method == 'POST':
        title = request.form.get('title', '')  # 空でも許容
        description = request.form.get('description', '')
        category_id = request.form.get('category_id', type=int)
        
        if not category_id:
            flash('カテゴリは必須です。')
            return render_template(
                'basebuilder/import_text.html',
                categories=categories
            )
        
        # CSVファイルのチェック
        if 'csv_file' not in request.files:
            flash('CSVファイルが選択されていません。')
            return redirect(request.url)
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('CSVファイルが選択されていません。')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            try:
                # ファイルを読み込む
                csv_content = file.read().decode('utf-8-sig')  # BOMを考慮
                
                # 問題をインポート
                from basebuilder import importers
                success_count, error_count, errors = importers.import_text_from_csv(
                    csv_content, title, description, category_id, db, TextSet, BasicKnowledgeItem, current_user.id
                )
                
                # 結果を表示
                if success_count > 0:
                    flash(f'{success_count}個の問題を含むテキストがインポートされました。')
                
                if error_count > 0:
                    for error in errors:
                        flash(error, 'error')
                
                return redirect(url_for('basebuilder_module.text_sets'))
            
            except Exception as e:
                flash(f'CSVファイルの処理中にエラーが発生しました: {str(e)}')
                return redirect(request.url)
        else:
            flash('CSVファイルの形式が正しくありません。')
            return redirect(request.url)
    
    # GETリクエストの場合、インポートフォームを表示
    return render_template(
        'basebuilder/import_text.html',
        categories=categories
    )

# テキスト一覧
@basebuilder_module.route('/text_sets')
@login_required
def text_sets():
    if current_user.role == 'student':
        # 学生用のテキスト一覧へリダイレクト
        return redirect(url_for('basebuilder_module.my_texts'))
    
    elif current_user.role == 'teacher':
        # 教師が作成したテキストセットを取得
        text_sets = TextSet.query.filter_by(created_by=current_user.id).all()
        
        return render_template(
            'basebuilder/text_sets.html',
            text_sets=text_sets
        )
    
    # その他のロールの場合
    return redirect(url_for('basebuilder_module.index'))

# テキスト詳細表示
@basebuilder_module.route('/text_set/<int:text_id>')
@login_required
def view_text_set(text_id):
    # テキストセットを取得
    text_set = TextSet.query.get_or_404(text_id)
    
    # 教師の場合は作成者か確認
    if current_user.role == 'teacher' and text_set.created_by != current_user.id:
        flash('このテキストを閲覧する権限がありません。')
        return redirect(url_for('basebuilder_module.text_sets'))
    
    # 学生の場合は配信されたテキストか確認
    if current_user.role == 'student':
        # 学生が所属するクラスを取得
        enrolled_class_ids = [c.id for c in current_user.enrolled_classes]
        
        # そのクラスに配信されているか確認
        delivery = TextDelivery.query.filter(
            TextDelivery.text_set_id == text_id,
            TextDelivery.class_id.in_(enrolled_class_ids)
        ).first()
        
        if not delivery:
            flash('このテキストを閲覧する権限がありません。')
            return redirect(url_for('basebuilder_module.my_texts'))
    
    # テキストに含まれる問題を取得
    problems = BasicKnowledgeItem.query.filter_by(
        text_set_id=text_id
    ).order_by(BasicKnowledgeItem.order_in_text).all()
    
    # 学生の解答状況を取得（学生の場合のみ）
    answers = {}
    if current_user.role == 'student':
        for problem in problems:
            answer = AnswerRecord.query.filter_by(
                student_id=current_user.id,
                problem_id=problem.id
            ).order_by(AnswerRecord.timestamp.desc()).first()
            
            answers[problem.id] = answer
    
    return render_template(
        'basebuilder/view_text.html',
        text_set=text_set,
        problems=problems,
        answers=answers
    )

# テキスト配信
@basebuilder_module.route('/text_set/<int:text_id>/deliver', methods=['GET', 'POST'])
@login_required
def deliver_text(text_id):
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # テキストセットを取得
    text_set = TextSet.query.get_or_404(text_id)
    
    # 作成者か確認
    if text_set.created_by != current_user.id:
        flash('このテキストを配信する権限がありません。')
        return redirect(url_for('basebuilder_module.text_sets'))
    
    # 教師が担当するクラスを取得
    classes = getattr(current_user, 'classes_teaching', [])
    
    if request.method == 'POST':
        class_ids = request.form.getlist('class_ids')
        due_date_str = request.form.get('due_date', '')
        
        if not class_ids:
            flash('配信先クラスを選択してください。')
            return render_template(
                'basebuilder/deliver_text.html',
                text_set=text_set,
                classes=classes
            )
        
        # 期限日の変換
        due_date = None
        if due_date_str:
            from datetime import datetime
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        
        # 各クラスに配信
        for class_id in class_ids:
            # 既に配信済みか確認
            existing = TextDelivery.query.filter_by(
                text_set_id=text_id,
                class_id=int(class_id)
            ).first()
            
            if existing:
                # 既存の配信を更新
                existing.due_date = due_date
                existing.delivered_at = datetime.utcnow()
            else:
                # 新規配信を作成
                delivery = TextDelivery(
                    text_set_id=text_id,
                    class_id=int(class_id),
                    delivered_by=current_user.id,
                    due_date=due_date
                )
                db.session.add(delivery)
        
        db.session.commit()
        flash(f'テキストが選択したクラスに配信されました。')
        return redirect(url_for('basebuilder_module.text_sets'))
    
    return render_template(
        'basebuilder/deliver_text.html',
        text_set=text_set,
        classes=classes
    )

# 学生向けの配信されたテキスト一覧
@basebuilder_module.route('/my_texts')
@login_required
def my_texts():
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # 学生が所属するクラスを取得
    enrolled_classes = current_user.enrolled_classes.all()
    class_ids = [c.id for c in enrolled_classes]
    
    # クラスに配信されたテキストを取得
    deliveries = TextDelivery.query.filter(
        TextDelivery.class_id.in_(class_ids)
    ).order_by(TextDelivery.delivered_at.desc()).all()
    
    # テキストごとの進捗状況を計算
    progress = {}
    for delivery in deliveries:
        # テキストに含まれる問題の総数
        problems = BasicKnowledgeItem.query.filter_by(
            text_set_id=delivery.text_set_id
        ).all()
        
        total_problems = len(problems)
        
        # 解答済みの問題数
        answered_count = 0
        for problem in problems:
            answer = AnswerRecord.query.filter_by(
                student_id=current_user.id,
                problem_id=problem.id
            ).first()
            
            if answer:
                answered_count += 1
        
        # 進捗率を計算
        if total_problems > 0:
            progress_percent = int((answered_count / total_problems) * 100)
        else:
            progress_percent = 0
        
        progress[delivery.text_set_id] = {
            'answered': answered_count,
            'total': total_problems,
            'percent': progress_percent
        }
    
    return render_template(
        'basebuilder/my_texts.html',
        deliveries=deliveries,
        progress=progress
    )

# テキスト解答ページ
@basebuilder_module.route('/text_set/<int:text_id>/solve')
@login_required
def solve_text(text_id):
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # テキストセットを取得
    text_set = TextSet.query.get_or_404(text_id)
    
    # 学生が所属するクラスを取得
    enrolled_class_ids = [c.id for c in current_user.enrolled_classes]
    
    # そのクラスに配信されているか確認
    delivery = TextDelivery.query.filter(
        TextDelivery.text_set_id == text_id,
        TextDelivery.class_id.in_(enrolled_class_ids)
    ).first()
    
    if not delivery:
        flash('このテキストを解答する権限がありません。')
        return redirect(url_for('basebuilder_module.my_texts'))
    
    # テキストに含まれる問題を取得
    problems = BasicKnowledgeItem.query.filter_by(
        text_set_id=text_id
    ).order_by(BasicKnowledgeItem.order_in_text).all()
    
    # 学生の解答状況を取得
    answers = {}
    for problem in problems:
        answer = AnswerRecord.query.filter_by(
            student_id=current_user.id,
            problem_id=problem.id
        ).order_by(AnswerRecord.timestamp.desc()).first()
    
        answers[problem.id] = answer

    # テキストの進捗状況を計算
    progress = {}
    total_problems = len(problems)
    answered_count = sum(1 for p in problems if p.id in answers and answers[p.id])
    progress_percent = int((answered_count / total_problems * 100) if total_problems > 0 else 0)

    progress[text_id] = {
        'answered': answered_count,
        'total': total_problems,
        'percent': progress_percent
    }
    
    return render_template(
        'basebuilder/solve_text.html',
        text_set=text_set,
        problems=problems,
        answers=answers,
        delivery=delivery,
        progress=progress, 
        now=datetime.now() 
    )

def update_text_proficiency(student_id, text_set_id):
    """
    テキストセットの熟練度を計算して更新する
    
    Args:
        student_id: 学生ID
        text_set_id: テキストセットID
    """
    # テキストに含まれる問題数を取得
    problems = BasicKnowledgeItem.query.filter_by(
        text_set_id=text_set_id
    ).all()
    
    if not problems:
        return
    
    # 学生の解答履歴を取得
    answers = {}
    correct_count = 0
    
    for problem in problems:
        answer = AnswerRecord.query.filter_by(
            student_id=student_id,
            problem_id=problem.id
        ).order_by(AnswerRecord.timestamp.desc()).first()
        
        if answer and answer.is_correct:
            correct_count += 1
    
    # 熟練度を計算（正解数÷問題数×100）
    level = int((correct_count / len(problems)) * 100)
    
    # 熟練度レコードを取得または作成
    proficiency = TextProficiencyRecord.query.filter_by(
        student_id=student_id,
        text_set_id=text_set_id
    ).first()
    
    if proficiency:
        proficiency.level = level
        proficiency.last_updated = datetime.utcnow()
    else:
        proficiency = TextProficiencyRecord(
            student_id=student_id,
            text_set_id=text_set_id,
            level=level
        )
        db.session.add(proficiency)
    
    db.session.commit()
    
    return proficiency