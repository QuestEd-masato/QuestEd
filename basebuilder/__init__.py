# basebuilder/__init__.py
def init_app(app):
    """BaseBuilderモジュールをアプリケーションに初期化する"""
    
    # Blueprintの登録 - ここでBlueprintを登録します
    from basebuilder.routes import basebuilder_module
    app.register_blueprint(basebuilder_module)
    
    # 管理画面へのモデル追加
    with app.app_context():
        from app import admin, db
        from flask_admin.contrib.sqla import ModelView
        from basebuilder.models import (
            ProblemCategory, BasicKnowledgeItem, KnowledgeThemeRelation,
            AnswerRecord, ProficiencyRecord, LearningPath, PathAssignment,
            TextSet, TextDelivery, TextProficiencyRecord  # テキスト関連モデルを追加
        )
        # 新しく追加したモジュールをインポート
        from basebuilder import exporters
        from basebuilder import importers
        
        class BaseBuilderModelView(ModelView):
            def is_accessible(self):
                from flask_login import current_user
                return current_user.is_authenticated and current_user.role == 'teacher'
        
        # 管理画面にモデルを追加
        admin.add_view(BaseBuilderModelView(ProblemCategory, db.session, name='問題カテゴリ'))
        admin.add_view(BaseBuilderModelView(BasicKnowledgeItem, db.session, name='基礎知識問題'))
        admin.add_view(BaseBuilderModelView(KnowledgeThemeRelation, db.session, name='問題テーマ関連'))
        admin.add_view(BaseBuilderModelView(AnswerRecord, db.session, name='解答記録'))
        admin.add_view(BaseBuilderModelView(ProficiencyRecord, db.session, name='熟練度記録'))
        admin.add_view(BaseBuilderModelView(LearningPath, db.session, name='学習パス'))
        admin.add_view(BaseBuilderModelView(PathAssignment, db.session, name='パス割り当て'))
        # テキスト関連のモデルを管理画面に追加
        admin.add_view(BaseBuilderModelView(TextSet, db.session, name='テキストセット'))
        admin.add_view(BaseBuilderModelView(TextDelivery, db.session, name='テキスト配信'))
        admin.add_view(BaseBuilderModelView(TextProficiencyRecord, db.session, name='テキスト熟練度'))
    
    # ナビゲーションのカスタマイズ
    @app.context_processor
    def inject_basebuilder_nav():
        from flask_login import current_user
        
        # ナビゲーション項目を追加
        nav_items = []
        
        if current_user.is_authenticated:
            if current_user.role == 'student':
                nav_items = [
                    {'url': '/basebuilder/', 'name': '基礎学力ホーム'},
                    {'url': '/basebuilder/my_texts', 'name': 'テキスト一覧'},
                    {'url': '/basebuilder/proficiency', 'name': '熟練度'},
                    {'url': '/basebuilder/history', 'name': '学習履歴'},
                    {'url': '/basebuilder/learning_paths', 'name': '学習パス'}
                ]
            elif current_user.role == 'teacher':
                nav_items = [
                    {'url': '/basebuilder/', 'name': '基礎学力ホーム'},
                    {'url': '/basebuilder/text_sets', 'name': 'テキスト管理'},
                    {'url': '/basebuilder/categories', 'name': 'カテゴリ管理'},
                    {'url': '/basebuilder/problems', 'name': '問題管理'},
                    {'url': '/basebuilder/theme_relations', 'name': 'テーマ関連付け'},
                    {'url': '/basebuilder/learning_paths', 'name': '学習パス管理'},
                    {'url': '/basebuilder/analysis', 'name': '理解度分析'}
                ]
        
        return {'basebuilder_nav': nav_items}
    
    return app