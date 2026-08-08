"""CRUD operations for durable user Party-scope batch receipts."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user_party_scope_batch_commit import UserPartyScopeBatchCommit


class UserPartyScopeBatchCommitCRUD:
    async def get_by_idempotency_async(
        self,
        db: AsyncSession,
        *,
        actor_id: str,
        idempotency_key: str,
    ) -> UserPartyScopeBatchCommit | None:
        stmt = select(UserPartyScopeBatchCommit).where(
            UserPartyScopeBatchCommit.actor_id == actor_id,
            UserPartyScopeBatchCommit.idempotency_key == idempotency_key,
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
        committed_at: datetime,
    ) -> UserPartyScopeBatchCommit:
        receipt = UserPartyScopeBatchCommit(
            **{
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


user_party_scope_batch_commit_crud = UserPartyScopeBatchCommitCRUD()

__all__ = [
    "UserPartyScopeBatchCommitCRUD",
    "user_party_scope_batch_commit_crud",
]
