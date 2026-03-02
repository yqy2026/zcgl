"""
基于角色的访问控制(RBAC)数据模型
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .party import Party
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


class Role(Base):
    """角色模型"""

    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 基本信息
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, comment="角色名称"
    )
    display_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="显示名称"
    )
    description: Mapped[str | None] = mapped_column(Text, comment="角色描述")

    # 角色级别和类型
    level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="角色级别"
    )
    category: Mapped[str | None] = mapped_column(String(50), comment="角色类别")
    is_system_role: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否系统角色"
    )

    # 状态信息
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否激活"
    )

    # 主体关联
    party_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("parties.id"),
        index=True,
        comment="所属主体ID",
    )

    # 权限范围
    scope: Mapped[str] = mapped_column(
        String(50),
        default="global",
        comment="权限范围(global/party/party_subtree)",
    )
    scope_id: Mapped[str | None] = mapped_column(String, comment="范围ID（parties.id）")

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
    party: Mapped["Party | None"] = relationship("Party")
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )
    # users = relationship("User", secondary="user_role_assignments")  # 完全移除以避免循环依赖
    user_assignments: Mapped[list["UserRoleAssignment"]] = relationship(
        "UserRoleAssignment", back_populates="role"
    )

    def __repr__(self) -> str:
        return (  # pragma: no cover
            f"<Role(id={self.id}, name={self.name}, display_name={self.display_name})>"  # pragma: no cover
        )  # pragma: no cover


class Permission(Base):
    """权限模型"""

    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 基本信息
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, comment="权限名称"
    )
    display_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="显示名称"
    )
    description: Mapped[str | None] = mapped_column(Text, comment="权限描述")

    # 权限分类
    resource: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="资源类型"
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False, comment="操作类型")

    # 权限特征
    is_system_permission: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否系统权限"
    )
    requires_approval: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否需要审批"
    )

    # 权限限制
    max_level: Mapped[int | None] = mapped_column(Integer, comment="最大级别")
    conditions: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, comment="权限条件(JSON格式)"
    )

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
    permission_grants: Mapped[list["PermissionGrant"]] = relationship(  # DEPRECATED
        "PermissionGrant", back_populates="permission"  # DEPRECATED
    )

    @property
    def is_active(self) -> bool:
        """权限始终激活（通过角色分配来控制访问）"""
        return True  # pragma: no cover

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name={self.name}, resource={self.resource}, action={self.action})>"  # pragma: no cover


class UserRoleAssignment(Base):
    """用户角色分配模型"""

    __tablename__ = "user_role_assignments"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

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
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否激活"
    )

    # 分配原因和备注
    reason: Mapped[str | None] = mapped_column(Text, comment="分配原因")
    notes: Mapped[str | None] = mapped_column(Text, comment="备注")

    # 上下文信息
    context: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, comment="上下文信息(JSON格式)"
    )

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


class ResourcePermission(Base):  # DEPRECATED
    """DEPRECATED: 资源权限模型（兼容保留）"""

    __tablename__ = "resource_permissions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 资源信息
    resource_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="资源类型"
    )
    resource_id: Mapped[str] = mapped_column(String, nullable=False, comment="资源ID")

    # 权限信息
    user_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id"), comment="用户ID"
    )
    role_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("roles.id"), comment="角色ID"
    )
    permission_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("permissions.id"), comment="权限ID"
    )

    # 权限级别
    permission_level: Mapped[str] = mapped_column(
        String(20), default="read", comment="权限级别(read/write/delete/admin)"
    )

    # 有效期
    granted_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment="授权时间"
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, comment="过期时间")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否激活"
    )

    # 授权信息
    granted_by: Mapped[str | None] = mapped_column(String(100), comment="授权人")
    reason: Mapped[str | None] = mapped_column(Text, comment="授权原因")

    # 条件限制
    conditions: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, comment="权限条件(JSON格式)"
    )

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
        return f"<ResourcePermission(resource={self.resource_type}:{self.resource_id}, level={self.permission_level})>"  # pragma: no cover DEPRECATED


class PermissionGrant(Base):  # DEPRECATED
    """DEPRECATED: 统一权限授权记录（兼容保留）"""

    __tablename__ = "permission_grants"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID"
    )
    permission_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("permissions.id"),
        nullable=False,
        index=True,
        comment="权限ID",
    )

    grant_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="direct", index=True, comment="授权类型"
    )
    effect: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="allow",
        index=True,
        comment="效果 allow/deny",
    )

    scope: Mapped[str] = mapped_column(
        String(50), nullable=False, default="global", index=True, comment="作用域类型"
    )
    scope_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    conditions: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="条件表达式(JSON)"
    )

    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True, comment="生效时间"
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True, comment="过期时间"
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, comment="优先级(越大越高)"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True, comment="是否激活"
    )

    source_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True, comment="来源类型"
    )
    source_id: Mapped[str | None] = mapped_column(
        String, nullable=True, index=True, comment="来源记录ID"
    )
    granted_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="撤销时间"
    )
    revoked_by: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="撤销人"
    )

    user: Mapped["User"] = relationship("User")
    permission: Mapped["Permission"] = relationship(
        "Permission", back_populates="permission_grants"
    )

    def __repr__(self) -> str:
        effect = self.effect if self.effect is not None else "allow"
        return f"<PermissionGrant(user_id={self.user_id}, permission_id={self.permission_id}, effect={effect})>"  # pragma: no cover DEPRECATED


class PermissionAuditLog(Base):
    """权限审计日志"""

    __tablename__ = "permission_audit_logs"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 操作信息
    action: Mapped[str] = mapped_column(String(50), nullable=False, comment="操作类型")
    resource_type: Mapped[str | None] = mapped_column(String(50), comment="资源类型")
    resource_id: Mapped[str | None] = mapped_column(String, comment="资源ID")

    # 用户信息
    user_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id"), comment="用户ID"
    )
    operator_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id"), comment="操作人ID"
    )

    # 权限变更
    old_permissions: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, comment="原权限(JSON格式)"
    )
    new_permissions: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, comment="新权限(JSON格式)"
    )

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
