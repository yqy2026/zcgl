"""
测试认证服务拆分 (使用 Mock 避免数据库依赖)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.core.authentication_service import AsyncAuthenticationService
from src.services.core.user_management_service import AsyncUserManagementService


@pytest.fixture
def auth_service(mock_db):
    """创建 AuthenticationService 实例"""
    return AsyncAuthenticationService(mock_db)


@pytest.fixture
def user_mgmt(mock_db):
    """创建 UserManagementService 实例"""
    return AsyncUserManagementService(mock_db)


@pytest.fixture
def mock_db():
    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


def _mock_execute_first(value):
    result = MagicMock()
    scalars = MagicMock()
    scalars.first.return_value = value
    result.scalars.return_value = scalars
    return result


@pytest.mark.asyncio
async def test_auth_services_split_verification(auth_service, user_mgmt, mock_db):
    """测试认证服务拆分 - 简化版本"""
    # 这个测试主要验证服务可以正常实例化和调用
    # 具体的业务逻辑测试应该在集成测试中进行

    # 1. 验证服务实例化
    assert auth_service is not None
    assert user_mgmt is not None

    # 2. 验证服务方法存在
    assert hasattr(auth_service, "authenticate_user")
    assert hasattr(user_mgmt, "create_user")
    assert hasattr(user_mgmt, "get_user_by_username")

    mock_db.execute.return_value = _mock_execute_first(None)
    result = await auth_service.authenticate_user("nonexistent", "password")
    assert result is None

    mock_db.execute.return_value = _mock_execute_first(None)
    user = await user_mgmt.get_user_by_username("nonexistent")
    assert user is None
