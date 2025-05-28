# Blueprint移行ガイド

このドキュメントは、モノリシックな`app.py`からBlueprint構造への移行手順を説明します。

## 移行の概要

元の`app.py`（4831行）を以下のBlueprint構造に分割しました：

```
app/
├── __init__.py      # アプリケーションファクトリー
├── models/          # データベースモデル (431行)
│   └── __init__.py
├── auth/            # 認証・認可 (約800行)
│   └── __init__.py
├── admin/           # 管理機能 (約600行)
│   └── __init__.py
├── teacher/         # 教師機能 (約1,200行)
│   └── __init__.py
├── student/         # 学生機能 (約1,000行)
│   └── __init__.py
├── ai/              # AI機能 (約400行)
│   ├── __init__.py
│   ├── helpers.py
│   └── curriculum_helpers.py
└── api/             # API機能 (約400行)
    └── __init__.py
```

## 移行手順

### 1. バックアップの作成

```bash
cp app.py app_backup.py
cp -r . ../quested-app-backup
```

### 2. 新しい構造への切り替え

```bash
# 古いapp.pyをリネーム
mv app.py app_old.py

# 新しい実行スクリプトを使用
python run.py
```

### 3. 環境変数の確認

`.env`ファイルに以下が設定されていることを確認：
- `SECRET_KEY`
- `DB_USERNAME`, `DB_PASSWORD`, `DB_HOST`, `DB_NAME`
- `OPENAI_API_KEY`
- `FLASK_ENV` (オプション)

### 4. データベースマイグレーション

データベース構造に変更はないため、マイグレーションは不要です。

```bash
# 念のため現在のマイグレーション状態を確認
flask db current
```

## 主な変更点

### URLパターンの変更

Blueprintを使用することで、一部のURLパターンが変更されています：

- 認証関連: `/login` → `/login` (変更なし)
- 管理者: `/admin/*` → `/admin/*` (変更なし) 
- API: `/api/*` → `/api/*` (変更なし)

### インポートパスの変更

#### 旧:
```python
from ai_helpers import generate_system_prompt
```

#### 新:
```python
from app.ai import generate_system_prompt
```

### テンプレートとの互換性

テンプレート内の`url_for`呼び出しを更新する必要があります：

#### 旧:
```jinja2
{{ url_for('login') }}
{{ url_for('teacher_dashboard') }}
{{ url_for('student_dashboard') }}
```

#### 新:
```jinja2
{{ url_for('auth.login') }}
{{ url_for('teacher.dashboard') }}
{{ url_for('student.dashboard') }}
```

## テスト方法

### 1. 基本動作確認

```bash
# アプリケーション起動
python run.py

# ブラウザでアクセス
http://localhost:5000
```

### 2. 各ロールでの動作確認

- **管理者**: `/admin/dashboard`にアクセス
- **教師**: ログイン後、ダッシュボードが表示されることを確認
- **学生**: ログイン後、ダッシュボードが表示されることを確認

### 3. 主要機能の確認

- ユーザー登録・ログイン
- クラス作成・管理
- 生徒の活動記録
- AI機能（テーマ生成、評価生成）

## トラブルシューティング

### ImportError が発生する場合

```bash
# Pythonパスを確認
export PYTHONPATH=/home/masat/claude-projects/quested-app:$PYTHONPATH
```

### テンプレートが見つからない場合

テンプレートファイルは`templates/`ディレクトリに配置されている必要があります。

### 静的ファイルが読み込まれない場合

`static/`ディレクトリのパスが正しいことを確認してください。

## ロールバック手順

問題が発生した場合は、以下の手順で元に戻せます：

```bash
# 新しい構造を削除
rm -rf app/
rm run.py

# バックアップから復元
mv app_old.py app.py
```

## 今後の推奨事項

1. **テスト追加**: 各Blueprintに対するユニットテストを追加
2. **CI/CD設定**: GitHub Actionsなどで自動テストを設定
3. **環境分離**: development/staging/production環境の明確な分離
4. **ログ設定**: 各Blueprintでの適切なログ設定
5. **エラーハンドリング**: Blueprint毎のエラーハンドラー実装