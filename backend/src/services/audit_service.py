"""
Compatibility shim for legacy import path:
from src.services.audit_service import AuditService

Provides alias AuditService -> EnhancedAuditLogger.
"""

from .core.audit_service import EnhancedAuditLogger as AuditService
from .core.audit_service import EnhancedAuditLogger

__all__ = ["AuditService", "EnhancedAuditLogger"]