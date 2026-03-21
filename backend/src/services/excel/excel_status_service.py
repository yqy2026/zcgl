"""Excel status service layer."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import not_found
from ...crud.task import task_crud
from ...models.auth import User
from ...schemas.excel_advanced import ExcelStatusResponse
from ..task.access import ensure_task_access, resolve_task_user_filter


class ExcelStatusService:
    """Service for excel status/history routes."""

    async def get_task_status(
        self,
        db: AsyncSession,
        *,
        task_id: str,
        current_user: User,
    ) -> ExcelStatusResponse:
        task = await task_crud.get(db=db, id=task_id)
        if not task:
            raise not_found("任务不存在", resource_type="task", resource_id=task_id)
        await ensure_task_access(task, current_user, db)

        task_id_val = str(getattr(task, "id", ""))
        status_val = str(getattr(task, "status", ""))
        progress_val = int(getattr(task, "progress", 0)) or 0
        total_items_val = getattr(task, "total_items", None)
        total_items_final = (
            int(total_items_val) if total_items_val is not None else None
        )
        processed_items_val = int(getattr(task, "processed_items", 0)) or 0
        error_message_val = getattr(task, "error_message", None)
        created_at_val = getattr(task, "created_at")
        started_at_val = getattr(task, "started_at")
        completed_at_val = getattr(task, "completed_at")

        return ExcelStatusResponse(
            task_id=task_id_val,
            status=status_val,
            progress=progress_val,
            total_items=total_items_final,
            processed_items=processed_items_val,
            error_message=str(error_message_val)
            if error_message_val is not None
            else None,
            created_at=created_at_val,
            started_at=started_at_val,
            completed_at=completed_at_val,
        )

    async def get_history(
        self,
        db: AsyncSession,
        *,
        task_type: str | None,
        status: str | None,
        page: int,
        page_size: int,
        current_user: User,
    ) -> dict[str, Any]:
        skip = (page - 1) * page_size
        effective_user_id = await resolve_task_user_filter(None, current_user, db)

        tasks = await task_crud.get_multi_async(
            db=db,
            skip=skip,
            limit=page_size,
            task_type=task_type,
            status=status,
            user_id=effective_user_id,
            order_by="created_at",
            order_dir="desc",
        )
        total = await task_crud.count_async(
            db=db,
            task_type=task_type,
            status=status,
            user_id=effective_user_id,
        )

        history_items: list[dict[str, Any]] = []
        for task in tasks:
            result_data_raw = task.result_data if task.result_data else {}
            result_data: dict[str, Any] = (
                result_data_raw if isinstance(result_data_raw, dict) else {}
            )
            history_items.append(
                {
                    "task_id": task.id,
                    "task_type": task.task_type,
                    "title": task.title,
                    "status": task.status,
                    "progress": task.progress or 0,
                    "created_at": task.created_at,
                    "completed_at": task.completed_at,
                    "result_summary": {
                        "total": result_data.get("total", 0),
                        "success": result_data.get("success", 0),
                        "failed": result_data.get("failed", 0),
                        "record_count": result_data.get("record_count", 0),
                    },
                }
            )

        return {
            "items": history_items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }


excel_status_service = ExcelStatusService()


def get_excel_status_service() -> ExcelStatusService:
    return excel_status_service
