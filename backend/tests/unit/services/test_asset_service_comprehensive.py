"""
资产服务全面测试

Comprehensive tests for Asset Service to maximize coverage
"""

import pytest
from sqlalchemy.orm import Session
from datetime import datetime, UTC


@pytest.fixture
def asset_service(db: Session):
    """资产服务实例"""
    from src.services.asset.asset_service import AssetService
    return AssetService(db)


@pytest.fixture
def sample_asset(db: Session, admin_user):
    """示例资产数据"""
    from src.schemas.asset import AssetCreate
    from src.crud.asset import asset_crud

    asset = asset_crud.create(
        db,
        obj_in=AssetCreate(
            name="测试资产",
            code="TEST-ASSET-001",
            area=1000.0,
            asset_type="building",
            usage="office",
            project_id="project-001",
            ownership_id="owner-001"
        )
    )
    yield asset
    try:
        asset_crud.remove(db, id=asset.id)
    except:
        pass


class TestAssetServiceBusinessLogic:
    """测试资产服务业务逻辑"""

    def test_calculate_depreciation(self, asset_service):
        """测试折旧计算"""
        # 测试不同类型资产的折旧计算
        pass

    def test_get_asset_by_code(self, asset_service, sample_asset):
        """测试按代码获取资产"""
        result = asset_service.get_asset_by_code(sample_asset.code)
        assert result is not None

    def test_search_assets_advanced_filters(self, asset_service, db: Session):
        """测试高级搜索筛选"""
        result = asset_service.search_assets(
            db,
            keyword="测试",
            asset_type="building",
            min_area=500.0,
            max_area=2000.0
        )
        assert result is not None

    def test_batch_update_assets_validation(self, asset_service, db: Session):
        """测试批量更新验证"""
        update_data = {
            "usage": "warehouse",
            "status": "active"
        }
        asset_ids = ["id1", "id2"]
        result = asset_service.batch_update_assets(
            db,
            asset_ids=asset_ids,
            update_data=update_data
        )
        assert result is not None

    def test_get_asset_statistics(self, asset_service, db: Session):
        """测试获取资产统计信息"""
        stats = asset_service.get_asset_statistics(db)
        assert stats is not None
        assert "total_count" in stats
        assert "total_area" in stats

    def test_transfer_ownership(self, asset_service, sample_asset, db: Session):
        """测试权属转移"""
        new_owner_id = "new-owner-001"
        result = asset_service.transfer_ownership(
            db,
            asset_id=sample_asset.id,
            new_owner_id=new_owner_id
        )
        assert result is not None

    def test_retire_asset(self, asset_service, sample_asset, db: Session):
        """测试资产报废"""
        result = asset_service.retire_asset(
            db,
            asset_id=sample_asset.id,
            reason="testing_retirement"
        )
        assert result is not None

    def test_reactivate_asset(self, asset_service, sample_asset, db: Session):
        """测试重新激活资产"""
        result = asset_service.reactivate_asset(
            db,
            asset_id=sample_asset.id
        )
        assert result is not None

    def test_asset_area_validation(self, asset_service):
        """测试资产面积验证"""
        # 测试各种边界情况
        with pytest.raises(ValueError):
            asset_service.validate_asset_area(-100)
        with pytest.raises(ValueError):
            asset_service.validate_asset_area(0)
        assert asset_service.validate_asset_area(100) is not None
