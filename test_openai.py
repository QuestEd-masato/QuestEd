# test_openai.py として保存
import os
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数を読み込む
load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')
print(f"APIキー: {api_key[:5]}...{api_key[-4:] if api_key else 'なし'}")

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
    print(f"APIエラー: {str(e)}")