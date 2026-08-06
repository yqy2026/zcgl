"""ABAC authorization dependency helpers."""

from __future__ import annotations

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
from ..services.authz import authz_service as default_authz_service
from . import resource_context as trusted_resource_context
from .identity import get_current_active_user

logger = logging.getLogger(__name__)

ResourceIdResolver = Callable[[Request], str | None | Awaitable[str | None]]
ResourceContextResolver = Callable[
    [Request],
    Mapping[str, Any]
    | dict[str, Any]
    | None
    | Awaitable[Mapping[str, Any] | dict[str, Any] | None],
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
        authz_service_client: Any = default_authz_service,
        log: logging.Logger | None = None,
    ) -> None:
        self.authz_service = authz_service_client
        self.logger = log or logger
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
            decision = await self.authz_service.check_access(
                db,
                user_id=str(current_user.id),
                resource_type=self.resource_type,
                action=self.action,
                resource_id=resolved_resource_id,
                resource=resolved_resource_context,
            )
        except Exception:
            self.logger.exception(
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
            subject_context = (
                await self.authz_service.context_builder.build_subject_context(
                    db,
                    user_id=user_id,
                )
            )
        except Exception:
            self.logger.exception(
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

    def _is_queryable_session(self, db: Any) -> bool:
        return trusted_resource_context.is_queryable_session(db)

    async def _load_asset_scope_context(
        self,
        *,
        db: AsyncSession,
        asset_id: str,
    ) -> dict[str, Any]:
        return await trusted_resource_context.load_asset_scope_context(
            db=db,
            asset_id=asset_id,
        )

    async def _load_project_scope_context(
        self,
        *,
        db: AsyncSession,
        project_id: str,
    ) -> dict[str, Any]:
        return await trusted_resource_context.load_project_scope_context(
            db=db,
            project_id=project_id,
        )

    async def _load_contract_scope_context(
        self,
        *,
        db: AsyncSession,
        contract_id: str,
    ) -> dict[str, Any]:
        return await trusted_resource_context.load_contract_scope_context(
            db=db,
            contract_id=contract_id,
        )

    async def _load_ownership_scope_context(
        self,
        *,
        db: AsyncSession,
        ownership_id: str,
    ) -> dict[str, Any]:
        return await trusted_resource_context.load_ownership_scope_context(
            db=db,
            ownership_id=ownership_id,
            resolve_ownership_party_id=self._resolve_ownership_party_id,
        )

    async def _load_party_scope_context(
        self,
        *,
        db: AsyncSession,
        party_id: str,
    ) -> dict[str, Any]:
        return await trusted_resource_context.load_party_scope_context(
            db=db,
            party_id=party_id,
        )

    async def _load_role_scope_context(
        self,
        *,
        db: AsyncSession,
        role_id: str,
    ) -> dict[str, Any]:
        return await trusted_resource_context.load_role_scope_context(
            db=db,
            role_id=role_id,
        )

    async def _load_user_scope_context(
        self,
        *,
        db: AsyncSession,
        user_id: str,
    ) -> dict[str, Any]:
        return await trusted_resource_context.load_user_scope_context(
            db=db,
            user_id=user_id,
        )

    async def _load_task_scope_context(
        self,
        *,
        db: AsyncSession,
        task_id: str,
    ) -> dict[str, Any]:
        return await trusted_resource_context.load_task_scope_context(
            db=db,
            task_id=task_id,
            load_user_scope_context=self._load_user_scope_context,
        )

    @staticmethod
    def _build_unscoped_party_id(*, resource_type: str, resource_id: str) -> str:
        return trusted_resource_context.build_unscoped_party_id(
            resource_type=resource_type,
            resource_id=resource_id,
        )

    async def _load_organization_scope_context(
        self,
        *,
        db: AsyncSession,
        organization_id: str,
    ) -> dict[str, Any]:
        return await trusted_resource_context.load_organization_scope_context(
            db=db,
            organization_id=organization_id,
        )

    async def _resolve_ownership_party_id(
        self,
        *,
        db: AsyncSession,
        ownership_id: str,
        ownership_code: Any,
        ownership_name: Any,
    ) -> str | None:
        return await trusted_resource_context.resolve_ownership_party_id(
            db=db,
            ownership_id=ownership_id,
            ownership_code=ownership_code,
            ownership_name=ownership_name,
        )

    async def _load_property_certificate_scope_context(
        self,
        *,
        db: AsyncSession,
        certificate_id: str,
    ) -> dict[str, Any]:
        return await trusted_resource_context.load_property_certificate_scope_context(
            db=db,
            certificate_id=certificate_id,
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
