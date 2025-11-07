"""
Compatibility shim for legacy import path:
from src.services.pdf_import_service import PDFImportService
"""

try:
    from .document.pdf_import_service import PDFImportService
except Exception:
    # Fallback to a minimal stub to ensure import success
    from .document.pdf_import_service_stub import PDFImportService  # type: ignore

__all__ = ["PDFImportService"]