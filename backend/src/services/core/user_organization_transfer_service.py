"""Sensitive preview/commit flow for human-user organization transfers."""

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
    ResourceNotFoundError,
    ServiceUnavailableError,
    UserOrganizationTransferPreviewStaleError,
)
from ...crud.auth import UserCRUD
from ...crud.organization import organization as organization_crud
from ...crud.user_organization_transfer_commit import (
    UserOrganizationTransferCommitCRUD,
    user_organization_transfer_commit_crud,
)
from ...models.auth import User
from ...schemas.user_organization_transfer import (
    UserOrganizationTransferCommitRequest,
    UserOrganizationTransferCommitResponse,
    UserOrganizationTransferImpact,
    UserOrganizationTransferPreviewResponse,
    UserOrganizationTransferProposal,
)
from ...schemas.user_party_scope import UserPartyScopeIssue, UserPartyScopeState
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
    before_scope: UserPartyScopeState
    after_scope: UserPartyScopeState
    impact: UserOrganizationTransferImpact
    state_fingerprint: str


class UserOrganizationTransferPreviewStore:
    """Short-lived server-side storage for opaque transfer preview tokens."""

    NAMESPACE = "user_organization_transfer_preview"
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
                "Unable to store the user organization transfer preview",
                service_name="user_organization_transfer_preview",
            )
        return token, expires_at

    def consume(self, raw_token: str) -> dict[str, object] | None:
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


class _OverlayUserOrganizationScopeRepository:
    """Resolve the proposed organization without writing it to the user row."""

    def __init__(
        self,
        *,
        base: PartyScopeRepository,
        user_id: str,
        organization_id: str,
    ) -> None:
        self._base = base
        self._user_id = user_id
        self._organization_id = organization_id

    async def load_role_names(
        self, db: AsyncSession, *, user_id: str, now: datetime
    ) -> list[str]:
        return await self._base.load_role_names(db, user_id=user_id, now=now)

    async def load_user(
        self, db: AsyncSession, *, user_id: str
    ) -> Mapping[str, Any] | None:
        user = await self._base.load_user(db, user_id=user_id)
        if user is None or user_id != self._user_id:
            return user
        return {**dict(user), "organization_id": self._organization_id}

    async def load_bindings(
        self, db: AsyncSession, *, user_id: str, now: datetime
    ) -> list[Mapping[str, Any]]:
        return await self._base.load_bindings(db, user_id=user_id, now=now)

    async def load_organization(
        self, db: AsyncSession, *, organization_id: str
    ) -> Mapping[str, Any] | None:
        return await self._base.load_organization(db, organization_id=organization_id)


class UserOrganizationTransferService:
    """Preview and commit one human user's organization transfer atomically."""

    def __init__(
        self,
        *,
        preview_store: UserOrganizationTransferPreviewStore | None = None,
        commit_crud: UserOrganizationTransferCommitCRUD | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC).replace(tzinfo=None))
        self.preview_store = preview_store or UserOrganizationTransferPreviewStore(
            clock=self._clock
        )
        self.commit_crud = commit_crud or user_organization_transfer_commit_crud
        self.user_crud = UserCRUD()

    async def preview(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        proposal: UserOrganizationTransferProposal,
        actor_id: str,
    ) -> UserOrganizationTransferPreviewResponse:
        normalized_proposal = self._proposal_payload(proposal)
        analysis = await self._build_preview_analysis(
            db,
            user_id=user_id,
            proposal=normalized_proposal,
            now=self._clock(),
        )
        token, expires_at = self.preview_store.issue(
            {
                "actor_id": actor_id,
                "user_id": user_id,
                "proposal": normalized_proposal,
                "state_fingerprint": analysis.state_fingerprint,
            }
        )
        return UserOrganizationTransferPreviewResponse(
            user_id=user_id,
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
        user_id: str,
        request: UserOrganizationTransferCommitRequest,
        actor_id: str,
    ) -> UserOrganizationTransferCommitResponse:
        """Commit one current preview exactly once and return its durable receipt."""
        existing = await self.commit_crud.get_by_idempotency_async(
            db,
            user_id=user_id,
            actor_id=actor_id,
            idempotency_key=request.idempotency_key,
        )
        if existing is not None:
            return self._response_from_receipt(existing, idempotent=True)

        preview_payload = self.preview_store.consume(request.preview_token)
        if preview_payload is None:
            raise UserOrganizationTransferPreviewStaleError("missing_or_expired")
        proposal = self._proposal_from_preview_payload(
            preview_payload,
            user_id=user_id,
            actor_id=actor_id,
        )

        locked_user = await self.user_crud.get_for_update_async(db, user_id=user_id)
        if locked_user is None:
            raise ResourceNotFoundError("User", user_id)
        locked_target = await organization_crud.get_for_update_async(
            db,
            id=proposal["organization_id"],
        )
        if locked_target is None:
            raise UserOrganizationTransferPreviewStaleError(
                "target_organization_missing"
            )

        try:
            analysis = await self._build_preview_analysis(
                db,
                user_id=user_id,
                proposal=proposal,
                now=self._clock(),
            )
        except (OperationNotAllowedError, ResourceNotFoundError) as exc:
            raise UserOrganizationTransferPreviewStaleError("state_changed") from exc
        if preview_payload.get("state_fingerprint") != analysis.state_fingerprint:
            raise UserOrganizationTransferPreviewStaleError("state_changed")

        existing = await self.commit_crud.get_by_idempotency_async(
            db,
            user_id=user_id,
            actor_id=actor_id,
            idempotency_key=request.idempotency_key,
        )
        if existing is not None:
            return self._response_from_receipt(existing, idempotent=True)

        committed_at = self._clock()
        locked_user.organization_id = proposal["organization_id"]
        locked_user.updated_at = committed_at
        locked_user.updated_by = actor_id
        response = UserOrganizationTransferCommitResponse(
            user_id=user_id,
            organization_id=proposal["organization_id"],
            before_scope=analysis.before_scope,
            after_scope=analysis.after_scope,
            impact=analysis.impact,
            committed_at=committed_at,
            idempotent=False,
        )
        await self.commit_crud.create_async(
            db,
            user_id=user_id,
            actor_id=actor_id,
            target_organization_id=proposal["organization_id"],
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
        await db.refresh(locked_user)
        invalidate_user_accessible_organizations_cache(user_id)
        await party_service._publish_user_scope_invalidation(user_id)
        return response

    async def _build_preview_analysis(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        proposal: dict[str, str],
        now: datetime,
    ) -> _PreviewAnalysis:
        user = await self.user_crud.get_async(db, user_id)
        if user is None:
            raise ResourceNotFoundError("User", user_id)
        self._assert_human_user(user)

        current_organization_id = _normalize_identifier(user.organization_id)
        if current_organization_id == proposal["organization_id"]:
            raise OperationNotAllowedError(
                "The user is already assigned to the target organization",
                reason="user_organization_transfer_no_change",
            )

        base_repository = PartyScopeRepository()
        target_chain = await self._load_organization_chain(
            db,
            repository=base_repository,
            organization_id=proposal["organization_id"],
            require_active=True,
        )
        source_chain = await self._load_organization_chain(
            db,
            repository=base_repository,
            organization_id=current_organization_id,
            require_active=False,
        )

        before_resolver = PartyScopeResolver(
            repository=base_repository,
            clock=lambda: now,
        )
        after_resolver = PartyScopeResolver(
            repository=_OverlayUserOrganizationScopeRepository(
                base=base_repository,
                user_id=user_id,
                organization_id=proposal["organization_id"],
            ),
            clock=lambda: now,
        )
        before_effective = await before_resolver.resolve(db, user_id=user_id)
        after_effective = await after_resolver.resolve(db, user_id=user_id)
        before_scope = self._scope_state(before_effective)
        after_scope = self._scope_state(after_effective)
        if after_scope.error_code is not None:
            raise OperationNotAllowedError(
                "The target organization does not resolve to an effective Party scope",
                reason="user_organization_transfer_scope_invalid",
            )

        bindings = await base_repository.load_bindings(db, user_id=user_id, now=now)
        role_names = await base_repository.load_role_names(db, user_id=user_id, now=now)
        impact = UserOrganizationTransferImpact(
            organization_changed=True,
            scope_changed=self._scope_signature(before_scope)
            != self._scope_signature(after_scope),
            current_explicit_binding_count=self._current_binding_count(
                bindings, now=now
            ),
            uses_explicit_party_scope_after=after_scope.source == "explicit",
            cache_invalidation_required=True,
        )
        fingerprint = self._state_fingerprint(
            user=user,
            proposal=proposal,
            source_chain=source_chain,
            target_chain=target_chain,
            bindings=bindings,
            role_names=role_names,
            before_scope=before_scope,
            after_scope=after_scope,
            impact=impact,
        )
        return _PreviewAnalysis(
            before_scope=before_scope,
            after_scope=after_scope,
            impact=impact,
            state_fingerprint=fingerprint,
        )

    @staticmethod
    def _proposal_from_preview_payload(
        payload: dict[str, object],
        *,
        user_id: str,
        actor_id: str,
    ) -> dict[str, str]:
        if payload.get("user_id") != user_id:
            raise UserOrganizationTransferPreviewStaleError("user_mismatch")
        if payload.get("actor_id") != actor_id:
            raise UserOrganizationTransferPreviewStaleError("actor_mismatch")
        raw_proposal = payload.get("proposal")
        if not isinstance(raw_proposal, dict):
            raise UserOrganizationTransferPreviewStaleError("proposal_missing")
        try:
            proposal = UserOrganizationTransferProposal.model_validate(raw_proposal)
        except ValueError as exc:
            raise UserOrganizationTransferPreviewStaleError("proposal_invalid") from exc
        return UserOrganizationTransferService._proposal_payload(proposal)

    @staticmethod
    def _proposal_payload(
        proposal: UserOrganizationTransferProposal,
    ) -> dict[str, str]:
        return {"organization_id": proposal.organization_id}

    @staticmethod
    def _response_from_receipt(
        receipt: Any,
        *,
        idempotent: bool,
    ) -> UserOrganizationTransferCommitResponse:
        result_data = getattr(receipt, "result_data", None)
        if not isinstance(result_data, dict):
            raise UserOrganizationTransferPreviewStaleError("receipt_invalid")
        return UserOrganizationTransferCommitResponse.model_validate(
            {**result_data, "idempotent": idempotent}
        )

    async def _load_organization_chain(
        self,
        db: AsyncSession,
        *,
        repository: PartyScopeRepository,
        organization_id: str | None,
        require_active: bool,
    ) -> list[dict[str, object]]:
        if organization_id is None:
            return []

        snapshots: list[dict[str, object]] = []
        current_id: str | None = organization_id
        visited: set[str] = set()
        while current_id is not None:
            if current_id in visited:
                if require_active:
                    raise OperationNotAllowedError(
                        "The target organization hierarchy contains a cycle",
                        reason="user_organization_transfer_target_chain_invalid",
                    )
                snapshots.append({"id": current_id, "cycle": True})
                break
            visited.add(current_id)
            record = await repository.load_organization(
                db,
                organization_id=current_id,
            )
            if record is None:
                if require_active and len(snapshots) == 0:
                    raise ResourceNotFoundError("Organization", organization_id)
                if require_active:
                    raise OperationNotAllowedError(
                        "The target organization hierarchy is incomplete",
                        reason="user_organization_transfer_target_chain_invalid",
                    )
                snapshots.append({"id": current_id, "missing": True})
                break

            snapshot = self._organization_snapshot(record)
            snapshots.append(snapshot)
            if require_active and (
                snapshot["status"] != "active" or snapshot["is_deleted"] is True
            ):
                raise OperationNotAllowedError(
                    "The target organization hierarchy must be active",
                    reason="user_organization_transfer_target_chain_invalid",
                )
            current_id = _normalize_identifier(record.get("parent_id"))
        return snapshots

    @staticmethod
    def _organization_snapshot(record: Mapping[str, Any]) -> dict[str, object]:
        return {
            "id": _normalize_identifier(record.get("id")),
            "parent_id": _normalize_identifier(record.get("parent_id")),
            "status": _normalize_enum(record.get("status")),
            "is_deleted": bool(record.get("is_deleted")),
            "represented_party_id": _normalize_identifier(
                record.get("represented_party_id")
            ),
            "represented_party_perspective": _normalize_enum(
                record.get("represented_party_perspective")
            ),
            "party_type": _normalize_enum(record.get("party_type")),
            "party_status": _normalize_enum(record.get("party_status")),
            "party_review_status": _normalize_enum(record.get("party_review_status")),
        }

    @staticmethod
    def _assert_human_user(user: User) -> None:
        if _normalize_enum(user.account_type) != "human":
            raise OperationNotAllowedError(
                "Only human users can be transferred between organizations",
                reason="user_organization_transfer_account_type_invalid",
            )

    @staticmethod
    def _scope_state(scope: EffectivePartyScope) -> UserPartyScopeState:
        return UserPartyScopeState(
            source=scope.source,
            scope_mode=scope.scope_mode,
            owner_party_ids=scope.owner_party_ids,
            manager_party_ids=scope.manager_party_ids,
            organization_id=scope.organization_id,
            source_organization_id=scope.source_organization_id,
            next_transition_at=scope.next_transition_at,
            error_code=scope.error_code,
            issues=[
                UserPartyScopeIssue(
                    code=issue.code,
                    node_type=issue.node_type,
                    safe_label=issue.safe_label,
                    node_ref=issue.node_ref,
                )
                for issue in scope.issues
            ],
        )

    @staticmethod
    def _scope_signature(scope: UserPartyScopeState) -> tuple[object, ...]:
        return (
            scope.source,
            scope.scope_mode,
            tuple(scope.owner_party_ids),
            tuple(scope.manager_party_ids),
            scope.source_organization_id,
            scope.error_code,
        )

    @staticmethod
    def _current_binding_count(
        bindings: list[Mapping[str, Any]],
        *,
        now: datetime,
    ) -> int:
        return sum(
            1
            for binding in bindings
            if PartyScopeResolver._is_current_binding(binding, now=now)
        )

    def _state_fingerprint(
        self,
        *,
        user: User,
        proposal: dict[str, str],
        source_chain: list[dict[str, object]],
        target_chain: list[dict[str, object]],
        bindings: list[Mapping[str, Any]],
        role_names: list[str],
        before_scope: UserPartyScopeState,
        after_scope: UserPartyScopeState,
        impact: UserOrganizationTransferImpact,
    ) -> str:
        payload = {
            "user": {
                "id": str(user.id),
                "account_type": _normalize_enum(user.account_type),
                "organization_id": _normalize_identifier(user.organization_id),
                "is_active": bool(user.is_active),
                "updated_at": _serialize_datetime(user.updated_at),
            },
            "proposal": proposal,
            "source_organization_chain": source_chain,
            "target_organization_chain": target_chain,
            "bindings": [
                {
                    "id": _normalize_identifier(binding.get("id")),
                    "party_id": _normalize_identifier(binding.get("party_id")),
                    "relation_type": _normalize_enum(binding.get("relation_type")),
                    "valid_from": _serialize_datetime(binding.get("valid_from")),
                    "valid_to": _serialize_datetime(binding.get("valid_to")),
                    "party_status": _normalize_enum(binding.get("party_status")),
                    "party_review_status": _normalize_enum(
                        binding.get("party_review_status")
                    ),
                }
                for binding in bindings
            ],
            "roles": sorted({str(role_name).strip() for role_name in role_names}),
            "before_scope": before_scope.model_dump(mode="json"),
            "after_scope": after_scope.model_dump(mode="json"),
            "impact": impact.model_dump(mode="json"),
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _normalize_identifier(value: object | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized if normalized != "" else None


def _normalize_enum(value: object | None) -> str | None:
    return _normalize_identifier(getattr(value, "value", value))


def _serialize_datetime(value: object | None) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


user_organization_transfer_service = UserOrganizationTransferService()

__all__ = [
    "UserOrganizationTransferPreviewStore",
    "UserOrganizationTransferService",
    "user_organization_transfer_service",
]
