"""
環境設定の検証ユーティリティ
"""
import os
import logging
from typing import List, Dict, Any

class ConfigValidator:
    """環境設定の検証クラス"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_required_env_vars(self, required_vars: List[str]) -> bool:
        """
        必須の環境変数をチェック
        
        Args:
            required_vars: 必須の環境変数のリスト
            
        Returns:
            bool: すべての必須変数が設定されているか
        """
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            self.errors.append(error_msg)
            logging.error(error_msg)
            return False
        
        return True
    
    def validate_database_config(self) -> bool:
        """
        データベース設定の検証
        
        Returns:
            bool: データベース設定が有効か
        """
        db_vars = ['DB_HOST', 'DB_NAME', 'DB_USERNAME', 'DB_PASSWORD']
        missing_vars = []
        
        for var in db_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            # デフォルト値があるため警告レベル
            warning_msg = f"Database environment variables not set, using defaults: {', '.join(missing_vars)}"
            self.warnings.append(warning_msg)
            logging.warning(warning_msg)
        
        return True
    
    def validate_security_config(self) -> bool:
        """
        セキュリティ設定の検証
        
        Returns:
            bool: セキュリティ設定が有効か
        """
        secret_key = os.getenv('SECRET_KEY')
        if not secret_key:
            error_msg = "SECRET_KEY not set - this is critical for production security"
            self.errors.append(error_msg)
            logging.error(error_msg)
            return False
        
        if len(secret_key) < 32:
            warning_msg = "SECRET_KEY is shorter than recommended (32+ characters)"
            self.warnings.append(warning_msg)
            logging.warning(warning_msg)
        
        return True
    
    def validate_api_keys(self) -> bool:
        """
        APIキーの検証
        
        Returns:
            bool: APIキーが設定されているか
        """
        openai_key = os.getenv('OPENAI_API_KEY')
        if not openai_key:
            warning_msg = "OPENAI_API_KEY not set - AI features will not work"
            self.warnings.append(warning_msg)
            logging.warning(warning_msg)
        
        return True
    
    def validate_email_config(self) -> bool:
        """
        メール設定の検証
        
        Returns:
            bool: メール設定が有効か
        """
        email_vars = ['MAIL_SERVER', 'MAIL_USERNAME', 'MAIL_PASSWORD']
        missing_vars = []
        
        for var in email_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            warning_msg = f"Email configuration incomplete: {', '.join(missing_vars)} - email features may not work"
            self.warnings.append(warning_msg)
            logging.warning(warning_msg)
        
        return True
    
    def validate_all(self) -> Dict[str, Any]:
        """
        すべての設定を検証
        
        Returns:
            dict: 検証結果
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 各種検証を実行
        security_valid = self.validate_security_config()
        self.validate_database_config()
        self.validate_api_keys()
        self.validate_email_config()
        
        # 結果をまとめる
        if self.errors:
            results['valid'] = False
        
        results['errors'] = self.errors
        results['warnings'] = self.warnings
        
        return results
    
    def log_validation_results(self, results: Dict[str, Any]):
        """
        検証結果をログに記録
        
        Args:
            results: validate_all()の結果
        """
        if results['valid']:
            logging.info("Configuration validation passed")
        else:
            logging.error("Configuration validation failed")
        
        for error in results['errors']:
            logging.error(f"Config Error: {error}")
        
        for warning in results['warnings']:
            logging.warning(f"Config Warning: {warning}")

def validate_startup_config():
    """
    アプリケーション起動時の設定検証
    
    Returns:
        bool: 起動可能な設定か
    """
    validator = ConfigValidator()
    results = validator.validate_all()
    validator.log_validation_results(results)
    
    return results['valid']