"""
Unit test configuration and fixtures
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture(autouse=True)
def mock_enum_validation_service():
    """
    自动 mock EnumValidationService 用于所有测试

    这个 fixture 会自动应用到所有测试，避免在每个测试中单独 mock。
    它返回常见枚举值，使测试可以正常通过验证。
    """
    mock_service = MagicMock()

    # Mock get_valid_values 方法返回常见枚举值
    def mock_get_valid_values(enum_type_code: str) -> list[str]:
        # 定义常见的枚举值映射
        enum_values = {
            # 资产相关枚举
            'ownership_status': ['已确权', '未确权', '确权中'],
            'property_nature': ['商业', '住宅', '工业', '办公', '综合'],
            'usage_status': ['在租', '空置', '自用', '装修中'],
            'data_status': ['正常', '冻结', '已删除'],
            'business_model': ['自持', '租赁', '混合'],
            'operation_status': ['运营中', '停业', '筹备中'],
            'tenant_type': ['企业', '个人', '政府', '事业单位'],
            'business_category': ['零售', '餐饮', '办公', '仓储'],
            # 角色权限相关枚举
            'role_type': ['系统角色', '自定义角色'],
            'permission_type': ['菜单权限', '按钮权限', '数据权限'],
        }
        return enum_values.get(enum_type_code, ['test_value'])

    # Mock 方法 (注意: 这些是实例方法，不需要 self 参数)
    mock_service.validate_field_value = lambda table, field, value: True
    mock_service.validate_asset_data = lambda data: (True, [])

    # Patch EnumValidationService 在所有模块中的使用
    with patch('src.services.enum_validation_service.EnumValidationService', return_value=mock_service):
        with patch('src.services.enum_validation_service.get_enum_validation_service', return_value=mock_service):
            yield mock_service


@pytest.fixture
def client(monkeypatch):
    """Create a test client for unit tests with authentication bypassed"""
    from src.database import get_db
    from src.main import app
    from src.middleware.auth import get_current_active_user, require_permission

    # Mock authenticated user
    mock_user = MagicMock()
    mock_user.id = "test_user_001"
    mock_user.username = "testuser"
    mock_user.email = "test@example.com"
    mock_user.role = "admin"
    mock_user.is_active = True

    # Use monkeypatch to replace functions at module level
    def mock_get_current_user():
        return mock_user

    def mock_require_permission(resource, action):
        def dependency():
            return mock_user

        return dependency

    monkeypatch.setattr(
        "src.middleware.auth.get_current_active_user", mock_get_current_user
    )
    monkeypatch.setattr(
        "src.middleware.auth.require_permission", mock_require_permission
    )

    # Override dependencies in FastAPI app
    app.dependency_overrides[get_current_active_user] = mock_get_current_user
    app.dependency_overrides[require_permission] = mock_require_permission

    # Mock database session
    def mock_get_db():
        db = MagicMock(spec=Session)
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = mock_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user():
    """Mock admin user for testing admin-only endpoints"""
    mock_user = MagicMock()
    mock_user.id = "admin_001"
    mock_user.username = "admin"
    mock_user.email = "admin@example.com"
    mock_user.role = "admin"
    mock_user.is_active = True
    return mock_user


@pytest.fixture
def normal_user():
    """Mock normal user for testing permission checks"""
    mock_user = MagicMock()
    mock_user.id = "user_001"
    mock_user.username = "testuser"
    mock_user.email = "user@example.com"
    mock_user.role = "user"
    mock_user.is_active = True
    return mock_user


@pytest.fixture
def unauthenticated_client():
    """Create a test client without authentication for testing unauthorized access"""
    from fastapi.testclient import TestClient

    from src.main import app

    # Return client without auth headers
    return TestClient(app)
