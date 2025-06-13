from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from app import db
from app.utils.exceptions import ValidationError, NotFoundError, PermissionError

class BaseService(ABC):
    """サービス層の基底クラス"""
    
    def __init__(self):
        self.db = db
    
    def commit(self):
        """データベースコミット"""
        try:
            self.db.session.commit()
        except Exception as e:
            self.db.session.rollback()
            raise e
    
    def rollback(self):
        """データベースロールバック"""
        self.db.session.rollback()
    
    def validate_permissions(self, user, action: str, resource: Any = None):
        """権限検証"""
        if not self._has_permission(user, action, resource):
            raise PermissionError(f"Permission denied for action: {action}")
    
    @abstractmethod
    def _has_permission(self, user, action: str, resource: Any = None) -> bool:
        """権限チェック（各サービスで実装）"""
        pass

class CRUDService(BaseService):
    """CRUD操作の基底サービス"""
    
    model = None  # 各サービスで設定
    
    def get_by_id(self, id: int, user=None):
        """IDで取得"""
        if user:
            self.validate_permissions(user, 'read')
        
        obj = self.model.query.get(id)
        if not obj:
            raise NotFoundError(f"{self.model.__name__} not found")
        return obj
    
    def get_all(self, user=None, filters: Dict = None, page: int = 1, per_page: int = 20):
        """一覧取得"""
        if user:
            self.validate_permissions(user, 'read')
        
        query = self.model.query
        
        if filters:
            query = self._apply_filters(query, filters)
        
        return query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
    
    def create(self, data: Dict, user=None):
        """作成"""
        if user:
            self.validate_permissions(user, 'create')
        
        self._validate_create_data(data)
        
        obj = self.model(**data)
        self.db.session.add(obj)
        self.commit()
        
        return obj
    
    def update(self, id: int, data: Dict, user=None):
        """更新"""
        obj = self.get_by_id(id, user)
        
        if user:
            self.validate_permissions(user, 'update', obj)
        
        self._validate_update_data(data, obj)
        
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        
        self.commit()
        return obj
    
    def delete(self, id: int, user=None):
        """削除"""
        obj = self.get_by_id(id, user)
        
        if user:
            self.validate_permissions(user, 'delete', obj)
        
        self.db.session.delete(obj)
        self.commit()
        
        return True
    
    def _apply_filters(self, query, filters: Dict):
        """フィルター適用（各サービスでオーバーライド）"""
        return query
    
    def _validate_create_data(self, data: Dict):
        """作成データ検証（各サービスでオーバーライド）"""
        pass
    
    def _validate_update_data(self, data: Dict, obj):
        """更新データ検証（各サービスでオーバーライド）"""
        pass