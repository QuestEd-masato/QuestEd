# app/admin/analytics_secure.py
"""
セキュア版 - 管理者向け分析・使用状況ダッシュボード
SQLインジェクション対策済み
"""
from flask import render_template, jsonify, request, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import logging

from app.models import User, School, Class
from app.admin import admin_bp, admin_required
from app.utils.safe_queries import SafeAnalyticsQueries, SafeSearchQueries

@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics_dashboard():
    """セキュアな使用状況分析ダッシュボード"""
    try:
        # セキュアなクエリを使用して基本統計を取得
        basic_stats = get_basic_stats_secure()
        
        # 日別アクティブユーザー（過去30日）
        daily_active_users = SafeAnalyticsQueries.get_daily_active_users(30)
        
        # API使用統計
        api_usage = SafeAnalyticsQueries.get_api_usage_statistics(30)
        
        # 学校統計
        school_stats = SafeAnalyticsQueries.get_school_statistics()
        
        # 最近の活動
        recent_activities = SafeAnalyticsQueries.get_recent_activities(20)
        
        # チャート用データの整形
        chart_data = format_chart_data(daily_active_users)
        
        return render_template('admin/analytics_dashboard.html',
                             stats=basic_stats,
                             daily_active_users=chart_data,
                             api_usage=api_usage,
                             school_stats=school_stats,
                             recent_activities=recent_activities)
                             
    except Exception as e:
        current_app.logger.error(f"Analytics dashboard error: {str(e)}", exc_info=True)
        
        # エラー時は安全なデフォルト値を返す
        default_data = get_default_analytics_data()
        return render_template('admin/analytics_dashboard.html', **default_data)

@admin_bp.route('/analytics/api')
@login_required
@admin_required
def analytics_api():
    """セキュアな分析データAPI"""
    try:
        data_type = request.args.get('type', '').strip()
        
        # 許可されたデータタイプのみ処理
        allowed_types = ['daily_users', 'school_stats', 'api_usage', 'recent_activities']
        if data_type not in allowed_types:
            return jsonify({'error': 'Invalid data type'}), 400
        
        if data_type == 'daily_users':
            days = min(int(request.args.get('days', 7)), 90)  # 最大90日
            data = SafeAnalyticsQueries.get_daily_active_users(days)
            
        elif data_type == 'school_stats':
            data = SafeAnalyticsQueries.get_school_statistics()
            
        elif data_type == 'api_usage':
            days = min(int(request.args.get('days', 30)), 90)
            data = SafeAnalyticsQueries.get_api_usage_statistics(days)
            
        elif data_type == 'recent_activities':
            limit = min(int(request.args.get('limit', 20)), 50)
            data = SafeAnalyticsQueries.get_recent_activities(limit)
            
        return jsonify({'status': 'success', 'data': data})
        
    except ValueError as e:
        current_app.logger.warning(f"Invalid parameter in analytics API: {str(e)}")
        return jsonify({'error': 'Invalid parameters'}), 400
        
    except Exception as e:
        current_app.logger.error(f"Analytics API error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

@admin_bp.route('/analytics/user/<int:user_id>')
@login_required
@admin_required
def user_analytics(user_id):
    """特定ユーザーの分析データ"""
    try:
        # 権限チェック（管理者のみ）
        if current_user.role != 'admin':
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        # ユーザー存在チェック
        user = User.query.get_or_404(user_id)
        
        # セキュアなクエリでユーザー活動取得
        user_activity = SafeAnalyticsQueries.get_user_activity_summary(user_id, 30)
        
        return jsonify({
            'status': 'success',
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
                'school': user.school.name if user.school else None
            },
            'activity': user_activity
        })
        
    except Exception as e:
        current_app.logger.error(f"User analytics error for user {user_id}: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to fetch user analytics'}), 500

@admin_bp.route('/analytics/search')
@login_required
@admin_required
def search_analytics():
    """セキュアな検索機能"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query or len(query) < 2:
            return jsonify({'error': 'Search query too short'}), 400
        
        # 検索文字列の長さ制限
        if len(query) > 100:
            return jsonify({'error': 'Search query too long'}), 400
        
        # セキュアな検索実行
        results = SafeSearchQueries.search_users(query, current_user.id, 20)
        
        return jsonify({
            'status': 'success',
            'results': results,
            'count': len(results)
        })
        
    except Exception as e:
        current_app.logger.error(f"Search analytics error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Search failed'}), 500

def get_basic_stats_secure():
    """セキュアな基本統計情報取得"""
    try:
        # ORMを使用してSQLインジェクション対策
        total_users = User.query.count()
        total_schools = School.query.count()
        total_classes = Class.query.count()
        
        # 今月の新規ユーザー
        this_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_users_this_month = User.query.filter(
            User.created_at >= this_month_start
        ).count()
        
        # 過去7日のアクティブユーザー
        week_ago = datetime.now() - timedelta(days=7)
        # ActivityLogとの結合はSafeAnalyticsQueriesで実行
        
        return {
            'total_users': total_users,
            'new_users_this_month': new_users_this_month,
            'total_schools': total_schools,
            'total_classes': total_classes,
            'active_users_week': 0,  # SafeAnalyticsQueriesで別途取得
            'total_activities': 0,   # SafeAnalyticsQueriesで別途取得
            'ai_usage_count': 0      # SafeAnalyticsQueriesで別途取得
        }
        
    except Exception as e:
        current_app.logger.error(f"Error getting basic stats: {str(e)}", exc_info=True)
        return get_default_stats()

def format_chart_data(daily_data):
    """チャート用データの整形"""
    try:
        labels = [item['date'] for item in daily_data]
        data = [item['active_users'] for item in daily_data]
        
        return {
            'labels': labels,
            'data': data
        }
    except Exception as e:
        current_app.logger.warning(f"Error formatting chart data: {str(e)}")
        return {'labels': [], 'data': []}

def get_default_analytics_data():
    """エラー時のデフォルトデータ"""
    return {
        'stats': get_default_stats(),
        'daily_active_users': {'labels': [], 'data': []},
        'api_usage': {
            'chat_usage': 0, 'theme_generation': 0, 'evaluation_usage': 0,
            'curriculum_usage': 0, 'total_api_calls': 0, 
            'estimated_cost_usd': 0, 'estimated_cost_jpy': 0
        },
        'school_stats': [],
        'recent_activities': []
    }

def get_default_stats():
    """デフォルト統計データ"""
    return {
        'total_users': 0,
        'new_users_this_month': 0,
        'active_users_week': 0,
        'total_activities': 0,
        'ai_usage_count': 0,
        'total_schools': 0,
        'total_classes': 0
    }