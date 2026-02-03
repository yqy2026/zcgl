"""
PDF文件上传API路由模块

从 pdf_import_unified.py 提取的上传相关端点

职责：
- 文件上传与流式处理
- 文件验证（类型、大小）
- 安全文件名处理
- 创建处理会话

端点：
- POST /upload: 上传PDF并开始处理
- POST /upload_and_extract: V1兼容的上传和提取

Best practice (breaking change):
- 仅保留 /upload 作为上传入口，不再提供 /process 等别名。
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ....constants.file_size_constants import DEFAULT_MAX_FILE_SIZE
from ....core.exception_handler import BaseBusinessError, bad_request, internal_error
from ....database import get_async_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....schemas.pdf_import import ExtractionResponse, FileUploadResponse
from ....security.file_validation import validate_upload_file
from ....services.document.pdf_import_service import PDFImportService
from ....utils.file_security import generate_safe_filename
from ..dependencies import get_optional_services, get_pdf_import_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["PDF上传"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_pdf_file(
    file: UploadFile = File(...),
    prefer_markitdown: bool = Form(default=False),
    force_method: str | None = Form(default=None),
    organization_id: int | None = Form(default=None),
    db: AsyncSession = Depends(get_async_db),
    pdf_service: PDFImportService = Depends(get_pdf_import_service),
    optional: Any = Depends(get_optional_services),
    current_user: User = Depends(get_current_active_user),
) -> FileUploadResponse:
    """上传PDF文件并开始处理"""

    # 通过 Magic Number 校验文件真实类型（防止恶意文件伪装）
    await validate_upload_file(file, "application/pdf")

    # 验证文件类型（保留后缀名检查作为备用）
    if file.content_type != "application/pdf" and not (
        file.filename and file.filename.lower().endswith(".pdf")
    ):
        raise bad_request("只支持PDF文件上传")

    # 验证并保存文件大小（流式处理，避免内存耗尽）
    max_size = DEFAULT_MAX_FILE_SIZE
    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)

    file_id = str(uuid.uuid4())
    safe_filename = generate_safe_filename(
        file.filename or "upload.pdf", prefix=file_id
    )
    temp_file_path = temp_dir / safe_filename

    total_size = 0
    chunk_size = 64 * 1024

    try:
        with open(temp_file_path, "wb") as temp_file:
            while chunk := await file.read(chunk_size):
                total_size += len(chunk)
                if total_size > max_size:
                    temp_file_path.unlink(missing_ok=True)
                    raise bad_request(
                        f"文件大小超过限制({max_size // (1024 * 1024)}MB)"
                    )
                temp_file.write(chunk)

        logger.info("PDF文件已保存: %s, size=%s", temp_file_path, total_size)

    except Exception as e:
        temp_file_path.unlink(missing_ok=True)
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"文件处理失败: {str(e)}")

    sanitized_force_method = force_method.strip() if force_method else None
    allowed_methods = {"text", "vision", "smart"}
    if (
        sanitized_force_method is not None
        and sanitized_force_method not in allowed_methods
    ):
        raise bad_request("force_method 仅支持: text, vision, smart")

    session_id = f"session-{uuid.uuid4().hex[:12]}"
    processing_options = {
        "prefer_markitdown": prefer_markitdown,
        "force_method": sanitized_force_method,
        "max_pages": 100,
        "dpi": 300 if sanitized_force_method == "vision" else 150,
        "validate_fields": True,
        "enable_asset_matching": True,
        "enable_ownership_matching": True,
        "enable_duplicate_check": True,
    }
    session = await pdf_service.create_import_session(
        db,
        session_id=session_id,
        original_filename=file.filename or "upload.pdf",
        file_size=total_size,
        file_path=str(temp_file_path),
        content_type=file.content_type or "application/pdf",
        organization_id=organization_id,
        processing_options=processing_options,
    )
    resolved_session_id = session_id
    session_session_id = getattr(session, "session_id", None)
    if isinstance(session_session_id, str) and session_session_id.strip() != "":
        resolved_session_id = session_session_id
    resolved_processing_options = processing_options
    session_processing_options = getattr(session, "processing_options", None)
    if isinstance(session_processing_options, dict) and session_processing_options:
        resolved_processing_options = session_processing_options

    # 开始处理
    try:
        await pdf_service.process_pdf_file(
            db=db,
            session_id=resolved_session_id,
            organization_id=organization_id,
            file_size=total_size,
            file_path=str(temp_file_path),
            content_type=file.content_type or "application/pdf",
            processing_options=resolved_processing_options,
        )
    except Exception as e:
        logger.error("PDF处理失败: %s", e)
        raise internal_error(f"PDF处理失败: {str(e)}")

    return FileUploadResponse(
        success=True,
        message="PDF文件上传成功，正在处理中",
        session_id=resolved_session_id,
        estimated_time="30-60秒",
    )


@router.post("/upload-and-extract", response_model=ExtractionResponse)
async def upload_and_extract_pdf_v1_compatible(
    file: UploadFile = File(...),
    should_include_raw_text: bool = Form(default=False),
    should_validate_fields: bool = Form(default=True),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    optional: Any = Depends(get_optional_services),
    current_user: User = Depends(get_current_active_user),
) -> ExtractionResponse:
    """上传PDF文件并提取信息（V1兼容端点；如不需要可后续移除）"""

    start_time = datetime.now()
    pdf_processing_service = optional.pdf_processing_service

    if file.content_type != "application/pdf":
        raise bad_request("只支持PDF文件上传")

    if pdf_processing_service is None:
        return ExtractionResponse(
            success=False,
            error="PDF处理服务不可用",
            processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
            real_data_verified=False,
        )

    max_size = DEFAULT_MAX_FILE_SIZE
    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    file_id = str(uuid.uuid4())
    safe_filename = generate_safe_filename(
        file.filename or "uploaded_file.pdf", prefix=file_id
    )
    temp_file_path = temp_dir / safe_filename

    total_size = 0
    chunk_size = 64 * 1024

    try:
        with open(temp_file_path, "wb") as temp_file:
            while chunk := await file.read(chunk_size):
                total_size += len(chunk)
                if total_size > max_size:
                    temp_file_path.unlink(missing_ok=True)
                    raise bad_request(
                        f"文件大小超过限制({max_size // (1024 * 1024)}MB)"
                    )
                temp_file.write(chunk)

        text_result = await pdf_processing_service.extract_text_from_pdf(
            str(temp_file_path)
        )

        if not text_result.get("success"):
            return ExtractionResponse(
                success=False,
                error="PDF文本提取失败",
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                real_data_verified=False,
            )

        # Best practice: import from backend service module, not "src.*"
        from ....services.document.contract_extractor import ContractExtractor

        extraction_result = ContractExtractor().extract_contract_info(
            text_result.get("text", "")
        )

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        if extraction_result.get("success"):
            validation_results = {}
            if should_validate_fields:
                validation_results = _validate_extracted_fields_v1(
                    extraction_result.get("extracted_fields", {})
                )

            response = ExtractionResponse(
                success=True,
                confidence=extraction_result.get("overall_confidence", 0.0),
                extracted_fields=extraction_result.get("extracted_fields", {}),
                validation_results=validation_results,
                processing_time_ms=processing_time,
                real_data_verified=extraction_result.get("validation_passed", False),
            )

            if should_include_raw_text:
                response.extracted_fields["_raw_text"] = text_result.get("text", "")

            return response

        return ExtractionResponse(
            success=False,
            error=extraction_result.get("error", "PDF内容提取失败"),
            processing_time_ms=processing_time,
            real_data_verified=False,
        )

    except BaseBusinessError:
        raise
    except Exception as e:
        logger.error("V1兼容模式PDF处理异常: %s", e)
        return ExtractionResponse(
            success=False,
            error=f"PDF处理异常: {str(e)}",
            processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
            real_data_verified=False,
        )
    finally:
        temp_file_path.unlink(missing_ok=True)


def _validate_extracted_fields_v1(extracted_fields: dict[str, Any]) -> dict[str, Any]:
    """V1兼容的字段验证函数"""

    validation_results: dict[str, Any] = {}

    for field_name, field_value in extracted_fields.items():
        if field_value and str(field_value).strip():
            validation_results[field_name] = {
                "is_valid": True,
                "validation_errors": [],
                "confidence": 0.8,
            }
        else:
            validation_results[field_name] = {
                "is_valid": False,
                "validation_errors": ["字段值为空"],
                "confidence": 0.0,
            }

    return validation_results
