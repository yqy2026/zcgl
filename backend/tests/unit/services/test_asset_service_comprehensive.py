"""
资产服务全面测试

Comprehensive tests for Asset Service to maximize coverage
"""


import pytest
from sqlalchemy.orm import Session


@pytest.fixture
def asset_service(db: Session):
    """资产服务实例"""
    from src.services.asset.asset_service import AssetService

    return AssetService(db)


@pytest.fixture
def sample_asset(db: Session, admin_user):
    """示例资产数据"""
    from src.crud.asset import asset_crud
    from src.schemas.asset import AssetCreate

    asset = asset_crud.create(
        db,
        obj_in=AssetCreate(
            name="测试资产",
            code="TEST-ASSET-001",
            area=1000.0,
            asset_type="building",
            usage="office",
            project_id="project-001",
            ownership_id="owner-001",
        ),
    )
    yield asset
    try:
        asset_crud.remove(db, id=asset.id)
    except Exception:
        pass


class TestAssetServiceBusinessLogic:
    """测试资产服务业务逻辑"""

    def test_get_asset_by_code(self, asset_service, sample_asset):
        """测试按代码获取资产"""
        # Note: AssetService currently doesn't have get_asset_by_code,
        # it relies on search or get by id. We'll test get_asset (by ID) instead
        result = asset_service.get_asset(sample_asset.id)
        assert result is not None
        assert result.code == sample_asset.code
        assert result.id == sample_asset.id

    def test_search_assets_advanced_filters(self, asset_service, db: Session, sample_asset):
        """测试高级搜索筛选"""
        # Basic search
        result, count = asset_service.get_assets(
            search=sample_asset.property_name[:2]
        )
        assert count >= 1
        assert result[0].id == sample_asset.id

        # Filter search
        filters = {"asset_type": sample_asset.asset_type}
        result, count = asset_service.get_assets(filters=filters)
        assert count >= 1

    def test_create_asset_logic(self, asset_service, db: Session, admin_user):
        """测试创建资产业务逻辑"""
        from src.schemas.asset import AssetCreate

        asset_in = AssetCreate(
            name="新测试资产",
            code="NEW-ASSET-001",
            area=500.0,
            asset_type="building",
            usage="office",
            project_id="project-001",
            ownership_id="owner-001"
        )

        # Mock enum validation and calculator to avoid dependencies for this unit test
        # or rely on integration if dependencies are available.
        # Given this is "unit" but uses "db" fixture, it's an integration test.

        asset = asset_service.create_asset(
            asset_in,
            current_user=admin_user
        )

        assert asset.id is not None
        assert asset.property_name == "新测试资产"
        assert asset.status == "idle"  # Default

    def test_update_asset_logic(self, asset_service, sample_asset, db: Session, admin_user):
        """测试更新资产逻辑"""
        from src.schemas.asset import AssetUpdate

        update_data = AssetUpdate(
            name="更新后的资产",
            usage="retail"
        )

        updated = asset_service.update_asset(
            sample_asset.id,
            update_data,
            current_user=admin_user
        )

        assert updated.property_name == "更新后的资产"
        assert updated.usage == "retail"
        # Ensure other fields remain
        assert updated.code == sample_asset.code

    def test_delete_asset_logic(self, asset_service, sample_asset):
        """测试删除资产逻辑"""
        from src.core.exception_handler import ResourceNotFoundError

        asset_id = sample_asset.id
        asset_service.delete_asset(asset_id)

        # Verify deletion
        with pytest.raises(ResourceNotFoundError):
            asset_service.get_asset(asset_id)

    def test_get_distinct_field_values(self, asset_service, sample_asset):
        """测试获取唯一值"""
        values = asset_service.get_distinct_field_values("asset_type")
        assert sample_asset.asset_type in values
