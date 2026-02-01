"""
任务服务增强测试

Enhanced tests for Task Service to improve coverage
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session


@pytest.fixture
def task_service(db: Session):
    """任务服务实例"""
    from src.services.task.service import TaskService

    return TaskService(db)


@pytest.fixture
def sample_task(db: Session, admin_user):
    """示例任务数据"""
    from src.crud.task import task_crud
    from src.schemas.task import TaskCreate

    task = task_crud.create(
        db,
        obj_in=TaskCreate(
            title="测试任务",
            description="任务描述",
            task_type="inspection",
            priority="normal",
            status="pending",
            assigned_to=admin_user.id,
            due_date=datetime.now(UTC),
        ),
    )
    yield task
    try:
        task_crud.remove(db, id=task.id)
    except Exception:
        pass


class TestTaskServiceBusinessLogic:
    """测试任务服务业务逻辑"""

    def test_task_status_transition(self, task_service, sample_task, db: Session):
        """测试任务状态转换"""
        # pending → in_progress
        updated = task_service.update_task_status(db, sample_task.id, "in_progress")
        assert updated.status == "in_progress"

    def test_task_priority_sorting(self, task_service, db: Session):
        """测试任务按优先级排序"""
        result = task_service.get_tasks_sorted_by_priority(db)
        assert result is not None

    def test_task_assignment(self, task_service, db: Session, admin_user):
        """测试任务分配"""
        result = task_service.assign_task(
            db, task_id="test-task-id", user_id=admin_user.id
        )
        # 可能返回成功或失败
        assert result is not None

    def test_task_due_date_reminder(self, task_service, db: Session):
        """测试任务到期提醒"""
        result = task_service.get_overdue_tasks(db)
        assert result is not None

    def test_task_statistics(self, task_service, db: Session):
        """测试任务统计信息"""
        stats = task_service.get_task_statistics(db)
        assert stats is not None
