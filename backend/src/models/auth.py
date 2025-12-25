"""
认证相关数据模型
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, cast

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import relationship

from ..database import Base


class UserRole(str, Enum):
    """用户角色枚举"""

    ADMIN = "admin"
    USER = "user"


class User(Base):
    """用户模型"""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 基本信息
    username = Column(
        String(50), unique=True, nullable=False, index=True, comment="用户名"
    )
    email = Column(String(100), unique=True, nullable=False, index=True, comment="邮箱")
    full_name = Column(String(100), nullable=False, comment="全名")

    # 认证信息
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    password_history = Column(JSON, comment="密码历史记录")

    # 角色和状态
    role = Column(
        String(20), nullable=False, default=UserRole.USER.value, comment="用户角色"
    )
    is_active = Column(Boolean, nullable=False, default=True, comment="是否激活")
    is_locked = Column(Boolean, nullable=False, default=False, comment="是否锁定")

    # 登录信息
    last_login_at = Column(DateTime, comment="最后登录时间")
    failed_login_attempts = Column(
        Integer, nullable=False, default=0, comment="失败登录次数"
    )
    locked_until = Column(DateTime, comment="锁定到期时间")
    password_last_changed = Column(
        DateTime, default=datetime.now, comment="密码最后修改时间"
    )

    # 组织关联
    employee_id = Column(String, ForeignKey("employees.id"), comment="关联员工ID")
    default_organization_id = Column(
        String, ForeignKey("organizations.id"), comment="默认组织ID"
    )

    # 审计信息
    created_at = Column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )
    created_by = Column(String(100), comment="创建人")
    updated_by = Column(String(100), comment="更新人")

    # 关系
    # 暂时移除双向关系以避免循环依赖问题
    # employee = relationship("Employee", back_populates="user", foreign_keys=[employee_id])
    default_organization = relationship("Organization")
    user_sessions = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs = relationship("AuditLog", back_populates="user")
    role_assignments = relationship("UserRoleAssignment", back_populates="user")

    # 动态权限关系 - 暂时注释掉有问题的关系
    # dynamic_permissions = relationship("DynamicPermission", foreign_keys="DynamicPermission.user_id", back_populates="user")
    # temporary_permissions = relationship("TemporaryPermission", foreign_keys="TemporaryPermission.user_id", back_populates="user")
    # conditional_permissions = relationship("ConditionalPermission", foreign_keys="ConditionalPermission.user_id", back_populates="user")
    # permission_requests = relationship("PermissionRequest", back_populates="user")
    # delegated_permissions = relationship("PermissionDelegation", foreign_keys="PermissionDelegation.delegatee_id", back_populates="delegatee")
    # delegated_permissions_to_others = relationship("PermissionDelegation", foreign_keys="PermissionDelegation.delegator_id", back_populates="delegator")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"

    @property
    def is_admin(self) -> bool:
        """检查是否为管理员"""
        # 注意：这是实例属性，不是SQL查询表达式
        # 在实际使用中，self.role应该是从数据库加载的具体值
        if TYPE_CHECKING:
            # 在类型检查时，self.role是Column对象
            return False
        else:
            # 在运行时，self.role是具体的值
            role_value = cast(str, self.role)
            if isinstance(role_value, str):
                return role_value == UserRole.ADMIN.value
            elif hasattr(role_value, "value"):  # 如果是枚举类型
                return role_value.value == UserRole.ADMIN.value
            return False

    def is_locked_now(self) -> bool:
        """检查当前是否被锁定"""
        if TYPE_CHECKING:
            # 在类型检查时，返回明确的bool值
            return False
        else:
            # 安全地检查 is_locked 字段
            is_locked = cast(bool, self.is_locked)
            if isinstance(is_locked, str):
                is_locked = is_locked.lower() in ("true", "1", "yes")
            elif not isinstance(is_locked, bool):
                is_locked = bool(is_locked) if is_locked is not None else False

            if not is_locked:
                return False

            # 检查锁定时间
            locked_until_value = cast(datetime, self.locked_until)
            if locked_until_value is not None and locked_until_value > datetime.now():
                return True

            # 如果锁定时间已过，自动解锁（安全地设置字段）
            try:
                self.is_locked = False
                self.locked_until = None
                self.failed_login_attempts = 0
            except Exception:
                # 如果无法设置字段，忽略错误，只返回结果
                pass

            return False


class UserSession(Base):
    """用户会话模型"""

    __tablename__ = "user_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 关联用户
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 会话信息
    session_id = Column(String(100), unique=True, comment="会话ID")
    refresh_token = Column(String(255), unique=True, nullable=False, comment="刷新令牌")
    device_info = Column(Text, comment="设备信息")
    device_id = Column(String(100), comment="设备ID")
    platform = Column(String(50), comment="平台")
    ip_address = Column(String(45), comment="IP地址")
    user_agent = Column(Text, comment="用户代理")

    # 状态信息
    is_active = Column(Boolean, nullable=False, default=True, comment="是否活跃")
    expires_at = Column(DateTime, nullable=False, comment="过期时间")

    # 时间信息
    created_at = Column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    last_accessed_at = Column(
        DateTime, nullable=False, default=datetime.now, comment="最后访问时间"
    )

    # 关系
    user = relationship("User", back_populates="user_sessions")

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"

    def is_expired(self) -> bool:
        """检查会话是否已过期"""
        if TYPE_CHECKING:
            # 在类型检查时，返回明确的bool值
            return False
        else:
            expires_at_value = cast(datetime, self.expires_at)
            if expires_at_value is None:
                return True
            return datetime.now() > expires_at_value


class AuditLog(Base):
    """审计日志模型"""

    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 用户信息
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    username = Column(String(50), nullable=False)
    user_role = Column(String(20), comment="用户角色")
    user_organization = Column(String(200), comment="用户所属组织")

    # 操作信息
    action = Column(String(100), nullable=False, comment="操作动作")
    resource_type = Column(String(50), comment="资源类型")
    resource_id = Column(String, comment="资源ID")
    resource_name = Column(String(200), comment="资源名称")

    # 请求信息
    api_endpoint = Column(String(200), comment="API端点")
    http_method = Column(String(10), comment="HTTP方法")
    request_params = Column(Text, comment="请求参数")
    request_body = Column(Text, comment="请求体")

    # 响应信息
    response_status = Column(Integer, comment="响应状态码")
    response_message = Column(String(500), comment="响应消息")

    # 环境信息
    ip_address = Column(String(45), comment="IP地址")
    user_agent = Column(Text, comment="用户代理")
    session_id = Column(String(100), comment="会话ID")

    # 时间信息
    created_at = Column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )

    # 关系
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, user={self.username})>"
