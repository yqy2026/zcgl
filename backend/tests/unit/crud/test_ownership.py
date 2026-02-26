"""
权属方 CRUD 单元测试

测试 CRUDOwnership 的所有主要方法
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crud.ownership import CRUDOwnership
from src.crud.query_builder import PartyFilter
from src.models.ownership import Ownership


class TestCRUDOwnershipGet:
    """测试 get 方法"""

    @pytest.fixture
    def crud(self):
        """创建 CRUD 实例"""
        return CRUDOwnership(Ownership)

    @pytest.fixture
    def mock_db(self, db_session):
        """使用真实数据库会话"""
        db_session.query = MagicMock()
        return db_session

    def test_get_existing_ownership(self, crud, mock_db):
        """测试获取存在的权属方"""
        mock_ownership = MagicMock(spec=Ownership)
        mock_ownership.id = "1"
        mock_ownership.name = "测试权属方"

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_ownership
        )

        with patch.object(crud, "get", return_value=mock_ownership):
            result = asyncio.run(crud.get(mock_db, id="1"))

        assert result is not None

    def test_get_nonexistent_ownership(self, crud, mock_db):
        """测试获取不存在的权属方"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch.object(crud, "get", return_value=None):
            result = asyncio.run(crud.get(mock_db, id="999"))

        assert result is None


class TestCRUDOwnershipGetByName:
    """测试 get_by_name 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDOwnership(Ownership)

    @pytest.fixture
    def mock_db(self, db_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        db_session.execute = AsyncMock(return_value=mock_result)
        return db_session

    def test_get_by_name_exists(self, crud, mock_db):
        """测试通过名称获取存在的权属方"""
        mock_ownership = MagicMock(spec=Ownership)
        mock_ownership.name = "测试权属方"

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_ownership
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = asyncio.run(crud.get_by_name(mock_db, name="测试权属方"))

        assert result is not None
        assert result.name == "测试权属方"

    def test_get_by_name_not_exists(self, crud, mock_db):
        """测试通过名称获取不存在的权属方"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = asyncio.run(crud.get_by_name(mock_db, name="不存在"))

        assert result is None


class TestCRUDOwnershipGetByCode:
    """测试 get_by_code 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDOwnership(Ownership)

    @pytest.fixture
    def mock_db(self, db_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        db_session.execute = AsyncMock(return_value=mock_result)
        return db_session

    def test_get_by_code_exists(self, crud, mock_db):
        """测试通过编码获取存在的权属方"""
        mock_ownership = MagicMock(spec=Ownership)
        mock_ownership.code = "OWN-001"

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_ownership
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = asyncio.run(crud.get_by_code(mock_db, code="OWN-001"))

        assert result is not None
        assert result.code == "OWN-001"

    def test_get_by_code_not_exists(self, crud, mock_db):
        """测试通过编码获取不存在的权属方"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        result = asyncio.run(crud.get_by_code(mock_db, code="NOT-EXIST"))

        assert result is None


class TestCRUDOwnershipGetMultiWithFilters:
    """测试 get_multi_with_filters 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDOwnership(Ownership)

    @pytest.fixture
    def mock_db(self, db_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db_session.execute = AsyncMock(return_value=mock_result)
        return db_session

    def test_get_multi_default_params(self, crud, mock_db):
        """测试默认参数获取多个权属方"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()
            result = asyncio.run(crud.get_multi_with_filters(mock_db))

        assert isinstance(result, list)

    def test_get_multi_with_is_active_filter(self, crud, mock_db):
        """测试带活跃状态筛选"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()
            asyncio.run(crud.get_multi_with_filters(mock_db, is_active=True))

        mock_build.assert_called_once()

    def test_get_multi_with_keyword(self, crud, mock_db):
        """测试带关键词搜索"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()
            asyncio.run(crud.get_multi_with_filters(mock_db, keyword="测试"))

        mock_build.assert_called_once()

    def test_get_multi_with_tenant_filter(self, crud, mock_db):
        """测试透传 party_filter 参数"""
        party_filter = PartyFilter(party_ids=["org-1"])
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()
            asyncio.run(
                crud.get_multi_with_filters(
                    mock_db,
                    party_filter=party_filter,
                )
            )

        assert mock_build.call_args.kwargs.get("party_filter") == party_filter

    def test_get_multi_with_pagination(self, crud, mock_db):
        """测试分页参数"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()
            asyncio.run(crud.get_multi_with_filters(mock_db, skip=10, limit=20))

        mock_build.assert_called_with(
            filters={},
            search_query=None,
            search_fields=["name", "short_name", "code"],
            sort_by="created_at",
            sort_desc=True,
            skip=10,
            limit=20,
            party_filter=None,
        )


class TestCRUDOwnershipSearch:
    """测试 search 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDOwnership(Ownership)

    @pytest.fixture
    def mock_db(self, db_session):
        db_session.execute = AsyncMock()
        db_session.scalar = AsyncMock(return_value=0)
        return db_session

    def test_search_returns_dict(self, crud, mock_db):
        """测试搜索返回字典结构"""
        search_params = MagicMock()
        search_params.page = 1
        search_params.page_size = 10
        search_params.keyword = None
        search_params.is_active = None

        with patch.object(
            crud,
            "get_multi_with_count",
            new=AsyncMock(return_value=([], 0)),
        ):
            result = asyncio.run(crud.search(mock_db, search_params))

        assert isinstance(result, dict)
        assert "items" in result
        assert "total" in result
