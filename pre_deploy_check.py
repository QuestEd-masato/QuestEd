#!/usr/bin/env python3
"""
QuestEd v1.4.1 デプロイ前チェックスクリプト
"""
import sys
import os
import importlib.util

def check_import_safety():
    """循環インポートのチェック"""
    print("🔍 Import安全性チェック...")
    
    try:
        # 基本的なインポートテスト
        sys.path.insert(0, '.')
        
        # Extensions first
        from extensions import db
        print("✅ extensions.db import OK")
        
        # Config check
        from config import Config
        print("✅ config.Config import OK")
        
        # Models check
        from app.models import User, Subject
        print("✅ app.models import OK")
        
        # App factory check
        from app import create_app
        print("✅ app.create_app import OK")
        
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def check_celery_dependencies():
    """Celery依存関係チェック"""
    print("\n🔍 Celery依存関係チェック...")
    
    try:
        import celery
        print(f"✅ Celery version: {celery.__version__}")
        
        from celery.schedules import crontab
        print("✅ crontab import OK")
        
        # Test crontab creation
        schedule = crontab(hour=18, minute=0)
        print(f"✅ Schedule creation OK: {schedule}")
        
        return True
    except ImportError as e:
        print(f"❌ Celery not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Celery error: {e}")
        return False

def check_file_security():
    """ファイルセキュリティ機能チェック"""
    print("\n🔍 ファイルセキュリティ機能チェック...")
    
    try:
        # Required modules
        import imghdr
        print("✅ imghdr OK")
        
        import uuid
        print("✅ uuid OK")
        
        import hashlib
        print("✅ hashlib OK")
        
        from werkzeug.utils import secure_filename
        print("✅ werkzeug.secure_filename OK")
        
        # Check if python-magic is available
        try:
            import magic
            print("✅ python-magic available")
        except ImportError:
            print("⚠️  python-magic not available (will use fallback)")
        
        # Test file validator import
        from app.utils.file_security import file_validator
        print("✅ FileValidator import OK")
        
        return True
    except Exception as e:
        print(f"❌ File security error: {e}")
        return False

def check_migration_consistency():
    """マイグレーションファイル整合性チェック"""
    print("\n🔍 マイグレーション整合性チェック...")
    
    try:
        migration_file = "migrations/versions/c6847f391ffe_initial_migration.py"
        if os.path.exists(migration_file):
            with open(migration_file, 'r') as f:
                content = f.read()
                if "revision = 'c6847f391ffe'" in content:
                    print("✅ Migration revision ID consistent")
                    return True
                else:
                    print("❌ Migration revision ID mismatch")
                    return False
        else:
            print("❌ Migration file not found")
            return False
    except Exception as e:
        print(f"❌ Migration check error: {e}")
        return False

def check_config_safety():
    """設定ファイル安全性チェック"""
    print("\n🔍 設定ファイル安全性チェック...")
    
    try:
        from config import Config
        
        # Check if Celery config is properly set
        if hasattr(Config, 'CELERY_BEAT_SCHEDULE'):
            schedule = Config.CELERY_BEAT_SCHEDULE
            print(f"✅ CELERY_BEAT_SCHEDULE found: {schedule}")
            
            if 'daily-reports' in schedule:
                daily_task = schedule['daily-reports']
                if 'schedule' in daily_task:
                    print(f"✅ Daily report schedule: {daily_task['schedule']}")
                    return True
                else:
                    print("❌ Daily report schedule missing")
                    return False
            else:
                print("❌ daily-reports task missing")
                return False
        else:
            print("❌ CELERY_BEAT_SCHEDULE missing")
            return False
    except Exception as e:
        print(f"❌ Config check error: {e}")
        return False

def check_new_files():
    """新規ファイルの存在チェック"""
    print("\n🔍 新規ファイル存在チェック...")
    
    required_files = [
        "app/utils/file_security.py",
        "manage_celery.py",
        "SAFE_DEPLOY_v1.4.1.md"
    ]
    
    all_ok = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            all_ok = False
    
    return all_ok

def main():
    """メインチェック関数"""
    print("🚀 QuestEd v1.4.1 デプロイ前チェック開始")
    print("=" * 50)
    
    checks = [
        ("Import安全性", check_import_safety),
        ("Celery依存関係", check_celery_dependencies),
        ("ファイルセキュリティ", check_file_security),
        ("マイグレーション整合性", check_migration_consistency),
        ("設定ファイル", check_config_safety),
        ("新規ファイル", check_new_files)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} チェック失敗: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("📊 チェック結果サマリー")
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {name}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 すべてのチェックが通過しました！")
        print("👍 デプロイ準備完了です")
        return 0
    else:
        print("⚠️  一部のチェックが失敗しました")
        print("🔧 失敗項目を修正してからデプロイしてください")
        return 1

if __name__ == "__main__":
    sys.exit(main())