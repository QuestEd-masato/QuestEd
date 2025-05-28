import os
import sys
import pymysql
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# データベース接続情報
DB_USERNAME = os.getenv('DB_USERNAME')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')

# 期待されるテーブルとカラムの定義
EXPECTED_SCHEMA = {
    'users': [
        'id', 'username', 'password', 'email', 'role', 'created_at'
    ],
    'classes': [
        'id', 'teacher_id', 'name'
    ],
    'interest_surveys': [
        'id', 'student_id', 'responses'
    ],
    'personality_surveys': [
        'id', 'student_id', 'responses'
    ],
    'inquiry_themes': [
        'id', 'student_id', 'title', 'question', 'description', 
        'rationale', 'approach', 'potential', 'is_selected'
    ],
    'activity_logs': [
        'id', 'student_id', 'activity', 'timestamp'
    ]
}

def check_and_fix_schema():
    """すべてのテーブルとカラムの存在を確認し、必要に応じて修正"""
    try:
        # MySQLデータベースに接続
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USERNAME,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        
        with connection.cursor() as cursor:
            # データベース内の既存テーブルを取得
            cursor.execute("""
                SHOW TABLES
            """)
            existing_tables = [table[0] for table in cursor.fetchall()]
            
            for table_name, expected_columns in EXPECTED_SCHEMA.items():
                # テーブルが存在するか確認
                if table_name not in existing_tables:
                    print(f"テーブル '{table_name}' が存在しません。")
                    continue
                
                # テーブルの既存カラムを取得
                cursor.execute(f"""
                    SHOW COLUMNS FROM {table_name}
                """)
                existing_columns = [column[0] for column in cursor.fetchall()]
                
                # 欠けているカラムを確認
                missing_columns = [col for col in expected_columns if col not in existing_columns]
                
                if missing_columns:
                    print(f"テーブル '{table_name}' に以下のカラムが欠けています: {', '.join(missing_columns)}")
                    
                    # 欠けているカラムを追加
                    for column in missing_columns:
                        print(f"カラム '{column}' を追加しています...")
                        
                        # カラムのデータ型を決定（簡易的な実装）
                        if column == 'id':
                            column_type = "INT AUTO_INCREMENT PRIMARY KEY"
                        elif column.endswith('_id'):
                            column_type = "INT"
                        elif column == 'timestamp':
                            column_type = "DATETIME DEFAULT CURRENT_TIMESTAMP"
                        elif column == 'created_at':
                            column_type = "DATETIME DEFAULT CURRENT_TIMESTAMP"
                        elif column == 'password':
                            column_type = "VARCHAR(255)"
                        elif column in ('username', 'email'):
                            column_type = "VARCHAR(100)"
                        elif column == 'role':
                            column_type = "VARCHAR(10)"
                        elif column == 'is_selected':
                            column_type = "BOOLEAN DEFAULT FALSE"
                        else:
                            column_type = "TEXT"
                        
                        try:
                            cursor.execute(f"""
                                ALTER TABLE {table_name}
                                ADD COLUMN {column} {column_type}
                            """)
                            print(f"カラム '{column}' を追加しました。")
                        except Exception as e:
                            print(f"カラム '{column}' の追加中にエラーが発生しました: {e}")
                else:
                    print(f"テーブル '{table_name}' のカラムはすべて存在します。")
            
            # 変更をコミット
            connection.commit()
            print("データベーススキーマの確認と修正が完了しました。")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        sys.exit(1)
    finally:
        connection.close()

if __name__ == "__main__":
    check_and_fix_schema()