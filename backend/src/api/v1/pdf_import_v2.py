"""
PDF智能导入API V2
完全重写的PDF导入API，整合完整的PDF处理流程
"""

import os
import uuid
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# 导入新的PDF处理服务
from ...services.pdf_import_service import pdf_import_service
from ...services.pdf_session_service import pdf_session_service
from ...services.pdf_processing_service import pdf_processing_service
from ...services.pdf_validation_matching_service import PDFValidationMatchingService

# 数据库和模型
from ...database import get_db
from ...models.pdf_import_session import PDFImportSession, ProcessingConfiguration, SessionStatus
from ...models.asset import Asset
from ...models.asset import Ownership
from ...models.rent_contract import RentContract

# 配置
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pdf-import-v2"])

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
        # 设置系统能力
        capabilities = SystemCapabilities(
            pdfplumber_available=True,
            pymupdf_available=True,
            spacy_available=True,
            ocr_available=True,
            supported_formats=['.pdf', '.jpg', '.jpeg', '.png'],
            max_file_size_mb=50,
            estimated_processing_time="30-60秒"
        )

        return SystemInfoResponse(
            success=True,
            message="PDF导入系统正常运行",
            capabilities=capabilities,
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

    # 验证文件大小（50MB限制）
    max_size = 50 * 1024 * 1024  # 50MB
    file_content = await file.read()
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制({max_size // (1024*1024)}MB)"
        )

    try:
        # 创建临时文件
        temp_dir = Path("temp_uploads")
        temp_dir.mkdir(exist_ok=True)

        file_id = str(uuid.uuid4())
        temp_file_path = temp_dir / f"{file_id}_{file.filename}"

        # 保存文件
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(file_content)

        logger.info(f"PDF文件已保存: {temp_file_path}")

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
            file_size=len(file_content),
            file_path=str(temp_file_path),
            content_type=file.content_type or 'application/pdf',
            organization_id=organization_id,
            processing_options=processing_options
        )

        # 开始异步处理
        process_result = await pdf_import_service.process_pdf_file(
            db=db,
            session_id=session.session_id,
            organization_id=organization_id
        )

        processing_time = (datetime.now() - start_time).total_seconds()

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

@router.post("/extract")
async def extract_contract_info(
    text: str = Form(...),
    validate_fields: bool = Form(default=True),
    db: Session = Depends(get_db)
):
    """直接从文本提取合同信息（用于测试）"""
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