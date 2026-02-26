"""
资产服务全面测试

Comprehensive tests for Asset Service to maximize coverage
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from src import database as database
from src.core.exception_handler import ResourceNotFoundError
from src.models.ownership import Ownership
from src.schemas.asset import AssetCreate, AssetUpdate
from src.services.asset.asset_service import AssetService

pytestmark = pytest.mark.asyncio


def _build_asset_data(**overrides):
    data = {
        "ownership_id": "ownership-default",
        "property_name": "测试物业A",
        "address": "北京市朝阳区测试路123号",
        "ownership_status": "已确权",
        "property_nature": "商业",
        "usage_status": "出租中",
        "rentable_area": Decimal("1000.00"),
        "rented_area": Decimal("600.00"),
    }
    data.update(overrides)
    return AssetCreate(**data)


@pytest.fixture
async def db_session():
    async_engine = create_async_engine(
        database.get_async_database_url(),
        echo=False,
        poolclass=NullPool,
    )

    async with async_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
            await async_engine.dispose()


@pytest.fixture
def asset_service(db_session: AsyncSession):
    """资产服务实例"""
    return AssetService(db_session)


@pytest.fixture
async def ownership_record(db_session: AsyncSession):
    ownership = Ownership(
        id="ownership-default",
        name="测试公司",
        code="OWN-DEFAULT",
    )
    db_session.add(ownership)
    await db_session.flush()
    return ownership


@pytest.fixture
async def sample_asset(asset_service: AssetService, ownership_record):
    """示例资产数据"""
    return await asset_service.create_asset(_build_asset_data())


class TestAssetServiceBusinessLogic:
    """测试资产服务业务逻辑"""

    async def test_get_asset_by_id(self, asset_service, sample_asset):
        """测试按ID获取资产"""
        result = await asset_service.get_asset(sample_asset.id)
        assert result is not None
        assert result.property_name == sample_asset.property_name
        assert result.id == sample_asset.id

    async def test_search_assets_advanced_filters(
        self, asset_service, sample_asset
    ):
        """测试高级搜索筛选"""
        result, count = await asset_service.get_assets(
            search=sample_asset.property_name[:2]
        )
        assert count >= 1
        assert result[0].id == sample_asset.id

        filters = {"property_nature": sample_asset.property_nature}
        result, count = await asset_service.get_assets(filters=filters)
        assert count >= 1

    async def test_create_asset_logic(self, asset_service, ownership_record):
        """测试创建资产业务逻辑"""
        _ = ownership_record
        asset_in = _build_asset_data(property_name="新测试资产")

        asset = await asset_service.create_asset(asset_in)

        assert asset.id is not None
        assert asset.property_name == "新测试资产"
        assert asset.data_status == "正常"

    async def test_update_asset_logic(self, asset_service, sample_asset):
        """测试更新资产逻辑"""
        update_data = AssetUpdate(property_name="更新后的资产", usage_status="空置")

        updated = await asset_service.update_asset(sample_asset.id, update_data)

        assert updated.property_name == "更新后的资产"
        assert updated.usage_status == "空置"

    async def test_delete_asset_logic(self, asset_service, sample_asset):
        """测试删除资产逻辑"""
        asset_id = sample_asset.id
        await asset_service.delete_asset(asset_id)

        with pytest.raises(ResourceNotFoundError):
            await asset_service.get_asset(asset_id)

    async def test_get_distinct_field_values(self, asset_service, sample_asset):
        """测试获取唯一值"""
        values = await asset_service.get_distinct_field_values("property_nature")
        assert sample_asset.property_nature in values
