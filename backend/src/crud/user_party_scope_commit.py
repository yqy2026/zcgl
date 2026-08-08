"""CRUD operations for durable user Party-scope commit receipts."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user_party_scope_commit import UserPartyScopeCommit


class UserPartyScopeCommitCRUD:
    async def get_by_idempotency_async(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        actor_id: str,
        idempotency_key: str,
    ) -> UserPartyScopeCommit | None:
        stmt = select(UserPartyScopeCommit).where(
            UserPartyScopeCommit.user_id == user_id,
            UserPartyScopeCommit.actor_id == actor_id,
            UserPartyScopeCommit.idempotency_key == idempotency_key,
        )
        return (await db.execute(stmt)).scalars().first()

    async def create_async(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        actor_id: str,
        idempotency_key: str,
        reason: str,
        proposal: dict[str, Any],
        before_scope: dict[str, Any],
        after_scope: dict[str, Any],
        impact_summary: dict[str, Any],
        result_data: dict[str, Any],
        committed_at: datetime,
    ) -> UserPartyScopeCommit:
        receipt = UserPartyScopeCommit(
            **{
                "user_id": user_id,
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


user_party_scope_commit_crud = UserPartyScopeCommitCRUD()

__all__ = ["UserPartyScopeCommitCRUD", "user_party_scope_commit_crud"]
