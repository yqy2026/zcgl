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

# Core Services
__all__: list[str] = []
logger = logging.getLogger(__name__)


def _log_import_error(service_name: str) -> None:
    logger.warning(f"Service import failed: {service_name}", exc_info=True)


try:
    from .auth_service import AuthService as AuthService

    __all__.append("AuthService")
except Exception:  # nosec - B110: Intentional graceful degradation
    # Fallback to legacy shim
    try:
        from ..auth_service import AuthService as AuthService  # type: ignore[no-redef]

        __all__.append("AuthService")
    except Exception:  # nosec - B110: Intentional graceful degradation
        _log_import_error("core.auth_service.AuthService (legacy fallback)")

# Import AuditService
try:
    from . import audit_service

    AuditService = audit_service.AuditService
    __all__.append("AuditService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("core.audit_service.AuditService")

try:
    from .security_service import SecurityService as SecurityService

    __all__.append("SecurityService")
except Exception:  # nosec - B110: Intentional graceful degradation
    # Provide a minimal stub to ensure import success
    class SecurityService:  # type: ignore[no-redef]
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

    __all__.append("SecurityService")
    _log_import_error("core.security_service.SecurityService (stubbed)")

try:
    from .error_recovery_service import ErrorRecoveryEngine as ErrorRecoveryEngine

    __all__.append("ErrorRecoveryEngine")
except Exception:  # nosec - B110: Intentional graceful degradation
    # Fallback to legacy shim
    try:
        from ..error_recovery_service import (
            ErrorRecoveryEngine as ErrorRecoveryEngine,
        )

        __all__.append("ErrorRecoveryEngine")
    except Exception:  # nosec - B110: Intentional graceful degradation
        # Provide a minimal stub to ensure import success
        class ErrorRecoveryEngine:  # type: ignore[no-redef]
            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

        __all__.append("ErrorRecoveryEngine")
        _log_import_error("core.error_recovery_service.ErrorRecoveryEngine (stubbed)")
