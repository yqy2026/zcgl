"""Data-scope request context dependencies."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exception_handler import bad_request, forbidden
from ..database import get_async_db
from ..models.auth import User
from ..schemas.authz import BindingType, ScopeMode
from ..services.authz import authz_service as default_authz_service
from ..services.authz.resource_perspective_registry import (
    get_registered_perspectives,
    resolve_capability_perspectives,
    resource_requires_perspective,
)
from ..services.permission.rbac_service import RBACService
from .identity import get_current_active_user

AuthzServiceGetter = Callable[[], Any]
RBACServiceFactory = Callable[[AsyncSession], Any]


def _default_authz_service_getter() -> Any:
    return default_authz_service


def _default_rbac_service_factory(db: AsyncSession) -> RBACService:
    return RBACService(db)


@dataclass(frozen=True)
class DataScopeContext:
    """Resolved request data-scope context."""

    scope_mode: ScopeMode
    allowed_binding_types: list[BindingType]
    owner_party_ids: list[str]
    manager_party_ids: list[str]
    effective_party_ids: list[str]
    source: Literal["query", "auto"]


class DataScopeContextChecker:
    """Resolve and validate request data-scope context."""

    EXEMPT_PATH_PREFIXES: tuple[str, ...] = ("/api/v1/auth",)
    ANALYTICS_PATH_PREFIXES: tuple[str, ...] = (
        "/api/v1/analytics",
        "/api/v1/statistics",
    )

    def __init__(
        self,
        *,
        resource_type: str | None = None,
        authz_service_getter: AuthzServiceGetter | None = None,
        rbac_service_factory: RBACServiceFactory | None = None,
    ) -> None:
        self.resource_type = resource_type
        self.authz_service_getter = (
            authz_service_getter or _default_authz_service_getter
        )
        self.rbac_service_factory = (
            rbac_service_factory or _default_rbac_service_factory
        )

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

    async def resolve(
        self,
        *,
        request: Request,
        current_user: User,
        db: AsyncSession,
    ) -> DataScopeContext | None:
        request_path = request.url.path
        raw_view_mode = (
            self._normalize_view_mode(request)
            if any(
                request_path.startswith(prefix)
                for prefix in self.ANALYTICS_PATH_PREFIXES
            )
            else None
        )

        if self._is_exempt_path(request_path):
            if raw_view_mode is None:
                request.state.data_scope_context = None
                return None

        rbac_service = self.rbac_service_factory(db)
        authz_service = self.authz_service_getter()
        is_admin = bool(await rbac_service.is_admin(str(current_user.id)))
        subject_context = await authz_service.context_builder.build_subject_context(
            db,
            user_id=str(current_user.id),
        )
        subject_binding_types = (
            authz_service.context_builder.resolve_allowed_binding_types(subject_context)
        )

        source: Literal["query", "auto"] = "query"
        if raw_view_mode is None:
            raw_view_mode = self._resolve_auto_scope_mode(
                request_path=request_path,
                is_admin=is_admin,
                subject_binding_types=subject_binding_types,
            )
            source = "auto"

        if raw_view_mode not in {"owner", "manager", "all"}:
            raise bad_request("view_mode 仅支持 owner 或 manager")
        normalized_scope_mode = cast(ScopeMode, raw_view_mode)

        if self.resource_type is not None:
            if is_admin:
                allowed_binding_types: list[BindingType] = list(
                    get_registered_perspectives(self.resource_type)
                )
            else:
                allowed_binding_types = resolve_capability_perspectives(
                    self.resource_type,
                    subject_binding_types,
                )
                if (
                    resource_requires_perspective(self.resource_type)
                    and len(allowed_binding_types) == 0
                ):
                    raise forbidden("当前资源无可用视角")
        else:
            allowed_binding_types = (
                cast(list[BindingType], ["owner", "manager"])
                if is_admin
                else subject_binding_types
            )
        if (
            normalized_scope_mode != "all"
            and normalized_scope_mode not in allowed_binding_types
        ):
            raise forbidden("当前视角不可用")

        if is_admin:
            effective_party_ids = []
        elif normalized_scope_mode == "all":
            effective_party_ids = sorted(
                set(subject_context.owner_party_ids).union(
                    subject_context.manager_party_ids
                )
            )
        else:
            effective_party_ids = (
                authz_service.context_builder.resolve_effective_party_ids(
                    subject_context,
                    normalized_scope_mode,
                )
            )

        data_scope_context = DataScopeContext(
            scope_mode=normalized_scope_mode,
            allowed_binding_types=allowed_binding_types,
            owner_party_ids=list(subject_context.owner_party_ids),
            manager_party_ids=list(subject_context.manager_party_ids),
            effective_party_ids=effective_party_ids,
            source=source,
        )
        request.state.data_scope_context = data_scope_context
        return data_scope_context

    @classmethod
    def _is_exempt_path(cls, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in cls.EXEMPT_PATH_PREFIXES)

    @classmethod
    def _resolve_auto_scope_mode(
        cls,
        *,
        request_path: str,
        is_admin: bool,
        subject_binding_types: list[BindingType],
    ) -> ScopeMode:
        if is_admin:
            return "all"
        if any(
            request_path.startswith(prefix) for prefix in cls.ANALYTICS_PATH_PREFIXES
        ):
            if "owner" in subject_binding_types:
                return "owner"
            if "manager" in subject_binding_types:
                return "manager"
        return "all"

    @staticmethod
    def _normalize_optional_mode(value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip().lower()
        if normalized == "":
            return None
        return normalized

    @classmethod
    def _normalize_view_mode(cls, request: Request) -> str | None:
        return cls._normalize_optional_mode(request.query_params.get("view_mode"))


def require_data_scope_context(
    *, resource_type: str | None = None
) -> DataScopeContextChecker:
    """Data-scope request-contract dependency factory."""
    return DataScopeContextChecker(resource_type=resource_type)
