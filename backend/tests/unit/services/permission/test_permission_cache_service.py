"""
权限缓存服务单元测试

测试 PermissionCacheService 的缓存管理功能
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.services.permission.permission_cache_service import (
    PermissionCacheService,
    get_permission_cache_service,
    set_permission_cache_service,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_redis():
    """模拟Redis客户端"""
    redis = Mock()
    redis.get = AsyncMock()
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    redis.scan = AsyncMock()
    return redis


@pytest.fixture
def cache_service(mock_redis):
    """权限缓存服务实例"""
    return PermissionCacheService(redis_client=mock_redis, ttl_seconds=300)


@pytest.fixture
def disabled_cache_service():
    """禁用的权限缓存服务实例（无Redis）"""
    return PermissionCacheService(redis_client=None, ttl_seconds=300)


# ============================================================================
# __init__ 测试
# ============================================================================


class TestPermissionCacheServiceInit:
    """测试权限缓存服务初始化"""

    def test_init_with_redis(self, mock_redis):
        """测试使用Redis客户端初始化"""
        service = PermissionCacheService(redis_client=mock_redis, ttl_seconds=600)

        assert service.redis is not None
        assert service.ttl == 600
        assert service.enabled is True

    def test_init_without_redis(self):
        """测试不使用Redis客户端初始化"""
        service = PermissionCacheService(redis_client=None, ttl_seconds=300)

        assert service.redis is None
        assert service.ttl == 300
        assert service.enabled is False


# ============================================================================
# _get_user_permissions_key 测试
# ============================================================================


class TestGetUserPermissionsKey:
    """测试获取用户权限缓存键"""

    def test_with_int_user_id(self, cache_service):
        """测试整数用户ID"""
        key = cache_service._get_user_permissions_key(123)
        assert key == "permission:user:123:permissions"

    def test_with_str_user_id(self, cache_service):
        """测试字符串用户ID"""
        key = cache_service._get_user_permissions_key("user-123")
        assert key == "permission:user:user-123:permissions"


# ============================================================================
# _get_user_roles_key 测试
# ============================================================================


class TestGetUserRolesKey:
    """测试获取用户角色缓存键"""

    def test_with_int_user_id(self, cache_service):
        """测试整数用户ID"""
        key = cache_service._get_user_roles_key(123)
        assert key == "permission:user:123:roles"

    def test_with_str_user_id(self, cache_service):
        """测试字符串用户ID"""
        key = cache_service._get_user_roles_key("user-123")
        assert key == "permission:user:user-123:roles"


# ============================================================================
# _get_role_permissions_key 测试
# ============================================================================


class TestGetRolePermissionsKey:
    """测试获取角色权限缓存键"""

    def test_with_int_role_id(self, cache_service):
        """测试整数角色ID"""
        key = cache_service._get_role_permissions_key(1)
        assert key == "permission:role:1:permissions"

    def test_with_str_role_id(self, cache_service):
        """测试字符串角色ID"""
        key = cache_service._get_role_permissions_key("role-1")
        assert key == "permission:role:role-1:permissions"


# ============================================================================
# get_user_permissions 测试
# ============================================================================


class TestGetUserPermissions:
    """测试获取用户权限"""

    @pytest.mark.asyncio
    async def test_cache_hit(self, cache_service, mock_redis):
        """测试缓存命中"""
        permissions = ["asset.view", "asset.create", "asset.edit"]
        mock_redis.get.return_value = json.dumps(permissions)

        result = await cache_service.get_user_permissions(123)

        assert result == permissions
        mock_redis.get.assert_called_once_with("permission:user:123:permissions")

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache_service, mock_redis):
        """测试缓存未命中"""
        mock_redis.get.return_value = None

        result = await cache_service.get_user_permissions(123)

        assert result is None
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_disabled(self, disabled_cache_service):
        """测试缓存禁用时返回None"""
        result = await disabled_cache_service.get_user_permissions(123)
        assert result is None

    @pytest.mark.asyncio
    async def test_redis_error(self, cache_service, mock_redis):
        """测试Redis异常"""
        mock_redis.get.side_effect = Exception("Redis connection error")

        result = await cache_service.get_user_permissions(123)

        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_json(self, cache_service, mock_redis):
        """测试无效的JSON"""
        mock_redis.get.return_value = "invalid json"

        result = await cache_service.get_user_permissions(123)

        # 应该捕获JSON解析错误并返回None
        assert result is None


# ============================================================================
# set_user_permissions 测试
# ============================================================================


class TestSetUserPermissions:
    """测试设置用户权限"""

    @pytest.mark.asyncio
    async def test_set_success(self, cache_service, mock_redis):
        """测试成功设置权限"""
        permissions = ["asset.view", "asset.create"]
        mock_redis.setex.return_value = True

        result = await cache_service.set_user_permissions(123, permissions)

        assert result is True
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "permission:user:123:permissions"
        assert call_args[0][1] == 300
        assert call_args[0][2] == json.dumps(permissions)

    @pytest.mark.asyncio
    async def test_set_empty_permissions(self, cache_service, mock_redis):
        """测试设置空权限列表"""
        permissions = []
        mock_redis.setex.return_value = True

        result = await cache_service.set_user_permissions(123, permissions)

        assert result is True
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_disabled(self, disabled_cache_service):
        """测试缓存禁用时返回False"""
        result = await disabled_cache_service.set_user_permissions(
            123, ["asset.view"]
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_redis_error(self, cache_service, mock_redis):
        """测试Redis异常"""
        mock_redis.setex.side_effect = Exception("Redis connection error")

        result = await cache_service.set_user_permissions(123, ["asset.view"])

        assert result is False


# ============================================================================
# get_user_roles 测试
# ============================================================================


class TestGetUserRoles:
    """测试获取用户角色"""

    @pytest.mark.asyncio
    async def test_cache_hit(self, cache_service, mock_redis):
        """测试缓存命中"""
        roles = [
            {"id": "role-1", "name": "admin"},
            {"id": "role-2", "name": "user"},
        ]
        mock_redis.get.return_value = json.dumps(roles)

        result = await cache_service.get_user_roles(123)

        assert result == roles
        mock_redis.get.assert_called_once_with("permission:user:123:roles")

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache_service, mock_redis):
        """测试缓存未命中"""
        mock_redis.get.return_value = None

        result = await cache_service.get_user_roles(123)

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_disabled(self, disabled_cache_service):
        """测试缓存禁用时返回None"""
        result = await disabled_cache_service.get_user_roles(123)
        assert result is None

    @pytest.mark.asyncio
    async def test_redis_error(self, cache_service, mock_redis):
        """测试Redis异常"""
        mock_redis.get.side_effect = Exception("Redis connection error")

        result = await cache_service.get_user_roles(123)

        assert result is None


# ============================================================================
# set_user_roles 测试
# ============================================================================


class TestSetUserRoles:
    """测试设置用户角色"""

    @pytest.mark.asyncio
    async def test_set_success(self, cache_service, mock_redis):
        """测试成功设置角色"""
        roles = [
            {"id": "role-1", "name": "admin"},
            {"id": "role-2", "name": "user"},
        ]
        mock_redis.setex.return_value = True

        result = await cache_service.set_user_roles(123, roles)

        assert result is True
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "permission:user:123:roles"
        assert call_args[0][2] == json.dumps(roles)

    @pytest.mark.asyncio
    async def test_set_empty_roles(self, cache_service, mock_redis):
        """测试设置空角色列表"""
        roles = []
        mock_redis.setex.return_value = True

        result = await cache_service.set_user_roles(123, roles)

        assert result is True

    @pytest.mark.asyncio
    async def test_cache_disabled(self, disabled_cache_service):
        """测试缓存禁用时返回False"""
        result = await disabled_cache_service.set_user_roles(123, [])
        assert result is False

    @pytest.mark.asyncio
    async def test_redis_error(self, cache_service, mock_redis):
        """测试Redis异常"""
        mock_redis.setex.side_effect = Exception("Redis connection error")

        result = await cache_service.set_user_roles(123, [])

        assert result is False


# ============================================================================
# invalidate_user_cache 测试
# ============================================================================


class TestInvalidateUserCache:
    """测试清除用户缓存"""

    @pytest.mark.asyncio
    async def test_invalidate_success(self, cache_service, mock_redis):
        """测试成功清除用户缓存"""
        mock_redis.delete.return_value = 2

        result = await cache_service.invalidate_user_cache(123)

        assert result is True
        mock_redis.delete.assert_called_once_with(
            "permission:user:123:permissions", "permission:user:123:roles"
        )

    @pytest.mark.asyncio
    async def test_cache_disabled(self, disabled_cache_service):
        """测试缓存禁用时返回False"""
        result = await disabled_cache_service.invalidate_user_cache(123)
        assert result is False

    @pytest.mark.asyncio
    async def test_redis_error(self, cache_service, mock_redis):
        """测试Redis异常"""
        mock_redis.delete.side_effect = Exception("Redis connection error")

        result = await cache_service.invalidate_user_cache(123)

        assert result is False


# ============================================================================
# invalidate_role_cache 测试
# ============================================================================


class TestInvalidateRoleCache:
    """测试清除角色缓存"""

    @pytest.mark.asyncio
    async def test_invalidate_success(self, cache_service, mock_redis):
        """测试成功清除角色缓存"""
        mock_redis.delete.return_value = 1

        result = await cache_service.invalidate_role_cache("role-1")

        assert result is True
        mock_redis.delete.assert_called_once_with(
            "permission:role:role-1:permissions"
        )

    @pytest.mark.asyncio
    async def test_cache_disabled(self, disabled_cache_service):
        """测试缓存禁用时返回False"""
        result = await disabled_cache_service.invalidate_role_cache("role-1")
        assert result is False

    @pytest.mark.asyncio
    async def test_redis_error(self, cache_service, mock_redis):
        """测试Redis异常"""
        mock_redis.delete.side_effect = Exception("Redis connection error")

        result = await cache_service.invalidate_role_cache("role-1")

        assert result is False


# ============================================================================
# invalidate_all_permission_cache 测试
# ============================================================================


class TestInvalidateAllPermissionCache:
    """测试清除所有权限缓存"""

    @pytest.mark.asyncio
    async def test_invalidate_all_success(self, cache_service, mock_redis):
        """测试成功清除所有权限缓存"""
        # 模拟SCAN返回结果，第一次返回一些键（cursor=0表示已完成）
        mock_redis.scan.return_value = (
            0, [b"permission:user:1:permissions", b"permission:user:2:roles"]
        )
        mock_redis.delete.return_value = 2

        result = await cache_service.invalidate_all_permission_cache()

        assert result is True
        mock_redis.scan.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_all_multiple_pages(self, cache_service, mock_redis):
        """测试清除多页缓存"""
        # 模拟SCAN返回多页结果
        mock_redis.scan.side_effect = [
            (1, [b"permission:user:1:permissions"]),  # 第一页，cursor=1
            (0, [b"permission:user:2:roles"]),  # 第二页，cursor=0（结束）
        ]
        mock_redis.delete.return_value = 1

        result = await cache_service.invalidate_all_permission_cache()

        assert result is True
        assert mock_redis.scan.call_count == 2
        assert mock_redis.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_invalidate_all_no_keys(self, cache_service, mock_redis):
        """测试没有权限缓存键"""
        mock_redis.scan.side_effect = [(0, [])]
        mock_redis.delete.return_value = 0

        result = await cache_service.invalidate_all_permission_cache()

        assert result is True
        mock_redis.scan.assert_called_once()
        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_disabled(self, disabled_cache_service):
        """测试缓存禁用时返回False"""
        result = await disabled_cache_service.invalidate_all_permission_cache()
        assert result is False

    @pytest.mark.asyncio
    async def test_redis_error(self, cache_service, mock_redis):
        """测试Redis异常"""
        mock_redis.scan.side_effect = Exception("Redis connection error")

        result = await cache_service.invalidate_all_permission_cache()

        assert result is False


# ============================================================================
# has_permission 测试
# ============================================================================


class TestHasPermission:
    """测试检查用户权限"""

    @pytest.mark.asyncio
    async def test_has_permission_true(self, cache_service, mock_redis):
        """测试用户拥有权限"""
        permissions = ["asset.view", "asset.create", "asset.edit"]
        mock_redis.get.return_value = json.dumps(permissions)

        result = await cache_service.has_permission(123, "asset.view")

        assert result is True

    @pytest.mark.asyncio
    async def test_has_permission_false(self, cache_service, mock_redis):
        """测试用户不拥有权限"""
        permissions = ["asset.view", "asset.create"]
        mock_redis.get.return_value = json.dumps(permissions)

        result = await cache_service.has_permission(123, "asset.delete")

        assert result is False

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, cache_service, mock_redis):
        """测试缓存未命中返回None"""
        mock_redis.get.return_value = None

        result = await cache_service.has_permission(123, "asset.view")

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_disabled(self, disabled_cache_service):
        """测试缓存禁用时返回None"""
        result = await disabled_cache_service.has_permission(123, "asset.view")
        assert result is None


# ============================================================================
# get_cache_stats 测试
# ============================================================================


class TestGetCacheStats:
    """测试获取缓存统计"""

    @pytest.mark.asyncio
    async def test_stats_enabled(self, cache_service, mock_redis):
        """测试获取缓存统计（启用状态）"""
        # 模拟SCAN返回混合键
        mock_redis.scan.side_effect = [
            (
                0,
                [
                    b"permission:user:1:permissions",
                    b"permission:user:2:roles",
                    b"permission:role:1:permissions",
                ],
            )
        ]

        result = await cache_service.get_cache_stats()

        assert result["enabled"] is True
        assert result["ttl_seconds"] == 300
        assert result["total_keys"] == 3
        assert result["user_permission_keys"] == 1
        assert result["user_role_keys"] == 1
        assert result["role_permission_keys"] == 1

    @pytest.mark.asyncio
    async def test_stats_string_keys(self, cache_service, mock_redis):
        """测试字符串类型的键"""
        mock_redis.scan.side_effect = [
            (
                0,
                [
                    "permission:user:1:permissions",  # 字符串键
                    "permission:user:2:roles",
                ],
            )
        ]

        result = await cache_service.get_cache_stats()

        assert result["enabled"] is True
        assert result["total_keys"] == 2
        assert result["user_permission_keys"] == 1
        assert result["user_role_keys"] == 1

    @pytest.mark.asyncio
    async def test_stats_empty(self, cache_service, mock_redis):
        """测试空缓存统计"""
        mock_redis.scan.side_effect = [(0, [])]

        result = await cache_service.get_cache_stats()

        assert result["enabled"] is True
        assert result["total_keys"] == 0
        assert result["user_permission_keys"] == 0
        assert result["user_role_keys"] == 0
        assert result["role_permission_keys"] == 0

    @pytest.mark.asyncio
    async def test_stats_disabled(self, disabled_cache_service):
        """测试缓存禁用时的统计"""
        result = await disabled_cache_service.get_cache_stats()

        assert result == {"enabled": False}

    @pytest.mark.asyncio
    async def test_stats_redis_error(self, cache_service, mock_redis):
        """测试Redis异常"""
        mock_redis.scan.side_effect = Exception("Redis connection error")

        result = await cache_service.get_cache_stats()

        assert result["enabled"] is True
        assert "error" in result
        assert "Redis connection error" in result["error"]


# ============================================================================
# 全局服务实例测试
# ============================================================================


class TestGlobalServiceInstance:
    """测试全局服务实例"""

    def test_get_permission_cache_service_singleton(self):
        """测试获取单例服务实例"""
        # 重置全局实例
        import src.services.permission.permission_cache_service as cache_module

        cache_module._permission_cache_service = None

        service1 = get_permission_cache_service()
        service2 = get_permission_cache_service()

        assert service1 is service2

    def test_set_permission_cache_service(self, mock_redis):
        """测试设置服务实例"""
        custom_service = PermissionCacheService(
            redis_client=mock_redis, ttl_seconds=600
        )

        set_permission_cache_service(custom_service)

        service = get_permission_cache_service()
        assert service is custom_service
        assert service.ttl == 600

        # 重置全局实例
        import src.services.permission.permission_cache_service as cache_module

        cache_module._permission_cache_service = None
