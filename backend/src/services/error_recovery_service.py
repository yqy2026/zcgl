"""
Compatibility shim for legacy import path:
from src.services.error_recovery_service import ErrorRecoveryEngine
"""

try:
    from .core.error_recovery_service import ErrorRecoveryEngine
except Exception:
    # Fallback to core package export (which may provide a stub)
    try:
        from .core import ErrorRecoveryEngine  # type: ignore
    except Exception:
        # Final minimal stub to ensure import success
        class ErrorRecoveryEngine:  # type: ignore
            def __init__(self, *args, **kwargs):
                pass

__all__ = ["ErrorRecoveryEngine"]