#!/usr/bin/env python3
"""
Celery管理スクリプト
"""
import os
import sys
import click
import logging

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.tasks import CELERY_AVAILABLE

@click.group()
def cli():
    """Celery管理ツール"""
    pass

@cli.command()
def worker():
    """Celery Workerを起動"""
    if not CELERY_AVAILABLE:
        click.echo("❌ Celeryが利用できません。 'pip install celery redis' を実行してください。")
        sys.exit(1)
    
    try:
        from celery_worker import celery
        click.echo("🚀 Celery Worker を起動中...")
        celery.worker_main(['worker', '--loglevel=info'])
    except Exception as e:
        click.echo(f"❌ Worker起動エラー: {e}")
        sys.exit(1)

@cli.command()
def beat():
    """Celery Beat（スケジューラー）を起動"""
    if not CELERY_AVAILABLE:
        click.echo("❌ Celeryが利用できません。")
        sys.exit(1)
    
    try:
        from celery_worker import celery
        click.echo("📅 Celery Beat を起動中...")
        celery.worker_main(['beat', '--loglevel=info'])
    except Exception as e:
        click.echo(f"❌ Beat起動エラー: {e}")
        sys.exit(1)

@cli.command()
def status():
    """Celery Workerの状態を確認"""
    if not CELERY_AVAILABLE:
        click.echo("❌ Celeryが利用できません。")
        return
    
    try:
        from celery_worker import celery
        inspect = celery.control.inspect()
        
        # アクティブなWorkerを確認
        workers = inspect.stats()
        if workers:
            click.echo("✅ アクティブなWorker:")
            for worker_name, stats in workers.items():
                click.echo(f"  - {worker_name}")
        else:
            click.echo("⚠️  アクティブなWorkerが見つかりません")
        
        # アクティブなタスクを確認
        active_tasks = inspect.active()
        if active_tasks:
            click.echo("\n📋 実行中のタスク:")
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    click.echo(f"  - {task['name']} (ID: {task['id']})")
        else:
            click.echo("\n💤 実行中のタスクはありません")
            
    except Exception as e:
        click.echo(f"❌ 状態確認エラー: {e}")

@cli.command()
def test_daily_report():
    """日次レポートのテスト実行"""
    if not CELERY_AVAILABLE:
        click.echo("⚠️  Celeryが利用できないため、直接実行します...")
        from app.tasks.daily_report import main
        main()
        return
    
    try:
        from app.tasks.daily_report import generate_daily_reports
        click.echo("🧪 日次レポートのテスト実行...")
        
        # 非同期タスクとして実行
        result = generate_daily_reports.delay()
        click.echo(f"タスクID: {result.id}")
        
        # 結果を待機
        click.echo("結果を待機中...")
        task_result = result.get(timeout=60)
        
        if task_result['success']:
            click.echo(f"✅ {task_result['message']}")
        else:
            click.echo(f"❌ {task_result['message']}")
            
    except Exception as e:
        click.echo(f"❌ テスト実行エラー: {e}")

@cli.command()
def sync_daily_report():
    """日次レポートの同期実行（Celeryを使わない）"""
    click.echo("📊 日次レポートを同期実行中...")
    try:
        from app.tasks.daily_report import main
        main()
    except Exception as e:
        click.echo(f"❌ 実行エラー: {e}")

@cli.command()
def install_service():
    """systemdサービスファイルを生成"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    python_path = sys.executable
    
    # Celery Worker サービス
    worker_service = f"""[Unit]
Description=QuestEd Celery Worker
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory={current_dir}
Environment=PATH={os.path.dirname(python_path)}
ExecStart={python_path} manage_celery.py worker
Restart=always

[Install]
WantedBy=multi-user.target
"""

    # Celery Beat サービス
    beat_service = f"""[Unit]
Description=QuestEd Celery Beat
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory={current_dir}
Environment=PATH={os.path.dirname(python_path)}
ExecStart={python_path} manage_celery.py beat
Restart=always

[Install]
WantedBy=multi-user.target
"""

    # サービスファイルを生成
    with open('quested-celery-worker.service', 'w') as f:
        f.write(worker_service)
    
    with open('quested-celery-beat.service', 'w') as f:
        f.write(beat_service)
    
    click.echo("✅ systemdサービスファイルを生成しました:")
    click.echo("  - quested-celery-worker.service")
    click.echo("  - quested-celery-beat.service")
    click.echo("")
    click.echo("インストール手順:")
    click.echo("1. sudo cp *.service /etc/systemd/system/")
    click.echo("2. sudo systemctl daemon-reload")
    click.echo("3. sudo systemctl enable quested-celery-worker")
    click.echo("4. sudo systemctl enable quested-celery-beat")
    click.echo("5. sudo systemctl start quested-celery-worker")
    click.echo("6. sudo systemctl start quested-celery-beat")

@cli.command()
@click.option('--check-redis', is_flag=True, help='Redisサーバーの接続確認も行う')
def check_deps(check_redis):
    """依存関係の確認"""
    click.echo("🔍 依存関係を確認中...")
    
    # Celeryの確認
    if CELERY_AVAILABLE:
        click.echo("✅ Celery: 利用可能")
    else:
        click.echo("❌ Celery: 利用不可 (pip install celery が必要)")
    
    # Redisの確認
    if check_redis:
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0)
            r.ping()
            click.echo("✅ Redis: 接続OK")
        except ImportError:
            click.echo("❌ Redis Python Client: 利用不可 (pip install redis が必要)")
        except Exception as e:
            click.echo(f"❌ Redis Server: 接続失敗 ({e})")
    
    # 他の依存関係
    try:
        import jinja2
        click.echo("✅ Jinja2: 利用可能")
    except ImportError:
        click.echo("❌ Jinja2: 利用不可")

if __name__ == '__main__':
    cli()