"""
多租户模型
支持完整的租户管理和数据隔离
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

from ..database import Base


class Tenant(Base):
    """租户模型"""
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, index=True)

    # 基本信息
    name = Column(String(200), nullable=False, index=True, comment="租户名称")
    code = Column(String(50), unique=True, nullable=False, index=True, comment="租户代码")
    domain = Column(String(255), unique=True, nullable=True, index=True, comment="自定义域名")

    # 租户计划和状态
    plan = Column(String(50), nullable=False, default="basic", comment="租户计划")
    status = Column(String(50), nullable=False, default="pending", comment="租户状态")

    # 资源限制
    max_users = Column(Integer, nullable=False, default=10, comment="最大用户数")
    max_assets = Column(Integer, nullable=False, default=100, comment="最大资产数")
    max_projects = Column(Integer, nullable=False, default=50, comment="最大项目数")
    max_storage_gb = Column(Integer, nullable=False, default=1, comment="最大存储空间(GB)")

    # 联系信息
    contact_name = Column(String(100), comment="联系人姓名")
    contact_email = Column(String(255), comment="联系人邮箱")
    contact_phone = Column(String(50), comment="联系人电话")

    # 业务信息
    industry = Column(String(100), comment="行业")
    company_size = Column(String(50), comment="公司规模")
    description = Column(Text, comment="描述")

    # 暂停和终止信息
    suspension_reason = Column(Text, comment="暂停原因")
    suspended_at = Column(DateTime, comment="暂停时间")
    suspended_by = Column(String, comment="暂停操作人")

    termination_reason = Column(Text, comment="终止原因")
    terminated_at = Column(DateTime, comment="终止时间")
    terminated_by = Column(String, comment="终止操作人")

    # 配置信息
    settings = Column(JSON, nullable=True, comment="租户设置")

    # 审计信息
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    created_by = Column(String, comment="创建人")
    updated_by = Column(String, comment="更新人")

    # 关系
    users = relationship("TenantUser", back_populates="tenant")
    config = relationship("TenantConfig", back_populates="tenant", uselist=False)
    resources = relationship("TenantResource", back_populates="tenant")

    def __repr__(self):
        return f"<Tenant(id={self.id}, name={self.name}, code={self.code}, status={self.status})>"

    @property
    def is_active(self) -> bool:
        """检查租户是否活跃"""
        return self.status == "active"

    @property
    def is_suspended(self) -> bool:
        """检查租户是否被暂停"""
        return self.status == "suspended"

    @property
    def is_terminated(self) -> bool:
        """检查租户是否被终止"""
        return self.status == "terminated"


class TenantUser(Base):
    """租户用户关联模型"""
    __tablename__ = "tenant_users"

    id = Column(String, primary_key=True, index=True)

    # 关联信息
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # 角色和权限
    role = Column(String(50), nullable=False, default="member", comment="租户角色")
    permissions = Column(JSON, nullable=True, comment="租户权限列表")

    # 状态
    is_active = Column(Boolean, nullable=False, default=True, comment="是否激活")

    # 有效期
    joined_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="加入时间")
    expires_at = Column(DateTime, nullable=True, comment="过期时间")

    # 审计信息
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    created_by = Column(String, comment="创建人")
    updated_by = Column(String, comment="更新人")

    # 关系
    tenant = relationship("Tenant", back_populates="users")
    user = relationship("User", overlaps="tenant_memberships")  # 移除 back_populates 以避免循环依赖

    def __repr__(self):
        return f"<TenantUser(tenant_id={self.tenant_id}, user_id={self.user_id}, role={self.role})>"


class TenantConfig(Base):
    """租户配置模型"""
    __tablename__ = "tenant_configs"

    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), unique=True, nullable=False, index=True)

    # 功能开关
    allow_custom_domains = Column(Boolean, default=False, comment="允许自定义域名")
    allow_api_access = Column(Boolean, default=True, comment="允许API访问")
    allow_data_export = Column(Boolean, default=True, comment="允许数据导出")
    allow_data_import = Column(Boolean, default=True, comment="允许数据导入")
    allow_multi_org = Column(Boolean, default=False, comment="允许多组织")

    # 安全设置
    require_mfa = Column(Boolean, default=False, comment="要求多因子认证")
    session_timeout_minutes = Column(Integer, default=480, comment="会话超时时间(分钟)")
    password_policy = Column(JSON, nullable=True, comment="密码策略")
    ip_whitelist = Column(JSON, nullable=True, comment="IP白名单")

    # 功能标志
    feature_flags = Column(JSON, nullable=True, comment="功能标志")

    # 集成设置
    sso_config = Column(JSON, nullable=True, comment="单点登录配置")
    ldap_config = Column(JSON, nullable=True, comment="LDAP配置")
    email_config = Column(JSON, nullable=True, comment="邮件配置")

    # 自定义设置
    custom_settings = Column(JSON, nullable=True, comment="自定义设置")

    # 审计信息
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    created_by = Column(String, comment="创建人")
    updated_by = Column(String, comment="更新人")

    # 关系
    tenant = relationship("Tenant", back_populates="config")

    def __repr__(self):
        return f"<TenantConfig(tenant_id={self.tenant_id}, sso_enabled={bool(self.sso_config)})>"


class TenantResource(Base):
    """租户资源使用记录模型"""
    __tablename__ = "tenant_resources"

    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)

    # 资源信息
    resource_type = Column(String(50), nullable=False, comment="资源类型")
    resource_id = Column(String, nullable=False, comment="资源ID")
    resource_name = Column(String(200), comment="资源名称")

    # 使用统计
    size_bytes = Column(Integer, default=0, comment="资源大小(字节)")
    access_count = Column(Integer, default=0, comment="访问次数")
    last_accessed_at = Column(DateTime, comment="最后访问时间")

    # 创建信息
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    created_by = Column(String, comment="创建人")

    # 关系
    tenant = relationship("Tenant", back_populates="resources")

    def __repr__(self):
        return f"<TenantResource(tenant_id={self.tenant_id}, type={self.resource_type}, id={self.resource_id})>"


class TenantInvoice(Base):
    """租户账单模型"""
    __tablename__ = "tenant_invoices"

    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)

    # 账单信息
    invoice_number = Column(String(100), unique=True, nullable=False, comment="账单号")
    billing_period_start = Column(DateTime, nullable=False, comment="计费期开始")
    billing_period_end = Column(DateTime, nullable=False, comment="计费期结束")

    # 金额信息
    base_amount = Column(Integer, nullable=False, default=0, comment="基础金额")
    usage_amount = Column(Integer, nullable=False, default=0, comment="使用费用")
    discount_amount = Column(Integer, nullable=False, default=0, comment="折扣金额")
    total_amount = Column(Integer, nullable=False, default=0, comment="总金额")
    currency = Column(String(10), default="CNY", comment="货币")

    # 状态
    status = Column(String(50), default="pending", comment="账单状态")
    paid_at = Column(DateTime, comment="支付时间")
    payment_method = Column(String(50), comment="支付方式")

    # 备注
    notes = Column(Text, comment="备注")

    # 审计信息
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    created_by = Column(String, comment="创建人")
    updated_by = Column(String, comment="更新人")

    # 关系
    tenant = relationship("Tenant")

    def __repr__(self):
        return f"<TenantInvoice(id={self.id}, tenant_id={self.tenant_id}, amount={self.total_amount})>"


class TenantAuditLog(Base):
    """租户审计日志模型"""
    __tablename__ = "tenant_audit_logs"

    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)

    # 操作信息
    action = Column(String(100), nullable=False, comment="操作动作")
    resource_type = Column(String(50), comment="资源类型")
    resource_id = Column(String, comment="资源ID")
    resource_name = Column(String(200), comment="资源名称")

    # 用户信息
    user_id = Column(String, ForeignKey("users.id"), comment="操作用户ID")
    username = Column(String(50), comment="操作用户名")
    user_role = Column(String(50), comment="用户角色")

    # 变更信息
    old_values = Column(JSON, nullable=True, comment="变更前值")
    new_values = Column(JSON, nullable=True, comment="变更后值")
    changes_summary = Column(Text, comment="变更摘要")

    # 环境信息
    ip_address = Column(String(45), comment="IP地址")
    user_agent = Column(Text, comment="用户代理")
    session_id = Column(String(100), comment="会话ID")

    # 时间信息
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")

    # 关系
    tenant = relationship("Tenant")
    user = relationship("User")

    def __repr__(self):
        return f"<TenantAuditLog(tenant_id={self.tenant_id}, action={self.action}, user={self.username})>"


class TenantApiKey(Base):
    """租户API密钥模型"""
    __tablename__ = "tenant_api_keys"

    id = Column(String, primary_key=True, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)

    # 密钥信息
    key_name = Column(String(100), nullable=False, comment="密钥名称")
    key_hash = Column(String(255), nullable=False, unique=True, comment="密钥哈希")
    key_prefix = Column(String(20), nullable=False, comment="密钥前缀(用于显示)")

    # 权限和限制
    permissions = Column(JSON, nullable=True, comment="API权限")
    rate_limit = Column(Integer, default=1000, comment="速率限制(每小时)")
    allowed_ips = Column(JSON, nullable=True, comment="允许的IP地址")

    # 状态
    is_active = Column(Boolean, nullable=False, default=True, comment="是否激活")
    expires_at = Column(DateTime, nullable=True, comment="过期时间")

    # 使用统计
    last_used_at = Column(DateTime, comment="最后使用时间")
    usage_count = Column(Integer, default=0, comment="使用次数")

    # 审计信息
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    created_by = Column(String, comment="创建人")
    revoked_at = Column(DateTime, comment="撤销时间")
    revoked_by = Column(String, comment="撤销人")

    # 关系
    tenant = relationship("Tenant")

    def __repr__(self):
        return f"<TenantApiKey(tenant_id={self.tenant_id}, name={self.key_name}, prefix={self.key_prefix})>"