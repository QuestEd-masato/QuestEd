#!/usr/bin/env python
"""
adminテンプレートのurl_forを修正するスクリプト
"""
import re
import os

# 修正マッピング
ADMIN_URL_MAPPINGS = {
    # Schools
    'create_school': 'admin.admin_create_school',
    'edit_school': 'admin.admin_edit_school',
    'delete_school': 'admin.admin_delete_school',
    'school.list_schools': 'admin.admin_schools',
    
    # Academic (年度・クラス管理) - 実際のルートが不明なので仮定
    'academic.list_years': 'admin.admin_school_years',
    'academic.create_year': 'admin.admin_create_school_year',
    'academic.edit_year': 'admin.admin_edit_school_year',
    'academic.set_current_year': 'admin.admin_set_current_year',
    'academic.list_classes': 'admin.admin_class_groups',
    'academic.create_class': 'admin.admin_create_class_group',
    
    # Enrollment
    'enrollment.list_students': 'admin.admin_student_enrollment',
    'enrollment.download_template': 'admin.download_user_template',
}

def fix_url_for_in_file(filepath):
    """ファイル内のurl_forを修正"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    for old_name, new_name in ADMIN_URL_MAPPINGS.items():
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
    admin_templates_dir = '/home/masat/claude-projects/quested-app/templates/admin'
    fixed_files = []
    
    for file in os.listdir(admin_templates_dir):
        if file.endswith('.html'):
            filepath = os.path.join(admin_templates_dir, file)
            if fix_url_for_in_file(filepath):
                fixed_files.append(filepath)
    
    print(f"Fixed {len(fixed_files)} files:")
    for file in fixed_files:
        print(f"  - {file}")

if __name__ == '__main__':
    main()