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

    async def list_batches(
        self,
        db: AsyncSession,
        *,
        created_by: str,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ImportBatch], int]:
        """The actor's recent batches (both modes mixed), newest first.

        Owner-only to match the detail/commit paths: a batch whose
        created_by differs is invisible here, exactly as ``get_batch``
        hides it.
        """
        from sqlalchemy import func, select

        base = select(ImportBatch).where(ImportBatch.created_by == created_by)
        count = int(
            (
                await db.execute(
                    select(func.count()).select_from(base.order_by(None).subquery())
                )
            ).scalar_one()
        )
        rows = (
            (
                await db.execute(
                    base.order_by(ImportBatch.created_at.desc(), ImportBatch.id)
                    .offset(offset)
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), count

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
