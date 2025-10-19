"""
多租户支持服务
提供完整的租户管理和数据隔离功能
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from ..models.tenant import Tenant, TenantUser, TenantConfig, TenantResource
from ..models.auth import User
from ..models.organization import Organization
from ..models.asset import Asset
from ..exceptions import BusinessLogicError


class TenantStatus(str, Enum):
    """租户状态"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    PENDING = "pending"


class TenantPlan(str, Enum):
    """租户计划"""
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class ResourceType(str, Enum):
    """资源类型"""
    ASSET = "asset"
    PROJECT = "project"
    USER = "user"
    STORAGE = "storage"
    API_CALL = "api_call"


class MultiTenantService:
    """多租户服务"""

    def __init__(self, db: Session):
        self.db = db

    def create_tenant(
        self,
        name: str,
        code: str,
        domain: Optional[str] = None,
        plan: TenantPlan = TenantPlan.BASIC,
        max_users: int = 10,
        max_assets: int = 100,
        max_storage_gb: int = 1,
        admin_user_id: Optional[str] = None,
        created_by: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> Tenant:
        """
        创建新租户

        Args:
            name: 租户名称
            code: 租户代码（唯一）
            domain: 自定义域名
            plan: 租户计划
            max_users: 最大用户数
            max_assets: 最大资产数
            max_storage_gb: 最大存储空间(GB)
            admin_user_id: 管理员用户ID
            created_by: 创建人
            settings: 租户设置

        Returns:
            创建的租户对象
        """
        # 检查租户代码是否已存在
        existing_tenant = self.db.query(Tenant).filter(
            Tenant.code == code
        ).first()

        if existing_tenant:
            raise BusinessLogicError(f"租户代码 {code} 已存在")

        # 创建租户
        tenant = Tenant(
            name=name,
            code=code,
            domain=domain,
            plan=plan,
            status=TenantStatus.PENDING,
            max_users=max_users,
            max_assets=max_assets,
            max_storage_gb=max_storage_gb,
            created_by=created_by,
            settings=settings or {}
        )

        self.db.add(tenant)
        self.db.flush()  # 获取tenant.id

        # 创建默认租户配置
        tenant_config = TenantConfig(
            tenant_id=tenant.id,
            allow_custom_domains=False,
            allow_api_access=True,
            allow_data_export=True,
            require_mfa=False,
            session_timeout_minutes=480,
            password_policy={
                "min_length": 8,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_numbers": True,
                "require_symbols": False
            },
            ip_whitelist=[],
            feature_flags={
                "advanced_analytics": plan in [TenantPlan.PROFESSIONAL, TenantPlan.ENTERPRISE],
                "custom_reports": plan in [TenantPlan.PROFESSIONAL, TenantPlan.ENTERPRISE],
                "api_access": True,
                "data_export": True,
                "multi_org": plan == TenantPlan.ENTERPRISE
            }
        )

        self.db.add(tenant_config)

        # 如果指定了管理员用户，创建租户用户关联
        if admin_user_id:
            tenant_user = TenantUser(
                tenant_id=tenant.id,
                user_id=admin_user_id,
                role="admin",
                is_active=True,
                created_by=created_by
            )
            self.db.add(tenant_user)

        self.db.commit()
        self.db.refresh(tenant)

        return tenant

    def get_tenant_by_id(self, tenant_id: str) -> Optional[Tenant]:
        """根据ID获取租户"""
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def get_tenant_by_code(self, tenant_code: str) -> Optional[Tenant]:
        """根据代码获取租户"""
        return self.db.query(Tenant).filter(Tenant.code == tenant_code).first()

    def get_tenant_by_domain(self, domain: str) -> Optional[Tenant]:
        """根据域名获取租户"""
        return self.db.query(Tenant).filter(
            or_(
                Tenant.domain == domain,
                Tenant.code == domain  # 也支持代码作为子域名
            )
        ).first()

    def update_tenant(
        self,
        tenant_id: str,
        name: Optional[str] = None,
        domain: Optional[str] = None,
        plan: Optional[TenantPlan] = None,
        max_users: Optional[int] = None,
        max_assets: Optional[int] = None,
        max_storage_gb: Optional[int] = None,
        status: Optional[TenantStatus] = None,
        settings: Optional[Dict[str, Any]] = None,
        updated_by: Optional[str] = None
    ) -> Tenant:
        """
        更新租户信息

        Args:
            tenant_id: 租户ID
            name: 租户名称
            domain: 自定义域名
            plan: 租户计划
            max_users: 最大用户数
            max_assets: 最大资产数
            max_storage_gb: 最大存储空间
            status: 租户状态
            settings: 租户设置
            updated_by: 更新人

        Returns:
            更新后的租户对象
        """
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            raise BusinessLogicError(f"租户 {tenant_id} 不存在")

        # 更新字段
        if name is not None:
            tenant.name = name
        if domain is not None:
            # 检查域名是否已被其他租户使用
            existing = self.db.query(Tenant).filter(
                and_(
                    Tenant.domain == domain,
                    Tenant.id != tenant_id
                )
            ).first()
            if existing:
                raise BusinessLogicError(f"域名 {domain} 已被其他租户使用")
            tenant.domain = domain
        if plan is not None:
            tenant.plan = plan
        if max_users is not None:
            tenant.max_users = max_users
        if max_assets is not None:
            tenant.max_assets = max_assets
        if max_storage_gb is not None:
            tenant.max_storage_gb = max_storage_gb
        if status is not None:
            tenant.status = status
        if settings is not None:
            tenant.settings.update(settings)

        tenant.updated_by = updated_by
        tenant.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(tenant)

        return tenant

    def add_user_to_tenant(
        self,
        tenant_id: str,
        user_id: str,
        role: str = "member",
        permissions: Optional[List[str]] = None,
        created_by: Optional[str] = None
    ) -> TenantUser:
        """
        将用户添加到租户

        Args:
            tenant_id: 租户ID
            user_id: 用户ID
            role: 用户角色 (admin, manager, member)
            permissions: 权限列表
            created_by: 创建人

        Returns:
            租户用户关联对象
        """
        # 检查租户是否存在
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            raise BusinessLogicError(f"租户 {tenant_id} 不存在")

        # 检查用户是否已在租户中
        existing = self.db.query(TenantUser).filter(
            and_(
                TenantUser.tenant_id == tenant_id,
                TenantUser.user_id == user_id
            )
        ).first()

        if existing:
            raise BusinessLogicError(f"用户 {user_id} 已在租户 {tenant_id} 中")

        # 检查租户用户数限制
        current_user_count = self.db.query(TenantUser).filter(
            and_(
                TenantUser.tenant_id == tenant_id,
                TenantUser.is_active == True
            )
        ).count()

        if current_user_count >= tenant.max_users:
            raise BusinessLogicError(f"租户 {tenant_id} 用户数已达上限 {tenant.max_users}")

        # 创建租户用户关联
        tenant_user = TenantUser(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            permissions=permissions or [],
            is_active=True,
            created_by=created_by
        )

        self.db.add(tenant_user)
        self.db.commit()
        self.db.refresh(tenant_user)

        return tenant_user

    def remove_user_from_tenant(
        self,
        tenant_id: str,
        user_id: str,
        removed_by: Optional[str] = None
    ) -> bool:
        """
        从租户中移除用户

        Args:
            tenant_id: 租户ID
            user_id: 用户ID
            removed_by: 移除人

        Returns:
            是否成功移除
        """
        tenant_user = self.db.query(TenantUser).filter(
            and_(
                TenantUser.tenant_id == tenant_id,
                TenantUser.user_id == user_id
            )
        ).first()

        if not tenant_user:
            return False

        # 不能移除最后一个管理员
        if tenant_user.role == "admin":
            admin_count = self.db.query(TenantUser).filter(
                and_(
                    TenantUser.tenant_id == tenant_id,
                    TenantUser.role == "admin",
                    TenantUser.is_active == True
                )
            ).count()

            if admin_count <= 1:
                raise BusinessLogicError("不能移除租户中最后一个管理员")

        self.db.delete(tenant_user)
        self.db.commit()

        return True

    def get_tenant_users(
        self,
        tenant_id: str,
        include_inactive: bool = False,
        role: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取租户用户列表

        Args:
            tenant_id: 租户ID
            include_inactive: 是否包含非活跃用户
            role: 角色筛选

        Returns:
            用户列表
        """
        query = self.db.query(TenantUser).filter(TenantUser.tenant_id == tenant_id)

        if not include_inactive:
            query = query.filter(TenantUser.is_active == True)

        if role:
            query = query.filter(TenantUser.role == role)

        tenant_users = query.all()

        result = []
        for tenant_user in tenant_users:
            user = self.db.query(User).filter(User.id == tenant_user.user_id).first()
            if user:
                result.append({
                    "tenant_user_id": tenant_user.id,
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": tenant_user.role,
                    "permissions": tenant_user.permissions,
                    "is_active": tenant_user.is_active,
                    "joined_at": tenant_user.created_at
                })

        return result

    def get_user_tenants(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户所属的租户列表

        Args:
            user_id: 用户ID

        Returns:
            租户列表
        """
        tenant_users = self.db.query(TenantUser).filter(
            and_(
                TenantUser.user_id == user_id,
                TenantUser.is_active == True
            )
        ).all()

        result = []
        for tenant_user in tenant_users:
            tenant = self.get_tenant_by_id(tenant_user.tenant_id)
            if tenant and tenant.status == TenantStatus.ACTIVE:
                result.append({
                    "tenant_id": tenant.id,
                    "tenant_name": tenant.name,
                    "tenant_code": tenant.code,
                    "domain": tenant.domain,
                    "plan": tenant.plan,
                    "role": tenant_user.role,
                    "permissions": tenant_user.permissions,
                    "joined_at": tenant_user.created_at
                })

        return result

    def check_tenant_resource_limit(
        self,
        tenant_id: str,
        resource_type: ResourceType,
        additional_count: int = 1
    ) -> Tuple[bool, str]:
        """
        检查租户资源限制

        Args:
            tenant_id: 租户ID
            resource_type: 资源类型
            additional_count: 额外增加的数量

        Returns:
            (是否允许, 原因)
        """
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            return False, "租户不存在"

        if tenant.status != TenantStatus.ACTIVE:
            return False, f"租户状态为 {tenant.status}，无法使用资源"

        current_count = 0
        limit = 0

        if resource_type == ResourceType.USER:
            current_count = self.db.query(TenantUser).filter(
                and_(
                    TenantUser.tenant_id == tenant_id,
                    TenantUser.is_active == True
                )
            ).count()
            limit = tenant.max_users

        elif resource_type == ResourceType.ASSET:
            # 这里需要根据实际的资产表结构来查询
            # 假设资产表有tenant_id字段
            current_count = self.db.query(Asset).filter(
                Asset.ownership_entity == tenant.name  # 临时使用名称匹配
            ).count()
            limit = tenant.max_assets

        elif resource_type == ResourceType.PROJECT:
            # 项目统计暂时跳过，因为项目模型不存在
            current_count = 0
            limit = getattr(tenant, 'max_projects', 50)  # 假设有这个字段

        if current_count + additional_count > limit:
            return False, f"{resource_type.value} 资源超限，当前 {current_count}，限制 {limit}，申请增加 {additional_count}"

        return True, "资源检查通过"

    def get_tenant_usage_stats(self, tenant_id: str) -> Dict[str, Any]:
        """
        获取租户使用统计

        Args:
            tenant_id: 租户ID

        Returns:
            使用统计信息
        """
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            raise BusinessLogicError(f"租户 {tenant_id} 不存在")

        # 获取各项资源使用情况
        user_count = self.db.query(TenantUser).filter(
            and_(
                TenantUser.tenant_id == tenant_id,
                TenantUser.is_active == True
            )
        ).count()

        asset_count = self.db.query(Asset).filter(
            Asset.ownership_entity == tenant.name
        ).count()

        project_count = 0  # 项目统计暂时跳过，因为项目模型不存在

        # 计算使用率
        stats = {
            "tenant_info": {
                "id": tenant.id,
                "name": tenant.name,
                "code": tenant.code,
                "plan": tenant.plan,
                "status": tenant.status
            },
            "usage": {
                "users": {
                    "current": user_count,
                    "limit": tenant.max_users,
                    "usage_percentage": round(user_count / tenant.max_users * 100, 2) if tenant.max_users > 0 else 0
                },
                "assets": {
                    "current": asset_count,
                    "limit": tenant.max_assets,
                    "usage_percentage": round(asset_count / tenant.max_assets * 100, 2) if tenant.max_assets > 0 else 0
                },
                "projects": {
                    "current": project_count,
                    "limit": getattr(tenant, 'max_projects', 50),
                    "usage_percentage": round(project_count / getattr(tenant, 'max_projects', 50) * 100, 2)
                },
                "storage": {
                    "current": 0,  # 需要实现存储统计
                    "limit": tenant.max_storage_gb,
                    "usage_percentage": 0
                }
            },
            "limits": {
                "max_users": tenant.max_users,
                "max_assets": tenant.max_assets,
                "max_storage_gb": tenant.max_storage_gb
            }
        }

        return stats

    def update_tenant_config(
        self,
        tenant_id: str,
        config_updates: Dict[str, Any],
        updated_by: Optional[str] = None
    ) -> TenantConfig:
        """
        更新租户配置

        Args:
            tenant_id: 租户ID
            config_updates: 配置更新
            updated_by: 更新人

        Returns:
            更新后的配置对象
        """
        config = self.db.query(TenantConfig).filter(
            TenantConfig.tenant_id == tenant_id
        ).first()

        if not config:
            raise BusinessLogicError(f"租户 {tenant_id} 配置不存在")

        # 更新配置
        for key, value in config_updates.items():
            if hasattr(config, key):
                setattr(config, key, value)

        config.updated_by = updated_by
        config.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(config)

        return config

    def get_tenant_config(self, tenant_id: str) -> Optional[TenantConfig]:
        """获取租户配置"""
        return self.db.query(TenantConfig).filter(
            TenantConfig.tenant_id == tenant_id
        ).first()

    def suspend_tenant(
        self,
        tenant_id: str,
        reason: str,
        suspended_by: Optional[str] = None
    ) -> Tenant:
        """
        暂停租户

        Args:
            tenant_id: 租户ID
            reason: 暂停原因
            suspended_by: 暂停操作人

        Returns:
            更新后的租户对象
        """
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            raise BusinessLogicError(f"租户 {tenant_id} 不存在")

        tenant.status = TenantStatus.SUSPENDED
        tenant.suspension_reason = reason
        tenant.suspended_at = datetime.utcnow()
        tenant.suspended_by = suspended_by

        self.db.commit()
        self.db.refresh(tenant)

        return tenant

    def activate_tenant(
        self,
        tenant_id: str,
        activated_by: Optional[str] = None
    ) -> Tenant:
        """
        激活租户

        Args:
            tenant_id: 租户ID
            activated_by: 激活操作人

        Returns:
            更新后的租户对象
        """
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            raise BusinessLogicError(f"租户 {tenant_id} 不存在")

        tenant.status = TenantStatus.ACTIVE
        tenant.suspension_reason = None
        tenant.suspended_at = None
        tenant.suspended_by = None
        tenant.updated_by = activated_by
        tenant.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(tenant)

        return tenant

    def terminate_tenant(
        self,
        tenant_id: str,
        reason: str,
        terminated_by: Optional[str] = None
    ) -> Tenant:
        """
        终止租户

        Args:
            tenant_id: 租户ID
            reason: 终止原因
            terminated_by: 终止操作人

        Returns:
            更新后的租户对象
        """
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            raise BusinessLogicError(f"租户 {tenant_id} 不存在")

        tenant.status = TenantStatus.TERMINATED
        tenant.termination_reason = reason
        tenant.terminated_at = datetime.utcnow()
        tenant.terminated_by = terminated_by

        # 停用所有租户用户
        self.db.query(TenantUser).filter(
            TenantUser.tenant_id == tenant_id
        ).update({"is_active": False})

        self.db.commit()
        self.db.refresh(tenant)

        return tenant

    def get_tenant_list(
        self,
        status: Optional[TenantStatus] = None,
        plan: Optional[TenantPlan] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        获取租户列表

        Args:
            status: 状态筛选
            plan: 计划筛选
            page: 页码
            limit: 每页数量

        Returns:
            租户列表和分页信息
        """
        query = self.db.query(Tenant)

        if status:
            query = query.filter(Tenant.status == status)

        if plan:
            query = query.filter(Tenant.plan == plan)

        total = query.count()
        tenants = query.offset((page - 1) * limit).limit(limit).all()

        return {
            "tenants": tenants,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }