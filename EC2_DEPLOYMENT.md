# QuestEd v1.3.0 - EC2デプロイメント手順

## 実装完了内容 ✅

### 教科機能の完全実装
1. **マイグレーション作成**: `migrations/versions/add_subjects_support_v1.py`
2. **Subjectモデル追加**: 教科マスタテーブル
3. **初期データスクリプト**: `app/scripts/init_subjects.py`
4. **クラス作成フォーム更新**: 教科選択機能追加
5. **AIチャット機能**: 教科別プロンプト対応

### セキュリティ強化
- XSS脆弱性修正: `basebuilder/start_learning_path.html`の`|safe`フィルタ削除

### メール送信機能改善
- 新しい`EmailSender`クラス実装
- SMTP/Gmail API両対応
- `.env.example`ファイル作成

## EC2デプロイメント手順

### 1. マイグレーションの実行

```bash
# EC2サーバーにSSH接続
cd /var/www/quested/QuestEd

# 最新コードを取得
git pull origin main

# マイグレーション実行（重要: 必須手順）
export FLASK_APP=run.py
python3 -m flask db upgrade

# マイグレーション確認
python3 -m flask db current
```

### 2. 教科初期データの投入

```bash
# 教科データ投入スクリプト実行
python3 app/scripts/init_subjects.py

# データベース確認
mysql -h "$DB_HOST" -u "$DB_USERNAME" -p"$DB_PASSWORD" "$DB_NAME" -e "
SELECT id, name, code FROM subjects;
"
```

### 3. アプリケーション再起動

```bash
# Gunicornプロセス停止
sudo pkill -f gunicorn

# アプリケーション再起動
/usr/bin/python3 /home/ec2-user/.local/bin/gunicorn \
    --timeout 600 --workers 4 --bind 127.0.0.1:8001 \
    run:app --log-file gunicorn_port8001.log \
    --log-level debug --daemon

# ログ監視
tail -f gunicorn_port8001.log
```

## 動作確認項目

### ✅ 教科機能
1. **教師ダッシュボード** → **新規クラス作成**
   - 教科選択プルダウンが表示されるか
   - 理科、数学、国語、社会、英語、総合的な学習の時間が選択できるか

2. **クラス作成テスト**
   - 「2年1組」+「理科」を選択 → 「2年1組 (理科)」として作成されるか
   - クラス詳細画面で教科情報が表示されるか

### ✅ AIチャット機能
1. **教科別プロンプトテスト**
   - 理科クラスで質問: 「光合成について教えて」
   - 数学クラスで質問: 「二次関数について教えて」
   - 回答が教科特性に応じた内容になっているか

2. **チャット履歴確認**
   ```sql
   SELECT ch.*, s.name as subject_name 
   FROM chat_history ch 
   LEFT JOIN subjects s ON ch.subject_id = s.id 
   WHERE ch.user_id = [ユーザーID] 
   ORDER BY ch.timestamp DESC 
   LIMIT 10;
   ```

### ✅ セキュリティ確認
1. **XSS対策確認**
   - BaseBuilderの学習パス画面でHTML入力テスト
   - スクリプトタグが実行されないことを確認

### ✅ メール送信機能
1. **SMTP設定確認**
   - 環境変数が正しく設定されているか
   - テストメール送信が成功するか

## トラブルシューティング

### マイグレーションエラー
```bash
# マイグレーション状態確認
python3 -m flask db heads
python3 -m flask db current

# エラー時のロールバック
python3 -m flask db downgrade
```

### 教科データが表示されない
```sql
-- 教科データ確認
SELECT * FROM subjects WHERE is_active = 1;

-- 手動でデータ投入（必要時）
INSERT INTO subjects (name, code, ai_system_prompt, grade_level, is_active) 
VALUES ('理科', 'science', '科学的思考を促進し...', '中学', 1);
```

### Gunicornエラー
```bash
# プロセス確認
ps aux | grep gunicorn

# ログ確認
tail -100 gunicorn_port8001.log

# 強制終了後再起動
sudo pkill -9 -f gunicorn
# 再起動コマンド実行
```

## バージョン情報
- **Current Version**: 1.3.0
- **Previous Version**: 1.2.0
- **Deployment Date**: 2025-01-09
- **Major Changes**: 教科機能完全実装、AIチャット教科別対応

## 注意事項
1. ⚠️ **マイグレーション必須**: 教科機能を使用するには必ずマイグレーションを実行
2. ⚠️ **初期データ必須**: 教科選択肢を表示するには初期データ投入が必要
3. ⚠️ **アプリ再起動必須**: 新機能を反映するにはGunicorn再起動が必要
4. ✅ **既存データ影響なし**: 既存のクラスやチャット履歴は影響を受けません

## サポート情報
- GitHub: [QuestEd Repository](https://github.com/QuestEd-masato/QuestEd)
- 問題報告: GitHubのIssues
- バックアップ: デプロイ前に必ずデータベースバックアップを作成してください