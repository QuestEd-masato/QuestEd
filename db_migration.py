"""
このスクリプトは既存のデータベースにresponsesカラムを追加します。
Flask-Migrateを使用している場合は、代わりにマイグレーションツールを使用してください。
"""
import os
import sys
import pymysql
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# データベース接続情報
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')

def add_responses_column():
    """interest_surveysテーブルとpersonality_surveysテーブルにresponsesカラムを追加"""
    try:
        # MySQLデータベースに接続
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USERNAME,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        
        with connection.cursor() as cursor:
            # カラムが存在するか確認して、なければ追加
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'interest_surveys' 
                AND column_name = 'responses'
                AND table_schema = %s
            """, (DB_NAME,))
            
            if cursor.fetchone()[0] == 0:
                print("interest_surveysテーブルにresponsesカラムを追加しています...")
                cursor.execute("""
                    ALTER TABLE interest_surveys 
                    ADD COLUMN responses TEXT
                """)
                print("interest_surveysテーブルにresponsesカラムを追加しました。")
            else:
                print("interest_surveysテーブルにはすでにresponsesカラムが存在します。")
            
            # personality_surveysテーブルも確認
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'personality_surveys' 
                AND column_name = 'responses'
                AND table_schema = %s
            """, (DB_NAME,))
            
            if cursor.fetchone()[0] == 0:
                print("personality_surveysテーブルにresponsesカラムを追加しています...")
                cursor.execute("""
                    ALTER TABLE personality_surveys 
                    ADD COLUMN responses TEXT
                """)
                print("personality_surveysテーブルにresponsesカラムを追加しました。")
            else:
                print("personality_surveysテーブルにはすでにresponsesカラムが存在します。")
        
        # 変更をコミット
        connection.commit()
        print("データベースの更新が完了しました。")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        sys.exit(1)
    finally:
        connection.close()

if __name__ == "__main__":
    add_responses_column()