"""Authz service orchestration for ABAC checks and capability snapshots."""

from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.authz import CRUDAuthz, crud_authz
from ...models.abac import ABACEffect
from ...schemas.authz import (
    AuthzAction,
    CapabilitiesResponse,
    CapabilityItem,
    DataScope,
    PerspectiveName,
)
from ...schemas.rbac import PermissionCheckRequest
from ..permission.rbac_service import RBACService
from .cache import (
    AuthzDecisionCache,
    build_decision_key,
    compute_roles_hash,
)
from .context_builder import AuthzContextBuilder
from .engine import AuthzDecision, AuthzEngine
from .events import AuthzEventBus
from .resource_perspective_registry import (
    resolve_capability_perspectives,
    resource_requires_perspective,
)


class AuthzService:
    """Facade for ABAC decision and capability APIs."""

    CAPABILITIES_VERSION = "2026-03-25.v1"

    def __init__(
        self,
        *,
        engine: AuthzEngine | None = None,
        context_builder: AuthzContextBuilder | None = None,
        authz_crud: CRUDAuthz | None = None,
        decision_cache: AuthzDecisionCache | None = None,
        event_bus: AuthzEventBus | None = None,
    ) -> None:
        self.engine = engine or AuthzEngine()
        self.context_builder = context_builder or AuthzContextBuilder()
        self.authz_crud = authz_crud or crud_authz
        self.decision_cache = decision_cache or AuthzDecisionCache()
        self.event_bus = event_bus or AuthzEventBus()

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
        role_summary = await self._get_user_role_summary(db, user_id=user_id)
        role_ids = role_summary.get("role_ids", [])
        if bool(role_summary.get("is_admin")):
            return AuthzDecision(
                allowed=True,
                reason_code="rbac_admin_bypass",
            )

        subject_context = await self.context_builder.build_subject_context(
            db,
            user_id=user_id,
            role_ids=role_ids,
        )

        resource_payload = dict(resource or {})
        resource_payload["resource_type"] = resource_type
        if resource_id is not None and str(resource_id).strip() != "":
            resource_payload.setdefault("resource_id", resource_id)

        roles_hash = compute_roles_hash(role_ids)
        perspective_token = self._build_perspective_token(subject_context)
        context_hash = self.decision_cache.hash_context(
            {
                "roles_hash": roles_hash,
                "subject": subject_context.to_dict(),
                "resource": resource_payload,
                "action": action,
            }
        )
        decision_key = build_decision_key(
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            perspective=perspective_token,
            context_hash=context_hash,
        )

        cached = self.decision_cache.lookup(decision_key)
        if cached.cache_hit and isinstance(cached.value, dict):
            return self._deserialize_decision(cached.value)

        policies = await self.authz_crud.get_policies_by_role_ids(
            db,
            role_ids=role_ids,
            enabled_only=True,
        )
        has_matching_policy_rule = self._has_matching_policy_rule(
            policies,
            resource_type=resource_type,
            action=action,
        )
        decision = self.engine.evaluate_with_reason(
            subject=subject_context.to_dict(),
            resource=resource_payload,
            action=action,
            policies=policies,
        )
        if (
            not decision.allowed
            and not has_matching_policy_rule
            and await self._has_static_rbac_permission(
                db,
                user_id=user_id,
                resource_type=resource_type,
                action=action,
                resource_id=resource_id,
            )
        ):
            decision = AuthzDecision(
                allowed=True,
                reason_code="rbac_permission_fallback",
            )
        self.decision_cache.set(decision_key, self._serialize_decision(decision))
        return decision

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
        static_rbac_actions = await self._get_static_rbac_actions(db, user_id=user_id)

        actions_by_resource: dict[str, set[str]] = {}
        for resource, actions in static_rbac_actions.items():
            actions_by_resource.setdefault(resource, set()).update(actions)
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

        subject_perspectives = self._resolve_perspectives(subject_context)
        capabilities: list[CapabilityItem] = []
        for resource, actions in sorted(actions_by_resource.items()):
            normalized_actions: list[AuthzAction] = []
            for action in sorted(actions):
                if action in {"create", "read", "list", "update", "delete", "export"}:
                    normalized_actions.append(cast(AuthzAction, action))
            perspectives = resolve_capability_perspectives(
                resource,
                subject_perspectives,
            )
            if resource_requires_perspective(resource) and len(perspectives) == 0:
                continue
            capabilities.append(
                CapabilityItem(
                    resource=resource,
                    actions=normalized_actions,
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

    async def _get_user_role_summary(
        self,
        db: AsyncSession,
        *,
        user_id: str,
    ) -> dict[str, Any]:
        rbac_service = RBACService(db)
        summary = await rbac_service.get_user_role_summary(user_id)
        if not isinstance(summary, dict):
            return {
                "role_ids": [],
                "is_admin": False,
            }

        role_ids = summary.get("role_ids")
        if not isinstance(role_ids, list):
            role_ids = []

        resolved_ids: list[str] = []
        for role_id in role_ids:
            role_id_str = str(role_id).strip()
            if role_id_str != "":
                resolved_ids.append(role_id_str)

        return {
            "role_ids": resolved_ids,
            "is_admin": bool(summary.get("is_admin")),
        }

    async def _get_user_role_ids(self, db: AsyncSession, *, user_id: str) -> list[str]:
        role_summary = await self._get_user_role_summary(db, user_id=user_id)
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
    def _resolve_perspectives(subject_context: Any) -> list[PerspectiveName]:
        perspectives: list[PerspectiveName] = []
        if len(subject_context.owner_party_ids) > 0:
            perspectives.append("owner")
        if len(subject_context.manager_party_ids) > 0:
            perspectives.append("manager")
        return perspectives

    @classmethod
    def _build_perspective_token(cls, subject_context: Any) -> str:
        perspectives = cls._resolve_perspectives(subject_context)
        if not perspectives:
            return "-"
        return ",".join(sorted(set(perspectives)))

    @staticmethod
    def _has_matching_policy_rule(
        policies: list[Any],
        *,
        resource_type: str,
        action: str,
    ) -> bool:
        for policy in policies:
            if not bool(getattr(policy, "enabled", True)):
                continue
            for rule in getattr(policy, "rules", []):
                if str(getattr(rule, "resource_type", "") or "") != resource_type:
                    continue
                if str(getattr(rule, "action", "") or "") != action:
                    continue
                return True
        return False

    async def _get_static_rbac_actions(
        self,
        db: AsyncSession,
        *,
        user_id: str,
    ) -> dict[str, set[str]]:
        rbac_service = RBACService(db)
        try:
            summary = await rbac_service.get_user_permissions_summary(user_id)
        except Exception:
            return {}

        effective_permissions = getattr(summary, "effective_permissions", {})
        if not isinstance(effective_permissions, dict):
            return {}

        normalized: dict[str, set[str]] = {}
        for resource, actions in effective_permissions.items():
            resource_name = str(resource).strip()
            if resource_name == "" or not isinstance(actions, list):
                continue
            for action_name in actions:
                normalized_action = str(action_name).strip()
                if normalized_action == "":
                    continue
                normalized.setdefault(resource_name, set()).add(normalized_action)
        return normalized

    async def _has_static_rbac_permission(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        resource_type: str,
        action: str,
        resource_id: str | None,
    ) -> bool:
        rbac_service = RBACService(db)
        try:
            result = await rbac_service.check_permission(
                user_id,
                PermissionCheckRequest(
                    resource=resource_type,
                    action=action,
                    resource_id=resource_id,
                    context=None,
                ),
            )
        except Exception:
            return False

        return bool(getattr(result, "has_permission", False))

    @staticmethod
    def _serialize_decision(decision: AuthzDecision) -> dict[str, Any]:
        return {
            "allowed": decision.allowed,
            "reason_code": decision.reason_code,
            "matched_policy_id": decision.matched_policy_id,
            "matched_rule_id": decision.matched_rule_id,
            "field_mask": decision.field_mask,
        }

    @staticmethod
    def _deserialize_decision(payload: dict[str, Any]) -> AuthzDecision:
        return AuthzDecision(
            allowed=bool(payload.get("allowed", False)),
            reason_code=str(payload.get("reason_code") or "cached_decision"),
            matched_policy_id=(
                str(payload.get("matched_policy_id"))
                if payload.get("matched_policy_id") is not None
                else None
            ),
            matched_rule_id=(
                str(payload.get("matched_rule_id"))
                if payload.get("matched_rule_id") is not None
                else None
            ),
            field_mask=(
                payload.get("field_mask")
                if isinstance(payload.get("field_mask"), dict)
                else None
            ),
        )


__all__ = ["AuthzService"]
