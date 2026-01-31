"""
异步 PDF 缓存实现
"""

import asyncio
import hashlib
import json
import logging
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

from ...core.exception_handler import InternalServerError
from .config import get_config

aiofiles: Any | None

try:
    import importlib

    aiofiles = importlib.import_module("aiofiles")
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False
    aiofiles = None

logger = logging.getLogger(__name__)


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
        if self._use_async and aiofiles is not None:
            async with aiofiles.open(file_path, "rb") as f:
                md5 = hashlib.md5(usedforsecurity=False)
                while chunk := await f.read(8192):
                    md5.update(chunk)
                return md5.hexdigest()
        else:
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
                await asyncio.to_thread(cache_file.unlink)
                self._evictions += 1
                logger.debug(f"Cache expired (age: {age_seconds}s)")
                return None

            # 读取缓存
            if self._use_async and aiofiles is not None:
                async with aiofiles.open(cache_file, "r", encoding="utf-8") as f:
                    content = await f.read()
            else:
                content = await asyncio.to_thread(
                    cache_file.read_text, encoding="utf-8"
                )

            cached_data = cast(dict[str, Any], json.loads(content))

            # 更新访问时间
            await asyncio.to_thread(os.utime, cache_file, None)

            self._hits += 1
            logger.info(f"Cache HIT (age: {age_seconds:.0f}s)")
            return cached_data

        except json.JSONDecodeError:
            logger.error(
                f"Async cache file corrupted: {cache_file}",
                exc_info=True,
                extra={"error_id": "ASYNC_CACHE_CORRUPTED", "file_hash": file_hash},
            )
            # 删除损坏的缓存
            try:
                await asyncio.to_thread(cache_file.unlink)
            except Exception:  # nosec B110
                logger.warning(
                    "Failed to delete corrupted async cache file",
                    exc_info=True,
                    extra={
                        "error_id": "ASYNC_CACHE_DELETE_FAILED",
                        "file_hash": file_hash,
                    },
                )
            self._evictions += 1
            self._misses += 1
            return None
        except (PermissionError, OSError) as e:
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
            logger.error(
                f"Async cache system failure: {e}",
                exc_info=True,
                extra={
                    "error_id": "ASYNC_CACHE_SYSTEM_FAILURE",
                    "file_hash": file_hash,
                },
            )
            raise InternalServerError(
                message="Async cache system malfunction",
                original_error=e,
                details={
                    "error_id": "ASYNC_CACHE_SYSTEM_FAILURE",
                    "file_hash": file_hash,
                },
            ) from e

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

                cached_data = {
                    "file_hash": file_hash,
                    "cached_at": datetime.now().isoformat(),
                    "expires_at": (
                        datetime.now() + timedelta(seconds=ttl or self.ttl_seconds)
                    ).isoformat(),
                    "data": data,
                }

                content = json.dumps(cached_data, ensure_ascii=False, indent=2)

                if self._use_async and aiofiles is not None:
                    async with aiofiles.open(cache_file, "w", encoding="utf-8") as f:
                        await f.write(content)
                else:
                    await asyncio.to_thread(
                        cache_file.write_text, content, encoding="utf-8"
                    )

                logger.info(f"Cached data for hash {file_hash[:8]}...")
                return True

        except OSError as e:
            if "No space left" in str(e) or getattr(e, "errno", None) == 28:
                logger.error(
                    "Disk full - cannot cache async",
                    extra={
                        "error_id": "ASYNC_CACHE_DISK_FULL",
                        "file_hash": file_hash[:8],
                    },
                )
                raise InternalServerError(
                    message="Disk space exhausted, cannot cache results",
                    original_error=e,
                    details={
                        "error_id": "ASYNC_CACHE_DISK_FULL",
                        "file_hash": file_hash,
                    },
                ) from e
            elif "Permission denied" in str(e) or getattr(e, "errno", None) == 13:
                logger.error(
                    "Permission denied writing async cache",
                    extra={
                        "error_id": "ASYNC_CACHE_PERMISSION_ERROR",
                        "file_hash": file_hash[:8],
                    },
                )
                raise InternalServerError(
                    message="Cache directory not writable",
                    original_error=e,
                    details={
                        "error_id": "ASYNC_CACHE_PERMISSION_ERROR",
                        "file_hash": file_hash,
                    },
                ) from e
            else:
                logger.error(
                    f"File system error caching async: {e}",
                    exc_info=True,
                    extra={"error_id": "ASYNC_CACHE_WRITE_ERROR"},
                )
                raise
        except (TypeError, ValueError) as e:
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
            raise InternalServerError(
                message="Unexpected async cache write error",
                original_error=e,
                details={
                    "error_id": "ASYNC_CACHE_WRITE_FAILURE",
                    "file_hash": file_hash,
                },
            ) from e

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
