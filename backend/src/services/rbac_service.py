"""
Compatibility shim for legacy import path:
from src.services.rbac_service import RBACService
"""

from .permission.rbac_service import RBACService

__all__ = ["RBACService"]