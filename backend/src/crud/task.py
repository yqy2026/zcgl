from datetime import datetime
from typing import Any

from sqlalchemy import and_, asc, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from ..enums.task import TaskStatus, TaskType
from ..models.task import AsyncTask, ExcelTaskConfig, TaskHistory
from ..schemas.task import ExcelTaskConfigCreate, TaskCreate, TaskUpdate
from .base import CRUDBase


class TaskCRUD(CRUDBase[AsyncTask, TaskCreate, TaskUpdate]):
    """任务CRUD操作类"""

    def _apply_task_filters(
        self,
        query: Any,
        *,
        task_type: str | None = None,
        status: str | None = None,
        user_id: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        filters: dict[str, Any] | None = None,
    ) -> Any:
        """应用任务筛选条件（用于列表与统计）"""
        if filters:
            for field, value in filters.items():
                if hasattr(AsyncTask, field) and value is not None:
                    query = query.filter(getattr(AsyncTask, field) == value)

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

        return query

    async def create_async(
        self,
        db: AsyncSession,
        *,
        obj_in: TaskCreate | dict[str, Any],
        commit: bool = True,
        **kwargs: Any,
    ) -> AsyncTask:
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            obj_in_data = obj_in.model_dump()

        obj_in_data.update(kwargs)
        db_obj = AsyncTask(**obj_in_data)
        db.add(db_obj)
        if commit:
            await db.commit()
            await db.refresh(db_obj)
        else:
            await db.flush()
            await db.refresh(db_obj)
        return db_obj

    async def get_multi_async(
        self,
        db: AsyncSession,
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
        filters: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> list[AsyncTask]:
        stmt = select(AsyncTask).filter(AsyncTask.is_active.is_(True))
        stmt = self._apply_task_filters(
            stmt,
            task_type=task_type,
            status=status,
            user_id=user_id,
            created_after=created_after,
            created_before=created_before,
            filters=filters,
        )

        if hasattr(AsyncTask, order_by):
            order_column = getattr(AsyncTask, order_by)
            if order_dir.lower() == "desc":
                stmt = stmt.order_by(desc(order_column))
            else:
                stmt = stmt.order_by(asc(order_column))

        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def count_async(
        self,
        db: AsyncSession,
        filters: dict[str, Any] | None = None,
        task_type: str | None = None,
        status: str | None = None,
        user_id: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        **kwargs: Any,
    ) -> int:
        stmt = select(func.count(AsyncTask.id)).filter(AsyncTask.is_active.is_(True))
        stmt = self._apply_task_filters(
            stmt,
            task_type=task_type,
            status=status,
            user_id=user_id,
            created_after=created_after,
            created_before=created_before,
            filters=filters,
        )
        result = await db.execute(stmt)
        return int(result.scalar() or 0)

    async def get_statistics_async(
        self, db: AsyncSession, user_id: str | None = None
    ) -> dict[str, Any]:
        conditions: list[ColumnElement[bool]] = [AsyncTask.is_active.is_(True)]
        if user_id:
            conditions.append(AsyncTask.user_id == user_id)

        total_stmt = select(func.count(AsyncTask.id)).where(*conditions)
        total_tasks = int((await db.execute(total_stmt)).scalar() or 0)

        status_rows = (
            await db.execute(
                select(AsyncTask.status, func.count(AsyncTask.id))
                .where(*conditions)
                .group_by(AsyncTask.status)
            )
        ).all()
        allowed_statuses = {status.value for status in TaskStatus}
        by_status = {
            str(status): int(count or 0)
            for status, count in status_rows
            if (
                status is not None
                and str(status) in allowed_statuses
                and int(count or 0) > 0
            )
        }
        running_tasks = by_status.get(TaskStatus.RUNNING.value, 0)
        completed_tasks = by_status.get(TaskStatus.COMPLETED.value, 0)
        failed_tasks = by_status.get(TaskStatus.FAILED.value, 0)

        type_rows = (
            await db.execute(
                select(AsyncTask.task_type, func.count(AsyncTask.id))
                .where(*conditions)
                .group_by(AsyncTask.task_type)
            )
        ).all()
        allowed_types = {task_type.value for task_type in TaskType}
        by_type = {
            str(task_type): int(count or 0)
            for task_type, count in type_rows
            if (
                task_type is not None
                and str(task_type) in allowed_types
                and int(count or 0) > 0
            )
        }

        completed_rows_stmt = select(
            AsyncTask.started_at, AsyncTask.completed_at
        ).where(
            *conditions,
            AsyncTask.status == TaskStatus.COMPLETED.value,
            AsyncTask.started_at.isnot(None),
            AsyncTask.completed_at.isnot(None),
        )
        completed_rows = (await db.execute(completed_rows_stmt)).all()
        avg_duration = 0.0
        if completed_rows:
            durations: list[float] = []
            for started_at, completed_at in completed_rows:
                if started_at is None or completed_at is None:
                    continue
                durations.append((completed_at - started_at).total_seconds())
            if durations:
                avg_duration = sum(durations) / len(durations)

        return {
            "total_tasks": total_tasks,
            "running_tasks": running_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "by_type": by_type,
            "by_status": by_status,
            "avg_duration": avg_duration,
        }

    async def get_history_async(
        self, db: AsyncSession, task_id: str
    ) -> list[TaskHistory]:
        stmt = (
            select(TaskHistory)
            .filter(TaskHistory.task_id == task_id)
            .order_by(desc(TaskHistory.created_at))
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_cleanup_candidates_async(
        self, db: AsyncSession, *, cutoff_date: datetime
    ) -> list[AsyncTask]:
        stmt = select(AsyncTask).filter(
            and_(
                AsyncTask.created_at < cutoff_date,
                AsyncTask.status.in_(
                    [
                        TaskStatus.COMPLETED.value,
                        TaskStatus.FAILED.value,
                        TaskStatus.CANCELLED.value,
                    ]
                ),
                AsyncTask.is_active.is_(True),
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # create_history, update status logic, etc moved to Service.


class ExcelTaskConfigCRUD(CRUDBase[ExcelTaskConfig, ExcelTaskConfigCreate, TaskUpdate]):
    """Excel任务配置CRUD操作类"""

    async def get_default_async(
        self, db: AsyncSession, config_type: str, task_type: str
    ) -> ExcelTaskConfig | None:
        stmt = select(ExcelTaskConfig).filter(
            and_(
                ExcelTaskConfig.config_type == config_type,
                ExcelTaskConfig.task_type == task_type,
                ExcelTaskConfig.is_default.is_(True),
                ExcelTaskConfig.is_active.is_(True),
            )
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_multi_async(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        config_type: str | None = None,
        task_type: str | None = None,
        is_active: bool = True,
        **kwargs: Any,
    ) -> list[ExcelTaskConfig]:
        stmt = select(ExcelTaskConfig).filter(ExcelTaskConfig.is_active == is_active)

        if config_type:
            stmt = stmt.filter(ExcelTaskConfig.config_type == config_type)
        if task_type:
            stmt = stmt.filter(ExcelTaskConfig.task_type == task_type)

        stmt = (
            stmt.order_by(
                ExcelTaskConfig.is_default.desc(), ExcelTaskConfig.created_at.desc()
            )
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def unset_default_configs_async(
        self,
        db: AsyncSession,
        *,
        config_type: str,
        task_type: str,
        exclude_config_id: str | None = None,
    ) -> None:
        conditions = [
            ExcelTaskConfig.config_type == config_type,
            ExcelTaskConfig.task_type == task_type,
            ExcelTaskConfig.is_default.is_(True),
        ]
        if exclude_config_id is not None and exclude_config_id.strip() != "":
            conditions.append(ExcelTaskConfig.id != exclude_config_id)

        stmt = update(ExcelTaskConfig).where(and_(*conditions)).values(is_default=False)
        await db.execute(stmt)

    # create method in base is fine, extra default toggle logic moved to service


# 创建CRUD实例
task_crud = TaskCRUD(AsyncTask)
excel_task_config_crud = ExcelTaskConfigCRUD(ExcelTaskConfig)
