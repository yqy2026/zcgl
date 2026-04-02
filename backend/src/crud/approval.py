"""审批域 CRUD。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.approval import ApprovalActionLog, ApprovalInstance, ApprovalTaskSnapshot


class ApprovalCRUD:
    """审批数据访问层。"""

    async def find_active_instance(
        self,
        db: AsyncSession,
        *,
        business_type: str,
        business_id: str,
    ) -> ApprovalInstance | None:
        stmt = select(ApprovalInstance).where(
            ApprovalInstance.business_type == business_type,
            ApprovalInstance.business_id == business_id,
            ApprovalInstance.status == "pending",
        )
        return (await db.execute(stmt)).scalars().first()

    async def get_instance(
        self,
        db: AsyncSession,
        *,
        approval_instance_id: str,
    ) -> ApprovalInstance | None:
        stmt = select(ApprovalInstance).where(ApprovalInstance.id == approval_instance_id)
        return (await db.execute(stmt)).scalars().first()

    async def get_task(
        self,
        db: AsyncSession,
        *,
        task_id: str,
    ) -> ApprovalTaskSnapshot | None:
        stmt = select(ApprovalTaskSnapshot).where(ApprovalTaskSnapshot.id == task_id)
        return (await db.execute(stmt)).scalars().first()

    async def list_pending_tasks(
        self,
        db: AsyncSession,
        *,
        assignee_user_id: str,
    ) -> list[ApprovalTaskSnapshot]:
        stmt = (
            select(ApprovalTaskSnapshot)
            .where(
                ApprovalTaskSnapshot.assignee_user_id == assignee_user_id,
                ApprovalTaskSnapshot.status == "pending",
            )
            .order_by(ApprovalTaskSnapshot.created_at.desc())
        )
        return list((await db.execute(stmt)).scalars().all())

    async def list_started_processes(
        self,
        db: AsyncSession,
        *,
        starter_id: str,
    ) -> list[ApprovalInstance]:
        stmt = (
            select(ApprovalInstance)
            .where(ApprovalInstance.starter_id == starter_id)
            .order_by(ApprovalInstance.started_at.desc())
        )
        return list((await db.execute(stmt)).scalars().all())

    async def list_action_logs(
        self,
        db: AsyncSession,
        *,
        approval_instance_id: str,
    ) -> list[ApprovalActionLog]:
        stmt = (
            select(ApprovalActionLog)
            .where(ApprovalActionLog.approval_instance_id == approval_instance_id)
            .order_by(ApprovalActionLog.created_at.asc())
        )
        return list((await db.execute(stmt)).scalars().all())


approval_crud = ApprovalCRUD()
