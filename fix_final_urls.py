#!/usr/bin/env python
"""
最後のurl_for修正スクリプト
"""
import re
import os

# 最終的な修正マッピング
FINAL_MAPPINGS = {
    # Teacher routes
    'teacher_dashboard': 'teacher.dashboard',
    'view_main_themes': 'teacher.main_themes',
    'delete_main_theme': 'teacher.delete_main_theme',
    'delete_class': 'teacher.delete_class',
    'create_curriculum_form': 'teacher.create_curriculum',
    'generate_curriculum': 'teacher.generate_curriculum',
    'import_curriculum': 'teacher.import_curriculum',
    'export_curriculum': 'teacher.export_curriculum',
    'delete_curriculum': 'teacher.delete_curriculum',
    'generate_evaluations': 'teacher.generate_evaluations',
    
    # Student routes
    'student_dashboard': 'student.dashboard',
    'delete_goal': 'student.delete_goal',
    'toggle_todo': 'student.toggle_todo',
    'complete_todo': 'student.complete_todo',
    'delete_todo': 'student.delete_todo',
    
    # API routes
    'export_activities': 'api.export_activities',
}

def fix_url_for_in_file(filepath):
    """ファイル内のurl_forを修正"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    for old_name, new_name in FINAL_MAPPINGS.items():
        # url_for('old_name' の形式を修正
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