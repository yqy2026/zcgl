"""
Service Layer Entry Point

Refactored service layer organized by business domain:
- asset/        Asset management services
- permission/   Permission management services
- document/     Document processing services
- analytics/    Analytics services
- core/         Core services
"""

# Optional service imports; log failures for visibility during startup.
import logging

# Import core services with error handling for gradual migration
__all__: list[str] = []
logger = logging.getLogger(__name__)


def _log_import_error(service_name: str) -> None:
    logger.warning(f"Service import failed: {service_name}", exc_info=True)


# Permission services
try:
    from .permission.rbac_service import RBACService as RBACService

    __all__.append("RBACService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("permission.rbac_service.RBACService")

try:
    from .permission.permission_cache_service import (
        get_permission_cache_service as get_permission_cache_service,
    )

    __all__.append("get_permission_cache_service")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error(
        "permission.permission_cache_service.get_permission_cache_service"
    )

try:
    from .core.security_service import SecurityService as SecurityService

    __all__.append("SecurityService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("core.security_service.SecurityService")

# Core services - Audit Service
try:
    from .core.audit_service import AuditService as AuditService

    __all__.append("AuditService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("core.audit_service.AuditService")

try:
    from .core.error_recovery_service import (
        ErrorRecoveryEngine as ErrorRecoveryEngine,
    )

    __all__.append("ErrorRecoveryEngine")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("core.error_recovery_service.ErrorRecoveryEngine")

    class _ErrorRecoveryEngine:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

    ErrorRecoveryEngine = _ErrorRecoveryEngine
    __all__.append("ErrorRecoveryEngine")

# Asset services
try:
    from .asset.asset_calculator import AssetCalculator as AssetCalculator

    __all__.append("AssetCalculator")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("asset.asset_calculator.AssetCalculator")

try:
    from .asset.asset_calculator import (
        OccupancyRateCalculator as OccupancyRateCalculator,
    )

    __all__.append("OccupancyRateCalculator")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("asset.asset_calculator.OccupancyRateCalculator")

# Document services
try:
    from .document.pdf_import_service import PDFImportService as PDFImportService

    __all__.append("PDFImportService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("document.pdf_import_service.PDFImportService")

try:
    from .excel.excel_export_service import ExcelExportService as ExcelExportService

    __all__.append("ExcelExportService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("excel.excel_export_service.ExcelExportService")

try:
    from .excel.excel_import_service import ExcelImportService as ExcelImportService

    __all__.append("ExcelImportService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("excel.excel_import_service.ExcelImportService")

# Data analysis services
try:
    from .analytics.analytics_service import AnalyticsService as AnalyticsService

    __all__.append("AnalyticsService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("analytics.analytics_service.AnalyticsService")
