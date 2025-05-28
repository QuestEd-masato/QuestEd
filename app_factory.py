# app_factory.py
from flask import Flask
from config import get_config
from extensions import init_app as init_extensions

def create_app(config_object=None):
    """アプリケーションファクトリー - Flaskアプリケーションを作成して設定する"""
    app = Flask(__name__)
    
    # 設定を読み込む
    config = config_object or get_config()
    app.config.from_object(config)
    
    # 拡張機能を初期化
    init_extensions(app)
    
    # モデルの初期化 - 循環インポートを避けるために関数内でインポート
    with app.app_context():
        # 共通モデルを初期化
        from app import User, School, Class  # 必要に応じて他のモデルを追加
        
        # Blueprintの登録
        from core.academic import academic_bp
        from core.school import school_bp
        from core.enrollment import enrollment_bp
        
        app.register_blueprint(academic_bp)
        app.register_blueprint(school_bp)
        app.register_blueprint(enrollment_bp)
        
        # BaseBuilderモジュールを初期化
        from basebuilder import init_app as init_basebuilder
        init_basebuilder(app)
    
    # カスタムフィルターを追加
    @app.template_filter('nl2br')
    def nl2br_filter(text):
        """改行をHTMLのbrタグに変換するフィルター"""
        if not text:
            return ''
        import re
        return re.sub(r'\n', '<br>', str(text))
    
    return app

# アプリケーション実行用コード
if __name__ == '__main__':
    app = create_app()
    app.run(debug=app.config['DEBUG'])