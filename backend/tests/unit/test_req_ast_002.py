"""
REQ-AST-002 单元测试：资产与项目、权属关系可追踪

覆盖：
- Gap 1: Asset.project 只返回活跃绑定
- Gap 2: 资产运营方随当前项目派生，资产更新不独立写 manager_party_id
- Gap 3: 关系历史查询 API
- Gap 4: ProjectAsset active unique 约束
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.project_asset import ProjectAsset

pytestmark = [pytest.mark.asyncio, pytest.mark.unit]


class TestManagerChangeTracking:
    """update_asset 忽略独立 manager_party_id 输入。"""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.in_transaction.return_value = True
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
        db.add = MagicMock()
        return db

    @patch("src.services.asset.asset_service.party_crud")
    @patch("src.services.asset.asset_service.get_enum_validation_service_async")
    async def test_manager_change_is_ignored_by_asset_update(
        self,
        mock_get_enum_validation_service,
        mock_party_crud,
        mock_db,
    ):
        """资产运营方由项目派生，更新资产不应写经营方历史。"""
        from src.models.asset import Asset
        from src.models.auth import User
        from src.schemas.asset import AssetUpdate
        from src.services.asset.asset_service import AsyncAssetService

        # Setup
        asset = Asset()
        asset.id = "asset-1"
        asset.asset_name = "测试物业"
        asset.address = "测试地址"
        asset.ownership_status = "已确权"
        asset.property_nature = "商业"
        asset.usage_status = "在租"
        asset.owner_party_id = "party-owner"
        asset.manager_party_id = "party-old"
        asset.version = 1

        user = User()
        user.id = "user-1"
        user.username = "testuser"

        mock_party_crud.get_party = AsyncMock(return_value=MagicMock())
        validation_service = MagicMock()
        validation_service.validate_asset_data = AsyncMock(return_value=(True, []))
        mock_get_enum_validation_service.return_value = validation_service

        service = AsyncAssetService(mock_db)

        with patch.object(
            service, "get_asset", new_callable=AsyncMock, return_value=asset
        ):
            with patch.object(service, "asset_crud") as mock_asset_crud:
                mock_asset_crud.update_with_history_async = AsyncMock(
                    return_value=asset
                )
                mock_asset_crud.get_by_name_async = AsyncMock(return_value=None)

                update_data = AssetUpdate(manager_party_id="party-new")

                await service.update_asset(
                    "asset-1",
                    update_data,
                    current_user=user,
                )

                update_payload = (
                    mock_asset_crud.update_with_history_async.await_args.kwargs[
                        "obj_in"
                    ]
                )
                assert update_payload.manager_party_id is None


# ---------------------------------------------------------------------------
# Model: ProjectAsset partial unique index definition
# ---------------------------------------------------------------------------


class TestProjectAssetModel:
    """Verify ProjectAsset has the expected constraints."""

    def test_partial_unique_index_defined(self):
        """ProjectAsset.__table_args__ 包含 active asset 唯一索引。"""
        table_args = ProjectAsset.__table_args__
        index_names = [
            arg.name
            for arg in table_args
            if hasattr(arg, "name") and arg.name is not None
        ]
        assert "uq_project_assets_active_asset" in index_names

    def test_check_constraint_defined(self):
        """ProjectAsset.__table_args__ 包含时间范围检查约束。"""
        table_args = ProjectAsset.__table_args__
        constraint_names = [
            arg.name
            for arg in table_args
            if hasattr(arg, "name") and arg.name is not None
        ]
        assert "ck_project_assets_valid_range" in constraint_names


# ---------------------------------------------------------------------------
# Model: Asset.project relationship
# ---------------------------------------------------------------------------


class TestAssetProjectRelationship:
    """Verify Asset.project relationship is configured correctly."""

    def test_project_relationship_uselist_false(self):
        """Asset.project 是单值关系（uselist=False）。"""
        from src.models.asset import Asset

        prop = Asset.__mapper__.relationships["project"]
        assert prop.uselist is False

    def test_project_relationship_is_viewonly(self):
        """Asset.project 是只读关系。"""
        from src.models.asset import Asset

        prop = Asset.__mapper__.relationships["project"]
        assert prop.viewonly is True
