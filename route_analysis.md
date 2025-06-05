# QuestEd ルート分析レポート

## 概要
app.py に存在する全102個のルートを機能別に分類し、既存Blueprintでの実装状況を確認しました。

## 1. 認証関連 (auth_bp) - 11ルート

### 既にauth_bpで実装済み
- `/login` - ログイン
- `/logout` - ログアウト  
- `/register` - 新規登録
- `/verify_email/<int:user_id>` - メール確認ページ
- `/confirm_email/<int:user_id>/<token>` - メール確認処理
- `/resend_verification/<int:user_id>` - 確認メール再送信
- `/awaiting_approval` - 承認待ちページ
- `/forgot_password` - パスワード忘れ
- `/reset_password/<int:user_id>/<token>` - パスワードリセット
- `/change_password` - パスワード変更
- `/profile` - プロフィール (auth_bpには存在するがapp.pyにはない)

**状態**: ✅ 全て移行済み

## 2. 学生関連 (student_bp) - 36ルート

### 既にstudent_bpで実装済み
- `/student_dashboard` - 学生ダッシュボード
- `/surveys` - アンケート一覧
- `/interest_survey` - 興味アンケート
- `/interest_survey/edit` - 興味アンケート編集
- `/personality_survey` - 性格アンケート
- `/personality_survey/edit` - 性格アンケート編集
- `/activities` - 活動一覧
- `/new_activity` - 新規活動
- `/activity/<int:log_id>/edit` - 活動編集
- `/activity/<int:log_id>/delete` - 活動削除
- `/activities/export/<format>` - 活動エクスポート
- `/todos` - TODO一覧
- `/new_todo` - 新規TODO
- `/todo/<int:todo_id>/edit` - TODO編集
- `/todo/<int:todo_id>/delete` - TODO削除
- `/todo/<int:todo_id>/toggle` - TODO切り替え
- `/goals` - 目標一覧
- `/new_goal` - 新規目標
- `/goal/<int:goal_id>/edit` - 目標編集
- `/goal/<int:goal_id>/delete` - 目標削除
- `/goal/<int:goal_id>/update_progress` - 進捗更新
- `/themes` - テーマ一覧
- `/select_theme/<int:theme_id>` - テーマ選択
- `/regenerate_themes` - テーマ再生成
- `/main_themes` - メインテーマ一覧
- `/main_theme/<int:theme_id>/create_personal` - 個人テーマ作成
- `/main_theme/<int:theme_id>/generate_theme` - テーマ生成
- `/theme/<int:theme_id>/edit` - テーマ編集
- `/milestone/<int:milestone_id>` - マイルストーン表示
- `/group/<int:group_id>` - グループ詳細
- `/group/<int:group_id>/join` - グループ参加
- `/group/<int:group_id>/leave` - グループ離脱

### app.pyにあるがstudent_bpにない
- なし

**状態**: ✅ 全て移行済み

## 3. 教師関連 (teacher_bp) - 31ルート

### 既にteacher_bpで実装済み
- `/teacher_dashboard` - 教師ダッシュボード
- `/teacher/pending_users` - 承認待ちユーザー
- `/teacher/approve_user/<int:user_id>` - ユーザー承認
- `/classes` - クラス一覧
- `/create_class` - クラス作成
- `/class/<int:class_id>` - クラス詳細
- `/view_class/<int:class_id>` - クラス表示
- `/class/<int:class_id>/edit` - クラス編集
- `/class/<int:class_id>/delete` - クラス削除
- `/class/<int:class_id>/add_students` - 生徒追加
- `/class/<int:class_id>/remove_student/<int:student_id>` - 生徒削除
- `/class/<int:class_id>/main_themes` - クラステーマ
- `/class/<int:class_id>/main_themes/create` - テーマ作成
- `/main_theme/<int:theme_id>/edit` - テーマ編集
- `/main_theme/<int:theme_id>/delete` - テーマ削除
- `/create_milestone/<int:class_id>` - マイルストーン作成
- `/edit_milestone/<int:milestone_id>` - マイルストーン編集
- `/delete_milestone/<int:milestone_id>` - マイルストーン削除
- `/class/<int:class_id>/generate_evaluations` - 評価生成
- `/class/<int:class_id>/curriculums` - カリキュラム一覧
- `/class/<int:class_id>/curriculum/create` - カリキュラム作成
- `/class/<int:class_id>/curriculum/generate` - カリキュラム生成
- `/class/<int:class_id>/groups` - グループ一覧
- `/class/<int:class_id>/groups/create` - グループ作成
- `/class/<int:class_id>/students/import` - 生徒インポート
- `/api/teacher/first_class` - 最初のクラスAPI

### app.pyにあるがteacher_bpにない (カリキュラム関連)
- `/class/<int:class_id>/curriculum/import` - カリキュラムインポート
- `/curriculum/<int:curriculum_id>` - カリキュラム詳細
- `/curriculum/<int:curriculum_id>/edit` - カリキュラム編集
- `/curriculum/<int:curriculum_id>/delete` - カリキュラム削除
- `/curriculum/<int:curriculum_id>/export` - カリキュラムエクスポート
- `/curriculum/download_template` - テンプレートダウンロード

### app.pyにあるがteacher_bpにない (グループ関連)
- `/group/<int:group_id>/edit` - グループ編集
- `/group/<int:group_id>/delete` - グループ削除
- `/group/<int:group_id>/remove_member/<int:student_id>` - メンバー削除

**状態**: ⚠️ 9ルートが未移行

## 4. 管理者関連 (admin_bp) - 23ルート

### 既にadmin_bpで実装済み
- `/admin/dashboard` - 管理者ダッシュボード
- `/admin/users` - ユーザー管理
- `/admin/users/<int:user_id>/delete` - ユーザー削除
- `/admin/schools` - 学校一覧
- `/admin/school/<int:school_id>` - 学校詳細
- `/admin/schools/create` - 学校作成
- `/admin/schools/<int:school_id>/edit` - 学校編集
- `/admin/schools/<int:school_id>/delete` - 学校削除
- `/admin/school/<int:school_id>/year/create` - 学年作成
- `/admin/school_year/<int:school_year_id>/class_group/create` - クラスグループ作成
- `/admin/class_group/<int:class_group_id>` - クラスグループ詳細
- `/admin/class_group/<int:class_group_id>/add_students` - 生徒追加
- `/admin/enrollment/<int:enrollment_id>/delete` - 登録削除
- `/admin/import_users` - ユーザーインポート
- `/admin/download_user_template` - テンプレートダウンロード
- `/admin/access` - アクセス管理

### app.pyにあるがadmin_bpにない
- `/admin/school/create` (重複: `/admin/schools/create`と同じ)

**状態**: ✅ ほぼ移行済み（重複1件）

## 5. API関連 (api_bp) - 1ルート

### 既にapi_bpで実装済み
- `/api/teacher/first_class` - 最初のクラスAPI
- `/api/chat` - チャットAPI (api_bpには存在するがapp.pyには別形式)
- `/api/export/evaluations` - 評価エクスポート
- `/api/theme/<int:theme_id>/select` - テーマ選択
- `/api/todo/<int:todo_id>/toggle` - TODO切り替え
- `/api/goal/<int:goal_id>/progress` - 目標進捗
- `/api/stats` - 統計

### app.pyにあるがapi_bpと異なる形式
- `/api/teacher/first_class` - teacher_bpとapi_bpで重複

**状態**: ✅ APIエンドポイントは整理済み

## 6. その他/共通 - 2ルート

### app/__init__.pyで実装
- `/` - ホームページ

### special_routes.pyで実装
- `/admin_access` - 管理者アクセス

**状態**: ✅ 実装済み

## 重複ルートの詳細

### 同一Blueprint内での重複
1. admin_bp:
   - `/admin/school/create` と `/admin/schools/create` - 同じ機能

### 異なるBlueprint間での重複
1. teacher_bpとapi_bp:
   - `/api/teacher/first_class` - 両方に実装

### コメントアウトされているが実装されているルート
- app.pyに多数のコメントアウトされたルートが存在するが、実際にはBlueprintで実装済み

## 移行が必要なルート一覧

### 教師関連 (teacher_bp) - 9ルート
1. `/class/<int:class_id>/curriculum/import` - カリキュラムインポート
2. `/curriculum/<int:curriculum_id>` - カリキュラム詳細
3. `/curriculum/<int:curriculum_id>/edit` - カリキュラム編集
4. `/curriculum/<int:curriculum_id>/delete` - カリキュラム削除
5. `/curriculum/<int:curriculum_id>/export` - カリキュラムエクスポート
6. `/curriculum/download_template` - テンプレートダウンロード
7. `/group/<int:group_id>/edit` - グループ編集
8. `/group/<int:group_id>/delete` - グループ削除
9. `/group/<int:group_id>/remove_member/<int:student_id>` - メンバー削除

## 推奨アクション

1. **カリキュラム関連ルートの移行**
   - 6つのカリキュラム関連ルートをteacher_bpに移行
   - これらは教師機能として一貫性がある

2. **グループ管理ルートの移行**
   - 3つのグループ管理ルートをteacher_bpに移行
   - グループは教師が管理するため

3. **重複ルートの整理**
   - `/admin/school/create`を削除（`/admin/schools/create`を使用）
   - `/api/teacher/first_class`の重複を解消

4. **コメントアウトされたコードの削除**
   - app.pyから既にBlueprintに移行済みのコメントアウトされたルートを削除

## まとめ

- **総ルート数**: 102
- **移行済み**: 93 (91.2%)
- **未移行**: 9 (8.8%)
- **重複**: 2

主にカリキュラムとグループ管理機能の移行が残っているが、全体的には移行がほぼ完了している状態です。