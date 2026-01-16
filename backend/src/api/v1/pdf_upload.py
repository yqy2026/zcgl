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
"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from ...database import get_db
from ...schemas.pdf_import import ExtractionResponse, FileUploadResponse
from ...services.document.pdf_import_service import PDFImportService
from .dependencies import get_optional_services, get_pdf_import_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["PDF上传"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_pdf_file(
    file: UploadFile = File(...),
    prefer_markitdown: bool = Form(default=False),
    prefer_ocr: bool = Form(default=False),
    organization_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    pdf_service: PDFImportService = Depends(get_pdf_import_service),
    optional: Any = Depends(get_optional_services),
) -> FileUploadResponse:
    """
    上传PDF文件并开始处理

    功能：
    - 文件类型验证（仅支持PDF）
    - 文件大小验证（最大50MB）
    - 流式文件保存（避免内存耗尽）
    - 安全文件名处理（防止路径遍历攻击）
    - 创建处理会话
    - 异步处理文件

    处理选项：
    - prefer_markitdown: 优先使用Markdown处理
    - prefer_ocr: 优先使用OCR处理
    - organization_id: 组织ID（可选）

    返回：
    - FileUploadResponse: 包含会话ID和预计处理时间
    """
    retry_count = 0
    enhanced_error_handler = optional.enhanced_error_handler

    # 验证文件类型
    if file.content_type != "application/pdf" and not (
        file.filename and file.filename.lower().endswith(".pdf")
    ):
        if enhanced_error_handler:
            error_result = enhanced_error_handler.handle_error(
                ValueError("不支持的文件类型"),
                {"filename": file.filename, "content_type": file.content_type},
                "file_format_unsupported",
                retry_count,
            )
            return FileUploadResponse(
                success=False,
                message=error_result["error"],
                error=error_result["suggested_action"],
            )
        else:
            raise HTTPException(status_code=400, detail="只支持PDF文件上传")

    # 验证并保存文件大小（流式处理，避免内存耗尽）
    max_size = (
        enhanced_error_handler.max_file_size_mb * 1024 * 1024
        if enhanced_error_handler
        else 50 * 1024 * 1024
    )
    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)

    # 安全文件名处理 - 防止路径遍历攻击
    from ..utils.file_security import generate_safe_filename

    file_id = str(uuid.uuid4())
    safe_filename = generate_safe_filename(file.filename, file_id)
    temp_file_path = temp_dir / safe_filename

    # 使用流式保存，同时验证文件大小
    total_size = 0
    chunk_size = 64 * 1024  # 64KB chunks

    try:
        with open(temp_file_path, "wb") as temp_file:
            while chunk := await file.read(chunk_size):
                total_size += len(chunk)
                if total_size > max_size:
                    # 清理部分写入的文件
                    temp_file.close()
                    temp_file_path.unlink(missing_ok=True)

                    if enhanced_error_handler:
                        error_result = enhanced_error_handler.handle_error(
                            ValueError(f"文件大小 {total_size} 超过限制 {max_size}"),
                            {"filename": file.filename, "file_size": total_size},
                            "file_too_large",
                            retry_count,
                        )
                        return FileUploadResponse(
                            success=False,
                            message=error_result["error"],
                            error=error_result["suggested_action"],
                        )
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"文件大小超过限制({max_size // (1024 * 1024)}MB)",
                        )
                temp_file.write(chunk)

        logger.info(f"PDF文件已流式保存: {temp_file_path}, 大小: {total_size} bytes")

    except Exception as e:
        # 清理临时文件
        temp_file_path.unlink(missing_ok=True)

        if enhanced_error_handler:
            error_result = enhanced_error_handler.handle_error(
                e,
                {"filename": file.filename, "step": "file_upload"},
                "unknown_error",
                retry_count,
            )
            return FileUploadResponse(
                success=False,
                message=error_result["error"],
                error=error_result["suggested_action"],
            )
        else:
            raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")

    # 创建会话
    processing_options = {
        "prefer_ocr": prefer_ocr,
        "prefer_markitdown": prefer_markitdown,
        "max_pages": 100,
        "dpi": 300 if prefer_ocr else 150,
        "validate_fields": True,
        "enable_asset_matching": True,
        "enable_ownership_matching": True,
        "enable_duplicate_check": True,
    }

    # 获取session service（可选）
    session_service = optional.pdf_session_service
    if session_service is None:
        # 如果不可用，返回错误
        return FileUploadResponse(
            success=False,
            message="PDF会话服务不可用",
            error="PDF_SESSION_SERVICE_UNAVAILABLE",
        )

    session = await session_service.create_session(
        db=db,
        filename=file.filename,
        file_size=total_size,  # 使用流式计算的大小
        file_path=str(temp_file_path),
        content_type=file.content_type or "application/pdf",
        organization_id=organization_id,
        processing_options=processing_options,
    )

    # 开始异步处理（带性能优化和错误处理）
    try:
        process_result = await pdf_service.process_pdf_file(
            db=db,
            session_id=session.session_id,
            organization_id=organization_id,
            file_size=total_size,  # 使用流式计算的大小
            file_path=str(temp_file_path),
            content_type=file.content_type or "application/pdf",
            processing_options=processing_options,
        )

    except Exception as e:
        logger.error(f"PDF处理失败: {str(e)}")

        if enhanced_error_handler:
            error_result = enhanced_error_handler.handle_error(
                e,
                {
                    "session_id": session.session_id,
                    "file_path": str(temp_file_path),
                    "processing_options": processing_options,
                    "step": "pdf_processing",
                },
                "processing_timeout"
                if "timeout" in str(e).lower()
                else "unknown_error",
                retry_count,
            )

            return FileUploadResponse(
                success=False,
                message=error_result["error"],
                error=error_result["suggested_action"],
                session_id=session.session_id,
            )
        else:
            raise HTTPException(status_code=500, detail=f"PDF处理失败: {str(e)}")

    # 返回优化后的结果
    if process_result["success"]:
        return FileUploadResponse(
            success=True,
            message="PDF文件上传成功，正在处理中（优化版）",
            session_id=session.session_id,
            estimated_time="30-60秒",
        )
    else:
        return FileUploadResponse(
            success=False,
            message=f"处理启动失败: {process_result.get('error_message', '未知错误')}",
            session_id=session.session_id,
            estimated_time="60-120秒",
        )


@router.post("/upload_and_extract", response_model=ExtractionResponse)
async def upload_and_extract_pdf_v1_compatible(
    file: UploadFile = File(...),
    include_raw_text: bool = Form(default=False),
    validate_fields: bool = Form(default=True),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    optional: Any = Depends(get_optional_services),
) -> ExtractionResponse:
    """
    上传PDF文件并提取信息（V1兼容版本）

    这是一个V1兼容端点，用于向后兼容旧的客户端。

    功能：
    - 同步上传并提取PDF信息
    - 返回提取的字段和验证结果
    - 支持V1响应格式

    参数：
    - file: PDF文件
    - include_raw_text: 是否包含原始文本
    - validate_fields: 是否验证字段
    """
    start_time = datetime.now()
    pdf_processing_service = optional.pdf_processing_service

    # 验证文件类型
    if not file.content_type == "application/pdf":
        raise HTTPException(status_code=400, detail="只支持PDF文件上传")

    # 验证文件大小（50MB限制）
    max_size = 50 * 1024 * 1024  # 50MB
    file_content = await file.read()
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=400, detail=f"文件大小超过限制({max_size // (1024 * 1024)}MB)"
        )

    if pdf_processing_service is None:
        return ExtractionResponse(
            success=False,
            error="PDF处理服务不可用",
            processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
            real_data_verified=False,
        )

    try:
        # 使用V2的文件管理服务
        from ...services.document.pdf_import_service import PDFImportService

        pdf_import_service_instance = PDFImportService()
        filename = file.filename or "uploaded_file.pdf"
        file_info = await pdf_import_service_instance.upload_file(
            file_content, filename
        )

        # 使用V2的处理服务提取文本
        text_result = await pdf_processing_service.extract_text_from_pdf(
            file_info["file_path"],
        )

        if not text_result.get("success"):
            return ExtractionResponse(
                success=False,
                error="PDF文本提取失败",
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                real_data_verified=False,
            )

        # 使用V1的提取器处理文本
        from ...services.contract_extractor import extract_contract_info

        extraction_result = extract_contract_info(text_result.get("text", ""))

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        if extraction_result.get("success"):
            # 字段验证
            validation_results = {}
            if validate_fields:
                validation_results = _validate_extracted_fields_v1(
                    extraction_result.get("extracted_fields", {})
                )

            # 构建V1兼容响应
            response = ExtractionResponse(
                success=True,
                confidence=extraction_result.get("overall_confidence", 0.0),
                extracted_fields=extraction_result.get("extracted_fields", {}),
                validation_results=validation_results,
                processing_time_ms=processing_time,
                real_data_verified=extraction_result.get("validation_passed", False),
            )

            # 如果需要，包含原始文本
            if include_raw_text:
                response.extracted_fields["_raw_text"] = text_result.get("text", "")

            logger.info(
                f"V1兼容模式PDF处理完成，置信度: {extraction_result.get('overall_confidence', 0):.2f}"
            )
            return response
        else:
            return ExtractionResponse(
                success=False,
                error=extraction_result.get("error", "PDF内容提取失败"),
                processing_time_ms=processing_time,
                real_data_verified=False,
            )

    except Exception as e:
        logger.error(f"V1兼容模式PDF处理异常: {e}")
        return ExtractionResponse(
            success=False,
            error=f"PDF处理异常: {str(e)}",
            processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
            real_data_verified=False,
        )


def _validate_extracted_fields_v1(extracted_fields: dict[str, Any]) -> dict[str, Any]:
    """
    V1兼容的字段验证函数

    对提取的字段进行基本验证：
    - 检查字段是否为空
    - 分配默认置信度

    参数：
    - extracted_fields: 提取的字段字典

    返回：
    - 验证结果字典
    """
    validation_results = {}

    # 基本字段验证
    for field_name, field_value in extracted_fields.items():
        if field_value and str(field_value).strip():
            validation_results[field_name] = {
                "is_valid": True,
                "validation_errors": [],
                "confidence": 0.8,  # 默认置信度
            }
        else:
            validation_results[field_name] = {
                "is_valid": False,
                "validation_errors": ["字段值为空"],
                "confidence": 0.0,
            }

    return validation_results
