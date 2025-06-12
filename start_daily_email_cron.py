#!/usr/bin/env python3
"""
Celeryの代替として、システムのcronを使用した日報送信
毎日17:00（日本時間）に実行されるスクリプト
"""
import sys
import os
import subprocess
from pathlib import Path

def setup_cron_job():
    """システムcronに日報送信ジョブを追加"""
    script_path = Path(__file__).parent / "scripts" / "send_daily_summary.py"
    python_path = sys.executable
    
    # cronエントリ
    cron_command = f"0 17 * * * cd {Path(__file__).parent} && {python_path} {script_path} >> /tmp/quested_daily_email.log 2>&1"
    
    print("=== QuestEd 日報メール cron設定 ===")
    print(f"実行スクリプト: {script_path}")
    print(f"実行時間: 毎日 17:00（日本時間）")
    print(f"Cronエントリ: {cron_command}")
    print()
    
    # 現在のcronを確認
    try:
        current_cron = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        existing_crons = current_cron.stdout if current_cron.returncode == 0 else ""
    except:
        existing_crons = ""
    
    # 既存のQuestEd cronをチェック
    if "send_daily_summary.py" in existing_crons:
        print("✅ QuestEd日報送信のcronが既に設定されています")
        print("現在の設定:")
        for line in existing_crons.split('\n'):
            if "send_daily_summary.py" in line:
                print(f"  {line}")
        return True
    
    # 新しいcronを追加
    confirm = input("システムcronに日報送信ジョブを追加しますか？ (y/N): ").strip().lower()
    if confirm in ['y', 'yes']:
        try:
            # 新しいcronを追加
            new_cron = existing_crons + "\n" + cron_command + "\n"
            process = subprocess.run(['crontab', '-'], input=new_cron, text=True)
            
            if process.returncode == 0:
                print("✅ Cronジョブが正常に追加されました")
                print("ログファイル: /tmp/quested_daily_email.log")
                return True
            else:
                print("❌ Cronジョブの追加に失敗しました")
                return False
        except Exception as e:
            print(f"❌ エラー: {e}")
            return False
    else:
        print("⏭️  Cronジョブの追加をスキップしました")
        print("手動でcronを設定する場合は、以下のコマンドを実行してください：")
        print(f"echo '{cron_command}' | crontab -")
        return False

def show_manual_setup():
    """手動セットアップの手順を表示"""
    script_path = Path(__file__).parent / "scripts" / "send_daily_summary.py"
    python_path = sys.executable
    
    print("\n=== 手動セットアップ手順 ===")
    print("1. メール設定の確認:")
    print("   .envファイルに以下を設定してください：")
    print("   EMAIL_METHOD=smtp")
    print("   SMTP_USER=your-email@gmail.com")
    print("   SMTP_PASSWORD=your-app-password")
    print()
    print("2. メール送信テスト:")
    print(f"   python3 {Path(__file__).parent}/test_email_simple.py")
    print()
    print("3. 手動日報送信テスト:")
    print(f"   python3 {script_path}")
    print()
    print("4. Cron設定（手動）:")
    print(f"   crontab -e")
    print(f"   以下の行を追加:")
    print(f"   0 17 * * * cd {Path(__file__).parent} && {python_path} {script_path} >> /tmp/quested_daily_email.log 2>&1")

if __name__ == '__main__':
    print("🚀 QuestEd 日報メール設定ツール")
    print()
    
    # 依存関係チェック
    script_exists = (Path(__file__).parent / "scripts" / "send_daily_summary.py").exists()
    if not script_exists:
        print("❌ send_daily_summary.py が見つかりません")
        sys.exit(1)
    
    # Cronセットアップ
    success = setup_cron_job()
    
    # 手動セットアップ手順を表示
    show_manual_setup()
    
    if success:
        print("\n✅ セットアップ完了！")
    else:
        print("\n⚠️  手動でセットアップを完了してください")