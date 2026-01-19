"""
Excel任务状态模块
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ....core.api_errors import not_found
from ....crud.task import task_crud
from ....database import get_db
from ....schemas.excel_advanced import ExcelStatusResponse

router = APIRouter()


@router.get(
    "/status/{task_id}", response_model=ExcelStatusResponse, summary="获取任务状态"
)
async def get_excel_task_status(
    task_id: str, db: Session = Depends(get_db)
) -> ExcelStatusResponse:
    """
    获取Excel导入导出任务状态

    - **task_id**: 任务ID
    """
    task = task_crud.get(db=db, id=task_id)
    if not task:
        raise not_found("任务不存在", resource_type="task", resource_id=task_id)

    # Extract values from Column objects - use getattr to get actual values
    task_id_val = str(getattr(task, "id", ""))
    status_val = str(getattr(task, "status", ""))
    progress_val = int(getattr(task, "progress", 0)) or 0
    total_items_val = getattr(task, "total_items", None)
    total_items_final = int(total_items_val) if total_items_val is not None else None
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
        error_message=str(error_message_val) if error_message_val is not None else None,
        created_at=created_at_val,
        started_at=started_at_val,
        completed_at=completed_at_val,
    )


@router.get("/history", summary="获取Excel操作历史")
async def get_excel_history(
    task_type: str | None = Query(None, description="任务类型筛选"),
    status: str | None = Query(None, description="状态筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    skip: int = Query(0, ge=0, description="跳过数量"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    获取Excel操作历史记录

    - **task_type**: 按任务类型筛选
    - **status**: 按状态筛选
    - **limit**: 返回数量
    - **skip**: 跳过数量
    """
    tasks = task_crud.get_multi(
        db=db,
        skip=skip,
        limit=limit,
        task_type=task_type,
        status=status,
        order_by="created_at",
        order_dir="desc",
    )

    # 转换为响应格式
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
        "total": len(history_items),
        "skip": skip,
        "limit": limit,
    }
