# Permission Management Services
__all__ = []

try:
    from .rbac_service import RBACService  # noqa: F401

    __all__.append("RBACService")  # pragma: no cover
except Exception:  # nosec - B110: Intentional graceful degradation  # pragma: no cover
    # Fallback to legacy shim if available
    try:
        from ..rbac_service import RBACService  # type: ignore  # noqa: F401

        __all__.append("RBACService")  # pragma: no cover
    except Exception:  # nosec - B110: Intentional graceful degradation  # pragma: no cover
        pass

try:
    from .permission_cache_service import get_permission_cache_service  # noqa: F401

    __all__.append("get_permission_cache_service")  # pragma: no cover
except Exception:  # nosec - B110: Intentional graceful degradation  # pragma: no cover
    pass
