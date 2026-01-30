"""
TaskService 集成测试
测试任务的创建、更新、状态管理、取消、删除等功能
"""

import pytest
from sqlalchemy.orm import Session

from src.core.exception_handler import OperationNotAllowedError, ResourceNotFoundError
from src.enums.task import TaskStatus
from src.models.task import AsyncTask, TaskHistory
from src.schemas.task import TaskCreate, TaskUpdate
from src.services.task.service import TaskService

# ============================================================================
# Test Data Factory
# ============================================================================


class TaskTestDataFactory:
    """任务测试数据工厂"""

    @staticmethod
    def create_task_dict(**kwargs):
        """生成任务创建数据"""
        default_data = {
            "task_type": "data_validation",  # 使用有效的task_type
            "title": "测试任务",
            "description": "这是一个测试任务",
            "parameters": {},
            "config": {},
        }
        default_data.update(kwargs)
        return default_data


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def task_service(db_session: Session):
    """TaskService实例（返回类而非实例，因为service在方法中接收db）"""
    return TaskService


# ============================================================================
# Test Class 1: Task Creation
# ============================================================================


class TestTaskCreation:
    """任务创建测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        self.db = db_session
        self.factory = TaskTestDataFactory()

    def test_create_task_success(self):
        """测试成功创建任务"""
        task_data = TaskCreate(**self.factory.create_task_dict())

        task = TaskService().create_task(self.db, obj_in=task_data, user_id="test_user")

        assert task.id is not None
        assert task.title == "测试任务"
        assert task.status == TaskStatus.PENDING
        assert task.progress == 0

    def test_create_task_with_user_id(self):
        """测试创建带用户ID的任务"""
        task_data = TaskCreate(
            **self.factory.create_task_dict(
                title="用户任务",
            )
        )

        task = TaskService().create_task(self.db, obj_in=task_data, user_id="user123")

        assert task.user_id == "user123"

    def test_create_task_creates_history(self):
        """测试创建任务时记录历史"""
        task_data = TaskCreate(**self.factory.create_task_dict())

        task = TaskService().create_task(self.db, obj_in=task_data, user_id="test_user")

        history = (
            self.db.query(TaskHistory).filter(TaskHistory.task_id == task.id).first()
        )

        assert history is not None
        assert history.action == "created"
        assert "已创建" in history.message


# ============================================================================
# Test Class 2: Task Status Update
# ============================================================================


class TestTaskStatusUpdate:
    """任务状态更新测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        self.db = db_session
        self.factory = TaskTestDataFactory()

        # 创建测试任务
        task_data = TaskCreate(**self.factory.create_task_dict())
        self.task = TaskService().create_task(self.db, obj_in=task_data)

    def test_update_task_status_to_running(self):
        """测试更新任务状态为运行中"""
        updated = TaskService().update_task_status(
            self.db, task_id=self.task.id, status=TaskStatus.RUNNING
        )

        assert updated.status == TaskStatus.RUNNING
        assert updated.started_at is not None

    def test_update_task_status_to_completed(self):
        """测试更新任务状态为已完成"""
        updated = TaskService().update_task_status(
            self.db, task_id=self.task.id, status=TaskStatus.COMPLETED
        )

        assert updated.status == TaskStatus.COMPLETED
        assert updated.completed_at is not None
        assert updated.progress == 100

    def test_update_task_status_with_progress(self):
        """测试更新任务状态和进度"""
        updated = TaskService().update_task_status(
            self.db, task_id=self.task.id, status=TaskStatus.RUNNING, progress=50
        )

        assert updated.progress == 50

    def test_update_task_status_to_failed(self):
        """测试更新任务状态为失败"""
        error_msg = "任务执行失败"
        updated = TaskService().update_task_status(
            self.db,
            task_id=self.task.id,
            status=TaskStatus.FAILED,
            error_message=error_msg,
        )

        assert updated.status == TaskStatus.FAILED
        assert updated.error_message == error_msg
        assert updated.completed_at is not None

    def test_update_nonexistent_task_raises_error(self):
        """测试更新不存在的任务抛出异常"""
        with pytest.raises(ResourceNotFoundError, match="任务.*不存在"):
            TaskService().update_task_status(
                self.db, task_id="nonexistent-id", status=TaskStatus.RUNNING
            )

    def test_update_task_status_creates_history(self):
        """测试更新任务状态时记录历史"""
        TaskService().update_task_status(
            self.db, task_id=self.task.id, status=TaskStatus.RUNNING
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
        assert "RUNNING" in history.message


# ============================================================================
# Test Class 3: Task Update
# ============================================================================


class TestTaskUpdate:
    """任务更新测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        self.db = db_session
        self.factory = TaskTestDataFactory()

        # 创建测试任务
        task_data = TaskCreate(**self.factory.create_task_dict())
        self.task = TaskService().create_task(self.db, obj_in=task_data)

    def test_update_task_error_message(self):
        """测试更新任务错误信息"""
        update_data = TaskUpdate(error_message="测试错误信息")

        updated = TaskService().update_task(
            self.db, task_id=self.task.id, obj_in=update_data
        )

        assert updated.error_message == "测试错误信息"

    def test_update_task_status_via_update(self):
        """测试通过update_task更新状态"""
        update_data = TaskUpdate(status=TaskStatus.RUNNING)

        updated = TaskService().update_task(
            self.db, task_id=self.task.id, obj_in=update_data
        )

        assert updated.status == TaskStatus.RUNNING

    def test_update_completed_task_raises_error(self):
        """测试更新已完成的任务抛出异常"""
        # 先将任务标记为完成
        TaskService().update_task_status(
            self.db, task_id=self.task.id, status=TaskStatus.COMPLETED
        )

        # 尝试更新已完成的任务
        update_data = TaskUpdate(title="新标题")

        with pytest.raises(OperationNotAllowedError, match="已完成的任务无法更新"):
            TaskService().update_task(self.db, task_id=self.task.id, obj_in=update_data)


# ============================================================================
# Test Class 4: Task Cancellation
# ============================================================================


class TestTaskCancellation:
    """任务取消测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        self.db = db_session
        self.factory = TaskTestDataFactory()

    def test_cancel_pending_task_success(self):
        """测试取消待处理任务"""
        task_data = TaskCreate(**self.factory.create_task_dict())
        task = TaskService().create_task(self.db, obj_in=task_data)

        cancelled = TaskService().cancel_task(
            self.db, task_id=task.id, reason="测试取消"
        )

        assert cancelled.status == TaskStatus.CANCELLED
        assert "任务被取消" in cancelled.error_message

    def test_cancel_running_task_success(self):
        """测试取消运行中的任务"""
        task_data = TaskCreate(**self.factory.create_task_dict())
        task = TaskService().create_task(self.db, obj_in=task_data)

        # 先将任务设为运行中
        TaskService().update_task_status(
            self.db, task_id=task.id, status=TaskStatus.RUNNING
        )

        # 取消任务
        cancelled = TaskService().cancel_task(
            self.db, task_id=task.id, reason="用户取消"
        )

        assert cancelled.status == TaskStatus.CANCELLED

    def test_cancel_completed_task_raises_error(self):
        """测试取消已完成的任务抛出异常"""
        task_data = TaskCreate(**self.factory.create_task_dict())
        task = TaskService().create_task(self.db, obj_in=task_data)

        # 先将任务标记为完成
        TaskService().update_task_status(
            self.db, task_id=task.id, status=TaskStatus.COMPLETED
        )

        # 尝试取消
        with pytest.raises(OperationNotAllowedError, match="任务无法取消"):
            TaskService().cancel_task(self.db, task_id=task.id)

    def test_cancel_nonexistent_task_raises_error(self):
        """测试取消不存在的任务抛出异常"""
        with pytest.raises(ResourceNotFoundError, match="任务不存在"):
            TaskService().cancel_task(self.db, task_id="nonexistent-id")


# ============================================================================
# Test Class 5: Task Deletion
# ============================================================================


class TestTaskDeletion:
    """任务删除测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        self.db = db_session
        self.factory = TaskTestDataFactory()

    def test_delete_task_success(self):
        """测试成功删除任务"""
        task_data = TaskCreate(**self.factory.create_task_dict())
        task = TaskService().create_task(self.db, obj_in=task_data)
        task_id = task.id

        TaskService().delete_task(self.db, task_id=task_id)

        # 验证任务已软删除(is_active=False)
        deleted = self.db.query(AsyncTask).filter(AsyncTask.id == task_id).first()
        assert deleted is not None
        assert deleted.is_active is False

    def test_delete_nonexistent_task_raises_error(self):
        """测试删除不存在的任务抛出异常"""
        with pytest.raises(ResourceNotFoundError, match="任务不存在"):
            TaskService().delete_task(self.db, task_id="nonexistent-id")
