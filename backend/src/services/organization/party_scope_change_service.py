"""Sensitive Organization represented-Party scope changes."""

from __future__ import annotations

import hashlib
import json
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.cache_manager import cache_manager
from ...core.exception_handler import (
    OperationNotAllowedError,
    OrganizationPartyScopePreviewStaleError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from ...crud.auth import UserCRUD
from ...crud.organization import organization as organization_crud
from ...crud.organization_history import OrganizationHistoryCRUD
from ...crud.organization_party_scope_commit import (
    OrganizationPartyScopeCommitCRUD,
    organization_party_scope_commit_crud,
)
from ...crud.party import party_crud
from ...models.organization import Organization, RepresentedPartyPerspective
from ...models.party import Party, PartyReviewStatus, PartyType
from ...schemas.organization import (
    OrganizationPartyScopeCommitRequest,
    OrganizationPartyScopeCommitResponse,
    OrganizationPartyScopeImpact,
    OrganizationPartyScopePreviewResponse,
    OrganizationPartyScopeProposal,
    OrganizationPartyScopeState,
    OrganizationResponse,
)
from ..organization_permission_service import (
    invalidate_user_accessible_organizations_cache,
)
from ..party_scope_resolver import (
    EffectivePartyScope,
    PartyScopeRepository,
    PartyScopeResolver,
)


@dataclass(frozen=True)
class OrganizationPartyScopeAnalysis:
    """Validated impact analysis reusable by single and batch scope changes."""

    before_scope: OrganizationPartyScopeState
    after_scope: OrganizationPartyScopeState
    impact: OrganizationPartyScopeImpact
    state_fingerprint: str
    user_scope_signatures: tuple[dict[str, object], ...]
    lock_organization_ids: tuple[str, ...]


class OrganizationPartyScopePreviewStore:
    """Short-lived server-side storage for opaque Organization scope tokens."""

    NAMESPACE = "organization_party_scope_preview"
    TTL = timedelta(minutes=10)

    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC).replace(tzinfo=None))

    def issue(self, payload: dict[str, object]) -> tuple[str, datetime]:
        token = secrets.token_urlsafe(32)
        expires_at = self._clock() + self.TTL
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        stored_payload = {
            **payload,
            "expires_at": expires_at.isoformat(),
        }
        if not cache_manager.set(
            token_hash,
            stored_payload,
            ttl=int(self.TTL.total_seconds()),
            namespace=self.NAMESPACE,
        ):
            raise ServiceUnavailableError(
                "Unable to store the Organization Party scope preview",
                service_name="organization_party_scope_preview",
            )
        return token, expires_at

    def consume(self, raw_token: str) -> dict[str, object] | None:
        """Consume a preview token exactly once."""
        return self._load(raw_token, consume=True)

    def peek(self, raw_token: str) -> dict[str, object] | None:
        """Read a still-valid token without consuming it for authorization checks."""
        return self._load(raw_token, consume=False)

    def _load(
        self,
        raw_token: str,
        *,
        consume: bool,
    ) -> dict[str, object] | None:
        token = str(raw_token).strip()
        if token == "":  # nosec B105 - token 空串守卫，非硬编码密码
            return None

        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        payload = (
            cache_manager.consume(token_hash, namespace=self.NAMESPACE)
            if consume
            else cache_manager.get(token_hash, namespace=self.NAMESPACE)
        )
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


class _OverlayPartyScopeRepository:
    def __init__(
        self,
        *,
        base: PartyScopeRepository,
        organization_id: str,
        proposal: dict[str, str | None],
    ) -> None:
        self._base = base
        self._organization_id = organization_id
        self._proposal = proposal

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
        return {
            **dict(organization),
            "represented_party_id": self._proposal["represented_party_id"],
            "represented_party_perspective": self._proposal[
                "represented_party_perspective"
            ],
        }


class OrganizationPartyScopeService:
    """Build safe previews before committing Organization Party scope changes."""

    def __init__(
        self,
        *,
        preview_store: OrganizationPartyScopePreviewStore | None = None,
        commit_crud: OrganizationPartyScopeCommitCRUD | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC).replace(tzinfo=None))
        self.preview_store = preview_store or OrganizationPartyScopePreviewStore(
            clock=self._clock
        )
        self.commit_crud = commit_crud or organization_party_scope_commit_crud
        self.user_crud = UserCRUD()

    async def preview(
        self,
        db: AsyncSession,
        *,
        organization_id: str,
        proposal: OrganizationPartyScopeProposal,
        actor_id: str,
    ) -> OrganizationPartyScopePreviewResponse:
        analysis = await self._build_preview_analysis(
            db,
            organization_id=organization_id,
            proposal=proposal,
        )
        normalized_proposal = self.proposal_payload(proposal)
        token, expires_at = self.preview_store.issue(
            {
                "actor_id": actor_id,
                "organization_id": organization_id,
                "proposal": normalized_proposal,
                "state_fingerprint": analysis.state_fingerprint,
            }
        )
        return OrganizationPartyScopePreviewResponse(
            organization_id=organization_id,
            before_scope=analysis.before_scope,
            after_scope=analysis.after_scope,
            impact=analysis.impact,
            preview_token=token,
            expires_at=expires_at,
        )

    async def analyze(
        self,
        db: AsyncSession,
        *,
        organization_id: str,
        proposal: OrganizationPartyScopeProposal,
    ) -> OrganizationPartyScopeAnalysis:
        """Validate and calculate a direct Organization Party scope proposal."""
        return await self._build_preview_analysis(
            db,
            organization_id=organization_id,
            proposal=proposal,
        )

    async def commit(
        self,
        db: AsyncSession,
        *,
        organization_id: str,
        request: OrganizationPartyScopeCommitRequest,
        actor_id: str,
    ) -> OrganizationPartyScopeCommitResponse:
        """Commit a current preview exactly once and return its durable receipt."""
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
            raise OrganizationPartyScopePreviewStaleError("missing_or_expired")

        proposal = self._proposal_from_preview_payload(
            preview_payload,
            organization_id=organization_id,
            actor_id=actor_id,
        )
        locked_organization = await organization_crud.get_for_update_async(
            db,
            id=organization_id,
        )
        if locked_organization is None:
            raise ResourceNotFoundError("组织", organization_id)
        self._assert_active_organization(locked_organization)

        analysis = await self._build_preview_analysis(
            db,
            organization_id=organization_id,
            proposal=proposal,
        )
        if preview_payload.get("state_fingerprint") != analysis.state_fingerprint:
            raise OrganizationPartyScopePreviewStaleError("state_changed")

        # A different token may race with this request but carry the same
        # idempotency key. The durable receipt remains the source of truth.
        existing = await self.commit_crud.get_by_idempotency_async(
            db,
            organization_id=organization_id,
            actor_id=actor_id,
            idempotency_key=request.idempotency_key,
        )
        if existing is not None:
            return self._response_from_receipt(existing, idempotent=True)

        committed_at = self._clock()
        proposal_payload = self.proposal_payload(proposal)
        before_scope = analysis.before_scope.model_dump(mode="json")
        after_scope = analysis.after_scope.model_dump(mode="json")
        impact_summary = analysis.impact.model_dump(mode="json")

        setattr(
            locked_organization,
            "represented_party_id",
            proposal_payload["represented_party_id"],
        )
        setattr(
            locked_organization,
            "represented_party_perspective",
            proposal_payload["represented_party_perspective"],
        )
        setattr(locked_organization, "updated_at", committed_at)
        setattr(locked_organization, "updated_by", actor_id)

        history_crud = OrganizationHistoryCRUD()
        await history_crud.create_async(
            db,
            organization_id=organization_id,
            action="party_scope_update",
            field_name="represented_party_scope",
            old_value=json.dumps(before_scope, ensure_ascii=False, sort_keys=True),
            new_value=json.dumps(after_scope, ensure_ascii=False, sort_keys=True),
            change_reason=request.reason,
            created_by=actor_id,
        )

        response = OrganizationPartyScopeCommitResponse(
            organization=OrganizationResponse.model_validate(locked_organization),
            before_scope=analysis.before_scope,
            after_scope=analysis.after_scope,
            impact=analysis.impact,
            committed_at=committed_at,
            idempotent=False,
        )
        result_data = response.model_dump(mode="json")
        await self.commit_crud.create_async(
            db,
            organization_id=organization_id,
            actor_id=actor_id,
            idempotency_key=request.idempotency_key,
            reason=request.reason,
            proposal=proposal_payload,
            before_scope=before_scope,
            after_scope=after_scope,
            impact_summary=impact_summary,
            result_data=result_data,
            committed_at=committed_at,
        )
        await db.commit()
        await db.refresh(locked_organization)
        self.invalidate_caches()
        return response

    @staticmethod
    def _proposal_from_preview_payload(
        payload: dict[str, object],
        *,
        organization_id: str,
        actor_id: str,
    ) -> OrganizationPartyScopeProposal:
        if payload.get("organization_id") != organization_id:
            raise OrganizationPartyScopePreviewStaleError("organization_mismatch")
        if payload.get("actor_id") != actor_id:
            raise OrganizationPartyScopePreviewStaleError("actor_mismatch")

        raw_proposal = payload.get("proposal")
        if not isinstance(raw_proposal, dict):
            raise OrganizationPartyScopePreviewStaleError("proposal_missing")
        try:
            return OrganizationPartyScopeProposal.model_validate(raw_proposal)
        except ValueError as exc:
            raise OrganizationPartyScopePreviewStaleError("proposal_invalid") from exc

    @staticmethod
    def _response_from_receipt(
        receipt: Any,
        *,
        idempotent: bool,
    ) -> OrganizationPartyScopeCommitResponse:
        result_data = getattr(receipt, "result_data", None)
        if not isinstance(result_data, dict):
            raise OrganizationPartyScopePreviewStaleError("receipt_invalid")
        return OrganizationPartyScopeCommitResponse.model_validate(
            {**result_data, "idempotent": idempotent}
        )

    @staticmethod
    def invalidate_caches() -> None:
        cache_manager.clear(namespace="organization")
        invalidate_user_accessible_organizations_cache()

    async def _build_preview_analysis(
        self,
        db: AsyncSession,
        *,
        organization_id: str,
        proposal: OrganizationPartyScopeProposal,
    ) -> OrganizationPartyScopeAnalysis:
        organization = await organization_crud.get_async(
            db,
            id=organization_id,
            use_cache=False,
        )
        if organization is None:
            raise ResourceNotFoundError("组织", organization_id)
        self._assert_active_organization(organization)

        normalized_proposal = self.proposal_payload(proposal)
        proposed_party = await self._validate_proposed_party(
            db,
            represented_party_id=normalized_proposal["represented_party_id"],
        )
        path_to_root = await organization_crud.get_path_to_root_async(
            db,
            org_id=organization_id,
        )
        descendants = await organization_crud.get_children_async(
            db,
            parent_id=organization_id,
            recursive=True,
        )
        organizations = self._deduplicate_organizations(
            [*path_to_root, organization, *descendants]
        )
        organization_by_id = {str(item.id): item for item in organizations}
        subtree = [organization, *descendants]

        before_scope = self._organization_scope_state(
            organization,
            organization_by_id=organization_by_id,
            override=None,
        )
        after_scope = self._organization_scope_state(
            organization,
            organization_by_id=organization_by_id,
            override=(organization_id, normalized_proposal),
        )
        changed_organization_ids = [
            str(item.id)
            for item in subtree
            if self._scope_state_signature(
                self._organization_scope_state(
                    item,
                    organization_by_id=organization_by_id,
                    override=None,
                )
            )
            != self._scope_state_signature(
                self._organization_scope_state(
                    item,
                    organization_by_id=organization_by_id,
                    override=(organization_id, normalized_proposal),
                )
            )
        ]
        users = await self.user_crud.get_active_human_by_organization_ids_async(
            db,
            organization_ids=[str(item.id) for item in subtree],
        )
        (
            user_scope_changes,
            user_scope_signatures,
        ) = await self._count_user_scope_changes(
            db,
            users=users,
            organization_id=organization_id,
            proposal=normalized_proposal,
        )
        impact = OrganizationPartyScopeImpact(
            organization_count=len(subtree),
            organization_scope_change_count=len(changed_organization_ids),
            user_count=len(users),
            user_scope_change_count=user_scope_changes,
        )
        fingerprint = self._state_fingerprint(
            organization_by_id=organization_by_id,
            users=users,
            proposed_party=proposed_party,
            proposal=normalized_proposal,
            before_scope=before_scope,
            after_scope=after_scope,
            impact=impact,
            user_scope_signatures=user_scope_signatures,
        )
        return OrganizationPartyScopeAnalysis(
            before_scope=before_scope,
            after_scope=after_scope,
            impact=impact,
            state_fingerprint=fingerprint,
            user_scope_signatures=user_scope_signatures,
            lock_organization_ids=tuple(sorted(organization_by_id)),
        )

    async def _validate_proposed_party(
        self,
        db: AsyncSession,
        *,
        represented_party_id: str | None,
    ) -> Party | None:
        if represented_party_id is None:
            return None

        party = await party_crud.get_party(db, party_id=represented_party_id)
        if party is None:
            raise ResourceNotFoundError("主体", represented_party_id)
        if (
            party.party_type != PartyType.LEGAL_ENTITY
            or party.review_status != PartyReviewStatus.APPROVED
            or party.status != "active"
        ):
            raise OperationNotAllowedError(
                "组织只能直接代表已审核且启用的法人主体",
                reason="organization_represented_party_invalid",
            )
        return party

    async def _count_user_scope_changes(
        self,
        db: AsyncSession,
        *,
        users: list[Any],
        organization_id: str,
        proposal: dict[str, str | None],
    ) -> tuple[int, tuple[dict[str, object], ...]]:
        now = self._clock()
        base_repository = PartyScopeRepository()
        before_resolver = PartyScopeResolver(
            repository=base_repository,
            clock=lambda: now,
        )
        after_resolver = PartyScopeResolver(
            repository=_OverlayPartyScopeRepository(
                base=base_repository,
                organization_id=organization_id,
                proposal=proposal,
            ),
            clock=lambda: now,
        )
        changed_count = 0
        signatures: list[dict[str, object]] = []
        for user in users:
            user_id = str(user.id)
            before = await before_resolver.resolve(db, user_id=user_id)
            after = await after_resolver.resolve(db, user_id=user_id)
            signatures.append(
                {
                    "user_id": user_id,
                    "before": self._effective_scope_signature(before),
                    "after": self._effective_scope_signature(after),
                }
            )
            if self._effective_scope_signature(
                before
            ) != self._effective_scope_signature(after):
                changed_count += 1
        return changed_count, tuple(signatures)

    @staticmethod
    def _assert_active_organization(organization: Organization) -> None:
        if bool(organization.is_deleted) or str(organization.status) != "active":
            raise OperationNotAllowedError(
                "Only active Organizations can change represented Party scope",
                reason="organization_party_scope_target_invalid",
            )

    @staticmethod
    def proposal_payload(
        proposal: OrganizationPartyScopeProposal,
    ) -> dict[str, str | None]:
        perspective = proposal.represented_party_perspective
        return {
            "represented_party_id": proposal.represented_party_id,
            "represented_party_perspective": (
                str(perspective) if perspective is not None else None
            ),
        }

    @staticmethod
    def _deduplicate_organizations(
        organizations: list[Organization],
    ) -> list[Organization]:
        seen_ids: set[str] = set()
        deduplicated: list[Organization] = []
        for organization in organizations:
            organization_id = str(organization.id)
            if organization_id in seen_ids:
                continue
            seen_ids.add(organization_id)
            deduplicated.append(organization)
        return deduplicated

    @classmethod
    def _organization_scope_state(
        cls,
        organization: Organization,
        *,
        organization_by_id: dict[str, Organization],
        override: tuple[str, dict[str, str | None]] | None,
    ) -> OrganizationPartyScopeState:
        organization_id = str(organization.id)
        override_organization_id = override[0] if override is not None else None
        override_proposal = override[1] if override is not None else None
        direct_party_id, direct_perspective = cls._direct_scope_pair(
            organization,
            override=(
                override_proposal
                if override_organization_id == organization_id
                else None
            ),
        )
        current = organization
        visited: set[str] = set()
        while True:
            current_id = str(current.id)
            if current_id in visited:
                break
            visited.add(current_id)
            party_id, perspective = cls._direct_scope_pair(
                current,
                override=(
                    override_proposal
                    if override_proposal is not None
                    and current_id == override_organization_id
                    else None
                ),
            )
            if party_id is not None and perspective is not None:
                return OrganizationPartyScopeState(
                    represented_party_id=direct_party_id,
                    represented_party_perspective=cls._as_perspective(
                        direct_perspective
                    ),
                    effective_party_id=party_id,
                    effective_party_perspective=cls._as_perspective(perspective),
                    source_organization_id=current_id,
                )
            parent_id = cls._normalize_identifier(getattr(current, "parent_id", None))
            if parent_id is None or parent_id not in organization_by_id:
                break
            current = organization_by_id[parent_id]

        return OrganizationPartyScopeState(
            represented_party_id=direct_party_id,
            represented_party_perspective=cls._as_perspective(direct_perspective),
        )

    @classmethod
    def _direct_scope_pair(
        cls,
        organization: Organization,
        *,
        override: dict[str, str | None] | None,
    ) -> tuple[str | None, str | None]:
        if override is not None:
            return (
                cls._normalize_identifier(override["represented_party_id"]),
                cls._normalize_identifier(override["represented_party_perspective"]),
            )
        return (
            cls._normalize_identifier(
                getattr(organization, "represented_party_id", None)
            ),
            cls._normalize_identifier(
                getattr(organization, "represented_party_perspective", None)
            ),
        )

    @staticmethod
    def _normalize_identifier(value: object | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized if normalized != "" else None

    @staticmethod
    def _as_perspective(
        value: str | None,
    ) -> RepresentedPartyPerspective | None:
        return RepresentedPartyPerspective(value) if value is not None else None

    @staticmethod
    def _scope_state_signature(
        scope: OrganizationPartyScopeState,
    ) -> tuple[str | None, str | None, str | None]:
        return (
            scope.effective_party_id,
            (
                str(scope.effective_party_perspective)
                if scope.effective_party_perspective is not None
                else None
            ),
            scope.source_organization_id,
        )

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

    def _state_fingerprint(
        self,
        *,
        organization_by_id: dict[str, Organization],
        users: list[Any],
        proposed_party: Party | None,
        proposal: dict[str, str | None],
        before_scope: OrganizationPartyScopeState,
        after_scope: OrganizationPartyScopeState,
        impact: OrganizationPartyScopeImpact,
        user_scope_signatures: tuple[dict[str, object], ...],
    ) -> str:
        payload = {
            "proposal": proposal,
            "organizations": [
                {
                    "id": organization_id,
                    "parent_id": self._normalize_identifier(
                        getattr(organization, "parent_id", None)
                    ),
                    "status": str(getattr(organization, "status", "")),
                    "is_deleted": bool(getattr(organization, "is_deleted", False)),
                    "represented_party_id": self._normalize_identifier(
                        getattr(organization, "represented_party_id", None)
                    ),
                    "represented_party_perspective": self._normalize_identifier(
                        getattr(organization, "represented_party_perspective", None)
                    ),
                    "updated_at": self._serialize_datetime(
                        getattr(organization, "updated_at", None)
                    ),
                }
                for organization_id, organization in sorted(organization_by_id.items())
            ],
            "users": [
                {
                    "id": str(user.id),
                    "organization_id": self._normalize_identifier(
                        getattr(user, "organization_id", None)
                    ),
                    "updated_at": self._serialize_datetime(
                        getattr(user, "updated_at", None)
                    ),
                }
                for user in sorted(users, key=lambda item: str(item.id))
            ],
            "proposed_party": (
                {
                    "id": str(proposed_party.id),
                    "party_type": str(proposed_party.party_type),
                    "status": str(proposed_party.status),
                    "review_status": str(proposed_party.review_status),
                    "updated_at": self._serialize_datetime(proposed_party.updated_at),
                }
                if proposed_party is not None
                else None
            ),
            "before_scope": before_scope.model_dump(mode="json"),
            "after_scope": after_scope.model_dump(mode="json"),
            "impact": impact.model_dump(mode="json"),
            "user_scope_signatures": user_scope_signatures,
        }
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _serialize_datetime(value: object | None) -> str | None:
        return value.isoformat() if isinstance(value, datetime) else None


organization_party_scope_service = OrganizationPartyScopeService()

__all__ = [
    "OrganizationPartyScopeAnalysis",
    "OrganizationPartyScopePreviewStore",
    "OrganizationPartyScopeService",
    "organization_party_scope_service",
]
