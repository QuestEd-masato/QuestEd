#!/usr/bin/env python
"""
url_forをBlueprint対応に修正するスクリプト
"""
import re
import os

# 修正するマッピング
URL_FOR_MAPPING = {
    # Student routes
    'view_themes': 'student.view_themes',
    'activities': 'student.activities',
    'surveys': 'student.surveys',
    'todos': 'student.todos',
    'goals': 'student.goals',
    'new_goal': 'student.new_goal',
    'edit_goal': 'student.edit_goal',
    'new_todo': 'student.new_todo',
    'edit_todo': 'student.edit_todo',
    'create_activity': 'student.create_activity',
    'edit_activity': 'student.edit_activity',
    'view_activity': 'student.view_activity',
    'interest_survey': 'student.interest_survey',
    'personality_survey': 'student.personality_survey',
    'personality_survey_edit': 'student.personality_survey_edit',
    'student_classes': 'student.student_classes',
    'view_themes': 'student.view_themes',
    'student_themes': 'student.student_themes',
    'generate_theme': 'student.generate_theme',
    'create_personal_theme': 'student.create_personal_theme',
    'submit_milestone': 'student.submit_milestone',
    'student_view_milestone': 'student.student_view_milestone',
    'student_main_themes': 'student.student_main_themes',
    
    # Teacher routes
    'teacher_themes': 'teacher.teacher_themes',
    'create_class': 'teacher.create_class',
    'edit_class': 'teacher.edit_class',
    'view_class': 'teacher.view_class',
    'teacher_classes': 'teacher.teacher_classes',
    'class_details': 'teacher.class_details',
    'create_milestone': 'teacher.create_milestone',
    'edit_milestone': 'teacher.edit_milestone',
    'view_milestone': 'teacher.view_milestone',
    'teacher_import_students': 'teacher.teacher_import_students',
    'add_students': 'teacher.add_students',
    'add_student': 'teacher.add_student',
    'evaluate_students': 'teacher.evaluate_students',
    'create_curriculum': 'teacher.create_curriculum',
    'edit_curriculum': 'teacher.edit_curriculum',
    'view_curriculum': 'teacher.view_curriculum',
    'curriculums': 'teacher.curriculums',
    'upload_curriculum': 'teacher.upload_curriculum',
    'create_main_theme': 'teacher.create_main_theme',
    'edit_main_theme': 'teacher.edit_main_theme',
    'main_themes': 'teacher.main_themes',
    'create_group': 'teacher.create_group',
    'edit_group': 'teacher.edit_group',
    'view_group': 'teacher.view_group',
    'view_groups': 'teacher.view_groups',
    'teacher_import_users': 'teacher.teacher_import_users',
    'teacher_pending_users': 'teacher.teacher_pending_users',
    
    # Admin routes
    'admin_schools': 'admin.admin_schools',
    'admin_create_school': 'admin.admin_create_school',
    'admin_edit_school': 'admin.admin_edit_school',
    'admin_school_detail': 'admin.admin_school_detail',
    'admin_school_years': 'admin.admin_school_years',
    'admin_class_groups': 'admin.admin_class_groups',
    'admin_users': 'admin.admin_users',
    'admin_import_users': 'admin.admin_import_users',
    'admin_student_enrollment': 'admin.admin_student_enrollment',
    'admin_import_students': 'admin.admin_import_students',
    'admin_promote_students': 'admin.admin_promote_students',
    
    # API routes
    'chat': 'api.chat',
    'export_activities_pdf': 'api.export_activities_pdf',
}

def fix_url_for_in_file(filepath):
    """ファイル内のurl_forを修正"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    for old_name, new_name in URL_FOR_MAPPING.items():
        # url_for('old_name') -> url_for('new_name')
        pattern = rf"url_for\(['\"]({old_name})['\"]"
        replacement = rf"url_for('{new_name}'"
        content = re.sub(pattern, replacement, content)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    templates_dir = '/home/masat/claude-projects/quested-app/templates'
    fixed_files = []
    
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                if fix_url_for_in_file(filepath):
                    fixed_files.append(filepath)
    
    print(f"Fixed {len(fixed_files)} files:")
    for file in fixed_files:
        print(f"  - {file}")

if __name__ == '__main__':
    main()