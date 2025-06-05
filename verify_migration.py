#!/usr/bin/env python3
"""Blueprint移行の静的検証スクリプト（Flask不要）"""

import os
import re

def check_blueprint_routes():
    """Blueprintファイルのルート定義を検証"""
    
    blueprint_files = {
        'teacher': 'app/teacher/__init__.py',
        'student': 'app/student/__init__.py',
        'auth': 'app/auth/__init__.py',
        'admin': 'app/admin/__init__.py',
        'api': 'app/api/__init__.py'
    }
    
    print("=== Blueprint移行検証 ===")
    
    total_routes = 0
    for bp_name, file_path in blueprint_files.items():
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # @bp.route パターンを検索
            route_pattern = rf'@{bp_name}_bp\.route\('
            routes = re.findall(route_pattern, content)
            route_count = len(routes)
            total_routes += route_count
            
            print(f"[{bp_name}_bp] {route_count}ルート")
            
            # 特定のルートを確認
            if bp_name == 'teacher':
                curriculum_routes = re.findall(r'@teacher_bp\.route\([\'"].*curriculum.*[\'"]', content)
                print(f"  カリキュラム関連: {len(curriculum_routes)}ルート")
                
            elif bp_name == 'student':
                group_routes = re.findall(r'@student_bp\.route\([\'"].*group.*[\'"]', content)
                survey_routes = re.findall(r'@student_bp\.route\([\'"].*survey.*[\'"]', content)
                print(f"  グループ関連: {len(group_routes)}ルート")
                print(f"  アンケート関連: {len(survey_routes)}ルート")
        else:
            print(f"[{bp_name}_bp] ファイルが見つかりません: {file_path}")
    
    print(f"\n総ルート数: {total_routes}")
    
    return total_routes

def check_app_py():
    """app.pyの最小化を確認"""
    print("\n=== app.py確認 ===")
    
    if os.path.exists('app.py'):
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.count('\n') + 1
        print(f"行数: {lines}")
        
        if 'create_app' in content:
            print("✓ create_app()を使用")
        else:
            print("✗ create_app()が見つかりません")
        
        # 古いルート定義が残っていないか確認
        old_routes = re.findall(r'@app\.route\(', content)
        if old_routes:
            print(f"⚠ 古いルート定義が{len(old_routes)}個残っています")
        else:
            print("✓ 古いルート定義は削除済み")
    
    # バックアップファイルの確認
    backup_files = [f for f in os.listdir('.') if f.startswith('app.py.backup_')]
    if backup_files:
        print(f"✓ バックアップファイル: {backup_files[0]}")
    else:
        print("⚠ バックアップファイルが見つかりません")

def check_templates():
    """テンプレートファイルの確認"""
    print("\n=== テンプレート確認 ===")
    
    required_templates = [
        'interest_survey_edit.html',
        'interest_survey.html',
        'personality_survey_edit.html'
    ]
    
    for template in required_templates:
        template_path = f'templates/{template}'
        if os.path.exists(template_path):
            print(f"✓ {template}")
        else:
            print(f"✗ {template} が見つかりません")

def check_blueprint_registration():
    """Blueprint登録を確認"""
    print("\n=== Blueprint登録確認 ===")
    
    app_init_path = 'app/__init__.py'
    if os.path.exists(app_init_path):
        with open(app_init_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        blueprints = ['auth_bp', 'student_bp', 'teacher_bp', 'admin_bp', 'api_bp']
        
        for bp in blueprints:
            if f'register_blueprint({bp}' in content or f'register_blueprint(bp={bp}' in content:
                print(f"✓ {bp}")
            else:
                print(f"✗ {bp} が登録されていません")
    else:
        print("✗ app/__init__.py が見つかりません")

def main():
    print("QuestEd Blueprint移行検証\n")
    
    # 各種確認を実行
    check_blueprint_routes()
    check_app_py()
    check_templates()
    check_blueprint_registration()
    
    print("\n=== 検証完了 ===")
    print("詳細な動作確認には以下が必要です:")
    print("1. pip install -r requirements.txt")
    print("2. python run.py")

if __name__ == '__main__':
    main()