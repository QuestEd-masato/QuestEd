# basebuilder/exporters.py
import csv
import io

def generate_problem_csv_template():
    """
    問題インポート用のCSVテンプレートを生成
    
    Returns:
        str: CSVテンプレート文字列
    """
    # テンプレート用のヘッダーと例を定義
    headers = [
        'title', 'category', 'question', 'answer_type', 'correct_answer',
        'choice_1', 'choice_2', 'choice_3', 'choice_4',
        'explanation', 'difficulty'
    ]
    
    # 例データ
    examples = [
        {
            'title': '江戸幕府の開始年',
            'category': '日本史',
            'question': '江戸幕府が始まったのは西暦何年か？',
            'answer_type': 'text',
            'correct_answer': '1603',
            'explanation': '徳川家康が征夷大将軍に任命され、江戸幕府を開いたのは1603年です。',
            'difficulty': '2'
        },
        {
            'title': '二酸化炭素の化学式',
            'category': '化学',
            'question': '二酸化炭素の化学式は何か？',
            'answer_type': 'multiple_choice',
            'correct_answer': 'choice_1',
            'choice_1': 'CO2',
            'choice_2': 'H2O',
            'choice_3': 'O2',
            'choice_4': 'CH4',
            'explanation': '二酸化炭素の化学式はCO2（炭素原子1つと酸素原子2つ）です。',
            'difficulty': '1'
        },
        {
            'title': 'ピタゴラスの定理',
            'category': '数学',
            'question': '直角三角形において、a²+b²=c²は正しいか？（aとbは直角をはさむ2辺、cは斜辺）',
            'answer_type': 'true_false',
            'correct_answer': 'true',
            'explanation': 'ピタゴラスの定理により、直角三角形の直角をはさむ2辺の長さの平方和は、斜辺の長さの平方に等しい。',
            'difficulty': '3'
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
    問題インポート用の空のCSVテンプレートを生成
    
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