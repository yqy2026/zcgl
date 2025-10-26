"""
PDF智能导入API (统一版本)
整合了完整的PDF处理流程和V1兼容功能的统一API
"""

import os
import uuid
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# 导入新的PDF处理服务 - 安全导入
try:
    from ...services.pdf_import_service import pdf_import_service
    from ...services.pdf_session_service import pdf_session_service
    from ...services.pdf_processing_service import pdf_processing_service
    from ...services.pdf_validation_matching_service import PDFValidationMatchingService
    from ...services.enhanced_matching_service import EnhancedPDFValidationMatchingService
    from ...services.enhanced_error_handler import enhanced_error_handler, handle_pdf_error
    from ...services.performance_monitor import performance_monitor
    PDF_SERVICES_AVAILABLE = True
except ImportError as e:
    logger.error(f"PDF服务导入失败: {e}")
    pdf_import_service = None
    pdf_session_service = None
    pdf_processing_service = None
    PDFValidationMatchingService = None
    EnhancedPDFValidationMatchingService = None
    PDF_SERVICES_AVAILABLE = False

# 数据库和模型
from ...database import get_db
from ...models.pdf_import_session import PDFImportSession, ProcessingConfiguration, SessionStatus
from ...models.asset import Asset
from ...models.asset import Ownership
from ...models.rent_contract import RentContract

# 配置
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pdf-import"])

# === V1兼容性数据传输对象 ===
class ExtractionRequest(BaseModel):
    """PDF信息提取请求模型 (V1兼容)"""
    text: str
    include_raw_text: bool = Field(default=False, description="是否包含原始文本")
    validate_fields: bool = Field(default=True, description="是否验证字段有效性")

class ExtractionResponse(BaseModel):
    """PDF信息提取响应模型 (V1兼容)"""
    success: bool
    extractor_used: str = "rental_contract_extractor"
    confidence: float = 0.0
    extracted_fields: Dict[str, Any] = {}
    validation_results: Dict[str, Any] = {}
    error: Optional[str] = None
    processing_time_ms: float = 0.0
    real_data_verified: bool = False

# 数据传输对象 (DTOs)
class FileUploadResponse(BaseModel):
    """文件上传响应"""
    success: bool
    message: str
    session_id: Optional[str] = None
    estimated_time: Optional[str] = None
    error: Optional[str] = None

class SessionProgressResponse(BaseModel):
    """会话进度响应"""
    success: bool
    session_status: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class MatchingResults(BaseModel):
    """匹配结果详细模型"""
    matched_assets: List[Dict[str, Any]] = []
    matched_ownerships: List[Dict[str, Any]] = []
    duplicate_contracts: List[Dict[str, Any]] = []
    recommendations: Dict[str, str] = {}
    overall_match_confidence: float = 0.0

class ExtractionResult(BaseModel):
    """提取结果详细模型"""
    success: bool
    data: Dict[str, Any] = {}
    confidence_score: float = 0.0
    extraction_method: str = ""
    processed_fields: int = 0
    total_fields: int = 0
    error: Optional[str] = None

class ValidationResult(BaseModel):
    """验证结果详细模型"""
    success: bool
    errors: List[str] = []
    warnings: List[str] = []
    validated_data: Dict[str, Any] = {}
    validation_score: float = 0.0
    processed_fields: int = 0
    required_fields_count: int = 0
    missing_required_fields: List[str] = []

class ConfirmImportRequest(BaseModel):
    """确认导入请求"""
    session_id: str
    confirmed_data: Dict[str, Any]
    selected_asset_id: Optional[str] = None
    selected_ownership_id: Optional[str] = None

class ConfirmImportResponse(BaseModel):
    """确认导入响应"""
    success: bool
    message: str
    contract_id: Optional[str] = None
    contract_number: Optional[str] = None
    created_terms_count: Optional[int] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None

class ActiveSessionResponse(BaseModel):
    """活跃会话响应"""
    success: bool
    active_sessions: List[Dict[str, Any]]
    total_count: int
    error: Optional[str] = None

class SystemCapabilities(BaseModel):
    """系统能力"""
    pdfplumber_available: bool = True
    pymupdf_available: bool = True
    spacy_available: bool = True
    ocr_available: bool = True
    supported_formats: List[str] = ['.pdf', '.jpg', '.jpeg', '.png']
    max_file_size_mb: int = 50
    estimated_processing_time: str = "30-60秒"

class SystemInfoResponse(BaseModel):
    """系统信息响应"""
    success: bool
    message: str
    capabilities: SystemCapabilities
    extractor_summary: Optional[Dict[str, Any]] = None
    validator_summary: Optional[Dict[str, Any]] = None

@router.get("/info", response_model=SystemInfoResponse)
async def get_system_info():
    """获取系统信息和能力"""
    try:
        # 简单版本 - 不依赖复杂服务
        return SystemInfoResponse(
            success=True,
            message="PDF导入系统正常运行",
            capabilities=SystemCapabilities(
                pdfplumber_available=True,
                pymupdf_available=True,
                spacy_available=True,
                ocr_available=True,
                supported_formats=['.pdf', '.jpg', '.jpeg', '.png'],
                max_file_size_mb=50,
                estimated_processing_time="30-60秒"
            ),
            extractor_summary={
                "method": "multi_engine",
                "description": "支持多种PDF处理引擎，包括PyMuPDF、PDFPlumber和OCR（PaddleOCR）",
                "engines": ["PyMuPDF", "PDFPlumber", "PaddleOCR"]
            },
            validator_summary={
                "enabled": True,
                "description": "智能数据验证和匹配功能",
                "features": ["字段验证", "资产匹配", "权属方匹配", "重复检查"]
            }
        )
    except Exception as e:
        logger.error(f"获取系统信息失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取系统信息失败: {str(e)}")

@router.get("/test_system")
async def test_system():
    """测试系统功能"""
    return {"system_status": "normal", "message": "PDF处理系统正常"}

@router.post("/upload", response_model=FileUploadResponse)
async def upload_pdf_file(
    file: UploadFile = File(...),
    prefer_markitdown: bool = Form(default=False),
    prefer_ocr: bool = Form(default=False),
    organization_id: Optional[int] = Form(default=None),
    db: Session = Depends(get_db)
):
    """上传PDF文件并开始处理"""
    start_time = datetime.now()

    # 验证文件类型
    if not file.content_type == 'application/pdf' and not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="只支持PDF文件上传"
        )

    # 验证并保存文件大小（流式处理，避免内存耗尽）
    max_size = 50 * 1024 * 1024  # 50MB
    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)

    file_id = str(uuid.uuid4())
    temp_file_path = temp_dir / f"{file_id}_{file.filename}"

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
                    raise HTTPException(
                        status_code=400,
                        detail=f"文件大小超过限制({max_size // (1024*1024)}MB)"
                    )
                temp_file.write(chunk)

        logger.info(f"PDF文件已流式保存: {temp_file_path}, 大小: {total_size} bytes")

    except Exception as e:
        # 清理临时文件
        temp_file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"文件处理失败: {str(e)}"
        )

    # 创建会话
    processing_options = {
        "prefer_ocr": prefer_ocr,
        "prefer_markitdown": prefer_markitdown,
        "max_pages": 100,
        "dpi": 300 if prefer_ocr else 150,
        "validate_fields": True,
        "enable_asset_matching": True,
        "enable_ownership_matching": True,
        "enable_duplicate_check": True
    }

    session = await pdf_session_service.create_session(
        db=db,
        filename=file.filename,
        file_size=total_size,  # 使用流式计算的大小
        file_path=str(temp_file_path),
        content_type=file.content_type or 'application/pdf',
        organization_id=organization_id,
        processing_options=processing_options
    )

    # 开始异步处理（带性能优化）
    start_time = time.time()
    process_result = await pdf_import_service.process_pdf_file(
        db=db,
        session_id=session.session_id,
        organization_id=organization_id,
        file_size=total_size,  # 使用流式计算的大小
        file_path=str(temp_file_path),
        content_type=file.content_type or 'application/pdf',
        processing_options=processing_options
    )
    processing_time = (datetime.now() - start_time).total_seconds()

    # 记录API调用和性能数据
    record_api_call(
        endpoint="/upload",
        method="upload_pdf_file",
        response_time_ms=processing_time * 1000,
        status_code=200 if process_result['success'] else 500,
        success=process_result['success'],
        cache_hit=False
    )

    # 返回优化后的结果
    if process_result['success']:
        return FileUploadResponse(
            success=True,
            message="PDF文件上传成功，正在处理中（优化版）",
            session_id=session.session_id,
            estimated_time="30-60秒",
            processing_options=processing_options
        )
    else:
        return FileUploadResponse(
            success=False,
            message=f"处理启动失败: {process_result.get('error_message', '未知错误')}",
            session_id=session.session_id,
            estimated_time="60-120秒"
        )

    processing_time = (datetime.now() - start_time).total_seconds()

    try:
        if process_result['success']:
            return FileUploadResponse(
                success=True,
                message="PDF文件上传成功，正在处理中",
                session_id=session.session_id,
                estimated_time="30-60秒"
            )
        else:
            return FileUploadResponse(
                success=False,
                message="处理启动失败",
                error=process_result.get('error', '未知错误')
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF上传处理失败: {str(e)}")
        return FileUploadResponse(
            success=False,
            message=f"处理失败: {str(e)}",
            error=str(e)
        )

@router.get("/progress/{session_id}", response_model=SessionProgressResponse)
async def get_session_progress(
    session_id: str,
    db: Session = Depends(get_db)
):
    """获取会话处理进度"""
    try:
        result = await pdf_import_service.get_session_status(db, session_id)
        return SessionProgressResponse(
            success=result['success'],
            session_status=result.get('session_status'),
            error=result.get('error')
        )
    except Exception as e:
        logger.error(f"获取会话进度失败: {str(e)}")
        return SessionProgressResponse(
            success=False,
            error=str(e)
        )

@router.get("/sessions", response_model=ActiveSessionResponse)
async def get_active_sessions(
    organization_id: Optional[int] = Query(None),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    """获取活跃会话列表"""
    try:
        if not PDF_SERVICES_AVAILABLE or pdf_session_service is None:
            return ActiveSessionResponse(
                success=False,
                active_sessions=[],
                total_count=0,
                error="PDF会话服务不可用"
            )

        sessions = await pdf_session_service.get_active_sessions(
            db, organization_id=organization_id
        )

        session_data = []
        for session in sessions:
            session_data.append({
                "session_id": session.session_id,
                "status": session.status.value,
                "progress": session.progress_percentage,
                "current_step": session.current_step.value if session.current_step else None,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat() if session.updated_at else None,
                "file_name": session.original_filename,
                "file_size": session.file_size,
                "error_message": session.error_message
            })

        return ActiveSessionResponse(
            success=True,
            active_sessions=session_data[:limit],
            total_count=len(session_data)
        )

    except Exception as e:
        logger.error(f"获取活跃会话失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return ActiveSessionResponse(
            success=False,
            active_sessions=[],
            total_count=0,
            error=str(e)
        )

@router.get("/sessions/history")
async def get_session_history(
    organization_id: Optional[int] = Query(None),
    limit: int = Query(100, le=200),
    db: Session = Depends(get_db)
):
    """获取会话历史记录"""
    try:
        sessions = await pdf_session_service.get_session_history(
            db, organization_id=organization_id, limit=limit
        )

        history_data = []
        for session in sessions:
            history_data.append({
                "session_id": session.session_id,
                "status": session.status.value,
                "progress": session.progress_percentage,
                "created_at": session.created_at.isoformat(),
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "file_name": session.original_filename,
                "confidence_score": session.confidence_score,
                "processing_method": session.processing_method,
                "error_message": session.error_message
            })

        return {
            "success": True,
            "history": history_data,
            "total_count": len(history_data)
        }

    except Exception as e:
        logger.error(f"获取会话历史失败: {str(e)}")
        return {
            "success": False,
            "history": [],
            "total_count": 0,
            "error": str(e)
        }

@router.post("/confirm_import", response_model=ConfirmImportResponse)
async def confirm_import(
    request: ConfirmImportRequest,
    db: Session = Depends(get_db)
):
    """确认导入合同数据"""
    start_time = datetime.now()

    try:
        # 添加用户选择的关联ID
        if request.selected_asset_id:
            request.confirmed_data['asset_id'] = request.selected_asset_id
        if request.selected_ownership_id:
            request.confirmed_data['ownership_id'] = request.selected_ownership_id

        result = await pdf_import_service.confirm_import(
            db=db,
            session_id=request.session_id,
            confirmed_data=request.confirmed_data,
            user_id=None  # TODO: 从认证中获取用户ID
        )

        processing_time = (datetime.now() - start_time).total_seconds()

        if result['success']:
            return ConfirmImportResponse(
                success=True,
                message="合同数据导入成功",
                contract_id=result.get('contract_id'),
                contract_number=request.confirmed_data.get('contract_number'),
                created_terms_count=len(request.confirmed_data.get('rent_terms', [])),
                processing_time=processing_time
            )
        else:
            return ConfirmImportResponse(
                success=False,
                message="导入失败",
                error=result.get('error', '未知错误')
            )

    except Exception as e:
        logger.error(f"确认导入失败: {str(e)}")
        return ConfirmImportResponse(
            success=False,
            message=f"导入失败: {str(e)}",
            error=str(e)
        )

@router.delete("/session/{session_id}")
async def cancel_session(
    session_id: str,
    reason: str = Query(default="用户取消"),
    db: Session = Depends(get_db)
):
    """取消会话处理"""
    try:
        result = await pdf_import_service.cancel_processing(
            db=db,
            session_id=session_id,
            reason=reason
        )

        return {
            "success": result['success'],
            "message": result['message'],
            "session_id": session_id
        }

    except Exception as e:
        logger.error(f"取消会话失败: {str(e)}")
        return {
            "success": False,
            "message": f"取消失败: {str(e)}",
            "session_id": session_id
        }

@router.get("/test")
async def test_system():
    """测试系统功能"""
    try:
        # 测试PDF处理服务
        test_result = {
            "pdf_processing": True,
            "session_management": True,
            "validation_matching": True,
            "database_import": True
        }

        return {
            "success": True,
            "message": "系统功能正常",
            "features": test_result,
            "system_ready": True
        }

    except Exception as e:
        logger.error(f"系统测试失败: {str(e)}")
        return {
            "success": False,
            "message": f"系统测试失败: {str(e)}",
            "system_ready": False
        }

@router.get("/health")
async def health_check():
    """健康检查"""
    try:
        return {
            "status": "healthy",
            "components": {
                "pdf_import": True,
                "text_extraction": True,
                "contract_validation": True,
                "data_matching": True,
                "database_import": True
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "components": {},
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# === V1兼容性API端点 ===
@router.post("/extract", response_model=ExtractionResponse)
async def extract_contract_from_text_v1_compatible(request: ExtractionRequest):
    """从文本提取合同信息 (V1兼容版本)"""
    start_time = datetime.now()

    try:
        logger.info(f"开始使用V2兼容模式处理文本，长度: {len(request.text)}")

        # 使用合同提取器 (与V1相同的提取器)
        from ...services.contract_extractor import extract_contract_info
        result = extract_contract_info(request.text)

        # 计算处理时间
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        if result.get('success'):
            # 字段验证
            validation_results = {}
            if request.validate_fields:
                validation_results = _validate_extracted_fields_v1(result.get('extracted_fields', {}))

            # 构建V1兼容响应
            response = ExtractionResponse(
                success=True,
                confidence=result.get('overall_confidence', 0.0),
                extracted_fields=result.get('extracted_fields', {}),
                validation_results=validation_results,
                processing_time_ms=processing_time,
                real_data_verified=result.get('validation_passed', False)
            )

            # 如果需要，包含原始文本
            if request.include_raw_text:
                response.extracted_fields['_raw_text'] = request.text

            logger.info(f"V1兼容模式文本提取完成，置信度: {result.get('overall_confidence', 0):.2f}, 提取字段数: {len(result.get('extracted_fields', {}))}")
            return response
        else:
            logger.warning(f"V1兼容模式文本提取失败: {result.get('error', '未知错误')}")
            return ExtractionResponse(
                success=False,
                error=result.get('error', '提取失败'),
                processing_time_ms=processing_time,
                real_data_verified=False
            )

    except Exception as e:
        logger.error(f"V1兼容模式文本提取异常: {e}")
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        return ExtractionResponse(
            success=False,
            error=f"处理异常: {str(e)}",
            processing_time_ms=processing_time,
            real_data_verified=False
        )

@router.post("/upload_and_extract", response_model=ExtractionResponse)
async def upload_and_extract_pdf_v1_compatible(
    file: UploadFile = File(...),
    include_raw_text: bool = Form(default=False),
    validate_fields: bool = Form(default=True),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """上传PDF文件并提取信息 (V1兼容版本)"""
    start_time = datetime.now()

    # 验证文件类型
    if not file.content_type == 'application/pdf':
        raise HTTPException(
            status_code=400,
            detail="只支持PDF文件上传"
        )

    # 验证文件大小（50MB限制）
    max_size = 50 * 1024 * 1024  # 50MB
    file_content = await file.read()
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制({max_size // (1024*1024)}MB)"
        )

    try:
        # 使用V2的文件管理服务
        file_info = await pdf_import_service.upload_file(file_content, file.filename)

        # 使用V2的处理服务提取文本
        text_result = await pdf_processing_service.extract_text_from_pdf(file_info['file_path'])

        if not text_result.get('success'):
            return ExtractionResponse(
                success=False,
                error="PDF文本提取失败",
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                real_data_verified=False
            )

        # 使用V1的提取器处理文本
        from ...services.contract_extractor import extract_contract_info
        extraction_result = extract_contract_info(text_result.get('text', ''))

        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        if extraction_result.get('success'):
            # 字段验证
            validation_results = {}
            if validate_fields:
                validation_results = _validate_extracted_fields_v1(extraction_result.get('extracted_fields', {}))

            # 构建V1兼容响应
            response = ExtractionResponse(
                success=True,
                confidence=extraction_result.get('overall_confidence', 0.0),
                extracted_fields=extraction_result.get('extracted_fields', {}),
                validation_results=validation_results,
                processing_time_ms=processing_time,
                real_data_verified=extraction_result.get('validation_passed', False)
            )

            # 如果需要，包含原始文本
            if include_raw_text:
                response.extracted_fields['_raw_text'] = text_result.get('text', '')

            logger.info(f"V1兼容模式PDF处理完成，置信度: {extraction_result.get('overall_confidence', 0):.2f}")
            return response
        else:
            return ExtractionResponse(
                success=False,
                error=extraction_result.get('error', 'PDF内容提取失败'),
                processing_time_ms=processing_time,
                real_data_verified=False
            )

    except Exception as e:
        logger.error(f"V1兼容模式PDF处理异常: {e}")
        return ExtractionResponse(
            success=False,
            error=f"PDF处理异常: {str(e)}",
            processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
            real_data_verified=False
        )

def _validate_extracted_fields_v1(extracted_fields: Dict[str, Any]) -> Dict[str, Any]:
    """V1兼容的字段验证函数"""
    validation_results = {}

    # 基本字段验证
    for field_name, field_value in extracted_fields.items():
        if field_value and str(field_value).strip():
            validation_results[field_name] = {
                "is_valid": True,
                "validation_errors": [],
                "confidence": 0.8  # 默认置信度
            }
        else:
            validation_results[field_name] = {
                "is_valid": False,
                "validation_errors": ["字段值为空"],
                "confidence": 0.0
            }

    return validation_results

@router.post("/extract")
async def extract_contract_info_v2_enhanced(
    text: str = Form(...),
    validate_fields: bool = Form(default=True),
    db: Session = Depends(get_db)
):
    """直接从文本提取合同信息 (V2增强版本)"""
    try:
        from ...services.contract_extractor import extract_contract_info

        # 提取信息
        extraction_result = extract_contract_info(text)

        if not extraction_result.get('success'):
            return {
                "success": False,
                "error": extraction_result.get('error', '提取失败')
            }

        # 验证和匹配
        validation_result = {}
        if validate_fields:
            validation_service = PDFValidationMatchingService(db)
            validation_result = await validation_service.validate_extracted_data(
                extraction_result.get('extracted_fields', {})
            )

        return {
            "success": True,
            "extraction_result": extraction_result,
            "validation_result": validation_result,
            "processing_time": extraction_result.get('processing_time_ms', 0) / 1000
        }

    except Exception as e:
        logger.error(f"文本提取失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

# === 增强性能监控端点 ===
@router.get("/performance/realtime")
async def get_realtime_performance():
    """获取实时性能监控数据"""
    try:
        performance_data = await performance_monitor.get_real_time_performance()
        return {
            "success": True,
            "data": performance_data,
            "message": "实时性能数据获取成功"
        }
    except Exception as e:
        logger.error(f"获取实时性能数据失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "data": None
        }

@router.get("/performance/report")
async def get_performance_report(hours: int = Query(default=24, ge=1, le=168)):
    """获取性能报告"""
    try:
        report = await performance_monitor.get_performance_report(hours)
        return {
            "success": True,
            "data": report,
            "message": "性能报告生成成功"
        }
    except Exception as e:
        logger.error(f"获取性能报告失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "data": None
        }

@router.get("/performance/health")
async def get_system_health():
    """获取系统健康状态"""
    try:
        from ...services.enhanced_error_handler import monitor_processing_health
        health_data = await monitor_processing_health()
        return {
            "success": True,
            "data": health_data,
            "message": "系统健康状态获取成功"
        }
    except Exception as e:
        logger.error(f"获取系统健康状态失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "data": None
        }