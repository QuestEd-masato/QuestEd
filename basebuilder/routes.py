from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response, session, current_app
from flask_login import login_required, current_user
import json
import random
import traceback
from datetime import datetime, timedelta, date
from extensions import db
from app.models import User, InquiryTheme, Class
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
@basebuilder_module.route('/')
@login_required
def index():
    try:
        current_app.logger.info(f"BaseBuilder index accessed by user {current_user.id}")
        
        if current_user.role == 'student':
            # 今日の日付
            today = datetime.now().date()
            
            # 学生が所属するクラスを取得
            enrolled_class_ids = [c.id for c in current_user.enrolled_classes]
            
            # 1. 配信されたテキストを取得
            delivered_texts = TextDelivery.query.filter(
                TextDelivery.class_id.in_(enrolled_class_ids)
            ).order_by(TextDelivery.delivered_at.desc()).limit(5).all()
            
            # 配信されたテキストのカテゴリをすべて取得
            delivered_category_ids = set()
            for delivery in delivered_texts:
                delivered_category_ids.add(delivery.text_set.category_id)
            
            # 2. それぞれのカテゴリを取得
            delivered_categories = ProblemCategory.query.filter(
                ProblemCategory.id.in_(delivered_category_ids)
            ).all()
            
            # 3. カテゴリごとのテキストセットをグループ化
            category_text_sets = {}
            for category_id in delivered_category_ids:
                text_sets = TextSet.query.filter_by(category_id=category_id).all()
                category_text_sets[category_id] = text_sets
            
            # 4. カテゴリの定着度を計算
            category_proficiency = {}
            for record in ProficiencyRecord.query.filter_by(student_id=current_user.id).all():
                category_proficiency[record.category_id] = {
                    'level': record.level * 20,  # 0-5を0-100%に変換
                    'last_updated': record.last_updated
                }
            
            # 5. テキストの定着度を計算
            text_proficiency = {}
            for text_set in TextSet.query.all():
                # テキストの定着度レコードを取得
                text_prof_record = TextProficiencyRecord.query.filter_by(
                    student_id=current_user.id,
                    text_set_id=text_set.id
                ).first()
    
                if text_prof_record:
                    # 定着度レコードが存在する場合
                    text_proficiency[text_set.id] = {
                        'level': text_prof_record.level,
                        'last_updated': text_prof_record.last_updated
                    }
                else:
                    # 定着度レコードが存在しない場合
                    text_proficiency[text_set.id] = {
                        'level': 0,
                        'last_updated': None
                    }

            # テキスト学習進捗状況を計算（解答済み問題数ベース）
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
            
            # 6. 学生の最近の解答履歴を取得（最新10件）
            recent_answers = AnswerRecord.query.filter_by(
                student_id=current_user.id
            ).order_by(AnswerRecord.timestamp.desc()).limit(10).all()
            
            # 7. 学生の選択した探究テーマを取得
            theme = InquiryTheme.query.filter_by(
                student_id=current_user.id, 
                is_selected=True
            ).first()
            
            # 8. テーマに関連する問題を取得
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
            
            return render_template(
                'basebuilder/student_dashboard.html',
                delivered_categories=delivered_categories,
                category_text_sets=category_text_sets,
                category_proficiency=category_proficiency,
                delivered_texts=delivered_texts,
                text_proficiency=text_proficiency,
                recent_answers=recent_answers,
                related_problems=related_problems,
                theme=theme,
                today=today
            )
    
        elif current_user.role == 'teacher':
            # 教師向けダッシュボード（既存のままでOK）
            problem_count = BasicKnowledgeItem.query.filter_by(created_by=current_user.id).count()
            category_count = ProblemCategory.query.filter_by(created_by=current_user.id).count()
            path_count = LearningPath.query.filter_by(created_by=current_user.id).count()
            classes = current_user.classes_teaching
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
    except Exception as e:
        current_app.logger.error(f"BaseBuilder index error: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        # 500.htmlが無い場合はエラーメッセージを返す
        try:
            return render_template('errors/500.html'), 500
        except:
            return f"Internal Server Error: {str(e)}", 500

# 問題カテゴリ一覧
@basebuilder_module.route('/categories')
@login_required
def categories():
    # 学校に所属していない場合の対応
    if not current_user.school_id:
        flash('カテゴリを表示するには学校に所属している必要があります。')
        return redirect(url_for('basebuilder_module.index'))
        
    # 同じ学校のトップレベルのカテゴリを取得
    top_categories = ProblemCategory.query.filter_by(
        parent_id=None,
        school_id=current_user.school_id
    ).all()
    
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
    
    # 学校IDがなければアクセスできない
    if not current_user.school_id:
        flash('カテゴリを作成するには学校に所属している必要があります。')
        return redirect(url_for('basebuilder_module.index'))
    
    # 親カテゴリの選択肢を取得（同じ学校のカテゴリのみ）
    parent_categories = ProblemCategory.query.filter_by(school_id=current_user.school_id).all()
    
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
                # 親カテゴリが同じ学校のものか確認
                parent_category = ProblemCategory.query.get(parent_id)
                if parent_category.school_id != current_user.school_id:
                    flash('無効な親カテゴリが選択されました。')
                    return render_template(
                        'basebuilder/create_category.html',
                        parent_categories=parent_categories
                    )
            except ValueError:
                parent_id = None
        else:
            parent_id = None
        
        # 新しいカテゴリを作成
        new_category = ProblemCategory(
            name=name,
            description=description,
            parent_id=parent_id,
            school_id=current_user.school_id,  # 教師の学校IDを設定
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
        # このカテゴリに関連するテキストセットを取得
        text_sets = TextSet.query.filter_by(category_id=category_id).all()
        
        # 各テキストセットとその関連レコードを削除
        for text_set in text_sets:
            # テキストセットに含まれる問題を取得
            text_problems = BasicKnowledgeItem.query.filter_by(text_set_id=text_set.id).all()
            
            # 各問題に関連するレコードを削除
            for problem in text_problems:
                # 単語の熟練度記録を削除
                WordProficiency.query.filter_by(problem_id=problem.id).delete()
                
                # 解答記録の削除
                AnswerRecord.query.filter_by(problem_id=problem.id).delete()
                
                # テーマとの関連付けを削除
                KnowledgeThemeRelation.query.filter_by(problem_id=problem.id).delete()
                
                # 問題を削除
                db.session.delete(problem)
            
            # テキストの熟練度記録を削除
            TextProficiencyRecord.query.filter_by(text_set_id=text_set.id).delete()
            
            # テキスト配信を削除
            TextDelivery.query.filter_by(text_set_id=text_set.id).delete()
            
            # テキストセットを削除
            db.session.delete(text_set)
        
        # このカテゴリに直接関連する問題を取得
        problems = BasicKnowledgeItem.query.filter_by(category_id=category_id).all()
        
        # 各問題に関連する解答記録・関連付けを削除
        for problem in problems:
            # 単語の熟練度記録を削除
            WordProficiency.query.filter_by(problem_id=problem.id).delete()
            
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
    # 学校に所属していない場合の対応
    if not current_user.school_id:
        flash('問題を表示するには学校に所属している必要があります。')
        return redirect(url_for('basebuilder_module.index'))
    
    # クエリパラメータからフィルタリング条件を取得
    category_id = request.args.get('category_id', type=int)
    text_id = request.args.get('text_id', type=int)
    difficulty = request.args.get('difficulty', type=int)
    search = request.args.get('search', '')
    proficiency = request.args.get('proficiency', '')
    
    # 検索パラメータをセッションに保存（「この検索結果から学習」のため）
    session['search_params'] = {
        'category_id': category_id,
        'text_id': text_id, 
        'difficulty': difficulty,
        'search': search,
        'proficiency': proficiency
    }
    
    # 基本クエリ - 同じ学校の問題のみ
    query = BasicKnowledgeItem.query.filter_by(school_id=current_user.school_id)
    
    if current_user.role == 'student':
        # 学生の場合は配信されたテキスト/カテゴリのみ表示
        # 所属クラスを取得
        enrolled_class_ids = [c.id for c in current_user.enrolled_classes]
        
        # 配信されたテキストを取得
        delivered_text_ids = db.session.query(TextDelivery.text_set_id).filter(
            TextDelivery.class_id.in_(enrolled_class_ids)
        ).all()
        delivered_text_ids = [t[0] for t in delivered_text_ids]
        
        # 配信されたテキストに含まれる問題のみを対象に
        query = query.filter(
            BasicKnowledgeItem.text_set_id.in_(delivered_text_ids)
        )
        
        # 配信されたテキストとカテゴリを取得（ドロップダウン用）
        delivered_text_sets = TextSet.query.filter(
            TextSet.id.in_(delivered_text_ids)
        ).all()
        
        delivered_category_ids = db.session.query(TextSet.category_id).filter(
            TextSet.id.in_(delivered_text_ids)
        ).distinct().all()
        delivered_category_ids = [c[0] for c in delivered_category_ids]
        
        delivered_categories = ProblemCategory.query.filter(
            ProblemCategory.id.in_(delivered_category_ids)
        ).all()
        
        # 問題IDのリストを先に取得（クエリは一旦実行しておく）
        problem_ids = [p.id for p in query.all()]
        word_proficiency_records = {}
        
        # 修正: WordProficiencyモデルから単語ごとの定着度を取得
        word_proficiencies = WordProficiency.query.filter(
            WordProficiency.student_id == current_user.id,
            WordProficiency.problem_id.in_(problem_ids)
        ).all()
        
        # 熟練度レコードを問題IDでマッピング
        for wp in word_proficiencies:
            word_proficiency_records[wp.problem_id] = {
                'level': wp.level,
                'last_updated': wp.last_updated,
                'review_date': wp.review_date
            }
        
    else:
        # 教師の場合は自分が作成した問題 + 同じ学校の問題を表示
        query = query.filter(
            (BasicKnowledgeItem.created_by == current_user.id) |
            (BasicKnowledgeItem.school_id == current_user.school_id)
        )
        delivered_text_sets = []
        delivered_categories = ProblemCategory.query.filter_by(school_id=current_user.school_id).all()
        word_proficiency_records = {}
    
    # フィルタリング条件の適用
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if text_id:
        query = query.filter_by(text_set_id=text_id)
    
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    
    if search:
        query = query.filter(
            (BasicKnowledgeItem.title.like(f'%{search}%')) |
            (BasicKnowledgeItem.question.like(f'%{search}%'))
        )
    
    # 定着度フィルターの適用（学生のみ）
    filtered_problem_ids = None
    if current_user.role == 'student' and proficiency:
        filtered_ids = []
        
        if proficiency == '0':
            # 未学習 (level = 0)
            # WordProficiencyに登録がない問題も含める
            wp_problem_ids = [wp_id for wp_id in word_proficiency_records.keys()]
            for pid in problem_ids:
                if pid not in wp_problem_ids or word_proficiency_records[pid]['level'] == 0:
                    filtered_ids.append(pid)
        elif proficiency == '1-2':
            # 初級 (level = 1-2)
            for pid, prof in word_proficiency_records.items():
                if 1 <= prof['level'] <= 2:
                    filtered_ids.append(pid)
        elif proficiency == '3-4':
            # 中級 (level = 3-4)
            for pid, prof in word_proficiency_records.items():
                if 3 <= prof['level'] <= 4:
                    filtered_ids.append(pid)
        elif proficiency == '5':
            # マスター (level = 5)
            for pid, prof in word_proficiency_records.items():
                if prof['level'] == 5:
                    filtered_ids.append(pid)
        
        if filtered_ids:
            query = query.filter(BasicKnowledgeItem.id.in_(filtered_ids))
            filtered_problem_ids = filtered_ids
    
    # 問題の取得（フィルター後のクエリを実行）
    problems = query.order_by(BasicKnowledgeItem.title).all()
    
    # 最終的な単語定着度レコードの絞り込み
    if filtered_problem_ids:
        filtered_word_proficiencies = {}
        for pid in filtered_problem_ids:
            if pid in word_proficiency_records:
                filtered_word_proficiencies[pid] = word_proficiency_records[pid]
        word_proficiency_records = filtered_word_proficiencies
    
    return render_template(
        'basebuilder/problems.html',
        problems=problems,
        categories=delivered_categories,
        delivered_categories=delivered_categories,
        delivered_text_sets=delivered_text_sets,
        selected_category_id=category_id,
        selected_text_id=text_id,
        selected_difficulty=difficulty,
        selected_proficiency=proficiency,
        search=search,
        word_proficiencies=word_proficiency_records
    )

@basebuilder_module.route('/start_search_session')
@login_required
def start_search_session():
    """検索結果の単語からセッションを開始する"""
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # 検索条件をセッションから取得
    search_params = session.get('search_params', {})
    
    # 検索条件に一致する問題を取得
    query = BasicKnowledgeItem.query.filter_by(is_active=True)
    
    # 配信されたテキストに限定
    enrolled_class_ids = [c.id for c in current_user.enrolled_classes]
    delivered_text_ids = db.session.query(TextDelivery.text_set_id).filter(
        TextDelivery.class_id.in_(enrolled_class_ids)
    ).distinct().all()
    delivered_text_ids = [id[0] for id in delivered_text_ids]
    
    query = query.filter(BasicKnowledgeItem.text_set_id.in_(delivered_text_ids))
    
    # その他の検索条件を適用
    if 'category_id' in search_params and search_params['category_id']:
        query = query.filter_by(category_id=search_params['category_id'])
    
    if 'text_id' in search_params and search_params['text_id']:
        query = query.filter_by(text_set_id=search_params['text_id'])
    
    if 'difficulty' in search_params and search_params['difficulty']:
        query = query.filter_by(difficulty=search_params['difficulty'])
    
    if 'search' in search_params and search_params['search']:
        search_term = search_params['search']
        query = query.filter(
            (BasicKnowledgeItem.title.like(f'%{search_term}%')) |
            (BasicKnowledgeItem.question.like(f'%{search_term}%'))
        )
    
    # 全ての問題を取得（定着度フィルター前）
    all_problems = query.all()
    problem_ids = [p.id for p in all_problems]
    
    # 定着度フィルターの適用
    if 'proficiency' in search_params and search_params['proficiency']:
        proficiency = search_params['proficiency']
        
        # 単語ごとの定着度を計算
        word_proficiency_records = {}
        for problem_id in problem_ids:
            # 解答履歴を取得（最新5件）
            answers = AnswerRecord.query.filter_by(
                student_id=current_user.id,
                problem_id=problem_id
            ).order_by(AnswerRecord.timestamp.desc()).limit(5).all()
            
            if answers:
                # 解答があれば定着度を計算
                correct_count = sum(1 for a in answers if a.is_correct)
                level = min(5, int((correct_count / len(answers)) * 5))
            else:
                # 解答がなければ0
                level = 0
            
            word_proficiency_records[problem_id] = level
        
        # 定着度フィルターに基づいてフィルタリング
        filtered_ids = []
        
        if proficiency == '0':
            # 未学習 (level = 0)
            for pid, level in word_proficiency_records.items():
                if level == 0:
                    filtered_ids.append(pid)
        elif proficiency == '1-2':
            # 初級 (level = 1-2)
            for pid, level in word_proficiency_records.items():
                if 1 <= level <= 2:
                    filtered_ids.append(pid)
        elif proficiency == '3-4':
            # 中級 (level = 3-4)
            for pid, level in word_proficiency_records.items():
                if 3 <= level <= 4:
                    filtered_ids.append(pid)
        elif proficiency == '5':
            # マスター (level = 5)
            for pid, level in word_proficiency_records.items():
                if level == 5:
                    filtered_ids.append(pid)
        
        if filtered_ids:
            problem_ids = filtered_ids
    
    if not problem_ids:
        flash('該当する問題が見つかりませんでした。検索条件を変更してください。')
        return redirect(url_for('basebuilder_module.problems'))
    
    # セッション情報を初期化
    session['learning_session'] = {
        'problem_ids': problem_ids,
        'total_problems': min(10, len(problem_ids)),
        'max_attempts': 15,
        'current_attempt': 0,
        'completed_problems': [],
        'current_problem_id': None,
        'session_start': datetime.now().isoformat(),
        'is_search_session': True  # 検索結果からのセッションであることを示すフラグ
    }
    
    # 最初の問題を選択
    return redirect(url_for('basebuilder_module.next_problem'))

# 問題の作成と編集
@basebuilder_module.route('/problem/create', methods=['GET', 'POST'])
@login_required
def create_problem():
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # 学校に所属していない場合の対応
    if not current_user.school_id:
        flash('問題を作成するには学校に所属している必要があります。')
        return redirect(url_for('basebuilder_module.index'))
    
    # 同じ学校のカテゴリのみ取得
    categories = ProblemCategory.query.filter_by(school_id=current_user.school_id).all()
    
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
        
        # カテゴリが同じ学校のものか確認
        category = ProblemCategory.query.get(category_id)
        if not category or category.school_id != current_user.school_id:
            flash('無効なカテゴリが選択されました。')
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
            created_by=current_user.id,
            school_id=current_user.school_id  # 学校IDを設定
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
    
    # 配信済みテキストを確認
    # 学生が所属するクラスを取得
    enrolled_class_ids = [c.id for c in current_user.enrolled_classes]
    
    # 配信されたテキストを取得
    delivered_text_ids = db.session.query(TextDelivery.text_set_id).filter(
        TextDelivery.class_id.in_(enrolled_class_ids)
    ).all()
    delivered_text_ids = [t[0] for t in delivered_text_ids]
    
    # カテゴリに属する配信済みテキストを取得
    text_sets = TextSet.query.filter(
        TextSet.category_id == category_id,
        TextSet.id.in_(delivered_text_ids)
    ).all()
    
    # 各テキストセットの問題数をカウント
    text_problem_counts = {}
    for text_set in text_sets:
        count = BasicKnowledgeItem.query.filter_by(text_set_id=text_set.id).count()
        text_problem_counts[text_set.id] = count
    
    # カテゴリの熟練度を取得
    proficiency_record = ProficiencyRecord.query.filter_by(
        student_id=current_user.id,
        category_id=category_id
    ).first()
    
    return render_template(
        'basebuilder/category_texts.html',
        category=category,
        text_sets=text_sets,
        text_problem_counts=text_problem_counts,
        total_problems=len(problems),
        proficiency_record=proficiency_record
    )

@basebuilder_module.route('/text_sets/delete', methods=['POST'])
@login_required
def delete_text_sets():
    """テキストセットの一括削除処理"""
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # フォームから選択されたテキストIDを取得
    text_ids = request.form.getlist('text_ids')
    
    if not text_ids:
        flash('削除するテキストが選択されていません。')
        return redirect(url_for('basebuilder_module.text_sets'))
    
    deleted_count = 0
    error_count = 0
    
    for text_id_str in text_ids:
        try:
            text_id = int(text_id_str)
            text_set = TextSet.query.get(text_id)
            
            # 作成者本人のみ削除可能
            if not text_set or text_set.created_by != current_user.id:
                error_count += 1
                continue
            
            # テキストに含まれる問題を取得
            problems = BasicKnowledgeItem.query.filter_by(text_set_id=text_id).all()
            
            # 各問題に関連する記録を削除
            for problem in problems:
                # 単語の熟練度記録を削除
                WordProficiency.query.filter_by(problem_id=problem.id).delete()
                
                # 解答記録を削除
                AnswerRecord.query.filter_by(problem_id=problem.id).delete()
                
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
            error_count += 1
            flash(f'テキストID {text_id_str} の削除中にエラーが発生しました: {str(e)}')
    
    # 成功したものをコミット
    try:
        db.session.commit()
        if deleted_count > 0:
            flash(f'{deleted_count} 件のテキストを削除しました。')
        
        if error_count > 0:
            flash(f'{error_count} 件のテキストを削除できませんでした。', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'テキストの削除中にエラーが発生しました: {str(e)}', 'error')
    
    return redirect(url_for('basebuilder_module.text_sets'))

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
    answer_records_list = AnswerRecord.query.filter(
        AnswerRecord.student_id == current_user.id,
        AnswerRecord.problem_id.in_(learning_session['completed_problems']),
        AnswerRecord.timestamp >= session_start
    ).order_by(AnswerRecord.timestamp).all()
    
    # 問題IDごとに最新の解答記録を取得
    latest_records = {}
    for record in answer_records_list:
        latest_records[record.problem_id] = record
    
    # 正解数・不正解数をカウント
    correct_count = sum(1 for record in latest_records.values() if record.is_correct)
    incorrect_count = len(latest_records) - correct_count
    
    # 各単語の熟練度を取得
    word_proficiencies = WordProficiency.query.filter(
        WordProficiency.student_id == current_user.id,
        WordProficiency.problem_id.in_(learning_session['completed_problems'])
    ).all()
    
    # 各カテゴリの熟練度を取得
    proficiency_records = ProficiencyRecord.query.filter_by(
        student_id=current_user.id
    ).all()
    
    return render_template(
        'basebuilder/session_summary.html',
        completed_problems=completed_problems,
        answer_records=latest_records,
        word_proficiencies=word_proficiencies,
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
    
    # 単語の熟練度レコードがない場合はデフォルト値0として計算
    found_problems = len(word_proficiencies)
    total_problems = len(problem_ids)
    
    # 合計熟練度計算
    total_level = sum(wp.level for wp in word_proficiencies) if word_proficiencies else 0
    
    # 平均熟練度計算 (存在する単語の熟練度の合計 / 全単語数)
    # 存在しない単語は熟練度0として計算
    avg_level = total_level / total_problems if total_problems > 0 else 0
    
    # カテゴリの熟練度を更新または作成
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
    
    # 熟練度は平均値を整数に切り捨て (0-5の範囲)
    proficiency.level = min(5, int(avg_level))
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
    
    # 学生が所属するクラスを取得
    enrolled_class_ids = [c.id for c in student.enrolled_classes]
    
    # 配信されたテキストを取得
    delivered_text_ids = db.session.query(TextDelivery.text_set_id).filter(
        TextDelivery.class_id.in_(enrolled_class_ids)
    ).distinct().all()
    delivered_text_ids = [t[0] for t in delivered_text_ids]
    
    # 配信されたテキストを取得
    text_sets = TextSet.query.filter(
        TextSet.id.in_(delivered_text_ids)
    ).all()
    
    # テキストごとの定着度データを収集
    category_proficiency = {}
    text_proficiency_data = {}
    total_words = 0
    mastered_words = 0
    
    for text in text_sets:
        # テキスト内の単語（問題）を取得
        problems = BasicKnowledgeItem.query.filter_by(
            text_set_id=text.id,
            is_active=True
        ).all()
        
        if not problems:
            continue
            
        # このテキストの単語数をカウント
        text_words_count = len(problems)
        total_words += text_words_count
        
        # 単語IDのリストを作成
        problem_ids = [p.id for p in problems]
        
        # カテゴリ情報
        category_id = text.category_id
        
        # 単語ごとの熟練度を取得
        word_proficiencies = WordProficiency.query.filter(
            WordProficiency.student_id == student_id,
            WordProficiency.problem_id.in_(problem_ids)
        ).all()
        
        # レベルごとの単語数をカウント
        level_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        # 単語マップを作成（存在する単語の熟練度）
        proficiency_map = {}
        
        for wp in word_proficiencies:
            proficiency_map[wp.problem_id] = wp.level
            level_counts[wp.level] += 1
        
        # 未学習の単語をカウント
        for pid in problem_ids:
            if pid not in proficiency_map:
                level_counts[0] += 1
        
        # このカテゴリのマスター単語数
        text_mastered = level_counts[5]
        mastered_words += text_mastered
        
        # テキストの定着度を計算
        max_points = text_words_count * 5  # 最大ポイント
        actual_points = sum(level * count for level, count in level_counts.items() if level > 0)
        
        # 最終更新日を取得
        last_updated = None
        if word_proficiencies:
            last_updated = max(wp.last_updated for wp in word_proficiencies)
        
        # テキストの定着度をパーセントで計算
        text_percentage = (actual_points / max_points * 100) if max_points > 0 else 0
        
        # テキスト定着度データを保存
        text_proficiency_data[text.id] = {
            'level': round(text_percentage),
            'last_updated': last_updated
        }
        
        # カテゴリ定着度データを更新/作成
        if category_id in category_proficiency:
            # 既存のカテゴリデータを更新
            category_proficiency[category_id]['total'] += text_words_count
            category_proficiency[category_id]['mastered'] += text_mastered
            
            # レベルカウントを更新
            for level, count in level_counts.items():
                if level in category_proficiency[category_id]['levels']:
                    category_proficiency[category_id]['levels'][level] += count
                else:
                    category_proficiency[category_id]['levels'][level] = count
            
            # 最終更新日を更新
            if last_updated and (not category_proficiency[category_id]['last_updated'] or 
                                last_updated > category_proficiency[category_id]['last_updated']):
                category_proficiency[category_id]['last_updated'] = last_updated
                
        else:
            # 新しいカテゴリデータを作成
            category_proficiency[category_id] = {
                'category': text.category,
                'text_set_id': text.id,  # 最初のテキストIDを保存
                'total': text_words_count,
                'mastered': text_mastered,
                'levels': level_counts,
                'last_updated': last_updated
            }
    
    # 各カテゴリの定着度パーセントを計算
    for category_data in category_proficiency.values():
        max_points = category_data['total'] * 5
        actual_points = sum(level * count for level, count in category_data['levels'].items() if level > 0)
        category_data['percentage'] = (actual_points / max_points * 100) if max_points > 0 else 0
    
    # 総合定着度を計算
    overall_proficiency = 0
    if total_words > 0:
        # 総合ポイント
        total_possible_points = total_words * 5
        total_actual_points = sum(
            sum(level * count for level, count in cat_data['levels'].items() if level > 0)
            for cat_data in category_proficiency.values()
        )
        overall_proficiency = (total_actual_points / total_possible_points * 100) if total_possible_points > 0 else 0
    
    # 習得率
    mastery_rate = (mastered_words / total_words * 100) if total_words > 0 else 0
    
    # 学生の解答履歴を取得（最新20件）
    answer_records = AnswerRecord.query.filter_by(
        student_id=student_id
    ).order_by(AnswerRecord.timestamp.desc()).limit(20).all()
    
    # 解答数と正解率を計算
    all_answers = AnswerRecord.query.filter_by(student_id=student_id).all()
    answer_count = len(all_answers)
    correct_count = sum(1 for answer in all_answers if answer.is_correct)
    correct_rate = (correct_count / answer_count * 100) if answer_count > 0 else 0
    
    # 最後の活動日時
    last_activity = answer_records[0].timestamp if answer_records else None
    
    # 単語ごとの熟練度を取得（解答履歴表示用）
    word_proficiency = {}
    
    # 解答履歴に含まれる問題IDを収集
    problem_ids = [record.problem_id for record in answer_records]
    
    # 熟練度レコードを取得
    word_prof_records = WordProficiency.query.filter(
        WordProficiency.student_id == student_id,
        WordProficiency.problem_id.in_(problem_ids)
    ).all()
    
    # 辞書にマッピング
    for wp in word_prof_records:
        word_proficiency[wp.problem_id] = {
            'level': wp.level,
            'last_updated': wp.last_updated,
            'review_date': wp.review_date
        }
    
    return render_template(
        'basebuilder/student_analysis.html',
        student=student,
        proficiency_records=None,  # 古い熟練度記録は不要
        answer_records=answer_records,
        overall_proficiency=overall_proficiency,
        category_proficiency=category_proficiency,
        text_proficiency=text_proficiency_data,
        total_words=total_words,
        mastered_words=mastered_words,
        mastery_rate=mastery_rate,
        correct_rate=correct_rate,
        answer_count=answer_count,
        last_activity=last_activity,
        word_proficiency=word_proficiency
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
    # 学校に所属していない場合の対応
    if not current_user.school_id:
        flash('学習パスを表示するには学校に所属している必要があります。')
        return redirect(url_for('basebuilder_module.index'))
    
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
        # 教師向け - 作成した学習パス + 同じ学校の学習パスを表示
        paths = LearningPath.query.filter(
            (LearningPath.created_by == current_user.id) |
            (LearningPath.school_id == current_user.school_id)
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
    
    # 学校に所属していない場合の対応
    if not current_user.school_id:
        flash('学習パスを作成するには学校に所属している必要があります。')
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
            created_by=current_user.id,
            school_id=current_user.school_id  # 学校IDを設定
        )
        
        db.session.add(new_path)
        db.session.commit()
        
        flash('学習パスが作成されました。')
        return redirect(url_for('basebuilder_module.learning_paths'))
    
    # 同じ学校のカテゴリを取得（ステップ作成用）
    categories = ProblemCategory.query.filter_by(school_id=current_user.school_id).all()
    
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

@basebuilder_module.route('/api/problems')
@login_required
def api_problems():
    """問題一覧を提供するAPIエンドポイント"""
    if current_user.role not in ['teacher', 'student']:
        return jsonify({'error': '権限がありません'}), 403
    
    # アクティブな問題を取得
    problems = BasicKnowledgeItem.query.filter_by(is_active=True).all()
    
    # 問題データをJSON形式で返す
    problem_data = []
    for problem in problems:
        data = {
            'id': problem.id,
            'title': problem.title,
            'category_id': problem.category_id,
            'category_name': problem.category.name,
            'difficulty': problem.difficulty
        }
        problem_data.append(data)
    
    return jsonify({'problems': problem_data})

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
    
    # 学校に所属していない場合の対応
    if not current_user.school_id:
        flash('問題をインポートするには学校に所属している必要があります。')
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
                    csv_content, db, ProblemCategory, BasicKnowledgeItem, 
                    current_user.id, current_user.school_id,  # 学校IDを追加
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
    
    # 学校に所属していない場合の対応
    if not current_user.school_id:
        flash('テキストをインポートするには学校に所属している必要があります。')
        return redirect(url_for('basebuilder_module.index'))
    
    # 同じ学校のカテゴリのみ取得
    categories = ProblemCategory.query.filter_by(school_id=current_user.school_id).all()
    
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
                    csv_content, title, description, category_id, db, TextSet, BasicKnowledgeItem, 
                    current_user.id, school_id=current_user.school_id  # 学校IDを追加
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
        # 学校に所属していない場合の対応
        if not current_user.school_id:
            flash('テキストを表示するには学校に所属している必要があります。')
            return redirect(url_for('basebuilder_module.index'))
            
        # 同じ学校のテキストセットを表示（自分が作成したもの + 学校内の共有されたもの）
        text_sets = TextSet.query.filter(
            (TextSet.created_by == current_user.id) | 
            (TextSet.school_id == current_user.school_id)
        ).all()
        
        return render_template(
            'basebuilder/text_sets.html',
            text_sets=text_sets
        )
    
    # その他のロールの場合
    return redirect(url_for('basebuilder_module.index'))
    
@basebuilder_module.route('/text_sets/bulk_delete', methods=['POST'])  # URLパスを変更
@login_required
def bulk_delete_text_sets():  # 関数名を変更
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # 選択されたテキストIDを取得
    text_ids = request.form.getlist('text_ids')
    
    if not text_ids:
        flash('削除するテキストが選択されていません。')
        return redirect(url_for('basebuilder_module.text_sets'))
    
    try:
        deleted_count = 0
        for text_id in text_ids:
            # テキストを取得
            text_set = TextSet.query.get(int(text_id))
            
            # 作成者チェック
            if text_set and text_set.created_by == current_user.id:
                # テキストに含まれる問題を取得
                problems = BasicKnowledgeItem.query.filter_by(text_set_id=text_set.id).all()
                
                # 問題の解答記録を削除
                for problem in problems:
                    AnswerRecord.query.filter_by(problem_id=problem.id).delete()
                    db.session.delete(problem)
                
                # テキストの配信記録を削除
                TextDelivery.query.filter_by(text_set_id=text_set.id).delete()
                
                # テキストの熟練度記録を削除
                TextProficiencyRecord.query.filter_by(text_set_id=text_set.id).delete()
                
                # テキストを削除
                db.session.delete(text_set)
                deleted_count += 1
        
        db.session.commit()
        flash(f'{deleted_count}件のテキストを削除しました。')
    
    except Exception as e:
        db.session.rollback()
        flash(f'テキストの削除中にエラーが発生しました: {str(e)}')
    
    return redirect(url_for('basebuilder_module.text_sets'))

# 修正が必要と思われるルーティング関数
@basebuilder_module.route('/text_set/<int:text_id>')
@login_required
def view_text_set(text_id):
    try:
        # テキストセットを取得（存在しない場合は404エラー）
        text_set = TextSet.query.get_or_404(text_id)
        
        # 教師の権限チェック
        if current_user.role == 'teacher' and text_set.created_by != current_user.id:
            flash('このテキストの詳細を閲覧する権限がありません。')
            return redirect(url_for('basebuilder_module.text_sets'))
        
        # 学生の権限チェック
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
        
        # テキストに含まれる問題を安全に取得
        problems = BasicKnowledgeItem.query.filter_by(
            text_set_id=text_id
        ).order_by(BasicKnowledgeItem.order_in_text).all() or []
        
        # テキスト全体の定着度と単語熟練度の初期化
        text_proficiency = None
        word_proficiencies = {}
        answers = {}
        
        if current_user.role == 'student':
            # テキストの定着度を取得（存在しなければNoneのまま）
            text_proficiency = TextProficiencyRecord.query.filter_by(
                student_id=current_user.id,
                text_set_id=text_id
            ).first()
            
            # 問題がある場合のみループ処理
            if problems:
                for problem in problems:
                    # 単語の熟練度を取得
                    wp = WordProficiency.query.filter_by(
                        student_id=current_user.id,
                        problem_id=problem.id
                    ).first()
                    
                    if wp:
                        word_proficiencies[problem.id] = {
                            'level': wp.level,
                            'last_updated': wp.last_updated
                        }
                    
                    # 解答状況を取得
                    answer = AnswerRecord.query.filter_by(
                        student_id=current_user.id,
                        problem_id=problem.id
                    ).order_by(AnswerRecord.timestamp.desc()).first()
                    
                    answers[problem.id] = answer
        
        return render_template(
            'basebuilder/View_text.html',
            text_set=text_set,
            problems=problems,
            answers=answers,
            text_proficiency=text_proficiency,
            word_proficiencies=word_proficiencies
        )
    
    except Exception as e:
        # デバッグ用にエラーをログに出力
        import traceback
        error_details = traceback.format_exc()
        print(f"view_text_set エラー (text_id={text_id}): {str(e)}\n{error_details}")
        
        flash('テキストの表示中にエラーが発生しました。管理者に連絡してください。')
        return redirect(url_for('basebuilder_module.index'))
    
def calculate_text_proficiency(student_id, text_id, problems=None):
    """
    テキスト全体の定着度を単語の熟練度から計算する関数
    
    Args:
        student_id: 学生ID
        text_id: テキストID
        problems: すでに取得済みの問題リスト（省略可）
        
    Returns:
        TextProficiencyRecord: 更新または作成されたテキスト定着度レコード
    """
    # テキストの定着度レコードを取得
    text_proficiency = TextProficiencyRecord.query.filter_by(
        student_id=student_id,
        text_set_id=text_id
    ).first()
    
    # 問題が渡されていない場合は取得
    if problems is None:
        problems = BasicKnowledgeItem.query.filter_by(
            text_set_id=text_id,
            is_active=True
        ).all()
    
    if problems:
        # 問題IDのリストを作成
        problem_ids = [p.id for p in problems]
        
        # 単語ごとの熟練度を取得
        word_proficiencies = WordProficiency.query.filter(
            WordProficiency.student_id == student_id,
            WordProficiency.problem_id.in_(problem_ids)
        ).all()
        
        # 熟練度マップを作成
        proficiency_map = {wp.problem_id: wp.level for wp in word_proficiencies}
        
        # 合計熟練度と最大可能熟練度を計算
        total_level = sum(proficiency_map.get(pid, 0) for pid in problem_ids)
        max_level = len(problem_ids) * 5  # 各問題の最大熟練度は5
        
        # 定着度を計算（%）
        level_percentage = (total_level / max_level * 100) if max_level > 0 else 0
        
        # 既存のレコードを更新または新規作成
        if text_proficiency:
            text_proficiency.level = int(level_percentage)
            text_proficiency.last_updated = datetime.utcnow()
        else:
            text_proficiency = TextProficiencyRecord(
                student_id=student_id,
                text_set_id=text_id,
                level=int(level_percentage)
            )
            db.session.add(text_proficiency)
        
        db.session.commit()
    
    return text_proficiency

# テキスト配信
@basebuilder_module.route('/text_set/<int:text_id>/deliver', methods=['GET', 'POST'])
@login_required
def deliver_text(text_id):
    from datetime import datetime  # ローカルでインポートして確実に使用できるようにする
    
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # テキストセットを取得
    text_set = TextSet.query.get_or_404(text_id)
    
    # 学校に所属していない場合の対応
    if not current_user.school_id:
        flash('テキストを配信するには学校に所属している必要があります。')
        return redirect(url_for('basebuilder_module.index'))
    
    # アクセス権限チェック（作成者または同じ学校の教師）
    if text_set.created_by != current_user.id and text_set.school_id != current_user.school_id:
        flash('このテキストを配信する権限がありません。')
        return redirect(url_for('basebuilder_module.text_sets'))
    
    # 教師が担当するクラスを取得（同じ学校のクラスのみ）
    classes = Class.query.filter_by(
        teacher_id=current_user.id,
        school_id=current_user.school_id
    ).all()
    
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
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('期限日の形式が正しくありません。YYYY-MM-DD形式で入力してください。')
                return render_template(
                    'basebuilder/deliver_text.html',
                    text_set=text_set,
                    classes=classes
                )
        
        # 各クラスに配信
        for class_id in class_ids:
            # クラスが同じ学校のものか確認
            class_obj = Class.query.get(int(class_id))
            if not class_obj or class_obj.school_id != current_user.school_id:
                continue
                
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
    
    # テキストごとの定着度を取得
    text_proficiency = {}
    for record in TextProficiencyRecord.query.filter_by(
        student_id=current_user.id
    ).all():
        text_proficiency[record.text_set_id] = {
            'level': record.level,
            'last_updated': record.last_updated
        }
    
    # レコードがないテキストの定着度を計算
    for delivery in deliveries:
        if delivery.text_set_id not in text_proficiency:
            # テキストに含まれる問題を取得
            problems = BasicKnowledgeItem.query.filter_by(
                text_set_id=delivery.text_set_id
            ).all()
            
            if problems:
                # 正解数をカウント
                correct_count = 0
                total_count = len(problems)
                
                for problem in problems:
                    answer = AnswerRecord.query.filter_by(
                        student_id=current_user.id,
                        problem_id=problem.id,
                        is_correct=True
                    ).order_by(AnswerRecord.timestamp.desc()).first()
                    
                    if answer:
                        correct_count += 1
                
                # 定着度を計算
                if total_count > 0:
                    level = int((correct_count / total_count) * 100)
                else:
                    level = 0
                
                text_proficiency[delivery.text_set_id] = {
                    'level': level,
                    'last_updated': datetime.now()
                }
    
    return render_template(
        'basebuilder/my_texts.html',
        deliveries=deliveries,
        text_proficiency=text_proficiency,
        now=datetime.now()
    )

@basebuilder_module.route('/problem/<int:problem_id>/solve', methods=['GET'])
@login_required
def solve_problem(problem_id):
    try:
        current_app.logger.info(f"Solving problem {problem_id} for user {current_user.id}")
        
        if current_user.role != 'student':
            flash('この機能は学生のみ利用可能です。')
            return redirect(url_for('basebuilder_module.index'))
        
        # 問題を取得
        problem = BasicKnowledgeItem.query.get_or_404(problem_id)
        
        # テキストコンテキスト（テキスト内の問題かどうか）
        text_context = None
        if problem.text_set_id:
            text_set = TextSet.query.get(problem.text_set_id)
            
            # テキスト内の前後の問題を取得
            next_problem = BasicKnowledgeItem.query.filter(
                BasicKnowledgeItem.text_set_id == problem.text_set_id,
                BasicKnowledgeItem.order_in_text > problem.order_in_text
            ).order_by(BasicKnowledgeItem.order_in_text).first()
            
            prev_problem = BasicKnowledgeItem.query.filter(
                BasicKnowledgeItem.text_set_id == problem.text_set_id,
                BasicKnowledgeItem.order_in_text < problem.order_in_text
            ).order_by(BasicKnowledgeItem.order_in_text.desc()).first()
            
            # テキストコンテキスト情報を構築
            text_context = {
                'text_set': text_set,
                'current_order': problem.order_in_text,
                'next_problem_id': next_problem.id if next_problem else None,
                'prev_problem_id': prev_problem.id if prev_problem else None
            }
        
        # 単語ごとの熟練度を取得（存在しない場合は作成）
        word_proficiency = WordProficiency.query.filter_by(
            student_id=current_user.id,
            problem_id=problem_id
        ).first()
        
        if not word_proficiency:
            word_proficiency = WordProficiency(
                student_id=current_user.id,
                problem_id=problem_id,
                level=0,
                review_date=datetime.now().date()
            )
            db.session.add(word_proficiency)
            db.session.commit()
        
        # 単語の熟練度に応じて問題形式を決定（0-2: 選択式、3-5: 入力式）
        # 修正：カテゴリの熟練度ではなく単語ごとの熟練度に基づく
        is_choice_mode = word_proficiency.level < 3
        
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
            
            # 正解が配列の何番目にあるか確認
            correct_index = all_choices.index(problem.title)
            
            # ダミー選択肢を更新（正解を除外）
            dummy_choices = [choice for choice in all_choices if choice != problem.title]
        
        # セッション関連の確認
        in_session = False
        learning_session = None
        if 'learning_session' in session:
            learning_session = session['learning_session']
            in_session = (learning_session.get('current_problem_id') == problem_id)
        
        # カテゴリ熟練度も取得（表示用）
        category_proficiency = ProficiencyRecord.query.filter_by(
            student_id=current_user.id,
            category_id=problem.category_id
        ).first()
        
        if not category_proficiency:
            # カテゴリの熟練度がなければ更新または作成する
            category_proficiency = update_category_proficiency(current_user.id, problem.category_id)

        return render_template(
            'basebuilder/solve_problem.html',
            problem=problem,
            proficiency_record=category_proficiency,
            word_proficiency=word_proficiency,
            dummy_choices=dummy_choices,
            all_choices=all_choices if is_choice_mode else None,
            correct_index=correct_index if is_choice_mode else None,
            is_choice_mode=is_choice_mode,
            in_session=in_session,
            learning_session=learning_session,
            text_context=text_context
        )
    except Exception as e:
        current_app.logger.error(f"Solve problem error: {str(e)}")
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        # 500.htmlが無い場合はエラーメッセージを返す
        try:
            return render_template('errors/500.html'), 500
        except:
            return f"Internal Server Error: {str(e)}", 500

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
    
    # 単語ごとの熟練度を更新
    word_proficiency = update_word_proficiency(current_user.id, problem_id, is_correct)
    
    # カテゴリの熟練度を更新（単語の熟練度から計算）
    category_proficiency = update_category_proficiency(current_user.id, problem.category_id)
    
    # テキストの定着度も更新（単語の熟練度の平均から）
    text_proficiency = None
    if problem.text_set_id:
        text_proficiency = update_text_proficiency(current_user.id, problem.text_set_id)
    
    db.session.commit()
    
    # セッション情報を更新
    next_url = None
    
    # テキストコンテキストの取得（次の問題への遷移用）
    text_context = None
    if problem.text_set_id:
        # テキスト内の次の問題を取得
        next_problem = BasicKnowledgeItem.query.filter(
            BasicKnowledgeItem.text_set_id == problem.text_set_id,
            BasicKnowledgeItem.order_in_text > problem.order_in_text
        ).order_by(BasicKnowledgeItem.order_in_text).first()
        
        if next_problem:
            next_url = url_for('basebuilder_module.solve_problem', problem_id=next_problem.id)
    
    # 学習セッションの更新
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
            if not next_url:  # テキストの次問題がなければセッションの次問題
                next_url = url_for('basebuilder_module.next_problem')
    
    # AJAXリクエストとフォーム送信を区別して応答
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # AJAXリクエストの場合はJSONを返す
        return jsonify({
            'is_correct': is_correct,
            'correct_answer': problem.title,  # 問題のタイトルを正解として返す
            'explanation': problem.explanation,
            'next_url': next_url,
            'proficiency_level': word_proficiency.level,  # 単語の熟練度を返す
            'category_level': category_proficiency.level if category_proficiency else 0,  # カテゴリの熟練度も
            'text_context': {
                'text_set_id': problem.text_set_id,
                'has_next_problem': next_problem is not None if 'next_problem' in locals() else False
            } if problem.text_set_id else None
        })
    else:
        # 通常のフォーム送信の場合はリダイレクト
        if is_correct:
            flash('正解です！ 単語の定着度が上がりました。')
        else:
            flash(f'不正解です。正解は: {problem.title}')
        
        # テキスト内の次問題、セッション中の次問題、または問題一覧に戻る
        if next_url:
            return redirect(next_url)
        elif problem.text_set_id:
            return redirect(url_for('basebuilder_module.view_text_set', text_id=problem.text_set_id))
        else:
            return redirect(url_for('basebuilder_module.problems'))

# テキスト一覧ページ -> 最初の問題へリダイレクト
@basebuilder_module.route('/text_set/<int:text_id>/solve')
@login_required
def solve_text(text_id):
    if current_user.role != 'student':
        flash('この機能は学生のみ利用可能です。')
        return redirect(url_for('basebuilder_module.index'))
    
    # テキストを取得
    text_set = TextSet.query.get_or_404(text_id)
    
    # 権限チェック（そのテキストが配信されているか）
    enrolled_class_ids = [c.id for c in current_user.enrolled_classes]
    delivery = TextDelivery.query.filter(
        TextDelivery.text_set_id == text_id,
        TextDelivery.class_id.in_(enrolled_class_ids)
    ).first()
    
    if not delivery:
        flash('このテキストにアクセスする権限がありません。')
        return redirect(url_for('basebuilder_module.my_texts'))
    
    # テキスト内の最初の問題を取得
    first_problem = BasicKnowledgeItem.query.filter_by(
        text_set_id=text_id
    ).order_by(BasicKnowledgeItem.order_in_text).first()
    
    if not first_problem:
        flash('このテキストには問題がありません。')
        return redirect(url_for('basebuilder_module.view_text_set', text_id=text_id))
    
    # 問題解答ページにリダイレクト
    return redirect(url_for('basebuilder_module.solve_problem', problem_id=first_problem.id))

# 単語熟練度を更新する関数
def update_word_proficiency(student_id, problem_id, is_correct):
    """
    単語の熟練度を更新する関数
    
    Args:
        student_id: 学生ID
        problem_id: 問題ID
        is_correct: 正解かどうか
        
    Returns:
        更新された熟練度レコード
    """
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
    
    return proficiency

# テキスト熟練度を更新する関数
def update_text_proficiency(student_id, text_set_id):
    """
    テキストセットの定着度を単語の熟練度から計算して更新する
    
    Args:
        student_id: 学生ID
        text_set_id: テキストセットID
        
    Returns:
        更新された熟練度レコード
    """
    # テキストセットを取得
    text_set = TextSet.query.get(text_set_id)
    if not text_set:
        return None
    
    # テキストに含まれる問題を取得
    problems = BasicKnowledgeItem.query.filter_by(
        text_set_id=text_set_id,
        is_active=True
    ).all()
    
    if not problems:
        return None
    
    # 問題IDのリストを作成
    problem_ids = [p.id for p in problems]
    
    # 単語の熟練度レコードを取得
    word_proficiencies = WordProficiency.query.filter(
        WordProficiency.student_id == student_id,
        WordProficiency.problem_id.in_(problem_ids)
    ).all()
    
    # 熟練度マップを作成（検索効率化のため）
    proficiency_map = {wp.problem_id: wp.level for wp in word_proficiencies}
    
    # 各問題の熟練度を集計（存在しない場合は0）
    total_level = 0
    for problem_id in problem_ids:
        total_level += proficiency_map.get(problem_id, 0)
    
    # 最大可能レベル（各問題が熟練度5の場合）
    max_possible_level = len(problems) * 5
    
    # テキスト全体の定着度を計算（0-100%）
    if max_possible_level > 0:
        overall_percentage = (total_level / max_possible_level) * 100
    else:
        overall_percentage = 0
    
    # テキストの定着度レコードを取得または作成
    text_proficiency = TextProficiencyRecord.query.filter_by(
        student_id=student_id,
        text_set_id=text_set_id
    ).first()
    
    if text_proficiency:
        text_proficiency.level = int(overall_percentage)
        text_proficiency.last_updated = datetime.utcnow()
    else:
        text_proficiency = TextProficiencyRecord(
            student_id=student_id,
            text_set_id=text_set_id,
            level=int(overall_percentage)
        )
        db.session.add(text_proficiency)
    
    db.session.commit()
    
    return text_proficiency

# テキスト配信情報を取得するAPI
@basebuilder_module.route('/api/text_set/<int:text_id>/deliveries')
@login_required
def api_text_deliveries(text_id):
    if current_user.role != 'teacher':
        return jsonify({'error': 'この機能は教師のみ利用可能です。'}), 403
    
    # テキストを確認（存在&作成者チェック）
    text_set = TextSet.query.get_or_404(text_id)
    if text_set.created_by != current_user.id:
        return jsonify({'error': 'このテキストの配信情報を取得する権限がありません。'}), 403
    
    # 配信情報を取得
    deliveries = TextDelivery.query.filter_by(text_set_id=text_id).all()
    
    # 配信情報をJSON形式で返す
    delivery_data = []
    for delivery in deliveries:
        # ここでクラス名を取得（Classモデルはdelivered_classリレーションを通して取得可能）
        class_obj = delivery.delivered_class
        
        delivery_data.append({
            'id': delivery.id,
            'class_id': delivery.class_id,
            'class_name': class_obj.name if class_obj else '不明なクラス',
            'delivered_at': delivery.delivered_at.strftime('%Y-%m-%d %H:%M'),
            'due_date': delivery.due_date.strftime('%Y-%m-%d') if delivery.due_date else None
        })
    
    return jsonify({'deliveries': delivery_data})

# テキスト配信解除
@basebuilder_module.route('/text_delivery/<int:delivery_id>/cancel', methods=['POST'])
@login_required
def cancel_text_delivery(delivery_id):
    """テキスト配信を解除する処理"""
    from datetime import datetime  # ローカルでインポート
    print(f"配信解除リクエストを受信: delivery_id={delivery_id}")  # デバッグ用
    
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.text_sets'))
    
    # 配信情報を取得
    delivery = TextDelivery.query.get_or_404(delivery_id)
    print(f"配信情報を取得: {delivery}")  # デバッグ用
    
    # テキストセットを取得（存在&権限チェック）
    text_set = TextSet.query.get_or_404(delivery.text_set_id)
    if text_set.created_by != current_user.id:
        flash('このテキストの配信を解除する権限がありません。')
        return redirect(url_for('basebuilder_module.text_sets'))
    
    # 配信情報のみを削除（解答記録や熟練度は残す）
    text_set_id = delivery.text_set_id
    class_name = "不明なクラス"
    
    if hasattr(delivery, 'delivered_class') and delivery.delivered_class:
        class_name = delivery.delivered_class.name
    
    try:
        print(f"配信を削除: text_set_id={text_set_id}, class_name={class_name}")  # デバッグ用
        
        # 実際に削除する
        db.session.delete(delivery)
        db.session.commit()
        
        flash(f'テキスト「{text_set.title}」の {class_name} への配信を解除しました。生徒の学習記録は保持されています。')
    except Exception as e:
        db.session.rollback()
        print(f"エラー発生: {str(e)}")  # デバッグ用
        flash(f'配信解除中にエラーが発生しました: {str(e)}')
    
    return redirect(url_for('basebuilder_module.text_sets'))

# 単体テキスト削除
@basebuilder_module.route('/text_sets/<int:text_id>/delete', methods=['POST'])
@login_required
def delete_single_text(text_id):
    if current_user.role != 'teacher':
        flash('この機能は教師のみ利用可能です。')
        return redirect(url_for('basebuilder_module.text_sets'))
    
    # テキストを取得（存在&権限チェック）
    text_set = TextSet.query.get_or_404(text_id)
    if text_set.created_by != current_user.id:
        flash('このテキストを削除する権限がありません。')
        return redirect(url_for('basebuilder_module.text_sets'))
    
    try:
        # テキストに含まれる問題を取得
        problems = BasicKnowledgeItem.query.filter_by(text_set_id=text_id).all()
        
        # 各問題に関連する解答記録・熟練度・関連付けを削除
        for problem in problems:
            # 単語の熟練度記録を削除
            WordProficiency.query.filter_by(problem_id=problem.id).delete()
            
            # 解答記録を削除
            AnswerRecord.query.filter_by(problem_id=problem.id).delete()
            
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
        db.session.commit()
        
        flash(f'テキスト「{text_set.title}」を削除しました。')
    except Exception as e:
        db.session.rollback()
        flash(f'テキストの削除中にエラーが発生しました: {str(e)}')
    
    return redirect(url_for('basebuilder_module.text_sets'))
