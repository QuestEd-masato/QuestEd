# utils/email.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import secrets
from datetime import datetime, timedelta
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
    # 環境変数からSMTP設定を取得
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    sender_email = os.getenv('SENDER_EMAIL', smtp_user)
    
    if not all([smtp_server, smtp_user, smtp_password]):
        # 開発環境ではコンソールに出力
        if os.getenv('FLASK_ENV') == 'development':
            confirm_url = url_for(
                'confirm_email', 
                user_id=user_id, 
                token=token, 
                _external=True
            )
            
            print("\n=== 確認メール ===")
            print(f"宛先: {user_email}")
            print(f"件名: QuestEd - メールアドレスの確認")
            print(f"本文:\n{username} 様\n\nQuestEdへのご登録ありがとうございます。\n"
                  f"以下のURLにアクセスして、メールアドレスの確認を完了してください。\n\n"
                  f"{confirm_url}\n\n"
                  f"このリンクは24時間有効です。\n\n"
                  f"※このメールに心当たりがない場合は無視してください。\n\n"
                  f"QuestEd運営チーム")
            print("================\n")
            
            return True
        else:
            raise ValueError("SMTP設定が不完全です。環境変数を確認してください。")
    
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
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()  # サーバーと対話を開始
        server.starttls()  # TLS暗号化を有効化
        server.ehlo()  # TLS開始後に再度ehlo
        server.login(smtp_user, smtp_password)
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
    # 環境変数からSMTP設定を取得
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    sender_email = os.getenv('SENDER_EMAIL', smtp_user)
    
    if not all([smtp_server, smtp_user, smtp_password]):
        # 開発環境ではコンソールに出力
        if os.getenv('FLASK_ENV') == 'development':
            reset_url = url_for(
                'reset_password', 
                user_id=user_id, 
                token=token, 
                _external=True
            )
            
            print("\n=== パスワードリセットメール ===")
            print(f"宛先: {user_email}")
            print(f"件名: QuestEd - パスワードリセット")
            print(f"本文:\n{username} 様\n\nQuestEdのパスワードリセットリクエストを受け付けました。\n"
                  f"以下のURLにアクセスして、新しいパスワードを設定してください。\n\n"
                  f"{reset_url}\n\n"
                  f"このリンクは1時間のみ有効です。\n\n"
                  f"※このメールに心当たりがない場合は無視してください。\n"
                  f"リクエストしていない場合、アカウントセキュリティを確認することをお勧めします。\n\n"
                  f"QuestEd運営チーム")
            print("================\n")
            
            return True
        else:
            raise ValueError("SMTP設定が不完全です。環境変数を確認してください。")
    
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
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()  # サーバーと対話を開始
        server.starttls()  # TLS暗号化を有効化
        server.ehlo()  # TLS開始後に再度ehlo
        server.login(smtp_user, smtp_password)
        server.sendmail(sender_email, user_email, message.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"メール送信エラー: {str(e)}")
        return False

def send_invitation_email(name, email, username, password, school_name, class_name):
    """
    生徒に招待メールを送信する関数
    
    Args:
        name: 生徒の名前
        email: 送信先メールアドレス
        username: ユーザー名
        password: 自動生成されたパスワード
        school_name: 学校名
        class_name: クラス名
        
    Returns:
        None: 送信に失敗した場合は例外を発生
    """
    # 環境変数からSMTP設定を取得
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    sender_email = os.getenv('SENDER_EMAIL', smtp_user)
    
    if not all([smtp_server, smtp_user, smtp_password]):
        # 開発環境ではコンソールに出力
        if os.getenv('FLASK_ENV') == 'development':
            print("\n=== 招待メール ===")
            print(f"宛先: {email}")
            print(f"件名: {school_name} 探究学習プラットフォームへのご招待")
            print(f"本文:\n{name} 様\n\n{school_name}の探究学習プラットフォーム「QuestEd」へようこそ！\n"
                  f"あなたは{class_name}のメンバーとして登録されました。\n\n"
                  f"以下の情報でログインしてください：\n\n"
                  f"ユーザー名: {username}\nパスワード: {password}\n\n"
                  f"セキュリティのため、初回ログイン後すぐにパスワードを変更してください。\n"
                  f"パスワードの変更は「アカウント設定」>「パスワード変更」から行えます。\n\n"
                  f"QuestEdでは、探究学習のテーマ設定から活動記録、成果発表まで、\n"
                  f"あなたの学びを効果的にサポートします。\n\n"
                  f"このメールは自動送信されています。\n"
                  f"ご不明な点があれば、担当教員にお問い合わせください。\n\n"
                  f"{school_name}")
            print("================\n")
            
            return
        else:
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
    
    セキュリティのため、初回ログイン後すぐにパスワードを変更してください。
    パスワードの変更は「アカウント設定」>「パスワード変更」から行えます。
    
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
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()  # サーバーと対話を開始
        server.starttls()  # TLS暗号化を有効化
        server.ehlo()  # TLS開始後に再度ehlo
        server.login(smtp_user, smtp_password)
        server.send_message(message)
        server.quit()
        return True
    except Exception as e:
        print(f"メール送信エラー: {str(e)}")
        return False