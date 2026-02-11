import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import OperationNotAllowedError, ResourceNotFoundError
from ...crud.task import excel_task_config_crud, task_crud
from ...enums.task import TaskStatus, TaskType
from ...models.task import AsyncTask, ExcelTaskConfig, TaskHistory
from ...schemas.task import ExcelTaskConfigCreate, TaskCreate, TaskUpdate
from ...utils.file_security import validate_file_path


class TaskService:
    """任务服务层"""

    @staticmethod
    def _utcnow_naive() -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    def _cleanup_task_file(self, task: AsyncTask) -> bool:
        result_data = task.result_data
        if not isinstance(result_data, dict):
            return False
        file_path = result_data.get("file_path")
        if not file_path:
            return False

        allowed_dirs = [
            str(Path("temp_uploads").resolve()),
            tempfile.gettempdir(),
        ]
        if not validate_file_path(str(file_path), allowed_dirs):
            return False

        try:
            Path(str(file_path)).unlink(missing_ok=True)
            return True
        except Exception:
            return False

    async def create_task(
        self, db: AsyncSession, *, obj_in: TaskCreate, user_id: str | None = None
    ) -> AsyncTask:
        """创建新任务"""
        db_obj = AsyncTask(
            task_type=obj_in.task_type,
            title=obj_in.title,
            description=obj_in.description,
            parameters=obj_in.parameters,
            config=obj_in.config,
            user_id=user_id,
            status=TaskStatus.PENDING,
            progress=0,
        )

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        task_id_value: str = getattr(db_obj, "id")
        user_id_value: str = user_id or ""
        await self.create_history(
            db=db,
            task_id=task_id_value,
            action="created",
            message=f"任务 '{db_obj.title}' 已创建",
            user_id=user_id_value,
        )

        return db_obj

    async def update_task_status(
        self,
        db: AsyncSession,
        *,
        task_id: str,
        status: TaskStatus,
        progress: int | None = None,
        error_message: str | None = None,
    ) -> AsyncTask:
        """更新任务状态"""
        task: AsyncTask | None = await task_crud.get(db, task_id)
        if not task:
            raise ResourceNotFoundError("任务", task_id)

        old_status = task.status

        update_data: dict[str, Any] = {"status": status}

        if old_status == TaskStatus.PENDING and status == TaskStatus.RUNNING:
            update_data["started_at"] = self._utcnow_naive()

        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            update_data["completed_at"] = self._utcnow_naive()
            if status == TaskStatus.COMPLETED:
                update_data["progress"] = 100

        if progress is not None:
            update_data["progress"] = progress

        if error_message is not None:
            update_data["error_message"] = error_message

        # Apply updates
        for field, value in update_data.items():
            setattr(task, field, value)

        db.add(task)
        await db.commit()
        await db.refresh(task)

        if status != old_status:
            task_id_value: str = getattr(task, "id")
            task_user_id: str | None = getattr(task, "user_id", None)
            status_details: dict[str, Any] = {
                "old_status": old_status,
                "new_status": status,
            }
            await self.create_history(
                db=db,
                task_id=task_id_value,
                action="status_changed",
                message=f"任务状态从 {old_status} 变更为 {status}"
                + (f": {error_message}" if error_message else ""),
                user_id=task_user_id or "",
                details=status_details,
            )

        return task

    async def update_task(
        self, db: AsyncSession, *, task_id: str, obj_in: TaskUpdate
    ) -> AsyncTask:
        """通用更新任务"""
        task: AsyncTask | None = await task_crud.get(db, task_id)
        if not task:
            raise ResourceNotFoundError("任务", task_id)

        if task.status in [
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ]:
            raise OperationNotAllowedError(
                "已完成的任务无法更新",
                reason="task_status_final",
            )

        update_data: dict[str, Any] = obj_in.model_dump(exclude_unset=True)
        old_status: str | None = None
        new_status: str | None = None
        if "status" in update_data:
            new_status = str(update_data["status"])
            old_status = task.status

            if old_status == TaskStatus.PENDING and new_status == TaskStatus.RUNNING:
                update_data["started_at"] = self._utcnow_naive()

            if new_status in [
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            ]:
                update_data["completed_at"] = self._utcnow_naive()
                if new_status == TaskStatus.COMPLETED:
                    update_data["progress"] = 100

        for field, value in update_data.items():
            setattr(task, field, value)

        db.add(task)
        await db.commit()
        await db.refresh(task)

        if (
            "status" in update_data
            and old_status is not None
            and new_status is not None
            and new_status != old_status
        ):
            task_id_value: str = getattr(task, "id")
            task_user_id: str | None = getattr(task, "user_id", None)
            status_details: dict[str, Any] = {
                "old_status": old_status,
                "new_status": new_status,
            }
            await self.create_history(
                db=db,
                task_id=task_id_value,
                action="status_changed",
                message=f"任务状态从 {old_status} 变更为 {new_status}",
                user_id=task_user_id or "",
                details=status_details,
            )

        return task

    async def cancel_task(
        self, db: AsyncSession, *, task_id: str, reason: str | None = None
    ) -> AsyncTask:
        """取消任务"""
        task = await task_crud.get(db, task_id)
        if not task:
            raise ResourceNotFoundError("任务", task_id)

        if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            raise OperationNotAllowedError(
                "任务无法取消",
                reason="task_status_not_cancelable",
            )

        error_msg = f"任务被取消: {reason if reason else '无原因'}"
        return await self.update_task_status(
            db, task_id=task_id, status=TaskStatus.CANCELLED, error_message=error_msg
        )

    async def delete_task(self, db: AsyncSession, *, task_id: str) -> None:
        """删除任务"""
        task = await task_crud.get(db, task_id)
        if not task:
            raise ResourceNotFoundError("任务", task_id)

        cleaned = self._cleanup_task_file(task)
        if cleaned and isinstance(task.result_data, dict):
            task.result_data = {**task.result_data, "file_path": None}

        setattr(task, "is_active", False)
        db.add(task)
        await db.commit()

        task_user_id: str | None = getattr(task, "user_id", None)
        await self.create_history(
            db=db,
            task_id=task_id,
            action="deleted",
            message=f"任务 '{task.title}' 已删除",
            user_id=task_user_id or "",
        )

    async def create_history(
        self,
        db: AsyncSession,
        *,
        task_id: str,
        action: str,
        message: str,
        user_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> TaskHistory:
        """创建历史记录"""
        history = TaskHistory(
            task_id=task_id,
            action=action,
            message=message,
            user_id=user_id,
            details=details or {},
        )
        db.add(history)
        await db.commit()
        await db.refresh(history)
        return history

    async def get_statistics(
        self, db: AsyncSession, *, user_id: str | None = None
    ) -> dict[str, Any]:
        return await task_crud.get_statistics_async(db, user_id=user_id)

    async def get_tasks(
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
    ) -> tuple[list[AsyncTask], int]:
        tasks = await task_crud.get_multi_async(
            db=db,
            skip=skip,
            limit=limit,
            task_type=task_type,
            status=status,
            user_id=user_id,
            created_after=created_after,
            created_before=created_before,
            order_by=order_by,
            order_dir=order_dir,
        )
        total = await task_crud.count_async(
            db=db,
            task_type=task_type,
            status=status,
            user_id=user_id,
            created_after=created_after,
            created_before=created_before,
        )
        return tasks, total

    async def get_task(self, db: AsyncSession, *, task_id: str) -> AsyncTask | None:
        return await task_crud.get(db=db, id=task_id)

    async def get_task_history(
        self, db: AsyncSession, *, task_id: str
    ) -> list[TaskHistory]:
        return await task_crud.get_history_async(db=db, task_id=task_id)

    async def get_running_tasks(
        self,
        db: AsyncSession,
        *,
        user_id: str | None = None,
        limit: int = 100,
    ) -> list[AsyncTask]:
        return await task_crud.get_multi_async(
            db=db,
            limit=limit,
            status=TaskStatus.RUNNING.value,
            user_id=user_id,
            order_by="started_at",
            order_dir="asc",
        )

    async def get_recent_tasks(
        self,
        db: AsyncSession,
        *,
        user_id: str | None = None,
        limit: int = 10,
    ) -> list[AsyncTask]:
        return await task_crud.get_multi_async(
            db=db,
            limit=limit,
            user_id=user_id,
            order_by="created_at",
            order_dir="desc",
        )

    async def cleanup_old_tasks(
        self, db: AsyncSession, *, days: int, dry_run: bool
    ) -> dict[str, Any]:
        """清理过期任务"""
        cutoff_date = self._utcnow_naive() - timedelta(days=days)
        old_tasks = await task_crud.get_cleanup_candidates_async(
            db,
            cutoff_date=cutoff_date,
        )

        if dry_run:
            dry_run_result: dict[str, Any] = {
                "message": f"试运行模式，发现 {len(old_tasks)} 个可清理的任务",
                "cleanup_date": cutoff_date.isoformat(),
                "task_count": len(old_tasks),
            }
            return dry_run_result

        count = 0
        for task in old_tasks:
            cleaned = False
            if task.task_type == TaskType.EXCEL_EXPORT:
                cleaned = self._cleanup_task_file(task)
                if cleaned and isinstance(task.result_data, dict):
                    task.result_data = {**task.result_data, "file_path": None}
            setattr(task, "is_active", False)
            count += 1

        await db.commit()
        cleanup_result: dict[str, Any] = {
            "message": f"成功清理 {count} 个过期任务",
            "cleanup_date": cutoff_date.isoformat(),
            "cleaned_count": count,
        }
        return cleanup_result

    async def create_excel_config(
        self,
        db: AsyncSession,
        *,
        obj_in: ExcelTaskConfigCreate,
        user_id: str | None = None,
    ) -> ExcelTaskConfig:
        if obj_in.is_default:
            await excel_task_config_crud.unset_default_configs_async(
                db,
                config_type=obj_in.config_type,
                task_type=obj_in.task_type,
            )

        payload = obj_in.model_dump()
        if user_id is not None and user_id.strip() != "":
            payload["created_by"] = user_id

        config: ExcelTaskConfig = await excel_task_config_crud.create(
            db, obj_in=payload
        )
        return config

    async def get_excel_configs(
        self,
        db: AsyncSession,
        *,
        config_type: str | None = None,
        task_type: str | None = None,
        limit: int = 50,
    ) -> list[ExcelTaskConfig]:
        return await excel_task_config_crud.get_multi_async(
            db=db,
            limit=limit,
            config_type=config_type,
            task_type=task_type,
        )

    async def get_default_excel_config(
        self,
        db: AsyncSession,
        *,
        config_type: str,
        task_type: str,
    ) -> ExcelTaskConfig | None:
        return await excel_task_config_crud.get_default_async(
            db=db,
            config_type=config_type,
            task_type=task_type,
        )

    async def get_excel_config(
        self, db: AsyncSession, *, config_id: str
    ) -> ExcelTaskConfig | None:
        return await excel_task_config_crud.get(db=db, id=config_id)

    async def update_excel_config(
        self,
        db: AsyncSession,
        *,
        config_id: str,
        config_data: dict[str, Any],
    ) -> ExcelTaskConfig:
        config = await self.get_excel_config(db, config_id=config_id)
        if not config:
            raise ResourceNotFoundError("Excel配置", config_id)

        if config_data.get("is_default") is True:
            if config.config_type is None or config.task_type is None:
                raise OperationNotAllowedError(
                    "Excel配置缺少类型信息",
                    reason="excel_config_missing_type",
                )
            await excel_task_config_crud.unset_default_configs_async(
                db,
                config_type=config.config_type,
                task_type=config.task_type,
                exclude_config_id=config_id,
            )

        return await excel_task_config_crud.update(
            db=db,
            db_obj=config,
            obj_in=config_data,
        )

    async def delete_excel_config(
        self, db: AsyncSession, *, config_id: str
    ) -> bool:
        config = await self.get_excel_config(db, config_id=config_id)
        if not config:
            return False

        await excel_task_config_crud.update(
            db=db,
            db_obj=config,
            obj_in={"is_active": False},
        )
        return True


task_service = TaskService()
