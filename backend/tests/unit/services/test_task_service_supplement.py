"""
任务服务补充测试

Supplemental tests for Task Service to increase coverage
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
            description="这是一个测试任务",
            task_type="inspection",
            priority="medium",
            due_date=datetime.now(UTC),
            assignee_id=admin_user.id,
            creator_id=admin_user.id,
        ),
    )
    yield task
    try:
        task_crud.remove(db, id=task.id)
    except Exception:
        pass


class TestTaskServiceSupplement:
    """测试任务服务补充功能"""

    def test_get_overdue_tasks(self, task_service, db: Session):
        """测试获取过期任务"""

        overdue_tasks = task_service.get_overdue_tasks(db, as_of_date=datetime.now(UTC))
        assert overdue_tasks is not None
        assert isinstance(overdue_tasks, list)

    def test_get_tasks_by_priority(self, task_service, db: Session):
        """测试按优先级获取任务"""
        high_priority_tasks = task_service.get_tasks_by_priority(db, priority="high")
        assert high_priority_tasks is not None

    def test_get_upcoming_tasks(self, task_service, db: Session):
        """测试获取即将到期的任务"""

        upcoming_tasks = task_service.get_upcoming_tasks(db, days_within=7)
        assert upcoming_tasks is not None

    def test_task_dependency_validation(self, task_service, sample_task, db: Session):
        """测试任务依赖验证"""
        # 创建前置任务
        from src.crud.task import task_crud
        from src.schemas.task import TaskCreate

        prerequisite_task = task_crud.create(
            db,
            obj_in=TaskCreate(
                title="前置任务",
                description="需要先完成的任务",
                task_type="inspection",
                priority="high",
                due_date=datetime.now(UTC),
                assignee_id=sample_task.assignee_id,
                creator_id=sample_task.creator_id,
            ),
        )

        # 尝试添加依赖
        result = task_service.add_task_dependency(
            db, task_id=sample_task.id, prerequisite_id=prerequisite_task.id
        )
        assert result is not None

    def test_validate_circular_dependency(self, task_service, sample_task, db: Session):
        """测试验证循环依赖"""
        # 任务A依赖任务B，任务B依赖任务A - 应该被拒绝
        from src.crud.task import task_crud
        from src.schemas.task import TaskCreate

        task_b = task_crud.create(
            db,
            obj_in=TaskCreate(
                title="任务B",
                description="依赖任务A",
                task_type="inspection",
                priority="medium",
                due_date=datetime.now(UTC),
                assignee_id=sample_task.assignee_id,
                creator_id=sample_task.creator_id,
            ),
        )

        # 添加A依赖B
        task_service.add_task_dependency(
            db, task_id=sample_task.id, prerequisite_id=task_b.id
        )

        # 尝试添加B依赖A - 应该失败（循环依赖）
        with pytest.raises(ValueError):
            task_service.add_task_dependency(
                db, task_id=task_b.id, prerequisite_id=sample_task.id
            )

    def test_batch_update_task_status(self, task_service, db: Session):
        """测试批量更新任务状态"""
        task_ids = ["task-1", "task-2"]
        new_status = "completed"

        result = task_service.batch_update_task_status(
            db, task_ids=task_ids, new_status=new_status
        )
        assert result is not None

    def test_get_task_statistics(self, task_service, db: Session):
        """测试获取任务统计信息"""
        stats = task_service.get_task_statistics(db)
        assert stats is not None
        assert "total_count" in stats
        assert "by_status" in stats
        assert "by_priority" in stats

    def test_search_tasks_advanced(self, task_service, db: Session):
        """测试高级搜索任务"""
        result = task_service.search_tasks(
            db,
            keyword="测试",
            task_type="inspection",
            priority="medium",
            status="pending",
        )
        assert result is not None

    def test_assign_task_to_user(self, task_service, sample_task, db: Session):
        """测试分配任务给用户"""
        new_assignee_id = "user-002"

        result = task_service.assign_task(
            db, task_id=sample_task.id, assignee_id=new_assignee_id
        )
        assert result is not None
        assert result.assignee_id == new_assignee_id

    def test_task_comment_operations(self, task_service, sample_task):
        """测试任务评论操作"""
        # 添加评论
        comment = task_service.add_task_comment(
            task_id=sample_task.id,
            user_id=sample_task.creator_id,
            content="这是一条测试评论",
        )
        assert comment is not None

        # 获取评论列表
        comments = task_service.get_task_comments(task_id=sample_task.id)
        assert comments is not None
        assert len(comments) > 0

    def test_task_attachment_operations(self, task_service, sample_task):
        """测试任务附件操作"""
        # 添加附件
        attachment = task_service.add_task_attachment(
            task_id=sample_task.id,
            file_name="test_document.pdf",
            file_path="/uploads/test_document.pdf",
            file_size=1024,
            uploaded_by=sample_task.creator_id,
        )
        assert attachment is not None

        # 获取附件列表
        attachments = task_service.get_task_attachments(task_id=sample_task.id)
        assert attachments is not None

    def test_task_reminder_check(self, task_service, db: Session):
        """测试任务提醒检查"""
        reminders = task_service.check_due_soon_tasks(db, hours_before=24)
        assert reminders is not None

    def test_get_task_by_assignee(self, task_service, db: Session):
        """测试按被分配人获取任务"""
        tasks = task_service.get_tasks_by_assignee(db, assignee_id="user-001")
        assert tasks is not None

    def test_get_task_by_creator(self, task_service, db: Session):
        """测试按创建人获取任务"""
        tasks = task_service.get_tasks_by_creator(db, creator_id="user-001")
        assert tasks is not None

    def test_task_completion_validation(self, task_service, sample_task, db: Session):
        """测试任务完成验证"""
        # 尝试完成任务
        result = task_service.complete_task(
            db, task_id=sample_task.id, completion_note="任务已完成"
        )
        assert result is not None
        assert result.status == "completed"

    def test_task_reopening(self, task_service, sample_task, db: Session):
        """测试重新打开任务"""
        # 先完成任务
        task_service.complete_task(
            db, task_id=sample_task.id, completion_note="临时完成"
        )

        # 重新打开
        reopened = task_service.reopen_task(
            db, task_id=sample_task.id, reason="需要补充材料"
        )
        assert reopened is not None
        assert reopened.status == "pending" or reopened.status == "in_progress"

    def test_task_priority_change(self, task_service, sample_task, db: Session):
        """测试任务优先级变更"""
        updated = task_service.change_task_priority(
            db, task_id=sample_task.id, new_priority="high", reason="重要且紧急"
        )
        assert updated is not None
        assert updated.priority == "high"

    def test_get_task_timeline(self, task_service, sample_task):
        """测试获取任务时间线"""
        timeline = task_service.get_task_timeline(task_id=sample_task.id)
        assert timeline is not None
        assert isinstance(timeline, list)

    def test_task_due_date_extension(self, task_service, sample_task, db: Session):
        """测试任务到期日期延期"""
        from datetime import timedelta

        new_due_date = datetime.now(UTC) + timedelta(days=7)

        result = task_service.extend_due_date(
            db, task_id=sample_task.id, new_due_date=new_due_date, reason="需要更多时间"
        )
        assert result is not None

    def test_get_overdue_tasks_count(self, task_service, db: Session):
        """测试获取过期任务数量"""
        count = task_service.get_overdue_tasks_count(db, as_of_date=datetime.now(UTC))
        assert count is not None
        assert count >= 0
