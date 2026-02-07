"""
Supplemental Task Service Integration Tests (Async)
"""


import pytest
from sqlalchemy import delete, select

from src.database import async_session_scope
from src.enums.task import TaskStatus, TaskType
from src.models.task import AsyncTask, ExcelTaskConfig, TaskHistory
from src.schemas.task import ExcelTaskConfigCreate, TaskCreate
from src.services.task.service import TaskService

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def async_db():
    async with async_session_scope() as session:
        yield session


@pytest.fixture(autouse=True)
async def clean_tasks():
    async with async_session_scope() as session:
        await session.execute(delete(TaskHistory))
        await session.execute(delete(ExcelTaskConfig))
        await session.execute(delete(AsyncTask))
        await session.commit()
    yield
    async with async_session_scope() as session:
        await session.execute(delete(TaskHistory))
        await session.execute(delete(ExcelTaskConfig))
        await session.execute(delete(AsyncTask))
        await session.commit()


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
                created_by="tester",
            ),
            user_id="tester",
        )
        assert config.config_name == "默认配置"

        result = await async_db.execute(
            select(ExcelTaskConfig).where(ExcelTaskConfig.id == str(config.id))
        )
        rows = list(result.scalars().all())
        assert rows
