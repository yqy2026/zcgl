"""
测试 AssetBatchService (资产批量操作服务)
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from src.services.asset.batch_service import (
    AssetBatchService,
    BatchOperationResult,
)


@pytest.fixture
def mock_db():
    """创建模拟数据库会话"""
    return MagicMock(spec=Session)


@pytest.fixture
def batch_service(mock_db):
    """创建 AssetBatchService 实例"""
    return AssetBatchService(mock_db)


class TestBatchOperationResult:
    """测试 BatchOperationResult 类"""

    def test_init_default(self):
        """测试默认初始化"""
        result = BatchOperationResult()
        assert result.success_count == 0
        assert result.failed_count == 0
        assert result.total_count == 0
        assert result.errors == []
        assert result.updated_ids == []

    def test_init_with_values(self):
        """测试带值初始化"""
        result = BatchOperationResult(
            success_count=5,
            failed_count=2,
            total_count=7,
            errors=[{"asset_id": "1", "error": "test"}],
            updated_ids=["1", "2", "3", "4", "5"],
        )
        assert result.success_count == 5
        assert result.failed_count == 2
        assert result.total_count == 7
        assert len(result.errors) == 1
        assert len(result.updated_ids) == 5

    def test_to_dict(self):
        """测试转换为字典"""
        result = BatchOperationResult(
            success_count=3,
            failed_count=1,
            total_count=4,
            errors=[{"asset_id": "1", "error": "error"}],
            updated_ids=["1", "2", "3"],
        )
        result_dict = result.to_dict()

        assert result_dict["success_count"] == 3
        assert result_dict["failed_count"] == 1
        assert result_dict["total_count"] == 4
        assert len(result_dict["errors"]) == 1
        assert len(result_dict["updated_assets"]) == 3


class TestAssetBatchService:
    """测试 AssetBatchService 类"""

    def test_init(self, mock_db):
        """测试服务初始化"""
        service = AssetBatchService(mock_db)
        assert service.db == mock_db
        assert service.validator is not None

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_update_success(self, mock_asset_crud, batch_service, mock_db):
        """测试批量更新成功"""
        # Mock CRUD操作
        mock_asset = MagicMock()
        mock_asset.id = "asset_1"
        mock_asset_crud.get.return_value = mock_asset
        mock_asset_crud.update.return_value = mock_asset

        with patch(
            "src.services.asset.batch_service.history_crud"
        ) as mock_history_crud:
            mock_history_crud.create.return_value = MagicMock()

            # 执行批量更新
            result = batch_service.batch_update(
                asset_ids=["asset_1", "asset_2"],
                updates={"usage_status": "出租"},
                operator="test_user",
            )

            # 验证结果 - 应该在第二次循环中抛出异常（asset_2不存在）
            assert result.total_count == 2
            mock_db.commit.assert_called()

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_update_with_rollback(self, mock_asset_crud, batch_service, mock_db):
        """测试批量更新失败时回滚"""
        # Mock 第一个资产成功，第二个资产失败
        mock_asset_1 = MagicMock()
        mock_asset_1.id = "asset_1"
        mock_asset_2 = MagicMock()
        mock_asset_2.id = "asset_2"

        mock_asset_crud.get.side_effect = [mock_asset_1, mock_asset_2]
        mock_asset_crud.update.side_effect = [MagicMock(), Exception("Update failed")]

        # V2: 批量服务现在返回BatchOperationResult而不是抛出异常
        # 这样更容错，即使部分失败也能继续处理其他资产
        result = batch_service.batch_update(
            asset_ids=["asset_1", "asset_2"],
            updates={"usage_status": "出租"},
        )

        # 验证结果：1个成功，1个失败
        assert result.success_count == 1
        assert result.failed_count == 1
        assert len(result.errors) == 1
        assert "Update failed" in result.errors[0]["error"]
        mock_db.commit.assert_called()  # 有成功的更新会提交
        mock_db.rollback.assert_not_called()  # 有成功的不回滚

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_update_all(self, mock_asset_crud, batch_service, mock_db):
        """测试更新所有资产"""
        # Mock 获取所有资产
        mock_assets = [MagicMock(id="asset_1"), MagicMock(id="asset_2")]
        mock_asset_crud.get_multi_with_search.return_value = (mock_assets, None)
        mock_asset_crud.get.return_value = MagicMock()
        mock_asset_crud.update.return_value = MagicMock()

        with patch(
            "src.services.asset.batch_service.history_crud"
        ) as mock_history_crud:
            mock_history_crud.create.return_value = MagicMock()

            result = batch_service.batch_update(
                asset_ids=None, updates={"usage_status": "出租"}, update_all=True
            )

            assert result.total_count == 2
            mock_asset_crud.get_multi_with_search.assert_called_once()

    def test_batch_update_empty_list(self, batch_service):
        """测试空资产列表"""
        result = batch_service.batch_update(asset_ids=[], updates={})

        assert result.total_count == 0
        assert result.success_count == 0
        assert result.failed_count == 0

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_delete_success(self, mock_asset_crud, batch_service, mock_db):
        """测试批量删除成功"""
        mock_asset = MagicMock()
        mock_asset.id = "asset_1"
        mock_asset_crud.get.return_value = mock_asset
        mock_asset_crud.remove.return_value = None

        result = batch_service.batch_delete(asset_ids=["asset_1"])

        assert result.success_count == 1
        assert result.failed_count == 0
        mock_db.commit.assert_called_once()

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_delete_with_rollback(self, mock_asset_crud, batch_service, mock_db):
        """测试批量删除失败时回滚"""
        mock_asset = MagicMock()
        mock_asset.id = "asset_1"
        mock_asset_crud.get.return_value = mock_asset
        mock_asset_crud.remove.side_effect = Exception("Delete failed")

        with pytest.raises(Exception) as excinfo:
            batch_service.batch_delete(asset_ids=["asset_1"])

        assert "Delete failed" in str(excinfo.value)
        mock_db.rollback.assert_called_once()

    def test_validate_asset_data_valid(self, batch_service):
        """测试有效数据验证"""
        data = {
            "property_name": "Test Asset",
            "address": "123 Test St",
            "ownership_status": "已确权",
            "property_nature": "经营性",
            "usage_status": "出租",
            "land_area": 1000.0,
            "rentable_area": 800.0,
            "rented_area": 600.0,
        }

        is_valid, errors, warnings, validated_fields = (
            batch_service.validate_asset_data(data=data)
        )

        assert is_valid is True
        assert len(errors) == 0
        assert len(validated_fields) > 0

    def test_validate_asset_data_invalid(self, batch_service):
        """测试无效数据验证"""
        data = {
            "property_name": "",  # 空值
            "address": None,  # 缺失
        }

        is_valid, errors, warnings, validated_fields = (
            batch_service.validate_asset_data(data=data)
        )

        assert is_valid is False
        assert len(errors) > 0
        # 应该有property_name和address的错误
        error_fields = [e["field"] for e in errors]
        assert "property_name" in error_fields

    def test_validate_asset_data_numeric_error(self, batch_service):
        """测试数值字段错误"""
        data = {
            "property_name": "Test",
            "address": "123 Test St",
            "ownership_status": "已确权",
            "property_nature": "经营性",
            "usage_status": "出租",
            "land_area": "invalid_number",  # 无效数字
        }

        is_valid, errors, warnings, validated_fields = (
            batch_service.validate_asset_data(data=data)
        )

        assert is_valid is False
        assert any(e["field"] == "land_area" for e in errors)

    def test_validate_asset_data_area_consistency(self, batch_service):
        """测试面积一致性验证"""
        data = {
            "property_name": "Test",
            "address": "123 Test St",
            "ownership_status": "已确权",
            "property_nature": "经营性",
            "usage_status": "出租",
            "rentable_area": 100.0,
            "rented_area": 150.0,  # 大于可出租面积
        }

        is_valid, errors, warnings, validated_fields = (
            batch_service.validate_asset_data(data=data)
        )

        assert is_valid is False
        assert any("已出租面积不能大于可出租面积" in e["error"] for e in errors)

    def test_validate_asset_suggestions(self, batch_service):
        """测试建议性警告"""
        data = {
            "property_name": "Test",
            "address": "123 Test St",
            "ownership_status": "已确权",
            "property_nature": "经营性",
            "usage_status": "出租",
            # 缺少建议字段: land_area, annual_income, etc.
        }

        is_valid, errors, warnings, validated_fields = (
            batch_service.validate_asset_data(data=data)
        )

        # 数据有效，但应该有警告
        assert is_valid is True
        assert len(warnings) > 0
        assert len(errors) == 0
