"""
Task Service Integration Tests (Async)
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from src import database as database
from src.enums.task import TaskStatus, TaskType
from src.models.task import AsyncTask, TaskHistory
from src.schemas.task import TaskCreate
from src.services.task.service import TaskService

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def async_db():
    async_engine = create_async_engine(
        database.get_async_database_url(),
        echo=False,
        poolclass=NullPool,
    )
    async with async_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
            await async_engine.dispose()


@pytest.fixture
def task_service():
    return TaskService()


@pytest.fixture
async def sample_task(async_db, task_service):
    task = await task_service.create_task(
        async_db,
        obj_in=TaskCreate(
            task_type=TaskType.EXCEL_IMPORT,
            title="测试任务",
            description="任务描述",
            parameters={"file": "test.xlsx"},
        ),
        user_id="test-user",
    )
    yield task


class TestTaskServiceIntegration:
    async def test_update_task_status_creates_history(
        self, async_db, task_service, sample_task
    ):
        updated = await task_service.update_task_status(
            async_db, task_id=str(sample_task.id), status=TaskStatus.RUNNING
        )
        assert updated.status == TaskStatus.RUNNING
        assert updated.started_at is not None

        result = await async_db.execute(
            select(TaskHistory).where(TaskHistory.task_id == str(sample_task.id))
        )
        history_rows = list(result.scalars().all())
        assert history_rows

    async def test_cleanup_old_tasks_marks_inactive(self, async_db, task_service):
        task = await task_service.create_task(
            async_db,
            obj_in=TaskCreate(
                task_type=TaskType.EXCEL_EXPORT,
                title="旧任务",
                description="用于清理测试",
                parameters={},
            ),
            user_id="cleanup-user",
        )
        old_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=60)
        await async_db.execute(
            update(AsyncTask)
            .where(AsyncTask.id == str(task.id))
            .values(created_at=old_date, status=TaskStatus.COMPLETED)
        )
        await async_db.commit()

        result = await task_service.cleanup_old_tasks(
            async_db, days=30, dry_run=False
        )
        assert result["cleaned_count"] >= 1

        refreshed = await async_db.get(AsyncTask, str(task.id))
        assert refreshed is not None
        assert refreshed.is_active is False
