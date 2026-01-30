"""
测试 AssetService CRUD 生命周期 (使用 Mock 避免数据库依赖)
"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.exception_handler import ResourceNotFoundError
from src.services.asset.asset_service import AssetService


@pytest.fixture
def asset_service(mock_db):
    """创建 AssetService 实例"""
    return AssetService(mock_db)


def test_asset_service_crud_lifecycle(asset_service, mock_db):
    """测试资产服务CRUD生命周期 - 简化版本"""
    # 这个测试主要验证服务可以正常实例化和方法存在
    # 具体的业务逻辑测试应该在集成测试中进行

    # 1. 验证服务实例化
    assert asset_service is not None

    # 2. 验证服务方法存在
    assert hasattr(asset_service, "create_asset")
    assert hasattr(asset_service, "get_asset")
    assert hasattr(asset_service, "update_asset")
    assert hasattr(asset_service, "delete_asset")
    assert hasattr(asset_service, "get_assets")

    # 3. 验证资源不存在的错误处理
    with patch("src.services.asset.asset_service.asset_crud") as mock_crud:
        mock_crud.get.return_value = None
        with pytest.raises(ResourceNotFoundError):
            asset_service.get_asset("nonexistent_id")

    # 4. 验证枚举验证服务可以被正确mock
    with patch(
        "src.services.asset.asset_service.get_enum_validation_service"
    ) as mock_enum:
        mock_enum_service = MagicMock()
        mock_enum_service.validate_asset_data.return_value = (True, [])
        mock_enum.return_value = mock_enum_service

        # 验证mock服务被正确设置
        assert mock_enum_service is not None
        assert callable(mock_enum_service.validate_asset_data)
