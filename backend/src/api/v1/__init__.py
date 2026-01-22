"""统一API路由 - 版本化架构 (/api/v1/*)"""

from fastapi import APIRouter

# 导入各个模块的路由
from .admin import router as admin_router
from .analytics import router as analytics_router
from .assets import router as assets_router
from .auth import router as auth_router
from .backup import router as backup_router
from .contact import router as contact_router
from .custom_fields import router as custom_fields_router
from .dictionaries import router as dictionaries_router
from .enum_field import router as enum_field_router

# 修复Excel模块导入 - 使用正确的router名称
from .excel import router as excel_router
from .history import router as history_router

# from .missing_apis import missing_apis_router  # Removed - module doesn't exist
from .monitoring import router as monitoring_router
from .notifications import router as notifications_router
from .occupancy import router as occupancy_router
from .operation_logs import router as operation_logs_router
from .organization import router as organization_router
from .ownership import router as ownership_router

# 尝试导入 PDF 批量路由，如果失败则跳过
pdf_batch_router: APIRouter | None = None
try:
    from .pdf_batch_routes import router as pdf_batch_router
except ImportError as e:
    import logging

    logging.warning(f"PDF batch routes not available: {e}")

from .pdf_import import router as pdf_import_router
from .project import router as project_router
from .rent_contract import router as rent_contract_router
from .roles import router as roles_router

# 修复statistics模块导入 - 使用正确的router名称
from .statistics import router as statistics_router

# 系统设置模块可能不存在，需要检查
# from .system_settings import router as system_settings_router
# test_coverage.py and test_performance.py removed - test files should be in tests/ directory
# missing_apis.py removed - had broken imports and was a temporary placeholder file
# 导入新创建的统一路由模块
from .system import router as system_router
from .system_dictionaries import router as system_dictionaries_router
from .tasks import router as tasks_router

# 尝试导入系统设置路由，如果不存在则跳过
system_settings_router: APIRouter | None = None
try:
    from .system_settings import router as system_settings_router
except ImportError:  # pragma: no cover
    print("系统设置路由模块不存在，跳过")  # pragma: no cover

# PDF导入API已统一到 pdf_import_unified.py，在main.py中直接注册
# from .pdf_import_unified import router as pdf_import_router
# from .organization_permissions import router as organization_permissions_router  # 已删除
# from .rbac import router as rbac_router  # 已删除
# from .dynamic_permissions import router as dynamic_permissions_router  # 已删除
# from .audit_dashboard import router as audit_dashboard_router  # 已删除
# from .permission_delegation import router as permission_delegation_router  # 已删除
# from .multi_tenant import router as multi_tenant_router  # 已删除
# from .dynamic_permission_api import router as dynamic_permission_api_router  # 已删除
# from .audit_dashboard_api import router as audit_dashboard_api_router  # 已删除
# from .test_assets import router as test_assets_router  # 已删除
# from .security_monitor import router as security_monitor_router  # 已删除
# from .ocr_analysis import router as ocr_analysis_router  # 已删除

# 创建统一API路由器 - 版本化架构
api_router = APIRouter()

# 包含各个模块的路由（使用版本化前缀，最终路径为 /api/v1/*）
api_router.include_router(auth_router, prefix="/auth", tags=["用户认证"])
api_router.include_router(roles_router, prefix="/roles", tags=["角色管理"])
api_router.include_router(operation_logs_router, prefix="/logs", tags=["操作日志"])
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
api_router.include_router(backup_router, prefix="/backup", tags=["数据备份和恢复"])
api_router.include_router(admin_router, prefix="/admin", tags=["系统管理"])
api_router.include_router(
    system_dictionaries_router, prefix="/system/dictionaries", tags=["系统字典管理"]
)
api_router.include_router(
    custom_fields_router, prefix="/asset-custom-fields", tags=["自定义字段管理"]
)
api_router.include_router(
    organization_router, prefix="/organizations", tags=["组织架构管理"]
)
api_router.include_router(enum_field_router, tags=["枚举字段管理"])
api_router.include_router(dictionaries_router, tags=["统一字典管理"])
api_router.include_router(ownership_router, prefix="/ownerships", tags=["权属方管理"])
api_router.include_router(project_router, prefix="/projects", tags=["项目管理"])
api_router.include_router(
    rent_contract_router, prefix="/rental-contracts", tags=["租赁合同管理"]
)
# Analytics路由 - Service层重构版 (2026-01-04)
# 原始 2017 行的 analytics.py 已重构为使用 AnalyticsService
# 业务逻辑迁移至 src/services/analytics/analytics_service.py
api_router.include_router(analytics_router, prefix="/analytics", tags=["综合分析"])

# 条件注册系统设置路由
if system_settings_router is not None:
    api_router.include_router(
        system_settings_router, prefix="/system", tags=["系统设置"]
    )
api_router.include_router(monitoring_router, prefix="/monitoring", tags=["系统监控"])
# test_coverage and test_performance routers removed
# defect_tracking router removed - architecture violation (raw SQL in API layer)
# missing_apis_router removed - was a temporary placeholder with broken imports

# 注册新创建的统一路由模块
api_router.include_router(system_router, tags=["系统管理"])
api_router.include_router(pdf_import_router, prefix="/pdf-import", tags=["PDF智能导入"])
if pdf_batch_router is not None:
    api_router.include_router(pdf_batch_router, tags=["PDF批量导入"])
api_router.include_router(
    notifications_router, prefix="/notifications", tags=["通知管理"]
)
api_router.include_router(contact_router, prefix="/contacts", tags=["联系人管理"])

# from .simple_pdf_import import router as pdf_import_router  # 已删除
# api_router.include_router(
#     pdf_import_router,
#     prefix="/pdf_import",
#     tags=["PDF合同导入"])
# )
# PDF智能导入API (统一版本，包含完整功能) - 已移至main.py注册
#     tags=["PDF智能导入"]
# 注释掉已删除的API路由器
# api_router.include_router(organization_permissions_router, ...)  # 已删除
# api_router.include_router(rbac_router, ...)  # 已删除
# api_router.include_router(dynamic_permissions_router, ...)  # 已删除
# api_router.include_router(audit_dashboard_router, ...)  # 已删除
# api_router.include_router(permission_delegation_router, ...)  # 已删除
# api_router.include_router(multi_tenant_router, ...)  # 已删除
# api_router.include_router(dynamic_permission_api_router, ...)  # 已删除
# api_router.include_router(audit_dashboard_api_router, ...)  # 已删除
# api_router.include_router(test_assets_router, ...)  # 已删除
# api_router.include_router(security_monitor_router, ...)  # 已删除
# api_router.include_router(ocr_analysis_router, ...)  # 已删除

__all__ = ["api_router"]
