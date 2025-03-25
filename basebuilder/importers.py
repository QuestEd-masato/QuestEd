# basebuilder/importers.py
import csv
import json
from io import StringIO
from datetime import datetime, timedelta, date

def validate_problem_csv(csv_content, current_user_id):
    """
    問題CSVデータを検証し、有効なデータと問題点を返す
    (単語インポート機能に置き換え)

    Args:
        csv_content: CSVファイルの内容（文字列）
        current_user_id: インポート実行ユーザーのID
        
    Returns:
        tuple: (valid_problems, errors)
            - valid_problems: 有効な問題データのリスト
            - errors: 検出されたエラーのリスト
    """
    valid_problems = []
    errors = []
    line_count = 0
    
    try:
        # CSVを読み込む
        csv_file = StringIO(csv_content)
        reader = csv.DictReader(csv_file)
        
        # 必須ヘッダーの確認
        required_headers = ['title', 'category', 'question', 'answer_type', 'correct_answer']
        headers = reader.fieldnames
        
        if not headers:
            return [], ["CSVファイルが空であるか、ヘッダーが見つかりません。"]
        
        for header in required_headers:
            if header not in headers:
                return [], [f"必須ヘッダー '{header}' がCSVファイルに見つかりません。"]
        
        # 各行を処理
        for row in reader:
            line_count += 1
            
            # 空行をスキップ
            if not any(row.values()):
                continue
            
            # 必須フィールドの検証
            row_errors = []
            for field in required_headers:
                if not row.get(field):
                    row_errors.append(f"{field} は必須項目です。")
            
            # answer_typeの検証
            answer_type = row.get('answer_type', '').strip().lower()
            if answer_type not in ['multiple_choice', 'text', 'true_false']:
                row_errors.append("answer_type は 'multiple_choice', 'text', 'true_false' のいずれかである必要があります。")
            
            # 選択肢の検証（multiple_choiceの場合）
            choices = []
            if answer_type == 'multiple_choice':
                # 選択肢カラムの取得（choices_1, choices_2, ...）
                choice_columns = [key for key in row.keys() if key.startswith('choice_')]
                
                if not choice_columns:
                    row_errors.append("選択問題には少なくとも1つの選択肢（choice_1, choice_2, ...）が必要です。")
                else:
                    # 選択肢をJSONに変換
                    for i, col in enumerate(sorted(choice_columns)):
                        choice_text = row.get(col, '').strip()
                        if choice_text:
                            is_correct = (row.get('correct_answer', '').strip() == col or 
                                          row.get('correct_answer', '').strip() == choice_text)
                            choices.append({
                                'id': f'choice_{i}',
                                'text': choice_text,
                                'value': f'choice_{i}',
                                'isCorrect': is_correct
                            })
                
                if not any(choice.get('isCorrect') for choice in choices):
                    row_errors.append("正解となる選択肢が指定されていません。correct_answerは選択肢のIDまたはテキストと一致する必要があります。")
            
            # 難易度の検証
            difficulty = 2  # デフォルト値
            if 'difficulty' in row and row['difficulty']:
                try:
                    difficulty = int(row['difficulty'])
                    if difficulty < 1 or difficulty > 5:
                        row_errors.append("難易度は1〜5の整数である必要があります。")
                except ValueError:
                    row_errors.append("難易度は整数値である必要があります。")
            
            # エラーがある場合はスキップ
            if row_errors:
                errors.append(f"行 {line_count}: " + ", ".join(row_errors))
                continue
            
            # 有効なデータを追加
            problem_data = {
                'title': row['title'].strip(),
                'category': row['category'].strip(),
                'question': row['question'].strip(),
                'answer_type': answer_type,
                'correct_answer': row['correct_answer'].strip(),
                'explanation': row.get('explanation', '').strip(),
                'difficulty': difficulty,
                'created_by': current_user_id,
                'choices': json.dumps(choices) if choices else None
            }
            
            valid_problems.append(problem_data)
        
        if not valid_problems and not errors:
            errors.append("有効な問題データが見つかりませんでした。")
            
        return valid_problems, errors
    
    except Exception as e:
        return [], [f"CSVファイル処理中にエラーが発生しました: {str(e)}"]

def import_problems_from_csv(csv_content, db, ProblemCategory, BasicKnowledgeItem, current_user_id):
    """
    CSVファイルから問題をインポートする
    
    Args:
        csv_content: CSVファイルの内容（文字列）
        db: SQLAlchemyのdbオブジェクト
        ProblemCategory: ProblemCategoryモデルクラス
        BasicKnowledgeItem: BasicKnowledgeItemモデルクラス
        current_user_id: インポート実行ユーザーのID
        
    Returns:
        tuple: (success_count, error_count, errors)
            - success_count: 正常にインポートされた問題数
            - error_count: エラーのあった問題数
            - errors: エラーメッセージのリスト
    """
    # CSVデータの検証
    valid_problems, errors = validate_problem_csv(csv_content, current_user_id)
    
    success_count = 0
    error_count = len(errors)
    
    # 有効なデータがない場合は終了
    if not valid_problems:
        return success_count, error_count, errors
    
    # カテゴリのキャッシュを作成
    categories = {}
    for category_obj in ProblemCategory.query.all():
        categories[category_obj.name.lower()] = category_obj
    
    # 各問題をデータベースに追加
    for problem in valid_problems:
        try:
            # カテゴリを検索または作成
            category_name = problem['category']
            category_key = category_name.lower()
            
            if category_key in categories:
                category = categories[category_key]
            else:
                # 新しいカテゴリを作成
                category = ProblemCategory(
                    name=category_name,
                    created_by=current_user_id
                )
                db.session.add(category)
                db.session.flush()  # IDを取得するためにフラッシュ
                categories[category_key] = category
            
            # 問題の作成
            new_problem = BasicKnowledgeItem(
                category_id=category.id,
                title=problem['title'],
                question=problem['question'],
                answer_type=problem['answer_type'],
                correct_answer=problem['correct_answer'],
                explanation=problem['explanation'],
                difficulty=problem['difficulty'],
                choices=problem['choices'],
                created_by=current_user_id
            )
            
            db.session.add(new_problem)
            success_count += 1
            
        except Exception as e:
            errors.append(f"問題 '{problem['title']}' のインポート中にエラーが発生しました: {str(e)}")
            error_count += 1
    
    # 変更をコミット
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        errors.append(f"データベースへの保存中にエラーが発生しました: {str(e)}")
        return 0, len(valid_problems), errors
    
    return success_count, error_count, errors

def import_text_from_csv(csv_content, title, description, category_id, db, TextSet, BasicKnowledgeItem, current_user_id):
    """
    CSVファイルから問題をインポートし、テキストセットとして保存する
    
    Args:
        csv_content: CSVファイルの内容（文字列）
        title: テキストセットのタイトル
        description: テキストセットの説明
        category_id: カテゴリID
        db: SQLAlchemyのdbオブジェクト
        TextSet: TextSetモデルクラス
        BasicKnowledgeItem: BasicKnowledgeItemモデルクラス
        current_user_id: インポート実行ユーザーのID
        
    Returns:
        tuple: (success_count, error_count, errors)
    """
    # CSVデータの検証
    valid_problems, errors = validate_problem_csv(csv_content, current_user_id)
    
    success_count = 0
    error_count = len(errors)
    
    # 有効なデータがない場合は終了
    if not valid_problems:
        return success_count, error_count, errors
    
    try:
        # 新しいテキストセットを作成
        new_text_set = TextSet(
            title=title,
            description=description,
            category_id=category_id,
            created_by=current_user_id
        )
        db.session.add(new_text_set)
        db.session.flush()  # IDを取得するためにフラッシュ
        
        # 各問題をテキストセットに追加
        for i, problem_data in enumerate(valid_problems):
            try:
                # 問題の作成
                new_problem = BasicKnowledgeItem(
                    category_id=category_id,
                    title=problem_data['title'],
                    question=problem_data['question'],
                    answer_type=problem_data['answer_type'],
                    correct_answer=problem_data['correct_answer'],
                    explanation=problem_data.get('explanation', ''),
                    difficulty=problem_data.get('difficulty', 2),
                    choices=problem_data.get('choices'),
                    created_by=current_user_id,
                    text_set_id=new_text_set.id,
                    order_in_text=i+1
                )
                
                db.session.add(new_problem)
                success_count += 1
                
            except Exception as e:
                errors.append(f"問題 '{problem_data['title']}' の追加中にエラーが発生しました: {str(e)}")
                error_count += 1
        
        # 変更をコミット
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        errors.append(f"テキストセットの作成中にエラーが発生しました: {str(e)}")
        return 0, len(valid_problems), errors
    
    return success_count, error_count, errors