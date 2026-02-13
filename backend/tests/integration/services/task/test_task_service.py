"""
TaskService 集成测试
测试任务的创建、更新、状态管理、取消、删除等功能。
"""

import pytest
from sqlalchemy.orm import Session

from src.core.exception_handler import OperationNotAllowedError, ResourceNotFoundError
from src.enums.task import TaskStatus
from src.models.task import AsyncTask, TaskHistory
from src.schemas.task import TaskCreate, TaskUpdate
from src.services.task.service import TaskService
from tests.shared.conftest_utils import AsyncSessionAdapter

pytestmark = pytest.mark.asyncio


class TaskTestDataFactory:
    """任务测试数据工厂"""

    @staticmethod
    def create_task_dict(**kwargs):
        default_data = {
            "task_type": "data_validation",
            "title": "测试任务",
            "description": "这是一个测试任务",
            "parameters": {},
            "config": {},
        }
        default_data.update(kwargs)
        return default_data


class TestTaskCreation:
    """任务创建测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        self.db = db_session
        self.async_db = AsyncSessionAdapter(db_session)
        self.service = TaskService()
        self.factory = TaskTestDataFactory()

    async def test_create_task_success(self):
        task_data = TaskCreate(**self.factory.create_task_dict())
        task = await self.service.create_task(
            self.async_db,
            obj_in=task_data,
            user_id="test_user",
        )

        assert task.id is not None
        assert task.title == "测试任务"
        assert task.status == TaskStatus.PENDING
        assert task.progress == 0

    async def test_create_task_with_user_id(self):
        task_data = TaskCreate(**self.factory.create_task_dict(title="用户任务"))
        task = await self.service.create_task(
            self.async_db,
            obj_in=task_data,
            user_id="user123",
        )
        assert task.user_id == "user123"

    async def test_create_task_creates_history(self):
        task_data = TaskCreate(**self.factory.create_task_dict())
        task = await self.service.create_task(
            self.async_db,
            obj_in=task_data,
            user_id="test_user",
        )

        history = (
            self.db.query(TaskHistory).filter(TaskHistory.task_id == task.id).first()
        )
        assert history is not None
        assert history.action == "created"
        assert "已创建" in history.message


class TestTaskStatusUpdate:
    """任务状态更新测试"""

    @pytest.fixture(autouse=True)
    async def setup(self, db_session: Session):
        self.db = db_session
        self.async_db = AsyncSessionAdapter(db_session)
        self.service = TaskService()
        self.factory = TaskTestDataFactory()
        task_data = TaskCreate(**self.factory.create_task_dict())
        self.task = await self.service.create_task(self.async_db, obj_in=task_data)

    async def test_update_task_status_to_running(self):
        updated = await self.service.update_task_status(
            self.async_db,
            task_id=self.task.id,
            status=TaskStatus.RUNNING,
        )
        assert updated.status == TaskStatus.RUNNING
        assert updated.started_at is not None

    async def test_update_task_status_to_completed(self):
        updated = await self.service.update_task_status(
            self.async_db,
            task_id=self.task.id,
            status=TaskStatus.COMPLETED,
        )
        assert updated.status == TaskStatus.COMPLETED
        assert updated.completed_at is not None
        assert updated.progress == 100

    async def test_update_task_status_with_progress(self):
        updated = await self.service.update_task_status(
            self.async_db,
            task_id=self.task.id,
            status=TaskStatus.RUNNING,
            progress=50,
        )
        assert updated.progress == 50

    async def test_update_task_status_to_failed(self):
        error_msg = "任务执行失败"
        updated = await self.service.update_task_status(
            self.async_db,
            task_id=self.task.id,
            status=TaskStatus.FAILED,
            error_message=error_msg,
        )
        assert updated.status == TaskStatus.FAILED
        assert updated.error_message == error_msg
        assert updated.completed_at is not None

    async def test_update_nonexistent_task_raises_error(self):
        with pytest.raises(ResourceNotFoundError, match="任务.*不存在"):
            await self.service.update_task_status(
                self.async_db,
                task_id="nonexistent-id",
                status=TaskStatus.RUNNING,
            )

    async def test_update_task_status_creates_history(self):
        await self.service.update_task_status(
            self.async_db,
            task_id=self.task.id,
            status=TaskStatus.RUNNING,
        )
        history = (
            self.db.query(TaskHistory)
            .filter(
                TaskHistory.task_id == self.task.id,
                TaskHistory.action == "status_changed",
            )
            .first()
        )
        assert history is not None


class TestTaskUpdate:
    """任务更新测试"""

    @pytest.fixture(autouse=True)
    async def setup(self, db_session: Session):
        self.db = db_session
        self.async_db = AsyncSessionAdapter(db_session)
        self.service = TaskService()
        self.factory = TaskTestDataFactory()
        task_data = TaskCreate(**self.factory.create_task_dict())
        self.task = await self.service.create_task(self.async_db, obj_in=task_data)

    async def test_update_task_error_message(self):
        updated = await self.service.update_task(
            self.async_db,
            task_id=self.task.id,
            obj_in=TaskUpdate(error_message="测试错误信息"),
        )
        assert updated.error_message == "测试错误信息"

    async def test_update_task_status_via_update(self):
        updated = await self.service.update_task(
            self.async_db,
            task_id=self.task.id,
            obj_in=TaskUpdate(status=TaskStatus.RUNNING),
        )
        assert updated.status == TaskStatus.RUNNING

    async def test_update_completed_task_raises_error(self):
        await self.service.update_task_status(
            self.async_db,
            task_id=self.task.id,
            status=TaskStatus.COMPLETED,
        )

        with pytest.raises(OperationNotAllowedError, match="已完成的任务无法更新"):
            await self.service.update_task(
                self.async_db,
                task_id=self.task.id,
                obj_in=TaskUpdate(),
            )


class TestTaskCancellation:
    """任务取消测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        self.db = db_session
        self.async_db = AsyncSessionAdapter(db_session)
        self.service = TaskService()
        self.factory = TaskTestDataFactory()

    async def test_cancel_pending_task_success(self):
        task = await self.service.create_task(
            self.async_db,
            obj_in=TaskCreate(**self.factory.create_task_dict()),
        )
        cancelled = await self.service.cancel_task(
            self.async_db,
            task_id=task.id,
            reason="测试取消",
        )
        assert cancelled.status == TaskStatus.CANCELLED
        assert "任务被取消" in (cancelled.error_message or "")

    async def test_cancel_running_task_success(self):
        task = await self.service.create_task(
            self.async_db,
            obj_in=TaskCreate(**self.factory.create_task_dict()),
        )
        await self.service.update_task_status(
            self.async_db,
            task_id=task.id,
            status=TaskStatus.RUNNING,
        )
        cancelled = await self.service.cancel_task(
            self.async_db,
            task_id=task.id,
            reason="用户取消",
        )
        assert cancelled.status == TaskStatus.CANCELLED

    async def test_cancel_completed_task_raises_error(self):
        task = await self.service.create_task(
            self.async_db,
            obj_in=TaskCreate(**self.factory.create_task_dict()),
        )
        await self.service.update_task_status(
            self.async_db,
            task_id=task.id,
            status=TaskStatus.COMPLETED,
        )

        with pytest.raises(OperationNotAllowedError, match="任务无法取消"):
            await self.service.cancel_task(self.async_db, task_id=task.id)

    async def test_cancel_nonexistent_task_raises_error(self):
        with pytest.raises(ResourceNotFoundError, match="任务.*不存在"):
            await self.service.cancel_task(self.async_db, task_id="nonexistent-id")


class TestTaskDeletion:
    """任务删除测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        self.db = db_session
        self.async_db = AsyncSessionAdapter(db_session)
        self.service = TaskService()
        self.factory = TaskTestDataFactory()

    async def test_delete_task_success(self):
        task = await self.service.create_task(
            self.async_db,
            obj_in=TaskCreate(**self.factory.create_task_dict()),
        )
        task_id = task.id

        await self.service.delete_task(self.async_db, task_id=task_id)

        deleted = self.db.query(AsyncTask).filter(AsyncTask.id == task_id).first()
        assert deleted is not None
        assert deleted.is_active is False

    async def test_delete_nonexistent_task_raises_error(self):
        with pytest.raises(ResourceNotFoundError, match="任务.*不存在"):
            await self.service.delete_task(self.async_db, task_id="nonexistent-id")
