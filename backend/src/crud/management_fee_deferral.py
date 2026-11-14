"""Append deferral marks without owning the command transaction."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.management_fee_deferral import ManagementFeeDeferral

_MARKS_ORDER = (ManagementFeeDeferral.created_at, ManagementFeeDeferral.id)


class ManagementFeeDeferralRepository:
    async def list_marks(
        self, db: AsyncSession, *, statement_id: str
    ) -> tuple[ManagementFeeDeferral, ...]:
        query = (
            select(ManagementFeeDeferral)
            .where(ManagementFeeDeferral.statement_id == statement_id)
            .order_by(*_MARKS_ORDER)
        )
        return tuple((await db.execute(query)).scalars().all())

    async def list_marks_for_statements(
        self, db: AsyncSession, *, statement_ids: Sequence[str]
    ) -> dict[str, tuple[ManagementFeeDeferral, ...]]:
        """Batch mark read for fee reads; grouped per statement, same order."""
        if not statement_ids:
            return {}
        query = (
            select(ManagementFeeDeferral)
            .where(ManagementFeeDeferral.statement_id.in_(statement_ids))
            .order_by(*_MARKS_ORDER)
        )
        grouped: dict[str, list[ManagementFeeDeferral]] = {}
        for mark in (await db.execute(query)).scalars().all():
            grouped.setdefault(mark.statement_id, []).append(mark)
        return {key: tuple(value) for key, value in grouped.items()}

    async def add_mark(self, db: AsyncSession, *, mark: ManagementFeeDeferral) -> None:
        db.add(mark)


management_fee_deferral_repository = ManagementFeeDeferralRepository()
