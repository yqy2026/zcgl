"""Excel 任务 CRUD 协调服务层。"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.task import task_crud
from ...enums.task import TaskStatus
from ...models.task import AsyncTask
from ...schemas.task import TaskCreate


class ExcelTaskService:
    """封装 Excel 场景下任务的创建/查询/更新。"""

    @staticmethod
    def _utcnow_naive() -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    async def create_task(
        self,
        db: AsyncSession,
        *,
        task_in: TaskCreate,
        user_id: str | None,
    ) -> AsyncTask:
        return await task_crud.create_async(db=db, obj_in=task_in, user_id=user_id)

    async def get_task(
        self,
        db: AsyncSession,
        *,
        task_id: str,
    ) -> AsyncTask | None:
        return await task_crud.get(db=db, id=task_id)

    async def update_task(
        self,
        db: AsyncSession,
        *,
        task: AsyncTask,
        task_data: dict[str, Any],
    ) -> AsyncTask:
        return await task_crud.update(
            db=db,
            db_obj=task,
            obj_in=task_data,
        )

    async def mark_task_failed(
        self,
        db: AsyncSession,
        *,
        task_id: str,
        error_message: str,
    ) -> AsyncTask | None:
        await db.rollback()

        task = await self.get_task(db=db, task_id=task_id)
        if task is None:
            return None

        return await self.update_task(
            db=db,
            task=task,
            task_data={
                "status": TaskStatus.FAILED,
                "error_message": error_message,
                "progress": 0,
                "processed_items": 0,
                "failed_items": 0,
                "completed_at": self._utcnow_naive(),
                "result_data": None,
            },
        )


excel_task_service = ExcelTaskService()


def get_excel_task_service() -> ExcelTaskService:
    return excel_task_service
