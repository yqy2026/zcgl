"""
Parallel PDF processor.

Provides simple concurrency for processing multiple PDF files.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

from .pdf_processing_service import PDFProcessingService


class ParallelPDFProcessor:
    """Process multiple PDFs concurrently with bounded concurrency."""

    def __init__(
        self, service: PDFProcessingService | None = None, *, concurrency: int = 4
    ) -> None:
        self.service = service or PDFProcessingService()
        self.concurrency = max(1, concurrency)

    async def process_files(self, file_paths: Iterable[str]) -> list[dict[str, Any]]:
        semaphore = asyncio.Semaphore(self.concurrency)

        async def _process(path: str) -> dict[str, Any]:
            async with semaphore:
                return await self.service.extract_text_from_pdf(path)

        tasks = [_process(path) for path in file_paths]
        if not tasks:
            return []
        return list(await asyncio.gather(*tasks, return_exceptions=False))
