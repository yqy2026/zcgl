from typing import Any

"""
统一缓存管理器
提供标准化的缓存操作和策略
Version: 1.1 - 添加了get_stats方法
"""

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from hashlib import md5

from .config import settings

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """缓存后端抽象类"""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """获取缓存值"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """设置缓存值"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        pass

    @abstractmethod
    def clear(self, pattern: str | None = None) -> bool:
        """清空缓存"""
        pass

    @abstractmethod
    def get_ttl(self, key: str) -> int | None:
        """获取缓存剩余时间"""
        pass


class MemoryCache(CacheBackend):
    """内存缓存实现"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: dict[str, dict[str, Any]] = {}

    def get(self, key: str) -> Any | None:
        """获取缓存值"""
        if key in self._cache:
            item = self._cache[key]
            if item["expires_at"] > datetime.now(UTC):
                return item["value"]
            else:
                # 过期了，删除
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """设置缓存值"""
        try:
            # 如果缓存已满，删除最旧的条目
            if len(self._cache) >= self.max_size:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]["created_at"])
                del self._cache[oldest_key]

            # 设置缓存项
            expires_at = datetime.now(UTC) + timedelta(seconds=ttl or 300)  # 默认5分钟
            self._cache[key] = {
                "value": value,
                "created_at": datetime.now(UTC),
                "expires_at": expires_at,
            }
            return True
        except Exception as e:  # pragma: no cover
            logger.error(f"设置缓存失败: {e}")  # pragma: no cover
            return False  # pragma: no cover

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        return self.get(key) is not None

    def clear(self, pattern: str | None = None) -> bool:
        """清空缓存"""
        if pattern:
            keys_to_delete = [key for key in self._cache if pattern in key]
            for key in keys_to_delete:
                del self._cache[key]
        else:
            self._cache.clear()
        return True

    def get_ttl(self, key: str) -> int | None:
        """获取缓存剩余时间"""
        if key in self._cache:
            expires_at = self._cache[key]["expires_at"]
            remaining = (expires_at - datetime.now(UTC)).total_seconds()
            return max(0, int(remaining))
        return None


class CacheManager:
    """统一缓存管理器"""

    def __init__(self, backend: CacheBackend | None = None):
        """
        初始化缓存管理器

        Args:
            backend: 缓存后端实现
        """
        self.backend = backend or MemoryCache()
        self.default_ttl = settings.CACHE_TTL if hasattr(settings, "CACHE_TTL") else 300
        self.key_prefix = (
            settings.CACHE_KEY_PREFIX if hasattr(settings, "CACHE_KEY_PREFIX") else "zcgl"
        )

    def _make_key(self, key: str, namespace: str | None = None) -> str:
        """生成缓存键"""
        if namespace:
            return f"{self.key_prefix}:{namespace}:{key}"
        return f"{self.key_prefix}:{key}"

    def _serialize_value(self, value: Any) -> Any:
        """序列化值"""
        if isinstance(value, (dict, list, tuple, set)):
            return json.dumps(value, ensure_ascii=False, default=str)
        elif hasattr(value, "model_dump"):
            return json.dumps(value.model_dump(), ensure_ascii=False, default=str)
        return value

    def _deserialize_value(self, value: Any) -> Any:
        """反序列化值"""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                return value
        return value

    # ==================== 基础缓存操作 ====================

    def get(self, key: str, namespace: str | None = None, default: Any = None) -> Any:
        """
        获取缓存值

        Args:
            key: 缓存键
            namespace: 命名空间
            default: 默认值

        Returns:
            缓存值或默认值
        """
        cache_key = self._make_key(key, namespace)
        value = self.backend.get(cache_key)
        if value is not None:
            return self._deserialize_value(value)
        return default

    def set(
        self, key: str, value: Any, ttl: int | None = None, namespace: str | None = None
    ) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
            namespace: 命名空间

        Returns:
            是否设置成功
        """
        cache_key = self._make_key(key, namespace)
        serialized_value = self._serialize_value(value)
        return self.backend.set(cache_key, serialized_value, ttl or self.default_ttl)

    def delete(self, key: str, namespace: str | None = None) -> bool:
        """
        删除缓存值

        Args:
            key: 缓存键
            namespace: 命名空间

        Returns:
            是否删除成功
        """
        cache_key = self._make_key(key, namespace)
        return self.backend.delete(cache_key)

    def exists(self, key: str, namespace: str | None = None) -> bool:
        """
        检查缓存是否存在

        Args:
            key: 缓存键
            namespace: 命名空间

        Returns:
            是否存在
        """
        cache_key = self._make_key(key, namespace)
        return self.backend.exists(cache_key)

    def clear(self, namespace: str | None = None, pattern: str | None = None) -> bool:
        """
        清空缓存

        Args:
            namespace: 命名空间
            pattern: 模式匹配

        Returns:
            是否清空成功
        """
        if namespace:  # pragma: no cover
            full_pattern = f"{self.key_prefix}:{namespace}:*"  # pragma: no cover
        elif pattern:  # pragma: no cover
            full_pattern = f"{self.key_prefix}:{pattern}"  # pragma: no cover
        else:
            full_pattern = f"{self.key_prefix}:*"

        return self.backend.clear(full_pattern)

    # ==================== 高级缓存操作 ====================

    def get_or_set(
        self,
        key: str,
        factory_func,
        ttl: int | None = None,
        namespace: str | None = None,
        *args,
        **kwargs,
    ) -> Any:
        """
        获取缓存或设置新值

        Args:
            key: 缓存键
            factory_func: 生成值的函数
            ttl: 过期时间
            namespace: 命名空间
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            缓存值或新生成的值
        """
        # 尝试从缓存获取
        value = self.get(key, namespace)
        if value is not None:
            return value

        # 生成新值
        try:
            value = factory_func(*args, **kwargs)
            # 设置缓存
            self.set(key, value, ttl, namespace)
            return value
        except Exception as e:
            logger.error(f"生成缓存值失败: {e}")
            raise

    def get_multi(self, keys: list[str], namespace: str | None = None) -> dict[str, Any]:
        """
        批量获取缓存值

        Args:
            keys: 缓存键列表
            namespace: 命名空间

        Returns:
            键值对字典
        """
        result = {}
        for key in keys:
            value = self.get(key, namespace)
            if value is not None:
                result[key] = value
        return result

    def set_multi(
        self, data: dict[str, Any], ttl: int | None = None, namespace: str | None = None
    ) -> bool:
        """
        批量设置缓存值

        Args:
            data: 键值对字典
            ttl: 过期时间
            namespace: 命名空间

        Returns:
            是否全部设置成功
        """
        success = True
        for key, value in data.items():
            if not self.set(key, value, ttl, namespace):  # pragma: no cover
                success = False  # pragma: no cover
        return success

    def delete_multi(self, keys: list[str], namespace: str | None = None) -> int:
        """
        批量删除缓存值

        Args:
            keys: 缓存键列表
            namespace: 命名空间

        Returns:
            成功删除的数量
        """
        count = 0
        for key in keys:
            if self.delete(key, namespace):
                count += 1
        return count

    def get_stats(self) -> dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            缓存统计字典
        """
        try:
            # 如果后端是MemoryCache，获取详细统计
            if isinstance(self.backend, MemoryCache):
                cache_data = self.backend._cache
                total_items = len(cache_data)

                # 计算过期项数量
                expired_items = 0
                valid_items = 0
                current_time = datetime.now(UTC)

                for item in cache_data.values():
                    if item["expires_at"] <= current_time:
                        expired_items += 1
                    else:
                        valid_items += 1

                # 计算内存使用估算
                total_memory = 0
                for key, item in cache_data.items():
                    total_memory += len(key.encode("utf-8"))  # key大小
                    total_memory += len(str(item["value"]).encode("utf-8"))  # value大小估算

                return {
                    "backend_type": "MemoryCache",
                    "total_items": total_items,
                    "valid_items": valid_items,
                    "expired_items": expired_items,
                    "max_size": self.backend.max_size,
                    "usage_ratio": round(total_items / self.backend.max_size, 2)
                    if self.backend.max_size > 0
                    else 0,
                    "memory_usage_bytes": total_memory,
                    "memory_usage_mb": round(total_memory / (1024 * 1024), 2),
                    "default_ttl": self.default_ttl,
                    "key_prefix": self.key_prefix,
                    "hit_rate": None,  # MemoryCache没有跟踪命中率
                    "created_at": datetime.now(UTC).isoformat(),
                }
            else:  # pragma: no cover
                # 对于其他类型的缓存后端，返回基本信息
                return {  # pragma: no cover
                    "backend_type": type(self.backend).__name__,  # pragma: no cover
                    "total_items": None,  # pragma: no cover
                    "valid_items": None,  # pragma: no cover
                    "expired_items": None,  # pragma: no cover
                    "max_size": None,  # pragma: no cover
                    "usage_ratio": None,  # pragma: no cover
                    "memory_usage_bytes": None,  # pragma: no cover
                    "memory_usage_mb": None,  # pragma: no cover
                    "default_ttl": self.default_ttl,  # pragma: no cover
                    "key_prefix": self.key_prefix,  # pragma: no cover
                    "hit_rate": None,  # pragma: no cover
                    "created_at": datetime.now(UTC).isoformat(),  # pragma: no cover
                }
        except Exception as e:  # pragma: no cover
            logger.error(f"获取缓存统计失败: {e}")  # pragma: no cover
            return {  # pragma: no cover
                "backend_type": type(self.backend).__name__,  # pragma: no cover
                "error": str(e),  # pragma: no cover
                "default_ttl": self.default_ttl,  # pragma: no cover
                "key_prefix": self.key_prefix,  # pragma: no cover
                "created_at": datetime.now(UTC).isoformat(),  # pragma: no cover
            }

    def generate_key(self, prefix: str, **kwargs) -> str:
        """
        生成缓存键，支持多个参数

        Args:
            prefix: 键前缀
            **kwargs: 其他参数，会被排序并序列化

        Returns:
            生成的缓存键
        """
        import hashlib
        import json

        # 过滤掉None值
        filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}

        # 如果没有参数，直接返回前缀
        if not filtered_kwargs:
            return prefix

        # 对参数进行排序以确保一致的键
        sorted_kwargs = dict(sorted(filtered_kwargs.items()))

        # 生成参数的哈希值
        params_str = json.dumps(sorted_kwargs, sort_keys=True, separators=(",", ":"))
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]  # nosec - B324: Cache key, not security

        return f"{prefix}_{params_hash}"

    # ==================== 装饰器 ====================

    def cached(
        self,
        ttl: int | None = None,
        namespace: str | None = None,
        key_generator: Callable | None = None,
    ):
        """
        缓存装饰器

        Args:
            ttl: 过期时间
            namespace: 命名空间
            key_generator: 键生成函数
        """

        def decorator(func):
            def wrapper(*args, **kwargs):
                # 生成缓存键
                if key_generator:  # pragma: no cover
                    cache_key = key_generator(*args, **kwargs)  # pragma: no cover
                else:
                    cache_key = f"{func.__name__}:{_hash_function_call(args, kwargs)}"

                # 尝试从缓存获取
                result = self.get(cache_key, namespace)
                if result is not None:
                    return result

                # 执行函数并缓存结果
                try:
                    result = func(*args, **kwargs)
                    self.set(cache_key, result, ttl, namespace)
                    return result
                except Exception as e:  # pragma: no cover
                    logger.error(f"缓存装饰器执行失败: {e}")  # pragma: no cover
                    raise  # pragma: no cover

            return wrapper

        return decorator

    def cache_invalidate(self, namespace: str | None = None, pattern: str | None = None):
        """
        缓存失效装饰器

        Args:
            namespace: 命名空间
            pattern: 匹配模式
        """

        def decorator(func):
            def wrapper(*args, **kwargs):
                try:
                    result = func(*args, **kwargs)
                    # 执行成功后清除缓存
                    self.clear(namespace, pattern)
                    return result
                except Exception as e:  # pragma: no cover
                    logger.error(f"缓存失效装饰器执行失败: {e}")  # pragma: no cover
                    raise  # pragma: no cover

            return wrapper

        return decorator


def _hash_function_call(args: tuple, kwargs: dict) -> str:
    """哈希函数调用参数"""
    try:
        # 尝试序列化参数
        serializable_args = []
        for arg in args:
            if hasattr(arg, "model_dump"):
                serializable_args.append(arg.model_dump())
            elif isinstance(arg, (str, int, float, bool, type(None))):
                serializable_args.append(arg)
            else:
                serializable_args.append(str(arg))

        serializable_kwargs = {}
        for key, value in kwargs.items():
            if hasattr(value, "model_dump"):  # pragma: no cover
                serializable_kwargs[key] = value.model_dump()  # pragma: no cover
            elif isinstance(value, (str, int, float, bool, type(None))):
                serializable_kwargs[key] = value
            else:  # pragma: no cover
                serializable_kwargs[key] = str(value)  # pragma: no cover

        # 生成哈希
        content = json.dumps(
            {"args": serializable_args, "kwargs": serializable_kwargs},
            sort_keys=True,
            default=str,
        )

        return md5(content.encode()).hexdigest()[:16]  # nosec - B324: Cache key generation  # fmt: skip
    except Exception:  # pragma: no cover
        # 如果序列化失败，使用字符串表示
        content = f"{args}{kwargs}"  # pragma: no cover
        return md5(content.encode()).hexdigest()[:16]  # pragma: no cover  # nosec - B324: Cache key generation  # fmt: skip


# 全局缓存管理器实例
cache_manager = CacheManager()

# 专用缓存实例
analytics_cache = CacheManager(backend=MemoryCache(max_size=500))
# 覆盖默认配置
analytics_cache.default_ttl = 600  # 10分钟缓存
analytics_cache.key_prefix = "analytics"


# 便捷函数
def cached(ttl: int | None = None, namespace: str | None = None):
    """缓存装饰器便捷函数"""
    return cache_manager.cached(ttl=ttl, namespace=namespace)


def cache_invalidate(namespace: str | None = None, pattern: str | None = None):
    """缓存失效装饰器便捷函数"""
    return cache_manager.cache_invalidate(namespace=namespace, pattern=pattern)


def get_cache(key: str, namespace: str | None = None, default: Any = None) -> Any:
    """获取缓存便捷函数"""
    return cache_manager.get(key, namespace, default)


def set_cache(key: str, value: Any, ttl: int | None = None, namespace: str | None = None) -> bool:
    """设置缓存便捷函数"""
    return cache_manager.set(key, value, ttl, namespace)


def delete_cache(key: str, namespace: str | None = None) -> bool:
    """删除缓存便捷函数"""
    return cache_manager.delete(key, namespace)


def clear_cache(namespace: str | None = None, pattern: str | None = None) -> bool:
    """清空缓存便捷函数"""
    return cache_manager.clear(namespace, pattern)
