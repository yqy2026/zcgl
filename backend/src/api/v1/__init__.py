"""
API v1版本路由
"""

from fastapi import APIRouter
from .auth import router as auth_router
from .assets import router as assets_router
from .excel import router as excel_router
from .history import router as history_router
# from .statistics import router as statistics_router  # 暂时注释，修复导入错误
from .occupancy import router as occupancy_router
from .backup import router as backup_router
from .admin import router as admin_router
from .system_dictionaries import router as system_dictionaries_router
from .custom_fields import router as custom_fields_router
from .organization import router as organization_router
from .enum_field import router as enum_field_router
from .dictionaries import router as dictionaries_router
from .ownership import router as ownership_router
from .project import router as project_router
from .rent_contract import router as rent_contract_router
from .analytics import router as analytics_router
# PDF导入API已统一到 pdf_import_unified.py
from .pdf_import_unified import router as pdf_import_router
# from .organization_permissions import router as organization_permissions_router  # 已删除
# from .rbac import router as rbac_router  # 已删除
# from .dynamic_permissions import router as dynamic_permissions_router  # 已删除
# from .audit_dashboard import router as audit_dashboard_router  # 已删除
# from .permission_delegation import router as permission_delegation_router  # 已删除
# from .multi_tenant import router as multi_tenant_router  # 已删除
# from .organization_permissions import router as organization_permissions_router  # 已删除
# from .dynamic_permission_api import router as dynamic_permission_api_router  # 已删除
# from .audit_dashboard_api import router as audit_dashboard_api_router  # 已删除
# from .test_assets import router as test_assets_router  # 已删除
# from .security_monitor import router as security_monitor_router  # 已删除
# from .ocr_analysis import router as ocr_analysis_router  # 已删除

# 创建API v1路由器
api_router = APIRouter(prefix="/api/v1")

# 包含各个模块的路由
api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["用户认证"]
)

api_router.include_router(
    assets_router,
    prefix="/assets",
    tags=["资产管理"]
)

api_router.include_router(
    excel_router,
    prefix="/excel",
    tags=["Excel导入导出"]
)


api_router.include_router(
    history_router,
    prefix="/history",
    tags=["变更历史"]
)

# api_router.include_router(
#     statistics_router,
#     prefix="/statistics",
#     tags=["数据统计和报表"]
# )  # 暂时注释，修复导入错误

api_router.include_router(
    occupancy_router,
    prefix="/occupancy",
    tags=["出租率计算"]
)

api_router.include_router(
    backup_router,
    prefix="/backup",
    tags=["数据备份和恢复"]
)

api_router.include_router(
    admin_router,
    prefix="/admin",
    tags=["系统管理"]
)

api_router.include_router(
    system_dictionaries_router,
    prefix="/system-dictionaries",
    tags=["系统字典管理"]
)

api_router.include_router(
    custom_fields_router,
    prefix="/asset-custom-fields",
    tags=["自定义字段管理"]
)

api_router.include_router(
    organization_router,
    prefix="/organizations",
    tags=["组织架构管理"]
)

api_router.include_router(
    enum_field_router,
    tags=["枚举字段管理"]
)

api_router.include_router(
    dictionaries_router,
    tags=["统一字典管理"]
)

api_router.include_router(
    ownership_router,
    prefix="/ownerships",
    tags=["权属方管理"]
)

api_router.include_router(
    project_router,
    prefix="/projects",
    tags=["项目管理"]
)

api_router.include_router(
    rent_contract_router,
    prefix="/rent_contract",
    tags=["租金台账管理"]
)

api_router.include_router(
    analytics_router,
    prefix="/analytics",
    tags=["综合分析"]
)

# from .simple_pdf_import import router as pdf_import_router  # 已删除
# api_router.include_router(
#     pdf_import_router,
#     prefix="/pdf_import",
#     tags=["PDF合同导入"]
# )

# api_router.include_router(
#     enhanced_pdf_import_router,
#     prefix="/enhanced_pdf_import",
#     tags=["增强PDF智能导入"]
# )

# api_router.include_router(
#     ocr_pdf_import_router,
#     prefix="/ocr_pdf_import",
#     tags=["完整OCR PDF导入"]
# )

# PDF智能导入API (统一版本，包含完整功能)
api_router.include_router(
    pdf_import_router,
    prefix="/pdf_import",
    tags=["PDF智能导入"]
)

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
