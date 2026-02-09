"""
Excel任务状态模块
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.params import Depends as DependsParam
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.middleware.auth import get_current_active_user
from src.models.auth import User
from src.schemas.excel_advanced import ExcelStatusResponse
from src.services.excel.excel_status_service import (
    ExcelStatusService,
    get_excel_status_service,
)

router = APIRouter()


def _resolve_service(service: ExcelStatusService | Any) -> ExcelStatusService | Any:
    if isinstance(service, DependsParam):
        return get_excel_status_service()
    return service


@router.get(
    "/status/{task_id}", response_model=ExcelStatusResponse, summary="获取任务状态"
)
async def get_excel_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: ExcelStatusService = Depends(get_excel_status_service),
) -> ExcelStatusResponse:
    """
    获取Excel导入导出任务状态

    - **task_id**: 任务ID
    """
    _ = current_user
    resolved_service = _resolve_service(service)
    return await resolved_service.get_task_status(
        db=db,
        task_id=task_id,
        current_user=current_user,
    )


@router.get("/history", summary="获取Excel操作历史")
async def get_excel_history(
    task_type: str | None = Query(None, description="任务类型筛选"),
    status: str | None = Query(None, description="状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页记录数"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: ExcelStatusService = Depends(get_excel_status_service),
) -> dict[str, Any]:
    """
    获取Excel操作历史记录

    - **task_type**: 按任务类型筛选
    - **status**: 按状态筛选
    - **page**: 页码
    - **page_size**: 每页记录数
    """
    _ = current_user
    resolved_service = _resolve_service(service)
    return await resolved_service.get_history(
        db=db,
        task_type=task_type,
        status=status,
        page=page,
        page_size=page_size,
        current_user=current_user,
    )
