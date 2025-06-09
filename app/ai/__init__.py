# app/ai/__init__.py
from flask import Blueprint
import os
import re
import json
import logging
from datetime import datetime

# OpenAIクライアントの初期化
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
except ImportError:
    # 古いバージョンのOpenAI
    import openai
    openai.api_key = os.getenv('OPENAI_API_KEY')
    client = None

ai_bp = Blueprint('ai', __name__)

# ヘルパーモジュールからインポート
try:
    from .helpers import (
        LEARNING_STEPS, TEACHER_FUNCTIONS, 
        get_learning_step_prompt, get_teacher_function_prompt,
        generate_system_prompt, call_openai_api
    )
except ImportError:
    # ヘルパーが見つからない場合のデフォルト
    LEARNING_STEPS = []
    TEACHER_FUNCTIONS = []
    def get_learning_step_prompt(step_id): return ""
    def get_teacher_function_prompt(func_id): return ""
    def generate_system_prompt(*args, **kwargs): return ""
    def call_openai_api(*args, **kwargs): return ""

def generate_student_evaluation(student, theme, goals, activity_logs, curriculum_data, rubric_data):
    """
    OpenAI APIを使用して学生の評価を生成する
    
    Args:
        student: 学生のUserオブジェクト
        theme: 選択中の探究テーマ
        goals: 設定された目標のリスト
        activity_logs: 学習記録のリスト
        curriculum_data: カリキュラムデータ
        rubric_data: ルーブリックデータ
        
    Returns:
        生成された評価文字列
    """
    # プロンプトの作成
    prompt = f"以下の情報に基づいて、学生 {student.username} の探究学習の評価を100〜150文字で生成してください。\n\n"
    
    # テーマ情報の追加
    if theme:
        prompt += f"【探究テーマ】\n"
        prompt += f"タイトル: {theme.title}\n"
        prompt += f"探究の問い: {theme.question}\n"
        if theme.description:
            prompt += f"説明: {theme.description}\n"
    else:
        prompt += "【探究テーマ】\n探究テーマは未選択です。\n"
    
    # 目標情報の追加
    prompt += "\n【設定された目標】\n"
    if goals:
        for goal in goals:
            prompt += f"- {goal.title}: 進捗 {goal.progress}%"
            if goal.is_completed:
                prompt += " (完了)"
            prompt += "\n"
    else:
        prompt += "設定された目標はありません。\n"
    
    # 学習記録の追加
    prompt += "\n【最近の学習記録】\n"
    if activity_logs:
        for log in activity_logs[:5]:  # 最新5件まで
            prompt += f"- {log.date.strftime('%Y-%m-%d')} {log.title if log.title else '（タイトルなし）'}\n"
            if log.content:
                prompt += f"  {log.content[:100]}{'...' if len(log.content) > 100 else ''}\n"
    else:
        prompt += "学習記録はありません。\n"
    
    # ルーブリック情報の追加
    if rubric_data:
        prompt += "\n【評価ルーブリック】\n"
        if isinstance(rubric_data, list):
            for rubric in rubric_data:
                if isinstance(rubric, dict):
                    prompt += f"- {rubric.get('category', '不明')}: {rubric.get('description', '')}\n"
    
    # 指示の追加
    prompt += "\n以下の点を考慮した評価を生成してください：\n"
    prompt += "1. 探究テーマへの取り組み方や深さ\n"
    prompt += "2. 目標達成に向けての進捗\n"
    prompt += "3. 学習記録の内容と質\n"
    prompt += "4. 今後の改善点や期待\n\n"
    prompt += "評価は100〜150字程度に収め、客観的かつ建設的な内容にしてください。"
    
    try:
        # OpenAI APIの呼び出し
        if client:
            # 新しいAPI
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたは教師として、探究学習における生徒の評価を行います。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            evaluation = response.choices[0].message.content.strip()
        else:
            # 古いAPI
            import openai
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたは教師として、探究学習における生徒の評価を行います。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            evaluation = response.choices[0].message['content'].strip()
        
        return evaluation
        
    except Exception as e:
        logging.error(f"評価生成エラー: {str(e)}")
        return "評価の生成中にエラーが発生しました。"

def generate_personal_themes_with_ai(main_theme, interest_responses, personality_responses):
    """
    OpenAI APIを使用して、大テーマと学生のアンケート回答に基づく個人テーマを生成する
    
    Args:
        main_theme: 大テーマのオブジェクト
        interest_responses: 興味関心アンケートの回答
        personality_responses: 思考特性アンケートの回答
        
    Returns:
        生成されたテーマのリスト（辞書形式）
    """
    # システムプロンプトの構築
    system_prompt = """
    あなたは教育AIアシスタントで、高校生の探究学習テーマ提案を担当しています。
    生徒の興味関心と思考特性に合わせて、与えられた大テーマに即した個人テーマを3つ提案してください。
    提案するテーマは、高校生が1年間かけて取り組むのに適切な範囲と難易度にしてください。
    
    各テーマには以下の要素を含めてください：
    1. タイトル（簡潔かつ具体的に）
    2. 探究の問い（具体的でオープンエンドな問いかけ）
    3. テーマの概要説明（100字程度）
    4. 選定理由（この生徒に合っている理由）
    5. アプローチ方法（調査や実験の進め方のアドバイス）
    6. 発展可能性（深掘りできる方向性）
    
    重要：提案するテーマは必ず大テーマの範囲内に収まるようにしてください。
    """

    # ユーザープロンプトの構築
    user_prompt = f"""
    【大テーマ】
    タイトル：{main_theme.title}
    説明：{main_theme.description}
    
    【生徒の興味関心アンケート回答】
    {format_survey_responses(interest_responses)}
    
    【生徒の思考特性アンケート回答】
    {format_survey_responses(personality_responses)}
    
    この生徒に合った、大テーマに即した個人テーマを3つ提案してください。
    回答はJSON形式で返してください：
    
    [
      {{
        "title": "テーマタイトル",
        "question": "探究の問い",
        "description": "テーマの概要説明", 
        "rationale": "選定理由",
        "approach": "アプローチ方法",
        "potential": "発展可能性"
      }},
      ...
    ]
    """
    
    try:
        if client:
            # 新しいAPI
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.9,
                max_tokens=1500
            )
            content = response.choices[0].message.content
        else:
            # 古いAPI
            import openai
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.9,
                max_tokens=1500
            )
            content = response.choices[0].message['content']
        
        # JSON部分を抽出（テキスト中からJSONを見つける）
        json_match = re.search(r'\[\s*{.*}\s*\]', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            themes = json.loads(json_str)
        else:
            # JSONの抽出に失敗した場合、全体をJSONとして解析
            themes = json.loads(content)
        
        return themes
        
    except Exception as e:
        logging.error(f"Error generating themes: {str(e)}")
        # エラー時はダミーテーマを返す
        return [
            {
                "title": "大テーマに関連する個人テーマ例",
                "question": f"{main_theme.title}に関して、どのような方法で探究できるか？",
                "description": f"{main_theme.title}に関連する個人的な探究テーマ。", 
                "rationale": "あなたの興味と関心に基づいています。",
                "approach": "文献調査と実地調査を組み合わせて進めるとよいでしょう。",
                "potential": "さらに専門的な視点や実践的な応用に発展させることができます。"
            }
        ]

def generate_curriculum_with_ai(data):
    """
    OpenAI APIを使用してカリキュラムを生成する
    
    Args:
        data: カリキュラム生成に必要な情報を含む辞書
        
    Returns:
        生成されたカリキュラムの内容（辞書形式）
    """
    # システムプロンプト
    system_prompt = """
    あなたは探究学習カリキュラムの専門家です。
    高校生向けの探究学習カリキュラムを作成してください。
    カリキュラムは実践的で、生徒の主体的な学習を促進するものにしてください。
    """
    
    # ユーザープロンプト
    user_prompt = f"""
    以下の条件で探究学習カリキュラムを作成してください：
    
    【基本情報】
    - タイトル: {data.get('title', '探究学習')}
    - 説明: {data.get('description', '')}
    - 総時間数: {data.get('total_hours', 35)}時間
    - メインテーマ: {data.get('main_theme', '未設定')}
    
    【活動設定】
    - フィールドワーク: {'あり' if data.get('has_fieldwork') else 'なし'}
    - フィールドワーク回数: {data.get('fieldwork_count', 0)}回
    - 最終発表: {'あり' if data.get('has_presentation') else 'なし'}
    - 発表形式: {data.get('presentation_format', 'プレゼンテーション')}
    - グループワーク: {data.get('group_work_level', 'ハイブリッド')}
    - 外部連携: {'あり' if data.get('external_collaboration') else 'なし'}
    
    以下の形式でカリキュラムを作成してください：
    {{
        "overview": "カリキュラムの概要（200字程度）",
        "objectives": ["学習目標1", "学習目標2", ...],
        "schedule": [
            {{
                "phase": "フェーズ名",
                "duration": "期間（週数）",
                "activities": ["活動1", "活動2", ...],
                "milestones": ["マイルストーン1", ...]
            }},
            ...
        ],
        "assessment": {{
            "methods": ["評価方法1", "評価方法2", ...],
            "criteria": ["評価基準1", "評価基準2", ...]
        }},
        "resources": ["必要なリソース1", "必要なリソース2", ...]
    }}
    """
    
    try:
        if client:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,
                max_tokens=2000
            )
            content = response.choices[0].message.content
        else:
            import openai
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,
                max_tokens=2000
            )
            content = response.choices[0].message['content']
        
        # JSON部分を抽出
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            curriculum = json.loads(json_str)
        else:
            curriculum = json.loads(content)
        
        return curriculum
        
    except Exception as e:
        logging.error(f"カリキュラム生成エラー: {str(e)}")
        # エラー時のデフォルトカリキュラム
        return {
            "overview": "探究学習を通じて、生徒が主体的に課題を発見し、解決する力を育成します。",
            "objectives": [
                "課題発見・設定能力の育成",
                "情報収集・分析能力の向上",
                "プレゼンテーション能力の開発"
            ],
            "schedule": [
                {
                    "phase": "導入期",
                    "duration": "4週間",
                    "activities": ["オリエンテーション", "テーマ探索"],
                    "milestones": ["テーマ決定"]
                },
                {
                    "phase": "探究期",
                    "duration": "20週間",
                    "activities": ["調査活動", "実験・観察", "データ分析"],
                    "milestones": ["中間発表", "最終レポート提出"]
                },
                {
                    "phase": "まとめ期",
                    "duration": "4週間",
                    "activities": ["成果整理", "発表準備"],
                    "milestones": ["最終発表"]
                }
            ],
            "assessment": {
                "methods": ["ポートフォリオ評価", "プレゼンテーション評価", "レポート評価"],
                "criteria": ["探究プロセスの適切性", "成果の独創性", "表現力"]
            },
            "resources": ["図書館", "インターネット環境", "実験機材"]
        }

def format_survey_responses(responses):
    """
    アンケート回答を整形して文字列として返す
    
    Args:
        responses: アンケート回答の辞書
        
    Returns:
        整形された回答文字列
    """
    if not responses:
        return "回答なし"
    
    formatted = []
    for key, value in responses.items():
        if isinstance(value, list):
            value = ", ".join(value)
        formatted.append(f"- {key}: {value}")
    
    return "\n".join(formatted)

def generate_chat_response(message, context=None, subject=None):
    """
    チャットメッセージに対するAI応答を生成
    
    Args:
        message: ユーザーからのメッセージ
        context: 会話のコンテキスト（オプション）
        subject: Subjectモデルのインスタンス（教科情報）
        
    Returns:
        AIの応答テキスト
    """
    # 基本のシステムプロンプト
    system_prompt = """
    あなたは教育支援AIアシスタントです。
    生徒や教師の質問に対して、親切で分かりやすく回答してください。
    探究学習、学習計画、学習方法などについてアドバイスを提供できます。
    """
    
    # 教科別プロンプトが設定されている場合は追加
    if subject and subject.ai_system_prompt:
        system_prompt = f"{system_prompt}\n\n【教科特性】\n{subject.ai_system_prompt}"
        
        # 教科の学習目標があれば追加
        if subject.learning_objectives:
            system_prompt += f"\n\n【学習目標】\n{subject.learning_objectives}"
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # コンテキストがある場合は追加
    if context:
        for ctx in context[-5:]:  # 最新5件のコンテキストのみ使用
            messages.append({
                "role": "user" if ctx.get('is_user') else "assistant",
                "content": ctx.get('message', '')
            })
    
    messages.append({"role": "user", "content": message})
    
    try:
        if client:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.8,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        else:
            import openai
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.8,
                max_tokens=500
            )
            return response.choices[0].message['content'].strip()
        
    except Exception as e:
        logging.error(f"チャット応答生成エラー: {str(e)}")
        return "申し訳ございません。現在、応答を生成できません。しばらくしてからもう一度お試しください。"

# エクスポート
__all__ = [
    'ai_bp',
    'generate_student_evaluation',
    'generate_personal_themes_with_ai',
    'generate_curriculum_with_ai',
    'format_survey_responses',
    'generate_chat_response',
    'LEARNING_STEPS',
    'TEACHER_FUNCTIONS',
    'generate_system_prompt',
    'call_openai_api'
]