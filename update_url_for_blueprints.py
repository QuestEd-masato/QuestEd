#!/usr/bin/env python3
"""
Script to update url_for calls in templates to use Blueprint prefixes
"""
import os
import re
from pathlib import Path

# Define endpoint mappings to blueprints
BLUEPRINT_MAPPINGS = {
    # Auth Blueprint (assuming these will be moved to auth blueprint)
    'auth': [
        'login', 'logout', 'register', 'forgot_password', 'reset_password',
        'verify_email', 'confirm_email', 'resend_verification', 'change_password',
        'awaiting_approval'
    ],
    
    # Admin Blueprint
    'admin': [
        'admin_dashboard', 'admin_users', 'admin_delete_user', 'admin_schools',
        'admin_school_detail', 'create_school', 'edit_school', 'delete_school',
        'import_users', 'download_user_template', 'admin_access'
    ],
    
    # Academic Blueprint (from core.academic)
    'academic': [
        'create_class', 'edit_class', 'delete_class', 'view_class', 'class_details',
        'classes', 'add_students', 'remove_student', 'view_groups', 'create_group',
        'view_group', 'edit_group', 'delete_group', 'join_group', 'leave_group',
        'remove_group_member', 'create_year', 'edit_year', 'list_classes', 
        'list_years', 'set_current_year'
    ],
    
    # School Blueprint (from core.school)
    'school': [
        'list_schools'
    ],
    
    # Enrollment Blueprint (from core.enrollment)
    'enrollment': [
        'import_students', 'list_students', 'edit_student', 'download_template'
    ],
    
    # Teacher Blueprint
    'teacher': [
        'teacher_dashboard', 'pending_users', 'approve_user', 'generate_evaluations',
        'create_milestone', 'edit_milestone', 'delete_milestone', 'view_milestone',
        'create_curriculum_form', 'import_curriculum', 'generate_curriculum',
        'view_curriculums', 'view_curriculum', 'edit_curriculum', 'delete_curriculum',
        'export_curriculum', 'download_curriculum_template'
    ],
    
    # Student Blueprint
    'student': [
        'student_dashboard', 'student_view_main_themes', 'submit_milestone',
        'surveys', 'interest_survey', 'interest_survey_edit', 
        'personality_survey', 'personality_survey_edit'
    ],
    
    # Activity Blueprint
    'activity': [
        'activities', 'new_activity', 'view_activity', 'edit_activity', 
        'delete_activity', 'export_activities', 'create_activity', 'add_feedback'
    ],
    
    # Theme Blueprint
    'theme': [
        'view_themes', 'view_main_themes', 'create_main_theme', 'edit_main_theme',
        'delete_main_theme', 'create_personal_theme', 'generate_theme', 
        'edit_theme', 'select_theme', 'teacher_themes'
    ],
    
    # Todo Blueprint
    'todo': [
        'todos', 'new_todo', 'edit_todo', 'delete_todo', 'toggle_todo'
    ],
    
    # Goal Blueprint
    'goal': [
        'goals', 'new_goal', 'edit_goal', 'delete_goal'
    ],
    
    # Chat Blueprint
    'chat': [
        'chat_page'
    ],
    
    # Main routes (no blueprint prefix)
    'main': [
        'index'
    ]
}

# Create reverse mapping
ENDPOINT_TO_BLUEPRINT = {}
for blueprint, endpoints in BLUEPRINT_MAPPINGS.items():
    for endpoint in endpoints:
        ENDPOINT_TO_BLUEPRINT[endpoint] = blueprint

def update_url_for_in_file(filepath):
    """Update url_for calls in a single file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    updated = False
    
    # Pattern to match url_for calls
    # Matches: url_for('endpoint_name') or url_for("endpoint_name")
    pattern = r'url_for\s*\(\s*[\'"]([^\'"]+)[\'"]'
    
    def replace_url_for(match):
        nonlocal updated
        endpoint = match.group(1)
        
        # Skip if already has a blueprint prefix
        if '.' in endpoint:
            return match.group(0)
        
        # Check if endpoint needs a blueprint prefix
        if endpoint in ENDPOINT_TO_BLUEPRINT:
            blueprint = ENDPOINT_TO_BLUEPRINT[endpoint]
            if blueprint != 'main':  # Don't add prefix for main blueprint
                updated = True
                return f"url_for('{blueprint}.{endpoint}'"
        
        return match.group(0)
    
    # Replace all url_for calls
    content = re.sub(pattern, replace_url_for, content)
    
    if updated:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    
    return False

def main():
    """Main function to update all template files"""
    templates_dir = Path('/home/masat/claude-projects/quested-app/templates')
    
    updated_files = []
    
    # Walk through all HTML files in templates directory
    for filepath in templates_dir.rglob('*.html'):
        if update_url_for_in_file(filepath):
            updated_files.append(filepath)
    
    print(f"Updated {len(updated_files)} files:")
    for filepath in updated_files:
        print(f"  - {filepath.relative_to(templates_dir)}")
    
    # Print summary of endpoints by blueprint
    print("\nEndpoint mappings by blueprint:")
    for blueprint, endpoints in BLUEPRINT_MAPPINGS.items():
        if endpoints:
            print(f"\n{blueprint}:")
            for endpoint in sorted(endpoints):
                print(f"  - {endpoint}")

if __name__ == '__main__':
    main()