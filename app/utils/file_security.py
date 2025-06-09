# app/utils/file_security.py
"""
ファイルアップロードのセキュリティ機能
"""
import os
import hashlib
import uuid
import imghdr
from werkzeug.utils import secure_filename
from flask import current_app

# Try to import python-magic, fall back to imghdr if not available
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

# 許可されたMIMEタイプ
ALLOWED_IMAGE_TYPES = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif']
}

ALLOWED_CSV_TYPES = {
    'text/csv': ['.csv'],
    'text/plain': ['.csv'],
    'application/csv': ['.csv']
}

# ファイルサイズ制限
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_CSV_SIZE = 2 * 1024 * 1024    # 2MB

class FileSecurityValidator:
    """ファイルアップロードのセキュリティバリデーター"""
    
    def __init__(self):
        if MAGIC_AVAILABLE:
            self.magic = magic.Magic(mime=True)
        else:
            self.magic = None
    
    def validate_image(self, file_stream, filename, max_size=MAX_IMAGE_SIZE):
        """
        画像ファイルの包括的検証
        
        Args:
            file_stream: ファイルストリーム
            filename: ファイル名
            max_size: 最大ファイルサイズ
            
        Returns:
            tuple: (is_valid, error_message, safe_filename)
        """
        # ファイルサイズチェック
        file_stream.seek(0, 2)
        file_size = file_stream.tell()
        file_stream.seek(0)
        
        if file_size > max_size:
            return False, f"ファイルサイズが大きすぎます（最大{max_size // 1024 // 1024}MB）", None
        
        if file_size == 0:
            return False, "空のファイルはアップロードできません", None
        
        # ファイル名検証
        if not filename or filename == '':
            return False, "ファイル名が無効です", None
        
        # 危険な文字列チェック
        dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
        if any(char in filename for char in dangerous_chars):
            return False, "ファイル名に使用できない文字が含まれています", None
        
        # MIMEタイプ検証（python-magicが利用可能な場合のみ）
        file_content = file_stream.read(1024)
        file_stream.seek(0)
        
        if self.magic:
            try:
                detected_mime = self.magic.from_buffer(file_content)
                # 許可されたMIMEタイプかチェック
                if detected_mime not in ALLOWED_IMAGE_TYPES:
                    return False, f"許可されていないファイル形式です: {detected_mime}", None
                
                # 拡張子とMIMEタイプの整合性チェック
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext not in ALLOWED_IMAGE_TYPES[detected_mime]:
                    return False, "ファイル拡張子とファイル内容が一致しません", None
            except Exception:
                return False, "ファイルタイプの検証に失敗しました", None
        else:
            # フォールバック: imghdrを使用した基本的な画像検証
            file_stream.seek(0)
            format = imghdr.what(file_stream)
            if not format:
                return False, "有効な画像ファイルではありません", None
            
            # 基本的な拡張子チェック
            file_ext = os.path.splitext(filename)[1].lower()
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            if file_ext not in allowed_extensions:
                return False, "許可されていないファイル拡張子です", None
        
        # 安全なファイル名生成
        secure_name = secure_filename(filename)
        unique_name = f"{uuid.uuid4().hex}_{secure_name}"
        
        return True, "検証成功", unique_name
    
    def validate_csv(self, file_stream, filename, max_size=MAX_CSV_SIZE):
        """
        CSVファイルの包括的検証
        
        Args:
            file_stream: ファイルストリーム
            filename: ファイル名
            max_size: 最大ファイルサイズ
            
        Returns:
            tuple: (is_valid, error_message, content)
        """
        # ファイルサイズチェック
        file_stream.seek(0, 2)
        file_size = file_stream.tell()
        file_stream.seek(0)
        
        if file_size > max_size:
            return False, f"ファイルサイズが大きすぎます（最大{max_size // 1024 // 1024}MB）", None
        
        if file_size == 0:
            return False, "空のファイルはアップロードできません", None
        
        # ファイル名検証
        if not filename or not filename.lower().endswith('.csv'):
            return False, "CSVファイルを選択してください", None
        
        # ファイル内容の読み取りと検証
        try:
            content = file_stream.read().decode('utf-8')
            file_stream.seek(0)
            
            # 基本的なCSV形式チェック
            if not content.strip():
                return False, "ファイルが空です", None
            
            # 行数制限（DoS攻撃防止）
            lines = content.split('\n')
            if len(lines) > 10000:  # 10,000行制限
                return False, "ファイルが大きすぎます（最大10,000行）", None
            
            # 危険なスクリプトタグなどのチェック
            dangerous_patterns = ['<script', 'javascript:', 'vbscript:', 'onload=', 'onerror=']
            content_lower = content.lower()
            if any(pattern in content_lower for pattern in dangerous_patterns):
                return False, "不正な内容が検出されました", None
            
            return True, "検証成功", content
            
        except UnicodeDecodeError:
            return False, "ファイルエンコーディングが無効です（UTF-8を使用してください）", None
        except Exception as e:
            return False, f"ファイル検証中にエラーが発生しました: {str(e)}", None
    
    def generate_file_hash(self, content):
        """
        ファイル内容のハッシュ値を生成（重複チェック用）
        
        Args:
            content: ファイル内容（bytes or str）
            
        Returns:
            str: SHA256ハッシュ値
        """
        if isinstance(content, str):
            content = content.encode('utf-8')
        return hashlib.sha256(content).hexdigest()
    
    def create_secure_path(self, filename, user_id=None):
        """
        セキュアなファイルパスを生成
        
        Args:
            filename: ファイル名
            user_id: ユーザーID（オプション）
            
        Returns:
            str: セキュアなファイルパス
        """
        upload_folder = current_app.config.get('SECURE_UPLOAD_FOLDER', current_app.config['UPLOAD_FOLDER'])
        
        # ユーザー別ディレクトリ作成
        if user_id:
            user_dir = os.path.join(upload_folder, str(user_id))
            os.makedirs(user_dir, mode=0o755, exist_ok=True)
            return os.path.join(user_dir, filename)
        else:
            os.makedirs(upload_folder, mode=0o755, exist_ok=True)
            return os.path.join(upload_folder, filename)

# グローバルバリデーターインスタンス
file_validator = FileSecurityValidator()
