"""
核心服务模块

包含系统核心服务：
- 认证服务
- 审计服务
- 安全服务
- 文件管理服务
- 错误恢复服务
- 数据验证服务
- 数据安全服务
"""

# Optional service imports; log failures for visibility during startup.
import logging
from typing import Any

# Core Services
__all__: list[str] = []
logger = logging.getLogger(__name__)


def _log_import_error(service_name: str) -> None:
    logger.warning(f"Service import failed: {service_name}", exc_info=True)


SecurityService: Any
ErrorRecoveryEngine: Any

# Import AuditService
try:
    from . import audit_service

    AuditService = audit_service.AuditService
    __all__.append("AuditService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("core.audit_service.AuditService")

try:
    from .security_service import SecurityService as _SecurityService

    SecurityService = _SecurityService

    __all__.append("SecurityService")
except Exception:  # nosec - B110: Intentional graceful degradation
    # Provide a minimal stub to ensure import success
    class _SecurityServiceStub:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

    SecurityService = _SecurityServiceStub
    __all__.append("SecurityService")
    _log_import_error("core.security_service.SecurityService (stubbed)")

try:
    from .error_recovery_service import ErrorRecoveryEngine as _ErrorRecoveryEngine

    ErrorRecoveryEngine = _ErrorRecoveryEngine

    __all__.append("ErrorRecoveryEngine")
except Exception:  # nosec - B110: Intentional graceful degradation
    # Fallback to legacy shim
    try:
        from ..error_recovery_service import (
            ErrorRecoveryEngine as _LegacyErrorRecoveryEngine,
        )

        ErrorRecoveryEngine = _LegacyErrorRecoveryEngine
        __all__.append("ErrorRecoveryEngine")
    except Exception:  # nosec - B110: Intentional graceful degradation
        # Provide a minimal stub to ensure import success
        class _ErrorRecoveryEngineStub:
            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

        ErrorRecoveryEngine = _ErrorRecoveryEngineStub
        __all__.append("ErrorRecoveryEngine")
        _log_import_error("core.error_recovery_service.ErrorRecoveryEngine (stubbed)")
