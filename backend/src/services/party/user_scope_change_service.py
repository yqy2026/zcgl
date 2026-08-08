"""Sensitive explicit user Party-scope changes."""

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
    UserPartyScopePreviewStaleError,
)
from ...crud.auth import UserCRUD
from ...crud.party import party_crud
from ...crud.user_party_scope_commit import (
    UserPartyScopeCommitCRUD,
    user_party_scope_commit_crud,
)
from ...models.auth import User
from ...models.party import Party, PartyReviewStatus
from ...models.user_party_binding import UserPartyBinding
from ...schemas.party import UserPartyBindingResponse
from ...schemas.user_party_scope import (
    UserPartyBindingScopeProposal,
    UserPartyScopeCommitRequest,
    UserPartyScopeCommitResponse,
    UserPartyScopeImpact,
    UserPartyScopeIssue,
    UserPartyScopePreviewResponse,
    UserPartyScopeState,
)
from ..party_scope_resolver import (
    EffectivePartyScope,
    PartyScopeRepository,
    PartyScopeResolver,
)
from .service import party_service


@dataclass(frozen=True)
class _PreviewAnalysis:
    before_scope: UserPartyScopeState
    after_scope: UserPartyScopeState
    impact: UserPartyScopeImpact
    state_fingerprint: str


class UserPartyScopePreviewStore:
    """Short-lived server-side storage for opaque user scope preview tokens."""

    NAMESPACE = "user_party_scope_preview"
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
                "Unable to store the user Party scope preview",
                service_name="user_party_scope_preview",
            )
        return token, expires_at

    def consume(self, raw_token: str) -> dict[str, object] | None:
        """Consume a preview token exactly once."""
        return self._load(raw_token, consume=True)

    def peek(self, raw_token: str) -> dict[str, object] | None:
        """Read a still-valid token without consuming it."""
        return self._load(raw_token, consume=False)

    def _load(
        self,
        raw_token: str,
        *,
        consume: bool,
    ) -> dict[str, object] | None:
        token = str(raw_token).strip()
        if token == "":
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


class _OverlayUserPartyScopeRepository:
    """Evaluate normalized binding proposals without writing them."""

    def __init__(
        self,
        *,
        base: PartyScopeRepository,
        user_id: str,
        proposals: list[dict[str, Any]],
        proposed_parties: list[Party],
    ) -> None:
        self._base = base
        self._user_id = user_id
        self._proposals = proposals
        self._proposed_party_by_id = {
            str(party.id): party for party in proposed_parties
        }

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
        bindings = [
            dict(binding)
            for binding in await self._base.load_bindings(
                db,
                user_id=user_id,
                now=now,
            )
        ]
        if user_id != self._user_id:
            return list(bindings)

        proposal_by_binding_id = {
            proposal["binding_id"]: proposal
            for proposal in self._proposals
            if proposal["binding_id"] is not None
        }
        updated_bindings: list[Mapping[str, Any]] = []
        for binding in bindings:
            binding_id = str(binding.get("id"))
            if binding_id not in proposal_by_binding_id:
                updated_bindings.append(binding)
                continue

            proposal = proposal_by_binding_id[binding_id]
            updated = dict(binding)
            if proposal["operation"] == "update":
                updated.update(
                    {
                        "party_id": proposal["party_id"],
                        "relation_type": proposal["relation_type"],
                        "valid_from": proposal["valid_from"],
                        "valid_to": proposal["valid_to"],
                        "party_status": self._party_status(proposal),
                        "party_review_status": self._party_review_status(proposal),
                    }
                )
            else:
                updated["valid_to"] = proposal["valid_to"]
            updated_bindings.append(updated)

        for proposal in self._proposals:
            if proposal["operation"] != "create":
                continue
            updated_bindings.append(self._new_binding_mapping(proposal))
        return list(updated_bindings)

    async def load_organization(
        self, db: AsyncSession, *, organization_id: str
    ) -> Mapping[str, Any] | None:
        return await self._base.load_organization(db, organization_id=organization_id)

    def _new_binding_mapping(self, proposal: dict[str, Any]) -> Mapping[str, Any]:
        return {
            "id": "__user_party_scope_preview__",
            "party_id": proposal["party_id"],
            "relation_type": proposal["relation_type"],
            "valid_from": proposal["valid_from"],
            "valid_to": proposal["valid_to"],
            "party_status": self._party_status(proposal),
            "party_review_status": self._party_review_status(proposal),
        }

    def _party_status(self, proposal: dict[str, Any]) -> str | None:
        return _normalize_enum(
            getattr(
                self._proposed_party_by_id.get(str(proposal["party_id"])),
                "status",
                None,
            )
        )

    def _party_review_status(self, proposal: dict[str, Any]) -> str | None:
        return _normalize_enum(
            getattr(
                self._proposed_party_by_id.get(str(proposal["party_id"])),
                "review_status",
                None,
            )
        )


class UserPartyScopeChangeService:
    """Preview and commit one explicit user Party binding atomically."""

    def __init__(
        self,
        *,
        preview_store: UserPartyScopePreviewStore | None = None,
        commit_crud: UserPartyScopeCommitCRUD | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC).replace(tzinfo=None))
        self.preview_store = preview_store or UserPartyScopePreviewStore(
            clock=self._clock
        )
        self.commit_crud = commit_crud or user_party_scope_commit_crud
        self.user_crud = UserCRUD()

    async def preview(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        proposal: UserPartyBindingScopeProposal,
        actor_id: str,
    ) -> UserPartyScopePreviewResponse:
        now = self._clock()
        normalized_proposal = await self._normalize_proposal(
            db,
            user_id=user_id,
            proposal=proposal,
            now=now,
        )
        analysis = await self._build_preview_analysis(
            db,
            user_id=user_id,
            proposals=[normalized_proposal],
            now=now,
        )
        token, expires_at = self.preview_store.issue(
            {
                "actor_id": actor_id,
                "user_id": user_id,
                "proposal": self._serialize_proposal(normalized_proposal),
                "state_fingerprint": analysis.state_fingerprint,
            }
        )
        return UserPartyScopePreviewResponse(
            user_id=user_id,
            operation=normalized_proposal["operation"],
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
        request: UserPartyScopeCommitRequest,
        actor_id: str,
    ) -> UserPartyScopeCommitResponse:
        """Commit a current preview exactly once and return its receipt."""
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
            raise UserPartyScopePreviewStaleError("missing_or_expired")
        normalized_proposal = self._proposal_from_preview_payload(
            preview_payload,
            user_id=user_id,
            actor_id=actor_id,
        )

        locked_user = await self.user_crud.get_for_update_async(db, user_id=user_id)
        if locked_user is None:
            raise ResourceNotFoundError("用户", user_id)

        locked_binding: UserPartyBinding | None = None
        if normalized_proposal["operation"] != "create":
            locked_binding = await party_crud.get_user_binding_for_update(
                db,
                user_id=user_id,
                binding_id=normalized_proposal["binding_id"],
            )
            if locked_binding is None:
                raise ResourceNotFoundError(
                    "用户主体绑定",
                    normalized_proposal["binding_id"],
                )

        analysis = await self._build_preview_analysis(
            db,
            user_id=user_id,
            proposals=[normalized_proposal],
            now=self._clock(),
        )
        if preview_payload.get("state_fingerprint") != analysis.state_fingerprint:
            raise UserPartyScopePreviewStaleError("state_changed")

        existing = await self.commit_crud.get_by_idempotency_async(
            db,
            user_id=user_id,
            actor_id=actor_id,
            idempotency_key=request.idempotency_key,
        )
        if existing is not None:
            return self._response_from_receipt(existing, idempotent=True)

        committed_at = self._clock()
        binding = await self._write_binding(
            db,
            user_id=user_id,
            proposal=normalized_proposal,
            locked_binding=locked_binding,
        )
        response = UserPartyScopeCommitResponse(
            binding=UserPartyBindingResponse.model_validate(binding),
            operation=normalized_proposal["operation"],
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
            idempotency_key=request.idempotency_key,
            reason=request.reason,
            proposal=self._serialize_proposal(normalized_proposal),
            before_scope=analysis.before_scope.model_dump(mode="json"),
            after_scope=analysis.after_scope.model_dump(mode="json"),
            impact_summary=analysis.impact.model_dump(mode="json"),
            result_data=response.model_dump(mode="json"),
            committed_at=committed_at,
        )
        await db.commit()
        await db.refresh(binding)
        await party_service._publish_user_scope_invalidation(user_id)
        return response

    async def _normalize_proposal(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        proposal: UserPartyBindingScopeProposal,
        now: datetime,
    ) -> dict[str, Any]:
        user = await self.user_crud.get_async(db, user_id)
        if user is None:
            raise ResourceNotFoundError("用户", user_id)

        if proposal.operation == "create":
            valid_from = proposal.valid_from or now
            normalized: dict[str, Any] = {
                "operation": "create",
                "binding_id": None,
                "party_id": proposal.party_id,
                "relation_type": _normalize_enum(proposal.relation_type),
                "valid_from": valid_from,
                "valid_to": proposal.valid_to,
            }
        else:
            binding = await party_crud.get_user_binding(
                db,
                user_id=user_id,
                binding_id=str(proposal.binding_id),
            )
            if binding is None:
                raise ResourceNotFoundError("用户主体绑定", str(proposal.binding_id))
            if binding.valid_to is not None and binding.valid_to < now:
                raise OperationNotAllowedError(
                    "已失效的用户主体绑定不能再变更",
                    reason="user_party_binding_already_closed",
                )

            if proposal.operation == "close":
                close_time = now if binding.valid_from <= now else binding.valid_from
                normalized = {
                    "operation": "close",
                    "binding_id": str(binding.id),
                    "party_id": str(binding.party_id),
                    "relation_type": _normalize_enum(binding.relation_type),
                    "valid_from": binding.valid_from,
                    "valid_to": close_time,
                }
            else:
                fields = proposal.model_fields_set
                normalized = {
                    "operation": "update",
                    "binding_id": str(binding.id),
                    "party_id": (
                        proposal.party_id
                        if "party_id" in fields
                        else str(binding.party_id)
                    ),
                    "relation_type": (
                        _normalize_enum(proposal.relation_type)
                        if "relation_type" in fields
                        else _normalize_enum(binding.relation_type)
                    ),
                    "valid_from": (
                        proposal.valid_from
                        if "valid_from" in fields
                        else binding.valid_from
                    ),
                    "valid_to": (
                        proposal.valid_to if "valid_to" in fields else binding.valid_to
                    ),
                }

        self._validate_valid_range(normalized)
        if normalized["operation"] != "close":
            await self._validate_target_party(
                db,
                party_id=normalized["party_id"],
            )
        return normalized

    async def _build_preview_analysis(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        proposals: list[dict[str, Any]],
        now: datetime,
    ) -> _PreviewAnalysis:
        user = await self.user_crud.get_async(db, user_id)
        if user is None:
            raise ResourceNotFoundError("用户", user_id)

        if not proposals:
            raise OperationNotAllowedError(
                "用户主体范围变更必须包含至少一条提案",
                reason="user_party_scope_batch_empty",
            )

        proposed_parties: list[Party] = []
        proposed_party_ids = {
            party_id
            for proposal in proposals
            if proposal["operation"] != "close"
            for party_id in [proposal["party_id"]]
            if isinstance(party_id, str) and party_id != ""
        }
        for party_id in sorted(proposed_party_ids):
            proposed_parties.append(
                await self._validate_target_party(
                    db,
                    party_id=party_id,
                )
            )

        base_repository = PartyScopeRepository()
        before_resolver = PartyScopeResolver(
            repository=base_repository,
            clock=lambda: now,
        )
        after_time = (
            now + timedelta(microseconds=1)
            if any(proposal["operation"] == "close" for proposal in proposals)
            else now
        )
        after_repository = _OverlayUserPartyScopeRepository(
            base=base_repository,
            user_id=user_id,
            proposals=proposals,
            proposed_parties=proposed_parties,
        )
        after_resolver = PartyScopeResolver(
            repository=after_repository,
            clock=lambda: after_time,
        )
        before_effective = await before_resolver.resolve(db, user_id=user_id)
        after_effective = await after_resolver.resolve(db, user_id=user_id)
        before_scope = self._scope_state(before_effective)
        after_scope = self._scope_state(after_effective)

        before_bindings = await base_repository.load_bindings(
            db,
            user_id=user_id,
            now=now,
        )
        after_bindings = await after_repository.load_bindings(
            db,
            user_id=user_id,
            now=after_time,
        )
        before_current_binding_count = self._current_binding_count(
            before_bindings,
            now=now,
        )
        after_current_binding_count = self._current_binding_count(
            after_bindings,
            now=after_time,
        )
        impact = UserPartyScopeImpact(
            before_current_binding_count=before_current_binding_count,
            after_current_binding_count=after_current_binding_count,
            scope_changed=self._scope_signature(before_scope)
            != self._scope_signature(after_scope),
            uses_organization_default_after=after_scope.source == "organization",
        )
        all_bindings = await party_crud.get_user_bindings(
            db,
            user_id=user_id,
            active_only=False,
        )
        role_names = await base_repository.load_role_names(
            db,
            user_id=user_id,
            now=now,
        )
        fingerprint = self._state_fingerprint(
            user=user,
            bindings=all_bindings,
            role_names=role_names,
            proposed_parties=proposed_parties,
            proposals=proposals,
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

    async def _write_binding(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        proposal: dict[str, Any],
        locked_binding: UserPartyBinding | None,
    ) -> UserPartyBinding:
        if proposal["operation"] == "create":
            return await party_crud.create_user_party_binding(
                db,
                obj_in={
                    "user_id": user_id,
                    "party_id": proposal["party_id"],
                    "relation_type": proposal["relation_type"],
                    "valid_from": proposal["valid_from"],
                    "valid_to": proposal["valid_to"],
                },
                commit=False,
            )
        if locked_binding is None:
            raise UserPartyScopePreviewStaleError("binding_missing")

        payload = {"valid_to": proposal["valid_to"]}
        if proposal["operation"] == "update":
            payload = {
                "party_id": proposal["party_id"],
                "relation_type": proposal["relation_type"],
                "valid_from": proposal["valid_from"],
                "valid_to": proposal["valid_to"],
            }
        return await party_crud.update_user_party_binding(
            db,
            db_obj=locked_binding,
            obj_in=payload,
            commit=False,
        )

    @staticmethod
    def _proposal_from_preview_payload(
        payload: dict[str, object],
        *,
        user_id: str,
        actor_id: str,
    ) -> dict[str, Any]:
        if payload.get("user_id") != user_id:
            raise UserPartyScopePreviewStaleError("user_mismatch")
        if payload.get("actor_id") != actor_id:
            raise UserPartyScopePreviewStaleError("actor_mismatch")
        raw_proposal = payload.get("proposal")
        if not isinstance(raw_proposal, dict):
            raise UserPartyScopePreviewStaleError("proposal_missing")

        operation = str(raw_proposal.get("operation", "")).strip()
        if operation not in {"create", "update", "close"}:
            raise UserPartyScopePreviewStaleError("proposal_invalid")
        binding_id = _normalize_identifier(raw_proposal.get("binding_id"))
        party_id = _normalize_identifier(raw_proposal.get("party_id"))
        relation_type = _normalize_enum(raw_proposal.get("relation_type"))
        valid_from = _deserialize_datetime(raw_proposal.get("valid_from"))
        valid_to = _deserialize_datetime(raw_proposal.get("valid_to"), allow_none=True)
        if (
            party_id is None
            or relation_type not in {"owner", "manager"}
            or valid_from is None
        ):
            raise UserPartyScopePreviewStaleError("proposal_invalid")
        if operation == "create" and binding_id is not None:
            raise UserPartyScopePreviewStaleError("proposal_invalid")
        if operation in {"update", "close"} and binding_id is None:
            raise UserPartyScopePreviewStaleError("proposal_invalid")
        if valid_to is not None and valid_to < valid_from:
            raise UserPartyScopePreviewStaleError("proposal_invalid")
        return {
            "operation": operation,
            "binding_id": binding_id,
            "party_id": party_id,
            "relation_type": relation_type,
            "valid_from": valid_from,
            "valid_to": valid_to,
        }

    @staticmethod
    def _serialize_proposal(proposal: dict[str, Any]) -> dict[str, object]:
        return {
            "operation": proposal["operation"],
            "binding_id": proposal["binding_id"],
            "party_id": proposal["party_id"],
            "relation_type": proposal["relation_type"],
            "valid_from": _serialize_datetime(proposal["valid_from"]),
            "valid_to": _serialize_datetime(proposal["valid_to"]),
        }

    @classmethod
    def _serialize_proposals(
        cls,
        proposals: list[dict[str, Any]],
    ) -> list[dict[str, object]]:
        return [cls._serialize_proposal(proposal) for proposal in proposals]

    @staticmethod
    def _response_from_receipt(
        receipt: Any,
        *,
        idempotent: bool,
    ) -> UserPartyScopeCommitResponse:
        result_data = getattr(receipt, "result_data", None)
        if not isinstance(result_data, dict):
            raise UserPartyScopePreviewStaleError("receipt_invalid")
        return UserPartyScopeCommitResponse.model_validate(
            {**result_data, "idempotent": idempotent}
        )

    async def _validate_target_party(
        self,
        db: AsyncSession,
        *,
        party_id: str,
    ) -> Party:
        party = await party_crud.get_party(db, party_id=party_id)
        if party is None:
            raise ResourceNotFoundError("主体", party_id)
        if (
            _normalize_enum(party.status) != "active"
            or party.review_status != PartyReviewStatus.APPROVED
        ):
            raise OperationNotAllowedError(
                "用户主体范围只能指向已审核且启用的主体",
                reason="user_party_scope_target_invalid",
            )
        return party

    @staticmethod
    def _validate_valid_range(proposal: dict[str, Any]) -> None:
        valid_from = proposal["valid_from"]
        valid_to = proposal["valid_to"]
        if valid_to is not None and valid_to < valid_from:
            raise OperationNotAllowedError(
                "用户主体绑定的失效时间不能早于生效时间",
                reason="user_party_binding_invalid_time_range",
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

    def _state_fingerprint(
        self,
        *,
        user: User,
        bindings: list[UserPartyBinding],
        role_names: list[str],
        proposed_parties: list[Party],
        proposals: list[dict[str, Any]],
        before_scope: UserPartyScopeState,
        after_scope: UserPartyScopeState,
        impact: UserPartyScopeImpact,
    ) -> str:
        payload = {
            "user": {
                "id": str(user.id),
                "account_type": _normalize_enum(getattr(user, "account_type", None)),
                "organization_id": _normalize_identifier(
                    getattr(user, "organization_id", None)
                ),
                "updated_at": _serialize_datetime(getattr(user, "updated_at", None)),
            },
            "bindings": [
                {
                    "id": str(binding.id),
                    "party_id": str(binding.party_id),
                    "relation_type": _normalize_enum(binding.relation_type),
                    "valid_from": _serialize_datetime(binding.valid_from),
                    "valid_to": _serialize_datetime(binding.valid_to),
                    "updated_at": _serialize_datetime(binding.updated_at),
                }
                for binding in sorted(bindings, key=lambda item: str(item.id))
            ],
            "roles": sorted({str(role_name).strip() for role_name in role_names}),
            "proposed_parties": [
                {
                    "id": str(party.id),
                    "status": _normalize_enum(party.status),
                    "review_status": _normalize_enum(party.review_status),
                    "updated_at": _serialize_datetime(party.updated_at),
                }
                for party in proposed_parties
            ],
            "proposals": [self._serialize_proposal(proposal) for proposal in proposals],
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


def _deserialize_datetime(
    value: object | None,
    *,
    allow_none: bool = False,
) -> datetime | None:
    if value is None:
        return None if allow_none else None
    if not isinstance(value, str):
        raise UserPartyScopePreviewStaleError("proposal_invalid")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise UserPartyScopePreviewStaleError("proposal_invalid") from exc


user_party_scope_change_service = UserPartyScopeChangeService()

__all__ = [
    "UserPartyScopeChangeService",
    "UserPartyScopePreviewStore",
    "user_party_scope_change_service",
]
