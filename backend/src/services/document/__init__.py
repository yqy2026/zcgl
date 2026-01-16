# Document Processing Services
# Using explicit re-export pattern to satisfy ruff F401
__all__: list[str] = []

# Core PDF processing services
try:
    from .pdf_import_service import PDFImportService as PDFImportService

    __all__.append("PDFImportService")
except Exception:  # nosec - B110: Intentional graceful degradation
    pass

try:
    from .pdf_processing_service import (
        PDFProcessingService as PDFProcessingService,
    )

    __all__.append("PDFProcessingService")
except Exception:  # nosec - B110: Intentional graceful degradation
    pass

try:
    from .parallel_pdf_processor import (
        ParallelPDFProcessor as ParallelPDFProcessor,
    )

    __all__.append("ParallelPDFProcessor")
except Exception:  # nosec - B110: Intentional graceful degradation
    pass

try:
    from .pdf_quality_assessment import (
        PDFQualityAssessment as PDFQualityAssessment,
    )

    __all__.append("PDFQualityAssessment")
except Exception:  # nosec - B110: Intentional graceful degradation
    pass

try:
    from .pdf_processing_cache import PDFProcessingCache as PDFProcessingCache

    __all__.append("PDFProcessingCache")
except Exception:  # nosec - B110: Intentional graceful degradation
    pass

try:
    from .pdf_session_service import PDFSessionService as PDFSessionService

    __all__.append("PDFSessionService")
except Exception:  # nosec - B110: Intentional graceful degradation
    pass

# Contract extraction services
try:
    from .contract_extractor import ContractExtractor as ContractExtractor

    __all__.extend(["ContractExtractor"])
except Exception:  # nosec - B110: Intentional graceful degradation
    pass

try:
    from .contract_extractor_manager import (
        ContractExtractorManager as ContractExtractorManager,
    )

    __all__.append("ContractExtractorManager")
except Exception:  # nosec - B110: Intentional graceful degradation
    pass

try:
    from .chinese_nlp_processor import ChineseNLPProcessor as ChineseNLPProcessor

    __all__.append("ChineseNLPProcessor")
except Exception:  # nosec - B110: Intentional graceful degradation
    pass

# Excel services
try:
    from .excel_export import ExcelExportService as ExcelExportService

    __all__.append("ExcelExportService")
except Exception:  # nosec - B110: Intentional graceful degradation
    pass

try:
    from .excel_import import ExcelImportService as ExcelImportService

    __all__.append("ExcelImportService")
except Exception:  # nosec - B110: Intentional graceful degradation
    pass

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
    pass
