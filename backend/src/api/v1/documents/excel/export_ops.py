"""
Excel导出操作模块 - 同步与异步导出
"""

import logging
import os
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    Query,
)
from fastapi.params import Depends as DependsParam
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.excel_config import STANDARD_SHEET_NAME
from src.constants.message_constants import ErrorIDs
from src.core.exception_handler import bad_request, not_found
from src.database import async_session_scope, get_async_db
from src.enums.task import TaskStatus, TaskType
from src.middleware.auth import get_current_active_user
from src.models.auth import User
from src.schemas.excel_advanced import ExcelExportRequest
from src.schemas.task import TaskCreate
from src.services.excel import ExcelExportService
from src.services.excel.excel_task_service import (
    ExcelTaskService,
    get_excel_task_service,
)
from src.services.task.access import ensure_task_access

logger = logging.getLogger(__name__)

router = APIRouter()


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _resolve_task_service(
    task_service: ExcelTaskService | Any,
) -> ExcelTaskService | Any:
    if isinstance(task_service, DependsParam):
        return get_excel_task_service()
    return task_service


@router.get("/export", summary="导出Excel文件")
async def export_excel(
    search: str | None = Query(None, description="搜索关键词"),
    ownership_status: str | None = Query(None, description="确权状态筛选"),
    property_nature: str | None = Query(None, description="物业性质筛选"),
    usage_status: str | None = Query(None, description="使用状态筛选"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """
    导出资产数据为Excel文件

    支持按条件筛选导出
    """
    # 构建筛选条件
    filters: dict[str, Any] = {}
    if ownership_status:
        filters["ownership_status"] = ownership_status
    if property_nature:
        filters["property_nature"] = property_nature
    if usage_status:
        filters["usage_status"] = usage_status

    # 使用ExcelExportService进行导出
    service = ExcelExportService(db)
    buffer = await service.export_assets_to_excel_async(
        filters=filters,
        search=search,
        limit=1000,
    )

    # 返回文件流（避免重复读取buffer）
    def file_generator() -> Generator[bytes, None, None]:
        data = buffer.getvalue()
        yield data
        buffer.close()

    return StreamingResponse(
        file_generator(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=assets_export.xlsx"},
    )


@router.post("/export", summary="导出选中资产Excel文件")
async def export_selected_assets(
    asset_ids: list[str] | None = Body(None, description="资产ID列表"),
    export_format: str = Query("excel", description="导出格式"),
    search: str | None = Query(None, description="搜索关键词"),
    ownership_status: str | None = Query(None, description="确权状态筛选"),
    property_nature: str | None = Query(None, description="物业性质筛选"),
    usage_status: str | None = Query(None, description="使用状态筛选"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """
    导出选中资产数据为Excel文件

    支持按条件筛选导出和指定资产ID导出
    """
    # 构建筛选条件
    filters: dict[str, Any] = {}
    if ownership_status:
        filters["ownership_status"] = ownership_status
    if property_nature:
        filters["property_nature"] = property_nature
    if usage_status:
        filters["usage_status"] = usage_status

    # 使用ExcelExportService进行导出
    service = ExcelExportService(db)
    buffer = await service.export_assets_to_excel_async(
        filters=filters,
        search=search,
        asset_ids=asset_ids,
        limit=1000,
    )

    # 根据导出类型确定文件名
    filename = (
        "selected_assets_export.xlsx" if asset_ids else "filtered_assets_export.xlsx"
    )

    # 返回文件流（避免重复读取buffer）
    def file_generator() -> Generator[bytes, None, None]:
        data = buffer.getvalue()
        yield data
        buffer.close()

    return StreamingResponse(
        file_generator(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/export/async", summary="异步导出Excel文件")
async def export_excel_async(
    background_tasks: BackgroundTasks,
    request: ExcelExportRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    task_service: ExcelTaskService = Depends(get_excel_task_service),
) -> dict[str, Any]:
    """
    异步导出Excel文件，返回任务ID用于跟踪进度

    - **request**: 导出配置参数
    """
    # 创建导出任务
    task_in = TaskCreate(
        task_type=TaskType.EXCEL_EXPORT,
        title="Excel导出任务",
        description="异步导出资产数据为Excel文件",
        parameters={
            "filters": request.filters or {},
            "fields": request.fields or [],
            "export_format": request.export_format,
            "sheet_name": request.sheet_name or STANDARD_SHEET_NAME,
            "include_headers": request.should_include_headers,
            "date_format": request.date_format,
        },
        config={"config_id": request.config_id} if request.config_id else {},
    )

    resolved_task_service = _resolve_task_service(task_service)
    task = await resolved_task_service.create_task(
        db=db,
        task_in=task_in,
        user_id=current_user.id,
    )

    # 添加后台任务
    background_tasks.add_task(
        _process_excel_export_async,
        task_id=str(task.id),
        request=request,
        task_service=resolved_task_service,
    )

    return {
        "message": "导出任务已创建",
        "task_id": task.id,
        "status": task.status,
        "estimated_time": "预计需要1-3分钟，请使用task_id查询进度",
    }


async def _process_excel_export_async(
    task_id: str,
    request: ExcelExportRequest,
    db_session: AsyncSession | None = None,
    task_service: ExcelTaskService | None = None,
) -> None:
    """
    后台处理Excel导出任务
    """
    resolved_task_service = task_service or get_excel_task_service()

    async def _run_export(session: AsyncSession) -> None:
        try:
            task = await resolved_task_service.get_task(db=session, task_id=task_id)
            if not task:
                return
            started_at = _utcnow_naive()
            await resolved_task_service.update_task(
                db=session,
                task=task,
                task_data={
                    "status": TaskStatus.RUNNING,
                    "progress": 0,
                    "processed_items": 0,
                    "failed_items": 0,
                    "error_message": None,
                    "result_data": None,
                    "started_at": started_at,
                },
            )

            service = ExcelExportService(session)
            filters: dict[str, Any] = request.filters or {}
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"assets_export_{timestamp}.{request.export_format}"

            temp_dir = Path("temp_uploads") / "excel_exports"
            temp_dir.mkdir(parents=True, exist_ok=True)
            file_path = str(temp_dir / filename)

            result_info: dict[str, Any] = await service.export_assets_to_file_async(
                file_path=file_path,
                filters=filters,
                fields=request.fields,
                sheet_name=request.sheet_name or STANDARD_SHEET_NAME,
                date_format=request.date_format,
                limit=5000,
            )

            completed_at = _utcnow_naive()
            await resolved_task_service.update_task(
                db=session,
                task=task,
                task_data={
                    "status": TaskStatus.COMPLETED,
                    "progress": 100,
                    "processed_items": 0,
                    "failed_items": 0,
                    "error_message": None,
                    "completed_at": completed_at,
                    "result_data": {
                        **result_info,
                        "download_url": f"/api/v1/excel/download/{task_id}",
                    },
                },
            )
        except Exception as e:
            logger.critical(
                f"异步Excel导出任务失败: task_id={task_id}",
                exc_info=True,
                extra={
                    "error_id": ErrorIDs.Task.EXPORT_FAILED,
                    "task_id": task_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )

            try:
                await resolved_task_service.mark_task_failed(
                    db=session,
                    task_id=task_id,
                    error_message=str(e),
                )
            except Exception as mark_failed_error:
                logger.error(
                    f"无法更新任务失败状态: task_id={task_id}",
                    exc_info=True,
                    extra={
                        "error_id": ErrorIDs.Task.STATUS_UPDATE_FAILED,
                        "task_id": task_id,
                        "original_error": str(e),
                        "commit_error": str(mark_failed_error),
                    },
                )

    if db_session is None:
        async with async_session_scope() as session:
            await _run_export(session)
    else:
        await _run_export(db_session)


@router.get("/download/{task_id}", summary="下载导出文件")
async def download_export_file(
    task_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    task_service: ExcelTaskService = Depends(get_excel_task_service),
) -> StreamingResponse:
    """
    下载异步导出的文件
    """
    # 获取任务信息
    resolved_task_service = _resolve_task_service(task_service)
    task = await resolved_task_service.get_task(db=db, task_id=task_id)
    if not task:
        raise not_found("任务不存在", resource_type="task", resource_id=task_id)
    await ensure_task_access(task, current_user, db)

    if task.status != TaskStatus.COMPLETED:
        raise bad_request("任务尚未完成")

    # 获取文件信息
    result_data_raw = task.result_data if task.result_data else {}
    result_data: dict[str, Any] = (
        result_data_raw if isinstance(result_data_raw, dict) else {}
    )
    file_path = result_data.get("file_path")
    file_name = result_data.get("file_name", f"export_{task_id}.xlsx")

    if not file_path or not os.path.exists(file_path):
        raise not_found(
            "导出文件不存在", resource_type="file", resource_id=str(file_path)
        )

    # 返回文件流
    def file_iter() -> Generator[bytes, None, None]:
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    return StreamingResponse(
        file_iter(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={file_name}"},
    )
