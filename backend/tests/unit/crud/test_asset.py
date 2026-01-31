"""
资产 CRUD 单元测试

测试 CRUDAsset 的所有主要方法
"""

from unittest.mock import MagicMock, patch

import pytest

from src.crud.asset import AssetCRUD
from src.models.asset import Asset


class TestCRUDAssetGet:
    """测试 get 方法"""

    @pytest.fixture
    def crud(self):
        return AssetCRUD()

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_get_existing_asset(self, crud, mock_db):
        """测试获取存在的资产"""
        mock_asset = MagicMock(spec=Asset)
        mock_asset.id = "1"
        mock_asset.name = "测试资产"

        with patch.object(crud, "get", return_value=mock_asset):
            result = crud.get(mock_db, id="1")

        assert result is not None

    def test_get_nonexistent_asset(self, crud, mock_db):
        """测试获取不存在的资产"""
        with patch.object(crud, "get", return_value=None):
            result = crud.get(mock_db, id="999")

        assert result is None


class TestCRUDAssetGetByCode:
    """测试 get_by_code 方法"""

    @pytest.fixture
    def crud(self):
        return AssetCRUD()

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_get_by_code_exists(self, crud, mock_db):
        """测试通过编码获取存在的资产"""
        mock_asset = MagicMock(spec=Asset)
        mock_asset.asset_code = "A001"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_asset

        result = crud.get_by_code(mock_db, code="A001")

        assert result is not None
        assert result.asset_code == "A001"

    def test_get_by_code_not_exists(self, crud, mock_db):
        """测试通过编码获取不存在的资产"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = crud.get_by_code(mock_db, code="NOT-EXIST")

        assert result is None


class TestCRUDAssetGetMulti:
    """测试 get_multi 方法"""

    @pytest.fixture
    def crud(self):
        return AssetCRUD()

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result
        return db

    def test_get_multi_default_params(self, crud, mock_db):
        """测试默认参数获取多个资产"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()
            result = crud.get_multi(mock_db)

        assert isinstance(result, list)

    def test_get_multi_with_pagination(self, crud, mock_db):
        """测试分页参数"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()
            crud.get_multi(mock_db, skip=10, limit=20)

        mock_build.assert_called_once()


class TestCRUDAssetCreate:
    """测试 create 方法"""

    @pytest.fixture
    def crud(self):
        return AssetCRUD()

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.add = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock()
        return db

    def test_create_asset(self, crud, mock_db):
        """测试创建资产"""
        create_data = MagicMock()
        create_data.model_dump.return_value = {
            "name": "新资产",
            "asset_code": "A002",
        }

        with patch.object(crud, "create") as mock_create:
            mock_asset = MagicMock()
            mock_asset.id = "new-id"
            mock_create.return_value = mock_asset

            result = crud.create(mock_db, obj_in=create_data)

        assert result is not None


class TestCRUDAssetUpdate:
    """测试 update 方法"""

    @pytest.fixture
    def crud(self):
        return AssetCRUD()

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    def test_update_asset(self, crud, mock_db):
        """测试更新资产"""
        mock_asset = MagicMock(spec=Asset)
        mock_asset.id = "1"

        update_data = {"name": "更新后的名称"}

        with patch.object(crud, "update") as mock_update:
            mock_update.return_value = mock_asset
            result = crud.update(mock_db, db_obj=mock_asset, obj_in=update_data)

        assert result is not None


class TestCRUDAssetDelete:
    """测试 remove 方法"""

    @pytest.fixture
    def crud(self):
        return AssetCRUD()

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.delete = MagicMock()
        db.commit = MagicMock()
        return db

    def test_delete_asset(self, crud, mock_db):
        """测试删除资产"""
        mock_asset = MagicMock(spec=Asset)
        mock_asset.id = "1"

        with patch.object(crud, "remove") as mock_remove:
            mock_remove.return_value = mock_asset
            result = crud.remove(mock_db, id="1")

        assert result is not None


class TestCRUDAssetSearch:
    """测试 search 相关方法"""

    @pytest.fixture
    def crud(self):
        return AssetCRUD()

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result
        db.scalar.return_value = 0
        return db

    def test_search_with_filters(self, crud, mock_db):
        """测试带筛选条件的搜索"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            with patch.object(crud.query_builder, "build_count_query") as mock_count:
                mock_build.return_value = MagicMock()
                mock_count.return_value = MagicMock()

                # 模拟搜索
                filters = {"ownership_entity": "公司A"}
                crud.get_multi(mock_db, filters=filters)

        mock_build.assert_called_once()
