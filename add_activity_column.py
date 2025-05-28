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

def add_activity_column():
    """activity_logsテーブルにactivityカラムを追加"""
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
                WHERE table_name = 'activity_logs' 
                AND column_name = 'activity'
                AND table_schema = %s
            """, (DB_NAME,))
            
            if cursor.fetchone()[0] == 0:
                print("activity_logsテーブルにactivityカラムを追加しています...")
                cursor.execute("""
                    ALTER TABLE activity_logs 
                    ADD COLUMN activity TEXT
                """)
                print("activity_logsテーブルにactivityカラムを追加しました。")
            else:
                print("activity_logsテーブルにはすでにactivityカラムが存在します。")
        
        # 変更をコミット
        connection.commit()
        print("データベースの更新が完了しました。")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        sys.exit(1)
    finally:
        connection.close()

if __name__ == "__main__":
    add_activity_column()