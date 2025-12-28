"""
基于角色的访问控制(RBAC)数据模型
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import relationship

from ..database import Base

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

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 基本信息
    name = Column(String(100), nullable=False, unique=True, comment="角色名称")
    display_name = Column(String(200), nullable=False, comment="显示名称")
    description = Column(Text, comment="角色描述")

    # 角色级别和类型
    level = Column(Integer, nullable=False, default=1, comment="角色级别")
    category = Column(String(50), comment="角色类别")
    is_system_role = Column(
        Boolean, nullable=False, default=False, comment="是否系统角色"
    )

    # 状态信息
    is_active = Column(Boolean, nullable=False, default=True, comment="是否激活")

    # 组织关联
    organization_id = Column(
        String, ForeignKey("organizations.id"), comment="所属组织ID"
    )

    # 权限范围
    scope = Column(
        String(50), default="global", comment="权限范围(global/organization/department)"
    )
    scope_id = Column(String, comment="范围ID")

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
    organization = relationship("Organization")
    permissions = relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )
    # users = relationship("User", secondary="user_role_assignments")  # 完全移除以避免循环依赖
    user_assignments = relationship(
        "UserRoleAssignment", back_populates="role"
    )

    def __repr__(self):
        return (
            f"<Role(id={self.id}, name={self.name}, display_name={self.display_name})>"
        )


class Permission(Base):
    """权限模型"""

    __tablename__ = "permissions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 基本信息
    name = Column(String(100), nullable=False, unique=True, comment="权限名称")
    display_name = Column(String(200), nullable=False, comment="显示名称")
    description = Column(Text, comment="权限描述")

    # 权限分类
    resource = Column(String(50), nullable=False, comment="资源类型")
    action = Column(String(50), nullable=False, comment="操作类型")

    # 权限特征
    is_system_permission = Column(
        Boolean, nullable=False, default=False, comment="是否系统权限"
    )
    requires_approval = Column(Boolean, default=False, comment="是否需要审批")

    # 权限限制
    max_level = Column(Integer, comment="最大级别")
    conditions = Column(Text, comment="权限条件(JSON格式)")

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
    roles = relationship(
        "Role", secondary=role_permissions, back_populates="permissions"
    )
    dynamic_permissions = relationship("DynamicPermission", back_populates="permission")
    temporary_permissions = relationship(
        "TemporaryPermission", back_populates="permission"
    )
    conditional_permissions = relationship(
        "ConditionalPermission", back_populates="permission"
    )

    @property
    def is_active(self) -> bool:
        """权限始终激活（通过角色分配来控制访问）"""
        return True

    def __repr__(self):
        return f"<Permission(id={self.id}, name={self.name}, resource={self.resource}, action={self.action})>"


class UserRoleAssignment(Base):
    """用户角色分配模型"""

    __tablename__ = "user_role_assignments"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 关联信息
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role_id = Column(String, ForeignKey("roles.id"), nullable=False)

    # 分配信息
    assigned_by = Column(String(100), comment="分配人")
    assigned_at = Column(
        DateTime, nullable=False, default=datetime.now, comment="分配时间"
    )

    # 有效期
    expires_at = Column(DateTime, comment="过期时间")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否激活")

    # 分配原因和备注
    reason = Column(Text, comment="分配原因")
    notes = Column(Text, comment="备注")

    # 上下文信息
    context = Column(Text, comment="上下文信息(JSON格式)")

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

    # 关系 - 修复映射冲突
    user = relationship("User", back_populates="role_assignments")
    role = relationship("Role", back_populates="user_assignments")

    def __repr__(self):
        return f"<UserRoleAssignment(user_id={self.user_id}, role_id={self.role_id}, active={self.is_active})>"


class ResourcePermission(Base):
    """资源权限模型 - 用于资源级别的权限控制"""

    __tablename__ = "resource_permissions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 资源信息
    resource_type = Column(String(50), nullable=False, comment="资源类型")
    resource_id = Column(String, nullable=False, comment="资源ID")

    # 权限信息
    user_id = Column(String, ForeignKey("users.id"), comment="用户ID")
    role_id = Column(String, ForeignKey("roles.id"), comment="角色ID")
    permission_id = Column(String, ForeignKey("permissions.id"), comment="权限ID")

    # 权限级别
    permission_level = Column(
        String(20), default="read", comment="权限级别(read/write/delete/admin)"
    )

    # 有效期
    granted_at = Column(
        DateTime, nullable=False, default=datetime.now, comment="授权时间"
    )
    expires_at = Column(DateTime, comment="过期时间")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否激活")

    # 授权信息
    granted_by = Column(String(100), comment="授权人")
    reason = Column(Text, comment="授权原因")

    # 条件限制
    conditions = Column(Text, comment="权限条件(JSON格式)")

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

    # 关系
    user = relationship("User")
    role = relationship("Role")
    permission = relationship("Permission")

    def __repr__(self):
        return f"<ResourcePermission(resource={self.resource_type}:{self.resource_id}, level={self.permission_level})>"


class PermissionAuditLog(Base):
    """权限审计日志"""

    __tablename__ = "permission_audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 操作信息
    action = Column(String(50), nullable=False, comment="操作类型")
    resource_type = Column(String(50), comment="资源类型")
    resource_id = Column(String, comment="资源ID")

    # 用户信息
    user_id = Column(String, ForeignKey("users.id"), comment="用户ID")
    operator_id = Column(String, ForeignKey("users.id"), comment="操作人ID")

    # 权限变更
    old_permissions = Column(Text, comment="原权限(JSON格式)")
    new_permissions = Column(Text, comment="新权限(JSON格式)")

    # 变更原因
    reason = Column(Text, comment="变更原因")

    # 环境信息
    ip_address = Column(String(45), comment="IP地址")
    user_agent = Column(Text, comment="用户代理")

    # 时间信息
    created_at = Column(
        DateTime, nullable=False, default=datetime.now, comment="创建时间"
    )

    # 关系
    user = relationship("User", foreign_keys=[user_id])
    operator = relationship("User", foreign_keys=[operator_id])

    def __repr__(self):
        return f"<PermissionAuditLog(action={self.action}, user_id={self.user_id}, operator_id={self.operator_id})>"
