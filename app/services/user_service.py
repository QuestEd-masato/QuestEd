from typing import Dict, List, Optional
from werkzeug.security import generate_password_hash
from app.models import User, School
from app.services.base_service import CRUDService
from app.utils.exceptions import ValidationError
from app.utils.validators import EmailValidator, PasswordValidator
import re

class UserService(CRUDService):
    """ユーザー管理サービス"""
    
    model = User
    
    def _has_permission(self, user, action: str, resource=None) -> bool:
        """権限チェック"""
        if user.role == 'admin':
            return True
        
        if action == 'read':
            if user.role == 'teacher':
                # 教師は自分の学校の生徒のみ閲覧可能
                if resource and resource.role == 'student':
                    return resource.school_id == user.school_id
                return resource == user
            return resource == user  # 生徒は自分のみ
        
        if action in ['create', 'update', 'delete']:
            return user.role in ['admin', 'teacher']
        
        return False
    
    def create_user(self, data: Dict, creator=None) -> User:
        """ユーザー作成"""
        if creator:
            self.validate_permissions(creator, 'create')
        
        # データ検証
        self._validate_user_data(data)
        
        # 重複チェック
        if User.query.filter_by(email=data['email']).first():
            raise ValidationError("このメールアドレスは既に使用されています")
        
        # パスワードハッシュ化
        if 'password' in data:
            data['password_hash'] = generate_password_hash(data.pop('password'))
        
        # デフォルト値設定
        data.setdefault('is_approved', False)
        data.setdefault('email_verified', False)
        
        user = User(**data)
        self.db.session.add(user)
        self.commit()
        
        return user
    
    def update_user(self, user_id: int, data: Dict, updater=None) -> User:
        """ユーザー更新"""
        user = self.get_by_id(user_id, updater)
        
        if updater:
            self.validate_permissions(updater, 'update', user)
        
        # パスワード更新の場合
        if 'password' in data:
            self._validate_password(data['password'])
            data['password_hash'] = generate_password_hash(data.pop('password'))
        
        # メールアドレス更新の場合
        if 'email' in data and data['email'] != user.email:
            if User.query.filter_by(email=data['email']).first():
                raise ValidationError("このメールアドレスは既に使用されています")
            data['email_verified'] = False  # 再認証が必要
        
        for key, value in data.items():
            if hasattr(user, key) and key != 'id':
                setattr(user, key, value)
        
        self.commit()
        return user
    
    def approve_user(self, user_id: int, approver=None) -> User:
        """ユーザー承認"""
        if approver and approver.role not in ['admin', 'teacher']:
            raise PermissionError("ユーザー承認権限がありません")
        
        user = self.get_by_id(user_id)
        user.is_approved = True
        self.commit()
        
        return user
    
    def get_users_by_school(self, school_id: int, role: Optional[str] = None, requester=None) -> List[User]:
        """学校別ユーザー取得"""
        if requester:
            self.validate_permissions(requester, 'read')
            
            # 権限チェック
            if requester.role != 'admin' and requester.school_id != school_id:
                raise PermissionError("他校のユーザー情報にはアクセスできません")
        
        query = User.query.filter_by(school_id=school_id)
        
        if role:
            query = query.filter_by(role=role)
        
        return query.all()
    
    def get_pending_approvals(self, approver=None) -> List[User]:
        """承認待ちユーザー取得"""
        if approver and approver.role not in ['admin', 'teacher']:
            raise PermissionError("承認待ちユーザーの確認権限がありません")
        
        query = User.query.filter_by(is_approved=False)
        
        # 教師は自分の学校のみ
        if approver and approver.role == 'teacher':
            query = query.filter_by(school_id=approver.school_id)
        
        return query.all()
    
    def search_users(self, query: str, requester=None) -> List[User]:
        """ユーザー検索"""
        if requester:
            self.validate_permissions(requester, 'read')
        
        search_query = User.query.filter(
            User.full_name.contains(query) | 
            User.email.contains(query)
        )
        
        # 権限による絞り込み
        if requester and requester.role == 'teacher':
            search_query = search_query.filter_by(school_id=requester.school_id)
        elif requester and requester.role == 'student':
            search_query = search_query.filter_by(id=requester.id)
        
        return search_query.limit(50).all()
    
    def _validate_user_data(self, data: Dict):
        """ユーザーデータ検証"""
        required_fields = ['email', 'role']
        
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"{field}は必須項目です")
        
        # メールアドレス検証
        if not EmailValidator.is_valid(data['email']):
            raise ValidationError("無効なメールアドレスです")
        
        # ロール検証
        valid_roles = ['admin', 'teacher', 'student']
        if data['role'] not in valid_roles:
            raise ValidationError("無効なロールです")
        
        # パスワード検証
        if 'password' in data:
            self._validate_password(data['password'])
        
        # 学校ID検証
        if 'school_id' in data and data['school_id']:
            if not School.query.get(data['school_id']):
                raise ValidationError("指定された学校が存在しません")
    
    def _validate_password(self, password: str):
        """パスワード検証"""
        if not PasswordValidator.is_strong(password):
            raise ValidationError(
                "パスワードは8文字以上で、英数字と特殊文字を含む必要があります"
            )