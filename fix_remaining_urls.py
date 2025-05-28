#!/usr/bin/env python
"""
残りのurl_forを修正するスクリプト
"""
import re
import os

# 追加の修正マッピング
ADDITIONAL_MAPPINGS = {
    'student_view_main_themes': 'student.student_main_themes',
    'chat_page': 'api.chat',
    'classes': 'teacher.teacher_classes',  # コンテキストによって異なる可能性あり
    'pending_users': 'teacher.teacher_pending_users',
    'view_curriculums': 'teacher.curriculums',
    'new_activity': 'student.create_activity',
    'delete_activity': 'student.delete_activity',
    'interest_survey_edit': 'student.interest_survey',
    'index': 'main.index',  # もしあれば
}

def fix_url_for_in_file(filepath):
    """ファイル内のurl_forを修正"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    for old_name, new_name in ADDITIONAL_MAPPINGS.items():
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
    
    print(f"Fixed {len(fixed_files)} additional files:")
    for file in fixed_files:
        print(f"  - {file}")

if __name__ == '__main__':
    main()