"""
Excel导入操作模块 - 同步与异步导入
"""

import logging
import os
import tempfile
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Query, UploadFile
from fastapi.params import Depends as DependsParam
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.excel_config import STANDARD_SHEET_NAME
from src.constants.file_size_constants import DEFAULT_MAX_EXCEL_FILE_SIZE
from src.constants.message_constants import ErrorIDs
from src.core.exception_handler import BusinessValidationError
from src.database import async_session_scope, get_async_db
from src.enums.task import TaskStatus, TaskType
from src.middleware.auth import AuthzContext, get_current_active_user, require_authz
from src.models.auth import User
from src.schemas.excel_advanced import ExcelImportRequest
from src.schemas.task import TaskCreate
from src.security.logging_security import security_auditor
from src.security.security import security_middleware
from src.services.excel import ExcelImportService
from src.services.excel.excel_task_service import (
    ExcelTaskService,
    get_excel_task_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()
_ASSET_CREATE_UNSCOPED_PARTY_ID = "__unscoped__:asset:create"
_ASSET_CREATE_RESOURCE_CONTEXT: dict[str, str] = {
    "party_id": _ASSET_CREATE_UNSCOPED_PARTY_ID,
    "owner_party_id": _ASSET_CREATE_UNSCOPED_PARTY_ID,
    "manager_party_id": _ASSET_CREATE_UNSCOPED_PARTY_ID,
}


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _resolve_task_service(
    task_service: ExcelTaskService | Any,
) -> ExcelTaskService | Any:
    if isinstance(task_service, DependsParam):
        return get_excel_task_service()
    return task_service


@router.post("/import", summary="导入Excel数据（同步）")
async def import_excel(
    file: UploadFile = File(...),
    should_skip_errors: bool = Query(False, description="是否跳过错误行"),
    sheet_name: str = Query(STANDARD_SHEET_NAME, description="Excel工作表名称"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="create",
            resource_type="asset",
            resource_context=_ASSET_CREATE_RESOURCE_CONTEXT,
        )
    ),
) -> dict[str, Any]:
    """
    从Excel文件导入资产数据（同步版本）
    """
    await security_middleware.validate_file_upload(
        file,
        allowed_types=[
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        ],
        max_size=DEFAULT_MAX_EXCEL_FILE_SIZE,
    )

    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise BusinessValidationError("文件格式不支持，请上传Excel文件(.xlsx/.xls)")

    security_auditor.log_security_event(
        event_type="EXCEL_IMPORT_STARTED",
        message=f"Excel import started: {file.filename} (sheet: {sheet_name})",
        details={
            "filename": file.filename,
            "size": file.size,
            "sheet_name": sheet_name,
            "skip_errors": should_skip_errors,
        },
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name

    try:
        default_org_id = getattr(current_user, "default_organization_id", None)
        organization_id = (
            str(default_org_id)
            if default_org_id is not None and str(default_org_id).strip() != ""
            else None
        )
        import_service = ExcelImportService(db)
        result = await import_service.import_assets_from_excel(
            file_path=tmp_file_path,
            sheet_name=sheet_name,
            should_validate_data=True,
            should_create_assets=True,
            should_update_existing=False,
            should_skip_errors=should_skip_errors,
            organization_id=organization_id,
        )

        return {
            "message": "导入完成",
            "total": result.get("total", 0),
            "success": result.get("success", 0),
            "failed": result.get("failed", 0),
            "errors": result.get("errors", []),
        }
    finally:
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)


@router.post("/import/async", summary="异步导入Excel数据")
async def import_excel_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    request: ExcelImportRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="create",
            resource_type="asset",
            resource_context=_ASSET_CREATE_RESOURCE_CONTEXT,
        )
    ),
    task_service: ExcelTaskService = Depends(get_excel_task_service),
) -> dict[str, Any]:
    """
    异步导入Excel文件，返回任务ID用于跟踪进度
    """
    validation_result = await security_middleware.validate_file_upload(
        file,
        allowed_types=[
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        ],
        max_size=DEFAULT_MAX_EXCEL_FILE_SIZE,
    )

    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise BusinessValidationError("文件格式不支持，请上传Excel文件(.xlsx/.xls)")

    security_auditor.log_security_event(
        event_type="EXCEL_ASYNC_IMPORT_STARTED",
        message=f"Async Excel import started: {file.filename}",
        details={
            "filename": file.filename,
            "size": file.size,
            "request_config": request.model_dump(),
            "validation_hash": validation_result.get("hash"),
        },
    )

    task_in = TaskCreate(
        task_type=TaskType.EXCEL_IMPORT,
        title=f"Excel导入任务 - {file.filename}",
        description=f"异步导入Excel文件: {file.filename}",
        parameters={
            "filename": file.filename,
            "sheet_name": STANDARD_SHEET_NAME,
            "validate_data": request.should_validate_data,
            "create_assets": request.should_create_assets,
            "update_existing": request.should_update_existing,
            "skip_errors": request.should_skip_errors,
            "batch_size": request.batch_size,
        },
        config={"config_id": request.config_id} if request.config_id else {},
    )

    resolved_task_service = _resolve_task_service(task_service)
    task = await resolved_task_service.create_task(
        db=db,
        task_in=task_in,
        user_id=current_user.id,
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name

    default_org_id = getattr(current_user, "default_organization_id", None)
    organization_id = (
        str(default_org_id)
        if default_org_id is not None and str(default_org_id).strip() != ""
        else None
    )

    background_tasks.add_task(
        _process_excel_import_async,
        task_id=str(task.id),
        file_path=tmp_file_path,
        request=request,
        task_service=resolved_task_service,
        organization_id=organization_id,
    )

    return {
        "message": "导入任务已创建",
        "task_id": task.id,
        "status": task.status,
        "estimated_time": "预计需要2-5分钟，请使用task_id查询进度",
    }


async def _process_excel_import_async(
    task_id: str,
    file_path: str,
    request: ExcelImportRequest,
    db_session: AsyncSession | None = None,
    task_service: ExcelTaskService | None = None,
    organization_id: str | None = None,
) -> None:
    """
    后台处理Excel导入任务
    """
    if db_session is None:
        async with async_session_scope() as session:
            await _process_excel_import_async(
                task_id=task_id,
                file_path=file_path,
                request=request,
                db_session=session,
                task_service=task_service,
                organization_id=organization_id,
            )
        return
    resolved_task_service = task_service or get_excel_task_service()
    try:
        task = await resolved_task_service.get_task(db=db_session, task_id=task_id)
        if not task:
            return
        started_at = _utcnow_naive()
        await resolved_task_service.update_task(
            db=db_session,
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

        import_service = ExcelImportService(db_session)
        result = await import_service.import_assets_from_excel(
            file_path=file_path,
            sheet_name=STANDARD_SHEET_NAME,
            should_validate_data=request.should_validate_data,
            should_create_assets=request.should_create_assets,
            should_update_existing=request.should_update_existing,
            should_skip_errors=request.should_skip_errors,
            batch_size=request.batch_size,
            organization_id=organization_id,
        )

        completed_at = _utcnow_naive()
        await resolved_task_service.update_task(
            db=db_session,
            task=task,
            task_data={
                "status": TaskStatus.COMPLETED,
                "progress": 100,
                "processed_items": 0,
                "failed_items": 0,
                "error_message": None,
                "completed_at": completed_at,
                "result_data": {
                    "total": result.get("total", 0),
                    "success": result.get("success", 0),
                    "failed": result.get("failed", 0),
                    "created_assets": result.get("created_assets", 0),
                    "updated_assets": result.get("updated_assets", 0),
                    "errors": result.get("errors", []),
                    "warnings": result.get("warnings", []),
                },
            },
        )
    except Exception as e:
        logger.critical(
            f"异步Excel导入任务失败: task_id={task_id}",
            exc_info=True,
            extra={
                "error_id": ErrorIDs.Task.IMPORT_FAILED,
                "task_id": task_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )

        try:
            if db_session is not None:
                await resolved_task_service.mark_task_failed(
                    db=db_session,
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
    finally:
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as cleanup_error:
            logger.warning(
                f"清理临时文件失败: {file_path}",
                extra={
                    "error_id": ErrorIDs.Filesystem.PERMISSION_DENIED,
                    "file_path": file_path,
                    "cleanup_error": str(cleanup_error),
                },
            )
