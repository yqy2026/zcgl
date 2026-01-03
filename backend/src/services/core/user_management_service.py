from datetime import datetime
from sqlalchemy.orm import Session

from ...exceptions import BusinessLogicError
from ...models.auth import User
from ...schemas.auth import UserCreate, UserUpdate
from .password_service import PasswordService
from .session_service import SessionService

class UserManagementService:
    """用户管理服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.password_service = PasswordService()
        # SessionService needs db
        self.session_service = SessionService(db)

    def get_user_by_id(self, user_id: str) -> User | None:
        """根据ID获取用户"""
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, username: str) -> User | None:
        """根据用户名获取用户"""
        return self.db.query(User).filter(User.username == username).first()

    def get_user_by_email(self, email: str) -> User | None:
        """根据邮箱获取用户"""
        return self.db.query(User).filter(User.email == email).first()

    def create_user(self, user_data: UserCreate) -> User:
        """创建用户"""
        # 检查用户名是否已存在
        existing_user = (
            self.db.query(User)
            .filter(
                (User.username == user_data.username) | (User.email == user_data.email)
            )
            .first()
        )
        if existing_user:
            if existing_user.username == user_data.username:
                raise BusinessLogicError("用户名已存在")
            else:
                raise BusinessLogicError("邮箱已存在")

        # 验证密码强度
        if not self.password_service.validate_password_strength(user_data.password):
            raise BusinessLogicError("密码不符合安全要求")

        # 创建新用户
        hashed_password = self.password_service.get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            password_hash=hashed_password,
            role=user_data.role,
            employee_id=user_data.employee_id,
            default_organization_id=user_data.default_organization_id,
        )

        # 将密码添加到历史记录
        self.password_service.add_password_to_history(db_user, hashed_password)

        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        return db_user

    def update_user(self, user_id: str, user_data: UserUpdate) -> User | None:
        """更新用户信息"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None

        # 检查邮箱唯一性
        if user_data.email and user_data.email != user.email:
            existing_user = self.get_user_by_email(user_data.email)
            if existing_user:
                raise BusinessLogicError("邮箱已被其他用户使用")

        # 检查用户名唯一性
        username = getattr(user_data, "username", None)
        if username and username != user.username:
            existing_user = self.get_user_by_username(username)
            if existing_user:
                raise BusinessLogicError("用户名已被其他用户使用")

        # 更新字段
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        user.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(user)

        return user

    def deactivate_user(self, user_id: str) -> bool:
        """停用用户"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_active = False
        user.updated_at = datetime.now()

        # 撤销所有会话
        self.session_service.revoke_all_user_sessions(user_id)

        self.db.commit()
        return True

    def activate_user(self, user_id: str) -> bool:
        """激活用户"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_active = True
        user.is_locked = False
        user.locked_until = None
        user.failed_login_attempts = 0
        user.updated_at = datetime.now()

        self.db.commit()
        return True
    
    def unlock_user(self, user_id: str) -> bool:
        """解锁用户"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False

        user.is_locked = False
        user.locked_until = None
        user.failed_login_attempts = 0
        user.updated_at = datetime.now()

        self.db.commit()
        return True

    def change_password(self, user: User, current_password: str, new_password: str) -> bool:
        """修改密码"""
        # 验证当前密码
        if not self.password_service.verify_password(current_password, user.password_hash):
            raise BusinessLogicError("当前密码不正确")

        # 验证新密码强度
        if not self.password_service.validate_password_strength(new_password):
            raise BusinessLogicError("新密码不符合安全要求")

        # 检查新密码是否与历史记录中的密码相同
        if self.password_service.is_password_in_history(user, new_password):
            raise BusinessLogicError("新密码不能与最近使用过的密码相同")

        # 更新密码
        new_password_hash = self.password_service.get_password_hash(new_password)
        user.password_hash = new_password_hash

        # 将新密码添加到历史记录
        self.password_service.add_password_to_history(user, new_password_hash)

        self.db.commit()

        # 撤销所有会话，强制重新登录
        self.session_service.revoke_all_user_sessions(user.id)

        return True
