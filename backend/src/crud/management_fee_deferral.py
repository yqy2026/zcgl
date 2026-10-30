"""Append deferral marks without owning the command transaction."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.management_fee_deferral import ManagementFeeDeferral


class ManagementFeeDeferralRepository:
    async def list_marks(
        self, db: AsyncSession, *, statement_id: str
    ) -> tuple[ManagementFeeDeferral, ...]:
        query = (
            select(ManagementFeeDeferral)
            .where(ManagementFeeDeferral.statement_id == statement_id)
            .order_by(ManagementFeeDeferral.created_at, ManagementFeeDeferral.id)
        )
        return tuple((await db.execute(query)).scalars().all())

    async def add_mark(self, db: AsyncSession, *, mark: ManagementFeeDeferral) -> None:
        db.add(mark)


management_fee_deferral_repository = ManagementFeeDeferralRepository()
