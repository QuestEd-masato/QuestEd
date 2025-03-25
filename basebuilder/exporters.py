# basebuilder/exporters.py
import csv
import io

def generate_problem_csv_template():
    """
    単語インポート用のCSVテンプレートを生成
    
    Returns:
        str: CSVテンプレート文字列
    """
    # テンプレート用のヘッダーと例を定義
    headers = [
        'title', 'category', 'question', 'answer_type', 'correct_answer',
        'choice_1', 'choice_2', 'choice_3', 'choice_4',
        'explanation', 'difficulty'
    ]
    
    # 例データ - 単語学習向けにカスタマイズ
    examples = [
        {
            'title': 'apple',  # 単語
            'category': '基本英単語',  # カテゴリ
            'question': 'リンゴ（果物）',  # 意味
            'answer_type': 'text',  # 常にtextとして扱う
            'correct_answer': 'アップル',  # 別の表記
            'explanation': '/ˈæpl/ 赤い皮と白い実をもつ果物',  # 発音記号や追加情報
            'difficulty': '1'  # 難易度
        },
        {
            'title': 'computer',
            'category': '基本英単語',
            'question': 'コンピュータ（電子機器）',
            'answer_type': 'text',
            'correct_answer': 'コンピューター',
            'choice_1': 'She uses a computer every day.',  # 例文をchoice欄に格納
            'choice_2': 'This computer is very fast.',
            'choice_3': 'I need to buy a new computer.',
            'explanation': '/kəmˈpjuːtər/ データを処理するための電子機器',
            'difficulty': '2'
        },
        {
            'title': 'beautiful',
            'category': '形容詞',
            'question': '美しい、きれいな',
            'answer_type': 'text',
            'correct_answer': 'ビューティフル',
            'choice_1': 'She is a beautiful woman.',
            'choice_2': 'What a beautiful day!',
            'explanation': '/ˈbjuːtɪfl/ 見た目が非常に良い、魅力的な',
            'difficulty': '2'
        },
        {
            'title': 'psychology',
            'category': '学術用語',
            'question': '心理学',
            'answer_type': 'text',
            'correct_answer': 'サイコロジー',
            'choice_1': 'She is studying psychology at university.',
            'explanation': '/saɪˈkɒlədʒi/ 人間の心理や行動を研究する学問',
            'difficulty': '4'
        },
        {
            'title': 'entrepreneur',
            'category': 'ビジネス用語',
            'question': '起業家、企業家',
            'answer_type': 'text',
            'correct_answer': 'アントレプレナー',
            'explanation': '/ˌɒntrəprəˈnɜːr/ 事業を立ち上げ、運営する人',
            'difficulty': '5'
        }
    ]
    
    # CSVファイルを生成
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    
    for example in examples:
        writer.writerow(example)
    
    return output.getvalue()

def generate_problem_csv_empty_template():
    """
    単語インポート用の空のCSVテンプレートを生成
    
    Returns:
        str: 空のCSVテンプレート文字列
    """
    # テンプレート用のヘッダーを定義
    headers = [
        'title', 'category', 'question', 'answer_type', 'correct_answer',
        'choice_1', 'choice_2', 'choice_3', 'choice_4',
        'explanation', 'difficulty'
    ]
    
    # CSVファイルを生成（ヘッダーのみ）
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    
    return output.getvalue()