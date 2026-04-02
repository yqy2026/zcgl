"""统一API路由 - 版本化架构 (/api/v1/*)"""

import logging
from importlib import import_module

from fastapi import APIRouter

# --- Party-Role Phase 1 新模块加载（触发 route_registry.register_router） ---
from . import (
    authz,  # noqa: F401
    party,  # noqa: F401
)

# 导入各个模块的路由 - Analytics
from .analytics.analytics import router as analytics_router
from .analytics.statistics import router as statistics_router
from .approval import router as approval_router

# 导入各个模块的路由 - Assets
from .assets.assets import router as assets_router
from .assets.custom_fields import router as custom_fields_router
from .assets.occupancy import router as occupancy_router
from .assets.ownership import router as ownership_router
from .assets.project import router as project_router
from .assets.property_certificate import router as property_certificate_router

# 导入各个模块的路由 - Auth
from .auth.admin import router as admin_router
from .auth.auth import router as auth_router
from .auth.data_policies import router as data_policies_router
from .auth.organization import router as organization_router
from .auth.roles import router as roles_router

# 导入各个模块的路由 - Contracts
from .contracts import contract_groups_router, ledger_router

# 导入各个模块的路由 - Documents
from .documents.excel import router as excel_router
from .documents.pdf_import import router as pdf_import_router

# 导入各个模块的路由 - LLM Prompts
from .llm_prompts import router as llm_prompts_router
from .search import router as search_router

# 导入各个模块的路由 - System
from .system.backup import router as backup_router
from .system.collection import router as collection_router
from .system.contact import router as contact_router
from .system.dictionaries import router as dictionaries_router
from .system.enum_field import router as enum_field_router
from .system.error_recovery import router as error_recovery_router
from .system.history import router as history_router
from .system.monitoring import router as monitoring_router
from .system.notifications import router as notifications_router
from .system.operation_logs import router as operation_logs_router
from .system.system import router as system_router
from .system.tasks import router as tasks_router

logger = logging.getLogger(__name__)


def _load_optional_router(
    module_path: str,
    *,
    missing_message: str,
    log_level: str = "warning",
) -> APIRouter | None:
    """按需加载可选路由模块，降低顶部条件导入复杂度。"""
    try:
        module = import_module(module_path, package=__package__)
    except ImportError as exc:
        if log_level == "debug":
            logger.debug(missing_message, exc)
        else:
            logger.warning(missing_message, exc)
        return None

    router = getattr(module, "router", None)
    if isinstance(router, APIRouter):
        return router

    logger.warning("可选路由模块 %s 存在但未暴露 APIRouter router 变量", module_path)
    return None


pdf_batch_router = _load_optional_router(
    ".documents.pdf_batch_routes",
    missing_message="PDF batch routes not available: %s",
)
system_settings_router = _load_optional_router(
    ".system.system_settings",
    missing_message="系统设置路由模块不存在，跳过: %s",
    log_level="debug",
)

# 创建统一API路由器 - 版本化架构
api_router = APIRouter()

# 包含各个模块的路由（使用版本化前缀，最终路径为 /api/v1/*）
api_router.include_router(auth_router, prefix="/auth", tags=["用户认证"])
api_router.include_router(data_policies_router, prefix="/auth", tags=["数据策略包"])
api_router.include_router(roles_router, prefix="/roles", tags=["角色管理"])
api_router.include_router(operation_logs_router, prefix="/logs", tags=["操作日志"])
api_router.include_router(approval_router, prefix="/approval", tags=["审批流"])
api_router.include_router(assets_router, prefix="/assets", tags=["资产管理"])
api_router.include_router(
    excel_router, tags=["Excel导入导出"]
)  # 移除重复的prefix，excel.py已定义
api_router.include_router(history_router, prefix="/history", tags=["变更历史"])
api_router.include_router(
    statistics_router, prefix="/statistics", tags=["数据统计和报表"]
)
api_router.include_router(
    tasks_router, tags=["任务管理"]
)  # Remove prefix - router defines its own paths
api_router.include_router(occupancy_router, prefix="/occupancy", tags=["出租率计算"])
api_router.include_router(admin_router, tags=["系统管理"])

# REMOVED CONFLICTING ROUTER
# api_router.include_router(
#     system_dictionaries_router, prefix="/system/dictionaries", tags=["系统字典管理"]
# )

api_router.include_router(
    custom_fields_router, prefix="/asset-custom-fields", tags=["自定义字段管理"]
)
api_router.include_router(
    organization_router, prefix="/organizations", tags=["组织架构管理"]
)
api_router.include_router(enum_field_router, tags=["枚举字段管理"])

# dictionaries_router 自带 prefix="/system/dictionaries"，此处直接 include
api_router.include_router(dictionaries_router)  # Unified dictionary API

api_router.include_router(ownership_router, prefix="/ownerships", tags=["权属方管理"])
api_router.include_router(project_router, prefix="/projects", tags=["项目管理"])
api_router.include_router(search_router, prefix="/search", tags=["全局搜索"])
# 合同组体系（REQ-RNT-001）：/contract-groups/* 和 /contracts/*
api_router.include_router(contract_groups_router, tags=["合同组管理"])
api_router.include_router(ledger_router, tags=["台账管理"])
# Analytics路由 - Service层重构版 (2026-01-04)
# 原始 2017 行的 analytics.py 已重构为使用 AnalyticsService
# 业务逻辑迁移至 src/services/analytics/analytics_service.py
api_router.include_router(analytics_router, prefix="/analytics", tags=["综合分析"])

# 条件注册系统设置路由
if system_settings_router is not None:
    logger.info("Registering system_settings_router")
    api_router.include_router(
        system_settings_router, prefix="/system", tags=["系统设置"]
    )
else:
    logger.warning("system_settings_router is None, NOT registering")
api_router.include_router(monitoring_router, prefix="/monitoring", tags=["系统监控"])

# 注册新创建的统一路由模块
api_router.include_router(system_router, tags=["系统管理"])
api_router.include_router(backup_router, prefix="/system/backup", tags=["数据备份"])
api_router.include_router(pdf_import_router, prefix="/pdf-import", tags=["PDF智能导入"])
if pdf_batch_router is not None:
    api_router.include_router(pdf_batch_router, tags=["PDF批量导入"])
api_router.include_router(
    notifications_router, prefix="/notifications", tags=["通知管理"]
)
api_router.include_router(contact_router, prefix="/contacts", tags=["联系人管理"])
api_router.include_router(collection_router, prefix="/collections", tags=["催缴管理"])
api_router.include_router(error_recovery_router, tags=["错误恢复"])
api_router.include_router(
    llm_prompts_router, prefix="/llm-prompts", tags=["LLM提示词管理"]
)
api_router.include_router(
    property_certificate_router, prefix="/property-certificates", tags=["产权证管理"]
)

__all__ = ["api_router"]
