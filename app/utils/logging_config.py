import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
import json

class StructuredFormatter(logging.Formatter):
    """構造化ログフォーマッター"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # 追加情報があれば含める
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'ip_address'):
            log_entry['ip_address'] = record.ip_address
            
        # 例外情報があれば含める
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry, ensure_ascii=False)

def setup_logging(app):
    """ログ設定のセットアップ"""
    
    if not app.debug and not app.testing:
        # ログディレクトリ作成
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # アプリケーションログ
        file_handler = RotatingFileHandler(
            'logs/quested.log', 
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(StructuredFormatter())
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # エラーログ
        error_handler = RotatingFileHandler(
            'logs/error.log',
            maxBytes=10240000,
            backupCount=10
        )
        error_handler.setFormatter(StructuredFormatter())
        error_handler.setLevel(logging.ERROR)
        app.logger.addHandler(error_handler)
        
        # アクセスログ
        access_handler = RotatingFileHandler(
            'logs/access.log',
            maxBytes=10240000,
            backupCount=10
        )
        access_handler.setFormatter(StructuredFormatter())
        access_handler.setLevel(logging.INFO)
        
        # ログレベル設定
        app.logger.setLevel(logging.INFO)
        app.logger.info('QuestEd startup')

class RequestLogger:
    """リクエストログ記録"""
    
    @staticmethod
    def log_request(request, user_id=None):
        """リクエスト開始ログ"""
        app.logger.info(
            'Request started',
            extra={
                'user_id': user_id,
                'ip_address': request.remote_addr,
                'method': request.method,
                'path': request.path,
                'user_agent': request.headers.get('User-Agent')
            }
        )
    
    @staticmethod
    def log_response(request, response, user_id=None, duration=None):
        """レスポンスログ"""
        app.logger.info(
            'Request completed',
            extra={
                'user_id': user_id,
                'ip_address': request.remote_addr,
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration': duration
            }
        )

class SecurityLogger:
    """セキュリティイベントログ"""
    
    @staticmethod
    def log_login_attempt(email, success, ip_address):
        """ログイン試行ログ"""
        level = logging.INFO if success else logging.WARNING
        message = 'Login successful' if success else 'Login failed'
        
        app.logger.log(
            level,
            message,
            extra={
                'email': email,
                'ip_address': ip_address,
                'event_type': 'authentication'
            }
        )
    
    @staticmethod
    def log_permission_denied(user_id, resource, ip_address):
        """権限エラーログ"""
        app.logger.warning(
            'Permission denied',
            extra={
                'user_id': user_id,
                'resource': resource,
                'ip_address': ip_address,
                'event_type': 'authorization'
            }
        )
    
    @staticmethod
    def log_suspicious_activity(user_id, activity, ip_address):
        """不審な活動ログ"""
        app.logger.error(
            'Suspicious activity detected',
            extra={
                'user_id': user_id,
                'activity': activity,
                'ip_address': ip_address,
                'event_type': 'security'
            }
        )