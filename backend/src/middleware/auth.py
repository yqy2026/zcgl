"""
认证中间件
"""

import logging
from collections.abc import Mapping
from typing import Any

import jwt as jwt
from fastapi import Cookie, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.environment import is_production as is_production
from ..core.exception_handler import forbidden
from ..database import get_async_db
from ..models.auth import User
from ..schemas.auth import TokenData
from ..schemas.authz import ScopeMode
from ..security.cookie_manager import cookie_manager as cookie_manager
from ..services import RBACService
from ..services.authz import authz_service
from . import identity as identity_service
from .audit import AuditLogger as _AuditLogger
from .authorization import (
    AuthzContext as AuthzContext,
)
from .authorization import (
    AuthzPermissionChecker as _AuthzPermissionChecker,
)
from .authorization import (
    ResourceContextResolver,
    ResourceIdResolver,
)
from .data_scope import DataScopeContext as DataScopeContext
from .data_scope import DataScopeContextChecker as _DataScopeContextChecker
from .security_config import SecurityConfig as SecurityConfig

logger = logging.getLogger(__name__)

_token_blacklist_circuit = identity_service._token_blacklist_circuit


def _is_token_blacklisted(
    jti: str | None,
    user_id: str | None = None,
    session_id: str | None = None,
    token_iat: int | float | None = None,
) -> bool:
    """检查 token 是否在黑名单中（熔断/异常统一 fail-closed）。"""
    return identity_service._is_token_blacklisted(
        jti=jti,
        user_id=user_id,
        session_id=session_id,
        token_iat=token_iat,
    )


def _validate_jwt_token(token: str) -> TokenData:
    """共享的JWT验证逻辑。"""
    return identity_service._validate_jwt_token(
        token,
        blacklist_checker=_is_token_blacklisted,
        log=logger,
    )


async def get_current_user(
    auth_token: str | None = Cookie(None, alias=cookie_manager.cookie_name),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Cookie-only authentication. Tokens are read from httpOnly cookies.
    """
    return await identity_service.resolve_current_user(
        # The request-provided JWT is not a hardcoded credential.
        auth_token=auth_token,  # nosec B106
        db=db,
        missing_token_message="无效的认证凭据",
        invalid_token_message="无效的认证凭据",
        missing_user_message="无效的认证凭据",
        disabled_user_message="用户账户已被禁用",
        locked_user_message="用户账户已被锁定，请稍后再试",
        token_validator=_validate_jwt_token,
    )


async def get_current_user_from_cookie(
    auth_token: str | None = Cookie(None, alias=cookie_manager.cookie_name),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """
    Get current user from httpOnly cookie.

    Args:
        auth_token: JWT from httpOnly cookie (automatically sent by browser)
        db: Database session

    Returns:
        User: Authenticated user object

    Raises:
        unauthorized: If no valid token found or user is inactive/locked
    """
    return await identity_service.resolve_current_user(
        # The request-provided JWT is not a hardcoded credential.
        auth_token=auth_token,  # nosec B106
        db=db,
        missing_token_message="Not authenticated",
        invalid_token_message="Invalid token",
        missing_user_message="Invalid authentication credentials",
        disabled_user_message="User account is disabled",
        locked_user_message="User account is locked, please try again later",
        token_validator=_validate_jwt_token,
    )


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户"""
    return identity_service.ensure_current_active_user(current_user)


async def require_admin(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """要求管理员权限"""
    rbac_service = RBACService(db)
    if not await rbac_service.is_admin(current_user.id):
        raise forbidden("需要管理员权限")
    return current_user


async def get_optional_current_user(
    auth_token: str | None = Cookie(None, alias=cookie_manager.cookie_name),
    db: AsyncSession = Depends(get_async_db),
) -> User | None:
    """获取可选的当前用户（用于可选认证的端点）"""
    return await identity_service.resolve_optional_current_user(
        auth_token=auth_token,
        db=db,
        token_validator=_validate_jwt_token,
    )


class DataScopeContextChecker(_DataScopeContextChecker):
    """Public auth-module data-scope dependency wrapper."""

    async def __call__(
        self,
        request: Request,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db),
    ) -> DataScopeContext | None:
        return await self.resolve(
            request=request,
            current_user=current_user,
            db=db,
        )


class AuthzPermissionChecker(_AuthzPermissionChecker):
    """Public auth-module ABAC dependency wrapper."""

    async def __call__(
        self,
        request: Request,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db),
    ) -> AuthzContext:
        return await self.resolve(
            request=request,
            current_user=current_user,
            db=db,
        )


def require_authz(
    action: str,
    resource_type: str,
    resource_id: str | ResourceIdResolver | None = None,
    resource_context: Mapping[str, Any] | ResourceContextResolver | None = None,
    *,
    deny_as_not_found: bool = False,
) -> AuthzPermissionChecker:
    """ABAC 鉴权依赖工厂。"""
    return AuthzPermissionChecker(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_context=resource_context,
        deny_as_not_found=deny_as_not_found,
        authz_service_client=authz_service,
        log=logger,
    )


def require_data_scope_context(
    *,
    resource_type: str | None = None,
    accepts_view_mode: bool | None = None,
    query_modes: tuple[ScopeMode, ...] = ("owner", "manager", "all"),
    require_single_perspective: bool = False,
) -> DataScopeContextChecker:
    """Data-scope request-contract dependency factory."""
    return DataScopeContextChecker(
        resource_type=resource_type,
        accepts_view_mode=accepts_view_mode,
        query_modes=query_modes,
        require_single_perspective=require_single_perspective,
        authz_service_getter=lambda: authz_service,
        rbac_service_factory=lambda db: RBACService(db),
    )


class AuditLogger(_AuditLogger):
    """Public auth-module audit dependency wrapper."""

    async def __call__(
        self,
        request: Request,
        current_user: User | None = Depends(get_optional_current_user),
        db: AsyncSession = Depends(get_async_db),
    ) -> User | None:
        return await self.resolve(
            request=request,
            current_user=current_user,
            db=db,
        )


def audit_action(action: str, resource_type: str | None = None) -> AuditLogger:
    """审计装饰器工厂函数"""
    return AuditLogger(action, resource_type)
