# update_all_accounts.py
import pymysql
from datetime import datetime

# データベース接続情報
DB_USERNAME = "QuestEd"
DB_PASSWORD = "QuestEd-03012025"
DB_HOST = "localhost"
DB_NAME = "quested_db"

def update_all_accounts():
    """既存アカウントの認証・承認状態を更新する"""
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
            # 未確認のアカウントを取得（学生と教師の両方）
            cursor.execute("""
                SELECT id, username, email, role, email_confirmed, is_approved
                FROM users
                WHERE email_confirmed IS NULL OR is_approved IS NULL
            """)
            unconfirmed_users = cursor.fetchall()
            
            if not unconfirmed_users:
                print("未確認のアカウントはありません。")
                return
            
            print(f"未確認のアカウント数: {len(unconfirmed_users)}")
            print("\n=== 未確認アカウント一覧 ===")
            for i, user in enumerate(unconfirmed_users, 1):
                status = []
                if not user['email_confirmed']:
                    status.append("メール未確認")
                if not user['is_approved']:
                    status.append("未承認")
                
                status_text = ", ".join(status) if status else "不明な問題"
                print(f"{i}. {user['username']} ({user['email']}) - {user['role']} - {status_text}")
            
            # 更新処理
            confirm_choice = input("\n全てのアカウントを確認済み・承認済みにしますか？(y/n): ")
            
            if confirm_choice.lower() == 'y':
                # 現在時刻を取得
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # 全ての未確認アカウントを更新
                cursor.execute(
                    """
                    UPDATE users
                    SET email_confirmed = 1, is_approved = 1
                    WHERE email_confirmed IS NULL OR is_approved IS NULL
                    """
                )
                connection.commit()
                
                affected_rows = cursor.rowcount
                print(f"{affected_rows}件のアカウントを確認済み・承認済みに更新しました。")
            
            else:
                # 個別に確認するか
                individual_confirm = input("個別にアカウントを確認しますか？(y/n): ")
                
                if individual_confirm.lower() == 'y':
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    updated_count = 0
                    
                    for user in unconfirmed_users:
                        user_confirm = input(f"{user['username']} ({user['email']}) - {user['role']} を確認・承認しますか？(y/n): ")
                        
                        if user_confirm.lower() == 'y':
                            cursor.execute(
                                """
                                UPDATE users
                                SET email_confirmed = 1, is_approved = 1
                                WHERE id = %s
                                """,
                                (user['id'],)
                            )
                            updated_count += 1
                            print(f"{user['username']} を確認済み・承認済みに更新しました。")
                    
                    connection.commit()
                    print(f"合計 {updated_count} 件のアカウントを確認済み・承認済みに更新しました。")
                else:
                    print("更新をキャンセルしました。")
            
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        if 'connection' in locals():
            connection.rollback()
    finally:
        if 'connection' in locals():
            connection.close()

if __name__ == "__main__":
    update_all_accounts()