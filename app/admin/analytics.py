# app/admin/analytics.py
"""
管理者向け分析・使用状況ダッシュボード
"""
from flask import render_template, jsonify, request, current_app
from flask_login import login_required
from sqlalchemy import func, desc, text
from datetime import datetime, timedelta
import os
import logging

from app.models import (
    db, User, School, Class, ActivityLog, ChatHistory, 
    InquiryTheme, StudentEvaluation, Curriculum, Todo, Goal
)
from app.admin import admin_bp, admin_required

@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics_dashboard():
    """使用状況分析ダッシュボード"""
    try:
        # 日別アクティブユーザー
        daily_active_users = get_daily_active_users(30)
        
        # 基本統計情報
        stats = {
            'total_users': 0,
            'new_users_this_month': 0,
            'active_users_week': 0,
            'total_activities': 0,
            'ai_usage_count': 0,
            'total_schools': 0,
            'total_classes': 0
        }
        
        try:
            # 総ユーザー数
            stats['total_users'] = User.query.count()
            
            # 今月の新規ユーザー
            this_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            stats['new_users_this_month'] = User.query.filter(User.created_at >= this_month_start).count()
            
            # アクティブユーザー数（過去7日）
            week_ago = datetime.now() - timedelta(days=7)
            stats['active_users_week'] = db.session.query(ActivityLog.student_id).filter(
                ActivityLog.timestamp >= week_ago
            ).distinct().count()
            
            # 今月の総活動記録数
            stats['total_activities'] = ActivityLog.query.filter(
                ActivityLog.timestamp >= this_month_start
            ).count()
            
            # 学校数
            stats['total_schools'] = School.query.count()
            
            # クラス数  
            stats['total_classes'] = Class.query.count()
            
        except Exception as e:
            logging.error(f"Error fetching basic stats: {str(e)}")
        
        # API使用状況（簡易版）
        api_usage = {
            'chat_usage': 0,
            'theme_generation': 0,
            'evaluation_usage': 0,
            'curriculum_usage': 0,
            'total_api_calls': 0,
            'estimated_cost_usd': 0,
            'estimated_cost_jpy': 0
        }
        
        try:
            this_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # 各テーブルが存在する場合のみカウント
            try:
                api_usage['chat_usage'] = ChatHistory.query.filter(
                    ChatHistory.timestamp >= this_month_start
                ).count()
            except:
                pass
                
            try:
                api_usage['theme_generation'] = InquiryTheme.query.filter(
                    InquiryTheme.created_at >= this_month_start,
                    InquiryTheme.description.isnot(None)
                ).count()
            except:
                pass
                
            try:
                api_usage['evaluation_usage'] = StudentEvaluation.query.filter(
                    StudentEvaluation.created_at >= this_month_start
                ).count()
            except:
                pass
                
            try:
                api_usage['curriculum_usage'] = Curriculum.query.filter(
                    Curriculum.created_at >= this_month_start
                ).count()
            except:
                pass
            
            # 統計値を更新
            stats['ai_usage_count'] = api_usage['chat_usage']
            api_usage['total_api_calls'] = (api_usage['chat_usage'] + api_usage['theme_generation'] + 
                                          api_usage['evaluation_usage'] + api_usage['curriculum_usage'])
            
            # 推定コスト計算
            gpt35_cost = api_usage['chat_usage'] * 0.002
            gpt4_cost = (api_usage['theme_generation'] + api_usage['evaluation_usage'] + 
                        api_usage['curriculum_usage']) * 0.06
            api_usage['estimated_cost_usd'] = round(gpt35_cost + gpt4_cost, 2)
            api_usage['estimated_cost_jpy'] = round(api_usage['estimated_cost_usd'] * 150, 0)
                
        except Exception as e:
            logging.warning(f"Could not fetch API usage: {str(e)}")
        
        # 学校統計（簡易版）
        school_stats = []
        try:
            schools = School.query.all()
            for school in schools:
                try:
                    user_count = User.query.filter_by(school_id=school.id).count()
                    activity_count = ActivityLog.query.join(User).filter(User.school_id == school.id).count()
                    
                    school_stats.append({
                        'school_name': school.name,
                        'school_code': school.code,
                        'user_count': user_count,
                        'teacher_count': User.query.filter_by(school_id=school.id, role='teacher').count(),
                        'student_count': User.query.filter_by(school_id=school.id, role='student').count(),
                        'class_count': Class.query.join(User).filter(User.school_id == school.id).count(),
                        'activity_count': activity_count
                    })
                except Exception as e:
                    logging.warning(f"Could not fetch stats for school {school.id}: {str(e)}")
        except Exception as e:
            logging.error(f"Could not fetch school stats: {str(e)}")
        
        # 機能使用統計
        feature_usage = {
            'activity_logs': 0,
            'chat_sessions': 0,
            'todos_created': 0,
            'goals_created': 0,
            'themes_generated': 0
        }
        
        try:
            this_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            feature_usage['activity_logs'] = ActivityLog.query.filter(
                ActivityLog.timestamp >= this_month_start
            ).count()
            feature_usage['chat_sessions'] = api_usage['chat_usage']
            
            try:
                feature_usage['todos_created'] = Todo.query.filter(Todo.created_at >= this_month_start).count()
            except:
                pass
                
            try:
                feature_usage['goals_created'] = Goal.query.filter(Goal.created_at >= this_month_start).count()
            except:
                pass
                
            feature_usage['themes_generated'] = api_usage['theme_generation']
            
        except Exception as e:
            logging.warning(f"Could not fetch feature usage: {str(e)}")
        
        # 最近のアクティビティ
        recent_activities = {
            'recent_users': [],
            'recent_activities': []
        }
        
        try:
            recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
            recent_activities['recent_users'] = [
                {
                    'id': user.id,
                    'username': user.username,
                    'role': user.role,
                    'created_at': user.created_at,
                    'school_name': user.school.name if user.school else '未設定'
                } for user in recent_users
            ]
            
            recent_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()
            recent_activities['recent_activities'] = [
                {
                    'id': log.id,
                    'student_name': log.student.display_name if log.student else 'Unknown',
                    'title': log.title,
                    'timestamp': log.timestamp,
                    'has_image': bool(log.image_url)
                } for log in recent_logs
            ]
        except Exception as e:
            logging.warning(f"Could not fetch recent activities: {str(e)}")
        
        return render_template('admin/analytics_dashboard.html',
                             stats=stats,
                             daily_active_users=daily_active_users,
                             api_usage=api_usage,
                             school_stats=school_stats,
                             feature_usage=feature_usage,
                             recent_activities=recent_activities)
                             
    except Exception as e:
        logging.error(f"Analytics dashboard error: {str(e)}")
        # エラー時でも空のデータで表示
        return render_template('admin/analytics_dashboard.html',
                             stats={'total_users': 0, 'new_users_this_month': 0, 'active_users_week': 0, 
                                   'total_activities': 0, 'ai_usage_count': 0, 'total_schools': 0, 'total_classes': 0},
                             daily_active_users={'labels': [], 'data': []},
                             api_usage={'chat_usage': 0, 'theme_generation': 0, 'evaluation_usage': 0, 
                                       'curriculum_usage': 0, 'total_api_calls': 0, 'estimated_cost_usd': 0, 'estimated_cost_jpy': 0},
                             school_stats=[],
                             feature_usage={'activity_logs': 0, 'chat_sessions': 0, 'todos_created': 0, 
                                          'goals_created': 0, 'themes_generated': 0},
                             recent_activities={'recent_users': [], 'recent_activities': []})

@admin_bp.route('/analytics/api')
@login_required
@admin_required
def analytics_api():
    """分析データのAPI（AJAX用）"""
    data_type = request.args.get('type', 'daily_users')
    
    if data_type == 'daily_users':
        data = get_daily_active_users(days=7)
    elif data_type == 'feature_usage':
        data = get_feature_usage_stats()
    elif data_type == 'school_performance':
        data = get_school_performance_stats()
    else:
        data = {}
    
    return jsonify(data)

def get_basic_stats():
    """基本統計情報を取得"""
    total_users = User.query.count()
    total_schools = School.query.count()
    total_classes = Class.query.count()
    
    # 今月の新規ユーザー
    this_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_users_this_month = User.query.filter(User.created_at >= this_month_start).count()
    
    # アクティブユーザー（過去7日間）
    week_ago = datetime.now() - timedelta(days=7)
    active_users_week = User.query.join(ActivityLog).filter(
        ActivityLog.timestamp >= week_ago
    ).distinct().count()
    
    # 今月の総活動記録数
    total_activities = ActivityLog.query.filter(ActivityLog.timestamp >= this_month_start).count()
    
    # AI機能使用回数（今月）
    ai_usage_count = ChatHistory.query.filter(ChatHistory.timestamp >= this_month_start).count()
    
    return {
        'total_users': total_users,
        'total_schools': total_schools,
        'total_classes': total_classes,
        'new_users_this_month': new_users_this_month,
        'active_users_week': active_users_week,
        'total_activities': total_activities,
        'ai_usage_count': ai_usage_count
    }

def get_daily_active_users(days=30):
    """日別アクティブユーザー数を取得"""
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # 日別のアクティブユーザー数を集計
        query = text("""
            SELECT DATE(timestamp) as activity_date,
                   COUNT(DISTINCT student_id) as active_users
            FROM activity_logs
            WHERE DATE(timestamp) >= :start_date
              AND DATE(timestamp) <= :end_date
            GROUP BY DATE(timestamp)
            ORDER BY activity_date
        """)
        
        result = db.session.execute(query, {
            'start_date': start_date,
            'end_date': end_date
        }).fetchall()
        
        # 結果を辞書形式に整形
        dates = []
        values = []
        
        # 全日付を生成（データがない日も0として含める）
        current_date = start_date
        date_data = {row.activity_date: row.active_users for row in result}
        
        while current_date <= end_date:
            dates.append(current_date.strftime('%m/%d'))
            values.append(date_data.get(current_date, 0))
            current_date += timedelta(days=1)
        
        return {
            'labels': dates,
            'data': values
        }
        
    except Exception as e:
        logging.error(f"Error in get_daily_active_users: {str(e)}")
        return {'labels': [], 'data': []}

def get_api_usage_stats():
    """API使用統計を取得"""
    this_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # チャット（GPT-3.5-turbo）使用回数
    chat_usage = ChatHistory.query.filter(ChatHistory.timestamp >= this_month_start).count()
    
    # テーマ生成（GPT-4）使用回数（推定）
    theme_generation = InquiryTheme.query.filter(
        InquiryTheme.created_at >= this_month_start,
        InquiryTheme.description.isnot(None)
    ).count()
    
    # 評価生成（GPT-4）使用回数
    evaluation_usage = StudentEvaluation.query.filter(
        StudentEvaluation.created_at >= this_month_start
    ).count()
    
    # カリキュラム生成（GPT-4）使用回数
    curriculum_usage = Curriculum.query.filter(
        Curriculum.created_at >= this_month_start
    ).count()
    
    # 推定コスト計算（概算）
    gpt35_cost = chat_usage * 0.002  # $0.002 per 1K tokens (推定)
    gpt4_cost = (theme_generation + evaluation_usage + curriculum_usage) * 0.06  # $0.06 per 1K tokens (推定)
    total_estimated_cost = gpt35_cost + gpt4_cost
    
    return {
        'chat_usage': chat_usage,
        'theme_generation': theme_generation,
        'evaluation_usage': evaluation_usage,
        'curriculum_usage': curriculum_usage,
        'total_api_calls': chat_usage + theme_generation + evaluation_usage + curriculum_usage,
        'estimated_cost_usd': round(total_estimated_cost, 2),
        'estimated_cost_jpy': round(total_estimated_cost * 150, 0)  # 1USD = 150JPY で概算
    }

def get_school_statistics():
    """学校別統計を取得"""
    query = text("""
        SELECT s.name as school_name,
               s.code as school_code,
               COUNT(DISTINCT u.id) as user_count,
               COUNT(DISTINCT CASE WHEN u.role = 'teacher' THEN u.id END) as teacher_count,
               COUNT(DISTINCT CASE WHEN u.role = 'student' THEN u.id END) as student_count,
               COUNT(DISTINCT c.id) as class_count,
               COUNT(DISTINCT al.id) as activity_count
        FROM schools s
        LEFT JOIN users u ON s.id = u.school_id
        LEFT JOIN classes c ON u.id = c.teacher_id
        LEFT JOIN activity_logs al ON u.id = al.student_id
        GROUP BY s.id, s.name, s.code
        ORDER BY user_count DESC
    """)
    
    result = db.session.execute(query).fetchall()
    
    schools = []
    for row in result:
        schools.append({
            'school_name': row.school_name,
            'school_code': row.school_code,
            'user_count': row.user_count or 0,
            'teacher_count': row.teacher_count or 0,
            'student_count': row.student_count or 0,
            'class_count': row.class_count or 0,
            'activity_count': row.activity_count or 0
        })
    
    return schools

def get_feature_usage_stats():
    """機能別使用統計を取得"""
    this_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 活動記録数
    activity_logs = ActivityLog.query.filter(ActivityLog.timestamp >= this_month_start).count()
    
    # チャット使用数
    chat_sessions = ChatHistory.query.filter(ChatHistory.timestamp >= this_month_start).count()
    
    # TODO作成数
    todos_created = Todo.query.filter(Todo.created_at >= this_month_start).count()
    
    # 目標設定数
    goals_created = Goal.query.filter(Goal.created_at >= this_month_start).count()
    
    # 探究テーマ生成数
    themes_generated = InquiryTheme.query.filter(InquiryTheme.created_at >= this_month_start).count()
    
    return {
        'activity_logs': activity_logs,
        'chat_sessions': chat_sessions,
        'todos_created': todos_created,
        'goals_created': goals_created,
        'themes_generated': themes_generated
    }

def get_recent_activities():
    """最近のアクティビティを取得"""
    recent_users = User.query.order_by(desc(User.created_at)).limit(5).all()
    recent_activities = ActivityLog.query.order_by(desc(ActivityLog.timestamp)).limit(10).all()
    
    activities = []
    for activity in recent_activities:
        activities.append({
            'id': activity.id,
            'student_name': activity.student.username if activity.student else 'Unknown',
            'title': activity.title,
            'timestamp': activity.timestamp,
            'has_image': bool(activity.image_url)
        })
    
    users = []
    for user in recent_users:
        users.append({
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'created_at': user.created_at,
            'school_name': user.school.name if user.school else '未設定'
        })
    
    return {
        'recent_users': users,
        'recent_activities': activities
    }

def get_school_performance_stats():
    """学校別パフォーマンス統計"""
    query = text("""
        SELECT s.name as school_name,
               COUNT(DISTINCT al.student_id) as active_students,
               COUNT(al.id) as total_activities,
               AVG(CASE WHEN al.timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY) 
                   THEN 1 ELSE 0 END) as weekly_activity_rate
        FROM schools s
        LEFT JOIN users u ON s.id = u.school_id AND u.role = 'student'
        LEFT JOIN activity_logs al ON u.id = al.student_id
        WHERE s.id IS NOT NULL
        GROUP BY s.id, s.name
        HAVING COUNT(DISTINCT u.id) > 0
        ORDER BY weekly_activity_rate DESC
    """)
    
    try:
        result = db.session.execute(query).fetchall()
        
        schools = []
        for row in result:
            schools.append({
                'school_name': row.school_name,
                'active_students': row.active_students or 0,
                'total_activities': row.total_activities or 0,
                'weekly_activity_rate': round((row.weekly_activity_rate or 0) * 100, 1)
            })
        
        return schools
    except Exception as e:
        # SQLiteやその他のDBでDATE_SUB関数が使えない場合のフォールバック
        return []

@admin_bp.route('/analytics/school/<int:school_id>')
@login_required
@admin_required
def school_analytics(school_id):
    """学校別の利用状況分析"""
    school = School.query.get_or_404(school_id)
    
    # 学校別の統計データを取得
    school_stats = {
        'total_users': User.query.filter_by(school_id=school_id).count(),
        'active_users': User.query.filter_by(school_id=school_id).filter(User.created_at >= datetime.now() - timedelta(days=30)).count(),
        'total_activities': ActivityLog.query.join(User).filter(User.school_id == school_id).count(),
        'weekly_activities': get_school_weekly_activities(school_id),
        'class_rankings': get_school_class_rankings(school_id)
    }
    
    return render_template('admin/school_analytics.html', 
                         school=school, 
                         stats=school_stats)

def get_school_weekly_activities(school_id):
    """学校の週間活動数を取得"""
    week_ago = datetime.now() - timedelta(days=7)
    return ActivityLog.query.join(User).filter(
        User.school_id == school_id,
        ActivityLog.timestamp >= week_ago
    ).count()

def get_school_class_rankings(school_id):
    """学校内のクラス別ランキングを取得"""
    from sqlalchemy import func
    
    results = db.session.query(
        Class.name,
        func.count(ActivityLog.id).label('activity_count')
    ).join(User, Class.teacher_id == User.id)\
     .outerjoin(ActivityLog, User.id == ActivityLog.student_id)\
     .filter(User.school_id == school_id)\
     .group_by(Class.id, Class.name)\
     .order_by(func.count(ActivityLog.id).desc())\
     .limit(10).all()
    
    return [{'name': r.name, 'activity_count': r.activity_count} for r in results]

@admin_bp.route('/analytics/export/pdf')
@login_required 
@admin_required
def export_analytics_pdf():
    """分析レポートをPDFで出力"""
    try:
        # データ収集
        data = {
            'date': datetime.now().strftime('%Y年%m月%d日'),
            'daily_users': get_daily_active_users(30),
            'api_usage': get_api_usage_stats(),
            'school_stats': get_school_statistics()
        }
        
        # HTMLテンプレートをレンダリング
        html_content = render_template('admin/analytics_report_pdf.html', **data)
        
        # 簡易PDF生成（WeasyPrintなしの場合）
        from flask import Response
        return Response(
            html_content,
            mimetype='text/html',
            headers={
                'Content-Disposition': f'attachment; filename=analytics_report_{datetime.now().strftime("%Y%m%d")}.html'
            }
        )
        
    except Exception as e:
        flash(f'レポート生成エラー: {str(e)}', 'error')
        return redirect(url_for('admin_panel.analytics_dashboard'))

def get_all_schools_statistics():
    """全学校の統計データを取得"""
    return get_school_statistics()