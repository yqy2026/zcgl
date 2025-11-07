# Document Processing Services
__all__ = []

try:
    from .unified_pdf_processor import UnifiedPDFProcessor
    __all__.append('UnifiedPDFProcessor')
except Exception:
    # Fallback to legacy path if a shim exists elsewhere
    try:
        from ..unified_pdf_processor import UnifiedPDFProcessor  # type: ignore
        __all__.append('UnifiedPDFProcessor')
    except Exception:
        pass

try:
    from .pdf_import_service import PDFImportService
    __all__.append('PDFImportService')
except Exception:
    # Fallback to legacy shim
    try:
        from ..pdf_import_service import PDFImportService  # type: ignore
        __all__.append('PDFImportService')
    except Exception:
        # Final fallback to stub
        try:
            from .pdf_import_service_stub import PDFImportService  # type: ignore
            __all__.append('PDFImportService')
        except Exception:
            pass

try:
    from .excel_export import ExcelExportService
    __all__.append('ExcelExportService')
except Exception:
    # Fallback to legacy shim
    try:
        from ..excel_export import ExcelExportService  # type: ignore
        __all__.append('ExcelExportService')
    except Exception:
        # Final fallback to stub
        try:
            from .excel_export_stub import ExcelExportService  # type: ignore
            __all__.append('ExcelExportService')
        except Exception:
            pass
