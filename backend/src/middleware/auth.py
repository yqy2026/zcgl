"""
认证中间件
"""

import inspect
import logging
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import jwt
from fastapi import Cookie, Depends, Request
from jwt import PyJWTError as JWTError
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.environment import is_production
from ..core.exception_handler import (
    BaseBusinessError,
    bad_request,
    forbidden,
    not_found,
    unauthorized,
)
from ..crud.auth import AuditLogCRUD
from ..database import get_async_db
from ..models.auth import User
from ..schemas.auth import TokenData
from ..schemas.rbac import PermissionCheckRequest
from ..security.cookie_manager import cookie_manager
from ..services import RBACService
from ..services.authz import authz_service
from ..services.permission.rbac_service import (
    ADMIN_PERMISSION_ACTION,
    ADMIN_PERMISSION_RESOURCE,
)
from .token_blacklist_guard import TokenBlacklistGuard

logger = logging.getLogger(__name__)


_token_blacklist_guard = TokenBlacklistGuard(is_production=lambda: is_production())
_token_blacklist_circuit = _token_blacklist_guard.circuit


def _is_token_blacklisted(
    jti: str | None,
    user_id: str | None = None,
    session_id: str | None = None,
    token_iat: int | float | None = None,
) -> bool:
    """检查 token 是否在黑名单中（熔断/异常统一 fail-closed）。"""
    return _token_blacklist_guard.is_token_blacklisted(
        jti=jti,
        user_id=user_id,
        session_id=session_id,
        token_iat=token_iat,
    )


def _get_jwt_settings() -> tuple[str, str, str, str]:
    return (
        settings.SECRET_KEY,
        getattr(settings, "ALGORITHM", "HS256"),
        settings.JWT_AUDIENCE,
        settings.JWT_ISSUER,
    )


def _validate_jwt_token(token: str) -> TokenData:
    """
    共享的JWT验证逻辑

    Args:
        token: JWT token string

    Returns:
        TokenData: 解析并验证后的token数据

    Raises:
        HTTPException: 如果token无效或验证失败
    """
    credentials_exception = unauthorized("无效的认证凭据")

    try:
        secret_key, algorithm, audience, issuer = _get_jwt_settings()
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
            audience=audience,
            issuer=issuer,
        )

        user_id: str | None = payload.get("sub")
        username: str | None = payload.get("username")
        exp: int | None = payload.get("exp")
        iat: int | None = payload.get("iat")
        jti: str | None = payload.get("jti")  # JWT ID for token tracking

        # 验证必需字段
        if user_id is None or username is None:
            logger.warning(
                f"JWT token missing required fields: sub={user_id}, username={username}"
            )
            raise credentials_exception

        # 验证过期时间（虽然jwt.decode已经验证，但双重检查更安全）
        if exp is None:
            logger.warning("JWT token missing expiration time")
            raise credentials_exception

        # 验证签发时间
        if iat is None:
            logger.warning("JWT token missing issued at time")
            raise credentials_exception

        # 验证token是否在黑名单中（如果实现了token黑名单）
        if _is_token_blacklisted(
            jti=jti, user_id=user_id, session_id=None, token_iat=iat
        ):
            logger.warning(f"JWT token {jti} is blacklisted")
            raise unauthorized("Token已失效")

        # 使用标准的TokenData Pydantic模型
        try:
            token_data = TokenData(
                sub=user_id,
                username=username,
                exp=payload.get("exp") if payload else None,
            )
        except Exception as e:
            # 如果TokenData验证失败，记录错误并抛出认证异常
            logger.error(f"TokenData validation failed: {e}")
            raise credentials_exception

    except BaseBusinessError:
        raise
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise credentials_exception
    except Exception as e:
        logger.exception("Unexpected JWT validation error: %s", e)
        raise credentials_exception

    return token_data


async def get_current_user(
    auth_token: str | None = Cookie(None, alias=cookie_manager.cookie_name),
    db: AsyncSession = Depends(get_async_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Cookie-only authentication. Tokens are read from httpOnly cookies.
    """
    credentials_exception = unauthorized("无效的认证凭据")

    token = auth_token
    if token:
        logger.debug("Authenticating using httpOnly cookie")

    # No token found in cookie
    if not token:
        raise credentials_exception

    # 使用共享的JWT验证逻辑
    try:
        token_data = _validate_jwt_token(token)
    except Exception:
        raise credentials_exception

    # Get user from database
    user_stmt = select(User).where(User.id == token_data.sub)
    user = (await db.execute(user_stmt)).scalars().first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise unauthorized("用户账户已被禁用")

    if user.is_locked_now():
        raise unauthorized("用户账户已被锁定，请稍后再试")

    logger.debug(f"Successfully authenticated user {user.username}")
    return user


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
    token = auth_token
    if token:
        logger.debug("Authenticating using httpOnly cookie")

    # No token found in either cookie or header
    if not token:
        raise unauthorized("Not authenticated")

    # 使用共享的JWT验证逻辑
    try:
        token_data = _validate_jwt_token(token)
    except Exception:
        raise unauthorized("Invalid token")

    # Get user from database
    user_stmt = select(User).where(User.id == token_data.sub)
    user = (await db.execute(user_stmt)).scalars().first()
    if user is None:
        raise unauthorized("Invalid authentication credentials")

    # Check if user is active
    if not user.is_active:
        raise unauthorized("User account is disabled")

    # Check if user is locked
    if user.is_locked_now():
        raise unauthorized("User account is locked, please try again later")

    logger.debug(
        f"Successfully authenticated user {user.username} via cookie-based auth"
    )
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise bad_request("用户账户未激活")
    return current_user


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
    resolved_token = auth_token

    if not resolved_token:
        return None

    try:
        token_data = _validate_jwt_token(resolved_token)
    except Exception:
        return None

    user_stmt = select(User).where(User.id == token_data.sub)
    user = (await db.execute(user_stmt)).scalars().first()
    if user and user.is_active and not user.is_locked_now():
        return user

    return None


class PermissionChecker:
    """权限检查器"""

    def __init__(self, required_permissions: list[str]):
        self.required_permissions = required_permissions

    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db),
    ) -> User:
        """检查用户权限"""
        if not await self._has_permission(current_user, db):
            raise forbidden("权限不足")
        return current_user

    async def _has_permission(self, user: User, db: AsyncSession) -> bool:
        """检查用户是否有所需权限"""
        rbac_service = RBACService(db)
        for permission_code in self.required_permissions:
            if ":" in permission_code:
                resource, action = permission_code.split(":", 1)
            else:
                resource, action = "system", permission_code
            if (
                resource == ADMIN_PERMISSION_RESOURCE
                and action == ADMIN_PERMISSION_ACTION
            ):
                if await rbac_service.is_admin(user.id):
                    return True
                continue
            if await rbac_service.check_user_permission(user.id, resource, action):
                return True
        return False


def require_permissions(required_permissions: list[str]) -> PermissionChecker:
    """权限装饰器工厂函数"""
    return PermissionChecker(required_permissions)


ResourceIdResolver = Callable[[Request], str | None | Awaitable[str | None]]
ResourceContextResolver = Callable[
    [Request],
    Mapping[str, Any] | dict[str, Any] | None | Awaitable[Mapping[str, Any] | dict[str, Any] | None],
]


@dataclass(frozen=True)
class AuthzContext:
    """ABAC 鉴权上下文。"""

    current_user: User
    action: str
    resource_type: str
    resource_id: str | None
    resource_context: dict[str, Any]
    allowed: bool
    reason_code: str | None


class AuthzPermissionChecker:
    """统一 ABAC 鉴权依赖。"""

    def __init__(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str | ResourceIdResolver | None = None,
        resource_context: Mapping[str, Any] | ResourceContextResolver | None = None,
        deny_as_not_found: bool = False,
    ) -> None:
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.resource_context = resource_context
        self.deny_as_not_found = deny_as_not_found

    async def __call__(
        self,
        request: Request,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db),
    ) -> AuthzContext:
        resolved_resource_id = await self._resolve_resource_id(request)
        resolved_resource_context = await self._resolve_resource_context(
            request=request,
            db=db,
            resource_id=resolved_resource_id,
        )
        resolved_resource_context = await self._inject_collection_scope_hint_if_needed(
            db=db,
            user_id=str(current_user.id),
            resource_id=resolved_resource_id,
            resource_context=resolved_resource_context,
        )

        try:
            decision = await authz_service.check_access(
                db,
                user_id=str(current_user.id),
                resource_type=self.resource_type,
                action=self.action,
                resource_id=resolved_resource_id,
                resource=resolved_resource_context,
            )
        except Exception:
            logger.exception(
                "ABAC check failed: user=%s resource=%s action=%s id=%s",
                getattr(current_user, "id", None),
                self.resource_type,
                self.action,
                resolved_resource_id,
            )
            raise forbidden("权限校验失败")

        if not decision.allowed:
            if self.deny_as_not_found:
                raise not_found(
                    resource_type=self.resource_type,
                    resource_id=resolved_resource_id,
                )
            raise forbidden("权限不足")

        return AuthzContext(
            current_user=current_user,
            action=self.action,
            resource_type=self.resource_type,
            resource_id=resolved_resource_id,
            resource_context=resolved_resource_context,
            allowed=True,
            reason_code=decision.reason_code,
        )

    async def _resolve_resource_id(self, request: Request) -> str | None:
        raw_value = await self._resolve_dynamic_value(self.resource_id, request)
        normalized = self._normalize_optional_str(raw_value)
        if normalized is None:
            return None
        return self._resolve_path_template(normalized, request)

    async def _resolve_resource_context(
        self,
        *,
        request: Request,
        db: AsyncSession,
        resource_id: str | None,
    ) -> dict[str, Any]:
        raw_context = await self._resolve_dynamic_value(self.resource_context, request)
        normalized_context = self._normalize_context_mapping(raw_context)
        request_context = await self._extract_request_context(request)
        trusted_context = await self._resolve_trusted_resource_context(
            db=db,
            resource_id=resource_id,
        )
        return {**request_context, **normalized_context, **trusted_context}

    async def _inject_collection_scope_hint_if_needed(
        self,
        *,
        db: AsyncSession,
        user_id: str,
        resource_id: str | None,
        resource_context: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._should_infer_collection_scope_hint(
            resource_id=resource_id,
            resource_context=resource_context,
        ):
            return resource_context

        inferred_scope_hint = await self._build_subject_scope_hint(
            db=db,
            user_id=user_id,
        )
        if len(inferred_scope_hint) == 0:
            return resource_context

        merged_context = dict(resource_context)
        for key, value in inferred_scope_hint.items():
            merged_context.setdefault(key, value)
        return merged_context

    def _should_infer_collection_scope_hint(
        self,
        *,
        resource_id: str | None,
        resource_context: Mapping[str, Any],
    ) -> bool:
        if self.action not in {"read", "list"}:
            return False
        if self._normalize_optional_str(resource_id) is not None:
            return False

        has_owner_scope = (
            self._normalize_optional_str(resource_context.get("owner_party_id"))
            is not None
        )
        has_manager_scope = (
            self._normalize_optional_str(resource_context.get("manager_party_id"))
            is not None
        )
        has_party_scope = (
            self._normalize_optional_str(resource_context.get("party_id")) is not None
        )
        return not (has_owner_scope and has_manager_scope and has_party_scope)

    async def _build_subject_scope_hint(
        self,
        *,
        db: AsyncSession,
        user_id: str,
    ) -> dict[str, Any]:
        try:
            subject_context = await authz_service.context_builder.build_subject_context(
                db,
                user_id=user_id,
            )
        except Exception:
            logger.exception(
                "Failed to infer collection scope hint for user %s",
                user_id,
            )
            return {}

        owner_party_ids = self._normalize_identifier_sequence(
            getattr(subject_context, "owner_party_ids", [])
        )
        manager_party_ids = self._normalize_identifier_sequence(
            getattr(subject_context, "manager_party_ids", [])
        )

        scope_hint: dict[str, Any] = {}
        if len(owner_party_ids) > 0:
            scope_hint["owner_party_ids"] = owner_party_ids
            scope_hint["owner_party_id"] = owner_party_ids[0]
        if len(manager_party_ids) > 0:
            scope_hint["manager_party_ids"] = manager_party_ids
            scope_hint["manager_party_id"] = manager_party_ids[0]

        party_candidates = [*owner_party_ids, *manager_party_ids]
        if len(party_candidates) > 0:
            scope_hint["party_id"] = party_candidates[0]
        return scope_hint

    async def _resolve_trusted_resource_context(
        self,
        *,
        db: AsyncSession,
        resource_id: str | None,
    ) -> dict[str, Any]:
        normalized_resource_id = self._normalize_optional_str(resource_id)
        if normalized_resource_id is None:
            return {}
        if not self._is_queryable_session(db):
            return {}

        if self.resource_type == "asset":
            return await self._load_asset_scope_context(
                db=db,
                asset_id=normalized_resource_id,
            )
        if self.resource_type == "project":
            return await self._load_project_scope_context(
                db=db,
                project_id=normalized_resource_id,
            )
        if self.resource_type == "rent_contract":
            return await self._load_rent_contract_scope_context(
                db=db,
                contract_id=normalized_resource_id,
            )
        if self.resource_type == "ownership":
            return await self._load_ownership_scope_context(
                db=db,
                ownership_id=normalized_resource_id,
            )
        if self.resource_type == "party":
            return await self._load_party_scope_context(
                db=db,
                party_id=normalized_resource_id,
            )
        if self.resource_type == "role":
            return await self._load_role_scope_context(
                db=db,
                role_id=normalized_resource_id,
            )
        if self.resource_type == "user":
            return await self._load_user_scope_context(
                db=db,
                user_id=normalized_resource_id,
            )
        if self.resource_type == "task":
            return await self._load_task_scope_context(
                db=db,
                task_id=normalized_resource_id,
            )
        if self.resource_type == "organization":
            return await self._load_organization_scope_context(
                db=db,
                organization_id=normalized_resource_id,
            )
        if self.resource_type == "property_certificate":
            return await self._load_property_certificate_scope_context(
                db=db,
                certificate_id=normalized_resource_id,
            )
        return {}

    def _is_queryable_session(self, db: Any) -> bool:
        if isinstance(db, AsyncSession):
            return True
        execute = getattr(db, "execute", None)
        if execute is None:
            return False
        return inspect.iscoroutinefunction(execute)

    async def _load_asset_scope_context(
        self,
        *,
        db: AsyncSession,
        asset_id: str,
    ) -> dict[str, Any]:
        from ..models.asset import Asset

        stmt = select(
            Asset.id.label("asset_id"),
            Asset.owner_party_id,
            Asset.manager_party_id,
            Asset.organization_id,
            Asset.ownership_id,
            Asset.project_id,
        ).where(Asset.id == asset_id)
        row = (await db.execute(stmt)).mappings().one_or_none()
        if row is None:
            return {}

        normalized_owner_party_id = self._normalize_optional_str(row.get("owner_party_id"))
        normalized_manager_party_id = self._normalize_optional_str(
            row.get("manager_party_id")
        )
        normalized_organization_id = self._normalize_optional_str(
            row.get("organization_id")
        )
        normalized_ownership_id = self._normalize_optional_str(row.get("ownership_id"))
        if normalized_owner_party_id is None and normalized_ownership_id is not None:
            normalized_owner_party_id = await self._resolve_ownership_party_id(
                db=db,
                ownership_id=normalized_ownership_id,
                ownership_code=None,
                ownership_name=None,
            )
            if normalized_owner_party_id is None:
                normalized_owner_party_id = normalized_ownership_id
        if (
            normalized_manager_party_id is None
            and normalized_organization_id is not None
        ):
            normalized_manager_party_id = await self._resolve_organization_party_id(
                db=db,
                organization_id=normalized_organization_id,
                organization_code=None,
                organization_name=None,
            )
            if normalized_manager_party_id is None:
                normalized_manager_party_id = normalized_organization_id
        scoped_party_id = normalized_owner_party_id or normalized_manager_party_id

        return self._normalize_scope_context(
            {
                "asset_id": row.get("asset_id"),
                "owner_party_id": normalized_owner_party_id,
                "manager_party_id": normalized_manager_party_id,
                "party_id": scoped_party_id,
                "organization_id": normalized_organization_id,
                "ownership_id": normalized_ownership_id,
                "project_id": row.get("project_id"),
            }
        )

    async def _load_project_scope_context(
        self,
        *,
        db: AsyncSession,
        project_id: str,
    ) -> dict[str, Any]:
        from ..models.project import Project

        stmt = select(
            Project.id.label("project_id"),
            Project.manager_party_id,
            Project.organization_id,
        ).where(Project.id == project_id)
        row = (await db.execute(stmt)).mappings().one_or_none()
        if row is None:
            return {}

        normalized_manager_party_id = self._normalize_optional_str(
            row.get("manager_party_id")
        )
        normalized_organization_id = self._normalize_optional_str(
            row.get("organization_id")
        )
        if (
            normalized_manager_party_id is None
            and normalized_organization_id is not None
        ):
            normalized_manager_party_id = await self._resolve_organization_party_id(
                db=db,
                organization_id=normalized_organization_id,
                organization_code=None,
                organization_name=None,
            )
            if normalized_manager_party_id is None:
                normalized_manager_party_id = normalized_organization_id

        return self._normalize_scope_context(
            {
                "project_id": row.get("project_id"),
                "manager_party_id": normalized_manager_party_id,
                "party_id": normalized_manager_party_id,
                "organization_id": normalized_organization_id,
            }
        )

    async def _load_rent_contract_scope_context(
        self,
        *,
        db: AsyncSession,
        contract_id: str,
    ) -> dict[str, Any]:
        from ..models.rent_contract import RentContract

        stmt = select(
            RentContract.id.label("contract_id"),
            RentContract.owner_party_id,
            RentContract.manager_party_id,
            RentContract.tenant_party_id,
            RentContract.ownership_id,
        ).where(RentContract.id == contract_id)
        row = (await db.execute(stmt)).mappings().one_or_none()
        if row is None:
            return {}

        normalized_owner_party_id = self._normalize_optional_str(row.get("owner_party_id"))
        normalized_manager_party_id = self._normalize_optional_str(
            row.get("manager_party_id")
        )
        normalized_ownership_id = self._normalize_optional_str(row.get("ownership_id"))
        if normalized_owner_party_id is None and normalized_ownership_id is not None:
            normalized_owner_party_id = await self._resolve_ownership_party_id(
                db=db,
                ownership_id=normalized_ownership_id,
                ownership_code=None,
                ownership_name=None,
            )
            if normalized_owner_party_id is None:
                normalized_owner_party_id = normalized_ownership_id

        return self._normalize_scope_context(
            {
                "contract_id": row.get("contract_id"),
                "owner_party_id": normalized_owner_party_id,
                "manager_party_id": normalized_manager_party_id,
                "party_id": normalized_owner_party_id or normalized_manager_party_id,
                "tenant_party_id": row.get("tenant_party_id"),
                "ownership_id": normalized_ownership_id,
            }
        )

    async def _load_ownership_scope_context(
        self,
        *,
        db: AsyncSession,
        ownership_id: str,
    ) -> dict[str, Any]:
        from ..models.ownership import Ownership

        stmt = select(
            Ownership.id.label("ownership_id"),
            Ownership.code.label("ownership_code"),
            Ownership.name.label("ownership_name"),
        ).where(Ownership.id == ownership_id)
        row = (await db.execute(stmt)).mappings().one_or_none()
        if row is None:
            return {}

        normalized_ownership_id = self._normalize_optional_str(row.get("ownership_id"))
        if normalized_ownership_id is None:
            return {}

        scoped_party_id = await self._resolve_ownership_party_id(
            db=db,
            ownership_id=normalized_ownership_id,
            ownership_code=row.get("ownership_code"),
            ownership_name=row.get("ownership_name"),
        )
        if scoped_party_id is None:
            # Legacy fallback: keep ownership-id based scoping fail-closed.
            scoped_party_id = normalized_ownership_id

        return self._normalize_scope_context(
            {
                "ownership_id": normalized_ownership_id,
                "party_id": scoped_party_id,
                "owner_party_id": scoped_party_id,
                "manager_party_id": scoped_party_id,
            }
        )

    async def _load_party_scope_context(
        self,
        *,
        db: AsyncSession,
        party_id: str,
    ) -> dict[str, Any]:
        from ..models.party import Party

        stmt = select(Party.id.label("party_id")).where(Party.id == party_id)
        row = (await db.execute(stmt)).mappings().one_or_none()
        if row is None:
            return {}
        return self._normalize_scope_context({"party_id": row.get("party_id")})

    async def _load_role_scope_context(
        self,
        *,
        db: AsyncSession,
        role_id: str,
    ) -> dict[str, Any]:
        from ..models.rbac import Role

        stmt = select(
            Role.id.label("role_id"),
            Role.party_id,
            Role.organization_id,
        ).where(Role.id == role_id)
        row = (await db.execute(stmt)).mappings().one_or_none()
        if row is None:
            return {}

        normalized_role_id = self._normalize_optional_str(row.get("role_id"))
        if normalized_role_id is None:
            return {}

        scoped_party_id = self._normalize_optional_str(row.get("party_id"))
        normalized_organization_id = self._normalize_optional_str(row.get("organization_id"))
        if scoped_party_id is None and normalized_organization_id is not None:
            scoped_party_id = await self._resolve_organization_party_id(
                db=db,
                organization_id=normalized_organization_id,
                organization_code=None,
                organization_name=None,
            )
            if scoped_party_id is None:
                scoped_party_id = normalized_organization_id
        if scoped_party_id is None:
            scoped_party_id = self._build_unscoped_party_id(
                resource_type="role",
                resource_id=normalized_role_id,
            )

        return self._normalize_scope_context(
            {
                "role_id": normalized_role_id,
                "organization_id": normalized_organization_id,
                "party_id": scoped_party_id,
                "owner_party_id": scoped_party_id,
                "manager_party_id": scoped_party_id,
            }
        )

    async def _load_user_scope_context(
        self,
        *,
        db: AsyncSession,
        user_id: str,
    ) -> dict[str, Any]:
        from ..models.auth import User
        from ..models.user_party_binding import UserPartyBinding

        user_stmt = select(
            User.id.label("user_id"),
            User.default_organization_id,
        ).where(User.id == user_id)
        user_row = (await db.execute(user_stmt)).mappings().one_or_none()
        if user_row is None:
            return {}

        normalized_user_id = self._normalize_optional_str(user_row.get("user_id"))
        if normalized_user_id is None:
            return {}

        now = datetime.now(UTC).replace(tzinfo=None)
        binding_stmt = (
            select(UserPartyBinding.party_id.label("party_id"))
            .where(UserPartyBinding.user_id == normalized_user_id)
            .where(UserPartyBinding.valid_from <= now)
            .where(
                (UserPartyBinding.valid_to.is_(None))
                | (UserPartyBinding.valid_to >= now)
            )
            .order_by(
                UserPartyBinding.is_primary.desc(),
                UserPartyBinding.valid_from.desc(),
                UserPartyBinding.created_at.desc(),
            )
            .limit(1)
        )
        binding_row = (await db.execute(binding_stmt)).mappings().one_or_none()

        scoped_party_id = self._normalize_optional_str(
            binding_row.get("party_id") if binding_row is not None else None
        )
        normalized_organization_id = self._normalize_optional_str(
            user_row.get("default_organization_id")
        )
        if scoped_party_id is None and normalized_organization_id is not None:
            scoped_party_id = await self._resolve_organization_party_id(
                db=db,
                organization_id=normalized_organization_id,
                organization_code=None,
                organization_name=None,
            )
            if scoped_party_id is None:
                scoped_party_id = normalized_organization_id
        if scoped_party_id is None:
            scoped_party_id = self._build_unscoped_party_id(
                resource_type="user",
                resource_id=normalized_user_id,
            )

        return self._normalize_scope_context(
            {
                "user_id": normalized_user_id,
                "organization_id": normalized_organization_id,
                "party_id": scoped_party_id,
                "owner_party_id": scoped_party_id,
                "manager_party_id": scoped_party_id,
            }
        )

    async def _load_task_scope_context(
        self,
        *,
        db: AsyncSession,
        task_id: str,
    ) -> dict[str, Any]:
        from ..models.task import AsyncTask

        task_stmt = select(
            AsyncTask.id.label("task_id"),
            AsyncTask.user_id,
        ).where(AsyncTask.id == task_id)
        task_row = (await db.execute(task_stmt)).mappings().one_or_none()
        if task_row is None:
            return {}

        normalized_task_id = self._normalize_optional_str(task_row.get("task_id"))
        if normalized_task_id is None:
            return {}

        normalized_user_id = self._normalize_optional_str(task_row.get("user_id"))
        user_scope: dict[str, Any] = {}
        if normalized_user_id is not None:
            user_scope = await self._load_user_scope_context(
                db=db,
                user_id=normalized_user_id,
            )

        scoped_party_id = self._normalize_optional_str(user_scope.get("party_id"))
        if scoped_party_id is None:
            scoped_party_id = self._build_unscoped_party_id(
                resource_type="task",
                resource_id=normalized_task_id,
            )

        owner_party_id = self._normalize_optional_str(user_scope.get("owner_party_id"))
        manager_party_id = self._normalize_optional_str(
            user_scope.get("manager_party_id")
        )
        organization_id = self._normalize_optional_str(
            user_scope.get("organization_id")
        )

        return self._normalize_scope_context(
            {
                "task_id": normalized_task_id,
                "user_id": normalized_user_id,
                "organization_id": organization_id,
                "party_id": scoped_party_id,
                "owner_party_id": owner_party_id or scoped_party_id,
                "manager_party_id": manager_party_id or scoped_party_id,
            }
        )

    @staticmethod
    def _build_unscoped_party_id(*, resource_type: str, resource_id: str) -> str:
        return f"__unscoped__:{resource_type}:{resource_id}"

    async def _load_organization_scope_context(
        self,
        *,
        db: AsyncSession,
        organization_id: str,
    ) -> dict[str, Any]:
        from ..models.organization import Organization

        stmt = select(
            Organization.id.label("organization_id"),
            Organization.code.label("organization_code"),
            Organization.name.label("organization_name"),
        ).where(Organization.id == organization_id)
        row = (await db.execute(stmt)).mappings().one_or_none()
        if row is None:
            return {}

        normalized_org_id = self._normalize_optional_str(row.get("organization_id"))
        if normalized_org_id is None:
            return {}

        scoped_party_id = await self._resolve_organization_party_id(
            db=db,
            organization_id=normalized_org_id,
            organization_code=row.get("organization_code"),
            organization_name=row.get("organization_name"),
        )
        if scoped_party_id is None:
            # Legacy fallback: keep organization-id based scoping fail-closed.
            scoped_party_id = normalized_org_id

        return self._normalize_scope_context(
            {
                "organization_id": normalized_org_id,
                "party_id": scoped_party_id,
                "owner_party_id": scoped_party_id,
                "manager_party_id": scoped_party_id,
            }
        )

    async def _resolve_organization_party_id(
        self,
        *,
        db: AsyncSession,
        organization_id: str,
        organization_code: Any,
        organization_name: Any,
    ) -> str | None:
        from ..models.party import Party, PartyType

        lookup_conditions = [
            Party.id == organization_id,
            Party.external_ref == organization_id,
        ]

        normalized_code = self._normalize_optional_str(organization_code)
        if normalized_code is not None:
            lookup_conditions.append(Party.code == normalized_code)

        normalized_name = self._normalize_optional_str(organization_name)
        if normalized_name is not None:
            lookup_conditions.append(Party.name == normalized_name)

        for condition in lookup_conditions:
            stmt = (
                select(Party.id.label("party_id"))
                .where(
                    Party.party_type == PartyType.ORGANIZATION.value,
                    condition,
                )
                .order_by(Party.id)
                .limit(1)
            )
            row = (await db.execute(stmt)).mappings().one_or_none()
            party_id = self._normalize_optional_str(
                row.get("party_id") if row is not None else None
            )
            if party_id is not None:
                return party_id
        return None

    async def _resolve_ownership_party_id(
        self,
        *,
        db: AsyncSession,
        ownership_id: str,
        ownership_code: Any,
        ownership_name: Any,
    ) -> str | None:
        from ..models.party import Party, PartyType

        lookup_conditions = [
            Party.id == ownership_id,
            Party.external_ref == ownership_id,
        ]

        normalized_code = self._normalize_optional_str(ownership_code)
        if normalized_code is not None:
            lookup_conditions.append(Party.code == normalized_code)

        normalized_name = self._normalize_optional_str(ownership_name)
        if normalized_name is not None:
            lookup_conditions.append(Party.name == normalized_name)

        for condition in lookup_conditions:
            stmt = (
                select(Party.id.label("party_id"))
                .where(
                    Party.party_type == PartyType.LEGAL_ENTITY.value,
                    condition,
                )
                .order_by(Party.id)
                .limit(1)
            )
            row = (await db.execute(stmt)).mappings().one_or_none()
            party_id = self._normalize_optional_str(
                row.get("party_id") if row is not None else None
            )
            if party_id is not None:
                return party_id
        return None

    async def _load_property_certificate_scope_context(
        self,
        *,
        db: AsyncSession,
        certificate_id: str,
    ) -> dict[str, Any]:
        from ..models.property_certificate import PropertyCertificate

        stmt = select(
            PropertyCertificate.id.label("certificate_id"),
            PropertyCertificate.organization_id,
        ).where(PropertyCertificate.id == certificate_id)
        row = (await db.execute(stmt)).mappings().one_or_none()
        if row is None:
            return {}

        normalized_organization_id = self._normalize_optional_str(row.get("organization_id"))
        scoped_party_id: str | None = None
        if normalized_organization_id is not None:
            scoped_party_id = await self._resolve_organization_party_id(
                db=db,
                organization_id=normalized_organization_id,
                organization_code=None,
                organization_name=None,
            )
            if scoped_party_id is None:
                scoped_party_id = normalized_organization_id

        return self._normalize_scope_context(
            {
                "certificate_id": row.get("certificate_id"),
                "organization_id": normalized_organization_id,
                "party_id": scoped_party_id,
                "owner_party_id": scoped_party_id,
                "manager_party_id": scoped_party_id,
            }
        )

    async def _resolve_dynamic_value(
        self,
        source: (
            str
            | Mapping[str, Any]
            | ResourceIdResolver
            | ResourceContextResolver
            | None
        ),
        request: Request,
    ) -> Any:
        if not callable(source):
            return source

        resolved = source(request)
        if inspect.isawaitable(resolved):
            return await resolved
        return resolved

    @staticmethod
    def _normalize_optional_str(value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        if normalized == "":
            return None
        return normalized

    def _resolve_path_template(self, value: str, request: Request) -> str | None:
        if not (value.startswith("{") and value.endswith("}")):
            return value

        param_name = value[1:-1].strip()
        if param_name == "":
            return None
        return self._normalize_optional_str(request.path_params.get(param_name))

    @classmethod
    def _normalize_context_mapping(cls, value: Any) -> dict[str, Any]:
        if value is None or not isinstance(value, Mapping):
            return {}

        normalized: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = cls._normalize_optional_str(key)
            if normalized_key is None:
                continue
            normalized[normalized_key] = item
        return normalized

    @classmethod
    def _normalize_scope_context(cls, value: Mapping[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = cls._normalize_optional_str(key)
            if normalized_key is None:
                continue
            normalized_value = cls._normalize_optional_str(item)
            if normalized_value is None:
                continue
            normalized[normalized_key] = normalized_value
        return normalized

    @classmethod
    def _normalize_identifier_sequence(cls, values: Any) -> list[str]:
        if not isinstance(values, list):
            return []

        normalized_values: list[str] = []
        for value in values:
            normalized = cls._normalize_optional_str(value)
            if normalized is None:
                continue
            normalized_values.append(normalized)
        return normalized_values

    async def _extract_request_context(self, request: Request) -> dict[str, Any]:
        context: dict[str, Any] = {}
        for key, value in request.path_params.items():
            if not key.endswith("_id"):
                continue
            normalized = self._normalize_optional_str(value)
            if normalized is None:
                continue
            context[key] = normalized
        return context


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
    )


class OrganizationPermissionChecker:  # DEPRECATED
    """组织权限检查器"""

    def __init__(self, organization_id: str | None = None):
        self.organization_id = organization_id

    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db),
    ) -> User:
        """检查用户是否有访问指定组织的权限"""
        if not await self._can_access_organization(current_user, db):
            raise forbidden("无权访问该组织的数据")
        return current_user

    async def _can_access_organization(self, user: User, db: AsyncSession) -> bool:
        """检查用户是否可以访问组织"""
        rbac_service = RBACService(db)
        if await rbac_service.is_admin(user.id):
            return True

        # 用户可以访问自己的默认组织
        if user.default_organization_id == self.organization_id:
            return True

        # 当未指定目标组织时，默认组织视为其组织访问范围
        if self.organization_id is None:
            return user.default_organization_id is not None

        return False


def require_organization_access(
    organization_id: str | None = None,
) -> OrganizationPermissionChecker:  # DEPRECATED
    """组织权限装饰器工厂函数"""
    return OrganizationPermissionChecker(organization_id)  # DEPRECATED


class AuditLogger:
    """审计日志记录器"""

    def __init__(self, action: str, resource_type: str | None = None):
        self.action = action
        self.resource_type = resource_type

    async def __call__(
        self,
        request: Request,
        current_user: User | None = Depends(get_optional_current_user),
        db: AsyncSession = Depends(get_async_db),
    ) -> User | None:
        """记录审计日志"""
        if not current_user:
            return current_user

        try:
            from ..middleware.security_middleware import get_client_ip

            ip_address = get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")
            request_params = str(request.query_params) if request.query_params else None

            await self.log_action(
                db=db,
                user=current_user,
                api_endpoint=request.url.path,
                http_method=request.method,
                request_params=request_params,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception as e:
            logger.warning(f"审计日志记录失败: {e}")
        return current_user

    async def log_action(
        self,
        db: AsyncSession,
        user: User,
        resource_id: str | None = None,
        resource_name: str | None = None,
        api_endpoint: str | None = None,
        http_method: str | None = None,
        request_params: str | None = None,
        request_body: str | None = None,
        response_status: int | None = None,
        response_message: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> None:
        audit_crud = AuditLogCRUD()
        await audit_crud.create_async(
            db=db,
            user_id=user.id,
            action=self.action,
            resource_type=self.resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            api_endpoint=api_endpoint,
            http_method=http_method,
            request_params=request_params,
            request_body=request_body,
            response_status=response_status,
            response_message=response_message,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
        )


def audit_action(action: str, resource_type: str | None = None) -> AuditLogger:
    """审计装饰器工厂函数"""
    return AuditLogger(action, resource_type)


# 安全配置
class SecurityConfig:
    """安全配置"""

    # 密码策略
    MIN_PASSWORD_LENGTH = settings.MIN_PASSWORD_LENGTH
    MAX_FAILED_ATTEMPTS = settings.MAX_FAILED_ATTEMPTS
    LOCKOUT_DURATION_MINUTES = settings.LOCKOUT_DURATION

    # JWT配置
    ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

    # 会话配置
    MAX_CONCURRENT_SESSIONS = settings.MAX_CONCURRENT_SESSIONS
    SESSION_EXPIRE_DAYS = settings.SESSION_EXPIRE_DAYS

    # 审计配置
    AUDIT_LOG_RETENTION_DAYS = settings.AUDIT_LOG_RETENTION_DAYS

    @classmethod
    def get_password_policy(cls) -> dict[str, Any]:
        """获取密码策略"""
        return {
            "min_length": cls.MIN_PASSWORD_LENGTH,
            "max_failed_attempts": cls.MAX_FAILED_ATTEMPTS,
            "lockout_duration_minutes": cls.LOCKOUT_DURATION_MINUTES,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_digits": True,
            "require_special_chars": True,
        }

    @classmethod
    def get_token_config(cls) -> dict[str, Any]:
        """获取令牌配置"""
        return {
            "access_token_expire_minutes": cls.ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_token_expire_days": cls.REFRESH_TOKEN_EXPIRE_DAYS,
            "algorithm": getattr(settings, "ALGORITHM", "HS256"),
            "max_concurrent_sessions": cls.MAX_CONCURRENT_SESSIONS,
            "session_expire_days": cls.SESSION_EXPIRE_DAYS,
        }


# ==================== RBAC权限检查器 ====================


class RBACPermissionChecker:
    """RBAC权限检查器"""

    def __init__(self, resource: str, action: str, resource_id: str | None = None):
        self.resource = resource
        self.action = action
        self.resource_id = resource_id

    async def __call__(
        self,
        current_user: User | None = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db),
    ) -> User | None:
        """检查用户权限"""

        # 如果没有用户（未认证），抛出认证异常
        if current_user is None:
            raise unauthorized("需要认证")

        rbac_service = RBACService(db)
        if await rbac_service.is_admin(current_user.id):
            return current_user

        # 使用RBAC服务检查权限
        permission_request = PermissionCheckRequest(
            resource=self.resource,
            action=self.action,
            resource_id=self.resource_id,
            context=None,
        )

        permission_result = await rbac_service.check_permission(
            current_user.id, permission_request
        )

        if not permission_result.has_permission:
            raise forbidden(f"权限不足，需要 {self.resource}:{self.action} 权限")

        return current_user


def require_permission(
    resource: str, action: str, resource_id: str | None = None
) -> RBACPermissionChecker:
    """RBAC权限装饰器工厂函数"""
    return RBACPermissionChecker(resource, action, resource_id)


class ResourcePermissionChecker:  # DEPRECATED
    """资源权限检查器"""

    def __init__(self, resource_type: str, required_level: str = "read"):
        self.resource_type = resource_type
        self.required_level = required_level

    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db),
        resource_id: str | None = None,
    ) -> User:
        """检查用户资源权限"""
        rbac_service = RBACService(db)
        if await rbac_service.is_admin(current_user.id):
            return current_user

        # 检查是否有对应的资源权限
        from ..models.rbac import ResourcePermission  # DEPRECATED

        stmt = select(ResourcePermission).where(  # DEPRECATED
            and_(
                ResourcePermission.user_id == current_user.id,  # DEPRECATED
                ResourcePermission.resource_type == self.resource_type,  # DEPRECATED
                ResourcePermission.resource_id == resource_id,  # DEPRECATED
                ResourcePermission.is_active,  # DEPRECATED
            )
        )
        resource_permission = (await db.execute(stmt)).scalars().first()

        if not resource_permission:
            raise forbidden(f"无权访问此{self.resource_type}资源")

        # 检查权限级别
        level_actions = {
            "read": ["read"],
            "write": ["read", "write"],
            "delete": ["read", "write", "delete"],
            "admin": ["read", "write", "delete", "admin"],
        }

        # 简化处理：假设当前操作对应required_level
        if self.required_level not in level_actions:
            raise forbidden(f"无效的权限级别: {self.required_level}")

        return current_user


def require_resource_permission(
    resource_type: str, required_level: str = "read"
) -> ResourcePermissionChecker:  # DEPRECATED
    """资源权限装饰器工厂函数"""
    return ResourcePermissionChecker(resource_type, required_level)  # DEPRECATED


class RoleBasedAccessChecker:
    """基于角色的访问检查器"""

    def __init__(self, required_roles: list[str]):
        self.required_roles = required_roles

    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_async_db),
    ) -> User:
        """检查用户角色"""
        rbac_service = RBACService(db)
        if await rbac_service.is_admin(current_user.id):
            return current_user

        # 获取用户角色
        user_roles = await rbac_service.get_user_roles(current_user.id)

        user_role_names = [role.name for role in user_roles]

        # 检查是否有所需角色
        if not any(role_name in self.required_roles for role_name in user_role_names):
            raise forbidden(f"需要以下角色之一: {', '.join(self.required_roles)}")

        return current_user


def require_roles(required_roles: list[str]) -> RoleBasedAccessChecker:
    """角色权限装饰器工厂函数"""
    return RoleBasedAccessChecker(required_roles)


async def can_edit_contract(user: User, db: AsyncSession, contract_id: str) -> bool:
    """
    检查用户是否可以编辑合同

    规则:
    - 管理员可以编辑任何合同
    - 其他角色需要通过RBAC服务检查特定权限
    """
    rbac_service = RBACService(db)
    if await rbac_service.is_admin(user.id):
        return True

    # 使用RBAC服务进行细粒度权限检查
    try:
        permission_request = PermissionCheckRequest(
            resource="rent_contract",
            action="edit",
            resource_id=contract_id,
            context=None,
        )

        result = await rbac_service.check_permission(user.id, permission_request)
        return bool(result.has_permission)
    except Exception:
        # 如果RBAC检查失败，默认拒绝权限（安全优先）
        return False


async def get_user_rbac_permissions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    """获取用户RBAC权限信息"""
    rbac_service = RBACService(db)
    permissions_summary = await rbac_service.get_user_permissions_summary(
        current_user.id
    )
    is_admin = await rbac_service.is_admin(current_user.id)

    return {
        "is_admin": is_admin,
        "roles": [role.name for role in permissions_summary.roles],
        "permissions": (
            ["all"]
            if is_admin
            else dict(permissions_summary.effective_permissions.items())
        ),
    }
