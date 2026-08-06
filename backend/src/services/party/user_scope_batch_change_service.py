"""Preview and commit all-or-nothing explicit user Party-scope batches."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import (
    OperationNotAllowedError,
    ResourceNotFoundError,
    UserPartyScopePreviewStaleError,
)
from ...crud.auth import UserCRUD
from ...crud.party import party_crud
from ...crud.user_party_scope_batch_commit import (
    UserPartyScopeBatchCommitCRUD,
    user_party_scope_batch_commit_crud,
)
from ...models.auth import User
from ...models.user_party_binding import UserPartyBinding
from ...schemas.user_party_scope import (
    UserPartyScopeBatchCommitRequest,
    UserPartyScopeBatchCommitResponse,
    UserPartyScopeBatchImpact,
    UserPartyScopeBatchPreviewItem,
    UserPartyScopeBatchPreviewRequest,
    UserPartyScopeBatchPreviewResponse,
    UserPartyScopeBatchProposal,
    UserPartyScopeBatchUser,
)
from .service import party_service
from .user_scope_change_service import (
    UserPartyScopeChangeService,
    UserPartyScopePreviewStore,
    user_party_scope_change_service,
)


@dataclass(frozen=True)
class _BatchItem:
    user: User
    operation: Literal["create", "update", "close"]
    proposals: list[dict[str, Any]]
    analysis: Any


@dataclass(frozen=True)
class _BatchAnalysis:
    items: tuple[_BatchItem, ...]
    impact: UserPartyScopeBatchImpact
    state_fingerprint: str
    lock_user_ids: tuple[str, ...]
    lock_binding_ids: tuple[str, ...]
    analysis_now: datetime


class UserPartyScopeBatchPreviewStore(UserPartyScopePreviewStore):
    """Dedicated token namespace so single and batch previews cannot mix."""

    NAMESPACE = "user_party_scope_batch_preview"


class UserPartyScopeBatchChangeService:
    """Batch explicit user Party-binding changes as one transaction."""

    def __init__(
        self,
        *,
        preview_store: UserPartyScopeBatchPreviewStore | None = None,
        commit_crud: UserPartyScopeBatchCommitCRUD | None = None,
        single_service: UserPartyScopeChangeService | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC).replace(tzinfo=None))
        self.preview_store = preview_store or UserPartyScopeBatchPreviewStore(
            clock=self._clock
        )
        self.commit_crud = commit_crud or user_party_scope_batch_commit_crud
        self.single_service = single_service or user_party_scope_change_service
        self.user_crud = UserCRUD()

    async def preview(
        self,
        db: AsyncSession,
        *,
        request: UserPartyScopeBatchPreviewRequest,
        actor_id: str,
    ) -> UserPartyScopeBatchPreviewResponse:
        analysis = await self._build_preview_analysis(db, items=request.items)
        proposal_payload = self._proposal_payload(request.items)
        token, expires_at = self.preview_store.issue(
            {
                "actor_id": actor_id,
                "proposal": proposal_payload,
                "state_fingerprint": analysis.state_fingerprint,
                "previewed_at": analysis.analysis_now.isoformat(),
            }
        )
        return UserPartyScopeBatchPreviewResponse(
            items=self._response_items(analysis.items),
            impact=analysis.impact,
            preview_token=token,
            expires_at=expires_at,
        )

    def get_preview_user_ids(
        self,
        *,
        preview_token: str,
        actor_id: str,
    ) -> tuple[str, ...]:
        payload = self.preview_store.peek(preview_token)
        if payload is None:
            raise UserPartyScopePreviewStaleError("missing_or_expired")
        return self._user_ids_from_payload(payload, actor_id=actor_id)

    async def get_commit_user_ids(
        self,
        db: AsyncSession,
        *,
        request: UserPartyScopeBatchCommitRequest,
        actor_id: str,
    ) -> tuple[str, ...]:
        existing = await self.commit_crud.get_by_idempotency_async(
            db,
            actor_id=actor_id,
            idempotency_key=request.idempotency_key,
        )
        if existing is not None:
            return self._user_ids_from_receipt(existing)
        return self.get_preview_user_ids(
            preview_token=request.preview_token,
            actor_id=actor_id,
        )

    async def commit(
        self,
        db: AsyncSession,
        *,
        request: UserPartyScopeBatchCommitRequest,
        actor_id: str,
    ) -> UserPartyScopeBatchCommitResponse:
        existing = await self.commit_crud.get_by_idempotency_async(
            db,
            actor_id=actor_id,
            idempotency_key=request.idempotency_key,
        )
        if existing is not None:
            return self._response_from_receipt(existing, idempotent=True)

        preview_payload = self.preview_store.consume(request.preview_token)
        if preview_payload is None:
            raise UserPartyScopePreviewStaleError("missing_or_expired")
        items = self._proposals_from_preview_payload(
            preview_payload,
            actor_id=actor_id,
        )
        previewed_at = _deserialize_datetime(
            preview_payload.get("previewed_at"),
            allow_none=True,
        )
        if previewed_at is None:
            raise UserPartyScopePreviewStaleError("preview_invalid")

        try:
            initial_analysis = await self._build_preview_analysis(
                db,
                items=items,
                now=previewed_at,
            )
            locked_users = await self._lock_users(
                db,
                initial_analysis.lock_user_ids,
            )
            locked_bindings = await self._lock_bindings(
                db,
                initial_analysis.lock_binding_ids,
            )
            analysis = await self._build_preview_analysis(
                db,
                items=items,
                now=previewed_at,
            )
        except (OperationNotAllowedError, ResourceNotFoundError) as exc:
            raise UserPartyScopePreviewStaleError("state_changed") from exc

        if preview_payload.get("state_fingerprint") != analysis.state_fingerprint:
            raise UserPartyScopePreviewStaleError("state_changed")

        existing = await self.commit_crud.get_by_idempotency_async(
            db,
            actor_id=actor_id,
            idempotency_key=request.idempotency_key,
        )
        if existing is not None:
            return self._response_from_receipt(existing, idempotent=True)

        committed_at = self._clock()
        for item in analysis.items:
            user_id = str(item.user.id)
            for proposal in item.proposals:
                await self.single_service._write_binding(
                    db,
                    user_id=user_id,
                    proposal=proposal,
                    locked_binding=locked_bindings.get(
                        str(proposal.get("binding_id") or "")
                    ),
                )

        response = UserPartyScopeBatchCommitResponse(
            items=self._response_items(analysis.items),
            impact=analysis.impact,
            committed_at=committed_at,
            idempotent=False,
        )
        await self.commit_crud.create_async(
            db,
            actor_id=actor_id,
            idempotency_key=request.idempotency_key,
            reason=request.reason,
            proposal=self._proposal_payload(items),
            before_scope=[
                item.analysis.before_scope.model_dump(mode="json")
                for item in analysis.items
            ],
            after_scope=[
                item.analysis.after_scope.model_dump(mode="json")
                for item in analysis.items
            ],
            impact_summary=analysis.impact.model_dump(mode="json"),
            result_data=response.model_dump(mode="json"),
            committed_at=committed_at,
        )
        await db.commit()
        for user in locked_users.values():
            await db.refresh(user)
        for binding in locked_bindings.values():
            await db.refresh(binding)
        for user_id in analysis.lock_user_ids:
            await party_service._publish_user_scope_invalidation(user_id)
        return response

    async def _build_preview_analysis(
        self,
        db: AsyncSession,
        *,
        items: list[UserPartyScopeBatchProposal],
        now: datetime | None = None,
    ) -> _BatchAnalysis:
        analysis_now = now or self._clock()
        grouped = await self._group_proposals(
            db,
            items=items,
            now=analysis_now,
        )
        analysis_items: list[_BatchItem] = []
        for user_id in sorted(grouped):
            user, proposals = grouped[user_id]
            analysis = await self.single_service._build_preview_analysis(
                db,
                user_id=user_id,
                proposals=proposals,
                now=analysis_now,
            )
            analysis_items.append(
                _BatchItem(
                    user=user,
                    operation=proposals[0]["operation"],
                    proposals=proposals,
                    analysis=analysis,
                )
            )

        impact = UserPartyScopeBatchImpact(
            user_count=len(analysis_items),
            binding_change_count=sum(
                len(item.proposals) for item in analysis_items
            ),
            scope_change_count=sum(
                1 for item in analysis_items if item.analysis.impact.scope_changed
            ),
            uses_organization_default_after_count=sum(
                1
                for item in analysis_items
                if item.analysis.impact.uses_organization_default_after
            ),
        )
        lock_user_ids = tuple(sorted({str(item.user.id) for item in analysis_items}))
        lock_binding_ids = tuple(
            sorted(
                {
                    str(proposal["binding_id"])
                    for item in analysis_items
                    for proposal in item.proposals
                    if proposal["binding_id"] is not None
                }
            )
        )
        fingerprint_payload = {
            "items": [
                {
                    "user_id": str(item.user.id),
                    "state_fingerprint": item.analysis.state_fingerprint,
                }
                for item in analysis_items
            ],
            "impact": impact.model_dump(mode="json"),
        }
        normalized = json.dumps(
            fingerprint_payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        return _BatchAnalysis(
            items=tuple(analysis_items),
            impact=impact,
            state_fingerprint=hashlib.sha256(
                normalized.encode("utf-8")
            ).hexdigest(),
            lock_user_ids=lock_user_ids,
            lock_binding_ids=lock_binding_ids,
            analysis_now=analysis_now,
        )

    async def _group_proposals(
        self,
        db: AsyncSession,
        *,
        items: list[UserPartyScopeBatchProposal],
        now: datetime,
    ) -> dict[str, tuple[User, list[dict[str, Any]]]]:
        grouped: dict[str, list[UserPartyScopeBatchProposal]] = {}
        for item in items:
            grouped.setdefault(item.user_id, []).append(item)

        result: dict[str, tuple[User, list[dict[str, Any]]]] = {}
        for user_id, proposals in grouped.items():
            user = await self.user_crud.get_async(db, user_id)
            if user is None:
                raise ResourceNotFoundError("用户", user_id)
            normalized: list[dict[str, Any]] = []
            for proposal in proposals:
                normalized.append(
                    await self.single_service._normalize_proposal(
                        db,
                        user_id=user_id,
                        proposal=proposal,
                        now=now,
                    )
                )
            result[user_id] = (user, normalized)
        return result

    async def _lock_users(
        self,
        db: AsyncSession,
        user_ids: tuple[str, ...],
    ) -> dict[str, User]:
        rows: dict[str, User] = {}
        for user_id in user_ids:
            user = await self.user_crud.get_for_update_async(db, user_id=user_id)
            if user is None:
                raise UserPartyScopePreviewStaleError("user_missing")
            rows[user_id] = user
        return rows

    async def _lock_bindings(
        self,
        db: AsyncSession,
        binding_ids: tuple[str, ...],
    ) -> dict[str, UserPartyBinding]:
        rows = await party_crud.get_user_bindings_for_update(
            db,
            binding_ids=binding_ids,
        )
        if len(rows) != len(binding_ids):
            raise UserPartyScopePreviewStaleError("binding_missing")
        return {str(binding.id): binding for binding in rows}

    def _response_items(
        self,
        items: tuple[_BatchItem, ...],
    ) -> list[UserPartyScopeBatchPreviewItem]:
        return [
            UserPartyScopeBatchPreviewItem(
                user=UserPartyScopeBatchUser.model_validate(item.user),
                operation=item.operation,
                before_scope=item.analysis.before_scope,
                after_scope=item.analysis.after_scope,
                impact=item.analysis.impact,
            )
            for item in items
        ]

    def _proposals_from_preview_payload(
        self,
        payload: dict[str, object],
        *,
        actor_id: str,
    ) -> list[UserPartyScopeBatchProposal]:
        if payload.get("actor_id") != actor_id:
            raise UserPartyScopePreviewStaleError("actor_mismatch")
        raw_proposal = payload.get("proposal")
        if not isinstance(raw_proposal, list):
            raise UserPartyScopePreviewStaleError("proposal_missing")
        try:
            return UserPartyScopeBatchPreviewRequest.model_validate(
                {"items": raw_proposal}
            ).items
        except ValueError as exc:
            raise UserPartyScopePreviewStaleError("proposal_invalid") from exc

    @staticmethod
    def _proposal_payload(
        proposals: list[UserPartyScopeBatchProposal],
    ) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        for proposal in proposals:
            item: dict[str, Any] = {
                "user_id": proposal.user_id,
                "operation": proposal.operation,
            }
            if proposal.operation == "create":
                item["party_id"] = proposal.party_id
                relation_type = proposal.relation_type
                if relation_type is not None:
                    item["relation_type"] = relation_type.value
            else:
                item["binding_id"] = proposal.binding_id
            if proposal.operation == "update":
                for field in ("party_id", "relation_type", "valid_from", "valid_to"):
                    if field in proposal.model_fields_set:
                        value = getattr(proposal, field)
                        item[field] = (
                            value.isoformat()
                            if isinstance(value, datetime)
                            else value
                        )
            payload.append(item)
        return payload

    @staticmethod
    def _user_ids_from_payload(
        payload: dict[str, object],
        *,
        actor_id: str,
    ) -> tuple[str, ...]:
        if payload.get("actor_id") != actor_id:
            raise UserPartyScopePreviewStaleError("actor_mismatch")
        raw_proposal = payload.get("proposal")
        if not isinstance(raw_proposal, list):
            raise UserPartyScopePreviewStaleError("proposal_missing")
        try:
            return tuple(
                item.user_id
                for item in UserPartyScopeBatchPreviewRequest.model_validate(
                    {"items": raw_proposal}
                ).items
            )
        except ValueError as exc:
            raise UserPartyScopePreviewStaleError("proposal_invalid") from exc

    @staticmethod
    def _user_ids_from_receipt(receipt: Any) -> tuple[str, ...]:
        proposal = getattr(receipt, "proposal", None)
        if not isinstance(proposal, list):
            raise UserPartyScopePreviewStaleError("receipt_invalid")
        try:
            return tuple(
                item.user_id
                for item in UserPartyScopeBatchPreviewRequest.model_validate(
                    {"items": proposal}
                ).items
            )
        except ValueError as exc:
            raise UserPartyScopePreviewStaleError("receipt_invalid") from exc

    @staticmethod
    def _response_from_receipt(
        receipt: Any,
        *,
        idempotent: bool,
    ) -> UserPartyScopeBatchCommitResponse:
        result_data = getattr(receipt, "result_data", None)
        if not isinstance(result_data, dict):
            raise UserPartyScopePreviewStaleError("receipt_invalid")
        return UserPartyScopeBatchCommitResponse.model_validate(
            {**result_data, "idempotent": idempotent}
        )


def _deserialize_datetime(
    value: object | None,
    *,
    allow_none: bool = False,
) -> datetime | None:
    if value is None:
        return None if allow_none else None
    if not isinstance(value, str):
        raise UserPartyScopePreviewStaleError("preview_invalid")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise UserPartyScopePreviewStaleError("preview_invalid") from exc


user_party_scope_batch_change_service = UserPartyScopeBatchChangeService()

__all__ = [
    "UserPartyScopeBatchChangeService",
    "UserPartyScopeBatchPreviewStore",
    "user_party_scope_batch_change_service",
]
