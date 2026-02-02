# Document Processing Services
# Using explicit re-export pattern to satisfy ruff F401
import logging

__all__: list[str] = []
logger = logging.getLogger(__name__)


def _log_import_error(service_name: str) -> None:
    logger.warning(f"Service import failed: {service_name}", exc_info=True)


# Core PDF processing services
try:
    from .pdf_import_service import PDFImportService as PDFImportService

    __all__.append("PDFImportService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("document.pdf_import_service.PDFImportService")

try:
    from .pdf_processing_service import (
        PDFProcessingService as PDFProcessingService,
    )

    __all__.append("PDFProcessingService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("document.pdf_processing_service.PDFProcessingService")

try:
    from .parallel_pdf_processor import (
        ParallelPDFProcessor as ParallelPDFProcessor,
    )

    __all__.append("ParallelPDFProcessor")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("document.parallel_pdf_processor.ParallelPDFProcessor")

try:
    from .pdf_quality_assessment import (
        PDFQualityAssessment as PDFQualityAssessment,
    )

    __all__.append("PDFQualityAssessment")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("document.pdf_quality_assessment.PDFQualityAssessment")

try:
    from .pdf_processing_cache import PDFProcessingCache as PDFProcessingCache

    __all__.append("PDFProcessingCache")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("document.pdf_processing_cache.PDFProcessingCache")

try:
    from .pdf_session_service import PDFSessionService as PDFSessionService

    __all__.append("PDFSessionService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("document.pdf_session_service.PDFSessionService")

# Contract extraction services
try:
    from .contract_extractor import ContractExtractor as ContractExtractor

    __all__.extend(["ContractExtractor"])
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("document.contract_extractor.ContractExtractor")

try:
    from .contract_extractor_manager import (
        ContractExtractorManager as ContractExtractorManager,
    )

    __all__.append("ContractExtractorManager")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("document.contract_extractor_manager.ContractExtractorManager")

# Excel services
try:
    from .excel_export import ExcelExportService as ExcelExportService

    __all__.append("ExcelExportService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("document.excel_export.ExcelExportService")

try:
    from .excel_import import ExcelImportService as ExcelImportService

    __all__.append("ExcelImportService")
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("document.excel_import.ExcelImportService")

# V3 Document Extraction Manager (2026-01)
try:
    from .extraction_manager import (
        DocumentExtractionManager as DocumentExtractionManager,
    )
    from .extraction_manager import DocumentType as DocumentType
    from .extraction_manager import ExtractionResult as ExtractionResult
    from .extraction_manager import get_extraction_manager as get_extraction_manager

    __all__.extend(
        [
            "DocumentExtractionManager",
            "DocumentType",
            "ExtractionResult",
            "get_extraction_manager",
        ]
    )
except Exception:  # nosec - B110: Intentional graceful degradation
    _log_import_error("document.extraction_manager.DocumentExtractionManager")
