"""CRUD operations for durable Organization move receipts."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.organization_move_commit import OrganizationMoveCommit


class OrganizationMoveCommitCRUD:
    async def get_by_idempotency_async(
        self,
        db: AsyncSession,
        *,
        organization_id: str,
        actor_id: str,
        idempotency_key: str,
    ) -> OrganizationMoveCommit | None:
        stmt = select(OrganizationMoveCommit).where(
            OrganizationMoveCommit.organization_id == organization_id,
            OrganizationMoveCommit.actor_id == actor_id,
            OrganizationMoveCommit.idempotency_key == idempotency_key,
        )
        return (await db.execute(stmt)).scalars().first()

    async def create_async(
        self,
        db: AsyncSession,
        *,
        organization_id: str,
        target_parent_id: str | None,
        actor_id: str,
        idempotency_key: str,
        reason: str,
        proposal: dict[str, Any],
        before_scope: dict[str, Any],
        after_scope: dict[str, Any],
        impact_summary: dict[str, Any],
        result_data: dict[str, Any],
        committed_at: datetime,
    ) -> OrganizationMoveCommit:
        receipt = OrganizationMoveCommit(
            **{
                "organization_id": organization_id,
                "target_parent_id": target_parent_id,
                "actor_id": actor_id,
                "idempotency_key": idempotency_key,
                "reason": reason,
                "proposal": proposal,
                "before_scope": before_scope,
                "after_scope": after_scope,
                "impact_summary": impact_summary,
                "result_data": result_data,
                "committed_at": committed_at,
            }
        )
        db.add(receipt)
        await db.flush()
        return receipt


organization_move_commit_crud = OrganizationMoveCommitCRUD()

__all__ = ["OrganizationMoveCommitCRUD", "organization_move_commit_crud"]
