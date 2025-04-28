# ai_curriculum_helpers.py
import os
import json
import csv
import io

def generate_curriculum_with_ai(class_details, curriculum_settings):
    """
    AIを使用してカリキュラムを生成する
    両方のAPIバージョンをサポート
    
    Args:
        class_details: クラスに関する情報（名前、大テーマなど）
        curriculum_settings: カリキュラム設定（時間数、フィールドワーク有無など）
        
    Returns:
        dict: カリキュラム内容
    """
    # システムプロンプトの構築
    system_prompt = """
    あなたは探究学習のカリキュラム設計専門AIアシスタントです。
    教師が入力した条件に基づいて、クラスの大テーマに沿った探究学習カリキュラムを作成してください。
    
    カリキュラムは以下の点を考慮して設計してください：
    1. 探究のプロセス（問いの設定→情報収集→整理・分析→まとめ・表現）を意識した流れ
    2. 生徒の主体性を引き出す活動設計
    3. 指定された時間数内で実現可能な計画
    4. フィールドワークや発表会などの特別活動の適切な配置
    5. 評価方法として活動記録とルーブリック評価を基本とする
    
    出力はJSON形式で、以下の構造で提供してください：
    {
      "phases": [
        {
          "phase": "フェーズ名（例：準備期、探究前半、探究後半、まとめ）",
          "weeks": [
            {
              "week": "第X週",
              "hours": 時間数,
              "theme": "この週のテーマ",
              "activities": "具体的な活動内容",
              "teacher_support": "教師のサポート内容",
              "evaluation": "評価方法や観点"
            }
          ]
        }
      ],
      "rubric_suggestion": [
        {
          "category": "評価カテゴリ（例：問いの設定、情報収集、分析力）",
          "description": "このカテゴリの説明",
          "levels": [
            {
              "level": "S/A/B/C などの評価レベル",
              "description": "このレベルの達成基準"
            }
          ]
        }
      ]
    }
    """
    
    # ユーザープロンプトの構築
    user_prompt = f"""
    【クラス情報】
    クラス名：{class_details['name']}
    大テーマ：{class_details['main_theme']}
    大テーマの説明：{class_details['main_theme_description']}
    
    【カリキュラム設定】
    総時間数：{curriculum_settings['total_hours']}時間
    フィールドワーク：{'あり（' + str(curriculum_settings['fieldwork_count']) + '回）' if curriculum_settings['has_fieldwork'] else 'なし'}
    発表会：{'あり（形式：' + curriculum_settings['presentation_format'] + '）' if curriculum_settings['has_presentation'] else 'なし'}
    グループ活動の度合い：{curriculum_settings['group_work_level']}
    外部連携：{'あり' if curriculum_settings['external_collaboration'] else 'なし'}
    
    以上の条件に基づいて、年間の探究学習カリキュラムを作成してください。
    """
    
    try:
        # APIキーの取得
        api_key = os.getenv('OPENAI_API_KEY')
        
        # 新しいAPIスタイルを試す
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            # OpenAI APIを呼び出す
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=3000
            )
            
            # APIレスポンスからカリキュラム内容を抽出
            content = response.choices[0].message.content
            
        except (ImportError, AttributeError):
            # 古いAPIスタイルにフォールバック
            import openai
            openai.api_key = api_key
            
            # OpenAI APIを呼び出す
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=3000
            )
            
            # APIレスポンスからカリキュラム内容を抽出
            content = response.choices[0].message['content']
        
        # JSONとして解析
        try:
            # 直接JSONとして解析を試みる
            curriculum_data = json.loads(content)
        except json.JSONDecodeError:
            # JSON部分を抽出して解析
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                curriculum_data = json.loads(json_str)
            else:
                # JSONが見つからない場合、テキスト全体をJSONとして解析を再試行
                import re
                json_pattern = r'{[\s\S]*}'
                match = re.search(json_pattern, content)
                if match:
                    json_str = match.group(0)
                    curriculum_data = json.loads(json_str)
                else:
                    raise ValueError("JSONデータを抽出できませんでした")
        
        return curriculum_data
        
    except Exception as e:
        print(f"カリキュラム生成エラー: {str(e)}")
        # エラー時は基本的なテンプレートを返す
        return {
            "phases": [
                {
                    "phase": "準備期",
                    "weeks": [
                        {
                            "week": "第1週",
                            "hours": 2,
                            "theme": "オリエンテーション",
                            "activities": "探究学習の概要説明、大テーマの理解",
                            "teacher_support": "探究学習の意義と進め方を説明",
                            "evaluation": "活動記録の確認"
                        }
                    ]
                }
            ],
            "rubric_suggestion": [
                {
                    "category": "問いの設定",
                    "description": "探究の問いを設定する力",
                    "levels": [
                        {
                            "level": "S",
                            "description": "独創的で深い問いを設定できる"
                        },
                        {
                            "level": "A",
                            "description": "適切な問いを設定できる"
                        },
                        {
                            "level": "B",
                            "description": "基本的な問いを設定できる"
                        },
                        {
                            "level": "C",
                            "description": "問いの設定が不十分"
                        }
                    ]
                }
            ]
        }

def generate_curriculum_csv(curriculum_data):
    """
    カリキュラムデータをCSV形式に変換する
    
    Args:
        curriculum_data: JSON形式のカリキュラムデータ
        
    Returns:
        str: CSV形式のカリキュラムデータ
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator='\n') # 改行コードを明示的に指定
    
    # ヘッダー行
    writer.writerow(['フェーズ', '週', '時間数', 'テーマ', '活動内容', '教師のサポート', '評価方法'])
    
    # カリキュラムデータの書き込み
    for phase in curriculum_data.get('phases', []):
        phase_name = phase.get('phase', '')
        for week in phase.get('weeks', []):
            writer.writerow([
                phase_name,
                week.get('week', ''),
                week.get('hours', ''),
                week.get('theme', ''),
                week.get('activities', ''),
                week.get('teacher_support', ''),
                week.get('evaluation', '')
            ])
    
    # ルーブリックデータのための区切り
    writer.writerow([])
    writer.writerow(['ルーブリック評価項目'])
    writer.writerow(['カテゴリ', '説明', 'レベル', '達成基準'])
    
    # ルーブリックデータの書き込み
    for rubric in curriculum_data.get('rubric_suggestion', []):
        category = rubric.get('category', '')
        description = rubric.get('description', '')
        for level in rubric.get('levels', []):
            writer.writerow([
                category,
                description,
                level.get('level', ''),
                level.get('description', '')
            ])
    
    return output.getvalue()