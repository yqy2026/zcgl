from typing import Any

"""
Caching wrapper for OCR services.

Provides an in-memory, TTL-based cache for document-level OCR results
without changing consumer code. It wraps any IOCRService-compatible
implementation and caches results keyed by input parameters.

This is intentionally lightweight and safe by default. Page-level calls
are passed through to the delegate to avoid complexity with transient
page objects; most consumers use process_pdf_document which benefits from
the cache.
"""

import time
from collections import OrderedDict

from ...services.interfaces.ocr_service import IOCRService


class CachingOCRService(IOCRService):  # type: ignore[misc]
    def __init__(
        self,
        delegate: IOCRService,
        ttl_seconds: int = 1800,
        max_entries: int = 256,
    ) -> None:
        self._delegate = delegate
        self._ttl_seconds = max(1, int(ttl_seconds))
        self._max_entries = max(1, int(max_entries))
        self._doc_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._page_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()

        # Marker to prevent double-wrapping via provider logic
        self._is_caching_wrapper = True

    def _now(self) -> float:
        return time.monotonic()

    def _doc_key(
        self,
        pdf_path: str,
        max_pages: int,
        max_concurrency: int | None,
        use_preprocessing: bool,
    ) -> str:
        return f"{pdf_path}|pages={max_pages}|conc={max_concurrency}|pre={use_preprocessing}"

    def _is_valid(self, entry: dict[str, Any]) -> bool:
        return entry.get("expires_at", 0) > self._now()

    def _evict_lru(self, cache: OrderedDict[str, dict[str, Any]]) -> None:
        while len(cache) > self._max_entries:
            # pop oldest
            cache.popitem(last=False)

    async def process_pdf_document(
        self,
        pdf_path: str,
        max_pages: int = 10,
        max_concurrency: int | None = None,
        use_preprocessing: bool = True,
    ) -> dict[str, Any]:
        key = self._doc_key(pdf_path, max_pages, max_concurrency, use_preprocessing)

        entry = self._doc_cache.get(key)
        if entry and self._is_valid(entry):
            # Move to end to mark as most recently used
            self._doc_cache.move_to_end(key)
            return entry["value"]

        result = await self._delegate.process_pdf_document(
            pdf_path=pdf_path,
            max_pages=max_pages,
            max_concurrency=max_concurrency,
            use_preprocessing=use_preprocessing,
        )

        # Only cache successful results to avoid persisting errors
        if result and result.get("success", False):
            self._doc_cache[key] = {
                "value": result,
                "expires_at": self._now() + self._ttl_seconds,
            }
            self._evict_lru(self._doc_cache)

        return result

    async def process_pdf_page(
        self, page: Any, page_num: int, use_preprocessing: bool = True
    ) -> Any:
        # Page-level caching is deliberately bypassed to avoid complexity
        # with transient page objects; delegate handles page processing.
        return await self._delegate.process_pdf_page(
            page, page_num, use_preprocessing=use_preprocessing
        )

    def get_performance_report(self) -> dict[str, Any]:
        report = self._delegate.get_performance_report()
        try:
            report["cache_stats"] = {
                "doc_entries": len(self._doc_cache),
                "page_entries": len(self._page_cache),
                "ttl_seconds": self._ttl_seconds,
                "max_entries": self._max_entries,
            }
        except Exception:
            # metrics enrichment is optional; ignore failures
            pass
        return report

    def clear_cache(self) -> None:
        self._doc_cache.clear()
        self._page_cache.clear()
