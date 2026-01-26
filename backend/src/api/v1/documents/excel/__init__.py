"""
Excel模块 - 路由聚合

将所有Excel相关的子路由合并到一个主路由器
"""

from fastapi import APIRouter

from src.security.route_guards import debug_only
from . import config, export_ops, import_ops, preview, status, template

# 创建主路由器
router = APIRouter(prefix="/excel", tags=["Excel导入导出"])

# 包含所有子路由
router.include_router(template.router)
router.include_router(config.router)
router.include_router(preview.router)
router.include_router(import_ops.router)
router.include_router(export_ops.router)
router.include_router(status.router)


# 测试端点
@router.get("/test", summary="测试端点")
@debug_only
async def test_endpoint():
    """测试端点"""
    return {"message": "Excel API 测试成功", "timestamp": "2025-08-27"}


# 向后兼容导出 - 允许直接导入 router
__all__ = ["router"]
