"""
基于角色的访问控制(RBAC)数据模型
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .dynamic_permission import ConditionalPermission, DynamicPermission, TemporaryPermission
    from .organization import Organization
    from .user import User

# 角色权限关联表
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", String, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", String, ForeignKey("permissions.id"), primary_key=True),
    Column("created_at", DateTime, default=datetime.now, comment="创建时间"),
    Column("created_by", String(100), comment="创建人"),
    extend_existing=True,
)


class Role(Base):  # type: ignore[valid-type, misc]
    """角色模型"""

    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, comment="角色名称")
    display_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="显示名称")
    description: Mapped[str | None] = mapped_column(Text, comment="角色描述")

    # 角色级别和类型
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, comment="角色级别")
    category: Mapped[str | None] = mapped_column(String(50), comment="角色类别")
    is_system_role: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否系统角色"
    )

    # 状态信息
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否激活")

    # 组织关联
    organization_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("organizations.id"), comment="所属组织ID"
    )

    # 权限范围
    scope: Mapped[str] = mapped_column(
        String(50), default="global", comment="权限范围(global/organization/department)"
    )
    scope_id: Mapped[str | None] = mapped_column(String, comment="范围ID")

    # 审计信息
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )
    created_by: Mapped[str | None] = mapped_column(String(100), comment="创建人")
    updated_by: Mapped[str | None] = mapped_column(String(100), comment="更新人")

    # 关系
    organization: Mapped["Organization"] = relationship("Organization")
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )
    # users = relationship("User", secondary="user_role_assignments")  # 完全移除以避免循环依赖
    user_assignments: Mapped[list["UserRoleAssignment"]] = relationship("UserRoleAssignment", back_populates="role")

    def __repr__(self) -> str:
        return (  # pragma: no cover
            f"<Role(id={self.id}, name={self.name}, display_name={self.display_name})>"  # pragma: no cover
        )  # pragma: no cover


class Permission(Base):  # type: ignore[valid-type, misc]
    """权限模型"""

    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, comment="权限名称")
    display_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="显示名称")
    description: Mapped[str | None] = mapped_column(Text, comment="权限描述")

    # 权限分类
    resource: Mapped[str] = mapped_column(String(50), nullable=False, comment="资源类型")
    action: Mapped[str] = mapped_column(String(50), nullable=False, comment="操作类型")

    # 权限特征
    is_system_permission: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否系统权限"
    )
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否需要审批")

    # 权限限制
    max_level: Mapped[int | None] = mapped_column(Integer, comment="最大级别")
    conditions: Mapped[dict[str, Any] | None] = mapped_column(JSON, comment="权限条件(JSON格式)")

    # 审计信息
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )
    created_by: Mapped[str | None] = mapped_column(String(100), comment="创建人")
    updated_by: Mapped[str | None] = mapped_column(String(100), comment="更新人")

    # 关系
    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary=role_permissions, back_populates="permissions"
    )
    dynamic_permissions: Mapped[list["DynamicPermission"]] = relationship("DynamicPermission", back_populates="permission")
    temporary_permissions: Mapped[list["TemporaryPermission"]] = relationship(
        "TemporaryPermission", back_populates="permission"
    )
    conditional_permissions: Mapped[list["ConditionalPermission"]] = relationship(
        "ConditionalPermission", back_populates="permission"
    )

    @property
    def is_active(self) -> bool:
        """权限始终激活（通过角色分配来控制访问）"""
        return True  # pragma: no cover

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name={self.name}, resource={self.resource}, action={self.action})>"  # pragma: no cover


class UserRoleAssignment(Base):  # type: ignore[valid-type, misc]
    """用户角色分配模型"""

    __tablename__ = "user_role_assignments"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 关联信息
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    role_id: Mapped[str] = mapped_column(String, ForeignKey("roles.id"), nullable=False)

    # 分配信息
    assigned_by: Mapped[str | None] = mapped_column(String(100), comment="分配人")
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="分配时间"
    )

    # 有效期
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, comment="过期时间")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否激活")

    # 分配原因和备注
    reason: Mapped[str | None] = mapped_column(Text, comment="分配原因")
    notes: Mapped[str | None] = mapped_column(Text, comment="备注")

    # 上下文信息
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON, comment="上下文信息(JSON格式)")

    # 审计信息
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )

    # 关系 - 修复映射冲突
    user: Mapped["User"] = relationship("User", back_populates="role_assignments")
    role: Mapped["Role"] = relationship("Role", back_populates="user_assignments")

    def __repr__(self) -> str:
        return f"<UserRoleAssignment(user_id={self.user_id}, role_id={self.role_id}, active={self.is_active})>"  # pragma: no cover


class ResourcePermission(Base):  # type: ignore[valid-type, misc]
    """资源权限模型 - 用于资源级别的权限控制"""

    __tablename__ = "resource_permissions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 资源信息
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="资源类型")
    resource_id: Mapped[str] = mapped_column(String, nullable=False, comment="资源ID")

    # 权限信息
    user_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), comment="用户ID")
    role_id: Mapped[str | None] = mapped_column(String, ForeignKey("roles.id"), comment="角色ID")
    permission_id: Mapped[str | None] = mapped_column(String, ForeignKey("permissions.id"), comment="权限ID")

    # 权限级别
    permission_level: Mapped[str] = mapped_column(
        String(20), default="read", comment="权限级别(read/write/delete/admin)"
    )

    # 有效期
    granted_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="授权时间"
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, comment="过期时间")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否激活")

    # 授权信息
    granted_by: Mapped[str | None] = mapped_column(String(100), comment="授权人")
    reason: Mapped[str | None] = mapped_column(Text, comment="授权原因")

    # 条件限制
    conditions: Mapped[dict[str, Any] | None] = mapped_column(JSON, comment="权限条件(JSON格式)")

    # 审计信息
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )

    # 关系
    user: Mapped["User"] = relationship("User")
    role: Mapped["Role"] = relationship("Role")
    permission: Mapped["Permission"] = relationship("Permission")

    def __repr__(self) -> str:
        return f"<ResourcePermission(resource={self.resource_type}:{self.resource_id}, level={self.permission_level})>"  # pragma: no cover


class PermissionAuditLog(Base):  # type: ignore[valid-type, misc]
    """权限审计日志"""

    __tablename__ = "permission_audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 操作信息
    action: Mapped[str] = mapped_column(String(50), nullable=False, comment="操作类型")
    resource_type: Mapped[str | None] = mapped_column(String(50), comment="资源类型")
    resource_id: Mapped[str | None] = mapped_column(String, comment="资源ID")

    # 用户信息
    user_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), comment="用户ID")
    operator_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), comment="操作人ID")

    # 权限变更
    old_permissions: Mapped[dict[str, Any] | None] = mapped_column(JSON, comment="原权限(JSON格式)")
    new_permissions: Mapped[dict[str, Any] | None] = mapped_column(JSON, comment="新权限(JSON格式)")

    # 变更原因
    reason: Mapped[str | None] = mapped_column(Text, comment="变更原因")

    # 环境信息
    ip_address: Mapped[str | None] = mapped_column(String(45), comment="IP地址")
    user_agent: Mapped[str | None] = mapped_column(Text, comment="用户代理")

    # 时间信息
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )

    # 关系
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    operator: Mapped["User"] = relationship("User", foreign_keys=[operator_id])

    def __repr__(self) -> str:
        return f"<PermissionAuditLog(action={self.action}, user_id={self.user_id}, operator_id={self.operator_id})>"  # pragma: no cover
