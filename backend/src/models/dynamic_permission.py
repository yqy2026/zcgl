"""
动态权限模型
支持临时权限、条件权限和动态权限分配
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

from ..database import Base


class DynamicPermission(Base):
    """动态权限模型"""
    __tablename__ = "dynamic_permissions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    permission_id = Column(String, ForeignKey("permissions.id"), nullable=False, index=True)

    # 权限类型: role_based, user_specific, temporary, conditional, template_based
    permission_type = Column(String, nullable=False, index=True)

    # 权限范围: global, organization, project, asset, custom
    scope = Column(String, nullable=False, index=True)
    scope_id = Column(String, nullable=True, index=True)  # 范围ID，当scope不是global时使用

    # 权限条件（JSON格式）
    conditions = Column(JSON, nullable=True)

    # 过期时间（可选）
    expires_at = Column(DateTime, nullable=True, index=True)

    # 分配信息
    assigned_by = Column(String, ForeignKey("users.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 撤销信息
    revoked_by = Column(String, ForeignKey("users.id"), nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    # 状态
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # 关系 - 暂时注释掉User关系引用
    # user = relationship("User", foreign_keys=[user_id], back_populates="dynamic_permissions")
    permission = relationship("Permission", back_populates="dynamic_permissions")
    # assigned_by_user = relationship("User", foreign_keys=[assigned_by])
    # revoked_by_user = relationship("User", foreign_keys=[revoked_by])


class TemporaryPermission(Base):
    """临时权限模型"""
    __tablename__ = "temporary_permissions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    permission_id = Column(String, ForeignKey("permissions.id"), nullable=False, index=True)

    # 权限范围: global, organization, project, asset, custom
    scope = Column(String, nullable=False, index=True)
    scope_id = Column(String, nullable=True, index=True)

    # 过期时间（必填）
    expires_at = Column(DateTime, nullable=False, index=True)

    # 分配信息
    assigned_by = Column(String, ForeignKey("users.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 状态
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # 关系 - 暂时注释掉User关系引用
    # user = relationship("User", foreign_keys=[user_id], back_populates="temporary_permissions")
    permission = relationship("Permission", back_populates="temporary_permissions")
    # assigned_by_user = relationship("User", foreign_keys=[assigned_by])


class ConditionalPermission(Base):
    """条件权限模型"""
    __tablename__ = "conditional_permissions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    permission_id = Column(String, ForeignKey("permissions.id"), nullable=False, index=True)

    # 权限范围: global, organization, project, asset, custom
    scope = Column(String, nullable=False, index=True)
    scope_id = Column(String, nullable=True, index=True)

    # 权限条件（JSON格式，必填）
    conditions = Column(JSON, nullable=False)

    # 分配信息
    assigned_by = Column(String, ForeignKey("users.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 状态
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # 关系 - 暂时注释掉User关系引用
    # user = relationship("User", foreign_keys=[user_id], back_populates="conditional_permissions")
    permission = relationship("Permission", back_populates="conditional_permissions")
    # assigned_by_user = relationship("User", foreign_keys=[assigned_by])


class PermissionTemplate(Base):
    """权限模板模型"""
    __tablename__ = "permission_templates"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # 权限ID列表
    permission_ids = Column(JSON, nullable=False)

    # 默认权限范围
    scope = Column(String, nullable=False, index=True)

    # 默认权限条件
    conditions = Column(JSON, nullable=True)

    # 创建信息
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 状态
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # 关系 - 暂时注释掉User关系引用
    # created_by_user = relationship("User", foreign_keys=[created_by])


class DynamicPermissionAudit(Base):
    """动态权限审计日志模型"""
    __tablename__ = "dynamic_permission_audit"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    permission_id = Column(String, ForeignKey("permissions.id"), nullable=False, index=True)

    # 操作类型: ASSIGN, REVOKE, ASSIGN_TEMPORARY, ASSIGN_CONDITIONAL
    action = Column(String, nullable=False, index=True)

    # 权限类型
    permission_type = Column(String, nullable=False, index=True)

    # 权限范围
    scope = Column(String, nullable=False, index=True)
    scope_id = Column(String, nullable=True, index=True)

    # 操作人
    assigned_by = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # 操作原因
    reason = Column(Text, nullable=True)

    # 权限条件（如果有）
    conditions = Column(JSON, nullable=True)

    # 操作时间
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 关系 - 暂时注释掉User关系引用
    # user = relationship("User", foreign_keys=[user_id])
    permission = relationship("Permission")
    # assigned_by_user = relationship("User", foreign_keys=[assigned_by])


class PermissionRequest(Base):
    """权限申请模型"""
    __tablename__ = "permission_requests"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    permission_ids = Column(JSON, nullable=False)  # 申请的权限ID列表

    # 申请范围
    scope = Column(String, nullable=False, index=True)
    scope_id = Column(String, nullable=True, index=True)

    # 申请理由
    reason = Column(Text, nullable=False)

    # 申请期限（临时权限申请）
    requested_duration_hours = Column(String, nullable=True)

    # 申请条件（条件权限申请）
    requested_conditions = Column(JSON, nullable=True)

    # 审批状态: pending, approved, rejected
    status = Column(String, default="pending", nullable=False, index=True)

    # 审批人
    approved_by = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    approved_at = Column(DateTime, nullable=True)

    # 审批意见
    approval_comment = Column(Text, nullable=True)

    # 申请信息
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系 - 暂时注释掉User关系引用
    # user = relationship("User", foreign_keys=[user_id])
    # approved_by_user = relationship("User", foreign_keys=[approved_by])


class PermissionDelegation(Base):
    """权限委托模型"""
    __tablename__ = "permission_delegations"

    id = Column(String, primary_key=True, index=True)
    delegator_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)  # 委托人
    delegatee_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)  # 被委托人
    permission_ids = Column(JSON, nullable=False)  # 委托的权限ID列表

    # 委托范围
    scope = Column(String, nullable=False, index=True)
    scope_id = Column(String, nullable=True, index=True)

    # 委托期限
    starts_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ends_at = Column(DateTime, nullable=False, index=True)

    # 委托条件
    conditions = Column(JSON, nullable=True)

    # 委托原因
    reason = Column(Text, nullable=True)

    # 状态
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # 创建信息
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 关系 - 暂时注释掉User关系引用
    # delegator = relationship("User", foreign_keys=[delegator_id])
    # delegatee = relationship("User", foreign_keys=[delegatee_id])