"""
同步 PDF 缓存实现
"""

import hashlib
import json
import logging
import os
import tempfile
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from ...core.exception_handler import InternalServerError
from .config import get_config

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
            InternalServerError: 缓存系统故障时抛出（需要立即处理的严重问题）
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
                    cached_data = cast(dict[str, Any], json.load(f))
            except json.JSONDecodeError:
                logger.error(
                    f"Cache file corrupted: {cache_file}",
                    exc_info=True,
                    extra={"error_id": "CACHE_CORRUPTED", "file_path": str(cache_file)},
                )
                # 删除损坏的缓存文件
                try:
                    cache_file.unlink()
                except Exception:  # nosec B110  # Intentional: continue if cache file deletion fails
                    logger.warning(
                        "Failed to delete corrupted cache file",
                        exc_info=True,
                        extra={
                            "error_id": "CACHE_DELETE_FAILED",
                            "file_path": str(cache_file),
                        },
                    )
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
            raise
        except Exception as e:
            logger.error(
                f"Cache system failure for {file_path}: {e}",
                exc_info=True,
                extra={"error_id": "CACHE_SYSTEM_FAILURE", "file_path": file_path},
            )
            raise InternalServerError(
                message="Cache system malfunction",
                original_error=e,
                details={
                    "error_id": "CACHE_SYSTEM_FAILURE",
                    "file_path": file_path,
                },
            ) from e

    def set(self, file_path: str, result: dict[str, Any]) -> bool:
        """
        设置缓存结果

        Args:
            file_path: 文件路径
            result: 要缓存的结果

        Returns:
            bool: 是否成功缓存
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
            if "No space left" in str(e) or getattr(e, "errno", None) == 28:
                logger.error(
                    f"Disk full - cannot cache {file_path}",
                    extra={"error_id": "CACHE_DISK_FULL", "file_path": file_path},
                )
                raise InternalServerError(
                    message="Disk space exhausted, cannot cache results",
                    original_error=e,
                    details={
                        "error_id": "CACHE_DISK_FULL",
                        "file_path": file_path,
                    },
                ) from e
            elif "Permission denied" in str(e) or getattr(e, "errno", None) == 13:
                logger.error(
                    f"Permission denied writing cache for {file_path}",
                    extra={
                        "error_id": "CACHE_PERMISSION_ERROR",
                        "file_path": file_path,
                    },
                )
                raise InternalServerError(
                    message="Cache directory not writable",
                    original_error=e,
                    details={
                        "error_id": "CACHE_PERMISSION_ERROR",
                        "file_path": file_path,
                    },
                ) from e
            else:
                logger.error(
                    f"File system error caching {file_path}: {e}",
                    exc_info=True,
                    extra={"error_id": "CACHE_WRITE_ERROR"},
                )
                raise
        except (TypeError, ValueError) as e:
            logger.error(
                f"Cannot serialize result for caching {file_path}: {e}",
                extra={"error_id": "CACHE_SERIALIZATION_ERROR", "file_path": file_path},
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected cache write error for {file_path}: {e}",
                exc_info=True,
                extra={"error_id": "CACHE_WRITE_FAILURE"},
            )
            raise InternalServerError(
                message="Unexpected cache write error",
                original_error=e,
                details={
                    "error_id": "CACHE_WRITE_FAILURE",
                    "file_path": file_path,
                },
            ) from e

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
                    cache_file.unlink()
                    count += 1
                else:
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


def cached_extraction(
    ttl_seconds: int = 3600,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    提取结果缓存装饰器

    Args:
        ttl_seconds: 缓存过期时间（秒）
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
