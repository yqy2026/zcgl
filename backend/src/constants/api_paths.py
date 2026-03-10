"""
API路径常量定义
统一API命名规范，使用 kebab-case 和 snake_case
"""


# 基础路径常量
class BasePaths:
    API = "/api/v1"  # 统一版本化架构
    HEALTH = "/api/v1/health"  # 健康检查
    ROOT = "/api/v1"  # 根路径


# 资产管理API路径
class AssetPaths:
    BASE = "/assets"
    LIST = "/assets"
    CREATE = "/assets"
    DETAIL = "/assets/{asset_id}"
    UPDATE = "/assets/{asset_id}"
    DELETE = "/assets/{asset_id}"
    BATCH_UPDATE = "/assets/batch-update"
    BATCH_DELETE = "/assets/batch-delete"
    BATCH_CUSTOM_FIELDS = "/assets/batch-custom-fields"
    SEARCH = "/assets/search"
    EXPORT = "/assets/export"
    IMPORT = "/assets/import"
    VALIDATE = "/assets/validate"
    STATISTICS = "/assets/statistics"
    HISTORY = "/assets/{asset_id}/history"
    FIELD_HISTORY = "/assets/{asset_id}/field-history/{field}"


# PDF导入API路径 (统一使用连字符)
class PDFImportPaths:
    BASE = "/pdf-import"
    UPLOAD = "/pdf-import/upload"
    PROCESS = "/pdf-import/process"
    SESSION = "/pdf-import/session/{session_id}"
    VALIDATE = "/pdf-import/validate"
    CONFIRM = "/pdf-import/confirm"
    PROGRESS = "/pdf-import/progress"
    CANCEL = "/pdf-import/cancel"
    RETRY = "/pdf-import/retry"
    ANALYSIS = "/pdf-import/analysis"
    CORRECTIONS = "/pdf-import/corrections"
    EXPORT = "/pdf-import/export"


# 认证管理API路径
class AuthPaths:
    BASE = "/auth"
    LOGIN = "/auth/login"
    LOGOUT = "/auth/logout"
    REFRESH = "/auth/refresh"
    ME = "/auth/me"
    VERIFY = "/auth/verify"
    PASSWORD_CHANGE = "/auth/password/change"  # nosec - B105: API path, not password
    PASSWORD_RESET = "/auth/password/reset"  # nosec - B105: API path, not password
    PASSWORD_CONFIRM = "/auth/password/confirm"  # nosec - B105: API path, not password


# 用户管理API路径
class UserPaths:
    BASE = "/users"
    LIST = "/users"
    CREATE = "/users"
    DETAIL = "/users/{user_id}"
    UPDATE = "/users/{user_id}"
    DELETE = "/users/{user_id}"
    LOCK = "/users/{user_id}/lock"
    UNLOCK = "/users/{user_id}/unlock"
    ROLES = "/users/{user_id}/roles"
    PERMISSIONS = "/users/{user_id}/permissions"


# 角色管理API路径
class RolePaths:
    BASE = "/roles"
    LIST = "/roles"
    CREATE = "/roles"
    DETAIL = "/roles/{role_id}"
    UPDATE = "/roles/{role_id}"
    DELETE = "/roles/{role_id}"
    PERMISSIONS = "/roles/{role_id}/permissions"
    USERS = "/roles/{role_id}/users"


# 组织架构API路径
class OrganizationPaths:
    BASE = "/organizations"
    LIST = "/organizations"
    CREATE = "/organizations"
    DETAIL = "/organizations/{org_id}"
    UPDATE = "/organizations/{org_id}"
    DELETE = "/organizations/{org_id}"
    TREE = "/organizations/tree"
    USERS = "/organizations/{org_id}/users"
    CHILDREN = "/organizations/{org_id}/children"


# 合同管理 API 路径
class ContractPaths:
    GROUPS = {
        "BASE": "/contract-groups",
        "LIST": "/contract-groups",
        "CREATE": "/contract-groups",
        "DETAIL": "/contract-groups/{group_id}",
        "UPDATE": "/contract-groups/{group_id}",
        "DELETE": "/contract-groups/{group_id}",
        "SUBMIT_REVIEW": "/contract-groups/{group_id}/submit-review",
        "CONTRACTS": "/contract-groups/{group_id}/contracts",
    }
    CONTRACTS = {
        "DETAIL": "/contracts/{contract_id}",
        "DELETE": "/contracts/{contract_id}",
        "SUBMIT_REVIEW": "/contracts/{contract_id}/submit-review",
        "APPROVE": "/contracts/{contract_id}/approve",
        "REJECT": "/contracts/{contract_id}/reject",
        "EXPIRE": "/contracts/{contract_id}/expire",
        "TERMINATE": "/contracts/{contract_id}/terminate",
        "VOID": "/contracts/{contract_id}/void",
        "RENT_TERMS": "/contracts/{contract_id}/rent-terms",
        "RENT_TERM_DETAIL": "/contracts/rent-terms/{rent_term_id}",
        "LEDGER": "/contracts/{contract_id}/ledger",
        "LEDGER_BATCH_UPDATE_STATUS": "/contracts/{contract_id}/ledger/batch-update-status",
    }


# 权属方管理API路径
class OwnershipPaths:
    BASE = "/ownerships"
    LIST = "/ownerships"
    CREATE = "/ownerships"
    DETAIL = "/ownerships/{ownership_id}"
    UPDATE = "/ownerships/{ownership_id}"
    DELETE = "/ownerships/{ownership_id}"
    ASSETS = "/ownerships/{ownership_id}/assets"
    STATISTICS = "/ownerships/statistics"


# 项目管理API路径
class ProjectPaths:
    BASE = "/projects"
    LIST = "/projects"
    CREATE = "/projects"
    DETAIL = "/projects/{project_id}"
    UPDATE = "/projects/{project_id}"
    DELETE = "/projects/{project_id}"
    ASSETS = "/projects/{project_id}/assets"
    STATISTICS = "/projects/{project_id}/statistics"


# 数据分析API路径
class AnalyticsPaths:
    BASE = "/analytics"
    DASHBOARD = "/analytics/dashboard"
    ASSETS = "/analytics/assets"
    RENTAL = "/analytics/rental"
    FINANCIAL = "/analytics/financial"
    OCCUPANCY = "/analytics/occupancy"
    TRENDS = "/analytics/trends"
    COMPARISON = "/analytics/comparison"
    EXPORT = "/analytics/export"


# 统计信息API路径
class StatisticsPaths:
    BASE = "/statistics"
    DASHBOARD = "/statistics/dashboard"
    BASIC = "/statistics/basic"
    ASSETS = "/statistics/assets"
    RENTAL = "/statistics/rental"
    FINANCIAL = "/statistics/financial"
    TREND = "/statistics/trend/{metric}"
    COMPARISON = "/statistics/comparison/{metric}"


# Excel导入导出API路径
class ExcelPaths:
    IMPORT = "/excel/import"
    EXPORT = "/excel/export"
    TEMPLATE = "/excel/import/template"
    DOWNLOAD = "/excel/download/{filename}"
    VALIDATE = "/excel/validate"
    PREVIEW = "/excel/preview"


# 数据备份API路径
class BackupPaths:
    CREATE = "/backup/create"
    LIST = "/backup/list"
    INFO = "/backup/info/{filename}"
    RESTORE = "/backup/restore"
    DELETE = "/backup/{filename}"
    CLEANUP = "/backup/cleanup"
    SCHEDULER = "/backup/scheduler/status"


# 系统管理API路径
class SystemPaths:
    BASE = "/system"
    INFO = "/system/info"
    SETTINGS = "/system/settings"
    DICTIONARIES = "/system/dictionaries"
    TEMPLATES = "/system/templates"
    LOGS = "/system/logs"
    MONITORING = "/system/monitoring"
    HEALTH = "/system/health"


# 历史记录API路径
class HistoryPaths:
    DETAIL = "/history/{history_id}"
    COMPARE = "/history/compare/{id1}/{id2}"
    ASSET_HISTORY = "/assets/{asset_id}/history"
    REVERT = "/history/revert/{history_id}"


# 自定义字段API路径
class CustomFieldPaths:
    BASE = "/asset-custom-fields"
    LIST = "/asset-custom-fields"
    CREATE = "/asset-custom-fields"
    DETAIL = "/asset-custom-fields/{field_id}"
    UPDATE = "/asset-custom-fields/{field_id}"
    DELETE = "/asset-custom-fields/{field_id}"
    BATCH_UPDATE = "/asset-custom-fields/batch-update"


# 统一路径字典
API_PATHS = {
    "base": BasePaths,
    "assets": AssetPaths,
    "pdf_import": PDFImportPaths,
    "auth": AuthPaths,
    "users": UserPaths,
    "roles": RolePaths,
    "organizations": OrganizationPaths,
    "contracts": ContractPaths,
    "ownerships": OwnershipPaths,
    "projects": ProjectPaths,
    "analytics": AnalyticsPaths,
    "statistics": StatisticsPaths,
    "excel": ExcelPaths,
    "backup": BackupPaths,
    "system": SystemPaths,
    "history": HistoryPaths,
    "custom_fields": CustomFieldPaths,
}


# 动态路径生成器
def dynamic_path(path_template: str, **kwargs: str) -> str:
    """生成动态API路径"""
    return path_template.format(**kwargs)


# 路径前缀映射
PREFIX_MAPPING = {
    "assets": "/assets",
    "pdf_import": "/pdf-import",
    "auth": "/auth",
    "users": "/users",
    "roles": "/roles",
    "organizations": "/organizations",
    "contract_groups": "/contract-groups",
    "contracts": "/contracts",
    "ownerships": "/ownerships",
    "projects": "/projects",
    "analytics": "/analytics",
    "statistics": "/statistics",
    "excel": "/excel",
    "backup": "/backup",
    "system": "/system",
    "history": "/history",
    "custom_fields": "/asset-custom-fields",
}

# 导出所有路径类
__all__ = [
    "BasePaths",
    "AssetPaths",
    "PDFImportPaths",
    "AuthPaths",
    "UserPaths",
    "RolePaths",
    "OrganizationPaths",
    "ContractPaths",
    "OwnershipPaths",
    "ProjectPaths",
    "AnalyticsPaths",
    "StatisticsPaths",
    "ExcelPaths",
    "BackupPaths",
    "SystemPaths",
    "HistoryPaths",
    "CustomFieldPaths",
    "API_PATHS",
    "dynamic_path",
    "PREFIX_MAPPING",
]
