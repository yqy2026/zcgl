"""
Compatibility shim for legacy import path:
from src.services.excel_export import ExcelExportService
"""

try:
    from .document.excel_export import ExcelExportService
except Exception:
    # Fallback to a minimal stub to ensure import success
    from .document.excel_export_stub import ExcelExportService  # type: ignore

__all__ = ["ExcelExportService"]