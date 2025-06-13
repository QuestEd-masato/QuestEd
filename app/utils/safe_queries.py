# app/utils/safe_queries.py
"""
安全なSQLクエリユーティリティ
SQLインジェクション対策済みのクエリビルダー
"""

from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from app.models import (
    User, School, ActivityLog, ChatHistory, 
    InquiryTheme, StudentEvaluation, Curriculum,
    Todo, Goal, Class
)
from app import db

class SafeAnalyticsQueries:
    """セキュアな分析クエリクラス"""
    
    @staticmethod
    def get_daily_active_users(days: int = 30) -> List[Dict]:
        """日別アクティブユーザー数を安全に取得"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # SQLAlchemyのORMを使用してSQLインジェクション対策
        query = db.session.query(
            func.date(ActivityLog.timestamp).label('activity_date'),
            func.count(ActivityLog.student_id.distinct()).label('active_users')
        ).filter(
            and_(
                func.date(ActivityLog.timestamp) >= start_date,
                func.date(ActivityLog.timestamp) <= end_date
            )
        ).group_by(
            func.date(ActivityLog.timestamp)
        ).order_by(
            asc('activity_date')
        )
        
        result = query.all()
        
        return [
            {
                'date': row.activity_date.isoformat(),
                'active_users': row.active_users
            }
            for row in result
        ]
    
    @staticmethod
    def get_school_statistics() -> List[Dict]:
        """学校別統計を安全に取得"""
        # JOINを使用してSQLインジェクション対策
        query = db.session.query(
            School.name.label('school_name'),
            School.school_code.label('school_code'),
            func.count(User.id.distinct()).label('user_count'),
            func.sum(
                func.case([(User.role == 'teacher', 1)], else_=0)
            ).label('teacher_count'),
            func.sum(
                func.case([(User.role == 'student', 1)], else_=0)
            ).label('student_count'),
            func.count(Class.id.distinct()).label('class_count'),
            func.count(ActivityLog.id.distinct()).label('activity_count')
        ).outerjoin(
            User, School.id == User.school_id
        ).outerjoin(
            Class, User.id == Class.teacher_id
        ).outerjoin(
            ActivityLog, User.id == ActivityLog.student_id
        ).group_by(
            School.id, School.name, School.school_code
        ).order_by(
            desc('user_count')
        )
        
        result = query.all()
        
        return [
            {
                'school_name': row.school_name or 'Unknown',
                'school_code': row.school_code or 'N/A',
                'user_count': row.user_count or 0,
                'teacher_count': row.teacher_count or 0,
                'student_count': row.student_count or 0,
                'class_count': row.class_count or 0,
                'activity_count': row.activity_count or 0
            }
            for row in result
        ]
    
    @staticmethod
    def get_school_performance_stats() -> List[Dict]:
        """学校別パフォーマンス統計を安全に取得"""
        week_ago = datetime.now() - timedelta(days=7)
        
        query = db.session.query(
            School.name.label('school_name'),
            func.count(ActivityLog.student_id.distinct()).label('active_students'),
            func.count(ActivityLog.id).label('total_activities'),
            func.avg(
                func.case([
                    (ActivityLog.timestamp >= week_ago, 1.0)
                ], else_=0.0)
            ).label('weekly_activity_rate')
        ).outerjoin(
            User, School.id == User.school_id
        ).outerjoin(
            ActivityLog, and_(
                User.id == ActivityLog.student_id,
                User.role == 'student'
            )
        ).filter(
            School.id.isnot(None)
        ).group_by(
            School.id, School.name
        ).order_by(
            desc('total_activities')
        )
        
        result = query.all()
        
        return [
            {
                'school_name': row.school_name,
                'active_students': row.active_students or 0,
                'total_activities': row.total_activities or 0,
                'weekly_activity_rate': float(row.weekly_activity_rate or 0)
            }
            for row in result
        ]
    
    @staticmethod
    def get_api_usage_statistics(days: int = 30) -> Dict:
        """API使用統計を安全に取得"""
        start_date = datetime.now() - timedelta(days=days)
        
        # 各種API使用量をORMで安全に取得
        chat_usage = ChatHistory.query.filter(
            ChatHistory.timestamp >= start_date
        ).count()
        
        theme_generation = InquiryTheme.query.filter(
            and_(
                InquiryTheme.created_at >= start_date,
                InquiryTheme.description.isnot(None)
            )
        ).count()
        
        evaluation_usage = StudentEvaluation.query.filter(
            StudentEvaluation.created_at >= start_date
        ).count()
        
        curriculum_usage = Curriculum.query.filter(
            Curriculum.created_at >= start_date
        ).count()
        
        total_api_calls = chat_usage + theme_generation + evaluation_usage + curriculum_usage
        
        # コスト計算（概算）
        gpt35_cost = chat_usage * 0.002  # GPT-3.5使用想定
        gpt4_cost = (theme_generation + evaluation_usage + curriculum_usage) * 0.06  # GPT-4使用想定
        estimated_cost_usd = gpt35_cost + gpt4_cost
        
        return {
            'chat_usage': chat_usage,
            'theme_generation': theme_generation,
            'evaluation_usage': evaluation_usage,
            'curriculum_usage': curriculum_usage,
            'total_api_calls': total_api_calls,
            'estimated_cost_usd': round(estimated_cost_usd, 2),
            'estimated_cost_jpy': round(estimated_cost_usd * 150, 0)
        }
    
    @staticmethod
    def get_user_activity_summary(user_id: int, days: int = 30) -> Dict:
        """特定ユーザーの活動サマリーを安全に取得"""
        start_date = datetime.now() - timedelta(days=days)
        
        # ユーザー存在チェック
        user = User.query.get(user_id)
        if not user:
            return {}
        
        # 活動ログ取得
        activities = ActivityLog.query.filter(
            and_(
                ActivityLog.student_id == user_id,
                ActivityLog.timestamp >= start_date
            )
        ).count()
        
        # チャット履歴取得
        chats = ChatHistory.query.filter(
            and_(
                ChatHistory.user_id == user_id,
                ChatHistory.timestamp >= start_date
            )
        ).count()
        
        # TODO・Goal取得
        todos = Todo.query.filter(
            and_(
                Todo.user_id == user_id,
                Todo.created_at >= start_date
            )
        ).count()
        
        goals = Goal.query.filter(
            and_(
                Goal.user_id == user_id,
                Goal.created_at >= start_date
            )
        ).count()
        
        return {
            'user_id': user_id,
            'username': user.username,
            'role': user.role,
            'activities': activities,
            'chats': chats,
            'todos': todos,
            'goals': goals,
            'period_days': days
        }
    
    @staticmethod
    def get_recent_activities(limit: int = 50) -> List[Dict]:
        """最近の活動を安全に取得"""
        # ページネーション対応で制限
        limit = min(limit, 100)  # 最大100件
        
        query = db.session.query(ActivityLog).options(
            joinedload(ActivityLog.student)
        ).order_by(
            desc(ActivityLog.timestamp)
        ).limit(limit)
        
        activities = query.all()
        
        return [
            {
                'id': activity.id,
                'student_name': activity.student.display_name if activity.student else 'Unknown',
                'student_id': activity.student_id,
                'title': activity.title,
                'content': activity.content[:100] + '...' if len(activity.content) > 100 else activity.content,
                'timestamp': activity.timestamp.isoformat(),
                'has_image': bool(activity.image_url)
            }
            for activity in activities
        ]

class SafeSearchQueries:
    """安全な検索クエリクラス"""
    
    @staticmethod
    def search_users(search_term: str, requester_user_id: int, limit: int = 20) -> List[Dict]:
        """ユーザー検索（SQLインジェクション対策済み）"""
        # 入力検証
        if not search_term or len(search_term.strip()) < 2:
            return []
        
        # 制限値確認
        limit = min(limit, 50)  # 最大50件
        
        # 検索項目をサニタイズ
        search_term = search_term.strip()
        
        # 権限チェック用にリクエストユーザー取得
        requester = User.query.get(requester_user_id)
        if not requester:
            return []
        
        # 基本クエリ
        query = User.query.filter(
            or_(
                User.full_name.contains(search_term),
                User.email.contains(search_term)
            )
        )
        
        # 権限による絞り込み
        if requester.role == 'teacher':
            query = query.filter(User.school_id == requester.school_id)
        elif requester.role == 'student':
            query = query.filter(User.id == requester.id)
        # adminは全体検索可能
        
        users = query.limit(limit).all()
        
        return [
            {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'school_name': user.school.name if user.school else None
            }
            for user in users
        ]