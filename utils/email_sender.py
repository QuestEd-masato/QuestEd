import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import url_for

def send_confirmation_email(user_email, user_id, token, username):
    """
    確認メールを送信する関数
    
    Args:
        user_email: 送信先メールアドレス
        user_id: ユーザーID
        token: 確認用トークン
        username: ユーザー名
    
    Returns:
        bool: 送信成功したかどうか
    """
    sender_email = "info@quested.jp"
    password = os.getenv('EMAIL_PASSWORD', '')
    
    # 確認URLを構築
    confirm_url = url_for(
        'confirm_email', 
        user_id=user_id, 
        token=token, 
        _external=True
    )
    
    # メールの構成
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = user_email
    message["Subject"] = "QuestEd - メールアドレスの確認"
    
    # メール本文
    body = f"""
    {username} 様
    
    QuestEdへのご登録ありがとうございます。
    以下のURLにアクセスして、メールアドレスの確認を完了してください。
    
    {confirm_url}
    
    このリンクは24時間有効です。
    
    ※このメールに心当たりがない場合は無視してください。
    
    QuestEd運営チーム
    """
    
    message.attach(MIMEText(body, "plain"))
    
    try:
        # SMTPサーバーに接続
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()  # サーバーと対話を開始
        server.starttls()  # TLS暗号化を有効化
        server.ehlo()  # TLS開始後に再度ehlo
        server.login(sender_email, password)
        server.sendmail(sender_email, user_email, message.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"メール送信エラー: {str(e)}")
        return False

def send_reset_password_email(user_email, user_id, token, username):
    """
    パスワードリセットメールを送信する関数
    
    Args:
        user_email: 送信先メールアドレス
        user_id: ユーザーID
        token: リセット用トークン
        username: ユーザー名
    
    Returns:
        bool: 送信成功したかどうか
    """
    sender_email = "info@quested.jp"
    password = os.getenv('EMAIL_PASSWORD', '')
    
    # リセットURLを構築
    reset_url = url_for(
        'reset_password', 
        user_id=user_id, 
        token=token, 
        _external=True
    )
    
    # メールの構成
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = user_email
    message["Subject"] = "QuestEd - パスワードリセット"
    
    # メール本文
    body = f"""
    {username} 様
    
    QuestEdのパスワードリセットリクエストを受け付けました。
    以下のURLにアクセスして、新しいパスワードを設定してください。
    
    {reset_url}
    
    このリンクは1時間のみ有効です。
    
    ※このメールに心当たりがない場合は無視してください。
    リクエストしていない場合、アカウントセキュリティを確認することをお勧めします。
    
    QuestEd運営チーム
    """
    
    message.attach(MIMEText(body, "plain"))
    
    try:
        # SMTPサーバーに接続
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()  # サーバーと対話を開始
        server.starttls()  # TLS暗号化を有効化
        server.ehlo()  # TLS開始後に再度ehlo
        server.login(sender_email, password)
        server.sendmail(sender_email, user_email, message.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"メール送信エラー: {str(e)}")
        return False