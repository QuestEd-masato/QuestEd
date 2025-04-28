# check_student_approval.py
import pymysql

# データベース接続情報
DB_USERNAME = "QuestEd"
DB_PASSWORD = "QuestEd-03012025"
DB_HOST = "localhost"
DB_NAME = "quested_db"

def check_student_approval():
    """生徒アカウントの承認状態を確認する"""
    try:
        # データベースに接続
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USERNAME,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection.cursor() as cursor:
            # usersテーブルの構造を確認
            cursor.execute("DESCRIBE users")
            fields = [row['Field'] for row in cursor.fetchall()]
            print("usersテーブルのフィールド:", fields)
            
            # 生徒アカウントの状態を確認
            cursor.execute("""
                SELECT id, username, email, email_confirmed, is_approved
                FROM users
                WHERE role = 'student'
            """)
            students = cursor.fetchall()
            
            print(f"\n生徒アカウント数: {len(students)}")
            for student in students:
                print(f"ID: {student['id']}, ユーザー名: {student['username']}, "
                      f"メール確認: {student['email_confirmed']}, 承認状態: {student['is_approved']}")
            
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    check_student_approval()