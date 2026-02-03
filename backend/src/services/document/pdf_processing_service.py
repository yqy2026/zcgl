"""
PDF processing service (text extraction).

This module provides a lightweight PDF text extraction service used by
the PDF upload endpoints and optional service wiring. It intentionally
keeps dependencies optional and degrades gracefully when unavailable.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Optional PyMuPDF dependency
try:  # pragma: no cover - exercised when dependency is installed
    import fitz  # type: ignore

    PYMUPDF_AVAILABLE = True
except ImportError:  # pragma: no cover - fallback for missing dependency
    fitz = None  # type: ignore
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not installed. PDF text extraction will be unavailable.")


class PDFProcessingService:
    """Basic PDF processing service for text extraction."""

    def __init__(self, *, max_pages: int | None = None) -> None:
        self.max_pages = max_pages

    async def extract_text_from_pdf(
        self, pdf_path: str | Path, *, max_pages: int | None = None
    ) -> dict[str, Any]:
        """Extract text from a PDF file using PyMuPDF if available."""
        path = Path(pdf_path)
        if not path.exists():
            return {"success": False, "error": f"PDF not found: {path}"}

        if not PYMUPDF_AVAILABLE:
            return {
                "success": False,
                "error": "PyMuPDF not installed; text extraction unavailable.",
            }

        page_limit = max_pages if max_pages is not None else self.max_pages

        try:
            with fitz.open(str(path)) as doc:  # type: ignore[attr-defined]
                page_count = len(doc)
                if page_limit is None:
                    page_limit = page_count
                page_limit = min(page_count, page_limit)

                texts: list[str] = []
                for page_index in range(page_limit):
                    page = doc[page_index]
                    texts.append(page.get_text("text"))

            text = "\n".join(texts).strip()
            return {
                "success": True,
                "text": text,
                "page_count": page_count,
                "extracted_pages": page_limit,
            }
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("PDF text extraction failed: %s", exc, exc_info=True)
            return {"success": False, "error": str(exc)}

    async def process(self, file_path: str) -> dict[str, object]:
        """
        Compatibility hook for older Protocol usage.

        This proxies to extract_text_from_pdf to keep interfaces aligned.
        """
        result = await self.extract_text_from_pdf(file_path)
        return dict(result)


# Default singleton for dependency injection
pdf_processing_service = PDFProcessingService()
