from datetime import datetime
from typing import Any

from sqlalchemy import and_, asc, desc
from sqlalchemy.orm import Session

from ..enums.task import TaskStatus, TaskType
from ..models.task import AsyncTask, ExcelTaskConfig, TaskHistory
from ..schemas.task import ExcelTaskConfigCreate, TaskCreate, TaskUpdate
from .base import CRUDBase


class TaskCRUD(CRUDBase[AsyncTask, TaskCreate, TaskUpdate]):
    """任务CRUD操作类"""

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        task_type: str | None = None,
        status: str | None = None,
        user_id: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        order_by: str = "created_at",
        order_dir: str = "desc",
        **kwargs: Any,  # 扩展参数，与基类兼容
    ) -> list[AsyncTask]:
        """获取任务列表"""
        query = db.query(AsyncTask).filter(AsyncTask.is_active)

        # 应用筛选条件
        if task_type:
            query = query.filter(AsyncTask.task_type == task_type)
        if status:
            query = query.filter(AsyncTask.status == status)
        if user_id:
            query = query.filter(AsyncTask.user_id == user_id)
        if created_after:
            query = query.filter(AsyncTask.created_at >= created_after)
        if created_before:
            query = query.filter(AsyncTask.created_at <= created_before)

        # 应用排序
        if hasattr(AsyncTask, order_by):
            order_column = getattr(AsyncTask, order_by)
            if order_dir.lower() == "desc":
                query = query.order_by(desc(order_column))
            else:
                query = query.order_by(asc(order_column))

        # 应用分页
        return query.offset(skip).limit(limit).all()

    def count(
        self,
        db: Session,
        *,
        task_type: str | None = None,
        status: str | None = None,
        **kwargs: Any,  # 扩展参数，与基类兼容
    ) -> int:
        """统计任务数量"""
        query = db.query(AsyncTask).filter(AsyncTask.is_active)

        if task_type:
            query = query.filter(AsyncTask.task_type == task_type)
        if status:
            query = query.filter(AsyncTask.status == status)

        return query.count()

    def get_statistics(self, db: Session, user_id: str | None = None) -> dict[str, Any]:
        """获取任务统计信息"""
        base_query = db.query(AsyncTask).filter(AsyncTask.is_active)

        if user_id:
            base_query = base_query.filter(AsyncTask.user_id == user_id)

        total_tasks = base_query.count()
        # Simplified counting mainly for read operations
        running_tasks = base_query.filter(
            AsyncTask.status == TaskStatus.RUNNING
        ).count()
        completed_tasks = base_query.filter(
            AsyncTask.status == TaskStatus.COMPLETED
        ).count()
        failed_tasks = base_query.filter(AsyncTask.status == TaskStatus.FAILED).count()

        # 按类型统计
        by_type = {}
        for task_type in TaskType:
            count = base_query.filter(AsyncTask.task_type == task_type).count()
            if count > 0:
                by_type[task_type.value] = count

        # 按状态统计
        by_status = {}
        for status in TaskStatus:
            count = base_query.filter(AsyncTask.status == status).count()
            if count > 0:
                by_status[status.value] = count

        # 平均持续时间
        completed_tasks_query = base_query.filter(
            and_(
                AsyncTask.status == TaskStatus.COMPLETED,
                AsyncTask.started_at.isnot(None),
                AsyncTask.completed_at.isnot(None),
            )
        )

        avg_duration = 0
        if completed_tasks_query.count() > 0:
            total_duration = sum(
                (task.completed_at - task.started_at).total_seconds()
                for task in completed_tasks_query.all()
            )
            avg_duration = total_duration / completed_tasks_query.count()

        return {
            "total_tasks": total_tasks,
            "running_tasks": running_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "by_type": by_type,
            "by_status": by_status,
            "avg_duration": avg_duration,
        }

    def get_history(self, db: Session, task_id: str) -> list[TaskHistory]:
        """获取任务历史记录"""
        return (
            db.query(TaskHistory)
            .filter(TaskHistory.task_id == task_id)
            .order_by(desc(TaskHistory.created_at))
            .all()
        )

    # create_history, update status logic, etc moved to Service.


class ExcelTaskConfigCRUD(CRUDBase[ExcelTaskConfig, ExcelTaskConfigCreate, TaskUpdate]):
    """Excel任务配置CRUD操作类"""

    def get_default(
        self, db: Session, config_type: str, task_type: str
    ) -> ExcelTaskConfig | None:
        """获取默认配置"""
        return (
            db.query(ExcelTaskConfig)
            .filter(
                and_(
                    ExcelTaskConfig.config_type == config_type,
                    ExcelTaskConfig.task_type == task_type,
                    ExcelTaskConfig.is_default,
                    ExcelTaskConfig.is_active,
                )
            )
            .first()
        )

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        config_type: str | None = None,
        task_type: str | None = None,
        is_active: bool = True,
        **kwargs: Any,  # 扩展参数，与基类兼容
    ) -> list[ExcelTaskConfig]:
        """获取配置列表"""
        query = db.query(ExcelTaskConfig).filter(ExcelTaskConfig.is_active == is_active)

        if config_type:
            query = query.filter(ExcelTaskConfig.config_type == config_type)
        if task_type:
            query = query.filter(ExcelTaskConfig.task_type == task_type)

        return (
            query.order_by(
                ExcelTaskConfig.is_default.desc(), ExcelTaskConfig.created_at.desc()
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    # create method in base is fine, extra default toggle logic moved to service


# 创建CRUD实例
task_crud = TaskCRUD(AsyncTask)
excel_task_config_crud = ExcelTaskConfigCRUD(ExcelTaskConfig)
