"""Sensitive Party activation-state preview and commit workflow."""

from __future__ import annotations

import hashlib
import json
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.cache_manager import cache_manager
from ...core.exception_handler import (
    OperationNotAllowedError,
    PartyLifecyclePreviewStaleError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from ...crud.auth import UserCRUD
from ...crud.organization import organization as organization_crud
from ...crud.party import party_crud
from ...crud.party_lifecycle_commit import (
    PartyLifecycleCommitCRUD,
    party_lifecycle_commit_crud,
)
from ...models.auth import User
from ...models.organization import Organization
from ...models.party import Party, PartyReviewStatus
from ...schemas.party import (
    PartyLifecycleCommitRequest,
    PartyLifecycleCommitResponse,
    PartyLifecycleImpact,
    PartyLifecycleOperation,
    PartyLifecyclePreviewRequest,
    PartyLifecyclePreviewResponse,
    PartyLifecycleState,
)
from ..organization_permission_service import (
    invalidate_user_accessible_organizations_cache,
)
from ..party_scope_resolver import (
    EffectivePartyScope,
    PartyScopeRepository,
    PartyScopeResolver,
)
from .service import party_service


@dataclass(frozen=True)
class _PreviewAnalysis:
    before_state: PartyLifecycleState
    after_state: PartyLifecycleState
    impact: PartyLifecycleImpact
    state_fingerprint: str
    affected_user_ids: tuple[str, ...]


class PartyLifecyclePreviewStore:
    """Short-lived server-side storage for opaque Party lifecycle tokens."""

    NAMESPACE = "party_lifecycle_preview"
    TTL = timedelta(minutes=10)

    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC).replace(tzinfo=None))

    def issue(self, payload: dict[str, object]) -> tuple[str, datetime]:
        token = secrets.token_urlsafe(32)
        expires_at = self._clock() + self.TTL
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if not cache_manager.set(
            token_hash,
            {**payload, "expires_at": expires_at.isoformat()},
            ttl=int(self.TTL.total_seconds()),
            namespace=self.NAMESPACE,
        ):
            raise ServiceUnavailableError(
                "Unable to store the Party lifecycle preview",
                service_name="party_lifecycle_preview",
            )
        return token, expires_at

    def consume(self, raw_token: str) -> dict[str, object] | None:
        """Consume a preview token exactly once."""
        token = str(raw_token).strip()
        if token == "":  # nosec B105 - token 空串守卫，非硬编码密码
            return None

        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        payload = cache_manager.consume(token_hash, namespace=self.NAMESPACE)
        if not isinstance(payload, dict):
            return None
        expires_at_raw = payload.get("expires_at")
        if not isinstance(expires_at_raw, str):
            return None
        try:
            expires_at = datetime.fromisoformat(expires_at_raw)
        except ValueError:
            return None
        if expires_at <= self._clock():
            return None
        return payload


class _OverlayPartyLifecycleScopeRepository:
    """Resolve affected scopes as though one Party had a new activation state."""

    def __init__(
        self,
        *,
        base: PartyScopeRepository,
        party_id: str,
        party_status: str,
    ) -> None:
        self._base = base
        self._party_id = party_id
        self._party_status = party_status

    async def load_role_names(
        self, db: AsyncSession, *, user_id: str, now: datetime
    ) -> list[str]:
        return await self._base.load_role_names(db, user_id=user_id, now=now)

    async def load_user(
        self, db: AsyncSession, *, user_id: str
    ) -> Mapping[str, Any] | None:
        return await self._base.load_user(db, user_id=user_id)

    async def load_bindings(
        self, db: AsyncSession, *, user_id: str, now: datetime
    ) -> list[Mapping[str, Any]]:
        bindings = await self._base.load_bindings(db, user_id=user_id, now=now)
        return [self._with_party_status(dict(binding)) for binding in bindings]

    async def load_organization(
        self, db: AsyncSession, *, organization_id: str
    ) -> Mapping[str, Any] | None:
        organization = await self._base.load_organization(
            db,
            organization_id=organization_id,
        )
        if organization is None:
            return None
        return self._with_party_status(dict(organization))

    def _with_party_status(self, value: dict[str, Any]) -> dict[str, Any]:
        party_id = self._normalize_identifier(value.get("party_id"))
        if party_id is None:
            party_id = self._normalize_identifier(value.get("represented_party_id"))
        if party_id == self._party_id:
            value["party_status"] = self._party_status
        return value

    @staticmethod
    def _normalize_identifier(value: object | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized if normalized != "" else None


class PartyLifecycleChangeService:
    """Preview and commit Party deactivate/reactivate actions atomically."""

    def __init__(
        self,
        *,
        preview_store: PartyLifecyclePreviewStore | None = None,
        commit_crud: PartyLifecycleCommitCRUD | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC).replace(tzinfo=None))
        self.preview_store = preview_store or PartyLifecyclePreviewStore(
            clock=self._clock
        )
        self.commit_crud = commit_crud or party_lifecycle_commit_crud
        self.user_crud = UserCRUD()

    async def preview(
        self,
        db: AsyncSession,
        *,
        party_id: str,
        request: PartyLifecyclePreviewRequest,
        actor_id: str,
    ) -> PartyLifecyclePreviewResponse:
        operation = self._normalize_operation(request.operation)
        analysis = await self._build_preview_analysis(
            db,
            party_id=party_id,
            operation=operation,
        )
        token, expires_at = self.preview_store.issue(
            {
                "actor_id": actor_id,
                "party_id": party_id,
                "operation": operation,
                "state_fingerprint": analysis.state_fingerprint,
            }
        )
        return PartyLifecyclePreviewResponse(
            party_id=party_id,
            operation=operation,
            before_state=analysis.before_state,
            after_state=analysis.after_state,
            impact=analysis.impact,
            preview_token=token,
            expires_at=expires_at,
        )

    async def commit(
        self,
        db: AsyncSession,
        *,
        party_id: str,
        operation: PartyLifecycleOperation | str,
        request: PartyLifecycleCommitRequest,
        actor_id: str,
    ) -> PartyLifecycleCommitResponse:
        """Commit a current lifecycle preview exactly once and return its receipt."""
        normalized_operation = self._normalize_operation(operation)
        existing = await self.commit_crud.get_by_idempotency_async(
            db,
            party_id=party_id,
            actor_id=actor_id,
            idempotency_key=request.idempotency_key,
        )
        if existing is not None:
            return self._response_from_receipt(existing, idempotent=True)

        preview_payload = self.preview_store.consume(request.preview_token)
        if preview_payload is None:
            raise PartyLifecyclePreviewStaleError("missing_or_expired")
        self._validate_preview_payload(
            preview_payload,
            party_id=party_id,
            operation=normalized_operation,
            actor_id=actor_id,
        )

        locked_party = await party_crud.get_party_for_update(db, party_id=party_id)
        if locked_party is None:
            raise PartyLifecyclePreviewStaleError("target_missing")

        try:
            analysis = await self._build_preview_analysis(
                db,
                party_id=party_id,
                operation=normalized_operation,
                party=locked_party,
            )
        except (OperationNotAllowedError, ResourceNotFoundError) as exc:
            raise PartyLifecyclePreviewStaleError("state_changed") from exc
        if preview_payload.get("state_fingerprint") != analysis.state_fingerprint:
            raise PartyLifecyclePreviewStaleError("state_changed")

        existing = await self.commit_crud.get_by_idempotency_async(
            db,
            party_id=party_id,
            actor_id=actor_id,
            idempotency_key=request.idempotency_key,
        )
        if existing is not None:
            return self._response_from_receipt(existing, idempotent=True)

        updated_party = await party_crud.update_party(
            db,
            db_obj=locked_party,
            obj_in={"status": analysis.after_state.status},
            commit=False,
        )
        await party_service._write_review_log(
            db,
            party_id=party_id,
            action=normalized_operation,
            from_status=analysis.before_state.status,
            to_status=analysis.after_state.status,
            operator=actor_id,
            reason=request.reason,
        )

        committed_at = self._clock()
        response = PartyLifecycleCommitResponse(
            party=party_service.to_response(updated_party),
            operation=normalized_operation,
            before_state=analysis.before_state,
            after_state=analysis.after_state,
            impact=analysis.impact,
            committed_at=committed_at,
            idempotent=False,
        )
        await self.commit_crud.create_async(
            db,
            party_id=party_id,
            actor_id=actor_id,
            idempotency_key=request.idempotency_key,
            operation=normalized_operation,
            reason=request.reason,
            before_state=analysis.before_state.model_dump(mode="json"),
            after_state=analysis.after_state.model_dump(mode="json"),
            impact_summary=analysis.impact.model_dump(mode="json"),
            result_data=response.model_dump(mode="json"),
            committed_at=committed_at,
        )
        await db.commit()
        await db.refresh(updated_party)
        await self._invalidate_after_commit(analysis.affected_user_ids)
        return response

    async def _build_preview_analysis(
        self,
        db: AsyncSession,
        *,
        party_id: str,
        operation: str,
        party: Party | None = None,
    ) -> _PreviewAnalysis:
        current_party = party or await party_crud.get_party(db, party_id=party_id)
        if current_party is None:
            raise ResourceNotFoundError("Party", party_id)
        self._assert_allowed_transition(current_party, operation=operation)

        now = self._clock()
        before_state = self._state_from_party(current_party)
        after_status = "inactive" if operation == "deactivate" else "active"
        after_state = PartyLifecycleState(
            party_id=str(current_party.id),
            status=after_status,
            review_status=self._normalize_enum(current_party.review_status) or "draft",
            available_for_new_references=after_status == "active",
        )

        represented_organizations = (
            await organization_crud.get_represented_by_party_async(
                db,
                party_id=party_id,
            )
        )
        affected_organizations = await self._load_affected_organizations(
            db,
            represented_organizations=represented_organizations,
        )
        reference_snapshot = await party_crud.get_lifecycle_reference_snapshot(
            db,
            party_id=party_id,
            now=now,
        )
        organization_users = (
            await self.user_crud.get_active_human_by_organization_ids_async(
                db,
                organization_ids=[str(item.id) for item in affected_organizations],
            )
        )
        binding_users = await self.user_crud.get_active_human_by_ids_async(
            db,
            user_ids=[
                str(binding["user_id"]) for binding in reference_snapshot["bindings"]
            ],
        )
        users = self._deduplicate_users([*organization_users, *binding_users])
        (
            user_scope_changes,
            user_scope_signatures,
        ) = await self._count_user_scope_changes(
            db,
            users=users,
            party_id=party_id,
            after_status=after_status,
            now=now,
        )
        bindings = reference_snapshot["bindings"]
        impact = PartyLifecycleImpact(
            represented_organization_count=len(represented_organizations),
            potentially_affected_organization_count=len(affected_organizations),
            current_user_binding_count=sum(
                1 for binding in bindings if self._is_current_binding(binding, now=now)
            ),
            affected_user_count=len(users),
            user_scope_change_count=user_scope_changes,
            asset_reference_count=len(reference_snapshot["asset_ids"]),
            project_reference_count=len(reference_snapshot["project_ids"]),
            contract_group_reference_count=len(
                reference_snapshot["contract_group_ids"]
            ),
            contract_reference_count=len(reference_snapshot["contract_ids"]),
        )
        fingerprint = self._state_fingerprint(
            party=current_party,
            operation=operation,
            before_state=before_state,
            after_state=after_state,
            represented_organizations=represented_organizations,
            affected_organizations=affected_organizations,
            users=users,
            reference_snapshot=reference_snapshot,
            impact=impact,
            user_scope_signatures=user_scope_signatures,
        )
        return _PreviewAnalysis(
            before_state=before_state,
            after_state=after_state,
            impact=impact,
            state_fingerprint=fingerprint,
            affected_user_ids=tuple(str(user.id) for user in users),
        )

    async def _load_affected_organizations(
        self,
        db: AsyncSession,
        *,
        represented_organizations: list[Organization],
    ) -> list[Organization]:
        organizations: list[Organization] = []
        for organization in represented_organizations:
            organizations.append(organization)
            organizations.extend(
                await organization_crud.get_children_async(
                    db,
                    parent_id=str(organization.id),
                    recursive=True,
                )
            )
        return self._deduplicate_organizations(organizations)

    async def _count_user_scope_changes(
        self,
        db: AsyncSession,
        *,
        users: list[User],
        party_id: str,
        after_status: str,
        now: datetime,
    ) -> tuple[int, tuple[dict[str, object], ...]]:
        base_repository = PartyScopeRepository()
        before_resolver = PartyScopeResolver(
            repository=base_repository,
            clock=lambda: now,
        )
        after_resolver = PartyScopeResolver(
            repository=_OverlayPartyLifecycleScopeRepository(
                base=base_repository,
                party_id=party_id,
                party_status=after_status,
            ),
            clock=lambda: now,
        )
        changed_count = 0
        signatures: list[dict[str, object]] = []
        for user in users:
            user_id = str(user.id)
            before = await before_resolver.resolve(db, user_id=user_id)
            after = await after_resolver.resolve(db, user_id=user_id)
            before_signature = self._effective_scope_signature(before)
            after_signature = self._effective_scope_signature(after)
            signatures.append(
                {
                    "user_id": user_id,
                    "before": before_signature,
                    "after": after_signature,
                }
            )
            if before_signature != after_signature:
                changed_count += 1
        return changed_count, tuple(signatures)

    async def _invalidate_after_commit(
        self, affected_user_ids: tuple[str, ...]
    ) -> None:
        cache_manager.clear(namespace="party")
        cache_manager.clear(namespace="organization")
        invalidate_user_accessible_organizations_cache()
        for user_id in affected_user_ids:
            await party_service._publish_user_scope_invalidation(user_id)

    @staticmethod
    def _assert_allowed_transition(party: Party, *, operation: str) -> None:
        if party.review_status != PartyReviewStatus.APPROVED:
            raise OperationNotAllowedError(
                "Only approved Parties can change activation state",
                reason="party_lifecycle_review_not_approved",
            )
        if operation == "deactivate" and party.status != "active":
            raise OperationNotAllowedError(
                "Only active Parties can be deactivated",
                reason="party_lifecycle_deactivate_invalid_status",
            )
        if operation == "reactivate" and party.status != "inactive":
            raise OperationNotAllowedError(
                "Only inactive Parties can be reactivated",
                reason="party_lifecycle_reactivate_invalid_status",
            )

    @classmethod
    def _state_from_party(cls, party: Party) -> PartyLifecycleState:
        status = cls._normalize_enum(getattr(party, "status", None)) or "inactive"
        review_status = (
            cls._normalize_enum(getattr(party, "review_status", None)) or "draft"
        )
        return PartyLifecycleState(
            party_id=str(party.id),
            status=status,
            review_status=review_status,
            available_for_new_references=(
                status == "active" and review_status == PartyReviewStatus.APPROVED.value
            ),
        )

    @staticmethod
    def _normalize_operation(
        value: PartyLifecycleOperation | str,
    ) -> PartyLifecycleOperation:
        normalized = str(getattr(value, "value", value)).strip()
        if normalized not in {"deactivate", "reactivate"}:
            raise PartyLifecyclePreviewStaleError("invalid_operation")
        return cast(PartyLifecycleOperation, normalized)

    @staticmethod
    def _validate_preview_payload(
        payload: dict[str, object],
        *,
        party_id: str,
        operation: str,
        actor_id: str,
    ) -> None:
        if (
            payload.get("party_id") != party_id
            or payload.get("operation") != operation
            or payload.get("actor_id") != actor_id
        ):
            raise PartyLifecyclePreviewStaleError("token_binding_mismatch")

    @staticmethod
    def _deduplicate_organizations(
        organizations: list[Organization],
    ) -> list[Organization]:
        deduplicated: list[Organization] = []
        seen_ids: set[str] = set()
        for organization in organizations:
            organization_id = str(organization.id)
            if organization_id in seen_ids:
                continue
            seen_ids.add(organization_id)
            deduplicated.append(organization)
        return deduplicated

    @staticmethod
    def _deduplicate_users(users: list[User]) -> list[User]:
        deduplicated: list[User] = []
        seen_ids: set[str] = set()
        for user in users:
            user_id = str(user.id)
            if user_id in seen_ids:
                continue
            seen_ids.add(user_id)
            deduplicated.append(user)
        return deduplicated

    @staticmethod
    def _is_current_binding(binding: Mapping[str, Any], *, now: datetime) -> bool:
        valid_from = binding.get("valid_from")
        valid_to = binding.get("valid_to")
        return (
            isinstance(valid_from, datetime)
            and valid_from <= now
            and (
                valid_to is None or (isinstance(valid_to, datetime) and valid_to >= now)
            )
        )

    def _state_fingerprint(
        self,
        *,
        party: Party,
        operation: str,
        before_state: PartyLifecycleState,
        after_state: PartyLifecycleState,
        represented_organizations: list[Organization],
        affected_organizations: list[Organization],
        users: list[User],
        reference_snapshot: Mapping[str, Any],
        impact: PartyLifecycleImpact,
        user_scope_signatures: tuple[dict[str, object], ...],
    ) -> str:
        payload = {
            "operation": operation,
            "party": {
                "id": str(party.id),
                "status": self._normalize_enum(party.status),
                "review_status": self._normalize_enum(party.review_status),
                "updated_at": self._serialize_datetime(
                    getattr(party, "updated_at", None)
                ),
            },
            "before_state": before_state.model_dump(mode="json"),
            "after_state": after_state.model_dump(mode="json"),
            "represented_organizations": [
                self._organization_signature(item) for item in represented_organizations
            ],
            "affected_organizations": [
                self._organization_signature(item) for item in affected_organizations
            ],
            "users": [self._user_signature(item) for item in users],
            "references": self._serialize_reference_snapshot(reference_snapshot),
            "impact": impact.model_dump(mode="json"),
            "user_scope_signatures": user_scope_signatures,
        }
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @classmethod
    def _organization_signature(cls, organization: Organization) -> dict[str, object]:
        return {
            "id": str(organization.id),
            "parent_id": cls._normalize_identifier(
                getattr(organization, "parent_id", None)
            ),
            "status": cls._normalize_enum(getattr(organization, "status", None)),
            "is_deleted": bool(getattr(organization, "is_deleted", False)),
            "represented_party_id": cls._normalize_identifier(
                getattr(organization, "represented_party_id", None)
            ),
            "represented_party_perspective": cls._normalize_enum(
                getattr(organization, "represented_party_perspective", None)
            ),
            "updated_at": cls._serialize_datetime(
                getattr(organization, "updated_at", None)
            ),
        }

    @classmethod
    def _user_signature(cls, user: User) -> dict[str, object]:
        return {
            "id": str(user.id),
            "account_type": cls._normalize_enum(getattr(user, "account_type", None)),
            "organization_id": cls._normalize_identifier(
                getattr(user, "organization_id", None)
            ),
            "is_active": bool(getattr(user, "is_active", False)),
            "updated_at": cls._serialize_datetime(getattr(user, "updated_at", None)),
        }

    @classmethod
    def _serialize_reference_snapshot(
        cls, snapshot: Mapping[str, Any]
    ) -> dict[str, object]:
        bindings: list[dict[str, object]] = []
        for binding in snapshot["bindings"]:
            bindings.append(
                {
                    "id": str(binding["id"]),
                    "user_id": str(binding["user_id"]),
                    "relation_type": cls._normalize_enum(binding["relation_type"]),
                    "valid_from": cls._serialize_datetime(binding["valid_from"]),
                    "valid_to": cls._serialize_datetime(binding["valid_to"]),
                    "updated_at": cls._serialize_datetime(binding["updated_at"]),
                }
            )
        return {
            "asset_ids": list(snapshot["asset_ids"]),
            "project_ids": list(snapshot["project_ids"]),
            "contract_group_ids": list(snapshot["contract_group_ids"]),
            "contract_ids": list(snapshot["contract_ids"]),
            "bindings": bindings,
        }

    @staticmethod
    def _effective_scope_signature(
        scope: EffectivePartyScope,
    ) -> tuple[str, tuple[str, ...], tuple[str, ...], str | None]:
        return (
            scope.scope_mode,
            tuple(scope.owner_party_ids),
            tuple(scope.manager_party_ids),
            scope.error_code,
        )

    @staticmethod
    def _normalize_enum(value: object | None) -> str | None:
        if value is None:
            return None
        normalized = str(getattr(value, "value", value)).strip()
        return normalized if normalized != "" else None

    @staticmethod
    def _normalize_identifier(value: object | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized if normalized != "" else None

    @staticmethod
    def _serialize_datetime(value: object | None) -> str | None:
        return value.isoformat() if isinstance(value, datetime) else None

    @staticmethod
    def _response_from_receipt(
        receipt: Any, *, idempotent: bool
    ) -> PartyLifecycleCommitResponse:
        payload = dict(receipt.result_data)
        payload["idempotent"] = idempotent
        return PartyLifecycleCommitResponse.model_validate(payload)


party_lifecycle_change_service = PartyLifecycleChangeService()

__all__ = [
    "PartyLifecycleChangeService",
    "PartyLifecyclePreviewStore",
    "party_lifecycle_change_service",
]
