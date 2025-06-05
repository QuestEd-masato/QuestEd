# このファイルは後方互換性のために残されています
# すべての機能はBlueprintに移行されました
# 実際のアプリケーションはrun.pyから起動されます

from app import create_app

# 既存のインポートやwsgi.pyから参照される可能性があるため
app = create_app()

if __name__ == '__main__':
    print("警告: app.pyは非推奨です。run.pyを使用してください。")
    print("python run.py")
    app.run(debug=True)