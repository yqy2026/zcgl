from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.organization import OrganizationHistory


class OrganizationHistoryCRUD:
    """组织历史 CRUD 操作"""

    async def get_multi_async(
        self, db: AsyncSession, org_id: str, skip: int = 0, limit: int = 100
    ) -> list[OrganizationHistory]:
        items, _ = await self.get_multi_with_count_async(
            db=db, org_id=org_id, skip=skip, limit=limit
        )
        return items

    async def get_multi_with_count_async(
        self, db: AsyncSession, org_id: str, skip: int = 0, limit: int = 100
    ) -> tuple[list[OrganizationHistory], int]:
        conditions = [OrganizationHistory.organization_id == org_id]
        total_stmt = select(func.count(OrganizationHistory.id)).where(*conditions)
        total = int((await db.execute(total_stmt)).scalar() or 0)

        stmt = (
            select(OrganizationHistory)
            .where(*conditions)
            .order_by(OrganizationHistory.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        items = list((await db.execute(stmt)).scalars().all())
        return items, total
