# app/api/__init__.py
from flask import Blueprint, jsonify, request, session
from flask_login import login_required, current_user
import json
import logging

from app.models import db, ChatHistory, InquiryTheme, Class, StudentEvaluation, User
from app.ai import generate_chat_response
from app.utils.rate_limiting import smart_ai_limit, api_limit

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/chat', methods=['GET', 'POST'])
@login_required
@smart_ai_limit()
def chat():
    """チャットAPIエンドポイント - AIチャット応答を生成"""
    # GETリクエストの場合はエラーを返す
    if request.method == 'GET':
        return jsonify({"error": "このエンドポイントはPOSTメソッドのみ対応しています"}), 405
    
    try:
        # リクエストデータを取得
        if request.is_json:
            data = request.get_json()
            message = data.get('message', '')
            step_id = data.get('step', '')
            function_id = data.get('function', '')
            class_id = data.get('class_id')
        else:
            # フォームデータの場合
            message = request.form.get('message', '')
            step_id = request.form.get('step', '')
            function_id = request.form.get('function', '')
            class_id = request.form.get('class_id', type=int)
        
        # 教師ロールの場合は常に teacher_free ステップを使用
        if current_user.role == 'teacher':
            step_id = 'teacher_free'
            function_id = ''
        
        # メッセージが空でないことを確認
        if not message:
            return jsonify({"error": "メッセージが空です"}), 400
        
        # コンテキストの準備
        context_data = []
        
        # チャット履歴の取得（新しい順に10件）
        if class_id:
            chat_history = ChatHistory.query.filter_by(
                user_id=current_user.id,
                class_id=class_id
            ).order_by(ChatHistory.timestamp.desc()).limit(10).all()
        else:
            chat_history = ChatHistory.query.filter_by(
                user_id=current_user.id,
                class_id=None
            ).order_by(ChatHistory.timestamp.desc()).limit(10).all()
        
        # 古い順に並べ直してコンテキストに追加
        for chat in reversed(chat_history):
            context_data.append({
                'is_user': chat.is_user,
                'message': chat.message
            })
        
        # 選択中のテーマを取得（学生の場合）
        theme_context = None
        if current_user.role == 'student':
            if class_id:
                theme = InquiryTheme.query.filter_by(
                    student_id=current_user.id,
                    class_id=class_id,
                    is_selected=True
                ).first()
            else:
                theme = InquiryTheme.query.filter_by(
                    student_id=current_user.id, 
                    is_selected=True
                ).first()
            if theme:
                theme_context = f"現在の探究テーマ: {theme.title}"
                if theme.question:
                    theme_context += f"\n探究の問い: {theme.question}"
        
        # メッセージにテーマ情報を追加
        full_message = message
        if theme_context:
            full_message = f"{theme_context}\n\nユーザーの質問: {message}"
        
        # AI応答を生成
        ai_response = generate_chat_response(full_message, context_data)
        
        # チャット履歴を保存
        # ユーザーのメッセージを保存
        user_chat = ChatHistory(
            user_id=current_user.id,
            class_id=class_id,
            message=message, 
            is_user=True
        )
        db.session.add(user_chat)
        
        # AIの返答を保存
        ai_chat = ChatHistory(
            user_id=current_user.id,
            class_id=class_id,
            message=ai_response, 
            is_user=False
        )
        db.session.add(ai_chat)
        
        db.session.commit()
        
        return jsonify({
            "message": ai_response,
            "status": "success"
        })
        
    except Exception as e:
        logging.error(f"チャットAPIエラー: {str(e)}")
        db.session.rollback()
        return jsonify({
            "error": "エラーが発生しました。もう一度お試しください。",
            "status": "error"
        }), 500

@api_bp.route('/teacher/first_class', methods=['GET'])
@login_required
def teacher_first_class():
    """教師の最初のクラスを取得"""
    if current_user.role != 'teacher':
        return jsonify({'error': '教師のみアクセス可能です'}), 403
    
    # 教師の最初のクラスを取得
    first_class = Class.query.filter_by(teacher_id=current_user.id).first()
    if first_class:
        return jsonify({
            'class_id': first_class.id,
            'class_name': first_class.name
        })
    else:
        return jsonify({'class_id': None})

@api_bp.route('/export/evaluations', methods=['POST'])
@login_required
def export_evaluations():
    """評価データのエクスポート"""
    if current_user.role != 'teacher':
        return jsonify({'error': '教師のみアクセス可能です'}), 403
    
    try:
        # セッションから評価データを取得
        evaluations_json = session.get('evaluations')
        class_name = session.get('class_name', 'クラス')
        class_id = session.get('class_id')
        
        if not evaluations_json:
            # セッションにデータがない場合は、class_idから取得を試みる
            if class_id:
                evaluations = []
                db_evaluations = StudentEvaluation.query.filter_by(class_id=class_id).all()
                
                for eval_obj in db_evaluations:
                    student = User.query.get(eval_obj.student_id)
                    if student:
                        evaluations.append({
                            'student_name': student.username,
                            'evaluation': eval_obj.evaluation_text
                        })
            else:
                return jsonify({'error': 'エクスポートするデータがありません'}), 400
        else:
            evaluations = json.loads(evaluations_json)
        
        # レスポンスデータを作成
        return jsonify({
            'evaluations': evaluations,
            'class_name': class_name,
            'status': 'success'
        })
        
    except Exception as e:
        logging.error(f"評価エクスポートエラー: {str(e)}")
        return jsonify({
            'error': 'エクスポート中にエラーが発生しました',
            'status': 'error'
        }), 500

@api_bp.route('/theme/<int:theme_id>/select', methods=['POST'])
@login_required
@api_limit()
def select_theme(theme_id):
    """テーマ選択API"""
    if current_user.role != 'student':
        return jsonify({'error': '学生のみアクセス可能です'}), 403
    
    theme = InquiryTheme.query.get_or_404(theme_id)
    
    # 権限チェック
    if theme.student_id != current_user.id:
        return jsonify({'error': '権限がありません'}), 403
    
    try:
        # 既存の選択を解除
        InquiryTheme.query.filter_by(
            student_id=current_user.id, 
            is_selected=True
        ).update({'is_selected': False})
        
        # 新しいテーマを選択
        theme.is_selected = True
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'テーマ「{theme.title}」を選択しました'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"テーマ選択エラー: {str(e)}")
        return jsonify({
            'error': 'テーマの選択に失敗しました',
            'status': 'error'
        }), 500

@api_bp.route('/todo/<int:todo_id>/toggle', methods=['POST'])
@login_required
@api_limit()
def toggle_todo(todo_id):
    """To Do完了状態切り替えAPI"""
    if current_user.role != 'student':
        return jsonify({'error': '学生のみアクセス可能です'}), 403
    
    from app.models import Todo
    todo = Todo.query.get_or_404(todo_id)
    
    # 権限チェック
    if todo.student_id != current_user.id:
        return jsonify({'error': '権限がありません'}), 403
    
    try:
        # 完了状態を切り替え
        todo.is_completed = not todo.is_completed
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'is_completed': todo.is_completed,
            'message': f'To Doを{"完了" if todo.is_completed else "未完了"}にしました'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"To Do切り替えエラー: {str(e)}")
        return jsonify({
            'error': 'To Doの更新に失敗しました',
            'status': 'error'
        }), 500

@api_bp.route('/goal/<int:goal_id>/progress', methods=['POST'])
@login_required
@api_limit()
def update_goal_progress(goal_id):
    """目標進捗更新API"""
    if current_user.role != 'student':
        return jsonify({'error': '学生のみアクセス可能です'}), 403
    
    from app.models import Goal
    goal = Goal.query.get_or_404(goal_id)
    
    # 権限チェック
    if goal.student_id != current_user.id:
        return jsonify({'error': '権限がありません'}), 403
    
    try:
        data = request.get_json()
        progress = data.get('progress', 0)
        
        # 進捗を0-100の範囲に制限
        goal.progress = max(0, min(100, int(progress)))
        
        # 100%になったら完了フラグを立てる
        if goal.progress >= 100:
            goal.is_completed = True
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'progress': goal.progress,
            'is_completed': goal.is_completed,
            'message': f'進捗を{goal.progress}%に更新しました'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"目標進捗更新エラー: {str(e)}")
        return jsonify({
            'error': '進捗の更新に失敗しました',
            'status': 'error'
        }), 500

@api_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """ユーザー統計情報を取得"""
    stats = {}
    
    if current_user.role == 'admin':
        # 管理者用統計
        stats = {
            'total_users': User.query.count(),
            'total_students': User.query.filter_by(role='student').count(),
            'total_teachers': User.query.filter_by(role='teacher').count(),
            'total_classes': Class.query.count(),
            'pending_approvals': User.query.filter_by(
                role='student', 
                email_confirmed=True, 
                is_approved=False
            ).count()
        }
        
    elif current_user.role == 'teacher':
        # 教師用統計
        from app.models import ClassEnrollment
        
        classes = Class.query.filter_by(teacher_id=current_user.id).all()
        total_students = 0
        for class_obj in classes:
            total_students += ClassEnrollment.query.filter_by(class_id=class_obj.id).count()
        
        stats = {
            'total_classes': len(classes),
            'total_students': total_students,
            'pending_approvals': User.query.filter_by(
                role='student',
                school_id=current_user.school_id,
                email_confirmed=True,
                is_approved=False
            ).count()
        }
        
    elif current_user.role == 'student':
        # 学生用統計
        from app.models import Todo, Goal, ActivityLog
        
        stats = {
            'total_activities': ActivityLog.query.filter_by(student_id=current_user.id).count(),
            'pending_todos': Todo.query.filter_by(
                student_id=current_user.id, 
                is_completed=False
            ).count(),
            'active_goals': Goal.query.filter_by(
                student_id=current_user.id, 
                is_completed=False
            ).count(),
            'completed_goals': Goal.query.filter_by(
                student_id=current_user.id, 
                is_completed=True
            ).count()
        }
    
    return jsonify(stats)