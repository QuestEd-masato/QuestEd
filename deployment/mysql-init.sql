-- mysql-init.sql - EC2 MySQL初期化スクリプト

-- データベース作成
CREATE DATABASE IF NOT EXISTS quested_ec2 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ユーザー作成と権限付与
CREATE USER IF NOT EXISTS 'quested_user'@'%' IDENTIFIED BY 'QuEsTeDsEcUrE2024!';
GRANT ALL PRIVILEGES ON quested_ec2.* TO 'quested_user'@'%';

-- 追加のセキュリティ設定
-- リモート root アクセスを制限
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');

-- 匿名ユーザーを削除
DELETE FROM mysql.user WHERE User='';

-- テストデータベースを削除
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';

-- 権限を再読み込み
FLUSH PRIVILEGES;

-- タイムゾーン設定
SET GLOBAL time_zone = '+09:00';

-- 基本的なパフォーマンス設定
SET GLOBAL max_connections = 200;
SET GLOBAL innodb_buffer_pool_size = 268435456; -- 256MB

-- セキュリティ設定
SET GLOBAL sql_mode = 'STRICT_TRANS_TABLES,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION';

-- ログ設定
SET GLOBAL general_log = 'OFF';
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;

-- 文字セット確認
SELECT @@character_set_database, @@collation_database;

-- 作成完了メッセージ
SELECT 'MySQL initialization completed for QuestEd EC2' AS status;