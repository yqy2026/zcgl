"""Excel preview endpoints."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.middleware.auth import AuthzContext, get_current_active_user, require_authz
from src.models.auth import User
from src.schemas.excel_advanced import (
    ExcelFieldMapping,
    ExcelPreviewRequest,
    ExcelPreviewResponse,
)
from src.security.logging_security import security_auditor
from src.services.excel import ExcelPreviewService
from src.services.file_upload import StagedFileService, UploadPurpose

router = APIRouter()
TEMP_UPLOAD_ROOT = Path("temp_uploads")
_ASSET_CREATE_UNSCOPED_PARTY_ID = "__unscoped__:asset:create"
_ASSET_CREATE_RESOURCE_CONTEXT: dict[str, str] = {
    "party_id": _ASSET_CREATE_UNSCOPED_PARTY_ID,
    "owner_party_id": _ASSET_CREATE_UNSCOPED_PARTY_ID,
    "manager_party_id": _ASSET_CREATE_UNSCOPED_PARTY_ID,
}


@router.post(
    "/preview/advanced", response_model=ExcelPreviewResponse, summary="Advanced Excel preview"
)
async def preview_excel_advanced(
    file: UploadFile = File(...),
    request: ExcelPreviewRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="create",
            resource_type="asset",
            resource_context=_ASSET_CREATE_RESOURCE_CONTEXT,
        )
    ),
) -> ExcelPreviewResponse:
    """Preview a validated XLSX file with detected field mappings."""
    lifecycle = StagedFileService(TEMP_UPLOAD_ROOT)
    staged = await lifecycle.stage_upload(file, UploadPurpose.EXCEL_PREVIEW)
    validation_result = {
        "hash": staged.sha256,
        "validation_time": datetime.now(UTC).isoformat(),
    }

    security_auditor.log_security_event(
        event_type="FILE_UPLOAD_VALIDATED",
        message=f"Excel file validated successfully: {staged.original_filename}",
        details={
            "filename": staged.original_filename,
            "size": staged.size_bytes,
            "hash": validation_result["hash"],
            "validation_time": validation_result["validation_time"],
        },
    )

    try:
        content = staged.path.read_bytes()
        total, columns, preview_data, detected_mapping = await run_in_threadpool(
            ExcelPreviewService.build_preview_advanced, content, request.max_rows
        )
        detected_field_mapping = (
            [ExcelFieldMapping.model_validate(item) for item in detected_mapping]
            if detected_mapping is not None
            else None
        )

        return ExcelPreviewResponse(
            file_name=staged.original_filename,
            sheet_names=[f"Sheet{i + 1}" for i in range(1)],
            total_rows=total,
            columns=columns,
            preview_data=preview_data,
            detected_field_mapping=detected_field_mapping,
        )
    finally:
        lifecycle.discard_staged(staged)


@router.post("/preview", summary="Preview Excel file content")
async def preview_excel(
    file: UploadFile = File(...),
    max_rows: int = Query(10, ge=1, le=100, description="Preview row count"),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="create",
            resource_type="asset",
            resource_context=_ASSET_CREATE_RESOURCE_CONTEXT,
        )
    ),
) -> dict[str, Any]:
    """Preview a validated XLSX file before import."""
    lifecycle = StagedFileService(TEMP_UPLOAD_ROOT)
    staged = await lifecycle.stage_upload(file, UploadPurpose.EXCEL_PREVIEW)

    try:
        content = staged.path.read_bytes()
        total, columns, preview_data = await run_in_threadpool(
            ExcelPreviewService.build_preview, content, max_rows
        )
        return {
            "message": "Preview successful",
            "filename": staged.original_filename,
            "total": total,
            "preview_rows": len(preview_data),
            "columns": columns,
            "data": preview_data,
        }
    finally:
        lifecycle.discard_staged(staged)
