import json
import os
from datetime import datetime

class VersionManager:
    def __init__(self):
        self.version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'version.json')
        
    def get_current_version(self):
        """現在のバージョン情報を取得"""
        try:
            with open(self.version_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    'version': data.get('version', '0.0.0'),
                    'updated_at': data.get('updated_at'),
                    'changes': data.get('changes', [])
                }
        except FileNotFoundError:
            return {
                'version': '0.0.0',
                'updated_at': None,
                'changes': []
            }
    
    def increment_version(self, version_type='patch', changes=None):
        """バージョンをインクリメント"""
        current = self.get_current_version()
        major, minor, patch = map(int, current['version'].split('.'))
        
        if version_type == 'major':
            major += 1
            minor = patch = 0
        elif version_type == 'minor':
            minor += 1
            patch = 0
        else:
            patch += 1
        
        new_version = f'{major}.{minor}.{patch}'
        
        # 変更履歴に追加
        change_entry = {
            'version': new_version,
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'changes': changes or []
        }
        
        # バージョン情報を更新
        version_data = {
            'version': new_version,
            'updated_at': datetime.utcnow().isoformat() + 'Z',
            'changes': [change_entry] + current.get('changes', [])
        }
        
        with open(self.version_file, 'w', encoding='utf-8') as f:
            json.dump(version_data, f, indent=2, ensure_ascii=False)
        
        return version_data
    
    def get_version_history(self):
        """バージョン履歴を取得"""
        current = self.get_current_version()
        return current.get('changes', [])
    
    def create_migration_with_version(self, message):
        """バージョン付きマイグレーション名を生成"""
        current = self.get_current_version()
        version = current['version'].replace('.', '_')
        migration_name = f"v{version}_{message}"
        
        # Flaskマイグレーションコマンドを実行
        cmd = f"flask db revision -m '{migration_name}'"
        return cmd, migration_name


# Flaskアプリケーションにバージョン情報を追加するためのヘルパー関数
def init_version(app):
    """Flaskアプリケーションにバージョン情報を初期化"""
    version_manager = VersionManager()
    version_info = version_manager.get_current_version()
    
    app.config['APP_VERSION'] = version_info['version']
    app.config['APP_VERSION_DATE'] = version_info['updated_at']
    
    # Jinja2テンプレートでバージョン情報を使えるようにする
    @app.context_processor
    def inject_version():
        return {
            'app_version': version_info['version'],
            'app_version_date': version_info['updated_at']
        }
    
    return version_manager