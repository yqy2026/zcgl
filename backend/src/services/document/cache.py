"""
PDF 处理缓存层
拆分为同步/异步/提取缓存模块，当前文件仅做聚合导出。
"""

from .cache_async import AsyncDocumentCache as AsyncDocumentCache
from .cache_extraction import CachedExtractor as CachedExtractor
from .cache_extraction import ExtractionCache as ExtractionCache
from .cache_sync import PDFCache as PDFCache
from .cache_sync import cached_extraction as cached_extraction
from .cache_sync import clear_all_caches as clear_all_caches
from .cache_sync import get_cache as get_cache

__all__ = [
    "PDFCache",
    "AsyncDocumentCache",
    "CachedExtractor",
    "ExtractionCache",
    "get_cache",
    "clear_all_caches",
    "cached_extraction",
]
