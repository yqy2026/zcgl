"""Export terminal state must survive the renderer's real session closing."""

import asyncio
import base64
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.enums.task import TaskStatus
from src.models.auth import User
from src.models.occupancy_report import MonthlyOccupancyReport
from src.models.party import Party, PartyType
from src.models.task import AsyncTask, TaskHistory
from src.services.asset_operations.occupancy_report_submission_service import (
    occupancy_report_submission_service,
)
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = pytest.mark.e2e


@pytest.mark.parametrize("missing_report", [False, True])
def test_export_terminal_state_survives_renderer_session_close(
    test_database_url: str, missing_report: bool
) -> None:
    async def run() -> None:
        engine = create_async_engine(
            test_database_url.replace(
                "postgresql+psycopg://", "postgresql+asyncpg://", 1
            ),
            poolclass=NullPool,
        )
        maker = async_sessionmaker(engine, expire_on_commit=False)
        actor_id, operator_id, report_id = (str(uuid4()) for _ in range(3))
        task_id: str | None = None
        try:
            async with maker() as db:
                db.add_all(
                    [
                        User(
                            id=actor_id,
                            username=f"export-{uuid4().hex[:12]}",
                            email=f"export-{uuid4().hex[:12]}@example.com",
                            phone=f"13{uuid4().int % 10**9:09d}",
                            full_name="导出持久化回归",
                            password_hash="unused",
                            account_type="service",
                            is_active=True,
                        ),
                        Party(
                            id=operator_id,
                            party_type=PartyType.LEGAL_ENTITY,
                            name=f"导出主体-{uuid4().hex[:12]}",
                            code=f"LE-{uuid4().int % 1_000_000:06d}",
                            status="active",
                            review_status="approved",
                        ),
                    ]
                )
                await db.flush()
                db.add(
                    MonthlyOccupancyReport(
                        id=report_id,
                        operator_party_id=operator_id,
                        period="2026-10",
                        status="submitted",
                        submitted_by=actor_id,
                        submitted_at=datetime.now(UTC).replace(tzinfo=None),
                        created_by=actor_id,
                    )
                )
                await db.commit()
                task_id = await occupancy_report_submission_service.create_export_task(
                    db,
                    report_id=report_id,
                    actor_id=actor_id,
                    scope=EffectivePartyScope(
                        user_id=actor_id,
                        source="explicit",
                        scope_mode="manager",
                        manager_party_ids=[operator_id],
                    ),
                )
            if missing_report:
                async with maker() as db:
                    await db.execute(
                        delete(MonthlyOccupancyReport).where(
                            MonthlyOccupancyReport.id == report_id
                        )
                    )
                    await db.commit()
            async with maker() as renderer:
                await occupancy_report_submission_service.render_export(
                    renderer, task_id=task_id
                )
            # This independent reader cannot observe a mere flush in the closed renderer.
            async with maker() as reader:
                task = await reader.get(AsyncTask, task_id)
                assert task is not None
                assert task.status == (
                    TaskStatus.FAILED if missing_report else TaskStatus.COMPLETED
                )
                assert task.completed_at is not None
                if missing_report:
                    assert task.error_message == "报送快照不存在或未提交"
                    assert task.result_data is None
                else:
                    assert task.result_data is not None
                    content = base64.b64decode(
                        task.result_data["content_base64"]
                    ).decode("utf-8")
                    assert content.startswith("asset_unit_id,owner_name")
                    assert "report_summary" in content
                    assert (
                        task.result_data["file_name"] == "occupancy-report-2026-10.csv"
                    )
        finally:
            async with maker() as db:
                if task_id is not None:
                    await db.execute(
                        delete(TaskHistory).where(TaskHistory.task_id == task_id)
                    )
                    await db.execute(delete(AsyncTask).where(AsyncTask.id == task_id))
                await db.execute(
                    delete(MonthlyOccupancyReport).where(
                        MonthlyOccupancyReport.id == report_id
                    )
                )
                await db.execute(delete(User).where(User.id == actor_id))
                await db.execute(delete(Party).where(Party.id == operator_id))
                await db.commit()
            await engine.dispose()

    asyncio.run(run())
