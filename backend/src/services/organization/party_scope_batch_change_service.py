"""Preview and commit all-or-nothing Organization Party scope batches."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import (
    OperationNotAllowedError,
    OrganizationPartyScopePreviewStaleError,
    ResourceNotFoundError,
)
from ...crud.organization import organization as organization_crud
from ...crud.organization_history import OrganizationHistoryCRUD
from ...crud.organization_party_scope_batch_commit import (
    OrganizationPartyScopeBatchCommitCRUD,
    organization_party_scope_batch_commit_crud,
)
from ...models.organization import Organization
from ...schemas.organization import (
    OrganizationPartyScopeBatchCommitRequest,
    OrganizationPartyScopeBatchCommitResponse,
    OrganizationPartyScopeBatchPreviewItem,
    OrganizationPartyScopeBatchPreviewRequest,
    OrganizationPartyScopeBatchPreviewResponse,
    OrganizationPartyScopeBatchProposal,
    OrganizationPartyScopeImpact,
    OrganizationResponse,
)
from .party_scope_change_service import (
    OrganizationPartyScopeAnalysis,
    OrganizationPartyScopePreviewStore,
    OrganizationPartyScopeService,
    organization_party_scope_service,
)


@dataclass(frozen=True)
class _BatchItemAnalysis:
    organization: Organization
    proposal: OrganizationPartyScopeBatchProposal
    analysis: OrganizationPartyScopeAnalysis


@dataclass(frozen=True)
class _BatchPreviewAnalysis:
    items: tuple[_BatchItemAnalysis, ...]
    impact: OrganizationPartyScopeImpact
    state_fingerprint: str
    lock_organization_ids: tuple[str, ...]


class OrganizationPartyScopeBatchPreviewStore(OrganizationPartyScopePreviewStore):
    """Dedicated token namespace so single and batch previews cannot mix."""

    NAMESPACE = "organization_party_scope_batch_preview"


class OrganizationPartyScopeBatchService:
    """Batch direct Organization represented-Party changes as one transaction."""

    def __init__(
        self,
        *,
        preview_store: OrganizationPartyScopeBatchPreviewStore | None = None,
        commit_crud: OrganizationPartyScopeBatchCommitCRUD | None = None,
        analysis_service: OrganizationPartyScopeService | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC).replace(tzinfo=None))
        self.preview_store = preview_store or OrganizationPartyScopeBatchPreviewStore(
            clock=self._clock
        )
        self.commit_crud = commit_crud or organization_party_scope_batch_commit_crud
        self.analysis_service = analysis_service or organization_party_scope_service

    async def preview(
        self,
        db: AsyncSession,
        *,
        request: OrganizationPartyScopeBatchPreviewRequest,
        actor_id: str,
    ) -> OrganizationPartyScopeBatchPreviewResponse:
        analysis = await self._build_preview_analysis(db, items=request.items)
        proposal_payload = self._proposal_payload(request.items)
        token, expires_at = self.preview_store.issue(
            {
                "actor_id": actor_id,
                "proposal": proposal_payload,
                "state_fingerprint": analysis.state_fingerprint,
            }
        )
        return OrganizationPartyScopeBatchPreviewResponse(
            items=self._response_items(analysis.items),
            impact=analysis.impact,
            preview_token=token,
            expires_at=expires_at,
        )

    def get_preview_organization_ids(
        self,
        *,
        preview_token: str,
        actor_id: str,
    ) -> tuple[str, ...]:
        """Read token targets before committing, so routes can authorize each one."""
        payload = self.preview_store.peek(preview_token)
        if payload is None:
            raise OrganizationPartyScopePreviewStaleError("missing_or_expired")
        return tuple(
            item.organization_id
            for item in self._proposals_from_preview_payload(payload, actor_id=actor_id)
        )

    async def get_commit_organization_ids(
        self,
        db: AsyncSession,
        *,
        request: OrganizationPartyScopeBatchCommitRequest,
        actor_id: str,
    ) -> tuple[str, ...]:
        """Resolve batch targets for authorization, including idempotent retries."""
        existing = await self.commit_crud.get_by_idempotency_async(
            db,
            actor_id=actor_id,
            idempotency_key=request.idempotency_key,
        )
        if existing is not None:
            return self._organization_ids_from_receipt(existing)
        return self.get_preview_organization_ids(
            preview_token=request.preview_token,
            actor_id=actor_id,
        )

    async def commit(
        self,
        db: AsyncSession,
        *,
        request: OrganizationPartyScopeBatchCommitRequest,
        actor_id: str,
    ) -> OrganizationPartyScopeBatchCommitResponse:
        """Commit a previewed batch once, with no partial Organization writes."""
        existing = await self.commit_crud.get_by_idempotency_async(
            db,
            actor_id=actor_id,
            idempotency_key=request.idempotency_key,
        )
        if existing is not None:
            return self._response_from_receipt(existing, idempotent=True)

        preview_payload = self.preview_store.consume(request.preview_token)
        if preview_payload is None:
            raise OrganizationPartyScopePreviewStaleError("missing_or_expired")
        proposals = self._proposals_from_preview_payload(
            preview_payload,
            actor_id=actor_id,
        )

        try:
            initial_analysis = await self._build_preview_analysis(db, items=proposals)
            locked_organizations = await self._lock_organizations(
                db,
                initial_analysis.lock_organization_ids,
            )
            analysis = await self._build_preview_analysis(db, items=proposals)
        except (OperationNotAllowedError, ResourceNotFoundError) as exc:
            raise OrganizationPartyScopePreviewStaleError("state_changed") from exc

        if preview_payload.get("state_fingerprint") != analysis.state_fingerprint:
            raise OrganizationPartyScopePreviewStaleError("state_changed")

        existing = await self.commit_crud.get_by_idempotency_async(
            db,
            actor_id=actor_id,
            idempotency_key=request.idempotency_key,
        )
        if existing is not None:
            return self._response_from_receipt(existing, idempotent=True)

        committed_at = self._clock()
        history_crud = OrganizationHistoryCRUD()
        for item in analysis.items:
            organization_id = str(item.organization.id)
            organization = locked_organizations[organization_id]
            proposal_payload = self.analysis_service.proposal_payload(item.proposal)
            before_scope = item.analysis.before_scope.model_dump(mode="json")
            after_scope = item.analysis.after_scope.model_dump(mode="json")
            organization.represented_party_id = proposal_payload["represented_party_id"]
            organization.represented_party_perspective = proposal_payload[
                "represented_party_perspective"
            ]
            organization.updated_at = committed_at
            organization.updated_by = actor_id
            await history_crud.create_async(
                db,
                organization_id=organization_id,
                action="party_scope_batch",
                field_name="represented_party_scope",
                old_value=json.dumps(before_scope, ensure_ascii=False, sort_keys=True),
                new_value=json.dumps(after_scope, ensure_ascii=False, sort_keys=True),
                change_reason=request.reason,
                created_by=actor_id,
            )

        response = OrganizationPartyScopeBatchCommitResponse(
            items=self._response_items(analysis.items, organizations=locked_organizations),
            impact=analysis.impact,
            committed_at=committed_at,
            idempotent=False,
        )
        await self.commit_crud.create_async(
            db,
            actor_id=actor_id,
            idempotency_key=request.idempotency_key,
            reason=request.reason,
            proposal=self._proposal_payload(proposals),
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
        for organization in locked_organizations.values():
            await db.refresh(organization)
        self.analysis_service.invalidate_caches()
        return response

    async def _build_preview_analysis(
        self,
        db: AsyncSession,
        *,
        items: list[OrganizationPartyScopeBatchProposal],
    ) -> _BatchPreviewAnalysis:
        organizations = await self._load_organizations(db, items=items)
        await self._assert_non_overlapping_subtrees(
            db,
            organizations=organizations,
        )
        analysis_items: list[_BatchItemAnalysis] = []
        for proposal in items:
            organization_id = proposal.organization_id
            analysis_items.append(
                _BatchItemAnalysis(
                    organization=organizations[organization_id],
                    proposal=proposal,
                    analysis=await self.analysis_service.analyze(
                        db,
                        organization_id=organization_id,
                        proposal=proposal,
                    ),
                )
            )

        impact = OrganizationPartyScopeImpact(
            organization_count=sum(item.analysis.impact.organization_count for item in analysis_items),
            organization_scope_change_count=sum(
                item.analysis.impact.organization_scope_change_count
                for item in analysis_items
            ),
            user_count=sum(item.analysis.impact.user_count for item in analysis_items),
            user_scope_change_count=sum(
                item.analysis.impact.user_scope_change_count for item in analysis_items
            ),
        )
        lock_organization_ids = tuple(
            sorted(
                {
                    organization_id
                    for item in analysis_items
                    for organization_id in item.analysis.lock_organization_ids
                }
            )
        )
        fingerprint_payload = {
            "items": [
                {
                    "organization_id": item.proposal.organization_id,
                    "state_fingerprint": item.analysis.state_fingerprint,
                }
                for item in sorted(
                    analysis_items,
                    key=lambda item: item.proposal.organization_id,
                )
            ],
            "impact": impact.model_dump(mode="json"),
        }
        normalized = json.dumps(
            fingerprint_payload,
            sort_keys=True,
            separators=(",", ":"),
        )
        return _BatchPreviewAnalysis(
            items=tuple(analysis_items),
            impact=impact,
            state_fingerprint=hashlib.sha256(
                normalized.encode("utf-8")
            ).hexdigest(),
            lock_organization_ids=lock_organization_ids,
        )

    async def _load_organizations(
        self,
        db: AsyncSession,
        *,
        items: list[OrganizationPartyScopeBatchProposal],
    ) -> dict[str, Organization]:
        organizations: dict[str, Organization] = {}
        for item in items:
            organization = await organization_crud.get_async(
                db,
                id=item.organization_id,
                use_cache=False,
            )
            if organization is None:
                raise ResourceNotFoundError("组织", item.organization_id)
            organizations[item.organization_id] = organization
        return organizations

    async def _assert_non_overlapping_subtrees(
        self,
        db: AsyncSession,
        *,
        organizations: dict[str, Organization],
    ) -> None:
        selected_ids = set(organizations)
        for organization_id in sorted(selected_ids):
            descendants = await organization_crud.get_children_async(
                db,
                parent_id=organization_id,
                recursive=True,
            )
            overlapping_ids = selected_ids.intersection(
                str(item.id) for item in descendants
            )
            if len(overlapping_ids) > 0:
                raise OperationNotAllowedError(
                    "Organization Party scope batch cannot include an ancestor and descendant",
                    reason="organization_party_scope_batch_overlap",
                )

    async def _lock_organizations(
        self,
        db: AsyncSession,
        organization_ids: tuple[str, ...],
    ) -> dict[str, Organization]:
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
            raise OrganizationPartyScopePreviewStaleError("organization_missing")
        return {str(row.id): row for row in rows}

    @staticmethod
    def _response_items(
        items: tuple[_BatchItemAnalysis, ...],
        *,
        organizations: dict[str, Organization] | None = None,
    ) -> list[OrganizationPartyScopeBatchPreviewItem]:
        return [
            OrganizationPartyScopeBatchPreviewItem(
                organization=OrganizationResponse.model_validate(
                    organizations.get(str(item.organization.id), item.organization)
                    if organizations is not None
                    else item.organization
                ),
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
    ) -> list[OrganizationPartyScopeBatchProposal]:
        if payload.get("actor_id") != actor_id:
            raise OrganizationPartyScopePreviewStaleError("actor_mismatch")
        raw_proposal = payload.get("proposal")
        if not isinstance(raw_proposal, list):
            raise OrganizationPartyScopePreviewStaleError("proposal_missing")
        try:
            return OrganizationPartyScopeBatchPreviewRequest.model_validate(
                {"items": raw_proposal}
            ).items
        except ValueError as exc:
            raise OrganizationPartyScopePreviewStaleError("proposal_invalid") from exc

    def _proposal_payload(
        self,
        proposals: list[OrganizationPartyScopeBatchProposal],
    ) -> list[dict[str, str | None]]:
        return [
            {
                "organization_id": proposal.organization_id,
                **self.analysis_service.proposal_payload(proposal),
            }
            for proposal in proposals
        ]

    @staticmethod
    def _organization_ids_from_receipt(receipt: Any) -> tuple[str, ...]:
        proposal = getattr(receipt, "proposal", None)
        if not isinstance(proposal, list):
            raise OrganizationPartyScopePreviewStaleError("receipt_invalid")
        try:
            return tuple(
                item.organization_id
                for item in OrganizationPartyScopeBatchPreviewRequest.model_validate(
                    {"items": proposal}
                ).items
            )
        except ValueError as exc:
            raise OrganizationPartyScopePreviewStaleError("receipt_invalid") from exc

    @staticmethod
    def _response_from_receipt(
        receipt: Any,
        *,
        idempotent: bool,
    ) -> OrganizationPartyScopeBatchCommitResponse:
        result_data = getattr(receipt, "result_data", None)
        if not isinstance(result_data, dict):
            raise OrganizationPartyScopePreviewStaleError("receipt_invalid")
        return OrganizationPartyScopeBatchCommitResponse.model_validate(
            {**result_data, "idempotent": idempotent}
        )


organization_party_scope_batch_service = OrganizationPartyScopeBatchService()

__all__ = [
    "OrganizationPartyScopeBatchPreviewStore",
    "OrganizationPartyScopeBatchService",
    "organization_party_scope_batch_service",
]
