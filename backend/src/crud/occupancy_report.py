"""Data access for asset-operations v5 monthly occupancy reports."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..enums.task import TaskStatus
from ..models.occupancy_report import (
    MonthlyOccupancyReport,
    MonthlyOccupancyReportLine,
)
from ..models.party import Party
from ..models.project import Project
from ..models.task import AsyncTask


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class OccupancyReportRepository:
    """Persist the per-operator, per-month reporting chain rows."""

    async def get_active_chain_report(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        period: str,
        for_update: bool = False,
    ) -> MonthlyOccupancyReport | None:
        statement = (
            select(MonthlyOccupancyReport)
            .where(
                MonthlyOccupancyReport.operator_party_id == operator_party_id,
                MonthlyOccupancyReport.period == period,
                MonthlyOccupancyReport.status != "withdrawn",
            )
            .limit(1)
        )
        if for_update:
            # Locking reads must discard a stale identity-map row, matching
            # the assessment-scope and contract repositories.
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return (await db.execute(statement)).scalars().one_or_none()

    async def get_any_status(
        self,
        db: AsyncSession,
        *,
        report_id: str,
        for_update: bool = False,
    ) -> MonthlyOccupancyReport | None:
        statement = (
            select(MonthlyOccupancyReport)
            .where(MonthlyOccupancyReport.id == report_id)
            .limit(1)
        )
        if for_update:
            # Locking reads must discard a stale identity-map row, matching
            # the assessment-scope and contract repositories.
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return (await db.execute(statement)).scalars().one_or_none()

    async def get_async_task(
        self,
        db: AsyncSession,
        *,
        task_id: str,
    ) -> AsyncTask | None:
        statement = select(AsyncTask).where(AsyncTask.id == task_id).limit(1)
        return (await db.execute(statement)).scalars().one_or_none()

    async def create_chain_report(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        period: str,
        actor_id: str,
        created_at: datetime,
    ) -> MonthlyOccupancyReport:
        draft = MonthlyOccupancyReport(  # type: ignore[call-arg]
            id=str(uuid.uuid4()),
            operator_party_id=operator_party_id,
            period=period,
            status="draft",
            created_by=actor_id,
            created_at=created_at,
        )
        db.add(draft)
        await db.flush()
        return draft

    @staticmethod
    async def finish_task(
        db: AsyncSession,
        *,
        task: AsyncTask,
        status: TaskStatus,
        completed_at: datetime,
        error_message: str | None = None,
        result_data: dict[str, object] | None = None,
    ) -> None:
        """Terminal task-state write; the caller owns the transaction."""
        task.status = status
        task.progress = 100 if status == TaskStatus.COMPLETED else 0
        task.completed_at = completed_at
        if error_message is not None:
            task.error_message = error_message
        if result_data is not None:
            task.result_data = result_data
        await db.flush()

    async def get_line_display_names(
        self,
        db: AsyncSession,
        *,
        owner_party_ids: set[str],
        project_ids: set[str],
    ) -> dict[str, dict[str, str]]:
        """Current owner and project display names for report-line snapshots."""
        owners: dict[str, str] = {}
        if len(owner_party_ids) > 0:
            rows = (
                await db.execute(
                    select(Party.id, Party.name).where(Party.id.in_(owner_party_ids))
                )
            ).all()
            owners = {party_id: name for party_id, name in rows}
        projects: dict[str, str] = {}
        if len(project_ids) > 0:
            rows = (
                await db.execute(
                    select(Project.id, Project.project_name).where(
                        Project.id.in_(project_ids)
                    )
                )
            ).all()
            projects = {project_id: name for project_id, name in rows}
        return {"owner": owners, "project": projects}

    async def get_submitted_report(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        period: str,
    ) -> MonthlyOccupancyReport | None:
        statement = (
            select(MonthlyOccupancyReport)
            .where(
                MonthlyOccupancyReport.operator_party_id == operator_party_id,
                MonthlyOccupancyReport.period == period,
                MonthlyOccupancyReport.status == "submitted",
            )
            .limit(1)
        )
        return (await db.execute(statement)).scalars().one_or_none()

    async def lock_serialization(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        period: str,
    ) -> None:
        """Serialize draft-note upserts and later submissions per report."""
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": f"occupancy_report:{operator_party_id}:{period}"},
        )

    async def upsert_draft_for_note(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        period: str,
        change_note: str | None,
        actor_id: str,
    ) -> MonthlyOccupancyReport:
        """Create the chain draft when absent, then persist the note."""
        existing = await self.get_active_chain_report(
            db,
            operator_party_id=operator_party_id,
            period=period,
        )
        if existing is not None:
            existing.change_note = change_note
            existing.version = existing.version + 1
            await db.flush()
            return existing
        draft = MonthlyOccupancyReport(  # type: ignore[call-arg]
            id=str(uuid.uuid4()),
            operator_party_id=operator_party_id,
            period=period,
            status="draft",
            change_note=change_note,
            created_by=actor_id,
            created_at=_utcnow_naive(),
        )
        db.add(draft)
        await db.flush()
        return draft

    async def replace_lines(
        self,
        db: AsyncSession,
        *,
        report_id: str,
        lines: Sequence[MonthlyOccupancyReportLine],
    ) -> None:
        """Snapshot rows are written once per submission, replacing nothing."""
        await db.execute(
            MonthlyOccupancyReportLine.__table__.delete().where(
                MonthlyOccupancyReportLine.report_id == report_id
            )
        )
        for line in lines:
            db.add(line)
        await db.flush()

    async def list_lines(
        self,
        db: AsyncSession,
        *,
        report_id: str,
    ) -> list[MonthlyOccupancyReportLine]:
        statement = (
            select(MonthlyOccupancyReportLine)
            .where(MonthlyOccupancyReportLine.report_id == report_id)
            .order_by(MonthlyOccupancyReportLine.asset_unit_id)
        )
        return list((await db.execute(statement)).scalars().all())


occupancy_report_repository = OccupancyReportRepository()


__all__ = ["OccupancyReportRepository", "occupancy_report_repository"]
