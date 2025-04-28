# ai_helpers.py
import os

# モジュールレベルで変数を定義して、エクスポートできるようにする
LEARNING_STEPS = [
    {'id': 'theme', 'name': 'テーマ設定・問い立て'},
    {'id': 'research', 'name': 'リサーチ・情報収集'},
    {'id': 'ideation', 'name': 'アイデア創出・構想'},
    {'id': 'prototype', 'name': 'プロトタイプ作成'},
    {'id': 'presentation', 'name': '発表準備・共有'},
    {'id': 'reflection', 'name': '振り返り・改善'},
    {'id': 'free', 'name': '自由質問'}
]

# 教師用機能の定義（表示されないがコード構造維持のため残しておく）
TEACHER_FUNCTIONS = [
    {'id': 'activity_summary', 'name': '活動記録要約'},
    {'id': 'evaluation', 'name': '評価文生成'},
    {'id': 'curriculum', 'name': 'カリキュラム作成'},
    {'id': 'practice_case', 'name': '実践事例作成'},
    {'id': 'next_activity', 'name': '次回活動提案'}
]

def get_learning_step_prompt(step_id):
    """学習ステップ別プロンプト生成"""
    step_prompts = {
        'theme': """テーマ設定と問いの立て方のサポートをします。
        良いテーマと問いの条件：
        - 具体的で取り組み可能な範囲
        - オープンエンドな問いかけ
        - 自分の興味・関心に基づいている
        - 社会的意義や新規性がある
        この段階での質問にアドバイスします。""",
        
        'research': """情報収集と調査のサポートをします。
        効果的なリサーチの方法：
        - 信頼性の高い情報源の選び方
        - 多角的な視点での情報収集
        - インタビューや現地調査の方法
        - データの整理と分析の基礎
        この段階での質問にアドバイスします。""",
        
        'ideation': """アイデア創出と構想のサポートをします。
        効果的なアイデア創出：
        - ブレインストーミングの方法
        - アイデアの評価と選択
        - ビジネスモデル・解決策の構築
        - 実現可能性の検討
        この段階での質問にアドバイスします。""",
        
        'prototype': """プロトタイプ作成のサポートをします。
        効果的なプロトタイピング：
        - 簡易的な試作品の作り方
        - ユーザーテストの方法
        - フィードバックの集め方と活用法
        - 改良の進め方
        この段階での質問にアドバイスします。""",
        
        'presentation': """発表準備と共有のサポートをします。
        効果的なプレゼンテーション：
        - スライド構成のコツ
        - 説得力のある話し方
        - 質疑応答の準備
        - 聴衆を惹きつける方法
        この段階での質問にアドバイスします。""",
        
        'reflection': """振り返りと改善のサポートをします。
        効果的な振り返り：
        - 学びの整理方法
        - 成果と課題の分析
        - 次のステップの計画
        - 改善点の見つけ方
        この段階での質問にアドバイスします。""",
        
        'free': """自由に質問してください。
        学習の進行や探究活動、アントレプレナーシップに関することなど、
        どんな質問にもお答えします。""",
        
        'teacher_free': """教師向け自由質問モードです。
        探究学習やアントレプレナーシップ教育、授業設計、評価方法など、
        教育活動に関するどのような質問にもお答えします。
        生徒の指導・支援に役立つ情報や助言を提供します。"""
    }
    
    return step_prompts.get(step_id, step_prompts['free'])

def get_teacher_function_prompt(function_id):
    """教師向け機能別プロンプト生成（使用されないが互換性のために維持）"""
    function_prompts = {
        'activity_summary': """以下の活動記録を簡潔に要約し、主なポイント、進捗状況、課題を200字程度でまとめてください。
        要約は客観的な視点で行い、重要なポイントに焦点を当ててください。""",
        
        'evaluation': """以下の生徒の活動記録をもとに、学習指導要領に基づいた100～150字程度の評価文を作成してください。
        評価は以下の観点を含めてください：
        - 課題設定の適切さ
        - 情報収集・整理の能力
        - 思考力・判断力・表現力
        - 主体性・協働性
        生徒の成長が感じられる具体的な評価文にしてください。""",
        
        'curriculum': """以下の情報を基に、探究学習/アントレプレナーシップ教育のカリキュラム案を作成してください。
        カリキュラムには以下の要素を含めてください：
        - 単元の目標
        - 各回の授業内容（10回程度）
        - 評価方法
        - 必要な教材・リソース
        実践的で高校生に適した内容にしてください。""",
        
        'practice_case': """以下の活動内容を基に、教育実践事例として再構成してください。
        実践事例には以下の要素を含めてください：
        - 実践の目的・背景
        - 対象と期間
        - 具体的な活動内容
        - 成果と課題
        - 今後の展望
        他の教育者が参考にできる具体的な内容にしてください。""",
        
        'next_activity': """これまでの活動内容を踏まえ、次回の授業で実施すべき活動案を提案してください。
        活動案には以下の要素を含めてください：
        - 活動の目的
        - 具体的な進め方
        - 必要な準備・教材
        - 期待される成果
        現在の進捗状況に合わせた適切な次のステップを提案してください。"""
    }
    
    return function_prompts.get(function_id, """質問に教育者の視点で回答します。
    探究学習やアントレプレナーシップ教育に関する専門的な助言を提供します。""")

def generate_system_prompt(user, step_id=None, function_id=None, context=None):
    """ユーザータイプとコンテキストに基づいたシステムプロンプトを生成"""
    
    base_prompt = ""
    
    if user.role == 'student':
        # 学生の場合
        theme_text = ""
        if context and 'theme' in context and context['theme']:
            theme = context['theme']
            theme_text = f"\n選択中のテーマ: {theme.title}\n探究の問い: {theme.question}" 
        
        base_prompt = f"あなたは探究学習の支援AIアシスタントです。高校生の探究活動とアントレプレナーシップ教育をサポートします。{theme_text}"
        
        # 学習ステップが指定されている場合、そのステップの詳細プロンプトを追加
        if step_id:
            base_prompt += f"\n\n{get_learning_step_prompt(step_id)}"
    
    else:
        # 教師の場合 - 常に自由記述モードを使用
        base_prompt = "あなたは教育支援AIアシスタントです。教員の探究学習指導とアントレプレナーシップ教育をサポートします。"
        
        # 教師用の自由記述プロンプトを追加
        base_prompt += f"\n\n{get_learning_step_prompt('teacher_free')}"
    
    # 共通の安全性ガイドラインを追加
    safety_guidelines = """
    以下の点に注意してください：
    - 教育的で適切な言葉遣いで回答する
    - 事実と意見を区別し、偏りのない情報を提供する
    - 具体的かつ実践的なアドバイスを提供する
    - 必要に応じて例を示して説明する
    """
    
    return base_prompt + safety_guidelines

def call_openai_api(messages, api_key=None, model="gpt-4", temperature=0.7, max_tokens=None, timeout=30):
    """
    OpenAI APIを呼び出し、応答を取得する関数
    両方のAPIバージョンをサポート
    
    Args:
        messages (list): 会話メッセージのリスト
        api_key (str, optional): OpenAI APIキー。Noneの場合は環境変数から取得
        model (str, optional): 使用するモデル名。デフォルトは"gpt-4"
        temperature (float, optional): 応答の多様性。0.0〜1.0の範囲。デフォルトは0.7
        max_tokens (int, optional): 最大トークン数。Noneの場合は制限なし
        timeout (int, optional): リクエストのタイムアウト時間（秒）
        
    Returns:
        str: AIからの応答テキスト
        
    Raises:
        Exception: API呼び出し中にエラーが発生した場合
    """
    try:
        # APIキーの取得
        api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not api_key:
            return "APIキーが設定されていません。管理者に連絡してください。"
        
        # 新しいAPIスタイルを試す
        try:
            from openai import OpenAI
            # クライアントの初期化
            client = OpenAI(api_key=api_key, timeout=timeout)
            
            # パラメータの準備
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature
            }
            
            # max_tokensが指定されている場合のみ追加
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
            
            # APIリクエスト送信
            response = client.chat.completions.create(**params)
            
            # 応答の取得
            return response.choices[0].message.content
            
        except (ImportError, AttributeError):
            # 古いAPIスタイルにフォールバック
            import openai
            openai.api_key = api_key
            
            # パラメータの準備
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature
            }
            
            # max_tokensが指定されている場合のみ追加
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
            
            # APIリクエスト送信
            response = openai.ChatCompletion.create(**params)
            
            # 応答の取得
            return response.choices[0].message['content']
    
    except Exception as e:
        # エラーをログに記録
        error_msg = f"OpenAI API エラー: {str(e)}"
        print(error_msg)
        
        # エラーの種類に応じたユーザーフレンドリーなメッセージを返す
        if "timeout" in str(e).lower():
            return "リクエストがタイムアウトしました。後でもう一度お試しください。"
        elif "rate limit" in str(e).lower():
            return "APIの呼び出し制限に達しました。しばらくしてからもう一度お試しください。"
        elif "invalid api key" in str(e).lower():
            return "APIキーが無効です。管理者に連絡してください。"
        else:
            return f"エラーが発生しました: {str(e)}"