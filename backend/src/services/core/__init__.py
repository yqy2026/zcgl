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


ErrorRecoveryEngine: Any

# Import AuditService
try:
    from . import audit_service

    AuditService = audit_service.AuditService
    __all__.append("AuditService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("core.audit_service.AuditService")

try:
    from ..error_recovery_service import ErrorRecoveryEngine as _ErrorRecoveryEngine

    ErrorRecoveryEngine = _ErrorRecoveryEngine
    __all__.append("ErrorRecoveryEngine")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("error_recovery_service.ErrorRecoveryEngine")
