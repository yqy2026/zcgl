"""
项目 CRUD 单元测试

测试 CRUDProject 的所有主要方法
"""

from unittest.mock import MagicMock, patch

import pytest

from src.crud.project import CRUDProject
from src.models.asset import Project


class TestCRUDProjectGet:
    """测试 get 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDProject(Project)

    @pytest.fixture
    def mock_db(self, db_session):
        return db_session

    def test_get_existing_project(self, crud, mock_db):
        """测试获取存在的项目"""
        mock_project = MagicMock(spec=Project)
        mock_project.id = "1"
        mock_project.name = "测试项目"

        with patch.object(crud, "get", return_value=mock_project):
            result = crud.get(mock_db, id="1")

        assert result is not None

    def test_get_nonexistent_project(self, crud, mock_db):
        """测试获取不存在的项目"""
        with patch.object(crud, "get", return_value=None):
            result = crud.get(mock_db, id="999")

        assert result is None


class TestCRUDProjectGetByName:
    """测试 get_by_name 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDProject(Project)

    @pytest.fixture
    def mock_db(self, db_session):
        db_session.query = MagicMock()
        return db_session

    def test_get_by_name_exists(self, crud, mock_db):
        """测试通过名称获取存在的项目"""
        mock_project = MagicMock(spec=Project)
        mock_project.name = "测试项目"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_project

        result = crud.get_by_name(mock_db, name="测试项目")

        assert result is not None
        assert result.name == "测试项目"

    def test_get_by_name_not_exists(self, crud, mock_db):
        """测试通过名称获取不存在的项目"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = crud.get_by_name(mock_db, name="不存在")

        assert result is None


class TestCRUDProjectGetByCode:
    """测试 get_by_code 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDProject(Project)

    @pytest.fixture
    def mock_db(self, db_session):
        db_session.query = MagicMock()
        return db_session

    def test_get_by_code_exists(self, crud, mock_db):
        """测试通过编码获取存在的项目"""
        mock_project = MagicMock(spec=Project)
        mock_project.code = "PRJ-001"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_project

        result = crud.get_by_code(mock_db, code="PRJ-001")

        assert result is not None
        assert result.code == "PRJ-001"

    def test_get_by_code_not_exists(self, crud, mock_db):
        """测试通过编码获取不存在的项目"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = crud.get_by_code(mock_db, code="NOT-EXIST")

        assert result is None


class TestCRUDProjectGetMultiWithFilters:
    """测试 get_multi_with_filters 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDProject(Project)

    @pytest.fixture
    def mock_db(self, db_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db_session.execute = MagicMock(return_value=mock_result)
        return db_session

    def test_get_multi_default_params(self, crud, mock_db):
        """测试默认参数获取多个项目"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()
            result = crud.get_multi_with_filters(mock_db)

        assert isinstance(result, list)

    def test_get_multi_with_is_active_filter(self, crud, mock_db):
        """测试带活跃状态筛选"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()
            crud.get_multi_with_filters(mock_db, is_active=True)

        mock_build.assert_called_once()

    def test_get_multi_with_keyword(self, crud, mock_db):
        """测试带关键词搜索"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()
            crud.get_multi_with_filters(mock_db, keyword="测试")

        mock_build.assert_called_once()

    def test_get_multi_with_ownership_filter(self, crud, mock_db):
        """测试带权属方ID筛选"""
        with patch.object(crud.query_builder, "build_query") as mock_build:
            mock_build.return_value = MagicMock()
            crud.get_multi_with_filters(mock_db, ownership_id="own-1")

        mock_build.assert_called_once()


class TestCRUDProjectSearch:
    """测试 search 方法"""

    @pytest.fixture
    def crud(self):
        return CRUDProject(Project)

    @pytest.fixture
    def mock_db(self, db_session):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db_session.execute = MagicMock(return_value=mock_result)
        db_session.scalar = MagicMock(return_value=0)
        return db_session

    def test_search_returns_dict(self, crud, mock_db):
        """测试搜索返回字典结构"""
        search_params = MagicMock()
        search_params.page = 1
        search_params.page_size = 10
        search_params.keyword = None
        search_params.is_active = None
        search_params.ownership_id = None

        with patch.object(crud.query_builder, "build_query") as mock_build:
            with patch.object(crud.query_builder, "build_count_query") as mock_count:
                mock_build.return_value = MagicMock()
                mock_count.return_value = MagicMock()
                result = crud.search(mock_db, search_params)

        assert isinstance(result, dict)
        assert "items" in result
        assert "total" in result
