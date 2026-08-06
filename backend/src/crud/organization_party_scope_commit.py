"""CRUD operations for durable Organization Party scope commit receipts."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.organization import OrganizationPartyScopeCommit


class OrganizationPartyScopeCommitCRUD:
    async def get_by_idempotency_async(
        self,
        db: AsyncSession,
        *,
        organization_id: str,
        actor_id: str,
        idempotency_key: str,
    ) -> OrganizationPartyScopeCommit | None:
        stmt = select(OrganizationPartyScopeCommit).where(
            OrganizationPartyScopeCommit.organization_id == organization_id,
            OrganizationPartyScopeCommit.actor_id == actor_id,
            OrganizationPartyScopeCommit.idempotency_key == idempotency_key,
        )
        return (await db.execute(stmt)).scalars().first()

    async def create_async(
        self,
        db: AsyncSession,
        *,
        organization_id: str,
        actor_id: str,
        idempotency_key: str,
        reason: str,
        proposal: dict[str, Any],
        before_scope: dict[str, Any],
        after_scope: dict[str, Any],
        impact_summary: dict[str, Any],
        result_data: dict[str, Any],
        committed_at: Any,
    ) -> OrganizationPartyScopeCommit:
        receipt = OrganizationPartyScopeCommit(
            organization_id=organization_id,
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


organization_party_scope_commit_crud = OrganizationPartyScopeCommitCRUD()

__all__ = [
    "OrganizationPartyScopeCommitCRUD",
    "organization_party_scope_commit_crud",
]
