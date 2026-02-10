import fnmatch
import json
from collections.abc import Awaitable, Callable
from datetime import datetime
from decimal import Decimal
from typing import Any, ParamSpec, TypeVar, cast, overload

"""
缓存管理模块（统一后端）
为统计模块提供异步接口，但统一复用 core.cache_manager 的单一后端。
"""

from ..core.cache_manager import (
    MemoryCache,
    RedisCache,
)
from ..core.cache_manager import (
    cache_manager as core_cache_manager,
)

P = ParamSpec("P")
R = TypeVar("R")


class CacheManager:
    """异步接口的缓存管理器（委托到核心缓存）"""

    def __init__(self) -> None:
        self.backend = core_cache_manager.backend

    async def initialize(self) -> None:
        # 核心缓存为同步实现，初始化在 core 中完成
        return None

    async def close(self) -> None:
        return None

    async def get(self, prefix: str, key: str) -> Any | None:
        return core_cache_manager.get(key, namespace=prefix)

    async def set(self, prefix: str, key: str, value: Any, expire: int = 3600) -> bool:
        return core_cache_manager.set(key, value, ttl=expire, namespace=prefix)

    async def delete(self, prefix: str, key: str) -> bool:
        return core_cache_manager.delete(key, namespace=prefix)

    async def clear_pattern(self, pattern: str) -> int:
        full_pattern = f"{core_cache_manager.key_prefix}:{pattern}"
        backend = core_cache_manager.backend
        deleted_count = 0

        try:
            if isinstance(backend, MemoryCache):
                deleted_keys = [
                    key for key in backend._cache if fnmatch.fnmatch(key, full_pattern)
                ]
                for key in deleted_keys:
                    del backend._cache[key]
                deleted_count = len(deleted_keys)
            elif isinstance(backend, RedisCache):
                keys = list(backend.client.scan_iter(match=full_pattern))
                if keys:
                    backend.client.delete(*keys)
                deleted_count = len(keys)
            else:
                core_cache_manager.clear(pattern=pattern)
        except Exception:
            core_cache_manager.clear(pattern=pattern)
            deleted_count = 0

        return deleted_count

    def get_stats(self) -> dict[str, Any]:
        return core_cache_manager.get_stats()


class CacheJSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，用于序列化缓存数据"""

    def default(self, obj: Any) -> Any:
        """处理非JSON原生类型"""
        if isinstance(obj, datetime):
            return {"__datetime__": obj.isoformat()}
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def cache_json_dumps(obj: Any) -> bytes:
    """序列化对象为JSON字节串"""
    return json.dumps(obj, cls=CacheJSONEncoder).encode("utf-8")


def cache_json_loads(data: bytes) -> Any:
    """反序列化JSON字节串为对象"""

    def object_hook(dct: dict[str, Any]) -> Any:
        if "__datetime__" in dct:
            return datetime.fromisoformat(dct["__datetime__"])
        return dct

    try:
        return json.loads(data.decode("utf-8"), object_hook=object_hook)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None


# 全局缓存管理器实例
cache_manager: CacheManager = CacheManager()


async def get_cache_manager() -> CacheManager:
    """获取缓存管理器依赖"""
    return cache_manager


def cache_key_builder(func_name: str, **kwargs: Any) -> str:
    """构建缓存键"""
    # 过滤掉不需要包含在缓存键中的参数
    filtered_kwargs = {
        k: v
        for k, v in kwargs.items()
        if k not in ["db", "current_user", "skip", "page_size"]
    }

    # 将参数转换为字符串
    key_parts = [func_name]
    for k, v in sorted(filtered_kwargs.items()):
        key_parts.append(f"{k}={v}")

    return ":".join(key_parts)


class CacheDecorator:
    """缓存装饰器 - 支持同步和异步函数"""

    def __init__(
        self,
        prefix: str,
        expire: int = 3600,
        key_builder: Callable[..., str] | None = None,
    ) -> None:
        self.prefix = prefix
        self.expire = expire
        self.key_builder = key_builder or cache_key_builder

    @overload
    def __call__(
        self, func: Callable[P, Awaitable[R]]
    ) -> Callable[P, Awaitable[R]]: ...

    @overload
    def __call__(self, func: Callable[P, R]) -> Callable[P, R]: ...

    def __call__(self, func: Callable[P, Any]) -> Callable[P, Any]:
        import asyncio

        is_async_func = asyncio.iscoroutinefunction(func)

        if is_async_func:

            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                cache_key = self.key_builder(func.__name__, **kwargs)
                cached_result = await cache_manager.get(self.prefix, cache_key)
                if cached_result is not None:
                    return cached_result

                result = await func(*args, **kwargs)
                await cache_manager.set(self.prefix, cache_key, result, self.expire)
                return result

            return cast(Callable[P, Any], async_wrapper)

        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            cache_key = self.key_builder(func.__name__, **kwargs)
            cached_result = core_cache_manager.get(cache_key, namespace=self.prefix)
            if cached_result is not None:
                return cached_result

            result = func(*args, **kwargs)
            core_cache_manager.set(
                cache_key, result, ttl=self.expire, namespace=self.prefix
            )
            return result

        return sync_wrapper


# 常用缓存装饰器
def cache_statistics(expire: int = 1800) -> CacheDecorator:  # 30分钟
    """统计数据缓存"""
    return CacheDecorator("statistics", expire)


def cache_assets(expire: int = 3600) -> CacheDecorator:  # 1小时
    """资产数据缓存"""
    return CacheDecorator("assets", expire)


def cache_dictionary(expire: int = 7200) -> CacheDecorator:  # 2小时
    """字典数据缓存"""
    return CacheDecorator("dictionary", expire)
