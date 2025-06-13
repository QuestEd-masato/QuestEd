from flask import jsonify, request
from datetime import datetime
from typing import Any, Dict, List, Optional
from app.utils.exceptions import ValidationError, NotFoundError, PermissionError

class APIResponse:
    """標準APIレスポンス"""
    
    def __init__(self, data: Any = None, message: str = None, 
                 status: str = "success", status_code: int = 200):
        self.data = data
        self.message = message
        self.status = status
        self.status_code = status_code
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict:
        response = {
            'status': self.status,
            'timestamp': self.timestamp
        }
        
        if self.message:
            response['message'] = self.message
        
        if self.data is not None:
            response['data'] = self.data
        
        return response
    
    def to_response(self):
        """Flaskレスポンスオブジェクトを返す"""
        return jsonify(self.to_dict()), self.status_code

class APIError(Exception):
    """API例外基底クラス"""
    
    def __init__(self, message: str, status_code: int = 400, details: Dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_response(self):
        response = APIResponse(
            message=self.message,
            status="error",
            status_code=self.status_code
        )
        
        if self.details:
            response.data = {'details': self.details}
        
        return response.to_response()

def handle_api_exceptions(f):
    """API例外ハンドラーデコレータ"""
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as e:
            return APIError(str(e), 400).to_response()
        except NotFoundError as e:
            return APIError(str(e), 404).to_response()
        except PermissionError as e:
            return APIError(str(e), 403).to_response()
        except Exception as e:
            # 予期しないエラーはログに記録
            app.logger.error(f"Unexpected API error: {str(e)}")
            return APIError("内部サーバーエラーが発生しました", 500).to_response()
    
    wrapper.__name__ = f.__name__
    return wrapper

def paginate_query(query, page: int = None, per_page: int = None):
    """クエリのページネーション"""
    page = page or request.args.get('page', 1, type=int)
    per_page = per_page or request.args.get('per_page', 20, type=int)
    
    # 最大件数制限
    per_page = min(per_page, 100)
    
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    return {
        'items': pagination.items,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_prev': pagination.has_prev,
            'has_next': pagination.has_next,
            'prev_num': pagination.prev_num,
            'next_num': pagination.next_num
        }
    }

def validate_json_request(required_fields: List[str] = None):
    """JSONリクエスト検証デコレータ"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            if not request.is_json:
                raise ValidationError("Content-Type must be application/json")
            
            data = request.get_json()
            if data is None:
                raise ValidationError("Invalid JSON")
            
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
            
            return f(data, *args, **kwargs)
        
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator