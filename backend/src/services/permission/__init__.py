# Permission Management Services
__all__: list[str] = []

try:
    from .rbac_service import RBACService as RBACService

    __all__.append("RBACService")
except Exception:  # nosec - B110: Intentional graceful degradation
    # Fallback to legacy shim if available
    try:
        from ..rbac_service import RBACService as RBACService  # type: ignore

        __all__.append("RBACService")
    except Exception:  # nosec - B110: Intentional graceful degradation
        pass

try:
    from .permission_cache_service import (
        get_permission_cache_service as get_permission_cache_service,
    )

    __all__.append("get_permission_cache_service")
except Exception:  # nosec - B110: Intentional graceful degradation
    pass
