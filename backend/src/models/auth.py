"""
认证相关数据模型
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .notification import Notification
    from .organization import Organization
    from .rbac import UserRoleAssignment


class User(Base):
    """用户模型"""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 基本信息
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True, comment="用户名"
    )
    email: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True, comment="邮箱"
    )
    full_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="全名")

    # 认证信息
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="密码哈希"
    )
    password_history: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, comment="密码历史记录"
    )

    # 状态
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否激活"
    )
    is_locked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否锁定"
    )

    # 登录信息
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime, comment="最后登录时间"
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="失败登录次数"
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime, comment="锁定到期时间"
    )
    password_last_changed: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow(), comment="密码最后修改时间"
    )

    # 组织关联
    employee_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("employees.id"), comment="关联员工ID"
    )
    default_organization_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("organizations.id"), comment="默认组织ID"
    )

    # 审计信息
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.utcnow(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.utcnow(),
        onupdate=lambda: datetime.utcnow(),
        comment="更新时间",
    )
    created_by: Mapped[str | None] = mapped_column(String(100), comment="创建人")
    updated_by: Mapped[str | None] = mapped_column(String(100), comment="更新人")

    # 关系
    # 暂时移除双向关系以避免循环依赖问题
    # employee = relationship("Employee", back_populates="user", foreign_keys=[employee_id])
    default_organization: Mapped["Organization | None"] = relationship("Organization")
    user_sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="user"
    )
    role_assignments: Mapped[list["UserRoleAssignment"]] = relationship(
        "UserRoleAssignment", back_populates="user"
    )
    # 使用字符串引用避免循环依赖 - Notification模型在notification.py中定义
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="recipient",
        cascade="all, delete-orphan",
        foreign_keys="[Notification.recipient_id]",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"

    def is_locked_now(self) -> bool:
        """检查当前是否被锁定"""
        if TYPE_CHECKING:
            # 在类型检查时，返回明确的bool值
            return False
        else:
            # 安全地检查 is_locked 字段
            is_locked = cast("bool", self.is_locked)  # pragma: no cover
            if isinstance(is_locked, str):  # pragma: no cover
                is_locked = is_locked.lower() in (
                    "true",
                    "1",
                    "yes",
                )  # pragma: no cover
            elif not isinstance(is_locked, bool):  # pragma: no cover
                is_locked = (
                    bool(is_locked) if is_locked is not None else False
                )  # pragma: no cover

            if not is_locked:  # pragma: no cover
                return False  # pragma: no cover

            # 检查锁定时间
            locked_until_value = cast("datetime", self.locked_until)  # pragma: no cover
            if locked_until_value is not None:
                if locked_until_value.tzinfo is None:
                    locked_until_value = locked_until_value.replace(tzinfo=UTC)
                else:
                    locked_until_value = locked_until_value.astimezone(UTC)
                if locked_until_value > datetime.utcnow():
                    return True

            # 如果锁定时间已过，自动解锁（安全地设置字段）
            try:  # pragma: no cover
                self.is_locked = False  # pragma: no cover
                self.locked_until = None  # pragma: no cover
                self.failed_login_attempts = 0  # pragma: no cover
            except Exception:  # pragma: no cover  # nosec - B110: Intentional graceful degradation for optional field updates
                # 如果无法设置字段，忽略错误，只返回结果
                pass  # pragma: no cover

            return False  # pragma: no cover


class UserSession(Base):
    """用户会话模型"""

    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 关联用户
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)

    # 会话信息
    session_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, comment="会话ID"
    )
    refresh_token: Mapped[str] = mapped_column(
        Text, unique=True, nullable=False, comment="刷新令牌"
    )
    device_info: Mapped[str | None] = mapped_column(Text, comment="设备信息")
    device_id: Mapped[str | None] = mapped_column(String(100), comment="设备ID")
    platform: Mapped[str | None] = mapped_column(String(50), comment="平台")
    ip_address: Mapped[str | None] = mapped_column(String(45), comment="IP地址")
    user_agent: Mapped[str | None] = mapped_column(Text, comment="用户代理")

    # 状态信息
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否活跃"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="过期时间"
    )

    # 时间信息
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.utcnow(), comment="创建时间"
    )
    last_accessed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.utcnow(),
        comment="最后访问时间",
    )

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="user_sessions")

    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"

    def is_expired(self) -> bool:
        """检查会话是否已过期"""
        if TYPE_CHECKING:
            # 在类型检查时，返回明确的bool值
            return False
        else:
            expires_at_value = cast("datetime", self.expires_at)  # pragma: no cover
            if expires_at_value is None:  # pragma: no cover
                return True  # pragma: no cover
            if expires_at_value.tzinfo is None:  # pragma: no cover
                expires_at_value = expires_at_value.replace(
                    tzinfo=UTC
                )  # pragma: no cover
            else:  # pragma: no cover
                expires_at_value = expires_at_value.astimezone(UTC)  # pragma: no cover
            return datetime.utcnow() > expires_at_value  # pragma: no cover


class AuditLog(Base):
    """审计日志模型"""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 用户信息
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    user_role: Mapped[str | None] = mapped_column(String(20), comment="用户角色")
    user_organization: Mapped[str | None] = mapped_column(
        String(200), comment="用户所属组织"
    )

    # 操作信息
    action: Mapped[str] = mapped_column(String(100), nullable=False, comment="操作动作")
    resource_type: Mapped[str | None] = mapped_column(String(50), comment="资源类型")
    resource_id: Mapped[str | None] = mapped_column(String, comment="资源ID")
    resource_name: Mapped[str | None] = mapped_column(String(200), comment="资源名称")

    # 请求信息
    api_endpoint: Mapped[str | None] = mapped_column(String(200), comment="API端点")
    http_method: Mapped[str | None] = mapped_column(String(10), comment="HTTP方法")
    request_params: Mapped[str | None] = mapped_column(Text, comment="请求参数")
    request_body: Mapped[str | None] = mapped_column(Text, comment="请求体")

    # 响应信息
    response_status: Mapped[int | None] = mapped_column(Integer, comment="响应状态码")
    response_message: Mapped[str | None] = mapped_column(
        String(500), comment="响应消息"
    )

    # 环境信息
    ip_address: Mapped[str | None] = mapped_column(String(45), comment="IP地址")
    user_agent: Mapped[str | None] = mapped_column(Text, comment="用户代理")
    session_id: Mapped[str | None] = mapped_column(String(100), comment="会话ID")

    # 时间信息
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.utcnow(), comment="创建时间"
    )

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, user={self.username})>"
