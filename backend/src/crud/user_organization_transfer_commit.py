"""CRUD operations for durable user organization-transfer receipts."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user_organization_transfer_commit import UserOrganizationTransferCommit


class UserOrganizationTransferCommitCRUD:
    async def get_by_idempotency_async(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        actor_id: str,
        idempotency_key: str,
    ) -> UserOrganizationTransferCommit | None:
        stmt = select(UserOrganizationTransferCommit).where(
            UserOrganizationTransferCommit.user_id == user_id,
            UserOrganizationTransferCommit.actor_id == actor_id,
            UserOrganizationTransferCommit.idempotency_key == idempotency_key,
        )
        return (await db.execute(stmt)).scalars().first()

    async def create_async(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        actor_id: str,
        target_organization_id: str,
        idempotency_key: str,
        reason: str,
        proposal: dict[str, Any],
        before_scope: dict[str, Any],
        after_scope: dict[str, Any],
        impact_summary: dict[str, Any],
        result_data: dict[str, Any],
        committed_at: datetime,
    ) -> UserOrganizationTransferCommit:
        receipt = UserOrganizationTransferCommit(
            **{
                "user_id": user_id,
                "actor_id": actor_id,
                "target_organization_id": target_organization_id,
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


user_organization_transfer_commit_crud = UserOrganizationTransferCommitCRUD()

__all__ = [
    "UserOrganizationTransferCommitCRUD",
    "user_organization_transfer_commit_crud",
]
