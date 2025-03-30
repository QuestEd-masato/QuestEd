# utils/email.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_invitation_email(name, email, username, password, school_name, class_name):
    """生徒に招待メールを送信する"""
    
    # 環境変数からSMTP設定を取得
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    sender_email = os.getenv('SENDER_EMAIL', smtp_user)
    
    if not all([smtp_server, smtp_user, smtp_password]):
        raise ValueError("SMTP設定が不完全です。環境変数を確認してください。")
    
    # メール内容を作成
    subject = f"{school_name} 探究学習プラットフォームへのご招待"
    
    body = f"""
    {name} 様
    
    {school_name}の探究学習プラットフォーム「QuestEd」へようこそ！
    あなたは{class_name}のメンバーとして登録されました。
    
    以下の情報でログインしてください：
    
    ユーザー名: {username}
    パスワード: {password}
    
    初回ログイン後、パスワードを変更することをお勧めします。
    
    QuestEdでは、探究学習のテーマ設定から活動記録、成果発表まで、
    あなたの学びを効果的にサポートします。
    
    このメールは自動送信されています。
    ご不明な点があれば、担当教員にお問い合わせください。
    
    {school_name}
    """
    
    # メールの構築
    message = MIMEMultipart()
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = email
    
    # メール本文を添付
    message.attach(MIMEText(body, "plain"))
    
    # メール送信
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()  # TLS暗号化を有効化
        server.login(smtp_user, smtp_password)
        server.send_message(message)