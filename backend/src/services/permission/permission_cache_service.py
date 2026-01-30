"""
权限缓存服务
使用Redis缓存用户权限，提升权限验证性能
"""

import json
import logging
from typing import Any, cast

logger = logging.getLogger(__name__)


class PermissionCacheService:
    """权限缓存服务"""

    def __init__(self, redis_client: Any | None = None, ttl_seconds: int = 300):
        """
        初始化权限缓存服务

        Args:
            redis_client: Redis客户端实例
            ttl_seconds: 缓存过期时间（秒），默认5分钟
        """
        self.redis: Any | None = redis_client
        self.ttl = ttl_seconds
        self.enabled = redis_client is not None

        if not self.enabled:
            logger.warning("Redis client not available, permission cache is disabled")

    def _get_user_permissions_key(self, user_id: int | str) -> str:
        """获取用户权限缓存键"""
        return f"permission:user:{user_id}:permissions"

    def _get_user_roles_key(self, user_id: int | str) -> str:
        """获取用户角色缓存键"""
        return f"permission:user:{user_id}:roles"

    def _get_role_permissions_key(self, role_id: int | str) -> str:
        """获取角色权限缓存键"""
        return f"permission:role:{role_id}:permissions"

    async def get_user_permissions(self, user_id: int | str) -> list[str] | None:
        """
        获取用户权限列表（从缓存）

        Args:
            user_id: 用户ID

        Returns:
            权限代码列表，如果缓存未命中返回None
        """
        if not self.enabled or self.redis is None:
            return None

        try:
            key = self._get_user_permissions_key(user_id)
            cached = await self.redis.get(key)

            if cached:
                logger.debug(f"Cache hit for user {user_id} permissions")
                return cast(list[str], json.loads(cached))

            logger.debug(f"Cache miss for user {user_id} permissions")
            return None

        except Exception as e:
            logger.error(f"Error getting user permissions from cache: {e}")
            return None

    async def set_user_permissions(
        self, user_id: int | str, permissions: list[str]
    ) -> bool:
        """
        设置用户权限缓存

        Args:
            user_id: 用户ID
            permissions: 权限代码列表

        Returns:
            是否设置成功
        """
        if not self.enabled or self.redis is None:
            return False

        try:
            key = self._get_user_permissions_key(user_id)
            value = json.dumps(permissions)
            await self.redis.setex(key, self.ttl, value)
            logger.debug(f"Cached permissions for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error setting user permissions cache: {e}")
            return False

    async def get_user_roles(self, user_id: int | str) -> list[dict[str, Any]] | None:
        """
        获取用户角色列表（从缓存）

        Args:
            user_id: 用户ID

        Returns:
            角色信息列表，如果缓存未命中返回None
        """
        if not self.enabled or self.redis is None:
            return None  # pragma: no cover

        try:
            key = self._get_user_roles_key(user_id)
            cached = await self.redis.get(key)

            if cached:
                logger.debug(f"Cache hit for user {user_id} roles")
                return cast(list[dict[str, Any]], json.loads(cached))

            logger.debug(f"Cache miss for user {user_id} roles")
            return None

        except Exception as e:  # pragma: no cover
            logger.error(
                f"Error getting user roles from cache: {e}"
            )  # pragma: no cover
            return None  # pragma: no cover

    async def set_user_roles(
        self, user_id: int | str, roles: list[dict[str, Any]]
    ) -> bool:
        """
        设置用户角色缓存

        Args:
            user_id: 用户ID
            roles: 角色信息列表

        Returns:
            是否设置成功
        """
        if not self.enabled or self.redis is None:
            return False

        try:
            key = self._get_user_roles_key(user_id)
            value = json.dumps(roles)
            await self.redis.setex(key, self.ttl, value)
            logger.debug(f"Cached roles for user {user_id}")
            return True

        except Exception as e:  # pragma: no cover
            logger.error(f"Error setting user roles cache: {e}")  # pragma: no cover
            return False  # pragma: no cover

    async def invalidate_user_cache(self, user_id: int | str) -> bool:
        """
        清除用户相关缓存

        Args:
            user_id: 用户ID

        Returns:
            是否清除成功
        """
        if not self.enabled or self.redis is None:
            return False

        try:
            keys_to_delete = [
                self._get_user_permissions_key(user_id),
                self._get_user_roles_key(user_id),
            ]

            deleted = await self.redis.delete(*keys_to_delete)
            logger.info(f"Invalidated cache for user {user_id}, deleted {deleted} keys")
            return True

        except Exception as e:  # pragma: no cover
            logger.error(f"Error invalidating user cache: {e}")  # pragma: no cover
            return False  # pragma: no cover

    async def invalidate_role_cache(self, role_id: int | str) -> bool:
        """
        清除角色相关缓存

        Args:
            role_id: 角色ID

        Returns:
            是否清除成功
        """
        if not self.enabled or self.redis is None:
            return False

        try:
            key = self._get_role_permissions_key(role_id)
            await self.redis.delete(key)
            logger.info(f"Invalidated cache for role {role_id}")
            return True

        except Exception as e:  # pragma: no cover
            logger.error(f"Error invalidating role cache: {e}")  # pragma: no cover
            return False  # pragma: no cover

    async def invalidate_all_permission_cache(self) -> bool:
        """
        清除所有权限相关缓存

        Returns:
            是否清除成功
        """
        if not self.enabled or self.redis is None:
            return False

        try:
            # 使用SCAN命令查找所有权限相关的键
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await self.redis.scan(
                    cursor, match="permission:*", count=100
                )
                if keys:
                    deleted = await self.redis.delete(*keys)
                    deleted_count += deleted

                if cursor == 0:
                    break

            logger.info(
                f"Invalidated all permission cache, deleted {deleted_count} keys"
            )
            return True

        except Exception as e:  # pragma: no cover
            logger.error(
                f"Error invalidating all permission cache: {e}"
            )  # pragma: no cover
            return False  # pragma: no cover

    async def has_permission(
        self, user_id: int | str, permission_code: str
    ) -> bool | None:
        """
        检查用户是否拥有某个权限（从缓存）

        Args:
            user_id: 用户ID
            permission_code: 权限代码

        Returns:
            是否拥有权限，如果缓存未命中返回None
        """
        permissions = await self.get_user_permissions(user_id)
        if permissions is None:
            return None

        return permission_code in permissions

    async def get_cache_stats(self) -> dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            缓存统计信息
        """
        if not self.enabled or self.redis is None:
            return {"enabled": False}

        try:
            # 统计权限缓存键数量
            cursor = 0
            total_keys = 0
            user_permission_keys = 0
            user_role_keys = 0
            role_permission_keys = 0

            while True:
                cursor, keys = await self.redis.scan(
                    cursor, match="permission:*", count=100
                )
                total_keys += len(keys)

                for key in keys:
                    key_str = key.decode() if isinstance(key, bytes) else key
                    if ":permissions" in key_str:
                        if key_str.startswith("permission:user:"):
                            user_permission_keys += 1
                        elif key_str.startswith("permission:role:"):
                            role_permission_keys += 1
                    elif ":roles" in key_str:
                        user_role_keys += 1

                if cursor == 0:
                    break

            return {
                "enabled": True,
                "ttl_seconds": self.ttl,
                "total_keys": total_keys,
                "user_permission_keys": user_permission_keys,
                "user_role_keys": user_role_keys,
                "role_permission_keys": role_permission_keys,
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                "enabled": True,
                "error": str(e),
            }


# 全局权限缓存服务实例
_permission_cache_service: PermissionCacheService | None = None


def get_permission_cache_service() -> PermissionCacheService:
    """获取权限缓存服务实例"""
    global _permission_cache_service

    if _permission_cache_service is None:
        # 尝试获取Redis客户端
        redis_client = None
        try:
            from ...core.database import get_redis

            redis_client = get_redis()
        except ImportError:  # pragma: no cover
            logger.warning("Redis client not available")  # pragma: no cover
        except Exception as e:  # pragma: no cover
            logger.warning(f"Failed to get Redis client: {e}")  # pragma: no cover

        # 从配置获取TTL
        ttl_seconds = 300  # 默认5分钟，固定值

        _permission_cache_service = PermissionCacheService(
            redis_client=redis_client, ttl_seconds=ttl_seconds
        )

    return _permission_cache_service


def set_permission_cache_service(service: PermissionCacheService) -> None:
    """设置权限缓存服务实例（用于测试）"""
    global _permission_cache_service
    _permission_cache_service = service
