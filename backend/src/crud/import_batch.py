"""Data access for import batches and their per-row changes."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.import_batch import ImportBatch, ImportBatchChange


class ImportBatchRepository:
    async def get(self, db: AsyncSession, *, batch_id: str) -> ImportBatch | None:
        return (
            await db.execute(select(ImportBatch).where(ImportBatch.id == batch_id))
        ).scalar_one_or_none()

    async def get_for_update(
        self, db: AsyncSession, *, batch_id: str
    ) -> ImportBatch | None:
        return (
            await db.execute(
                select(ImportBatch).where(ImportBatch.id == batch_id).with_for_update()
            )
        ).scalar_one_or_none()

    async def list_changes(
        self,
        db: AsyncSession,
        *,
        batch_id: str,
        severity: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ImportBatchChange], int]:
        statement = select(ImportBatchChange).where(
            ImportBatchChange.batch_id == batch_id
        )
        count_statement = (
            select(func.count())
            .select_from(ImportBatchChange)
            .where(ImportBatchChange.batch_id == batch_id)
        )
        if severity is not None:
            statement = statement.where(ImportBatchChange.severity == severity)
            count_statement = count_statement.where(
                ImportBatchChange.severity == severity
            )
        statement = (
            statement.order_by(
                ImportBatchChange.row_number, ImportBatchChange.field_name
            )
            .offset(offset)
            .limit(limit)
        )
        rows = list((await db.execute(statement)).scalars().all())
        total = (await db.execute(count_statement)).scalar_one()
        return rows, total


import_batch_repository = ImportBatchRepository()
