# add_user_columns.py
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

def add_user_columns():
    """usersテーブルに必要なカラムを追加"""
    try:
        # MySQLデータベースに接続
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USERNAME,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        
        with connection.cursor() as cursor:
            # 追加するカラムのリスト
            columns_to_add = [
                ("email_confirmed", "BOOLEAN DEFAULT FALSE"),
                ("email_token", "VARCHAR(100)"),
                ("token_created_at", "DATETIME"),
                ("is_approved", "BOOLEAN DEFAULT FALSE"),
                ("reset_token", "VARCHAR(100)"),
                ("reset_token_created_at", "DATETIME")
            ]
            
            for column_name, column_type in columns_to_add:
                # カラムが存在するか確認
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    AND column_name = %s
                    AND table_schema = %s
                """, (column_name, DB_NAME))
                
                if cursor.fetchone()[0] == 0:
                    print(f"usersテーブルに{column_name}カラムを追加しています...")
                    cursor.execute(f"""
                        ALTER TABLE users 
                        ADD COLUMN {column_name} {column_type}
                    """)
                    print(f"{column_name}カラムを追加しました。")
                else:
                    print(f"{column_name}カラムは既に存在します。")
            
            # 既存レコードを全てemail_confirmed = Trueに設定
            print("既存ユーザーを全て確認済みにしています...")
            cursor.execute("""
                UPDATE users 
                SET email_confirmed = TRUE, is_approved = TRUE 
                WHERE email_confirmed IS NULL OR is_approved IS NULL
            """)
            
            affected_rows = cursor.rowcount
            print(f"{affected_rows}件のユーザーを確認済みに更新しました。")
            
            # 変更をコミット
            connection.commit()
            print("データベースの更新が完了しました。")
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        if 'connection' in locals():
            connection.rollback()
        sys.exit(1)
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    add_user_columns()