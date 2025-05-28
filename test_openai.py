# test_openai.py
import os
from dotenv import load_dotenv

# 環境変数を読み込む
load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')
print(f"APIキー: {api_key[:5]}...{api_key[-4:] if api_key else 'なし'}")

# 両方のインポート方式をサポート
try:
    # 新しいAPI形式を試す
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    
    # APIテスト
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたは教育支援AIアシスタントです。"},
                {"role": "user", "content": "こんにちは"}
            ]
        )
        print("APIレスポンス成功:")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"新しいAPIスタイルでのエラー: {str(e)}")
        raise  # エラーを再発生させて古いAPIスタイルも試せるようにする
        
except (ImportError, AttributeError):
    # 古いAPI形式にフォールバック
    import openai
    openai.api_key = api_key
    
    # APIテスト
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたは教育支援AIアシスタントです。"},
                {"role": "user", "content": "こんにちは"}
            ]
        )
        print("APIレスポンス成功:")
        print(response.choices[0].message['content'])
    except Exception as e:
        print(f"古いAPIスタイルでのエラー: {str(e)}")