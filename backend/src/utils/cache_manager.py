from typing import TYPE_CHECKING, Any

"""
缓存管理模块
提供Redis缓存功能，用于优化API性能
"""

import logging
import pickle  # nosec - B403: Internal cache data, validated source
from datetime import datetime, timedelta

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore

if TYPE_CHECKING:
    from redis.asyncio import Redis


# 设置默认配置，避免依赖外部配置文件
class Settings:
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_PASSWORD = None


settings = Settings()

logger = logging.getLogger(__name__)


class CacheManager:
    """缓存管理器 - 支持Redis和内存缓存后备"""

    def __init__(self):
        self.redis_client: Redis | None = None
        self.memory_cache: dict[str, Any] = {}
        self.memory_cache_expiry: dict[str, Any] = {}
        self.use_memory_fallback = True

    async def initialize(self):
        """初始化Redis连接"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis库未安装，使用内存缓存")
            return

        try:
            self.redis_client = redis.Redis(  # type: ignore
                host=settings.REDIS_HOST or "localhost",
                port=settings.REDIS_PORT or 6379,
                db=settings.REDIS_DB or 0,
                password=settings.REDIS_PASSWORD,
                decode_responses=False,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # 测试连接
            await self.redis_client.ping()
            logger.info("Redis缓存连接成功")
        except Exception as e:
            logger.warning(f"Redis连接失败: {e}")
            self.redis_client = None
            if self.use_memory_fallback:
                logger.info("启用内存缓存作为后备方案")
            else:
                logger.warning("缓存功能已禁用")

    def _clean_expired_memory_cache(self):
        """清理过期的内存缓存"""
        current_time = datetime.now()
        expired_keys = [
            key
            for key, expiry_time in self.memory_cache_expiry.items()
            if expiry_time <= current_time
        ]
        for key in expired_keys:
            self.memory_cache.pop(key, None)
            self.memory_cache_expiry.pop(key, None)

    async def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()

    def _get_key(self, prefix: str, key: str) -> str:
        """生成缓存键"""
        return f"{prefix}:{key}"

    async def get(self, prefix: str, key: str) -> Any | None:
        """获取缓存数据"""
        cache_key = self._get_key(prefix, key)

        # 首先尝试Redis缓存
        if self.redis_client:
            try:
                data = await self.redis_client.get(cache_key)
                if data:
                    return pickle.loads(data)  # nosec - B301: Internal cache data from trusted source
            except Exception as e:
                logger.warning(f"Redis缓存获取失败: {e}")

        # Redis不可用或失败时，使用内存缓存
        if self.use_memory_fallback:
            self._clean_expired_memory_cache()
            if cache_key in self.memory_cache:
                logger.debug(f"从内存缓存获取: {cache_key}")
                return self.memory_cache[cache_key]

        return None

    async def set(self, prefix: str, key: str, value: Any, expire: int = 3600) -> bool:
        """设置缓存数据"""
        cache_key = self._get_key(prefix, key)
        data = pickle.dumps(value)
        success = False

        # 首先尝试Redis缓存
        if self.redis_client:
            try:
                await self.redis_client.setex(cache_key, expire, data)
                success = True
                logger.debug(f"Redis缓存设置成功: {cache_key}")
            except Exception as e:
                logger.warning(f"Redis缓存设置失败: {e}")

        # 如果Redis失败，使用内存缓存
        if not success and self.use_memory_fallback:
            try:
                self.memory_cache[cache_key] = value
                expiry_time = datetime.now() + timedelta(seconds=expire)
                self.memory_cache_expiry[cache_key] = expiry_time
                logger.debug(f"内存缓存设置成功: {cache_key}")
                success = True
            except Exception as e:
                logger.error(f"内存缓存设置失败: {e}")

        return success

    async def delete(self, prefix: str, key: str) -> bool:
        """删除缓存数据"""
        cache_key = self._get_key(prefix, key)
        success = False

        # 尝试从Redis删除
        if self.redis_client:
            try:
                await self.redis_client.delete(cache_key)
                success = True
            except Exception as e:
                logger.warning(f"Redis缓存删除失败: {e}")

        # 从内存缓存删除
        if self.use_memory_fallback:
            self.memory_cache.pop(cache_key, None)
            self.memory_cache_expiry.pop(cache_key, None)
            success = True

        return success

    async def clear_pattern(self, pattern: str) -> int:
        """根据模式清除缓存"""
        deleted_count = 0

        # 尝试从Redis清除
        if self.redis_client:
            try:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    deleted_count = await self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis缓存清除失败: {e}")

        # 从内存缓存清除匹配的键
        if self.use_memory_fallback:
            try:
                keys_to_delete = [
                    key for key in self.memory_cache if pattern.replace("*", "") in key
                ]
                for key in keys_to_delete:
                    self.memory_cache.pop(key, None)
                    self.memory_cache_expiry.pop(key, None)
                    deleted_count += 1
            except Exception as e:
                logger.error(f"内存缓存清除失败: {e}")

        return deleted_count


# 全局缓存管理器实例
cache_manager = CacheManager()


async def get_cache_manager() -> CacheManager:
    """获取缓存管理器依赖"""
    return cache_manager


def cache_key_builder(func_name: str, **kwargs) -> str:
    """构建缓存键"""
    # 过滤掉不需要包含在缓存键中的参数
    filtered_kwargs = {
        k: v
        for k, v in kwargs.items()
        if k not in ["db", "current_user", "skip", "limit"]
    }

    # 将参数转换为字符串
    key_parts = [func_name]
    for k, v in sorted(filtered_kwargs.items()):
        key_parts.append(f"{k}={v}")

    return ":".join(key_parts)


class CacheDecorator:
    """缓存装饰器 - 支持同步和异步函数"""

    def __init__(self, prefix: str, expire: int = 3600, key_builder=None):
        self.prefix = prefix
        self.expire = expire
        self.key_builder = key_builder or cache_key_builder

    def __call__(self, func):
        # 检测函数是否为异步函数
        import asyncio

        is_async_func = asyncio.iscoroutinefunction(func)

        if is_async_func:
            # 异步函数的处理逻辑
            async def async_wrapper(*args, **kwargs):
                # 构建缓存键
                cache_key = self.key_builder(func.__name__, **kwargs)

                # 尝试从缓存获取
                cached_result = await cache_manager.get(self.prefix, cache_key)
                if cached_result is not None:
                    return cached_result

                # 执行异步函数
                result = await func(*args, **kwargs)

                # 设置缓存
                await cache_manager.set(self.prefix, cache_key, result, self.expire)

                return result

            return async_wrapper
        else:
            # 同步函数的处理逻辑
            def sync_wrapper(*args, **kwargs):
                # 构建缓存键
                self.key_builder(func.__name__, **kwargs)

                # 对于同步函数，使用同步方式的缓存（内存缓存）
                # 因为在同步上下文中无法使用async方法

                # 使用线程局部存储或简单返回结果（不在缓存中）
                # 由于cache_manager是异步的，同步函数暂时跳过缓存
                # 直接执行函数
                return func(*args, **kwargs)

            return sync_wrapper


# 常用缓存装饰器
def cache_statistics(expire: int = 1800):  # 30分钟
    """统计数据缓存"""
    return CacheDecorator("statistics", expire)


def cache_assets(expire: int = 3600):  # 1小时
    """资产数据缓存"""
    return CacheDecorator("assets", expire)


def cache_dictionary(expire: int = 7200):  # 2小时
    """字典数据缓存"""
    return CacheDecorator("dictionary", expire)
