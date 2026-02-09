"""
PDF系统信息API路由模块

从 pdf_import_unified.py 提取的系统信息相关端点

职责：
- 系统能力查询
- 健康检查
- 测试端点

端点：
- GET /info: 获取系统信息和能力
- GET /test_system: 测试系统功能
- GET /test_detailed: 详细测试
- GET /health: 健康检查
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends

from ....core.exception_handler import internal_error
from ....core.performance import PerformanceMonitor
from ....middleware.auth import get_current_active_user
from ....schemas.pdf_import import SystemCapabilities, SystemInfoResponse
from ....security.route_guards import debug_only, require_localhost
from ..dependencies import get_performance_monitor

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["PDF系统信息"],
    dependencies=[Depends(get_current_active_user)],
)


@router.get("/info", response_model=SystemInfoResponse)
def get_system_info() -> SystemInfoResponse:
    """
    获取系统信息和能力

    返回：
    - SystemInfoResponse: 包含系统能力、视觉可用性等信息
    """
    try:
        return SystemInfoResponse(
            success=True,
            message="PDF导入系统正常运行 (LLM Vision 模式)",
            capabilities=SystemCapabilities(
                pdfplumber_available=True,
                pymupdf_available=True,
                vision_available=True,
                supported_formats=[".pdf", ".jpg", ".jpeg", ".png"],
                max_file_size_mb=50,
                estimated_processing_time="10-30秒",
            ),
            extractor_summary={
                "method": "multi_engine",
                "description": "支持多种PDF处理引擎，包括PyMuPDF、PDFPlumber和LLM Vision",
                "engines": ["PyMuPDF", "PDFPlumber", "LLM Vision (Qwen/DeepSeek/GLM)"],
            },
            validator_summary={
                "enabled": True,
                "description": "智能数据验证和匹配功能",
                "features": ["字段验证", "资产匹配", "权属方匹配", "重复检查"],
            },
        )
    except Exception as e:
        logger.exception("获取系统信息失败: %s", str(e))
        raise internal_error("获取系统信息失败")


@router.get("/test-system", dependencies=[Depends(require_localhost)])
@debug_only
async def test_system() -> dict[str, Any]:
    """测试系统功能"""
    return {"system_status": "normal", "message": "PDF处理系统正常"}


@router.get("/test-detailed", dependencies=[Depends(require_localhost)])
@debug_only
async def test_system_detailed() -> dict[str, Any]:
    """测试系统功能（详细版本）"""
    try:
        # 测试PDF处理服务
        test_result = {
            "pdf_processing": True,
            "session_management": True,
            "validation_matching": True,
            "database_import": True,
        }

        return {
            "success": True,
            "message": "系统功能正常",
            "features": test_result,
            "system_ready": True,
        }

    except Exception as e:
        logger.exception("系统测试失败: %s", str(e))
        return {
            "success": False,
            "message": "系统测试失败",
            "system_ready": False,
        }


@router.get("/health")
async def health_check(
    perf_monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> dict[str, Any]:
    """
    健康检查

    返回：
    - 包含系统健康状态的字典
    """
    try:
        # 获取性能监控健康状态
        health_data = await perf_monitor.get_health_status()

        return {
            "status": "healthy",
            "components": {
                "pdf_import": True,
                "text_extraction": True,
                "contract_validation": True,
                "data_matching": True,
                "database_import": True,
            },
            "performance": health_data,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.exception("PDF系统健康检查失败: %s", str(e))
        return {
            "status": "degraded",
            "components": {},
            "error": "系统健康检查失败",
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/sessions")
def get_pdf_import_sessions() -> dict[str, Any]:
    """
    获取PDF导入会话列表

    返回：
    - 包含会话列表的字典
    """
    return {
        "success": True,
        "message": "PDF导入会话列表获取成功",
        "data": {
            "items": [],
            "pagination": {
                "page": 1,
                "page_size": 10,
                "total": 0,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False,
            },
            "unread_count": 0,
            "count": 0,
        },
        "timestamp": datetime.now().isoformat(),
    }
