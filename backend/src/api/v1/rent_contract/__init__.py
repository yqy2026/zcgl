"""
租金合同模块 - 路由聚合

将所有租金合同相关的子路由合并到一个主路由器
"""

from fastapi import APIRouter

from . import attachments, contracts, excel_ops, ledger, lifecycle, statistics, terms

# 创建主路由器
router = APIRouter()

# 包含所有子路由
router.include_router(contracts.router)
router.include_router(lifecycle.router)
router.include_router(terms.router)
router.include_router(ledger.router)
router.include_router(statistics.router)
router.include_router(excel_ops.router)
router.include_router(attachments.router)

# 向后兼容导出
__all__ = ["router"]
