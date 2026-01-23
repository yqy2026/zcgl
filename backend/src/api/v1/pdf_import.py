"""
PDF导入API - 主路由

统一入口，包含以下子模块:
- pdf_upload: 文件上传和处理
- pdf_sessions: 会话管理
- pdf_quality: 质量评估
- pdf_v1_compatibility: V1版本兼容
- pdf_performance: 性能监控
- pdf_system: 系统信息

从原 pdf_import_unified.py (1,128 lines) 拆分而成，遵循单一职责原则。
"""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
from . import pdf_system, pdf_upload

pdf_sessions = None
try:
    from . import pdf_sessions
except ImportError as exc:
    logger.warning("PDF会话模块不可用: %s", exc)

pdf_v1_compatibility = None
try:
    from . import pdf_v1_compatibility
except ImportError as exc:
    logger.warning("PDF兼容模块不可用: %s", exc)

# 创建主路由器
router = APIRouter()

# 包含子路由器
router.include_router(pdf_upload.router, tags=["PDF上传"])
if pdf_sessions is not None:
    router.include_router(pdf_sessions.router, tags=["PDF会话管理"])
if pdf_v1_compatibility is not None:
    router.include_router(pdf_v1_compatibility.router, tags=["PDF兼容性"])
router.include_router(pdf_system.router, tags=["PDF系统信息"])

logger.info("PDF导入API主路由初始化完成，包含4个子模块")
