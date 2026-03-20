"""
认证中间件 — 向后兼容的重导出模块。

实际实现已拆分为:
- auth_core.py          : Token 验证、用户解析
- auth_authz.py         : ABAC 鉴权 (AuthzPermissionChecker)
- auth_scope_loaders.py : 资源 scope context 加载器 (Mixin)
- auth_utils.py         : 权限检查器、审计日志、安全配置

本文件仅做 re-export，确保 ``from src.middleware.auth import X`` 继续工作。
"""

# --- auth_authz: ABAC 鉴权 ---
from .auth_authz import (  # noqa: F401
    AuthzContext,
    AuthzPermissionChecker,
    ResourceContextResolver,
    ResourceIdResolver,
    authz_service,
    require_authz,
)

# --- auth_core: Token 验证 & 用户解析 ---
# Re-export jwt, is_production, and logger so that `auth.jwt` / `auth.is_production`
# / `auth.logger` work (needed by tests that monkeypatch these on the hub module).
from .auth_core import (  # noqa: F401
    RBACService,
    _get_jwt_settings,
    _is_token_blacklisted,
    _token_blacklist_circuit,
    _token_blacklist_guard,
    _validate_jwt_token,
    get_current_active_user,
    get_current_user,
    get_current_user_from_cookie,
    get_optional_current_user,
    is_production,
    jwt,
    logger,
    require_admin,
)

# --- auth_scope_loaders: Scope context 加载器 Mixin ---
from .auth_scope_loaders import AuthzScopeLoaderMixin  # noqa: F401

# --- auth_utils: 权限检查器 / 审计 / 安全配置 ---
from .auth_utils import (  # noqa: F401
    AuditLogger,
    OrganizationPermissionChecker,
    PermissionChecker,
    RBACPermissionChecker,
    ResourcePermissionChecker,
    RoleBasedAccessChecker,
    SecurityConfig,
    audit_action,
    can_edit_contract,
    get_user_rbac_permissions,
    require_organization_access,
    require_permission,
    require_permissions,
    require_resource_permission,
    require_roles,
)

__all__ = [
    # auth_core (re-exported for monkeypatch compatibility)
    "jwt",
    "is_production",
    "logger",
    "RBACService",
    "_get_jwt_settings",
    "_is_token_blacklisted",
    "_token_blacklist_circuit",
    "_token_blacklist_guard",
    "_validate_jwt_token",
    "get_current_active_user",
    "get_current_user",
    "get_current_user_from_cookie",
    "get_optional_current_user",
    "require_admin",
    # auth_authz
    "AuthzContext",
    "AuthzPermissionChecker",
    "ResourceContextResolver",
    "ResourceIdResolver",
    "authz_service",
    "require_authz",
    # auth_scope_loaders
    "AuthzScopeLoaderMixin",
    # auth_utils
    "AuditLogger",
    "OrganizationPermissionChecker",
    "PermissionChecker",
    "RBACPermissionChecker",
    "ResourcePermissionChecker",
    "RoleBasedAccessChecker",
    "SecurityConfig",
    "audit_action",
    "can_edit_contract",
    "get_user_rbac_permissions",
    "require_organization_access",
    "require_permission",
    "require_permissions",
    "require_resource_permission",
    "require_roles",
]
