"""
Compatibility shim for legacy import path:
from src.services.auth_service import AuthService
"""

from .core.auth_service import AuthService

__all__ = ["AuthService"]