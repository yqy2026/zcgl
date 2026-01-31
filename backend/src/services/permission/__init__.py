# Permission Management Services
import logging

__all__: list[str] = []
logger = logging.getLogger(__name__)


def _log_import_error(service_name: str) -> None:
    logger.warning(f"Service import failed: {service_name}", exc_info=True)


try:
    from .rbac_service import RBACService as RBACService

    __all__.append("RBACService")
except Exception:  # nosec - B110: Intentional graceful degradation
    # Fallback to legacy shim if available
    try:
        from ..rbac_service import RBACService as RBACService  # type: ignore

        __all__.append("RBACService")
    except Exception:  # nosec - B110: Intentional graceful degradation
        _log_import_error("permission.rbac_service.RBACService (legacy fallback)")

try:
    from .permission_cache_service import (
        get_permission_cache_service as get_permission_cache_service,
    )

    __all__.append("get_permission_cache_service")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error(
        "permission.permission_cache_service.get_permission_cache_service"
    )
