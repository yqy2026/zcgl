"""CRUD operations for durable Party lifecycle commit receipts."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.party_lifecycle_commit import PartyLifecycleCommit


class PartyLifecycleCommitCRUD:
    async def get_by_idempotency_async(
        self,
        db: AsyncSession,
        *,
        party_id: str,
        actor_id: str,
        idempotency_key: str,
    ) -> PartyLifecycleCommit | None:
        stmt = select(PartyLifecycleCommit).where(
            PartyLifecycleCommit.party_id == party_id,
            PartyLifecycleCommit.actor_id == actor_id,
            PartyLifecycleCommit.idempotency_key == idempotency_key,
        )
        return (await db.execute(stmt)).scalars().first()

    async def create_async(
        self,
        db: AsyncSession,
        *,
        party_id: str,
        actor_id: str,
        idempotency_key: str,
        operation: str,
        reason: str,
        before_state: dict[str, Any],
        after_state: dict[str, Any],
        impact_summary: dict[str, Any],
        result_data: dict[str, Any],
        committed_at: datetime,
    ) -> PartyLifecycleCommit:
        receipt = PartyLifecycleCommit(
            **{
                "party_id": party_id,
                "actor_id": actor_id,
                "idempotency_key": idempotency_key,
                "operation": operation,
                "reason": reason,
                "before_state": before_state,
                "after_state": after_state,
                "impact_summary": impact_summary,
                "result_data": result_data,
                "committed_at": committed_at,
            }
        )
        db.add(receipt)
        await db.flush()
        return receipt


party_lifecycle_commit_crud = PartyLifecycleCommitCRUD()

__all__ = ["PartyLifecycleCommitCRUD", "party_lifecycle_commit_crud"]
