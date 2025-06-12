#!/usr/bin/env python3
"""
簡易メール送信テスト
Celeryなしでメール機能をテストする
"""
import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.utils.email_sender import EmailSender

def test_email():
    """簡単なメール送信テスト"""
    app = create_app()
    
    with app.app_context():
        print("=== メール送信テスト開始 ===")
        
        # 環境変数チェック
        email_method = os.getenv('EMAIL_METHOD', 'smtp')
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')
        
        print(f"EMAIL_METHOD: {email_method}")
        print(f"SMTP_USER: {smtp_user if smtp_user else '❌ 未設定'}")
        print(f"SMTP_PASSWORD: {'✅ 設定済み' if smtp_password else '❌ 未設定'}")
        
        if not smtp_user or not smtp_password:
            print("\n❌ メール設定が不完全です。")
            print("以下の環境変数を.envファイルに設定してください：")
            print("EMAIL_METHOD=smtp")
            print("SMTP_USER=your-email@gmail.com") 
            print("SMTP_PASSWORD=your-app-password")
            return False
        
        # テストメール送信
        email_sender = EmailSender()
        test_recipient = input("テスト送信先メールアドレスを入力してください: ").strip()
        
        if not test_recipient:
            test_recipient = smtp_user  # 自分宛に送信
        
        print(f"\n📧 {test_recipient} にテストメールを送信中...")
        
        success, message = email_sender.send(
            recipients=[test_recipient],
            subject="QuestEd メール送信テスト",
            html_body="""
            <h2>QuestEd メール送信テスト</h2>
            <p>このメールは QuestEd の日報機能のテストです。</p>
            <p>送信時刻: """ + str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')) + """</p>
            <p>この機能が正常に動作していることを確認しました。</p>
            """
        )
        
        if success:
            print("✅ メール送信成功！")
            return True
        else:
            print(f"❌ メール送信失敗: {message}")
            return False

if __name__ == '__main__':
    test_email()