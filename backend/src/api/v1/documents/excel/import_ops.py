"""Synchronous and asynchronous Excel import endpoints."""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Query, UploadFile
from fastapi.params import Depends as DependsParam
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.excel_config import STANDARD_SHEET_NAME
from src.constants.message_constants import ErrorIDs
from src.database import async_session_scope, get_async_db
from src.enums.task import TaskStatus, TaskType
from src.middleware.auth import AuthzContext, get_current_active_user, require_authz
from src.models.auth import User
from src.schemas.excel_advanced import ExcelImportRequest
from src.schemas.task import TaskCreate
from src.security.logging_security import security_auditor
from src.services.excel import ExcelImportService
from src.services.excel.excel_task_service import (
    ExcelTaskService,
    get_excel_task_service,
)
from src.services.file_upload import StagedFileService, UploadPurpose

logger = logging.getLogger(__name__)

router = APIRouter()
TEMP_UPLOAD_ROOT = Path("temp_uploads")
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


def _organization_id(current_user: User) -> str | None:
    organization_id = current_user.organization_id
    if organization_id is None or str(organization_id).strip() == "":
        return None
    return str(organization_id)


@router.post("/import", summary="Import Excel data synchronously")
async def import_excel(
    file: UploadFile = File(...),
    should_skip_errors: bool = Query(False, description="Whether to skip invalid rows"),
    sheet_name: str = Query(STANDARD_SHEET_NAME, description="Excel worksheet name"),
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
    """Import a validated XLSX file in the request lifecycle."""
    lifecycle = StagedFileService(TEMP_UPLOAD_ROOT)
    staged = await lifecycle.stage_upload(file, UploadPurpose.EXCEL_IMPORT)

    security_auditor.log_security_event(
        event_type="EXCEL_IMPORT_STARTED",
        message=f"Excel import started: {staged.original_filename} (sheet: {sheet_name})",
        details={
            "filename": staged.original_filename,
            "size": staged.size_bytes,
            "sheet_name": sheet_name,
            "skip_errors": should_skip_errors,
            "validation_hash": staged.sha256,
        },
    )

    try:
        import_service = ExcelImportService(db)
        result = await import_service.import_assets_from_excel(
            file_path=str(staged.path),
            sheet_name=sheet_name,
            should_validate_data=True,
            should_create_assets=True,
            should_update_existing=False,
            should_skip_errors=should_skip_errors,
            organization_id=_organization_id(current_user),
        )
        return {
            "message": "Import complete",
            "total": result.get("total", 0),
            "success": result.get("success", 0),
            "failed": result.get("failed", 0),
            "errors": result.get("errors", []),
        }
    finally:
        lifecycle.discard_staged(staged)


@router.post("/import/async", summary="Import Excel data asynchronously")
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
    """Create an asynchronous XLSX import task."""
    lifecycle = StagedFileService(TEMP_UPLOAD_ROOT)
    staged = await lifecycle.stage_upload(file, UploadPurpose.EXCEL_IMPORT)

    try:
        security_auditor.log_security_event(
            event_type="EXCEL_ASYNC_IMPORT_STARTED",
            message=f"Async Excel import started: {staged.original_filename}",
            details={
                "filename": staged.original_filename,
                "size": staged.size_bytes,
                "request_config": request.model_dump(),
                "validation_hash": staged.sha256,
            },
        )

        task_in = TaskCreate(
            task_type=TaskType.EXCEL_IMPORT,
            title=f"Excel import task - {staged.original_filename}",
            description=f"Asynchronous Excel import: {staged.original_filename}",
            parameters={
                "filename": staged.original_filename,
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
        background_tasks.add_task(
            _process_excel_import_async,
            task_id=str(task.id),
            file_path=str(staged.path),
            staging_root=TEMP_UPLOAD_ROOT,
            request=request,
            task_service=resolved_task_service,
            organization_id=_organization_id(current_user),
        )
    except BaseException:
        lifecycle.discard_staged(staged)
        raise

    return {
        "message": "Import task created",
        "task_id": task.id,
        "status": task.status,
        "estimated_time": "Use task_id to query import progress.",
    }


async def _process_excel_import_async(
    task_id: str,
    file_path: str,
    request: ExcelImportRequest,
    staging_root: Path = TEMP_UPLOAD_ROOT,
    db_session: AsyncSession | None = None,
    task_service: ExcelTaskService | None = None,
    organization_id: str | None = None,
) -> None:
    """Run an Excel import task and clean its validated staging directory."""
    if db_session is None:
        async with async_session_scope() as session:
            await _process_excel_import_async(
                task_id=task_id,
                file_path=file_path,
                staging_root=staging_root,
                request=request,
                db_session=session,
                task_service=task_service,
                organization_id=organization_id,
            )
        return

    resolved_task_service = task_service or get_excel_task_service()
    try:
        task = await resolved_task_service.get_task(db=db_session, task_id=task_id)
        if task is None:
            return
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
                "started_at": _utcnow_naive(),
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
        await resolved_task_service.update_task(
            db=db_session,
            task=task,
            task_data={
                "status": TaskStatus.COMPLETED,
                "progress": 100,
                "processed_items": 0,
                "failed_items": 0,
                "error_message": None,
                "completed_at": _utcnow_naive(),
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
    except Exception as exc:
        logger.critical(
            "asynchronous Excel import task failed: task_id=%s",
            task_id,
            exc_info=True,
            extra={
                "error_id": ErrorIDs.Task.IMPORT_FAILED,
                "task_id": task_id,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
            },
        )
        try:
            await resolved_task_service.mark_task_failed(
                db=db_session,
                task_id=task_id,
                error_message=str(exc),
            )
        except Exception as mark_failed_error:
            logger.error(
                "could not mark Excel import task failed: task_id=%s",
                task_id,
                exc_info=True,
                extra={
                    "error_id": ErrorIDs.Task.STATUS_UPDATE_FAILED,
                    "task_id": task_id,
                    "original_error": str(exc),
                    "commit_error": str(mark_failed_error),
                },
            )
    finally:
        try:
            StagedFileService(staging_root).discard_path(Path(file_path))
        except Exception as cleanup_error:
            logger.warning(
                "failed to clean staged Excel import file: %s",
                file_path,
                extra={
                    "error_id": ErrorIDs.Filesystem.PERMISSION_DENIED,
                    "file_path": file_path,
                    "cleanup_error": str(cleanup_error),
                },
            )
