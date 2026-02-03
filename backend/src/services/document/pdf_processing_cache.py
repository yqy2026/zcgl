"""
In-memory cache for PDF processing results.
"""

from __future__ import annotations

import time
from typing import Any


class PDFProcessingCache:
    """Simple TTL cache for PDF processing artifacts."""

    def __init__(self, *, ttl_seconds: int = 300, max_entries: int = 256) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._cache: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if not entry:
            return None
        value, timestamp = entry
        if time.time() - timestamp > self.ttl_seconds:
            self._cache.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if len(self._cache) >= self.max_entries:
            # Evict oldest entry
            oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
            self._cache.pop(oldest_key, None)
        self._cache[key] = (value, time.time())

    def clear(self) -> None:
        self._cache.clear()
