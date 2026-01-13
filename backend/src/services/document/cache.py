#!/usr/bin/env python3
"""
PDF 处理缓存层
基于文件 hash 的智能缓存，避免重复处理相同文件
"""

import asyncio
import hashlib
import json
import logging
import os
import tempfile
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .config import get_config

try:
    import aiofiles  # type: ignore[import-untyped]

    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False
    aiofiles = None

logger = logging.getLogger(__name__)


class PDFCache:
    """
    PDF 处理结果缓存

    基于 MD5 文件哈希的缓存系统，避免重复处理相同的 PDF 文件
    """

    def __init__(self, cache_dir: str | None = None, ttl_seconds: int = 3600):
        """
        初始化缓存

        Args:
            cache_dir: 缓存目录路径（默认从配置读取）
            ttl_seconds: 缓存过期时间（秒）
        """
        config = get_config()
        self.cache_dir = Path(
            cache_dir
            or config.extraction.cache_dir
            or Path(tempfile.gettempdir()) / "pdf_cache"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds

        # 缓存统计
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get_file_hash(self, file_path: str) -> str:
        """
        计算文件的 MD5 哈希

        Args:
            file_path: 文件路径

        Returns:
            str: MD5 哈希值（十六进制）
        """
        md5 = hashlib.md5(usedforsecurity=False)
        with open(file_path, "rb") as f:
            # 分块读取以支持大文件
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)
        return md5.hexdigest()

    def get(self, file_path: str) -> dict[str, Any] | None:
        """
        获取缓存的提取结果

        Args:
            file_path: 文件路径

        Returns:
            缓存的结果，如果不存在或已过期则返回 None

        Raises:
            OSError, PermissionError: 文件系统错误会重新抛出
            RuntimeError: 缓存系统故障时抛出（需要立即处理的严重问题）

        Note:
            - 缓存未命中（文件不存在、已过期）返回 None
            - JSON 损坏会删除缓存文件并返回 None
            - 文件系统错误（权限、磁盘故障）会抛出异常
            - 其他严重错误会抛出 RuntimeError
        """
        try:
            hash_key = self.get_file_hash(file_path)
            cache_file = self.cache_dir / f"{hash_key}.json"

            if not cache_file.exists():
                self._misses += 1
                return None

            # 检查缓存是否过期
            file_stat = cache_file.stat()
            age_seconds = time.time() - file_stat.st_mtime

            if age_seconds > self.ttl_seconds:
                # 缓存过期，删除
                cache_file.unlink()
                self._evictions += 1
                logger.debug(f"Cache expired for {file_path} (age: {age_seconds}s)")
                return None

            # 读取缓存，单独处理 JSON 解析错误
            try:
                with open(cache_file, encoding="utf-8") as f:
                    cached_data = json.load(f)
            except json.JSONDecodeError:
                logger.error(
                    f"Cache file corrupted: {cache_file}",
                    exc_info=True,
                    extra={"error_id": "CACHE_CORRUPTED", "file_path": str(cache_file)},
                )
                # 删除损坏的缓存文件
                try:
                    cache_file.unlink()
                except Exception:
                    pass
                self._evictions += 1
                self._misses += 1
                return None

            # 更新访问时间（LRU策略）
            try:
                os.utime(cache_file, None)
            except OSError:
                # 访问时间更新失败不影响缓存命中
                pass

            self._hits += 1
            logger.info(f"Cache HIT for {file_path} (age: {age_seconds:.0f}s)")
            return cached_data

        except (PermissionError, OSError) as e:
            logger.error(
                f"Cache file system error for {file_path}: {e}",
                exc_info=True,
                extra={"error_id": "CACHE_FILESYSTEM_ERROR", "file_path": file_path},
            )
            # 文件系统错误必须重新抛出 - 这些是需要立即关注的严重问题
            raise
        except Exception as e:
            # 未预期的错误不应该被静默转换为缓存未命中
            # 这可能表示缓存系统出现严重问题
            logger.error(
                f"Cache system failure for {file_path}: {e}",
                exc_info=True,
                extra={"error_id": "CACHE_SYSTEM_FAILURE", "file_path": file_path},
            )
            # 抛出运行时错误而不是静默返回 None
            raise RuntimeError(f"Cache system malfunction: {e}") from e

    def set(self, file_path: str, result: dict[str, Any]) -> bool:
        """
        设置缓存结果

        Args:
            file_path: 文件路径
            result: 要缓存的结果

        Returns:
            bool: 是否成功缓存

        Raises:
            OSError: 磁盘空间不足、权限错误或其他文件系统错误
            RuntimeError: 磁盘满或缓存目录不可写时抛出

        Note:
            - 序列化错误（TypeError, ValueError）返回 False，不抛出异常
            - 文件系统错误（磁盘满、权限）会抛出异常，需要立即处理
            - 其他未预期错误会抛出异常
        """
        try:
            hash_key = self.get_file_hash(file_path)
            cache_file = self.cache_dir / f"{hash_key}.json"

            # 添加元数据
            cached_data = {
                "file_path": file_path,
                "file_hash": hash_key,
                "cached_at": datetime.now().isoformat(),
                "result": result,
            }

            # 写入缓存
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cached_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Cached result for {file_path}")
            return True

        except OSError as e:
            # 磁盘空间不足
            if "No space left" in str(e) or getattr(e, "errno", None) == 28:
                logger.error(
                    f"Disk full - cannot cache {file_path}",
                    extra={"error_id": "CACHE_DISK_FULL", "file_path": file_path},
                )
                raise RuntimeError("Disk space exhausted, cannot cache results") from e
            # 权限错误
            elif "Permission denied" in str(e) or getattr(e, "errno", None) == 13:
                logger.error(
                    f"Permission denied writing cache for {file_path}",
                    extra={
                        "error_id": "CACHE_PERMISSION_ERROR",
                        "file_path": file_path,
                    },
                )
                raise RuntimeError("Cache directory not writable") from e
            else:
                # 其他文件系统错误
                logger.error(
                    f"File system error caching {file_path}: {e}",
                    exc_info=True,
                    extra={"error_id": "CACHE_WRITE_ERROR"},
                )
                raise
        except (TypeError, ValueError) as e:
            # 序列化错误 - 数据无法转换为 JSON
            logger.error(
                f"Cannot serialize result for caching {file_path}: {e}",
                extra={"error_id": "CACHE_SERIALIZATION_ERROR", "file_path": file_path},
            )
            # 序列化错误可以继续（返回 False），因为是数据问题而非系统问题
            return False
        except Exception as e:
            # 其他未预期错误应该抛出
            logger.error(
                f"Unexpected cache write error for {file_path}: {e}",
                exc_info=True,
                extra={"error_id": "CACHE_WRITE_FAILURE"},
            )
            raise

    def invalidate(self, file_path: str) -> bool:
        """
        使特定文件的缓存失效

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否成功删除
        """
        try:
            hash_key = self.get_file_hash(file_path)
            cache_file = self.cache_dir / f"{hash_key}.json"

            if cache_file.exists():
                cache_file.unlink()
                logger.info(f"Invalidated cache for {file_path}")
                return True

            return False

        except Exception as e:
            logger.warning(f"Failed to invalidate cache for {file_path}: {e}")
            return False

    def clear(self, older_than_seconds: int | None = None) -> int:
        """
        清理缓存

        Args:
            older_than_seconds: 只删除超过此秒数的缓存（None 表示全部）

        Returns:
            int: 删除的缓存文件数量
        """
        try:
            count = 0
            current_time = time.time()

            for cache_file in self.cache_dir.glob("*.json"):
                if older_than_seconds is None:
                    # 删除所有
                    cache_file.unlink()
                    count += 1
                else:
                    # 只删除过期的
                    age_seconds = current_time - cache_file.stat().st_mtime
                    if age_seconds > older_than_seconds:
                        cache_file.unlink()
                        count += 1
                        self._evictions += 1

            logger.info(f"Cleared {count} cache files")
            return count

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0

    def get_stats(self) -> dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            缓存统计数据
        """
        total_files = len(list[Any](self.cache_dir.glob("*.json")))
        hit_rate = (
            self._hits / (self._hits + self._misses)
            if (self._hits + self._misses) > 0
            else 0
        )

        return {
            "total_cached_files": total_files,
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "hit_rate": round(hit_rate, 2),
            "cache_dir": str(self.cache_dir),
            "ttl_seconds": self.ttl_seconds,
        }

    def cleanup_expired(self) -> int:
        """
        清理过期的缓存文件

        Returns:
            int: 删除的文件数量
        """
        return self.clear(older_than_seconds=self.ttl_seconds)


# ============================================================================
# 异步缓存系统
# ============================================================================


class AsyncDocumentCache:
    """
    异步文档缓存系统

    使用异步文件操作避免阻塞事件循环
    如果 aiofiles 不可用，自动回退到同步操作
    """

    def __init__(
        self,
        cache_dir: str | None = None,
        ttl_seconds: int = 3600,
        use_async: bool = True,
    ):
        """
        初始化异步缓存

        Args:
            cache_dir: 缓存目录路径
            ttl_seconds: 缓存过期时间（秒）
            use_async: 是否使用异步操作（False 时强制使用同步）
        """
        config = get_config()
        self.cache_dir = Path(
            cache_dir
            or config.extraction.cache_dir
            or Path(tempfile.gettempdir()) / "pdf_cache"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self._use_async = use_async and AIOFILES_AVAILABLE
        self._lock = asyncio.Lock()

        # 缓存统计
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        if not self._use_async and use_async:
            logger.warning(
                "aiofiles not available, falling back to synchronous file operations"
            )

    async def compute_file_hash(self, file_path: str) -> str:
        """
        异步计算文件 MD5 哈希

        Args:
            file_path: 文件路径

        Returns:
            str: MD5 哈希值
        """
        if self._use_async:
            async with aiofiles.open(file_path, "rb") as f:
                md5 = hashlib.md5(usedforsecurity=False)
                while chunk := await f.read(8192):
                    md5.update(chunk)
                return md5.hexdigest()
        else:
            # 回退到同步操作
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._sync_compute_hash, file_path)

    def _sync_compute_hash(self, file_path: str) -> str:
        """同步计算文件哈希（用于回退）"""
        md5 = hashlib.md5(usedforsecurity=False)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5.update(chunk)
        return md5.hexdigest()

    async def get(self, file_hash: str) -> dict[str, Any] | None:
        """
        异步获取缓存

        Args:
            file_hash: 文件哈希值

        Returns:
            缓存数据，不存在或过期则返回 None
        """
        cache_file = self.cache_dir / f"{file_hash}.json"

        if not cache_file.exists():
            self._misses += 1
            return None

        try:
            # 检查是否过期
            file_stat = await asyncio.to_thread(cache_file.stat)
            age_seconds = time.time() - file_stat.st_mtime

            if age_seconds > self.ttl_seconds:
                # 缓存过期
                await asyncio.to_thread(cache_file.unlink)
                self._evictions += 1
                logger.debug(f"Cache expired (age: {age_seconds}s)")
                return None

            # 读取缓存
            if self._use_async:
                async with aiofiles.open(cache_file, "r", encoding="utf-8") as f:
                    content = await f.read()
            else:
                content = await asyncio.to_thread(
                    cache_file.read_text, encoding="utf-8"
                )

            cached_data = json.loads(content)

            # 更新访问时间
            await asyncio.to_thread(os.utime, cache_file, None)

            self._hits += 1
            logger.info(f"Cache HIT (age: {age_seconds:.0f}s)")
            return cached_data

        except json.JSONDecodeError:
            # JSON 解析错误 - 缓存文件损坏
            logger.error(
                f"Async cache file corrupted: {cache_file}",
                exc_info=True,
                extra={"error_id": "ASYNC_CACHE_CORRUPTED", "file_hash": file_hash},
            )
            # 删除损坏的缓存
            try:
                await asyncio.to_thread(cache_file.unlink)
            except Exception:
                pass
            self._evictions += 1
            self._misses += 1
            return None
        except (PermissionError, OSError) as e:
            # 文件系统错误必须抛出
            logger.error(
                f"Async cache file system error: {e}",
                exc_info=True,
                extra={
                    "error_id": "ASYNC_CACHE_FILESYSTEM_ERROR",
                    "file_hash": file_hash,
                },
            )
            raise
        except Exception as e:
            # 其他严重错误（事件循环问题、内存错误等）
            logger.error(
                f"Async cache system failure: {e}",
                exc_info=True,
                extra={
                    "error_id": "ASYNC_CACHE_SYSTEM_FAILURE",
                    "file_hash": file_hash,
                },
            )
            raise RuntimeError(f"Async cache system malfunction: {e}") from e

    async def set(
        self, file_hash: str, data: dict[str, Any], ttl: int | None = None
    ) -> bool:
        """
        异步设置缓存

        Args:
            file_hash: 文件哈希值
            data: 要缓存的数据
            ttl: 过期时间（秒），默认使用实例的 ttl_seconds

        Returns:
            bool: 是否成功
        """
        try:
            async with self._lock:
                cache_file = self.cache_dir / f"{file_hash}.json"

                # 添加元数据
                cached_data = {
                    "file_hash": file_hash,
                    "cached_at": datetime.now().isoformat(),
                    "expires_at": (
                        datetime.now() + timedelta(seconds=ttl or self.ttl_seconds)
                    ).isoformat(),
                    "data": data,
                }

                content = json.dumps(cached_data, ensure_ascii=False, indent=2)

                if self._use_async:
                    async with aiofiles.open(cache_file, "w", encoding="utf-8") as f:
                        await f.write(content)
                else:
                    await asyncio.to_thread(
                        cache_file.write_text, content, encoding="utf-8"
                    )

                logger.info(f"Cached data for hash {file_hash[:8]}...")
                return True

        except OSError as e:
            # 磁盘空间不足
            if "No space left" in str(e) or getattr(e, "errno", None) == 28:
                logger.error(
                    "Disk full - cannot cache async",
                    extra={
                        "error_id": "ASYNC_CACHE_DISK_FULL",
                        "file_hash": file_hash[:8],
                    },
                )
                raise RuntimeError("Disk space exhausted, cannot cache results") from e
            # 权限错误
            elif "Permission denied" in str(e) or getattr(e, "errno", None) == 13:
                logger.error(
                    "Permission denied writing async cache",
                    extra={
                        "error_id": "ASYNC_CACHE_PERMISSION_ERROR",
                        "file_hash": file_hash[:8],
                    },
                )
                raise RuntimeError("Cache directory not writable") from e
            else:
                logger.error(
                    f"File system error caching async: {e}",
                    exc_info=True,
                    extra={"error_id": "ASYNC_CACHE_WRITE_ERROR"},
                )
                raise
        except (TypeError, ValueError) as e:
            # 序列化错误
            logger.error(
                f"Cannot serialize async cache data: {e}",
                extra={
                    "error_id": "ASYNC_CACHE_SERIALIZATION_ERROR",
                    "file_hash": file_hash[:8],
                },
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected async cache write error: {e}",
                exc_info=True,
                extra={"error_id": "ASYNC_CACHE_WRITE_FAILURE"},
            )
            raise

    async def invalidate(self, file_hash: str) -> bool:
        """
        使缓存失效

        Args:
            file_hash: 文件哈希值

        Returns:
            bool: 是否成功删除
        """
        try:
            cache_file = self.cache_dir / f"{file_hash}.json"
            if cache_file.exists():
                await asyncio.to_thread(cache_file.unlink)
                logger.info(f"Invalidated cache for hash {file_hash[:8]}...")
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {e}")
            return False

    async def clear(self, older_than_seconds: int | None = None) -> int:
        """
        清理缓存

        Args:
            older_than_seconds: 只删除超过此秒数的缓存

        Returns:
            int: 删除的缓存文件数量
        """
        try:
            count = 0
            current_time = time.time()

            for cache_file in self.cache_dir.glob("*.json"):
                if older_than_seconds is None:
                    await asyncio.to_thread(cache_file.unlink)
                    count += 1
                else:
                    file_stat = await asyncio.to_thread(cache_file.stat)
                    age_seconds = current_time - file_stat.st_mtime
                    if age_seconds > older_than_seconds:
                        await asyncio.to_thread(cache_file.unlink)
                        count += 1
                        self._evictions += 1

            logger.info(f"Cleared {count} cache files")
            return count

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0

    async def get_stats(self) -> dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            缓存统计数据
        """
        total_files = len(list[Any](self.cache_dir.glob("*.json")))
        hit_rate = (
            self._hits / (self._hits + self._misses)
            if (self._hits + self._misses) > 0
            else 0
        )

        return {
            "total_cached_files": total_files,
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "hit_rate": round(hit_rate, 2),
            "cache_dir": str(self.cache_dir),
            "ttl_seconds": self.ttl_seconds,
            "async_enabled": self._use_async,
        }


class CachedExtractor:
    """
    带缓存的提取器装饰器

    为任何提取函数添加缓存功能

    Example:
        @CachedExtractor()
        async def extract_contract(pdf_path: str):
            return await llm_service.extract(pdf_path)
    """

    def __init__(
        self,
        cache: PDFCache | None = None,
        cache_key_func: Callable[..., str] | None = None,
    ) -> None:
        """
        初始化装饰器

        Args:
            cache: 缓存实例（默认创建新实例）
            cache_key_func: 自定义缓存键函数（默认使用文件路径）
        """
        self.cache = cache or PDFCache()
        self.cache_key_func = cache_key_func

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """
        装饰器函数

        Args:
            func: 要装饰的异步函数

        Returns:
            包装后的函数
        """

        async def wrapper(file_path: str, *args, **kwargs):
            # 检查缓存
            cache_key = (
                self.cache_key_func(file_path) if self.cache_key_func else file_path
            )

            # 尝试从缓存获取
            if isinstance(cache_key, str):
                cached = self.cache.get(cache_key)
            else:
                cached = None

            if cached is not None:
                logger.info(f"Using cached result for {file_path}")
                return cached["result"]

            # 缓存未命中，执行函数
            logger.info(f"Cache miss for {file_path}, executing extraction")
            result = await func(file_path, *args, **kwargs)

            # 保存到缓存
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
        """
        初始化高级缓存

        Args:
            base_cache: 基础缓存实例
        """
        self.cache = base_cache or PDFCache()
        self._conditional_caches: dict[str, Callable[[dict[str, Any]], bool]] = {}

    def register_conditional_cache(
        self,
        name: str,
        condition_func: Callable[[dict[str, Any]], bool],
    ) -> None:
        """
        注册条件性缓存

        只有满足特定条件时才使用缓存

        Args:
            name: 缓存名称
            condition_func: 条件函数，返回 bool

        Example:
            cache.register_conditional_cache(
                "high_confidence_only",
                lambda result: result.get("confidence", 0) > 0.8
            )
        """
        self._conditional_caches[name] = condition_func

    def get(
        self, file_path: str, condition: str | None = None
    ) -> dict[str, Any] | None:
        """
        获取缓存，支持条件过滤

        Args:
            file_path: 文件路径
            condition: 条件缓存名称

        Returns:
            缓存结果
        """
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
        """
        缓存预热

        批量处理文件并缓存结果

        Args:
            file_paths: 要预处理的文件列表
            extraction_func: 提取函数

        Returns:
            预热统计
        """
        logger.info(f"Warming up cache with {len(file_paths)} files")

        success_count = 0
        failed_count = 0
        skipped_count = 0

        for file_path in file_paths:
            # 检查是否已缓存
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


# ============================================================================
# 全局缓存实例
# ============================================================================

_default_cache: PDFCache | None = None


def get_cache() -> PDFCache:
    """
    获取全局缓存实例（单例）

    Returns:
        PDFCache: 缓存实例
    """
    global _default_cache
    if _default_cache is None:
        _default_cache = PDFCache()
    return _default_cache


def clear_all_caches() -> int:
    """
    清理所有缓存

    Returns:
        int: 删除的文件数量
    """
    global _default_cache
    if _default_cache:
        return _default_cache.clear()
    return 0


# ============================================================================
# 便捷装饰器
# ============================================================================


def cached_extraction(ttl_seconds: int = 3600) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    提取结果缓存装饰器

    Args:
        ttl_seconds: 缓存过期时间（秒）

    Example:
        @cached_extraction(ttl_seconds=1800)
        async def extract_contract(pdf_path: str):
            return await llm_extractor.extract_smart(pdf_path)
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapper(file_path: str, *args: Any, **kwargs: Any) -> Any:
            cache = PDFCache(ttl_seconds=ttl_seconds)

            # 检查缓存
            cached = cache.get(file_path)
            if cached is not None:
                return cached["result"]

            # 执行提取
            result = await func(file_path, *args, **kwargs)

            # 保存到缓存
            if result.get("success"):
                cache.set(file_path, result)

            return result

        return wrapper

    return decorator


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":  # pragma: no cover
    # 基础缓存使用
    cache = PDFCache()

    # 模拟缓存操作
    print("=== PDF Cache Example ===")
    print(f"Cache dir: {cache.cache_dir}")
    print(f"Stats: {cache.get_stats()}")

    # 使用装饰器
    @cached_extraction(ttl_seconds=1800)
    async def mock_extract(file_path: str):
        return {"success": True, "data": "test"}
