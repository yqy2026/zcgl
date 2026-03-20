"""
ABAC 鉴权依赖 — AuthzPermissionChecker 及其工厂函数 require_authz。
"""

import inspect
import logging
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exception_handler import forbidden, not_found
from ..database import get_async_db
from ..models.auth import User
from ..services.authz import authz_service
from ..utils.str import normalize_optional_str
from .auth_core import get_current_active_user
from .auth_scope_loaders import AuthzScopeLoaderMixin

logger = logging.getLogger(__name__)
VIEW_PERSPECTIVE_HEADER_NAME = "X-View-Perspective"
VIEW_PARTY_ID_HEADER_NAME = "X-View-Party-Id"


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

ResourceIdResolver = Callable[[Request], str | None | Awaitable[str | None]]
ResourceContextResolver = Callable[
    [Request],
    Mapping[str, Any]
    | dict[str, Any]
    | None
    | Awaitable[Mapping[str, Any] | dict[str, Any] | None],
]


# ---------------------------------------------------------------------------
# AuthzContext — the value injected into route handlers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# AuthzPermissionChecker
# ---------------------------------------------------------------------------


class AuthzPermissionChecker(AuthzScopeLoaderMixin):
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
            authz_stale = await self._should_mark_authz_stale(
                request=request,
                db=db,
                user_id=str(current_user.id),
            )
            if self.deny_as_not_found:
                raise not_found(
                    resource_type=self.resource_type,
                    resource_id=resolved_resource_id,
                    authz_stale=authz_stale,
                )
            raise forbidden("权限不足", authz_stale=authz_stale)

        return AuthzContext(
            current_user=current_user,
            action=self.action,
            resource_type=self.resource_type,
            resource_id=resolved_resource_id,
            resource_context=resolved_resource_context,
            allowed=True,
            reason_code=decision.reason_code,
        )

    # ------------------------------------------------------------------
    # Resource-ID / context resolution
    # ------------------------------------------------------------------

    async def _resolve_resource_id(self, request: Request) -> str | None:
        raw_value = await self._resolve_dynamic_value(self.resource_id, request)
        normalized = normalize_optional_str(raw_value)
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
        preliminary_context = {**request_context, **normalized_context}
        trusted_context = await self._resolve_trusted_resource_context(
            db=db,
            resource_id=resource_id,
            request_context=preliminary_context,
        )
        return {**preliminary_context, **trusted_context}

    # ------------------------------------------------------------------
    # Collection scope hint injection
    # ------------------------------------------------------------------

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
        if normalize_optional_str(resource_id) is not None:
            return False

        has_owner_scope = (
            normalize_optional_str(resource_context.get("owner_party_id")) is not None
        )
        has_manager_scope = (
            normalize_optional_str(resource_context.get("manager_party_id")) is not None
        )
        has_party_scope = (
            normalize_optional_str(resource_context.get("party_id")) is not None
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

    async def _should_mark_authz_stale(
        self,
        *,
        request: Request,
        db: AsyncSession,
        user_id: str,
    ) -> bool:
        selected_view = self._extract_selected_view(request)
        if selected_view is None:
            return False

        try:
            subject_context = await authz_service.context_builder.build_subject_context(
                db,
                user_id=user_id,
            )
        except Exception:
            logger.exception(
                "Failed to resolve subject context for stale-view detection: user=%s",
                user_id,
            )
            return False

        perspective, party_id = selected_view
        if perspective == "owner":
            return party_id not in self._normalize_identifier_sequence(
                getattr(subject_context, "owner_party_ids", [])
            )
        if perspective == "manager":
            return party_id not in self._normalize_identifier_sequence(
                getattr(subject_context, "manager_party_ids", [])
            )
        return False

    # ------------------------------------------------------------------
    # Trusted resource context resolution (dispatches to scope loaders)
    # ------------------------------------------------------------------

    async def _resolve_trusted_resource_context(
        self,
        *,
        db: AsyncSession,
        resource_id: str | None,
        request_context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_resource_id = normalize_optional_str(resource_id)
        normalized_request_context = self._normalize_context_mapping(request_context)
        if normalized_resource_id is None and len(normalized_request_context) == 0:
            return {}
        if normalized_resource_id is None and self.resource_type == "contract":
            return {}
        if not self._is_queryable_session(db):
            return {}

        if self.resource_type == "contact":
            return await self._load_contact_scope_context(
                db=db,
                contact_id=normalized_resource_id,
                request_context=normalized_request_context,
            )
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
        if self.resource_type == "contract_group":
            return await self._load_contract_group_scope_context(
                db=db,
                group_id=normalized_resource_id,
            )
        if self.resource_type == "contract":
            return await self._load_contract_scope_context(
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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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

    def _resolve_path_template(self, value: str, request: Request) -> str | None:
        if not (value.startswith("{") and value.endswith("}")):
            return value

        param_name = value[1:-1].strip()
        if param_name == "":
            return None
        return normalize_optional_str(request.path_params.get(param_name))

    @classmethod
    def _normalize_context_mapping(cls, value: Any) -> dict[str, Any]:
        if value is None or not isinstance(value, Mapping):
            return {}

        normalized: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = normalize_optional_str(key)
            if normalized_key is None:
                continue
            normalized[normalized_key] = item
        return normalized

    @classmethod
    def _normalize_scope_context(cls, value: Mapping[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = normalize_optional_str(key)
            if normalized_key is None:
                continue
            normalized_value = normalize_optional_str(item)
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
            normalized = normalize_optional_str(value)
            if normalized is None:
                continue
            normalized_values.append(normalized)
        return normalized_values

    async def _extract_request_context(self, request: Request) -> dict[str, Any]:
        context: dict[str, Any] = {}
        for key, value in request.path_params.items():
            if not key.endswith("_id"):
                continue
            normalized = normalize_optional_str(value)
            if normalized is None:
                continue
            context[key] = normalized
        return context

    def _extract_selected_view(self, request: Request) -> tuple[str, str] | None:
        perspective = normalize_optional_str(
            request.headers.get(VIEW_PERSPECTIVE_HEADER_NAME)
        )
        party_id = normalize_optional_str(
            request.headers.get(VIEW_PARTY_ID_HEADER_NAME)
        )
        if perspective not in {"owner", "manager"} or party_id is None:
            return None
        return perspective, party_id

    def _is_queryable_session(self, db: Any) -> bool:
        if isinstance(db, AsyncSession):
            return True
        execute = getattr(db, "execute", None)
        if execute is None:
            return False
        return inspect.iscoroutinefunction(execute)

    @staticmethod
    def _build_unscoped_party_id(*, resource_type: str, resource_id: str) -> str:
        return f"__unscoped__:{resource_type}:{resource_id}"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


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
