"""Authz service orchestration for ABAC checks and capability snapshots."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.authz import CRUDAuthz, crud_authz
from ...models.abac import ABACEffect
from ...schemas.authz import (
    CapabilitiesResponse,
    CapabilityItem,
    DataScope,
)
from ..permission.rbac_service import RBACService
from .context_builder import AuthzContextBuilder
from .engine import AuthzDecision, AuthzEngine


class AuthzService:
    """Facade for ABAC decision and capability APIs."""

    CAPABILITIES_VERSION = "2026-02-17.v1"

    def __init__(
        self,
        *,
        engine: AuthzEngine | None = None,
        context_builder: AuthzContextBuilder | None = None,
        authz_crud: CRUDAuthz | None = None,
    ) -> None:
        self.engine = engine or AuthzEngine()
        self.context_builder = context_builder or AuthzContextBuilder()
        self.authz_crud = authz_crud or crud_authz

    async def check_access(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        resource_type: str,
        action: str,
        resource_id: str | None = None,
        resource: dict[str, Any] | None = None,
    ) -> AuthzDecision:
        role_ids = await self._get_user_role_ids(db, user_id=user_id)
        subject_context = await self.context_builder.build_subject_context(
            db,
            user_id=user_id,
            role_ids=role_ids,
        )
        policies = await self.authz_crud.get_policies_by_role_ids(
            db,
            role_ids=role_ids,
            enabled_only=True,
        )

        resource_payload = dict(resource or {})
        resource_payload["resource_type"] = resource_type
        if resource_id is not None and str(resource_id).strip() != "":
            resource_payload.setdefault("resource_id", resource_id)

        return self.engine.evaluate_with_reason(
            subject=subject_context.to_dict(),
            resource=resource_payload,
            action=action,
            policies=policies,
        )

    async def get_capabilities(
        self,
        db: AsyncSession,
        *,
        user_id: str,
    ) -> CapabilitiesResponse:
        role_ids = await self._get_user_role_ids(db, user_id=user_id)
        subject_context = await self.context_builder.build_subject_context(
            db,
            user_id=user_id,
            role_ids=role_ids,
        )
        policies = await self.authz_crud.get_policies_by_role_ids(
            db,
            role_ids=role_ids,
            enabled_only=True,
        )

        actions_by_resource: dict[str, set[str]] = {}
        for policy in policies:
            if not bool(getattr(policy, "enabled", True)):
                continue
            if str(getattr(policy, "effect", "allow")) != ABACEffect.ALLOW.value:
                continue

            for rule in getattr(policy, "rules", []):
                resource = str(getattr(rule, "resource_type", "") or "")
                action = str(getattr(rule, "action", "") or "")
                if resource.strip() == "" or action.strip() == "":
                    continue
                actions_by_resource.setdefault(resource, set()).add(action)

        perspectives = self._resolve_perspectives(subject_context)
        capabilities: list[CapabilityItem] = []
        for resource, actions in sorted(actions_by_resource.items()):
            capabilities.append(
                CapabilityItem(
                    resource=resource,
                    actions=sorted(actions),
                    perspectives=perspectives,
                    data_scope=DataScope(
                        owner_party_ids=subject_context.owner_party_ids,
                        manager_party_ids=subject_context.manager_party_ids,
                    ),
                )
            )

        return CapabilitiesResponse(
            version=self.CAPABILITIES_VERSION,
            generated_at=datetime.now(UTC),
            capabilities=capabilities,
        )

    async def _get_user_role_ids(self, db: AsyncSession, *, user_id: str) -> list[str]:
        rbac_service = RBACService(db)
        role_summary = await rbac_service.get_user_role_summary(user_id)
        role_ids = role_summary.get("role_ids")
        if not isinstance(role_ids, list):
            return []

        resolved_ids: list[str] = []
        for role_id in role_ids:
            role_id_str = str(role_id).strip()
            if role_id_str != "":
                resolved_ids.append(role_id_str)
        return resolved_ids

    @staticmethod
    def _resolve_perspectives(subject_context: Any) -> list[str]:
        perspectives: list[str] = []
        if len(subject_context.owner_party_ids) > 0:
            perspectives.append("owner")
        if len(subject_context.manager_party_ids) > 0:
            perspectives.append("manager")
        return perspectives


__all__ = ["AuthzService"]
