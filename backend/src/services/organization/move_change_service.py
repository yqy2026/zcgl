"""Sensitive preview/commit flow for Organization hierarchy moves."""

from __future__ import annotations

import hashlib
import json
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.cache_manager import cache_manager
from ...core.exception_handler import (
    OperationNotAllowedError,
    OrganizationMovePreviewStaleError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from ...crud.auth import UserCRUD
from ...crud.organization import organization as organization_crud
from ...crud.organization_history import OrganizationHistoryCRUD
from ...crud.organization_move_commit import (
    OrganizationMoveCommitCRUD,
    organization_move_commit_crud,
)
from ...models.organization import Organization, RepresentedPartyPerspective
from ...schemas.organization import (
    OrganizationMoveCommitRequest,
    OrganizationMoveCommitResponse,
    OrganizationMoveImpact,
    OrganizationMovePreviewResponse,
    OrganizationMoveProposal,
    OrganizationMoveScopeState,
    OrganizationResponse,
)
from ..organization_permission_service import (
    invalidate_user_accessible_organizations_cache,
)
from ..party.service import party_service
from ..party_scope_resolver import (
    EffectivePartyScope,
    PartyScopeRepository,
    PartyScopeResolver,
)


@dataclass(frozen=True)
class _PreviewAnalysis:
    source: Organization
    subtree: tuple[Organization, ...]
    before_scope: OrganizationMoveScopeState
    after_scope: OrganizationMoveScopeState
    impact: OrganizationMoveImpact
    state_fingerprint: str
    lock_organization_ids: tuple[str, ...]
    affected_user_ids: tuple[str, ...]


class OrganizationMovePreviewStore:
    """Short-lived server-side storage for opaque Organization move tokens."""

    NAMESPACE = "organization_move_preview"
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
                "Unable to store the Organization move preview",
                service_name="organization_move_preview",
            )
        return token, expires_at

    def consume(self, raw_token: str) -> dict[str, object] | None:
        token = str(raw_token).strip()
        if token == "":
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


class _OverlayOrganizationMoveScopeRepository:
    """Resolve the proposed parent link without writing the Organization row."""

    def __init__(
        self,
        *,
        base: PartyScopeRepository,
        organization_id: str,
        target_parent_id: str | None,
    ) -> None:
        self._base = base
        self._organization_id = organization_id
        self._target_parent_id = target_parent_id

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
        return await self._base.load_bindings(db, user_id=user_id, now=now)

    async def load_organization(
        self, db: AsyncSession, *, organization_id: str
    ) -> Mapping[str, Any] | None:
        organization = await self._base.load_organization(
            db,
            organization_id=organization_id,
        )
        if organization is None or organization_id != self._organization_id:
            return organization
        return {**dict(organization), "parent_id": self._target_parent_id}


class OrganizationMoveService:
    """Preview and atomically commit one Organization hierarchy move."""

    def __init__(
        self,
        *,
        preview_store: OrganizationMovePreviewStore | None = None,
        commit_crud: OrganizationMoveCommitCRUD | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC).replace(tzinfo=None))
        self.preview_store = preview_store or OrganizationMovePreviewStore(
            clock=self._clock
        )
        self.commit_crud = commit_crud or organization_move_commit_crud
        self.user_crud = UserCRUD()

    async def preview(
        self,
        db: AsyncSession,
        *,
        organization_id: str,
        proposal: OrganizationMoveProposal,
        actor_id: str,
    ) -> OrganizationMovePreviewResponse:
        normalized_proposal = self._proposal_payload(proposal)
        analysis = await self._build_preview_analysis(
            db,
            organization_id=organization_id,
            proposal=normalized_proposal,
            now=self._clock(),
        )
        token, expires_at = self.preview_store.issue(
            {
                "actor_id": actor_id,
                "organization_id": organization_id,
                "proposal": normalized_proposal,
                "state_fingerprint": analysis.state_fingerprint,
            }
        )
        return OrganizationMovePreviewResponse(
            organization_id=organization_id,
            before_scope=analysis.before_scope,
            after_scope=analysis.after_scope,
            impact=analysis.impact,
            preview_token=token,
            expires_at=expires_at,
        )

    async def commit(
        self,
        db: AsyncSession,
        *,
        organization_id: str,
        request: OrganizationMoveCommitRequest,
        actor_id: str,
    ) -> OrganizationMoveCommitResponse:
        existing = await self.commit_crud.get_by_idempotency_async(
            db,
            organization_id=organization_id,
            actor_id=actor_id,
            idempotency_key=request.idempotency_key,
        )
        if existing is not None:
            return self._response_from_receipt(existing, idempotent=True)

        preview_payload = self.preview_store.consume(request.preview_token)
        if preview_payload is None:
            raise OrganizationMovePreviewStaleError("missing_or_expired")

        proposal = self._proposal_from_preview_payload(
            preview_payload,
            organization_id=organization_id,
            actor_id=actor_id,
        )
        try:
            initial_analysis = await self._build_preview_analysis(
                db,
                organization_id=organization_id,
                proposal=proposal,
                now=self._clock(),
            )
            await self._lock_organizations(db, initial_analysis.lock_organization_ids)
            analysis = await self._build_preview_analysis(
                db,
                organization_id=organization_id,
                proposal=proposal,
                now=self._clock(),
            )
        except (OperationNotAllowedError, ResourceNotFoundError) as exc:
            raise OrganizationMovePreviewStaleError("state_changed") from exc
        if preview_payload.get("state_fingerprint") != analysis.state_fingerprint:
            raise OrganizationMovePreviewStaleError("state_changed")

        existing = await self.commit_crud.get_by_idempotency_async(
            db,
            organization_id=organization_id,
            actor_id=actor_id,
            idempotency_key=request.idempotency_key,
        )
        if existing is not None:
            return self._response_from_receipt(existing, idempotent=True)

        committed_at = self._clock()
        target_parent_id = proposal["target_parent_id"]
        old_parent_id = self._normalize_identifier(analysis.source.parent_id)
        target_parent = await self._load_target_parent(
            db,
            target_parent_id=target_parent_id,
        )

        analysis.source.parent_id = target_parent_id
        analysis.source.level = (
            (int(target_parent.level or 0) + 1) if target_parent is not None else 1
        )
        analysis.source.path = (
            f"{target_parent.path}/{analysis.source.id}"
            if target_parent is not None and target_parent.path
            else (
                f"/{target_parent.id}/{analysis.source.id}"
                if target_parent is not None
                else f"/{analysis.source.id}"
            )
        )
        analysis.source.updated_at = committed_at
        analysis.source.updated_by = actor_id
        await db.flush()
        await organization_crud.update_children_path_async(db, analysis.source)

        await OrganizationHistoryCRUD().create_async(
            db,
            organization_id=organization_id,
            action="move",
            field_name="parent_id",
            old_value=old_parent_id,
            new_value=target_parent_id,
            change_reason=request.reason,
            created_by=actor_id,
        )

        response = OrganizationMoveCommitResponse(
            organization=OrganizationResponse.model_validate(analysis.source),
            before_scope=analysis.before_scope,
            after_scope=analysis.after_scope,
            impact=analysis.impact,
            committed_at=committed_at,
            idempotent=False,
        )
        await self.commit_crud.create_async(
            db,
            organization_id=organization_id,
            target_parent_id=target_parent_id,
            actor_id=actor_id,
            idempotency_key=request.idempotency_key,
            reason=request.reason,
            proposal=proposal,
            before_scope=analysis.before_scope.model_dump(mode="json"),
            after_scope=analysis.after_scope.model_dump(mode="json"),
            impact_summary=analysis.impact.model_dump(mode="json"),
            result_data=response.model_dump(mode="json"),
            committed_at=committed_at,
        )
        await db.commit()
        await db.refresh(analysis.source)
        self._invalidate_organization_cache()
        for user_id in analysis.affected_user_ids:
            await party_service._publish_user_scope_invalidation(user_id)
        return response

    async def _build_preview_analysis(
        self,
        db: AsyncSession,
        *,
        organization_id: str,
        proposal: dict[str, str | None],
        now: datetime,
    ) -> _PreviewAnalysis:
        source = await organization_crud.get_async(
            db,
            id=organization_id,
            use_cache=False,
        )
        if source is None:
            raise ResourceNotFoundError("组织", organization_id)
        self._assert_active_source(source)

        subtree = await self._load_subtree(db, source)
        subtree_ids = {str(item.id) for item in subtree}
        target_parent_id = proposal["target_parent_id"]
        old_parent_id = self._normalize_identifier(source.parent_id)
        if old_parent_id == target_parent_id:
            raise OperationNotAllowedError(
                "Organization is already assigned to the target parent",
                reason="organization_move_no_change",
            )
        if target_parent_id is not None and target_parent_id in subtree_ids:
            raise OperationNotAllowedError(
                "Organization cannot be moved beneath its own subtree",
                reason="organization_cycle",
            )

        old_chain = await self._load_organization_chain(
            db,
            organization_id=organization_id,
            require_active=False,
            reason="organization_move_source_chain_invalid",
        )
        target_chain = (
            await self._load_organization_chain(
                db,
                organization_id=target_parent_id,
                require_active=True,
                reason="organization_move_target_chain_invalid",
            )
            if target_parent_id is not None
            else []
        )
        organization_by_id = self._organization_map(
            [*subtree, *old_chain, *target_chain]
        )

        before_scope = self._organization_scope_state(
            source,
            organization_by_id=organization_by_id,
            moved_organization_id=organization_id,
            proposed_parent_id=None,
            apply_proposal=False,
        )
        after_scope = self._organization_scope_state(
            source,
            organization_by_id=organization_by_id,
            moved_organization_id=organization_id,
            proposed_parent_id=target_parent_id,
            apply_proposal=True,
        )
        organization_scope_change_count = sum(
            self._scope_signature(
                self._organization_scope_state(
                    item,
                    organization_by_id=organization_by_id,
                    moved_organization_id=organization_id,
                    proposed_parent_id=None,
                    apply_proposal=False,
                )
            )
            != self._scope_signature(
                self._organization_scope_state(
                    item,
                    organization_by_id=organization_by_id,
                    moved_organization_id=organization_id,
                    proposed_parent_id=target_parent_id,
                    apply_proposal=True,
                )
            )
            for item in subtree
        )

        users = await self.user_crud.get_active_human_by_organization_ids_async(
            db,
            organization_ids=sorted(subtree_ids),
        )
        (
            user_scope_change_count,
            user_scope_signatures,
        ) = await self._count_user_scope_changes(
            db,
            users=users,
            organization_id=organization_id,
            target_parent_id=target_parent_id,
            now=now,
        )
        impact = OrganizationMoveImpact(
            organization_count=len(subtree),
            organization_scope_change_count=organization_scope_change_count,
            organization_path_change_count=len(subtree),
            user_count=len(users),
            user_scope_change_count=user_scope_change_count,
        )
        lock_ids = tuple(sorted(organization_by_id))
        return _PreviewAnalysis(
            source=source,
            subtree=tuple(subtree),
            before_scope=before_scope,
            after_scope=after_scope,
            impact=impact,
            state_fingerprint=self._state_fingerprint(
                proposal=proposal,
                organization_by_id=organization_by_id,
                users=users,
                before_scope=before_scope,
                after_scope=after_scope,
                impact=impact,
                user_scope_signatures=user_scope_signatures,
            ),
            lock_organization_ids=lock_ids,
            affected_user_ids=tuple(sorted(str(user.id) for user in users)),
        )

    async def _load_subtree(
        self, db: AsyncSession, source: Organization
    ) -> list[Organization]:
        subtree: list[Organization] = []
        pending = [source]
        seen_ids: set[str] = set()
        while pending:
            current = pending.pop(0)
            current_id = str(current.id)
            if current_id in seen_ids:
                raise OperationNotAllowedError(
                    "Organization subtree contains a cycle",
                    reason="organization_move_source_chain_invalid",
                )
            seen_ids.add(current_id)
            subtree.append(current)
            pending.extend(
                await organization_crud.get_children_async(
                    db,
                    parent_id=current_id,
                    recursive=False,
                )
            )
        return subtree

    async def _load_organization_chain(
        self,
        db: AsyncSession,
        *,
        organization_id: str,
        require_active: bool,
        reason: str,
    ) -> list[Organization]:
        chain: list[Organization] = []
        current_id: str | None = organization_id
        visited: set[str] = set()
        while current_id is not None:
            if current_id in visited:
                raise OperationNotAllowedError(
                    "Organization hierarchy contains a cycle",
                    reason=reason,
                )
            visited.add(current_id)
            current = await organization_crud.get_async(
                db,
                id=current_id,
                use_cache=False,
            )
            if current is None:
                raise OperationNotAllowedError(
                    "Organization hierarchy is incomplete",
                    reason=reason,
                )
            if require_active and (
                bool(current.is_deleted) or str(current.status) != "active"
            ):
                raise OperationNotAllowedError(
                    "Target organization hierarchy must be active",
                    reason=reason,
                )
            chain.append(current)
            current_id = self._normalize_identifier(current.parent_id)
        return chain

    async def _load_target_parent(
        self, db: AsyncSession, *, target_parent_id: str | None
    ) -> Organization | None:
        if target_parent_id is None:
            return None
        target = await organization_crud.get_for_update_async(db, id=target_parent_id)
        if target is None:
            raise OrganizationMovePreviewStaleError("target_missing")
        if bool(target.is_deleted) or str(target.status) != "active":
            raise OrganizationMovePreviewStaleError("target_state_changed")
        return target

    async def _count_user_scope_changes(
        self,
        db: AsyncSession,
        *,
        users: list[Any],
        organization_id: str,
        target_parent_id: str | None,
        now: datetime,
    ) -> tuple[int, tuple[dict[str, object], ...]]:
        base_repository = PartyScopeRepository()
        before_resolver = PartyScopeResolver(
            repository=base_repository,
            clock=lambda: now,
        )
        after_resolver = PartyScopeResolver(
            repository=_OverlayOrganizationMoveScopeRepository(
                base=base_repository,
                organization_id=organization_id,
                target_parent_id=target_parent_id,
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

    async def _lock_organizations(
        self, db: AsyncSession, organization_ids: tuple[str, ...]
    ) -> None:
        if len(organization_ids) == 0:
            return
        rows = list(
            (
                await db.execute(
                    select(Organization)
                    .where(Organization.id.in_(organization_ids))
                    .order_by(Organization.id)
                    .with_for_update()
                )
            )
            .scalars()
            .all()
        )
        if len(rows) != len(organization_ids):
            raise OrganizationMovePreviewStaleError("organization_missing")

    @staticmethod
    def _assert_active_source(source: Organization) -> None:
        if bool(source.is_deleted) or str(source.status) != "active":
            raise OperationNotAllowedError(
                "Only active Organizations can be moved",
                reason="organization_move_source_invalid",
            )

    @staticmethod
    def _proposal_from_preview_payload(
        payload: dict[str, object],
        *,
        organization_id: str,
        actor_id: str,
    ) -> dict[str, str | None]:
        if payload.get("organization_id") != organization_id:
            raise OrganizationMovePreviewStaleError("organization_mismatch")
        if payload.get("actor_id") != actor_id:
            raise OrganizationMovePreviewStaleError("actor_mismatch")
        proposal = payload.get("proposal")
        if not isinstance(proposal, dict):
            raise OrganizationMovePreviewStaleError("proposal_missing")
        try:
            return OrganizationMoveService._proposal_payload(
                OrganizationMoveProposal.model_validate(proposal)
            )
        except ValueError as exc:
            raise OrganizationMovePreviewStaleError("proposal_invalid") from exc

    @staticmethod
    def _proposal_payload(
        proposal: OrganizationMoveProposal,
    ) -> dict[str, str | None]:
        return {"target_parent_id": proposal.target_parent_id}

    @staticmethod
    def _response_from_receipt(
        receipt: Any,
        *,
        idempotent: bool,
    ) -> OrganizationMoveCommitResponse:
        result_data = getattr(receipt, "result_data", None)
        if not isinstance(result_data, dict):
            raise OrganizationMovePreviewStaleError("receipt_invalid")
        return OrganizationMoveCommitResponse.model_validate(
            {**result_data, "idempotent": idempotent}
        )

    @classmethod
    def _organization_scope_state(
        cls,
        organization: Organization,
        *,
        organization_by_id: dict[str, Organization],
        moved_organization_id: str,
        proposed_parent_id: str | None,
        apply_proposal: bool,
    ) -> OrganizationMoveScopeState:
        organization_id = str(organization.id)
        direct_party_id = cls._normalize_identifier(organization.represented_party_id)
        direct_perspective = cls._normalize_perspective(
            organization.represented_party_perspective
        )
        current_id: str | None = organization_id
        visited: set[str] = set()
        while current_id is not None:
            if current_id in visited:
                break
            visited.add(current_id)
            current = organization_by_id.get(current_id)
            if current is None:
                break
            party_id = cls._normalize_identifier(current.represented_party_id)
            perspective = cls._normalize_perspective(
                current.represented_party_perspective
            )
            if party_id is not None and perspective is not None:
                return OrganizationMoveScopeState(
                    parent_id=(
                        proposed_parent_id
                        if apply_proposal and organization_id == moved_organization_id
                        else cls._normalize_identifier(organization.parent_id)
                    ),
                    effective_party_id=party_id,
                    effective_party_perspective=perspective,
                    source_organization_id=current_id,
                )
            current_id = (
                proposed_parent_id
                if apply_proposal and current_id == moved_organization_id
                else cls._normalize_identifier(current.parent_id)
            )
        return OrganizationMoveScopeState(
            parent_id=(
                proposed_parent_id
                if apply_proposal and organization_id == moved_organization_id
                else cls._normalize_identifier(organization.parent_id)
            ),
            effective_party_id=direct_party_id,
            effective_party_perspective=direct_perspective,
        )

    @staticmethod
    def _organization_map(
        organizations: list[Organization],
    ) -> dict[str, Organization]:
        return {str(organization.id): organization for organization in organizations}

    @staticmethod
    def _scope_signature(
        scope: OrganizationMoveScopeState,
    ) -> tuple[str | None, str | None, str | None]:
        perspective = scope.effective_party_perspective
        return (
            scope.effective_party_id,
            str(perspective) if perspective is not None else None,
            scope.source_organization_id,
        )

    @staticmethod
    def _effective_scope_signature(
        scope: EffectivePartyScope,
    ) -> tuple[str, str, tuple[str, ...], tuple[str, ...], str | None, str | None]:
        return (
            scope.source,
            scope.scope_mode,
            tuple(scope.owner_party_ids),
            tuple(scope.manager_party_ids),
            scope.source_organization_id,
            scope.error_code,
        )

    def _state_fingerprint(
        self,
        *,
        proposal: dict[str, str | None],
        organization_by_id: dict[str, Organization],
        users: list[Any],
        before_scope: OrganizationMoveScopeState,
        after_scope: OrganizationMoveScopeState,
        impact: OrganizationMoveImpact,
        user_scope_signatures: tuple[dict[str, object], ...],
    ) -> str:
        payload = {
            "proposal": proposal,
            "organizations": [
                {
                    "id": organization_id,
                    "parent_id": self._normalize_identifier(organization.parent_id),
                    "status": str(organization.status),
                    "is_deleted": bool(organization.is_deleted),
                    "represented_party_id": self._normalize_identifier(
                        organization.represented_party_id
                    ),
                    "represented_party_perspective": self._normalize_perspective(
                        organization.represented_party_perspective
                    ),
                    "updated_at": self._serialize_datetime(organization.updated_at),
                }
                for organization_id, organization in sorted(organization_by_id.items())
            ],
            "users": [
                {
                    "id": str(user.id),
                    "organization_id": self._normalize_identifier(user.organization_id),
                    "updated_at": self._serialize_datetime(user.updated_at),
                }
                for user in sorted(users, key=lambda item: str(item.id))
            ],
            "before_scope": before_scope.model_dump(mode="json"),
            "after_scope": after_scope.model_dump(mode="json"),
            "impact": impact.model_dump(mode="json"),
            "user_scope_signatures": user_scope_signatures,
        }
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_identifier(value: object | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized if normalized != "" else None

    @staticmethod
    def _normalize_perspective(
        value: object | None,
    ) -> RepresentedPartyPerspective | None:
        normalized = OrganizationMoveService._normalize_identifier(value)
        if normalized in {"owner", "manager"}:
            return RepresentedPartyPerspective(normalized)
        return None

    @staticmethod
    def _serialize_datetime(value: object | None) -> str | None:
        return value.isoformat() if isinstance(value, datetime) else None

    @staticmethod
    def _invalidate_organization_cache() -> None:
        cache_manager.clear(namespace="organization")
        invalidate_user_accessible_organizations_cache()


organization_move_service = OrganizationMoveService()

__all__ = [
    "OrganizationMovePreviewStore",
    "OrganizationMoveService",
    "organization_move_service",
]
