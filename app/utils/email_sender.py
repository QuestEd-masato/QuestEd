import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2 import service_account
from googleapiclient.discovery import build
import base64

class EmailSender:
    def __init__(self):
        self.method = os.getenv('EMAIL_METHOD', 'smtp')  # smtp or gmail_api
        
    def send(self, recipients, subject, html_body, attachments=None):
        """メール送信の統一インターフェース"""
        if self.method == 'gmail_api':
            return self._send_via_gmail_api(recipients, subject, html_body)
        else:
            return self._send_via_smtp(recipients, subject, html_body)
    
    def _send_via_smtp(self, recipients, subject, html_body):
        """SMTP経由での送信（Gmailアプリパスワード使用）"""
        smtp_config = {
            'host': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'port': int(os.getenv('SMTP_PORT', 587)),
            'user': os.getenv('SMTP_USER'),
            'password': os.getenv('SMTP_PASSWORD')  # アプリパスワード
        }
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_config['user']
        msg['To'] = ', '.join(recipients)
        
        html_part = MIMEText(html_body, 'html', 'utf-8')
        msg.attach(html_part)
        
        try:
            with smtplib.SMTP(smtp_config['host'], smtp_config['port']) as server:
                server.starttls()
                server.login(smtp_config['user'], smtp_config['password'])
                server.send_message(msg)
            return True, "Email sent successfully"
        except Exception as e:
            return False, f"SMTP Error: {str(e)}"
    
    def _send_via_gmail_api(self, recipients, subject, html_body):
        """Gmail API経由での送信"""
        try:
            creds = service_account.Credentials.from_service_account_file(
                'credentials.json',
                scopes=['https://www.googleapis.com/auth/gmail.send']
            )
            
            service = build('gmail', 'v1', credentials=creds)
            
            message = MIMEMultipart()
            message['to'] = ', '.join(recipients)
            message['subject'] = subject
            message.attach(MIMEText(html_body, 'html'))
            
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            result = service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()
            
            return True, f"Message Id: {result['id']}"
        except Exception as e:
            return False, f"Gmail API Error: {str(e)}"

# Gmail送信テストスクリプト
def test_email_configuration():
    """メール設定のテスト"""
    sender = EmailSender()
    
    # SMTP設定確認
    print("Checking SMTP configuration...")
    smtp_vars = ['SMTP_SERVER', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD']
    for var in smtp_vars:
        value = os.getenv(var)
        if value:
            print(f"✓ {var} is set")
        else:
            print(f"✗ {var} is missing")
    
    # テストメール送信
    test_recipient = os.getenv('TEST_EMAIL', 'test@example.com')
    success, message = sender.send(
        recipients=[test_recipient],
        subject="QuestEd Email Test",
        html_body="<h1>Test Email</h1><p>This is a test email from QuestEd.</p>"
    )
    
    print(f"\nTest result: {success}")
    print(f"Message: {message}")
    
    return success

# 後方互換性のための関数
from flask import url_for

def send_confirmation_email(user_email, user_id, token, username):
    """
    確認メールを送信する関数（後方互換性）
    """
    sender = EmailSender()
    
    # 確認URLを構築
    confirm_url = url_for(
        'auth.verify_email', 
        user_id=user_id, 
        token=token, 
        _external=True
    )
    
    # HTML形式のメール本文
    html_body = f"""
    <html>
        <body>
            <h2>QuestEd - メールアドレスの確認</h2>
            <p>{username} 様</p>
            <p>QuestEdへのご登録ありがとうございます。</p>
            <p>以下のボタンをクリックして、メールアドレスの確認を完了してください。</p>
            <p style="margin: 20px 0;">
                <a href="{confirm_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    メールアドレスを確認
                </a>
            </p>
            <p>または、以下のURLをコピーしてブラウザのアドレスバーに貼り付けてください：</p>
            <p style="font-size: 12px; color: #666; word-break: break-all;">{confirm_url}</p>
            <p><small>このリンクは24時間有効です。</small></p>
            <hr>
            <p style="color: #666; font-size: 12px;">
                ※このメールに心当たりがない場合は無視してください。
            </p>
            <p>QuestEd運営チーム</p>
        </body>
    </html>
    """
    
    success, message = sender.send(
        recipients=[user_email],
        subject="QuestEd - メールアドレスの確認",
        html_body=html_body
    )
    
    if not success:
        print(f"メール送信エラー: {message}")
    
    return success

def send_reset_password_email(user_email, user_id, token, username):
    """
    パスワードリセットメールを送信する関数（後方互換性）
    """
    sender = EmailSender()
    
    # リセットURLを構築
    reset_url = url_for(
        'auth.reset_password', 
        user_id=user_id, 
        token=token, 
        _external=True
    )
    
    # HTML形式のメール本文
    html_body = f"""
    <html>
        <body>
            <h2>QuestEd - パスワードリセット</h2>
            <p>{username} 様</p>
            <p>QuestEdのパスワードリセットリクエストを受け付けました。</p>
            <p>以下のボタンをクリックして、新しいパスワードを設定してください。</p>
            <p style="margin: 20px 0;">
                <a href="{reset_url}" style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    パスワードをリセット
                </a>
            </p>
            <p>または、以下のURLをコピーしてブラウザのアドレスバーに貼り付けてください：</p>
            <p style="font-size: 12px; color: #666; word-break: break-all;">{reset_url}</p>
            <p><small>このリンクは1時間のみ有効です。</small></p>
            <hr>
            <p style="color: #666; font-size: 12px;">
                ※このメールに心当たりがない場合は無視してください。<br>
                リクエストしていない場合、アカウントセキュリティを確認することをお勧めします。
            </p>
            <p>QuestEd運営チーム</p>
        </body>
    </html>
    """
    
    success, message = sender.send(
        recipients=[user_email],
        subject="QuestEd - パスワードリセット",
        html_body=html_body
    )
    
    if not success:
        print(f"メール送信エラー: {message}")
    
    return success