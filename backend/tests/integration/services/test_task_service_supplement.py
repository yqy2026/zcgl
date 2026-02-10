"""
Supplemental Task Service Integration Tests (Async)
"""


import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from src import database as database
from src.enums.task import TaskStatus, TaskType
from src.models.task import AsyncTask, ExcelTaskConfig
from src.schemas.task import ExcelTaskConfigCreate, TaskCreate
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
            description="这是一个测试任务",
            parameters={"file": "test.xlsx"},
        ),
        user_id="user-001",
    )
    yield task


class TestTaskServiceSupplement:
    async def test_cancel_task(self, async_db, task_service, sample_task):
        updated = await task_service.cancel_task(
            async_db, task_id=str(sample_task.id), reason="Manual"
        )
        assert updated.status == TaskStatus.CANCELLED
        assert "Manual" in (updated.error_message or "")

    async def test_delete_task_soft_delete(self, async_db, task_service, sample_task):
        await task_service.delete_task(async_db, task_id=str(sample_task.id))
        refreshed = await async_db.get(AsyncTask, str(sample_task.id))
        assert refreshed is not None
        assert refreshed.is_active is False

    async def test_create_excel_config(self, async_db, task_service):
        config = await task_service.create_excel_config(
            async_db,
            obj_in=ExcelTaskConfigCreate(
                config_name="默认配置",
                config_type="import",
                task_type="excel_import",
                is_default=True,
            ),
        )
        assert config.config_name == "默认配置"

        result = await async_db.execute(
            select(ExcelTaskConfig).where(ExcelTaskConfig.id == str(config.id))
        )
        rows = list(result.scalars().all())
        assert rows
