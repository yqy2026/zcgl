"""
PDF质量评估API路由模块

从 pdf_import_unified.py 提取的质量评估相关端点

职责：
- PDF质量分析
- 质量评估结果查询
- 提取质量报告

端点：
- GET /quality/assessment/{session_id}: 获取会话质量评估
- POST /quality/analyze: 分析PDF文件质量
"""

import logging
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from ...database import get_db
from .dependencies import get_optional_services
from ...services.providers.ocr_provider import get_ocr_service
from ...utils.file_security import generate_safe_filename

logger = logging.getLogger(__name__)

router = APIRouter(tags=["PDF质量评估"])


@router.get("/quality/assessment/{session_id}")
async def get_quality_assessment(
    session_id: str,
    db: Session = Depends(get_db),
    optional: Any = Depends(get_optional_services),
) -> dict[str, Any]:
    """
    获取会话的质量评估结果

    参数：
    - session_id: 会话ID

    返回：
    - 包含质量评估结果和摘要的字典
    """
    try:
        session_service = optional.pdf_session_service
        if session_service is None:
            return {
                "success": False,
                "error": "PDF会话服务不可用",
                "quality_assessment": None,
            }

        # 获取会话信息
        session = await session_service.get_session(db, session_id)
        if not session:
            return {"success": False, "error": "会话不存在", "quality_assessment": None}

        # 获取处理结果中的质量评估
        processing_result = session.processing_result or {}
        quality_assessment = processing_result.get("quality_assessment")

        if not quality_assessment:
            return {
                "success": False,
                "error": "该会话尚未完成质量评估",
                "session_status": session.status.value,
                "quality_assessment": None,
            }

        return {
            "success": True,
            "session_id": session_id,
            "session_status": session.status.value,
            "quality_assessment": quality_assessment,
            "generated_at": quality_assessment.get("assessment_timestamp"),
            "summary": {
                "overall_score": quality_assessment.get("overall_quality_score", 0),
                "quality_level": quality_assessment.get("quality_level", {}).get(
                    "description", "Unknown"
                ),
                "total_fields_expected": quality_assessment.get(
                    "field_analysis", {}
                ).get("total_expected_fields", 0),
                "fields_extracted": quality_assessment.get("field_analysis", {}).get(
                    "extracted_fields_count", 0
                ),
                "extraction_rate": quality_assessment.get("field_analysis", {}).get(
                    "extraction_rate_percentage", 0
                ),
                "improvement_suggestions_count": len(
                    quality_assessment.get("improvement_suggestions", [])
                ),
            },
        }

    except Exception as e:
        logger.error(f"获取质量评估结果失败: {str(e)}")
        return {
            "success": False,
            "error": f"获取质量评估失败: {str(e)}",
            "quality_assessment": None,
        }


@router.post("/quality/analyze")
async def analyze_pdf_quality(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    ocr_service: Any = Depends(get_ocr_service),
    optional: Any = Depends(get_optional_services),
) -> dict[str, Any]:
    """
    分析PDF文件质量

    功能：
    - 上传PDF文件
    - 分析PDF质量和可提取性
    - 返回质量评估报告

    参数：
    - file: PDF文件

    返回：
    - 包含质量评估报告和处理摘要的字典
    """
    try:
        pdf_processing_service = optional.pdf_processing_service
        if pdf_processing_service is None:
            return {
                "success": False,
                "error": "PDF处理服务不可用",
                "quality_report": None,
            }

        # 验证文件类型
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            return {
                "success": False,
                "error": "只支持PDF文件质量分析",
                "quality_report": None,
            }

        # 保存临时文件
        temp_dir = Path(tempfile.gettempdir())
        file_id = str(uuid.uuid4())
        safe_filename = generate_safe_filename(file.filename, file_id)
        temp_file_path = temp_dir / safe_filename

        try:
            # 保存上传的文件
            with open(temp_file_path, "wb") as temp_file:
                content = await file.read()
                temp_file.write(content)

            logger.info(f"临时文件已保存: {temp_file_path}")

            # 处理PDF并获取质量评估
            result = await pdf_processing_service.extract_text_from_pdf(
                str(temp_file_path),
                prefer_ocr=False,  # 默认不使用OCR进行质量评估
                ocr_service=ocr_service,
            )

            if not result.get("success"):
                return {
                    "success": False,
                    "error": f"PDF处理失败: {result.get('error', '未知错误')}",
                    "quality_report": None,
                }

            # 获取质量评估结果
            quality_assessment = result.get("quality_assessment")
            if not quality_assessment:
                return {
                    "success": False,
                    "error": "质量评估失败",
                    "quality_report": None,
                    "processing_result": result,
                }

            return {
                "success": True,
                "message": "PDF质量分析完成",
                "quality_report": quality_assessment,
                "processing_summary": {
                    "processing_method": result.get("processing_method"),
                    "processing_time": result.get("processing_time_seconds"),
                    "file_size_bytes": result.get("file_size_bytes"),
                    "text_length": len(result.get("text", "")),
                    "page_count": result.get("page_count", 1),
                    # 并发与吞吐量指标（如OCR路径产生）
                    "concurrency_used": result.get("concurrency_used"),
                    "pages_per_second": result.get("pages_per_second"),
                },
            }

        finally:
            # 清理临时文件
            try:
                temp_file_path.unlink(missing_ok=True)
                logger.debug(f"临时文件已清理: {temp_file_path}")
            except Exception as cleanup_error:
                logger.warning(f"清理临时文件失败: {cleanup_error}")

    except Exception as e:
        logger.error(f"PDF质量分析失败: {str(e)}")
        return {
            "success": False,
            "error": f"质量分析异常: {str(e)}",
            "quality_report": None,
        }
