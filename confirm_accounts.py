# confirm_accounts.py
import os
import sys
import pymysql
from datetime import datetime
from dotenv import load_dotenv

# データベース接続情報を直接設定
DB_USERNAME = "QuestEd"
DB_PASSWORD = "QuestEd-03012025"
DB_HOST = "localhost"
DB_NAME = "quested_db"

def confirm_accounts():
    """未確認のアカウントを確認済み状態に更新する"""
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
            # 未確認のユーザーを取得
            cursor.execute("SELECT id, username, email FROM users WHERE email_confirmed IS NULL OR email_confirmed = 0")
            unconfirmed_users = cursor.fetchall()
            
            if not unconfirmed_users:
                print("未確認のアカウントはありません。")
                return
            
            print(f"未確認のアカウント数: {len(unconfirmed_users)}")
            print("\n=== 未確認アカウント一覧 ===")
            for i, user in enumerate(unconfirmed_users, 1):
                print(f"{i}. {user['username']} ({user['email']})")
            
            # 確認処理
            confirm_choice = input("\n全てのアカウントを確認済みにしますか？(y/n): ")
            
            if confirm_choice.lower() == 'y':
                # 全ての未確認アカウントを更新
                cursor.execute(
                    "UPDATE users SET email_confirmed = 1 WHERE email_confirmed IS NULL OR email_confirmed = 0"
                )
                connection.commit()
                
                affected_rows = cursor.rowcount
                print(f"{affected_rows}件のアカウントを確認済みに更新しました。")
            
            else:
                # 個別に確認するか
                individual_confirm = input("個別にアカウントを確認しますか？(y/n): ")
                
                if individual_confirm.lower() == 'y':
                    updated_count = 0
                    
                    for user in unconfirmed_users:
                        user_confirm = input(f"{user['username']} ({user['email']}) を確認しますか？(y/n): ")
                        
                        if user_confirm.lower() == 'y':
                            cursor.execute(
                                "UPDATE users SET email_confirmed = 1 WHERE id = %s",
                                (user['id'],)
                            )
                            updated_count += 1
                            print(f"{user['username']} を確認済みに更新しました。")
                    
                    connection.commit()
                    print(f"合計 {updated_count} 件のアカウントを確認済みに更新しました。")
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
    confirm_accounts()