#!/usr/bin/env python3
"""
1日の授業活動サマリーを教師に送信するスクリプト
毎日18:00にcronで実行される
"""
import sys
import os
from datetime import datetime, timedelta

# プロジェクトのパスを追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, User, ActivityLog, Class, School
from flask import render_template_string
from sqlalchemy import func
from app.utils.email_sender import EmailSender

# アプリケーションコンテキストを作成
app = create_app()

def send_daily_summary():
    """メイン処理"""
    with app.app_context():
        print(f"[{datetime.now()}] Starting daily summary email task...")
        
        # 今日の日付
        today = datetime.now().date()
        
        # 教師ユーザーを取得
        teachers = User.query.filter_by(
            role='teacher',
            is_active=True,
            email_confirmed=True
        ).all()
        
        sent_count = 0
        
        for teacher in teachers:
            try:
                # 教師が担当するクラスの活動を集計
                class_activities = get_teacher_class_activities(teacher.id, today)
                
                if class_activities:
                    # メール送信
                    send_summary_email(teacher, class_activities, today)
                    sent_count += 1
                    print(f"Sent email to {teacher.email}")
                
            except Exception as e:
                print(f"Error sending email to {teacher.email}: {str(e)}")
                continue
        
        print(f"[{datetime.now()}] Completed. Sent {sent_count} emails.")

def get_teacher_class_activities(teacher_id, date):
    """教師の担当クラスの活動を取得"""
    activities = db.session.query(
        Class.id,
        Class.name,
        func.count(ActivityLog.id).label('activity_count'),
        func.count(func.distinct(ActivityLog.student_id)).label('active_students')
    ).select_from(Class).outerjoin(
        ActivityLog, 
        (Class.id == ActivityLog.class_id) & 
        (func.date(ActivityLog.timestamp) == date)
    ).filter(
        Class.teacher_id == teacher_id
    ).group_by(
        Class.id, Class.name
    ).all()
    
    return activities

def send_summary_email(teacher, activities, date):
    """サマリーメールを送信"""
    # メール本文を作成
    email_body = render_email_template(teacher, activities, date)
    
    # HTMLメール本文を作成
    html_body = email_body.replace('\n', '<br>')
    
    # EmailSenderを使用してメール送信
    email_sender = EmailSender()
    success, message = email_sender.send(
        recipients=[teacher.email],
        subject=f'本日の授業活動まとめ - {date.strftime("%Y年%m月%d日")}',
        html_body=html_body
    )
    
    if not success:
        raise Exception(message)

def render_email_template(teacher, activities, date):
    """メールテンプレートをレンダリング"""
    template = """
{{ teacher.full_name }} 先生

お疲れ様です。
本日（{{ date }}）の授業活動のまとめをお送りします。

{% for activity in activities %}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
クラス: {{ activity.name }}
- 活動記録数: {{ activity.activity_count }}件
- アクティブな生徒数: {{ activity.active_students }}名
{% else %}
本日は活動記録がありませんでした。
{% endfor %}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
詳細はダッシュボードでご確認ください：
https://quest-ed.jp/teacher_dashboard

※このメールは自動送信されています。

---
QuestEd - 探究学習支援プラットフォーム
"""
    
    return render_template_string(
        template,
        teacher=teacher,
        activities=activities,
        date=date.strftime('%Y年%m月%d日')
    )

if __name__ == '__main__':
    send_daily_summary()