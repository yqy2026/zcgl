"""
提取缓存包装器
"""

import logging
from collections.abc import Callable
from typing import Any

from .cache_sync import PDFCache

logger = logging.getLogger(__name__)


class CachedExtractor:
    """
    带缓存的提取器装饰器

    为任何提取函数添加缓存功能
    """

    def __init__(
        self,
        cache: PDFCache | None = None,
        cache_key_func: Callable[..., str] | None = None,
    ) -> None:
        self.cache = cache or PDFCache()
        self.cache_key_func = cache_key_func

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapper(file_path: str, *args: Any, **kwargs: Any) -> Any:
            cache_key = (
                self.cache_key_func(file_path) if self.cache_key_func else file_path
            )

            if isinstance(cache_key, str):
                cached = self.cache.get(cache_key)
            else:
                cached = None

            if cached is not None:
                logger.info(f"Using cached result for {file_path}")
                return cached["result"]

            logger.info(f"Cache miss for {file_path}, executing extraction")
            result = await func(file_path, *args, **kwargs)

            if isinstance(cache_key, str):
                self.cache.set(cache_key, result)

            return result

        return wrapper


class ExtractionCache:
    """
    高级提取缓存

    支持更复杂的缓存策略，包括：
    - 基于内容的缓存（不只是文件哈希）
    - 条件性缓存
    - 缓存预热
    """

    def __init__(self, base_cache: PDFCache | None = None) -> None:
        self.cache = base_cache or PDFCache()
        self._conditional_caches: dict[str, Callable[[dict[str, Any]], bool]] = {}

    def register_conditional_cache(
        self,
        name: str,
        condition_func: Callable[[dict[str, Any]], bool],
    ) -> None:
        self._conditional_caches[name] = condition_func

    def get(
        self, file_path: str, condition: str | None = None
    ) -> dict[str, Any] | None:
        cached = self.cache.get(file_path)

        if cached and condition:
            condition_func = self._conditional_caches.get(condition)
            if condition_func and not condition_func(cached["result"]):
                logger.info(f"Cached result doesn't meet condition '{condition}'")
                return None

        return cached

    def warm_up(
        self,
        file_paths: list[str],
        extraction_func: Callable[[str], dict[str, Any]],
    ) -> dict[str, Any]:
        logger.info(f"Warming up cache with {len(file_paths)} files")

        success_count = 0
        failed_count = 0
        skipped_count = 0

        for file_path in file_paths:
            if self.cache.get(file_path) is not None:
                skipped_count += 1
                continue

            try:
                result = extraction_func(file_path)
                self.cache.set(file_path, result)
                success_count += 1
            except Exception as e:
                logger.warning(f"Failed to warm up cache for {file_path}: {e}")
                failed_count += 1

        return {
            "total": len(file_paths),
            "success": success_count,
            "failed": failed_count,
            "skipped": skipped_count,
        }
