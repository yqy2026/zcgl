"""
Excel导出操作模块 - 同步与异步导出
"""

import logging
import os
import tempfile
from collections.abc import AsyncGenerator, Generator
from datetime import datetime
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    Query,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ....config.excel_config import STANDARD_SHEET_NAME
from ....core.api_errors import bad_request, not_found
from ....crud.task import task_crud
from ....database import get_db
from ....enums.task import TaskStatus, TaskType
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....schemas.excel_advanced import ExcelExportRequest
from ....schemas.task import TaskCreate, TaskUpdate
from ....services.excel import ExcelExportService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/export", summary="导出Excel文件")
async def export_excel(
    search: str | None = Query(None, description="搜索关键词"),
    ownership_status: str | None = Query(None, description="确权状态筛选"),
    property_nature: str | None = Query(None, description="物业性质筛选"),
    usage_status: str | None = Query(None, description="使用状态筛选"),
    db: Session = Depends(get_db),
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
    buffer = service.export_assets_to_excel(
        filters=filters,
        search=search,
        limit=1000,
    )

    # 返回文件流（避免重复读取buffer）
    async def file_generator() -> AsyncGenerator[bytes, None]:
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
    db: Session = Depends(get_db),
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
    buffer = service.export_assets_to_excel(
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
    async def file_generator() -> AsyncGenerator[bytes, None]:
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
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
            "include_headers": request.include_headers,
            "date_format": request.date_format,
        },
        config={"config_id": request.config_id} if request.config_id else None,
    )

    task = task_crud.create(db=db, obj_in=task_in)

    # 添加后台任务
    background_tasks.add_task(
        _process_excel_export_async,
        task_id=str(task.id),
        request=request,
        db_session=db,
    )

    return {
        "message": "导出任务已创建",
        "task_id": task.id,
        "status": task.status,
        "estimated_time": "预计需要1-3分钟，请使用task_id查询进度",
    }


async def _process_excel_export_async(
    task_id: str, request: ExcelExportRequest, db_session: Session
) -> None:
    """
    后台处理Excel导出任务
    """
    try:
        # 更新任务状态为运行中
        db_obj = task_crud.get(db=db_session, id=task_id)
        if db_obj is not None:
            task_crud.update(
                db=db_session,
                db_obj=db_obj,
                obj_in=TaskUpdate(
                    status=TaskStatus.RUNNING,
                    progress=0,
                    processed_items=0,
                    failed_items=0,
                    error_message=None,
                    result_data=None,
                ),
            )
        db_session.commit()

        # 使用ExcelExportService进行导出
        service = ExcelExportService(db_session)

        # 构建筛选条件
        filters: dict[str, Any] = request.filters or {}

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"assets_export_{timestamp}.{request.export_format}"

        # 保存到临时文件
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, filename)

        # 执行导出到文件
        result_info: dict[str, Any] = service.export_assets_to_file(
            file_path=file_path,
            filters=filters,
            fields=request.fields,
            sheet_name=request.sheet_name or STANDARD_SHEET_NAME,
            date_format=request.date_format,
            limit=5000,
        )

        # 更新任务完成状态
        db_obj = task_crud.get(db=db_session, id=task_id)
        if db_obj is not None:
            task_crud.update(
                db=db_session,
                db_obj=db_obj,
                obj_in=TaskUpdate(
                    status=TaskStatus.COMPLETED,
                    progress=100,
                    processed_items=0,
                    failed_items=0,
                    error_message=None,
                    result_data={
                        **result_info,
                        "download_url": f"/api/v1/excel/download/{task_id}",
                    },
                ),
            )
        db_session.commit()

    except Exception as e:
        # 更新任务失败状态
        db_obj = task_crud.get(db=db_session, id=task_id)
        if db_obj is not None:
            task_crud.update(
                db=db_session,
                db_obj=db_obj,
                obj_in=TaskUpdate(
                    status=TaskStatus.FAILED,
                    error_message=str(e),
                    progress=0,
                    processed_items=0,
                    failed_items=0,
                    result_data=None,
                ),
            )
        db_session.commit()


@router.get("/download/{task_id}", summary="下载导出文件")
async def download_export_file(
    task_id: str, db: Session = Depends(get_db)
) -> StreamingResponse:
    """
    下载异步导出的文件
    """
    # 获取任务信息
    task = task_crud.get(db=db, id=task_id)
    if not task:
        raise not_found("任务不存在", resource_type="task", resource_id=task_id)

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
