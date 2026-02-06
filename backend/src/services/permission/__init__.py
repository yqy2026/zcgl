# Permission Management Services
import logging
from typing import Any

__all__: list[str] = []
logger = logging.getLogger(__name__)


def _log_import_error(service_name: str) -> None:
    logger.warning(f"Service import failed: {service_name}", exc_info=True)


RBACService: Any

try:
    from .rbac_service import RBACService as _RBACService

    RBACService = _RBACService

    __all__.append("RBACService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("permission.rbac_service.RBACService")

try:
    from .permission_cache_service import (
        get_permission_cache_service as get_permission_cache_service,
    )

    __all__.append("get_permission_cache_service")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error(
        "permission.permission_cache_service.get_permission_cache_service"
    )
