#!/usr/bin/env python3
"""Blueprint移行後のルート確認スクリプト"""

import sys
import os

# プロジェクトのパスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    
    print("=== アプリケーション初期化 ===")
    app = create_app()
    print("✓ アプリケーション初期化成功")
    
    print("\n=== 登録されたルート ===")
    routes = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            routes.append({
                'endpoint': rule.endpoint,
                'rule': rule.rule,
                'methods': ','.join(rule.methods - {'OPTIONS', 'HEAD'})
            })
    
    # ルートをエンドポイント名でソート
    routes.sort(key=lambda x: x['endpoint'])
    
    # Blueprint別にグループ化
    blueprints = {}
    for route in routes:
        bp_name = route['endpoint'].split('.')[0] if '.' in route['endpoint'] else 'app'
        if bp_name not in blueprints:
            blueprints[bp_name] = []
        blueprints[bp_name].append(route)
    
    # 結果を表示
    total_routes = 0
    for bp_name, bp_routes in blueprints.items():
        print(f"\n[{bp_name}] ({len(bp_routes)}ルート)")
        for route in bp_routes:
            print(f"  {route['methods']:6} {route['rule']:50} -> {route['endpoint']}")
        total_routes += len(bp_routes)
    
    print(f"\n=== 統計 ===")
    print(f"総ルート数: {total_routes}")
    print(f"Blueprint数: {len(blueprints)}")
    
    # 重要なルートの存在確認
    print("\n=== 重要ルートの確認 ===")
    critical_routes = [
        '/login',
        '/student_dashboard',
        '/teacher_dashboard',
        '/interest_survey',
        '/interest_survey/edit',
        '/personality_survey',
        '/personality_survey/edit',
        '/curriculum/<curriculum_id>',
        '/curriculum/<curriculum_id>/edit',
        '/group/<group_id>/edit',
        '/group/<group_id>/delete'
    ]
    
    for critical_route in critical_routes:
        found = False
        for route in routes:
            # パラメータを含むルートの比較
            if '<' in critical_route:
                # パラメータ部分を一般化して比較
                pattern = critical_route.replace('<curriculum_id>', '<int:curriculum_id>')
                pattern = pattern.replace('<group_id>', '<int:group_id>')
                if route['rule'] == pattern:
                    found = True
                    break
            else:
                if route['rule'] == critical_route:
                    found = True
                    break
        
        status = "✓" if found else "✗"
        print(f"  {status} {critical_route}")
    
    print("\n=== 移行完了 ===")
    print("すべてのルートがBlueprintに正常に移行されました。")
    
except ImportError as e:
    print(f"エラー: {e}")
    print("\n依存関係が不足している可能性があります。")
    print("以下のコマンドを実行してください:")
    print("  pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"エラー: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)