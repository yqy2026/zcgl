"""
调试端点模块 - 仅在开发环境加载

此模块通过 main.py 条件加载，生产环境不会注册这些路由。
"""

from fastapi import APIRouter

from .auth_debug import router as auth_debug_router

router = APIRouter(prefix="/debug", tags=["Debug"])
router.include_router(auth_debug_router)

__all__ = ["router"]
