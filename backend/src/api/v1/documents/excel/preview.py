"""
Excel 预览模块
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from src.constants.file_size_constants import DEFAULT_MAX_FILE_SIZE
from src.core.exception_handler import BusinessValidationError
from src.database import get_db
from src.middleware.auth import get_current_active_user
from src.models.auth import User
from src.schemas.excel_advanced import (
    ExcelFieldMapping,
    ExcelPreviewRequest,
    ExcelPreviewResponse,
)
from src.security.logging_security import security_auditor
from src.security.security import security_middleware
from src.services.excel import ExcelPreviewService

router = APIRouter()


@router.post(
    "/preview/advanced", response_model=ExcelPreviewResponse, summary="高级Excel预览"
)
async def preview_excel_advanced(
    file: UploadFile = File(...),
    request: ExcelPreviewRequest = Body(...),
    db: Session = Depends(get_db),
) -> ExcelPreviewResponse:
    """
    高级Excel文件预览，支持字段映射检测
    """
    await security_middleware.validate_file_upload(
        file,
        allowed_types=[
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        ],
        max_size=DEFAULT_MAX_FILE_SIZE,
    )

    validation_result = {
        "hash": f"computed_hash_{file.filename}",
        "validation_time": datetime.now(UTC).isoformat(),
    }

    security_auditor.log_security_event(
        event_type="FILE_UPLOAD_VALIDATED",
        message=f"Excel file validated successfully: {file.filename}",
        details={
            "filename": file.filename,
            "size": file.size,
            "hash": validation_result.get("hash"),
            "validation_time": validation_result.get("validation_time"),
        },
    )

    content = await file.read()

    total, columns, preview_data, detected_mapping = await run_in_threadpool(
        ExcelPreviewService.build_preview_advanced, content, request.max_rows
    )

    detected_field_mapping = (
        [ExcelFieldMapping.model_validate(item) for item in detected_mapping]
        if detected_mapping is not None
        else None
    )

    return ExcelPreviewResponse(
        file_name=file.filename or "unknown.xlsx",
        sheet_names=[f"Sheet{i + 1}" for i in range(1)],
        total_rows=total,
        columns=columns,
        preview_data=preview_data,
        detected_field_mapping=detected_field_mapping,
    )


@router.post("/preview", summary="预览Excel文件内容")
async def preview_excel(
    file: UploadFile = File(...),
    max_rows: int = Query(10, ge=1, le=100, description="预览行数"),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    预览Excel文件内容，用于导入前确认
    """
    await security_middleware.validate_file_upload(
        file,
        allowed_types=[
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        ],
        max_size=DEFAULT_MAX_FILE_SIZE,
    )

    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise BusinessValidationError("文件格式不支持，请上传Excel文件(.xlsx/.xls)")

    content = await file.read()

    total, columns, preview_data = await run_in_threadpool(
        ExcelPreviewService.build_preview, content, max_rows
    )

    return {
        "message": "预览成功",
        "filename": file.filename,
        "total": total,
        "preview_rows": len(preview_data),
        "columns": columns,
        "data": preview_data,
    }
