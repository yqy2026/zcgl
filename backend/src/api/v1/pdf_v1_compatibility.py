"""
PDF V1兼容性API路由模块

从 pdf_import_unified.py 提取的V1版本兼容端点

职责：
- V1 API向后兼容
- 文本提取接口
- 文件上传和提取接口
- 字段验证

端点：
- POST /extract: 从文本提取合同信息 (V1兼容，JSON)
- POST /upload_and_extract: 上传PDF并提取 (V1兼容)
- POST /extract: 从文本提取合同信息 (V2增强，Form)

注意：
存在两个 /extract 端点，通过请求内容类型区分：
- JSON body → V1 compatible version
- Form data → V2 enhanced version
"""

import logging
from datetime import datetime
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
from ...schemas.pdf_import import ExtractionRequest, ExtractionResponse
from ...services.providers.ocr_provider import get_ocr_service
from .dependencies import get_optional_services, get_pdf_import_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["PDF兼容性"])


@router.post("/extract", response_model=ExtractionResponse)
async def extract_contract_from_text_v1_compatible(
    request: ExtractionRequest,
) -> ExtractionResponse:
    """
    从文本提取合同信息 (V1兼容版本)

    使用JSON请求体，提供V1版本的响应格式。

    参数：
    - request: ExtractionRequest，包含文本和处理选项

    返回：
    - ExtractionResponse: V1格式的提取结果
    """
    start_time = datetime.now()

    try:
        logger.info(f"开始使用V2兼容模式处理文本，长度: {len(request.text)}")

        # 使用合同提取器 (与V1相同的提取器)
        from ...services.contract_extractor import extract_contract_info

        result = extract_contract_info(request.text)

        # 计算处理时间
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        if result.get("success"):
            # 字段验证
            validation_results = {}
            if request.validate_fields:
                validation_results = _validate_extracted_fields_v1(
                    result.get("extracted_fields", {})
                )

            # 构建V1兼容响应
            response = ExtractionResponse(
                success=True,
                confidence=result.get("overall_confidence", 0.0),
                extracted_fields=result.get("extracted_fields", {}),
                validation_results=validation_results,
                processing_time_ms=processing_time,
                real_data_verified=result.get("validation_passed", False),
            )

            # 如果需要，包含原始文本
            if request.include_raw_text:
                response.extracted_fields["_raw_text"] = request.text

            logger.info(
                f"V1兼容模式文本提取完成，置信度: {result.get('overall_confidence', 0):.2f}, 提取字段数: {len(result.get('extracted_fields', {}))}"
            )
            return response
        else:
            logger.warning(f"V1兼容模式文本提取失败: {result.get('error', '未知错误')}")
            return ExtractionResponse(
                success=False,
                error=result.get("error", "提取失败"),
                processing_time_ms=processing_time,
                real_data_verified=False,
            )

    except Exception as e:
        logger.error(f"V1兼容模式文本提取异常: {e}")
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return ExtractionResponse(
            success=False,
            error=f"处理异常: {str(e)}",
            processing_time_ms=processing_time,
            real_data_verified=False,
        )


@router.post("/upload_and_extract", response_model=ExtractionResponse)
async def upload_and_extract_pdf_v1_compatible(
    file: UploadFile = File(...),
    include_raw_text: bool = Form(default=False),
    validate_fields: bool = Form(default=True),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    ocr_service: Any = Depends(get_ocr_service),
    optional: Any = Depends(get_optional_services),
) -> ExtractionResponse:
    """
    上传PDF文件并提取信息 (V1兼容版本)

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
    pdf_import_service = get_pdf_import_service()
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
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        file_info = await pdf_import_service.upload_file(file_content, file.filename)

        # 使用V2的处理服务提取文本
        text_result = await pdf_processing_service.extract_text_from_pdf(
            file_info["file_path"],
            ocr_service=ocr_service,
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


@router.post("/extract")
async def extract_contract_info_v2_enhanced(
    text: str = Form(...),
    validate_fields: bool = Form(default=True),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    直接从文本提取合同信息 (V2增强版本)

    使用Form数据，提供V2版本的增强功能。

    注意：与上面的 /extract 端点通过请求内容类型区分：
    - JSON body (ExtractionRequest) → V1 compatible version
    - Form data (text field) → V2 enhanced version (本端点)

    参数：
    - text: 合同文本内容
    - validate_fields: 是否验证和匹配字段

    返回：
    - 包含提取结果和验证结果的字典
    """
    try:
        from ...services.contract_extractor import extract_contract_info
        from ...services.document.pdf_validation_matching_service import (
            PDFValidationMatchingService,
        )

        # 提取信息
        extraction_result = extract_contract_info(text)

        if not extraction_result.get("success"):
            return {
                "success": False,
                "error": extraction_result.get("error", "提取失败"),
            }

        # 验证和匹配
        validation_result = {}
        if validate_fields:
            validation_service = PDFValidationMatchingService(db)
            validation_result = await validation_service.validate_extracted_data(
                extraction_result.get("extracted_fields", {})
            )

        return {
            "success": True,
            "extraction_result": extraction_result,
            "validation_result": validation_result,
            "processing_time": extraction_result.get("processing_time_ms", 0) / 1000,
        }

    except Exception as e:
        logger.error(f"文本提取失败: {str(e)}")
        return {"success": False, "error": str(e)}
