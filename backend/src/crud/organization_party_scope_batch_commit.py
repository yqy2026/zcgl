"""CRUD operations for durable Organization Party scope batch receipts."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.organization import OrganizationPartyScopeBatchCommit


class OrganizationPartyScopeBatchCommitCRUD:
    async def get_by_idempotency_async(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        idempotency_key: str,
    ) -> OrganizationPartyScopeBatchCommit | None:
        stmt = select(OrganizationPartyScopeBatchCommit).where(
            OrganizationPartyScopeBatchCommit.actor_id == actor_id,
            OrganizationPartyScopeBatchCommit.idempotency_key == idempotency_key,
        )
        return (await db.execute(stmt)).scalars().first()

    async def create_async(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        idempotency_key: str,
        reason: str,
        proposal: list[dict[str, Any]],
        before_scope: list[dict[str, Any]],
        after_scope: list[dict[str, Any]],
        impact_summary: dict[str, Any],
        result_data: dict[str, Any],
        committed_at: Any,
    ) -> OrganizationPartyScopeBatchCommit:
        receipt = OrganizationPartyScopeBatchCommit(
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            reason=reason,
            proposal=proposal,
            before_scope=before_scope,
            after_scope=after_scope,
            impact_summary=impact_summary,
            result_data=result_data,
            committed_at=committed_at,
        )
        db.add(receipt)
        await db.flush()
        return receipt


organization_party_scope_batch_commit_crud = OrganizationPartyScopeBatchCommitCRUD()

__all__ = [
    "OrganizationPartyScopeBatchCommitCRUD",
    "organization_party_scope_batch_commit_crud",
]
