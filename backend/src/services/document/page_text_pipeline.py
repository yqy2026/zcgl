"""Ordered, page-level text extraction for the new document kernel."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from math import ceil
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Any, Literal, cast

import fitz
import numpy as np
from PIL import Image

from src.constants.document_processing_constants import CONTRACT_MAX_PDF_PAGES

TextSource = Literal["pdf_text", "rapidocr"]

_RAPIDOCR_LOCK = Lock()
logger = logging.getLogger(__name__)


class PagePipelineError(RuntimeError):
    """A terminal document pipeline failure."""


@dataclass(frozen=True)
class PageStageError:
    code: str
    stage: str
    page_number: int


@dataclass(frozen=True)
class OCRLine:
    text: str
    score: float | None = None
    box: tuple[float, ...] | None = None


@dataclass(frozen=True)
class PageText:
    page_number: int
    text_source: TextSource | None
    text_lines: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    ocr_lines: list[OCRLine] = field(default_factory=list)
    error: PageStageError | None = None


@dataclass(frozen=True)
class OrderedPageTextResult:
    pages: list[PageText]


def _normalize_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


class OrderedPageTextPipeline:
    """Extract one canonical text source per PDF or image page."""

    def __init__(
        self,
        ocr_engine: Callable[[np.ndarray[Any, Any]], Any],
        *,
        min_pdf_text_chars: int = 20,
        dpi: int = 200,
        page_timeout_seconds: float = 10,
        document_timeout_seconds: float = 180,
        max_pdf_pages: int = CONTRACT_MAX_PDF_PAGES,
        max_raster_bytes: int = 512 * 1024 * 1024,
        ocr_lock: Lock | None = None,
    ) -> None:
        self.ocr_engine = ocr_engine
        self.min_pdf_text_chars = min_pdf_text_chars
        self.dpi = dpi
        self.page_timeout_seconds = page_timeout_seconds
        self.document_timeout_seconds = document_timeout_seconds
        self.max_pdf_pages = max_pdf_pages
        self.max_raster_bytes = max_raster_bytes
        self._ocr_lock = ocr_lock or Lock()

    def extract_pdf_pages(self, pdf_path: str | Path) -> OrderedPageTextResult:
        path = Path(pdf_path)
        started_at = monotonic()
        try:
            document = fitz.open(path)
        except Exception as exc:
            raise PagePipelineError("pdf_open_failed") from exc

        try:
            if not document.is_pdf or document.needs_pass or document.is_encrypted:
                raise PagePipelineError("pdf_not_processable")
            if document.is_repaired or document.page_count == 0:
                raise PagePipelineError("pdf_not_processable")
            if document.page_count > self.max_pdf_pages:
                raise PagePipelineError("pdf_page_limit")

            pages: list[PageText] = []
            for page_index in range(document.page_count):
                self._check_document_timeout(started_at)
                page = document.load_page(page_index)
                raw_text = page.get_text("text")
                lines = _normalize_lines(raw_text)
                if len("".join(lines)) >= self.min_pdf_text_chars:
                    page_result = PageText(
                        page_number=page_index + 1,
                        text_source="pdf_text",
                        text_lines=lines,
                        evidence=[line[:240] for line in lines[:3]],
                    )
                else:
                    page_result = self._ocr_pdf_page(page, page_index + 1)
                pages.append(page_result)
                self._check_document_timeout(started_at)
            return OrderedPageTextResult(pages=pages)
        finally:
            document.close()

    def extract_image_page(self, image_path: str | Path) -> OrderedPageTextResult:
        try:
            with Image.open(image_path) as image:
                self._check_raster_size(image.width, image.height)
                image.load()
                with image.convert("RGB") as converted:
                    pixels = np.asarray(converted).copy()
        except PagePipelineError:
            raise
        except Exception as exc:
            raise PagePipelineError("image_open_failed") from exc
        return OrderedPageTextResult(pages=[self._ocr_pixels(pixels, 1)])

    def _ocr_pdf_page(self, page: fitz.Page, page_number: int) -> PageText:
        width = ceil(page.rect.width * self.dpi / 72)
        height = ceil(page.rect.height * self.dpi / 72)
        self._check_raster_size(width, height)
        matrix = fitz.Matrix(self.dpi / 72, self.dpi / 72)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        try:
            pixels = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                pixmap.height, pixmap.width, pixmap.n
            )
            return self._ocr_pixels(pixels, page_number)
        finally:
            del pixmap

    def _ocr_pixels(self, pixels: np.ndarray[Any, Any], page_number: int) -> PageText:
        started_at = monotonic()
        try:
            with self._ocr_lock:
                output = self.ocr_engine(pixels)
            if monotonic() - started_at > self.page_timeout_seconds:
                raise TimeoutError
            lines = self._normalize_ocr_output(output)
            return PageText(
                page_number=page_number,
                text_source="rapidocr",
                text_lines=[line.text for line in lines],
                evidence=[line.text[:240] for line in lines[:3]],
                ocr_lines=lines,
            )
        except TimeoutError:
            return PageText(
                page_number=page_number,
                text_source=None,
                error=PageStageError("page_timeout", "rapidocr", page_number),
            )
        except Exception as exc:
            logger.exception(
                "RapidOCR page extraction failed",
                extra={"page_number": page_number, "error_type": type(exc).__name__},
            )
            return PageText(
                page_number=page_number,
                text_source=None,
                error=PageStageError("page_ocr_failed", "rapidocr", page_number),
            )

    def _check_document_timeout(self, started_at: float) -> None:
        if monotonic() - started_at > self.document_timeout_seconds:
            raise PagePipelineError("document_timeout")

    def _check_raster_size(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0 or width * height * 3 > self.max_raster_bytes:
            raise PagePipelineError("page_resource_limit")

    @staticmethod
    def _normalize_ocr_output(output: Any) -> list[OCRLine]:
        if hasattr(output, "txts"):
            texts_value = output.txts
            scores_value = getattr(output, "scores", None)
            boxes_value = getattr(output, "boxes", None)
            texts = list(texts_value) if texts_value is not None else []
            scores = list(scores_value) if scores_value is not None else []
            boxes = list(boxes_value) if boxes_value is not None else []
            return [
                OCRLine(
                    text=str(text),
                    score=float(scores[index]) if index < len(scores) else None,
                    box=tuple(float(value) for value in boxes[index].flatten())
                    if index < len(boxes)
                    else None,
                )
                for index, text in enumerate(texts)
                if str(text).strip()
            ]
        if isinstance(output, str):
            return [OCRLine(text=output)] if output.strip() else []
        if isinstance(output, Sequence):
            return [OCRLine(text=str(item)) for item in output if str(item).strip()]
        return []


def get_ordered_page_text_pipeline(
    *, max_pdf_pages: int = CONTRACT_MAX_PDF_PAGES
) -> OrderedPageTextPipeline:
    """Build the internal pipeline around the startup-prewarmed OCR instance."""
    from src.core.document_processing_runtime import get_rapidocr_engine

    return OrderedPageTextPipeline(
        cast(Callable[[np.ndarray[Any, Any]], Any], get_rapidocr_engine()),
        max_pdf_pages=max_pdf_pages,
        ocr_lock=_RAPIDOCR_LOCK,
    )
