"""
Contract extractor manager.

Provides a simple orchestration layer to extract contract data from PDFs.
"""

from __future__ import annotations

import logging
from typing import Any

from .contract_extractor import ContractExtractor
from .pdf_processing_service import PDFProcessingService

logger = logging.getLogger(__name__)


class ContractExtractorManager:
    """Coordinate PDF text extraction and contract parsing."""

    def __init__(self, service: PDFProcessingService | None = None) -> None:
        self.processing_service = service or PDFProcessingService()
        self.contract_extractor = ContractExtractor()

    async def extract_from_pdf(self, file_path: str) -> dict[str, Any]:
        """Extract contract info from a PDF file path."""
        text_result = await self.processing_service.extract_text_from_pdf(file_path)
        if not text_result.get("success"):
            error = text_result.get("error", "PDF text extraction failed")
            logger.warning("Contract extraction failed: %s", error)
            return {"success": False, "error": str(error)}

        text = text_result.get("text", "")
        return self.contract_extractor.extract_contract_info(text)
