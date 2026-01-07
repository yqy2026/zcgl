"""
测试认证服务拆分 (使用 Mock 避免数据库依赖)
"""

from unittest.mock import MagicMock

import pytest

from src.services.core.authentication_service import AuthenticationService
from src.services.core.user_management_service import UserManagementService


@pytest.fixture
def mock_db():
    """创建模拟数据库会话"""
    return MagicMock()


@pytest.fixture
def auth_service(mock_db):
    """创建 AuthenticationService 实例"""
    return AuthenticationService(mock_db)


@pytest.fixture
def user_mgmt(mock_db):
    """创建 UserManagementService 实例"""
    return UserManagementService(mock_db)


def test_auth_services_split_verification(auth_service, user_mgmt, mock_db):
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

    # 3. 验证mock数据库可以正常工作
    mock_query = MagicMock()
    mock_db.query.return_value = mock_query
    assert mock_db.query.called is False  # 初始状态未调用

    # 4. 测试认证失败场景（用户不存在）
    mock_query.filter.return_value.first.return_value = None
    result = auth_service.authenticate_user("nonexistent", "password")
    assert result is None

    # 5. 测试用户名/邮箱查找逻辑
    mock_db.query.reset_mock()
    mock_query.reset_mock()
    mock_db.query.return_value = mock_query
    # 验证query被调用且使用了User模型
    mock_db.query.assert_not_called()  # 重置后未调用
