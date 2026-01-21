"""
资产服务单元测试

测试 AssetService 的所有主要方法
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from src.core.exception_handler import (
    BaseBusinessError,
    DuplicateResourceError,
    ResourceNotFoundError,
)
from src.models.asset import Asset
from src.models.auth import User
from src.schemas.asset import AssetCreate, AssetUpdate
from src.services.asset.asset_service import AssetService

TEST_ASSET_ID = "asset_123"
TEST_USER_ID = "user_123"


@pytest.fixture
def mock_db():
    """模拟数据库会话"""
    return MagicMock(spec=Session)


@pytest.fixture
def mock_asset():
    """模拟资产对象"""
    asset = Asset()
    asset.id = TEST_ASSET_ID
    asset.property_name = "测试物业"
    asset.ownership_entity = "权属方A"
    asset.address = "测试地址123"
    asset.ownership_status = "已确权"
    asset.property_nature = "商业"
    asset.usage_status = "在租"
    asset.rentable_area = 100.0
    asset.rented_area = 50.0
    return asset


@pytest.fixture
def mock_user():
    """模拟用户对象"""
    user = User()
    user.id = TEST_USER_ID
    user.username = "testuser"
    return user


@pytest.fixture
def asset_create_dict():
    """资产创建数据"""
    return {
        "ownership_entity": "权属方A",
        "property_name": "新测试物业",
        "address": "新测试地址456",
        "ownership_status": "已确权",
        "property_nature": "商业",
        "usage_status": "空置",
        "rentable_area": 200.0,
        "rented_area": 0.0,
    }


@pytest.fixture
def service(mock_db):
    """创建服务实例"""
    return AssetService(mock_db)


# ============================================================================
# AssetService.get_assets 测试
# ============================================================================
class TestGetAssets:
    """测试获取资产列表"""

    def test_get_assets_default_params(self, service, mock_db):
        """测试使用默认参数获取资产列表"""
        mock_assets = [MagicMock(spec=Asset), MagicMock(spec=Asset)]
        mock_db.total = 2

        with patch(
            "src.crud.asset.asset_crud.get_multi_with_search",
            return_value=(mock_assets, 2),
        ):
            result = service.get_assets()

            assert result == (mock_assets, 2)

    def test_get_assets_with_pagination(self, service, mock_db):
        """测试带分页的资产列表查询"""
        mock_assets = [MagicMock(spec=Asset)]
        mock_db.total = 1

        with patch(
            "src.crud.asset.asset_crud.get_multi_with_search",
            return_value=(mock_assets, 1),
        ) as mock_get:
            result = service.get_assets(skip=10, limit=20)

            assert result == (mock_assets, 1)
            mock_get.assert_called_once_with(
                mock_db,
                skip=10,
                limit=20,
                search=None,
                filters=None,
                sort_field="created_at",
                sort_order="desc",
            )

    def test_get_assets_with_search(self, service, mock_db):
        """测试带搜索的资产列表查询"""
        mock_assets = [MagicMock(spec=Asset)]

        with patch(
            "src.crud.asset.asset_crud.get_multi_with_search",
            return_value=(mock_assets, 1),
        ) as mock_get:
            result = service.get_assets(search="测试物业")

            assert result == (mock_assets, 1)
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args.kwargs
            assert call_kwargs["search"] == "测试物业"

    def test_get_assets_with_filters(self, service, mock_db):
        """测试带筛选的资产列表查询"""
        mock_assets = [MagicMock(spec=Asset)]
        filters = {"property_nature": "商业"}

        with patch(
            "src.crud.asset.asset_crud.get_multi_with_search",
            return_value=(mock_assets, 1),
        ) as mock_get:
            result = service.get_assets(filters=filters)

            assert result == (mock_assets, 1)
            call_kwargs = mock_get.call_args.kwargs
            assert call_kwargs["filters"] == filters

    def test_get_assets_with_sorting(self, service, mock_db):
        """测试带排序的资产列表查询"""
        mock_assets = [MagicMock(spec=Asset)]

        with patch(
            "src.crud.asset.asset_crud.get_multi_with_search",
            return_value=(mock_assets, 1),
        ) as mock_get:
            result = service.get_assets(sort_field="property_name", sort_order="asc")

            assert result == (mock_assets, 1)
            call_kwargs = mock_get.call_args.kwargs
            assert call_kwargs["sort_field"] == "property_name"
            assert call_kwargs["sort_order"] == "asc"

    def test_get_assets_empty_result(self, service, mock_db):
        """测试空结果"""
        with patch(
            "src.crud.asset.asset_crud.get_multi_with_search",
            return_value=([], 0),
        ):
            result = service.get_assets()

            assert result == ([], 0)


# ============================================================================
# AssetService.get_asset 测试
# ============================================================================
class TestGetAsset:
    """测试获取单个资产"""

    def test_get_asset_success(self, service, mock_asset):
        """测试成功获取资产"""
        with patch("src.crud.asset.asset_crud.get", return_value=mock_asset):
            result = service.get_asset(TEST_ASSET_ID)

            assert result.id == TEST_ASSET_ID
            assert result.property_name == "测试物业"

    def test_get_asset_not_found(self, service):
        """测试资产不存在"""
        with patch("src.crud.asset.asset_crud.get", return_value=None):
            with pytest.raises(ResourceNotFoundError) as excinfo:
                service.get_asset(TEST_ASSET_ID)

            assert "Asset" in str(excinfo.value)
            assert TEST_ASSET_ID in str(excinfo.value)


# ============================================================================
# AssetService.create_asset 测试
# ============================================================================
class TestCreateAsset:
    """测试创建资产"""

    def test_create_asset_success(self, service, asset_create_dict, mock_asset):
        """测试成功创建资产"""
        asset_in = AssetCreate(**asset_create_dict)

        # Mock order must match the service's execution order
        with patch(
            "src.services.enum_validation_service.get_enum_validation_service"
        ) as mock_validation:
            mock_validation_service = MagicMock()
            mock_validation_service.validate_asset_data.return_value = (True, [])
            mock_validation.return_value = mock_validation_service

            with patch("src.crud.asset.asset_crud.get_by_name", return_value=None):
                with patch(
                    "src.crud.asset.asset_crud.create_with_history",
                    return_value=mock_asset,
                ) as mock_create:
                    result = service.create_asset(asset_in)

                    assert result == mock_asset
                    mock_create.assert_called_once()

    def test_create_asset_enum_validation_fails(
        self, service, asset_create_dict, mock_enum_validation_service
    ):
        """测试枚举验证失败"""
        # 修改全局 mock 返回验证失败
        original_validate = mock_enum_validation_service.validate_asset_data
        mock_enum_validation_service.validate_asset_data = lambda data: (
            False,
            ["物业性质无效"],
        )

        asset_in = AssetCreate(**asset_create_dict)

        try:
            with pytest.raises(BaseBusinessError) as excinfo:
                service.create_asset(asset_in)

            assert excinfo.value.status_code == 422
            assert "枚举值验证失败" in str(excinfo.value.message)
        finally:
            # 恢复原始 mock
            mock_enum_validation_service.validate_asset_data = original_validate

    def test_create_asset_duplicate_name(self, service, asset_create_dict, mock_asset):
        """测试资产名称重复"""
        asset_in = AssetCreate(**asset_create_dict)

        with patch("src.crud.asset.asset_crud.get_by_name", return_value=mock_asset):
            with pytest.raises(DuplicateResourceError) as excinfo:
                service.create_asset(asset_in)

            assert "Asset" in str(excinfo.value)
            assert "property_name" in str(excinfo.value)

    def test_create_asset_area_validation_fails(self, service, asset_create_dict):
        """测试面积一致性验证失败"""
        # 创建已出租面积大于可出租面积的数据
        invalid_data = asset_create_dict.copy()
        invalid_data["rented_area"] = 300.0  # 大于 rentable_area (200.0)
        asset_in = AssetCreate(**invalid_data)

        with patch(
            "src.services.enum_validation_service.get_enum_validation_service"
        ) as mock_validation:
            mock_validation_service = MagicMock()
            mock_validation_service.validate_asset_data.return_value = (True, [])
            mock_validation.return_value = mock_validation_service

            with patch("src.crud.asset.asset_crud.get_by_name", return_value=None):
                with pytest.raises(BaseBusinessError) as excinfo:
                    service.create_asset(asset_in)

                assert excinfo.value.status_code == 422
                assert "数据验证失败" in str(excinfo.value.message)
                assert "已出租面积不能大于可出租面积" in str(excinfo.value.message)

    def test_create_asset_with_user(self, service, asset_create_dict, mock_asset):
        """测试带用户信息的创建"""
        asset_in = AssetCreate(**asset_create_dict)
        user = MagicMock(spec=User)
        user.id = TEST_USER_ID

        with patch(
            "src.services.enum_validation_service.get_enum_validation_service"
        ) as mock_validation:
            mock_validation_service = MagicMock()
            mock_validation_service.validate_asset_data.return_value = (True, [])
            mock_validation.return_value = mock_validation_service

            with patch("src.crud.asset.asset_crud.get_by_name", return_value=None):
                with patch(
                    "src.crud.asset.asset_crud.create_with_history",
                    return_value=mock_asset,
                ):
                    result = service.create_asset(asset_in, current_user=user)

                    assert result == mock_asset


# ============================================================================
# AssetService.update_asset 测试
# ============================================================================
class TestUpdateAsset:
    """测试更新资产"""

    def test_update_asset_success(self, service, mock_asset):
        """测试成功更新资产"""
        update_data = {
            "notes": "更新备注"
        }  # Use non-name field to avoid duplicate check
        asset_in = AssetUpdate(**update_data)

        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            return_value=mock_asset,
        ):
            with patch(
                "src.services.enum_validation_service.get_enum_validation_service"
            ) as mock_validation:
                mock_validation_service = MagicMock()
                mock_validation_service.validate_asset_data.return_value = (True, [])
                mock_validation.return_value = mock_validation_service

                with patch(
                    "src.crud.asset.asset_crud.update_with_history",
                    return_value=mock_asset,
                ) as mock_update:
                    result = service.update_asset(TEST_ASSET_ID, asset_in)

                    assert result == mock_asset
                    mock_update.assert_called_once()

    def test_update_asset_not_found(self, service):
        """测试更新不存在的资产"""
        update_data = {"property_name": "新名称"}
        asset_in = AssetUpdate(**update_data)

        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            side_effect=ResourceNotFoundError("Asset", TEST_ASSET_ID),
        ):
            with pytest.raises(ResourceNotFoundError):
                service.update_asset(TEST_ASSET_ID, asset_in)

    def test_update_asset_enum_validation_fails(
        self, service, mock_asset, mock_enum_validation_service
    ):
        """测试更新时枚举验证失败"""
        update_data = {"property_nature": "无效性质"}
        asset_in = AssetUpdate(**update_data)

        # 修改全局 mock 返回验证失败
        original_validate = mock_enum_validation_service.validate_asset_data
        mock_enum_validation_service.validate_asset_data = lambda data: (
            False,
            ["物业性质无效"],
        )

        try:
            with patch(
                "src.services.asset.asset_service.AssetService.get_asset",
                return_value=mock_asset,
            ):
                with pytest.raises(BaseBusinessError) as excinfo:
                    service.update_asset(TEST_ASSET_ID, asset_in)

                assert excinfo.value.status_code == 422
                assert "枚举值验证失败" in str(excinfo.value.message)
        finally:
            # 恢复原始 mock
            mock_enum_validation_service.validate_asset_data = original_validate

    def test_update_asset_duplicate_name(self, service, mock_asset):
        """测试更新为重复的名称"""
        update_data = {"property_name": "已存在的物业名称"}
        asset_in = AssetUpdate(**update_data)

        # 创建另一个已存在的资产
        existing_asset = MagicMock(spec=Asset)
        existing_asset.id = "other_asset_id"

        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            return_value=mock_asset,
        ):
            with patch(
                "src.services.enum_validation_service.get_enum_validation_service"
            ) as mock_validation:
                mock_validation_service = MagicMock()
                mock_validation_service.validate_asset_data.return_value = (True, [])
                mock_validation.return_value = mock_validation_service

                with patch(
                    "src.crud.asset.asset_crud.get_by_name",
                    return_value=existing_asset,
                ):
                    with pytest.raises(DuplicateResourceError) as excinfo:
                        service.update_asset(TEST_ASSET_ID, asset_in)

                    assert "Asset" in str(excinfo.value)
                    assert "property_name" in str(excinfo.value)

    def test_update_asset_same_name_allowed(self, service, mock_asset):
        """测试更新为相同名称（允许）"""
        # 使用相同的名称
        update_data = {"property_name": mock_asset.property_name}
        asset_in = AssetUpdate(**update_data)

        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            return_value=mock_asset,
        ):
            with patch(
                "src.services.enum_validation_service.get_enum_validation_service"
            ) as mock_validation:
                mock_validation_service = MagicMock()
                mock_validation_service.validate_asset_data.return_value = (True, [])
                mock_validation.return_value = mock_validation_service

                with patch(
                    "src.crud.asset.asset_crud.update_with_history",
                    return_value=mock_asset,
                ):
                    result = service.update_asset(TEST_ASSET_ID, asset_in)

                    assert result == mock_asset

    def test_update_asset_area_validation_fails(self, service, mock_asset):
        """测试更新时面积一致性验证失败"""
        # 设置当前资产数据
        mock_asset.rentable_area = 100.0
        mock_asset.rented_area = 50.0

        # 尝试更新为无效的面积数据
        update_data = {"rented_area": 150.0}  # 大于 rentable_area
        asset_in = AssetUpdate(**update_data)

        # Mock get_asset to return the mock_asset with proper attributes
        with patch.object(service, "get_asset", return_value=mock_asset):
            # Mock the calculator to return validation errors
            with patch(
                "src.services.asset.asset_service.AssetCalculator.validate_area_consistency",
                return_value=["已出租面积不能大于可出租面积"],
            ):
                with pytest.raises(BaseBusinessError) as excinfo:
                    service.update_asset(TEST_ASSET_ID, asset_in)

                assert excinfo.value.status_code == 422
                assert "数据验证失败" in str(excinfo.value.message)

    def test_update_asset_with_user(self, service, mock_asset, mock_user):
        """测试带用户信息的更新"""
        update_data = {"notes": "更新备注"}
        asset_in = AssetUpdate(**update_data)

        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            return_value=mock_asset,
        ):
            with patch(
                "src.services.enum_validation_service.get_enum_validation_service"
            ) as mock_validation:
                mock_validation_service = MagicMock()
                mock_validation_service.validate_asset_data.return_value = (True, [])
                mock_validation.return_value = mock_validation_service

                with patch(
                    "src.crud.asset.asset_crud.update_with_history",
                    return_value=mock_asset,
                ):
                    result = service.update_asset(
                        TEST_ASSET_ID, asset_in, current_user=mock_user
                    )

                    assert result == mock_asset

    def test_update_asset_partial_fields(self, service, mock_asset):
        """测试部分字段更新"""
        # 只更新一个字段
        update_data = {"notes": "新的备注"}
        asset_in = AssetUpdate(**update_data)

        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            return_value=mock_asset,
        ):
            with patch(
                "src.services.enum_validation_service.get_enum_validation_service"
            ) as mock_validation:
                mock_validation_service = MagicMock()
                mock_validation_service.validate_asset_data.return_value = (True, [])
                mock_validation.return_value = mock_validation_service

                with patch(
                    "src.crud.asset.asset_crud.update_with_history",
                    return_value=mock_asset,
                ) as mock_update:
                    result = service.update_asset(TEST_ASSET_ID, asset_in)

                    assert result == mock_asset
                    # 验证只传入了部分字段
                    call_args = mock_update.call_args
                    update_obj = call_args.kwargs.get("obj_in")
                    assert update_obj is not None


# ============================================================================
# AssetService.delete_asset 测试
# ============================================================================
class TestDeleteAsset:
    """测试删除资产"""

    def test_delete_asset_success(self, service, mock_asset):
        """测试成功删除资产"""
        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            return_value=mock_asset,
        ):
            with patch("src.crud.asset.asset_crud.remove") as mock_remove:
                service.delete_asset(TEST_ASSET_ID)

                mock_remove.assert_called_once_with(db=service.db, id=TEST_ASSET_ID)

    def test_delete_asset_not_found(self, service):
        """测试删除不存在的资产"""
        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            side_effect=ResourceNotFoundError("Asset", TEST_ASSET_ID),
        ):
            with pytest.raises(ResourceNotFoundError):
                service.delete_asset(TEST_ASSET_ID)

    def test_delete_asset_with_user(self, service, mock_asset, mock_user):
        """测试带用户信息的删除"""
        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            return_value=mock_asset,
        ):
            with patch("src.crud.asset.asset_crud.remove") as mock_remove:
                service.delete_asset(TEST_ASSET_ID, current_user=mock_user)

                mock_remove.assert_called_once_with(db=service.db, id=TEST_ASSET_ID)


# ============================================================================
# 边界情况和综合测试
# ============================================================================
class TestEdgeCases:
    """测试边界情况"""

    def test_create_asset_with_all_fields(self, service, mock_asset):
        """测试创建包含所有字段的资产"""
        complete_data = {
            "ownership_entity": "权属方A",
            "ownership_category": "国有",
            "project_name": "测试项目",
            "property_name": "完整物业",
            "address": "完整地址123号",
            "ownership_status": "已确权",
            "property_nature": "商业",
            "usage_status": "在租",
            "business_category": "零售",
            "is_litigated": False,
            "notes": "测试备注",
            "land_area": 1000.0,
            "actual_property_area": 800.0,
            "rentable_area": 600.0,
            "rented_area": 400.0,
            "non_commercial_area": 100.0,
            "include_in_occupancy_rate": True,
            "certificated_usage": "商业",
            "actual_usage": "零售",
            "tenant_name": "租户A",
            "tenant_type": "企业",
            "lease_contract_number": "CONTRACT001",
            "contract_start_date": "2024-01-01",
            "contract_end_date": "2025-12-31",
            "monthly_rent": 10000.0,
            "deposit": 20000.0,
            "is_sublease": False,
            "manager_name": "管理员A",
            "business_model": "自营",
            "operation_status": "正常",
            "data_status": "正常",
        }

        asset_in = AssetCreate(**complete_data)

        with patch(
            "src.services.enum_validation_service.get_enum_validation_service"
        ) as mock_validation:
            mock_validation_service = MagicMock()
            mock_validation_service.validate_asset_data.return_value = (True, [])
            mock_validation.return_value = mock_validation_service

            with patch("src.crud.asset.asset_crud.get_by_name", return_value=None):
                with patch(
                    "src.crud.asset.asset_crud.create_with_history",
                    return_value=mock_asset,
                ):
                    result = service.create_asset(asset_in)

                    assert result == mock_asset

    def test_update_multiple_assets_concurrent(self, service, mock_asset):
        """测试并发更新多个资产（模拟）"""
        update_data = {"notes": "并发更新"}
        asset_in = AssetUpdate(**update_data)

        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            return_value=mock_asset,
        ):
            with patch(
                "src.services.enum_validation_service.get_enum_validation_service"
            ) as mock_validation:
                mock_validation_service = MagicMock()
                mock_validation_service.validate_asset_data.return_value = (True, [])
                mock_validation.return_value = mock_validation_service

                with patch(
                    "src.crud.asset.asset_crud.update_with_history",
                    return_value=mock_asset,
                ):
                    # 模拟多次更新
                    for i in range(3):
                        result = service.update_asset(f"asset_{i}", asset_in)
                        assert result == mock_asset

    def test_get_assets_with_combined_filters(self, service):
        """测试组合筛选条件"""
        mock_assets = [MagicMock(spec=Asset)]

        with patch(
            "src.crud.asset.asset_crud.get_multi_with_search",
            return_value=(mock_assets, 1),
        ) as mock_get:
            filters = {
                "property_nature": "商业",
                "usage_status": "在租",
                "ownership_entity": "权属方A",
            }
            result = service.get_assets(
                search="测试", filters=filters, skip=0, limit=10
            )

            assert result == (mock_assets, 1)
            call_kwargs = mock_get.call_args.kwargs
            assert call_kwargs["search"] == "测试"
            assert call_kwargs["filters"] == filters
            assert call_kwargs["skip"] == 0
            assert call_kwargs["limit"] == 10

    def test_update_asset_no_changes(self, service, mock_asset):
        """测试空更新（没有实际变化）"""
        asset_in = AssetUpdate()

        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            return_value=mock_asset,
        ):
            with patch(
                "src.services.enum_validation_service.get_enum_validation_service"
            ) as mock_validation:
                mock_validation_service = MagicMock()
                # 空数据应该验证通过
                mock_validation_service.validate_asset_data.return_value = (True, [])
                mock_validation.return_value = mock_validation_service

                with patch(
                    "src.crud.asset.asset_crud.update_with_history",
                    return_value=mock_asset,
                ):
                    result = service.update_asset(TEST_ASSET_ID, asset_in)

                    assert result == mock_asset
