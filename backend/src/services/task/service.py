from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from ...crud.task import excel_task_config_crud, task_crud
from ...enums.task import TaskStatus
from ...models.task import AsyncTask, ExcelTaskConfig, TaskHistory
from ...schemas.task import ExcelTaskConfigCreate, TaskCreate, TaskUpdate


class TaskService:
    """任务服务层"""

    def create_task(
        self, db: Session, *, obj_in: TaskCreate, user_id: str | None = None
    ) -> AsyncTask:
        """创建新任务"""
        # Logic moved from CRUD.create
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
        db.commit()
        db.refresh(db_obj)

        # Log creation history
        task_id_value: str = getattr(db_obj, "id")
        user_id_value: str = user_id or ""
        self.create_history(
            db=db,
            task_id=task_id_value,
            action="created",
            message=f"任务 '{db_obj.title}' 已创建",
            user_id=user_id_value,
        )

        return db_obj

    def update_task_status(
        self,
        db: Session,
        *,
        task_id: str,
        status: TaskStatus,
        progress: int | None = None,
        error_message: str | None = None,
    ) -> AsyncTask:
        """更新任务状态"""
        task: AsyncTask | None = task_crud.get(db, task_id)
        if not task:
            raise ValueError(f"任务 {task_id} 不存在")

        old_status = task.status

        update_data: dict[str, Any] = {"status": status}

        # Logic moved from CRUD.update
        # Start time
        if old_status == TaskStatus.PENDING and status == TaskStatus.RUNNING:
            update_data["started_at"] = datetime.now(UTC)

        # End time
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            update_data["completed_at"] = datetime.now(UTC)
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
        db.commit()
        db.refresh(task)

        # Log history
        if status != old_status:
            task_id_value: str = getattr(task, "id")
            task_user_id: str | None = getattr(task, "user_id", None)
            status_details: dict[str, Any] = {
                "old_status": old_status,
                "new_status": status,
            }
            self.create_history(
                db=db,
                task_id=task_id_value,
                action="status_changed",
                message=f"任务状态从 {old_status} 变更为 {status}"
                + (f": {error_message}" if error_message else ""),
                user_id=task_user_id or "",
                details=status_details,
            )

        return task

    def update_task(
        self, db: Session, *, task_id: str, obj_in: TaskUpdate
    ) -> AsyncTask:
        """通用更新任务"""
        task: AsyncTask | None = task_crud.get(db, task_id)
        if not task:
            raise ValueError(f"任务 {task_id} 不存在")

        # Check permissions/state logic if any (from API)
        if task.status in [
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ]:
            # Only allow updating active tasks generally, unless specific fields?
            # API says: "已完成的任务无法更新"
            raise ValueError("已完成的任务无法更新")

        # Reuse update_task_status logic if status changes, OR just generic update?
        # If status is in obj_in, we should be careful.
        # API logic was just CRUD update with status hooks in CRUD.
        # Let's handle generic update here but delegate status specific logic blocks if needed.

        update_data: dict[str, Any] = obj_in.model_dump(exclude_unset=True)
        if "status" in update_data:
            # Calling specific status update logic would be cleaner, but let's replicate logic locally to support single commit
            new_status: TaskStatus = update_data["status"]
            old_status = task.status

            if old_status == TaskStatus.PENDING and new_status == TaskStatus.RUNNING:
                update_data["started_at"] = datetime.now(UTC)

            if new_status in [
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            ]:
                update_data["completed_at"] = datetime.now(UTC)
                if new_status == TaskStatus.COMPLETED:
                    update_data["progress"] = 100

            # Log history later

        for field, value in update_data.items():
            setattr(task, field, value)

        db.add(task)
        db.commit()
        db.refresh(task)

        if "status" in update_data and update_data["status"] != old_status:
            task_id_value: str = getattr(task, "id")
            task_user_id: str | None = getattr(task, "user_id", None)
            status_details: dict[str, Any] = {
                "old_status": old_status,
                "new_status": new_status,
            }
            self.create_history(
                db=db,
                task_id=task_id_value,
                action="status_changed",
                message=f"任务状态从 {old_status} 变更为 {new_status}",
                user_id=task_user_id or "",
                details=status_details,
            )

        return task

    def cancel_task(
        self, db: Session, *, task_id: str, reason: str | None = None
    ) -> AsyncTask:
        """取消任务"""
        task = task_crud.get(db, task_id)
        if not task:
            raise ValueError("任务不存在")

        if task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            raise ValueError("任务无法取消")

        error_msg = f"任务被取消: {reason if reason else '无原因'}"
        return self.update_task_status(
            db, task_id=task_id, status=TaskStatus.CANCELLED, error_message=error_msg
        )

    def delete_task(self, db: Session, *, task_id: str) -> None:
        """删除任务"""
        task = task_crud.get(db, task_id)
        if not task:
            raise ValueError("任务不存在")

        setattr(task, "is_active", False)
        db.add(task)
        db.commit()

        task_user_id: str | None = getattr(task, "user_id", None)
        self.create_history(
            db=db,
            task_id=task_id,
            action="deleted",
            message=f"任务 '{task.title}' 已删除",
            user_id=task_user_id or "",
        )

    def create_history(
        self,
        db: Session,
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
        db.commit()  # Ensuring history is persisted
        db.refresh(history)
        return history

    def get_statistics(
        self, db: Session, *, user_id: str | None = None
    ) -> dict[str, Any]:
        """获取统计信息 (Proxy to CRUD or implement here?) - Logic is reading DB, so keep in CRUD or move here? moving to service is fine for consistency"""
        # Kept in CRUD for now as it's read-only aggregation.
        return task_crud.get_statistics(db, user_id=user_id)

    def cleanup_old_tasks(
        self, db: Session, *, days: int, dry_run: bool
    ) -> dict[str, Any]:
        """清理过期任务"""
        # Moving logic from API
        from datetime import timedelta

        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        old_tasks = (
            db.query(AsyncTask)
            .filter(
                and_(
                    AsyncTask.created_at < cutoff_date,
                    AsyncTask.status.in_(
                        [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
                    ),
                    AsyncTask.is_active,
                )
            )
            .all()
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
            setattr(task, "is_active", False)
            count += 1

        db.commit()
        cleanup_result: dict[str, Any] = {
            "message": f"成功清理 {count} 个过期任务",
            "cleanup_date": cutoff_date.isoformat(),
            "cleaned_count": count,
        }
        return cleanup_result

    # Excel Config Logic
    def create_excel_config(
        self, db: Session, *, obj_in: ExcelTaskConfigCreate, user_id: str | None = None
    ) -> ExcelTaskConfig:
        if obj_in.is_default:
            db.query(ExcelTaskConfig).filter(
                and_(
                    ExcelTaskConfig.config_type == obj_in.config_type,
                    ExcelTaskConfig.task_type == obj_in.task_type,
                    ExcelTaskConfig.is_default,
                )
            ).update({"is_default": False})

        # Delegating actual creation to CRUD but handling transaction
        config: ExcelTaskConfig = excel_task_config_crud.create(
            db, obj_in=obj_in, user_id=user_id
        )
        # Note: CRUD might flush, we commit here
        db.commit()
        db.refresh(config)
        return config


task_service = TaskService()
