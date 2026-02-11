"""
资产服务单元测试

测试 AssetService 的所有主要方法
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import (
    BaseBusinessError,
    DuplicateResourceError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from src.crud.query_builder import TenantFilter
from src.models.asset import Asset
from src.models.auth import User
from src.schemas.asset import AssetCreate, AssetUpdate
from src.services.asset.asset_service import AssetService

TEST_ASSET_ID = "asset_123"
TEST_USER_ID = "user_123"

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db():
    """Mock AsyncSession for async AssetService tests."""
    db = MagicMock()
    ownership = MagicMock()
    ownership.id = "ownership-id"
    ownership.name = "权属方A"
    execute_result = MagicMock()
    execute_scalars = MagicMock()
    execute_scalars.first.return_value = ownership
    execute_result.scalars.return_value = execute_scalars

    db.in_transaction.return_value = True
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock(return_value=execute_result)
    db.add = MagicMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def mock_asset():
    """模拟资产对象"""
    asset = Asset()
    asset.id = TEST_ASSET_ID
    asset.property_name = "测试物业"
    asset.ownership_id = "ownership-id"
    ownership = MagicMock()
    ownership.name = "权属方A"
    asset.ownership = ownership
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
        "ownership_id": "ownership-id",
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

    async def test_get_assets_default_params(self, service, mock_db):
        """测试使用默认参数获取资产列表"""
        mock_assets = [MagicMock(spec=Asset), MagicMock(spec=Asset)]
        mock_db.total = 2

        with patch(
            "src.crud.asset.asset_crud.get_multi_with_search_async",
            new_callable=AsyncMock,
            return_value=(mock_assets, 2),
        ):
            result = await service.get_assets()

            assert result == (mock_assets, 2)

    async def test_get_assets_with_pagination(self, service, mock_db):
        """测试带分页的资产列表查询"""
        mock_assets = [MagicMock(spec=Asset)]
        mock_db.total = 1

        with patch(
            "src.crud.asset.asset_crud.get_multi_with_search_async",
            new_callable=AsyncMock,
            return_value=(mock_assets, 1),
        ) as mock_get:
            result = await service.get_assets(skip=10, limit=20)

            assert result == (mock_assets, 1)
            mock_get.assert_awaited_once_with(
                mock_db,
                skip=10,
                limit=20,
                search=None,
                filters=None,
                sort_field="created_at",
                sort_order="desc",
                include_relations=False,
            )

    async def test_get_assets_with_search(self, service, mock_db):
        """测试带搜索的资产列表查询"""
        mock_assets = [MagicMock(spec=Asset)]

        with patch(
            "src.crud.asset.asset_crud.get_multi_with_search_async",
            new_callable=AsyncMock,
            return_value=(mock_assets, 1),
        ) as mock_get:
            result = await service.get_assets(search="测试物业")

            assert result == (mock_assets, 1)
            mock_get.assert_awaited_once()
            call_kwargs = mock_get.call_args.kwargs
            assert call_kwargs["search"] == "测试物业"

    async def test_get_assets_with_filters(self, service, mock_db):
        """测试带筛选的资产列表查询"""
        mock_assets = [MagicMock(spec=Asset)]
        filters = {"property_nature": "商业"}

        with patch(
            "src.crud.asset.asset_crud.get_multi_with_search_async",
            new_callable=AsyncMock,
            return_value=(mock_assets, 1),
        ) as mock_get:
            result = await service.get_assets(filters=filters)

            assert result == (mock_assets, 1)
            call_kwargs = mock_get.call_args.kwargs
            assert call_kwargs["filters"] == filters

    async def test_get_assets_with_sorting(self, service, mock_db):
        """测试带排序的资产列表查询"""
        mock_assets = [MagicMock(spec=Asset)]

        with patch(
            "src.crud.asset.asset_crud.get_multi_with_search_async",
            new_callable=AsyncMock,
            return_value=(mock_assets, 1),
        ) as mock_get:
            result = await service.get_assets(sort_field="property_name", sort_order="asc")

            assert result == (mock_assets, 1)
            call_kwargs = mock_get.call_args.kwargs
            assert call_kwargs["sort_field"] == "property_name"
            assert call_kwargs["sort_order"] == "asc"

    async def test_get_assets_with_include_relations(self, service, mock_db):
        """测试显式加载关联数据"""
        mock_assets = [MagicMock(spec=Asset)]

        with patch(
            "src.crud.asset.asset_crud.get_multi_with_search_async",
            new_callable=AsyncMock,
            return_value=(mock_assets, 1),
        ) as mock_get:
            result = await service.get_assets(include_relations=True)

            assert result == (mock_assets, 1)
            call_kwargs = mock_get.call_args.kwargs
            assert call_kwargs["include_relations"] is True

    async def test_get_assets_empty_result(self, service, mock_db):
        """测试空结果"""
        with patch(
            "src.crud.asset.asset_crud.get_multi_with_search_async",
            new_callable=AsyncMock,
            return_value=([], 0),
        ):
            result = await service.get_assets()

            assert result == ([], 0)

    async def test_get_assets_with_current_user_resolves_tenant_filter(
        self, service, mock_db
    ):
        """测试 get_assets 按当前用户自动解析 tenant_filter 并透传"""
        mock_assets = [MagicMock(spec=Asset)]
        tenant_filter = TenantFilter(organization_ids=["org-1", "org-2"])

        with (
            patch.object(
                service,
                "_resolve_tenant_filter",
                new=AsyncMock(return_value=tenant_filter),
            ) as mock_resolve,
            patch(
                "src.crud.asset.asset_crud.get_multi_with_search_async",
                new_callable=AsyncMock,
                return_value=(mock_assets, 2),
            ) as mock_get,
        ):
            result = await service.get_assets(current_user_id="user-1")

        assert result == (mock_assets, 2)
        mock_resolve.assert_awaited_once_with(
            current_user_id="user-1",
            tenant_filter=None,
        )
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["tenant_filter"] == tenant_filter


class TestTenantFilterResolution:
    async def test_resolve_tenant_filter_returns_org_ids(self, service):
        """测试可访问组织列表会被转换为 TenantFilter"""
        mock_org_service = MagicMock()
        mock_org_service.get_user_accessible_organizations = AsyncMock(
            return_value=["org-1", "org-2"]
        )
        with patch(
            "src.services.organization_permission_service.OrganizationPermissionService",
            return_value=mock_org_service,
        ):
            tenant_filter = await service._resolve_tenant_filter(
                current_user_id="user-1"
            )

        assert tenant_filter is not None
        assert tenant_filter.organization_ids == ["org-1", "org-2"]

    async def test_resolve_tenant_filter_fail_closed_on_exception(self, service):
        """测试 tenant_filter 解析失败时走失败关闭策略"""
        with patch(
            "src.services.organization_permission_service.OrganizationPermissionService",
            side_effect=RuntimeError("boom"),
        ):
            tenant_filter = await service._resolve_tenant_filter(
                current_user_id="user-1"
            )

        assert tenant_filter is not None
        assert tenant_filter.organization_ids == []


class TestBuildFilters:
    async def test_build_filters_includes_occupancy_rate_range(self) -> None:
        filters = AssetService.build_filters(
            min_occupancy_rate=25.5,
            max_occupancy_rate=90.0,
        )

        assert filters is not None
        assert filters["min_occupancy_rate"] == 25.5
        assert filters["max_occupancy_rate"] == 90.0

    async def test_build_filters_returns_none_when_empty(self) -> None:
        assert AssetService.build_filters() is None

    async def test_build_filters_normalizes_is_litigated_bool(self) -> None:
        filters = AssetService.build_filters(is_litigated=True)
        assert filters is not None
        assert filters["is_litigated"] is True

    async def test_build_filters_normalizes_is_litigated_chinese(self) -> None:
        filters = AssetService.build_filters(is_litigated="否")
        assert filters is not None
        assert filters["is_litigated"] is False

    async def test_build_filters_includes_management_entity(self) -> None:
        filters = AssetService.build_filters(management_entity="管理方A")
        assert filters is not None
        assert filters["management_entity"] == "管理方A"

    async def test_build_filters_rejects_invalid_is_litigated(self) -> None:
        with pytest.raises(BaseBusinessError) as exc_info:
            AssetService.build_filters(is_litigated="maybe")

        assert exc_info.value.status_code == 422
        assert "is_litigated" in str(exc_info.value.message)


# ============================================================================
# AssetService.get_asset 测试
# ============================================================================
class TestGetAsset:
    """测试获取单个资产"""

    async def test_get_asset_success(self, service, mock_asset):
        """测试成功获取资产"""
        with patch("src.crud.asset.asset_crud.get_async", new_callable=AsyncMock, return_value=mock_asset):
            result = await service.get_asset(TEST_ASSET_ID)

            assert result.id == TEST_ASSET_ID
            assert result.property_name == "测试物业"

    async def test_get_asset_not_found(self, service):
        """测试资产不存在"""
        with patch("src.crud.asset.asset_crud.get_async", new_callable=AsyncMock, return_value=None):
            with pytest.raises(ResourceNotFoundError) as excinfo:
                await service.get_asset(TEST_ASSET_ID)

            assert "Asset" in str(excinfo.value)
            assert TEST_ASSET_ID in str(excinfo.value)

    async def test_get_asset_deleted(self, service, mock_asset):
        """测试资产已删除"""
        mock_asset.data_status = "已删除"
        with patch("src.crud.asset.asset_crud.get_async", new_callable=AsyncMock, return_value=mock_asset):
            with pytest.raises(ResourceNotFoundError):
                await service.get_asset(TEST_ASSET_ID)

    async def test_get_asset_with_current_user_resolves_tenant_filter(
        self, service, mock_asset
    ) -> None:
        tenant_filter = TenantFilter(organization_ids=["org-1"])

        with (
            patch.object(
                service,
                "_resolve_tenant_filter",
                new=AsyncMock(return_value=tenant_filter),
            ) as mock_resolve,
            patch(
                "src.crud.asset.asset_crud.get_async",
                new_callable=AsyncMock,
                return_value=mock_asset,
            ) as mock_get_async,
        ):
            result = await service.get_asset(
                TEST_ASSET_ID,
                current_user_id="user-1",
            )

        assert result == mock_asset
        mock_resolve.assert_awaited_once_with(
            current_user_id="user-1",
            tenant_filter=None,
        )
        mock_get_async.assert_awaited_once_with(
            db=service.db,
            id=TEST_ASSET_ID,
            use_cache=True,
            tenant_filter=tenant_filter,
        )

    async def test_get_asset_fail_closed_when_no_accessible_org(self, service) -> None:
        with patch.object(
            service,
            "_resolve_tenant_filter",
            new=AsyncMock(return_value=TenantFilter(organization_ids=[])),
        ):
            with patch(
                "src.crud.asset.asset_crud.get_async",
                new_callable=AsyncMock,
            ) as mock_get_async:
                with pytest.raises(ResourceNotFoundError):
                    await service.get_asset(
                        TEST_ASSET_ID,
                        current_user_id="user-1",
                    )

        mock_get_async.assert_not_awaited()


class TestGetAssetHistoryRecords:
    async def test_get_asset_history_records_success(self, service) -> None:
        history_records = [MagicMock(id="history-1")]

        with patch.object(service, "get_asset", new_callable=AsyncMock) as mock_get_asset:
            with patch(
                "src.services.asset.asset_service.history_crud.get_by_asset_id_async",
                new_callable=AsyncMock,
                return_value=history_records,
            ) as mock_get_history:
                result = await service.get_asset_history_records(TEST_ASSET_ID)

        assert result == history_records
        mock_get_asset.assert_awaited_once_with(
            TEST_ASSET_ID,
            tenant_filter=None,
            current_user_id=None,
        )
        mock_get_history.assert_awaited_once_with(service.db, asset_id=TEST_ASSET_ID)


class TestGetOwnershipEntityNames:
    async def test_get_ownership_entity_names_success(self, service, mock_db) -> None:
        execute_result = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = ["权属方A", "权属方B", None]
        execute_result.scalars.return_value = scalars
        mock_db.execute = AsyncMock(return_value=execute_result)

        result = await service.get_ownership_entity_names()

        assert result == ["权属方A", "权属方B"]
        mock_db.execute.assert_awaited_once()

    async def test_get_ownership_entity_names_empty(self, service, mock_db) -> None:
        execute_result = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = []
        execute_result.scalars.return_value = scalars
        mock_db.execute = AsyncMock(return_value=execute_result)

        result = await service.get_ownership_entity_names()

        assert result == []
        mock_db.execute.assert_awaited_once()


class TestOwnershipResolution:
    async def test_resolve_ownership_uses_crud_get(self, service):
        with patch(
            "src.services.asset.asset_service.ownership.get",
            new_callable=AsyncMock,
            return_value=MagicMock(id="ownership-id"),
        ) as mock_get:
            result = await service._resolve_ownership({"ownership_id": "ownership-id"})

        assert result["ownership_id"] == "ownership-id"
        mock_get.assert_awaited_once_with(service.db, id="ownership-id")


# ============================================================================
# AssetService.create_asset 测试
# ============================================================================
class TestCreateAsset:
    """测试创建资产"""

    async def test_create_asset_success(self, service, asset_create_dict, mock_asset):
        """测试成功创建资产"""
        asset_in = AssetCreate(**asset_create_dict)

        # Mock order must match the service's execution order
        with patch(
            "src.services.asset.asset_service.get_enum_validation_service_async"
        ) as mock_validation:
            mock_validation_service = MagicMock()
            mock_validation_service.validate_asset_data = AsyncMock()
            mock_validation_service.validate_asset_data.return_value = (True, [])
            mock_validation.return_value = mock_validation_service

            with patch("src.crud.asset.asset_crud.get_by_name_async", new_callable=AsyncMock, return_value=None):
                with patch(
                    "src.crud.asset.asset_crud.create_with_history_async",
            new_callable=AsyncMock,
            return_value=mock_asset,
                ) as mock_create:
                    result = await service.create_asset(asset_in)

                    assert result == mock_asset
                    mock_create.assert_awaited_once()

    async def test_create_asset_enum_validation_fails(self, service, asset_create_dict):
        """测试枚举验证失败"""
        asset_in = AssetCreate(**asset_create_dict)

        with patch(
            "src.services.asset.asset_service.get_enum_validation_service_async"
        ) as mock_validation:
            mock_validation_service = MagicMock()
            mock_validation_service.validate_asset_data = AsyncMock()
            mock_validation_service.validate_asset_data.return_value = (
                False,
                ["物业性质无效"],
            )
            mock_validation.return_value = mock_validation_service

            with pytest.raises(BaseBusinessError) as excinfo:
                await service.create_asset(asset_in)

            assert excinfo.value.status_code == 422
            assert "枚举值验证失败" in str(excinfo.value.message)

    async def test_create_asset_duplicate_name(self, service, asset_create_dict, mock_asset):
        """测试资产名称重复"""
        asset_in = AssetCreate(**asset_create_dict)

        with patch(
            "src.services.asset.asset_service.get_enum_validation_service_async"
        ) as mock_validation:
            mock_validation_service = MagicMock()
            mock_validation_service.validate_asset_data = AsyncMock()
            mock_validation_service.validate_asset_data.return_value = (True, [])
            mock_validation.return_value = mock_validation_service

            with patch(
                "src.crud.asset.asset_crud.get_by_name_async",
                new_callable=AsyncMock,
                return_value=mock_asset,
            ):
                with pytest.raises(DuplicateResourceError) as excinfo:
                    await service.create_asset(asset_in)

                assert "Asset" in str(excinfo.value)
                assert "property_name" in str(excinfo.value)

    async def test_create_asset_area_validation_fails(self, service, asset_create_dict):
        """测试面积一致性验证失败"""
        # 创建已出租面积大于可出租面积的数据
        invalid_data = asset_create_dict.copy()
        invalid_data["rented_area"] = 300.0  # 大于 rentable_area (200.0)
        asset_in = AssetCreate(**invalid_data)

        with patch(
            "src.services.asset.asset_service.get_enum_validation_service_async"
        ) as mock_validation:
            mock_validation_service = MagicMock()
            mock_validation_service.validate_asset_data = AsyncMock()
            mock_validation_service.validate_asset_data.return_value = (True, [])
            mock_validation.return_value = mock_validation_service

            with patch("src.crud.asset.asset_crud.get_by_name_async", new_callable=AsyncMock, return_value=None):
                with pytest.raises(BaseBusinessError) as excinfo:
                    await service.create_asset(asset_in)

                assert excinfo.value.status_code == 422
                assert "数据验证失败" in str(excinfo.value.message)
                assert "已出租面积不能大于可出租面积" in str(excinfo.value.message)

    async def test_create_asset_with_user(self, service, asset_create_dict, mock_asset):
        """测试带用户信息的创建"""
        asset_in = AssetCreate(**asset_create_dict)
        user = MagicMock(spec=User)
        user.id = TEST_USER_ID

        with patch(
            "src.services.asset.asset_service.get_enum_validation_service_async"
        ) as mock_validation:
            mock_validation_service = MagicMock()
            mock_validation_service.validate_asset_data = AsyncMock()
            mock_validation_service.validate_asset_data.return_value = (True, [])
            mock_validation.return_value = mock_validation_service

            with patch("src.crud.asset.asset_crud.get_by_name_async", new_callable=AsyncMock, return_value=None):
                with patch(
                    "src.crud.asset.asset_crud.create_with_history_async",
            new_callable=AsyncMock,
            return_value=mock_asset,
                ):
                    result = await service.create_asset(asset_in, current_user=user)

                    assert result == mock_asset


# ============================================================================
# AssetService.update_asset 测试
# ============================================================================
class TestUpdateAsset:
    """测试更新资产"""

    async def test_update_asset_success(self, service, mock_asset):
        """测试成功更新资产"""
        update_data = {
            "notes": "更新备注"
        }  # Use non-name field to avoid duplicate check
        asset_in = AssetUpdate(**update_data)

        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            new_callable=AsyncMock,
            return_value=mock_asset,
        ):
            with patch(
                "src.services.asset.asset_service.get_enum_validation_service_async"
            ) as mock_validation:
                mock_validation_service = MagicMock()
                mock_validation_service.validate_asset_data = AsyncMock()
                mock_validation_service.validate_asset_data.return_value = (True, [])
                mock_validation.return_value = mock_validation_service

                with patch(
                    "src.crud.asset.asset_crud.update_with_history_async",
            new_callable=AsyncMock,
            return_value=mock_asset,
                ) as mock_update:
                    result = await service.update_asset(TEST_ASSET_ID, asset_in)

                    assert result == mock_asset
                    mock_update.assert_awaited_once()

    async def test_update_asset_version_conflict(self, service, mock_asset):
        """测试版本冲突"""
        mock_asset.version = 2
        update_data = {"version": 1, "notes": "更新备注"}
        asset_in = AssetUpdate(**update_data)

        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            new_callable=AsyncMock,
            return_value=mock_asset,
        ):
            with patch(
                "src.services.asset.asset_service.get_enum_validation_service_async"
            ) as mock_validation:
                mock_validation_service = MagicMock()
                mock_validation_service.validate_asset_data = AsyncMock()
                mock_validation_service.validate_asset_data.return_value = (True, [])
                mock_validation.return_value = mock_validation_service

                with pytest.raises(BaseBusinessError) as excinfo:
                    await service.update_asset(TEST_ASSET_ID, asset_in)

                assert excinfo.value.status_code == 409
                assert "版本冲突" in str(excinfo.value.message)

    async def test_update_asset_not_found(self, service):
        """测试更新不存在的资产"""
        update_data = {"property_name": "新名称"}
        asset_in = AssetUpdate(**update_data)

        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            new_callable=AsyncMock,
            side_effect=ResourceNotFoundError("Asset", TEST_ASSET_ID),
        ):
            with pytest.raises(ResourceNotFoundError):
                await service.update_asset(TEST_ASSET_ID, asset_in)

    async def test_update_asset_enum_validation_fails(self, service, mock_asset):
        """测试更新时枚举验证失败"""
        update_data = {"property_nature": "无效性质"}
        asset_in = AssetUpdate(**update_data)

        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            new_callable=AsyncMock,
            return_value=mock_asset,
        ):
            with patch(
                "src.services.asset.asset_service.get_enum_validation_service_async"
            ) as mock_validation:
                mock_validation_service = MagicMock()
                mock_validation_service.validate_asset_data = AsyncMock()
                mock_validation_service.validate_asset_data.return_value = (
                    False,
                    ["物业性质无效"],
                )
                mock_validation.return_value = mock_validation_service

                with pytest.raises(BaseBusinessError) as excinfo:
                    await service.update_asset(TEST_ASSET_ID, asset_in)

                assert excinfo.value.status_code == 422
                assert "枚举值验证失败" in str(excinfo.value.message)

    async def test_update_asset_duplicate_name(self, service, mock_asset):
        """测试更新为重复的名称"""
        update_data = {"property_name": "已存在的物业名称"}
        asset_in = AssetUpdate(**update_data)

        # 创建另一个已存在的资产
        existing_asset = MagicMock(spec=Asset)
        existing_asset.id = "other_asset_id"

        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            new_callable=AsyncMock,
            return_value=mock_asset,
        ):
            with patch(
                "src.services.asset.asset_service.get_enum_validation_service_async"
            ) as mock_validation:
                mock_validation_service = MagicMock()
                mock_validation_service.validate_asset_data = AsyncMock()
                mock_validation_service.validate_asset_data.return_value = (True, [])
                mock_validation.return_value = mock_validation_service

                with patch(
                    "src.crud.asset.asset_crud.get_by_name_async",
                    new_callable=AsyncMock,
                    return_value=existing_asset,
                ):
                    with pytest.raises(DuplicateResourceError) as excinfo:
                        await service.update_asset(TEST_ASSET_ID, asset_in)

                    assert "Asset" in str(excinfo.value)
                    assert "property_name" in str(excinfo.value)

    async def test_update_asset_same_name_allowed(self, service, mock_asset):
        """测试更新为相同名称（允许）"""
        # 使用相同的名称
        update_data = {"property_name": mock_asset.property_name}
        asset_in = AssetUpdate(**update_data)

        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            new_callable=AsyncMock,
            return_value=mock_asset,
        ):
            with patch(
                "src.services.asset.asset_service.get_enum_validation_service_async"
            ) as mock_validation:
                mock_validation_service = MagicMock()
                mock_validation_service.validate_asset_data = AsyncMock()
                mock_validation_service.validate_asset_data.return_value = (True, [])
                mock_validation.return_value = mock_validation_service

                with patch(
                    "src.crud.asset.asset_crud.update_with_history_async",
            new_callable=AsyncMock,
            return_value=mock_asset,
                ):
                    result = await service.update_asset(TEST_ASSET_ID, asset_in)

                    assert result == mock_asset

    async def test_update_asset_area_validation_fails(self, service, mock_asset):
        """测试更新时面积一致性验证失败"""
        # 设置当前资产数据
        mock_asset.rentable_area = 100.0
        mock_asset.rented_area = 50.0

        # 尝试更新为无效的面积数据
        update_data = {"rented_area": 150.0}  # 大于 rentable_area
        asset_in = AssetUpdate(**update_data)

        # Mock get_asset to return the mock_asset with proper attributes
        with patch.object(service, "get_asset", new=AsyncMock(return_value=mock_asset)):
            # Mock the calculator to return validation errors
            with patch(
                "src.services.asset.asset_service.AssetCalculator.validate_area_consistency",
                return_value=["已出租面积不能大于可出租面积"],
            ):
                with pytest.raises(BaseBusinessError) as excinfo:
                    await service.update_asset(TEST_ASSET_ID, asset_in)

                assert excinfo.value.status_code == 422
                assert "数据验证失败" in str(excinfo.value.message)

    async def test_update_asset_with_user(self, service, mock_asset, mock_user):
        """测试带用户信息的更新"""
        update_data = {"notes": "更新备注"}
        asset_in = AssetUpdate(**update_data)

        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            new_callable=AsyncMock,
            return_value=mock_asset,
        ):
            with patch(
                "src.services.asset.asset_service.get_enum_validation_service_async"
            ) as mock_validation:
                mock_validation_service = MagicMock()
                mock_validation_service.validate_asset_data = AsyncMock()
                mock_validation_service.validate_asset_data.return_value = (True, [])
                mock_validation.return_value = mock_validation_service

                with patch(
                    "src.crud.asset.asset_crud.update_with_history_async",
            new_callable=AsyncMock,
            return_value=mock_asset,
                ):
                    result = await service.update_asset(
                        TEST_ASSET_ID, asset_in, current_user=mock_user
                    )

                    assert result == mock_asset

    async def test_update_asset_partial_fields(self, service, mock_asset):
        """测试部分字段更新"""
        # 只更新一个字段
        update_data = {"notes": "新的备注"}
        asset_in = AssetUpdate(**update_data)

        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            new_callable=AsyncMock,
            return_value=mock_asset,
        ):
            with patch(
                "src.services.asset.asset_service.get_enum_validation_service_async"
            ) as mock_validation:
                mock_validation_service = MagicMock()
                mock_validation_service.validate_asset_data = AsyncMock()
                mock_validation_service.validate_asset_data.return_value = (True, [])
                mock_validation.return_value = mock_validation_service

                with patch(
                    "src.crud.asset.asset_crud.update_with_history_async",
            new_callable=AsyncMock,
            return_value=mock_asset,
                ) as mock_update:
                    result = await service.update_asset(TEST_ASSET_ID, asset_in)

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

    async def test_delete_asset_success(self, service, mock_asset):
        """测试成功删除资产"""
        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            new_callable=AsyncMock,
            return_value=mock_asset,
        ):
            with patch(
                "src.services.asset.asset_service.AssetService._ensure_asset_not_linked",
                new_callable=AsyncMock,
                return_value=None,
            ):
                await service.delete_asset(TEST_ASSET_ID)

                assert mock_asset.data_status == "已删除"
                service.db.add.assert_any_call(mock_asset)
                assert service.db.add.call_count == 2
                service.db.flush.assert_awaited_once()

    async def test_delete_asset_not_found(self, service):
        """测试删除不存在的资产"""
        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            new_callable=AsyncMock,
            side_effect=ResourceNotFoundError("Asset", TEST_ASSET_ID),
        ):
            with pytest.raises(ResourceNotFoundError):
                await service.delete_asset(TEST_ASSET_ID)

    async def test_delete_asset_with_user(self, service, mock_asset, mock_user):
        """测试带用户信息的删除"""
        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            new_callable=AsyncMock,
            return_value=mock_asset,
        ):
            with patch(
                "src.services.asset.asset_service.AssetService._ensure_asset_not_linked",
                new_callable=AsyncMock,
                return_value=None,
            ):
                await service.delete_asset(TEST_ASSET_ID, current_user=mock_user)

                assert mock_asset.data_status == "已删除"
                assert mock_asset.updated_by == mock_user.username
                service.db.add.assert_any_call(mock_asset)
                assert service.db.add.call_count == 2
                service.db.flush.assert_awaited_once()


# ============================================================================
# AssetService.restore_asset 测试
# ============================================================================


class TestRestoreAsset:
    """测试恢复资产"""

    async def test_restore_asset_success(self, service, mock_asset, mock_user):
        """测试成功恢复资产"""
        mock_asset.data_status = "已删除"
        with patch(
            "src.crud.asset.asset_crud.get_async",
            new_callable=AsyncMock,
            return_value=mock_asset,
        ) as mock_get_async:
            result = await service.restore_asset(TEST_ASSET_ID, current_user=mock_user)

            assert result == mock_asset
            assert mock_asset.data_status == "正常"
            assert mock_asset.updated_by == mock_user.username
            service.db.add.assert_any_call(mock_asset)
            assert service.db.add.call_count == 2
            service.db.flush.assert_awaited_once()
            mock_get_async.assert_awaited_once_with(
                db=service.db,
                id=TEST_ASSET_ID,
                include_deleted=True,
            )

    async def test_restore_asset_not_deleted(self, service, mock_asset):
        """测试恢复未删除资产"""
        mock_asset.data_status = "正常"
        with patch("src.crud.asset.asset_crud.get_async", new_callable=AsyncMock, return_value=mock_asset):
            with pytest.raises(OperationNotAllowedError):
                await service.restore_asset(TEST_ASSET_ID)

    async def test_restore_asset_not_found(self, service):
        """测试恢复不存在资产"""
        with patch("src.crud.asset.asset_crud.get_async", new_callable=AsyncMock, return_value=None):
            with pytest.raises(ResourceNotFoundError):
                await service.restore_asset(TEST_ASSET_ID)


# ============================================================================
# AssetService.hard_delete_asset 测试
# ============================================================================


class TestHardDeleteAsset:
    """测试彻底删除资产"""

    async def test_hard_delete_asset_success(self, service, mock_asset, mock_user):
        """测试成功彻底删除资产"""
        mock_asset.data_status = "已删除"
        with patch(
            "src.crud.asset.asset_crud.get_async",
            new_callable=AsyncMock,
            return_value=mock_asset,
        ) as mock_get_async:
            with patch(
                "src.services.asset.asset_service.AssetService._ensure_asset_not_linked",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with patch(
                    "src.services.asset.asset_service.history_crud.remove_by_asset_id_async",
                    new_callable=AsyncMock,
                ) as mock_remove:
                    await service.hard_delete_asset(TEST_ASSET_ID, current_user=mock_user)

                    mock_remove.assert_awaited_once_with(
                        db=service.db,
                        asset_id=mock_asset.id,
                        commit=False,
                    )
                    mock_get_async.assert_awaited_once_with(
                        db=service.db,
                        id=TEST_ASSET_ID,
                        include_deleted=True,
                    )
                    service.db.delete.assert_awaited_once_with(mock_asset)
                    service.db.flush.assert_awaited_once()

    async def test_hard_delete_asset_not_deleted(self, service, mock_asset):
        """测试彻底删除未删除资产"""
        mock_asset.data_status = "正常"
        with patch("src.crud.asset.asset_crud.get_async", new_callable=AsyncMock, return_value=mock_asset):
            with pytest.raises(OperationNotAllowedError):
                await service.hard_delete_asset(TEST_ASSET_ID)

    async def test_hard_delete_asset_not_found(self, service):
        """测试彻底删除不存在资产"""
        with patch("src.crud.asset.asset_crud.get_async", new_callable=AsyncMock, return_value=None):
            with pytest.raises(ResourceNotFoundError):
                await service.hard_delete_asset(TEST_ASSET_ID)


# ============================================================================
# 边界情况和综合测试
# ============================================================================
class TestEdgeCases:
    """测试边界情况"""

    async def test_create_asset_with_all_fields(self, service, mock_asset):
        """测试创建包含所有字段的资产"""
        complete_data = {
            "ownership_id": "ownership-id",
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
            "tenant_type": "企业",
            "is_sublease": False,
            "manager_name": "管理员A",
            "business_model": "自营",
            "operation_status": "正常",
            "data_status": "正常",
        }

        asset_in = AssetCreate(**complete_data)

        with patch(
            "src.services.asset.asset_service.get_enum_validation_service_async"
        ) as mock_validation:
            mock_validation_service = MagicMock()
            mock_validation_service.validate_asset_data = AsyncMock()
            mock_validation_service.validate_asset_data.return_value = (True, [])
            mock_validation.return_value = mock_validation_service

            with patch("src.crud.asset.asset_crud.get_by_name_async", new_callable=AsyncMock, return_value=None):
                with patch(
                    "src.crud.asset.asset_crud.create_with_history_async",
            new_callable=AsyncMock,
            return_value=mock_asset,
                ):
                    result = await service.create_asset(asset_in)

                    assert result == mock_asset

    async def test_update_multiple_assets_concurrent(self, service, mock_asset):
        """测试并发更新多个资产（模拟）"""
        update_data = {"notes": "并发更新"}
        asset_in = AssetUpdate(**update_data)

        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            new_callable=AsyncMock,
            return_value=mock_asset,
        ):
            with patch(
                "src.services.asset.asset_service.get_enum_validation_service_async"
            ) as mock_validation:
                mock_validation_service = MagicMock()
                mock_validation_service.validate_asset_data = AsyncMock()
                mock_validation_service.validate_asset_data.return_value = (True, [])
                mock_validation.return_value = mock_validation_service

                with patch(
                    "src.crud.asset.asset_crud.update_with_history_async",
            new_callable=AsyncMock,
            return_value=mock_asset,
                ):
                    # 模拟多次更新
                    for i in range(3):
                        result = await service.update_asset(f"asset_{i}", asset_in)
                        assert result == mock_asset

    async def test_get_assets_with_combined_filters(self, service):
        """测试组合筛选条件"""
        mock_assets = [MagicMock(spec=Asset)]

        with patch(
            "src.crud.asset.asset_crud.get_multi_with_search_async",
            new_callable=AsyncMock,
            return_value=(mock_assets, 1),
        ) as mock_get:
            filters = {
                "property_nature": "商业",
                "usage_status": "在租",
                "ownership_id": "ownership-id",
            }
            result = await service.get_assets(
                search="测试", filters=filters, skip=0, limit=10
            )

            assert result == (mock_assets, 1)
            call_kwargs = mock_get.call_args.kwargs
            assert call_kwargs["search"] == "测试"
            assert call_kwargs["filters"] == filters
            assert call_kwargs["skip"] == 0
            assert call_kwargs["limit"] == 10

    async def test_update_asset_no_changes(self, service, mock_asset):
        """测试空更新（没有实际变化）"""
        asset_in = AssetUpdate()

        with patch(
            "src.services.asset.asset_service.AssetService.get_asset",
            new_callable=AsyncMock,
            return_value=mock_asset,
        ):
            with patch(
                "src.services.asset.asset_service.get_enum_validation_service_async"
            ) as mock_validation:
                mock_validation_service = MagicMock()
                mock_validation_service.validate_asset_data = AsyncMock()
                # 空数据应该验证通过
                mock_validation_service.validate_asset_data.return_value = (True, [])
                mock_validation.return_value = mock_validation_service

                with patch(
                    "src.crud.asset.asset_crud.update_with_history_async",
            new_callable=AsyncMock,
            return_value=mock_asset,
                ):
                    result = await service.update_asset(TEST_ASSET_ID, asset_in)

                    assert result == mock_asset
