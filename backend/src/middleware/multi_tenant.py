"""
多租户中间件
提供租户识别、数据隔离和访问控制功能
"""

from typing import Optional, List, Dict, Any
from functools import wraps
from fastapi import HTTPException, Depends, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.auth import User
from ..models.tenant import Tenant, TenantUser
from ..services.multi_tenant_service import MultiTenantService, TenantStatus
from ..exceptions import BusinessLogicError


class TenantContext:
    """租户上下文"""

    def __init__(
        self,
        tenant_id: str,
        tenant_code: str,
        user_role: str,
        permissions: List[str],
        tenant_config: Dict[str, Any]
    ):
        self.tenant_id = tenant_id
        self.tenant_code = tenant_code
        self.user_role = user_role
        self.permissions = permissions
        self.tenant_config = tenant_config

    @property
    def is_admin(self) -> bool:
        """检查是否为租户管理员"""
        return self.user_role == "admin"

    @property
    def is_manager(self) -> bool:
        """检查是否为租户管理者"""
        return self.user_role in ["admin", "manager"]

    def has_permission(self, permission: str) -> bool:
        """检查是否有特定权限"""
        return permission in self.permissions

    def has_any_permission(self, permissions: List[str]) -> bool:
        """检查是否有任一权限"""
        return any(perm in self.permissions for perm in permissions)

    def has_all_permissions(self, permissions: List[str]) -> bool:
        """检查是否有所有权限"""
        return all(perm in self.permissions for perm in permissions)


def get_tenant_from_request(request: Request) -> Optional[str]:
    """从请求中获取租户信息"""

    # 1. 从子域名获取租户
    host = request.headers.get("host", "")
    if "." in host:
        subdomain = host.split(".")[0]
        if subdomain and subdomain != "www":
            return subdomain

    # 2. 从请求头获取租户
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        return tenant_id

    tenant_code = request.headers.get("X-Tenant-Code")
    if tenant_code:
        return tenant_code

    # 3. 从URL路径获取租户 (如果使用路径隔离)
    # 例如: /api/v1/{tenant_code}/assets
    path_parts = request.url.path.strip("/").split("/")
    if len(path_parts) >= 4 and path_parts[0] == "api" and path_parts[1] == "v1":
        potential_tenant = path_parts[2]
        if potential_tenant and potential_tenant not in ["auth", "admin", "system"]:
            return potential_tenant

    return None


def get_tenant_context(
    request: Request,
    current_user: User = Depends(lambda: None),  # 实际使用时需要替换为真实的认证依赖
    db: Session = Depends(get_db)
) -> TenantContext:
    """获取租户上下文"""

    # 获取租户标识
    tenant_identifier = get_tenant_from_request(request)

    if not tenant_identifier:
        raise HTTPException(
            status_code=400,
            detail="无法确定租户信息，请在请求中提供租户标识"
        )

    multi_tenant_service = MultiTenantService(db)

    # 查找租户
    tenant = None

    # 尝试通过ID查找
    tenant = multi_tenant_service.get_tenant_by_id(tenant_identifier)

    # 如果没找到，尝试通过代码查找
    if not tenant:
        tenant = multi_tenant_service.get_tenant_by_code(tenant_identifier)

    # 如果还没找到，尝试通过域名查找
    if not tenant:
        tenant = multi_tenant_service.get_tenant_by_domain(tenant_identifier)

    if not tenant:
        raise HTTPException(
            status_code=404,
            detail=f"租户 {tenant_identifier} 不存在"
        )

    # 检查租户状态
    if tenant.status != TenantStatus.ACTIVE:
        raise HTTPException(
            status_code=403,
            detail=f"租户 {tenant.name} 状态为 {tenant.status}，无法访问"
        )

    # 如果用户已认证，检查用户是否属于该租户
    if current_user:
        tenant_user = db.query(TenantUser).filter(
            TenantUser.tenant_id == tenant.id,
            TenantUser.user_id == current_user.id,
            TenantUser.is_active == True
        ).first()

        if not tenant_user:
            raise HTTPException(
                status_code=403,
                detail=f"用户 {current_user.username} 不属于租户 {tenant.name}"
            )

        # 获取租户配置
        tenant_config = multi_tenant_service.get_tenant_config(tenant.id)

        return TenantContext(
            tenant_id=tenant.id,
            tenant_code=tenant.code,
            user_role=tenant_user.role,
            permissions=tenant_user.permissions or [],
            tenant_config=tenant_config.settings if tenant_config else {}
        )

    # 如果用户未认证，返回基础租户信息（用于公开API）
    return TenantContext(
        tenant_id=tenant.id,
        tenant_code=tenant.code,
        user_role="anonymous",
        permissions=[],
        tenant_config={}
    )


def require_tenant_permission(permission: str):
    """要求租户权限的装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从kwargs中获取tenant_context
            tenant_context = kwargs.get('tenant_context')
            if not tenant_context:
                raise HTTPException(
                    status_code=500,
                    detail="缺少租户上下文"
                )

            if not tenant_context.has_permission(permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"需要租户权限: {permission}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_tenant_role(role: str):
    """要求租户角色的装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从kwargs中获取tenant_context
            tenant_context = kwargs.get('tenant_context')
            if not tenant_context:
                raise HTTPException(
                    status_code=500,
                    detail="缺少租户上下文"
                )

            if tenant_context.user_role != role and tenant_context.user_role != "admin":
                raise HTTPException(
                    status_code=403,
                    detail=f"需要租户角色: {role}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_tenant_admin():
    """要求租户管理员权限的装饰器"""
    return require_tenant_role("admin")


def require_tenant_manager():
    """要求租户管理者权限的装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tenant_context = kwargs.get('tenant_context')
            if not tenant_context:
                raise HTTPException(
                    status_code=500,
                    detail="缺少租户上下文"
                )

            if not tenant_context.is_manager:
                raise HTTPException(
                    status_code=403,
                    detail="需要租户管理员或管理者权限"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


class TenantDataFilter:
    """租户数据过滤器"""

    def __init__(self, tenant_context: TenantContext):
        self.tenant_context = tenant_context

    def filter_assets_query(self, query):
        """过滤资产查询"""
        # 根据租户代码过滤资产
        return query.filter(
            # 假设资产有ownership_entity字段存储租户信息
            # 或者可以通过tenant_id字段直接关联
        )

    def filter_projects_query(self, query):
        """过滤项目查询"""
        # 根据租户过滤项目
        return query.filter(
            # 假设项目有ownership_entity字段存储租户信息
        )

    def filter_users_query(self, query):
        """过滤用户查询"""
        # 根据租户过滤用户
        if self.tenant_context.is_admin:
            # 管理员可以看到租户内所有用户
            return query.join(TenantUser).filter(
                TenantUser.tenant_id == self.tenant_context.tenant_id,
                TenantUser.is_active == True
            )
        else:
            # 普通用户只能看到自己
            return query.filter(User.id == self.tenant_context.user_id)

    def check_resource_access(self, resource_type: str, resource_id: str) -> bool:
        """检查资源访问权限"""
        # 这里可以实现具体的资源访问检查逻辑
        # 例如检查资产是否属于当前租户
        return True


def get_tenant_filter(
    tenant_context: TenantContext = Depends(get_tenant_context)
) -> TenantDataFilter:
    """获取租户数据过滤器"""
    return TenantDataFilter(tenant_context)


def validate_tenant_resource_limit(resource_type: str, additional_count: int = 1):
    """验证租户资源限制的装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tenant_context = kwargs.get('tenant_context')
            db = kwargs.get('db')

            if not tenant_context or not db:
                raise HTTPException(
                    status_code=500,
                    detail="缺少租户上下文或数据库连接"
                )

            multi_tenant_service = MultiTenantService(db)
            from ..services.multi_tenant_service import ResourceType

            # 检查资源限制
            resource_type_enum = ResourceType(resource_type.lower())
            allowed, reason = multi_tenant_service.check_tenant_resource_limit(
                tenant_context.tenant_id,
                resource_type_enum,
                additional_count
            )

            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail=reason
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def tenant_audit_log(action: str, resource_type: str = None):
    """记录租户审计日志的装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tenant_context = kwargs.get('tenant_context')
            current_user = kwargs.get('current_user')
            db = kwargs.get('db')

            # 执行原函数
            result = await func(*args, **kwargs)

            # 记录审计日志
            if tenant_context and current_user and db:
                try:
                    from ..models.tenant import TenantAuditLog
                    import uuid

                    audit_log = TenantAuditLog(
                        id=str(uuid.uuid4()),
                        tenant_id=tenant_context.tenant_id,
                        action=action,
                        resource_type=resource_type,
                        user_id=current_user.id,
                        username=current_user.username,
                        user_role=tenant_context.user_role,
                        # 可以根据需要添加更多审计信息
                    )

                    db.add(audit_log)
                    db.commit()
                except Exception as e:
                    # 审计日志记录失败不应该影响主业务流程
                    print(f"记录租户审计日志失败: {e}")

            return result
        return wrapper
    return decorator


# 租户功能开关检查
def check_tenant_feature(feature_name: str):
    """检查租户功能开关的装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tenant_context = kwargs.get('tenant_context')

            if not tenant_context:
                raise HTTPException(
                    status_code=500,
                    detail="缺少租户上下文"
                )

            feature_flags = tenant_context.tenant_config.get("feature_flags", {})

            if not feature_flags.get(feature_name, False):
                raise HTTPException(
                    status_code=403,
                    detail=f"租户未启用功能: {feature_name}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# IP白名单检查
def check_tenant_ip_whitelist():
    """检查租户IP白名单的装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tenant_context = kwargs.get('tenant_context')
            request = kwargs.get('request')

            if not tenant_context or not request:
                raise HTTPException(
                    status_code=500,
                    detail="缺少租户上下文或请求信息"
                )

            ip_whitelist = tenant_context.tenant_config.get("ip_whitelist", [])

            if ip_whitelist:
                client_ip = request.client.host
                if client_ip not in ip_whitelist:
                    raise HTTPException(
                        status_code=403,
                        detail=f"IP地址 {client_ip} 不在租户白名单中"
                    )

            return await func(*args, **kwargs)
        return wrapper
    return decorator