# inspect_users.py
import pymysql

# データベース接続情報
DB_USERNAME = "QuestEd"
DB_PASSWORD = "QuestEd-03012025"
DB_HOST = "localhost"
DB_NAME = "quested_db"

def check_users_table():
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USERNAME,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        
        with connection.cursor() as cursor:
            # usersテーブルの構造を確認
            cursor.execute("DESCRIBE users")
            columns = cursor.fetchall()
            
            print("usersテーブルの構造:")
            for column in columns:
                print(f"- {column[0]}: {column[1]}")
            
            # usersテーブルのデータ件数
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            print(f"\nデータ件数: {count}")
            
            # 最大10件のデータを表示
            if count > 0:
                cursor.execute("SELECT * FROM users LIMIT 10")
                rows = cursor.fetchall()
                
                print("\nユーザーデータ（最大10件）:")
                for i, row in enumerate(rows, 1):
                    print(f"\n--- ユーザー {i} ---")
                    for j, value in enumerate(row):
                        column_name = columns[j][0] if j < len(columns) else f"列{j}"
                        print(f"{column_name}: {value}")
    
    except Exception as e:
        if "Table 'quested_db.users' doesn't exist" in str(e):
            print("usersテーブルが存在しません。別の名前でユーザー情報が保存されている可能性があります。")
            
            # テーブル一覧を表示
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SHOW TABLES")
                    tables = cursor.fetchall()
                    
                    print("\nデータベース内のテーブル一覧:")
                    for table in tables:
                        print(f"- {table[0]}")
            except:
                pass
        else:
            print(f"エラーが発生しました: {e}")
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    check_users_table()