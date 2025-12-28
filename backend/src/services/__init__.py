"""
Service Layer Entry Point

Refactored service layer organized by business domain:
- asset/        Asset management services
- permission/   Permission management services
- document/     Document processing services
- analytics/    Analytics services
- core/         Core services
"""

# Import core services with error handling for gradual migration
__all__ = []

# Permission services
try:
    from .permission.rbac_service import RBACService
    __all__.append('RBACService')
except Exception:
    pass

try:
    from .permission.permission_cache_service import get_permission_cache_service
    __all__.append('get_permission_cache_service')
except Exception:
    pass

# Core services
try:
    from .core.auth_service import AuthService
    __all__.append('AuthService')
except Exception:
    pass

try:
    from .core.security_service import SecurityService
    __all__.append('SecurityService')
except Exception:
    pass

try:
    from .core.audit_service import EnhancedAuditLogger
    __all__.append('EnhancedAuditLogger')
except Exception:
    pass

try:
    from .core.error_recovery_service import ErrorRecoveryEngine
    __all__.append('ErrorRecoveryEngine')
except Exception:
    # Provide a minimal stub to ensure import success
    class ErrorRecoveryEngine:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass
    __all__.append('ErrorRecoveryEngine')

# Asset services
try:
    from .asset.asset_calculator import AssetCalculator
    __all__.append('AssetCalculator')
except Exception:
    pass

try:
    from .asset.asset_calculator import OccupancyRateCalculator
    __all__.append('OccupancyRateCalculator')
except Exception:
    pass

# Document services
try:
    from .document.pdf_import_service import PDFImportService
    __all__.append('PDFImportService')
except Exception:
    pass

try:
    from .document.excel_export import ExcelExportService
    __all__.append('ExcelExportService')
except Exception:
    pass

# Data analysis services
try:
    from .analytics.statistics import StatisticsService
    __all__.append('StatisticsService')
except Exception:
    pass

try:
    from .analytics.data_filter import DataFilterService
    __all__.append('DataFilterService')
except Exception:
    pass
