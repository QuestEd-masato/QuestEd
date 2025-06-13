# Access Control Vulnerabilities Analysis - QuestEd Application

## Executive Summary

This document details the access control vulnerabilities found in the QuestEd application. The analysis focused on identifying issues related to:
- Direct Object Reference vulnerabilities
- Missing authorization checks
- Insufficient role-based access control
- Data exposure through improper access controls

## Critical Findings

### 1. ✅ **SECURE: Activity Log Access Control**

**Location**: `/app/student/__init__.py`

The activity log functions properly implement authorization checks:

```python
@student_bp.route('/activity/<int:log_id>/delete')
@login_required
@student_required
def delete_activity(log_id):
    log = ActivityLog.query.get_or_404(log_id)
    
    # Proper authorization check
    if log.student_id != current_user.id:
        flash('この活動記録を削除する権限がありません。')
        return redirect(url_for('student.activities'))
```

**Status**: SECURE - Proper ownership validation is in place.

### 2. ✅ **SECURE: View Activity with Role-Based Access**

**Location**: `/app/student/__init__.py` - `view_activity()`

```python
def view_activity(activity_id):
    activity = ActivityLog.query.get_or_404(activity_id)
    
    if current_user.role == 'student':
        # Students can only view their own activities
        if activity.student_id != current_user.id:
            flash('この活動記録を閲覧する権限がありません。')
            return redirect(url_for('student.activities'))
    elif current_user.role == 'teacher':
        # Teachers can only view activities of students in their classes
        student_classes = ClassEnrollment.query.filter_by(student_id=activity.student_id).all()
        teacher_class_ids = [c.id for c in Class.query.filter_by(teacher_id=current_user.id).all()]
        
        student_class_ids = [e.class_id for e in student_classes]
        if not any(class_id in teacher_class_ids for class_id in student_class_ids):
            flash('この活動記録を閲覧する権限がありません。')
            return redirect(url_for('teacher.dashboard'))
```

**Status**: SECURE - Implements proper role-based access control.

### 3. ✅ **SECURE: Todo and Goal Access Control**

**Location**: `/app/student/__init__.py`

All Todo and Goal related functions properly check ownership:

```python
def edit_todo(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    if todo.student_id != current_user.id:
        flash('このToDoを編集する権限がありません。')
        return redirect(url_for('student.todos'))
```

**Status**: SECURE - Consistent ownership validation.

### 4. ✅ **SECURE: Theme Selection Access Control**

**Location**: `/app/api/__init__.py`

```python
@api_bp.route('/theme/<int:theme_id>/select', methods=['POST'])
@login_required
@api_limit()
def select_theme(theme_id):
    if current_user.role != 'student':
        return jsonify({'error': '学生のみアクセス可能です'}), 403
    
    theme = InquiryTheme.query.get_or_404(theme_id)
    
    # Proper ownership check
    if theme.student_id != current_user.id:
        return jsonify({'error': '権限がありません'}), 403
```

**Status**: SECURE - Proper role and ownership checks.

### 5. ⚠️ **POTENTIAL ISSUE: Export Evaluations API**

**Location**: `/app/api/__init__.py` - `export_evaluations()`

```python
@api_bp.route('/export/evaluations', methods=['POST'])
@login_required
def export_evaluations():
    if current_user.role != 'teacher':
        return jsonify({'error': '教師のみアクセス可能です'}), 403
    
    # ...
    if class_id:
        evaluations = []
        db_evaluations = StudentEvaluation.query.filter_by(class_id=class_id).all()
```

**Issue**: The function doesn't verify that the teacher owns the class before exporting evaluations.

**Recommendation**: Add ownership verification:
```python
if class_id:
    class_obj = Class.query.get(class_id)
    if not class_obj or class_obj.teacher_id != current_user.id:
        return jsonify({'error': 'このクラスの評価をエクスポートする権限がありません'}), 403
```

### 6. ✅ **SECURE: Survey Data Access**

Survey data is only accessed through the student's own dashboard and profile pages. No direct routes were found that allow accessing other students' survey data.

### 7. ✅ **SECURE: Class Enrollment Verification**

Teacher functions properly verify class ownership before allowing operations:

```python
def generate_evaluations(class_id):
    class_obj = Class.query.get_or_404(class_id)
    
    # Proper authorization check
    if class_obj.teacher_id != current_user.id:
        flash('このクラスの評価を生成する権限がありません。')
        return redirect(url_for('teacher.classes'))
```

### 8. ✅ **SECURE: Admin Functions**

Admin functions properly check for admin role and implement safe deletion with proper error handling:

```python
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Prevent self-deletion
    if user.id == current_user.id:
        flash('自分自身を削除することはできません。')
        return redirect(url_for('admin_panel.users'))
```

### 9. ✅ **SECURE: Chat History Access Control**

**Location**: `/app/api/__init__.py` - `chat()`

Chat history is properly filtered by the current user:

```python
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
```

**Status**: SECURE - Users can only access their own chat history.

## Summary of Findings

### Secure Implementations ✅
1. Student activity logs - proper ownership checks
2. Todo/Goal management - consistent authorization
3. Theme selection - role and ownership validation
4. Teacher class management - proper ownership verification
5. Admin user management - role-based access control
6. Survey data - no direct access routes found
7. Chat history - properly filtered by user ownership

### Areas Requiring Attention ⚠️
1. **Export Evaluations API** - Missing teacher-class ownership verification

### Recommendations

1. **Add ownership check to export_evaluations()**: Verify that the teacher owns the class before allowing evaluation export.

2. **Consider implementing a centralized authorization service**: Create a utility function to verify resource ownership consistently across all modules.

3. **Add audit logging**: Log all access attempts to sensitive resources for security monitoring.

4. **Implement rate limiting**: Already partially implemented but ensure all sensitive endpoints have rate limiting.

5. **Regular security reviews**: The current implementation is generally secure, but regular reviews should be conducted as new features are added.

## Overall Assessment

The QuestEd application demonstrates good security practices with consistent authorization checks across most modules. The identified issue with the export evaluations API is relatively minor and can be easily fixed. The application follows the principle of least privilege and implements proper role-based access control throughout.