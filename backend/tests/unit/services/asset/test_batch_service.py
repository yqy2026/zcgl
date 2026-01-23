"""
资产批量操作服务综合测试

测试 AssetBatchService 的所有功能：
1. 批量导入操作
2. 批量验证
3. 进度跟踪
4. 错误处理和回滚
5. 状态报告
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from src.models.asset import Asset
from src.services.asset.batch_service import (
    AssetBatchService,
    BatchOperationResult,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    """创建模拟数据库会话"""
    return MagicMock(spec=Session)


@pytest.fixture
def batch_service(mock_db):
    """创建 AssetBatchService 实例"""
    return AssetBatchService(mock_db)


@pytest.fixture
def mock_asset():
    """创建模拟资产对象"""
    asset = MagicMock(spec=Asset)
    asset.id = "asset_test_001"
    asset.property_name = "测试物业"
    asset.address = "北京市朝阳区测试路123号"
    asset.ownership_status = "已确权"
    asset.property_nature = "商业"
    asset.usage_status = "在用"
    return asset


@pytest.fixture
def valid_asset_data():
    """有效的资产数据"""
    return {
        "property_name": "测试物业",
        "address": "北京市朝阳区测试路123号",
        "ownership_status": "已确权",
        "property_nature": "商业",
        "usage_status": "在用",
        "land_area": 1000.0,
        "actual_property_area": 800.0,
        "rentable_area": 700.0,
        "rented_area": 500.0,
    }


@pytest.fixture
def invalid_asset_data():
    """无效的资产数据"""
    return {
        "property_name": "",  # 空值
        "address": None,  # 缺失
        "ownership_status": "已确权",
        "property_nature": "商业",
        "usage_status": "在用",
        "land_area": "invalid_number",  # 无效数字
    }


# ============================================================================
# BatchOperationResult Tests
# ============================================================================


class TestBatchOperationResult:
    """测试 BatchOperationResult Pydantic 模型"""

    def test_init_default_values(self):
        """测试默认初始化值"""
        result = BatchOperationResult()
        assert result.success_count == 0
        assert result.failed_count == 0
        assert result.total_count == 0
        assert result.errors == []
        assert result.updated_ids == []

    def test_init_with_all_values(self):
        """测试带所有值初始化"""
        result = BatchOperationResult(
            success_count=5,
            failed_count=2,
            total_count=7,
            errors=[
                {"asset_id": "1", "error": "test error", "error_type": "ValueError"}
            ],
            updated_ids=["1", "2", "3", "4", "5"],
        )
        assert result.success_count == 5
        assert result.failed_count == 2
        assert result.total_count == 7
        assert len(result.errors) == 1
        assert len(result.updated_ids) == 5

    def test_to_dict_conversion(self):
        """测试转换为字典格式"""
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

    def test_model_validator_valid_counts(self):
        """测试计数验证器 - 有效计数"""
        result = BatchOperationResult(
            success_count=5,
            failed_count=2,
            total_count=10,
        )
        assert result.success_count + result.failed_count <= result.total_count

    def test_model_validator_invalid_counts(self):
        """测试计数验证器 - 无效计数（超过总数）"""
        with pytest.raises(ValidationError) as excinfo:
            BatchOperationResult(
                success_count=8,
                failed_count=5,
                total_count=10,
            )
        assert "cannot exceed total_count" in str(excinfo.value)

    def test_model_validator_exactly_equal(self):
        """测试计数验证器 - 成功+失败等于总数"""
        result = BatchOperationResult(
            success_count=5,
            failed_count=5,
            total_count=10,
        )
        assert result.success_count + result.failed_count == result.total_count

    def test_negative_values_rejected(self):
        """测试拒绝负数值"""
        with pytest.raises(ValidationError):
            BatchOperationResult(success_count=-1)

        with pytest.raises(ValidationError):
            BatchOperationResult(failed_count=-5)

        with pytest.raises(ValidationError):
            BatchOperationResult(total_count=-10)


# ============================================================================
# AssetBatchService Initialization Tests
# ============================================================================


class TestAssetBatchServiceInit:
    """测试 AssetBatchService 初始化"""

    def test_service_initialization(self, batch_service, mock_db):
        """测试服务正确初始化"""
        assert batch_service.db == mock_db
        assert batch_service.validator is not None
        assert hasattr(batch_service, "validator")

    def test_validator_instance(self, batch_service):
        """测试验证器实例类型"""
        from src.services.asset.validators import AssetBatchValidator

        assert isinstance(batch_service.validator, AssetBatchValidator)


# ============================================================================
# Batch Update Tests
# ============================================================================


class TestBatchUpdate:
    """测试批量更新功能"""

    def test_batch_update_empty_list(self, batch_service):
        """测试空资产列表批量更新"""
        result = batch_service.batch_update(asset_ids=[], updates={})

        assert result.total_count == 0
        assert result.success_count == 0
        assert result.failed_count == 0
        assert result.updated_ids == []

    def test_batch_update_none_list(self, batch_service):
        """测试 None 资产列表批量更新"""
        result = batch_service.batch_update(asset_ids=None, updates={})

        assert result.total_count == 0
        assert result.success_count == 0

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_update_single_asset_success(
        self, mock_asset_crud, batch_service, mock_db, mock_asset
    ):
        """测试单个资产批量更新成功"""
        mock_asset_crud.get.return_value = mock_asset
        mock_asset_crud.update.return_value = mock_asset

        with patch("src.services.asset.batch_service.history_crud") as mock_history:
            mock_history.create.return_value = MagicMock()

            result = batch_service.batch_update(
                asset_ids=["asset_1"],
                updates={"usage_status": "出租"},
                operator="test_user",
            )

            assert result.total_count == 1
            assert result.success_count == 1
            assert result.failed_count == 0
            assert len(result.updated_ids) == 1
            assert "asset_1" in result.updated_ids
            mock_db.commit.assert_called()

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_update_multiple_assets_success(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试多个资产批量更新成功"""
        mock_assets = [
            MagicMock(id=f"asset_{i}", property_name=f"物业{i}") for i in range(1, 4)
        ]
        mock_asset_crud.get.side_effect = mock_assets
        mock_asset_crud.update.return_value = MagicMock()

        with patch("src.services.asset.batch_service.history_crud") as mock_history:
            mock_history.create.return_value = MagicMock()

            result = batch_service.batch_update(
                asset_ids=["asset_1", "asset_2", "asset_3"],
                updates={"usage_status": "出租"},
                operator="test_user",
            )

            assert result.total_count == 3
            assert result.success_count == 3
            assert result.failed_count == 0
            assert len(result.updated_ids) == 3
            mock_db.commit.assert_called()

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_update_asset_not_found(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试资产不存在时的处理"""
        mock_asset_crud.get.return_value = None

        result = batch_service.batch_update(
            asset_ids=["nonexistent_asset"],
            updates={"usage_status": "出租"},
        )

        assert result.total_count == 1
        assert result.success_count == 0
        assert result.failed_count == 1
        assert len(result.errors) == 1
        assert "资产不存在" in result.errors[0]["error"]
        assert result.errors[0]["error_type"] == "NotFoundError"

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_update_partial_failure(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试部分成功部分失败的情况"""
        asset_1 = MagicMock(id="asset_1")
        MagicMock(id="asset_2")

        mock_asset_crud.get.side_effect = [asset_1, None]
        mock_asset_crud.update.return_value = asset_1

        with patch("src.services.asset.batch_service.history_crud") as mock_history:
            mock_history.create.return_value = MagicMock()

            result = batch_service.batch_update(
                asset_ids=["asset_1", "asset_2"],
                updates={"usage_status": "出租"},
            )

            assert result.total_count == 2
            assert result.success_count == 1
            assert result.failed_count == 1
            assert len(result.updated_ids) == 1
            assert "asset_1" in result.updated_ids

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_update_exception_during_update(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试更新过程中的异常处理"""
        mock_asset = MagicMock(id="asset_1")
        mock_asset_crud.get.return_value = mock_asset
        mock_asset_crud.update.side_effect = Exception("Database error")

        result = batch_service.batch_update(
            asset_ids=["asset_1"],
            updates={"usage_status": "出租"},
        )

        assert result.total_count == 1
        assert result.success_count == 0
        assert result.failed_count == 1
        assert len(result.errors) == 1
        assert "Database error" in result.errors[0]["error"]

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_update_with_savepoint_rollback(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试 SAVEPOINT 回滚机制"""
        mock_asset = MagicMock(id="asset_1")
        mock_asset_crud.get.return_value = mock_asset
        mock_asset_crud.update.side_effect = Exception("Update failed")

        # 模拟 begin_nested
        mock_savepoint = MagicMock()
        mock_db.begin_nested.return_value = mock_savepoint

        result = batch_service.batch_update(
            asset_ids=["asset_1"],
            updates={"usage_status": "出租"},
        )

        # 验证失败但没有提交
        assert result.failed_count == 1
        assert result.success_count == 0
        mock_db.rollback.assert_called_once()

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_update_history_logging(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试历史记录日志"""
        mock_asset = MagicMock(id="asset_1")
        mock_asset_crud.get.return_value = mock_asset
        mock_asset_crud.update.return_value = mock_asset

        with patch("src.services.asset.batch_service.history_crud") as mock_history:
            mock_history.create.return_value = MagicMock()

            batch_service.batch_update(
                asset_ids=["asset_1"],
                updates={"usage_status": "出租", "tenant_name": "新租户"},
                operator="admin_user",
            )

            # 验证历史记录被创建
            assert mock_history.create.called
            call_args = mock_history.create.call_args
            assert call_args[1]["operator"] == "admin_user"
            assert "批量更新字段" in call_args[1]["description"]

    def test_batch_update_empty_updates(self, batch_service, mock_db):
        """测试空更新字典"""
        mock_asset = MagicMock(id="asset_1")
        mock_db.begin_nested.return_value = MagicMock()

        with patch("src.services.asset.batch_service.asset_crud") as mock_crud:
            mock_crud.get.return_value = mock_asset
            mock_crud.update.return_value = mock_asset

            with patch("src.services.asset.batch_service.history_crud"):
                result = batch_service.batch_update(
                    asset_ids=["asset_1"],
                    updates={},  # 空更新
                )

                # 应该成功，即使更新为空
                assert result.total_count == 1
                assert result.success_count == 1

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_update_field_extraction_from_error(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试从错误消息中提取字段名"""
        mock_asset = MagicMock(id="asset_1")
        mock_asset_crud.get.return_value = mock_asset
        mock_asset_crud.update.side_effect = ValueError(
            "usage_status\n  Field required"
        )

        result = batch_service.batch_update(
            asset_ids=["asset_1"],
            updates={"usage_status": "invalid_value"},
        )

        assert len(result.errors) == 1
        error = result.errors[0]
        assert "error_type" in error
        assert "field_context" in error


# ============================================================================
# Batch Update All Tests
# ============================================================================


class TestBatchUpdateAll:
    """测试更新所有资产功能"""

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_update_all_flag(self, mock_asset_crud, batch_service, mock_db):
        """测试 should_update_all=True 标志"""
        mock_assets = [MagicMock(id=f"asset_{i}") for i in range(1, 4)]
        mock_asset_crud.get_multi_with_search.return_value = (mock_assets, None)
        mock_asset_crud.get.side_effect = mock_assets
        mock_asset_crud.update.return_value = MagicMock()

        with patch("src.services.asset.batch_service.history_crud"):
            result = batch_service.batch_update(
                asset_ids=None,
                updates={"usage_status": "出租"},
                should_update_all=True,
            )

            assert result.total_count == 3
            mock_asset_crud.get_multi_with_search.assert_called_once_with(
                db=mock_db, skip=0, limit=10000
            )

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_update_all_empty_database(self, mock_asset_crud, batch_service):
        """测试空数据库时更新所有"""
        mock_asset_crud.get_multi_with_search.return_value = ([], None)

        result = batch_service.batch_update(
            asset_ids=None,
            updates={"usage_status": "出租"},
            should_update_all=True,  # Updated parameter name: update_all -> should_update_all
        )

        assert result.total_count == 0
        assert result.success_count == 0


# ============================================================================
# Batch Delete Tests
# ============================================================================


class TestBatchDelete:
    """测试批量删除功能"""

    def test_batch_delete_empty_list(self, batch_service):
        """测试空资产列表删除"""
        result = batch_service.batch_delete(asset_ids=[])

        assert result.total_count == 0
        assert result.success_count == 0
        assert result.failed_count == 0

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_delete_single_asset_success(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试单个资产删除成功"""
        mock_asset = MagicMock(id="asset_1")
        mock_asset_crud.get.return_value = mock_asset
        mock_asset_crud.remove.return_value = None

        result = batch_service.batch_delete(
            asset_ids=["asset_1"],
            operator="test_user",
        )

        assert result.total_count == 1
        assert result.success_count == 1
        assert result.failed_count == 0
        mock_db.commit.assert_called_once()
        mock_asset_crud.remove.assert_called_once_with(
            db=mock_db, id="asset_1", commit=False
        )

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_delete_multiple_assets_success(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试多个资产删除成功"""
        mock_assets = [MagicMock(id=f"asset_{i}") for i in range(1, 4)]
        mock_asset_crud.get.side_effect = mock_assets
        mock_asset_crud.remove.return_value = None

        result = batch_service.batch_delete(
            asset_ids=["asset_1", "asset_2", "asset_3"],
        )

        assert result.total_count == 3
        assert result.success_count == 3
        assert result.failed_count == 0
        assert mock_asset_crud.remove.call_count == 3

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_delete_asset_not_found(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试删除不存在的资产"""
        mock_asset_crud.get.return_value = None

        result = batch_service.batch_delete(asset_ids=["nonexistent_asset"])

        assert result.total_count == 1
        assert result.success_count == 0
        assert result.failed_count == 1
        assert len(result.errors) == 1
        assert "资产不存在" in result.errors[0]["error"]

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_delete_with_exception_rollback(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试删除异常时的事务回滚"""
        mock_asset = MagicMock(id="asset_1")
        mock_asset_crud.get.return_value = mock_asset
        mock_asset_crud.remove.side_effect = Exception("Delete failed")

        with pytest.raises(Exception) as excinfo:
            batch_service.batch_delete(asset_ids=["asset_1"])

        assert "Delete failed" in str(excinfo.value)
        mock_db.rollback.assert_called_once()
        mock_db.commit.assert_not_called()

    @patch("src.services.asset.batch_service.asset_crud")
    def test_batch_delete_partial_failure_triggers_rollback(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试删除过程中一个失败导致全部回滚"""
        asset_1 = MagicMock(id="asset_1")
        asset_2 = MagicMock(id="asset_2")

        mock_asset_crud.get.side_effect = [asset_1, asset_2]
        mock_asset_crud.remove.side_effect = [None, Exception("Second delete failed")]

        with pytest.raises(Exception):
            batch_service.batch_delete(asset_ids=["asset_1", "asset_2"])

        # 验证事务被回滚
        mock_db.rollback.assert_called_once()


# ============================================================================
# Validate Asset Data Tests
# ============================================================================


class TestValidateAssetData:
    """测试资产数据验证功能"""

    def test_validate_valid_data(self, batch_service, valid_asset_data):
        """测试验证有效数据"""
        is_valid, errors, warnings, validated_fields = (
            batch_service.validate_asset_data(data=valid_asset_data)
        )

        assert is_valid is True
        assert len(errors) == 0
        assert len(validated_fields) > 0

    def test_validate_invalid_data(self, batch_service, invalid_asset_data):
        """测试验证无效数据"""
        is_valid, errors, warnings, validated_fields = (
            batch_service.validate_asset_data(data=invalid_asset_data)
        )

        assert is_valid is False
        assert len(errors) > 0
        error_fields = [e["field"] for e in errors]
        assert "property_name" in error_fields

    def test_validate_missing_required_fields(self, batch_service):
        """测试缺少必填字段"""
        data = {
            "property_name": "测试",
            # 缺少其他必填字段
        }

        is_valid, errors, warnings, validated_fields = (
            batch_service.validate_asset_data(data=data)
        )

        assert is_valid is False
        assert len(errors) >= 4  # 至少缺少4个必填字段

    def test_validate_invalid_numeric_fields(self, batch_service):
        """测试无效数值字段"""
        data = {
            "property_name": "测试物业",
            "address": "北京市朝阳区",
            "ownership_status": "已确权",
            "property_nature": "商业",
            "usage_status": "在用",
            "land_area": "not_a_number",
        }

        is_valid, errors, warnings, validated_fields = (
            batch_service.validate_asset_data(data=data)
        )

        assert is_valid is False
        assert any(e["field"] == "land_area" for e in errors)

    def test_validate_area_consistency_error(self, batch_service):
        """测试面积一致性错误"""
        data = {
            "property_name": "测试物业",
            "address": "北京市朝阳区",
            "ownership_status": "已确权",
            "property_nature": "商业",
            "usage_status": "在用",
            "rentable_area": 100.0,
            "rented_area": 150.0,  # 大于可出租面积
        }

        is_valid, errors, warnings, validated_fields = (
            batch_service.validate_asset_data(data=data)
        )

        assert is_valid is False
        assert any("已出租面积不能大于可出租面积" in e["error"] for e in errors)

    def test_validate_invalid_date_format(self, batch_service):
        """测试无效日期格式"""
        data = {
            "property_name": "测试物业",
            "address": "北京市朝阳区",
            "ownership_status": "已确权",
            "property_nature": "商业",
            "usage_status": "在用",
            "contract_start_date": "2024/01/01",  # 错误格式
        }

        is_valid, errors, warnings, validated_fields = (
            batch_service.validate_asset_data(data=data)
        )

        # 日期格式错误应该被检测到
        assert any(e["field"] == "contract_start_date" for e in errors)

    def test_validate_suggestions_warnings(self, batch_service):
        """测试建议性警告"""
        data = {
            "property_name": "测试物业",
            "address": "北京市朝阳区",
            "ownership_status": "已确权",
            "property_nature": "商业",
            "usage_status": "在用",
            # 缺少建议字段
        }

        is_valid, errors, warnings, validated_fields = (
            batch_service.validate_asset_data(data=data)
        )

        # 数据有效但应该有警告
        assert is_valid is True
        assert len(warnings) > 0
        assert len(errors) == 0

    def test_validate_custom_rules(self, batch_service):
        """测试自定义验证规则"""
        data = {
            "property_name": "测试物业",
            "address": "北京市朝阳区",
            "ownership_status": "已确权",
            "property_nature": "商业",
            "usage_status": "在用",
            "rentable_area": 100.0,
            "rented_area": 150.0,
        }

        # 只验证数据格式，不验证必填字段
        is_valid, errors, warnings, validated_fields = (
            batch_service.validate_asset_data(data=data, validate_rules=["data_format"])
        )

        # 面积一致性应该被检测到
        assert any("已出租面积不能大于可出租面积" in e["error"] for e in errors)

    def test_validate_with_enum_validation_service(self, batch_service):
        """测试带枚举验证服务的验证"""
        mock_enum_service = MagicMock()
        mock_enum_service.validate_value.return_value = (True, "")

        data = {
            "property_name": "测试物业",
            "address": "北京市朝阳区",
            "ownership_status": "已确权",
            "property_nature": "商业",
            "usage_status": "在用",
        }

        is_valid, errors, warnings, validated_fields = (
            batch_service.validate_asset_data(
                data=data, enum_validation_service=mock_enum_service
            )
        )

        # 验证枚举服务被调用
        mock_enum_service.validate_value.assert_called_once()
        assert "ownership_status" in validated_fields

    def test_validate_enum_validation_failure(self, batch_service):
        """测试枚举验证失败"""
        mock_enum_service = MagicMock()
        mock_enum_service.validate_value.return_value = (
            False,
            "Invalid ownership status value",
        )

        data = {
            "property_name": "测试物业",
            "address": "北京市朝阳区",
            "ownership_status": "invalid_value",
            "property_nature": "商业",
            "usage_status": "在用",
        }

        is_valid, errors, warnings, validated_fields = (
            batch_service.validate_asset_data(
                data=data, enum_validation_service=mock_enum_service
            )
        )

        assert is_valid is False
        assert any(e["field"] == "ownership_status" for e in errors)


# ============================================================================
# Helper Method Tests
# ============================================================================


class TestHelperMethods:
    """测试辅助方法"""

    def test_extract_field_from_pydantic_error(self, batch_service):
        """测试从 Pydantic 错误中提取字段名"""
        error_msg = "usage_status\n  Field required"
        field = batch_service._extract_field_from_error(error_msg)
        assert field == "usage_status"

    def test_extract_field_from_value_error(self, batch_service):
        """测试从 ValueError 中提取字段名"""
        error_msg = "land_area\n  Value error"
        field = batch_service._extract_field_from_error(error_msg)
        assert field == "land_area"

    def test_extract_field_no_match(self, batch_service):
        """测试无匹配时返回 None"""
        error_msg = "Some random error message"
        field = batch_service._extract_field_from_error(error_msg)
        assert field is None

    def test_extract_field_complex_error(self, batch_service):
        """测试复杂错误消息"""
        error_msg = "tenant_name\n  Field required"
        field = batch_service._extract_field_from_error(error_msg)
        assert field == "tenant_name"


# ============================================================================
# Progress Tracking Tests
# ============================================================================


class TestProgressTracking:
    """测试进度跟踪功能"""

    @patch("src.services.asset.batch_service.asset_crud")
    def test_progress_tracking_during_batch_update(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试批量更新时的进度跟踪"""
        mock_assets = [MagicMock(id=f"asset_{i}") for i in range(1, 6)]
        mock_asset_crud.get.side_effect = mock_assets
        mock_asset_crud.update.return_value = MagicMock()

        with patch("src.services.asset.batch_service.history_crud"):
            result = batch_service.batch_update(
                asset_ids=["asset_1", "asset_2", "asset_3", "asset_4", "asset_5"],
                updates={"usage_status": "出租"},
            )

            # 验证进度计数
            assert result.total_count == 5
            assert result.success_count == 5
            assert len(result.updated_ids) == 5

    @patch("src.services.asset.batch_service.asset_crud")
    def test_progress_tracking_with_failures(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试有失败时的进度跟踪"""
        # 混合成功和失败
        mock_asset_crud.get.side_effect = [
            MagicMock(id="asset_1"),
            None,  # 不存在
            MagicMock(id="asset_3"),
            Exception("Error"),
        ]
        mock_asset_crud.update.side_effect = [
            MagicMock(),
            Exception("Update failed"),
        ]

        with patch("src.services.asset.batch_service.history_crud"):
            result = batch_service.batch_update(
                asset_ids=["asset_1", "asset_2", "asset_3", "asset_4"],
                updates={"usage_status": "出租"},
            )

            # 验证进度
            assert result.total_count == 4
            assert result.success_count >= 0
            assert result.failed_count >= 0
            assert result.success_count + result.failed_count == 4


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """测试错误处理机制"""

    @patch("src.services.asset.batch_service.asset_crud")
    def test_comprehensive_error_reporting(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试全面的错误报告"""
        mock_asset = MagicMock(id="asset_1")
        mock_asset_crud.get.return_value = mock_asset
        mock_asset_crud.update.side_effect = ValueError(
            "Validation error: usage_status"
        )

        result = batch_service.batch_update(
            asset_ids=["asset_1"],
            updates={"usage_status": "invalid"},
        )

        error = result.errors[0]
        assert error["asset_id"] == "asset_1"
        assert "error" in error
        assert "error_type" in error
        assert "field_context" in error

    @patch("src.services.asset.batch_service.asset_crud")
    def test_multiple_different_errors(self, mock_asset_crud, batch_service, mock_db):
        """测试多个不同的错误"""
        mock_asset_crud.get.side_effect = [
            MagicMock(id="asset_1"),
            None,  # 不存在
            MagicMock(id="asset_3"),
        ]
        mock_asset_crud.update.side_effect = [
            MagicMock(),
            Exception("Database error"),
        ]

        with patch("src.services.asset.batch_service.history_crud"):
            result = batch_service.batch_update(
                asset_ids=["asset_1", "asset_2", "asset_3"],
                updates={"usage_status": "出租"},
            )

            # 应该有不同类型的错误
            assert len(result.errors) >= 1
            error_types = [e.get("error_type") for e in result.errors]
            assert "NotFoundError" in error_types or "Exception" in error_types

    @patch("src.services.asset.batch_service.asset_crud")
    def test_transaction_commit_on_partial_success(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试部分成功时提交事务"""
        mock_asset = MagicMock(id="asset_1")
        mock_asset_crud.get.return_value = mock_asset
        mock_asset_crud.update.return_value = mock_asset

        with patch("src.services.asset.batch_service.history_crud"):
            result = batch_service.batch_update(
                asset_ids=["asset_1"],
                updates={"usage_status": "出租"},
            )

            # 有成功时应该提交
            assert result.success_count > 0
            mock_db.commit.assert_called()

    @patch("src.services.asset.batch_service.asset_crud")
    def test_transaction_rollback_on_all_failure(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试全部失败时回滚事务"""
        mock_asset_crud.get.return_value = None

        result = batch_service.batch_update(
            asset_ids=["asset_1", "asset_2"],
            updates={"usage_status": "出租"},
        )

        # 全部失败应该回滚
        assert result.success_count == 0
        assert result.failed_count == 2
        mock_db.rollback.assert_called()


# ============================================================================
# Status Reporting Tests
# ============================================================================


class TestStatusReporting:
    """测试状态报告功能"""

    @patch("src.services.asset.batch_service.asset_crud")
    def test_result_to_dict_status_report(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试结果转换为字典状态报告"""
        mock_asset = MagicMock(id="asset_1")
        mock_asset_crud.get.return_value = mock_asset
        mock_asset_crud.update.return_value = mock_asset

        with patch("src.services.asset.batch_service.history_crud"):
            result = batch_service.batch_update(
                asset_ids=["asset_1"],
                updates={"usage_status": "出租"},
            )

            # 转换为字典
            status_dict = result.to_dict()

            # 验证所有状态字段
            assert "success_count" in status_dict
            assert "failed_count" in status_dict
            assert "total_count" in status_dict
            assert "errors" in status_dict
            assert "updated_assets" in status_dict

    @patch("src.services.asset.batch_service.asset_crud")
    def test_comprehensive_status_report(self, mock_asset_crud, batch_service, mock_db):
        """测试全面的状态报告"""
        mock_assets = [MagicMock(id=f"asset_{i}") for i in range(1, 4)]
        mock_asset_crud.get.side_effect = mock_assets
        mock_asset_crud.update.side_effect = [
            MagicMock(),
            None,
            Exception("Error"),
        ]

        with patch("src.services.asset.batch_service.history_crud"):
            result = batch_service.batch_update(
                asset_ids=["asset_1", "asset_2", "asset_3"],
                updates={"usage_status": "出租"},
            )

            # 验证状态报告完整性
            assert result.total_count == 3
            assert result.success_count + result.failed_count == 3
            assert len(result.errors) == result.failed_count
            assert len(result.updated_ids) == result.success_count


# ============================================================================
# Integration Scenarios Tests
# ============================================================================


class TestIntegrationScenarios:
    """测试集成场景"""

    @patch("src.services.asset.batch_service.asset_crud")
    def test_real_world_batch_update_scenario(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试真实世界的批量更新场景"""
        # 模拟真实场景：100个资产，95个成功，5个失败
        asset_ids = [f"asset_{i:03d}" for i in range(1, 101)]
        mock_assets = [MagicMock(id=id) for id in asset_ids]

        # 设置前95个成功，后5个失败
        mock_asset_crud.get.side_effect = mock_assets
        mock_asset_crud.update.side_effect = [MagicMock()] * 95 + [
            Exception("Update failed")
        ] * 5

        with patch("src.services.asset.batch_service.history_crud"):
            result = batch_service.batch_update(
                asset_ids=asset_ids,
                updates={"usage_status": "出租"},
            )

            # 验证结果
            assert result.total_count == 100
            assert result.success_count == 95
            assert result.failed_count == 5
            assert len(result.errors) == 5
            assert len(result.updated_ids) == 95

    @patch("src.services.asset.batch_service.asset_crud")
    def test_validation_before_batch_update(
        self, mock_asset_crud, batch_service, mock_db
    ):
        """测试批量更新前的验证流程"""
        # 首先验证数据
        data = {
            "property_name": "测试物业",
            "address": "北京市朝阳区",
            "ownership_status": "已确权",
            "property_nature": "商业",
            "usage_status": "在用",
        }

        is_valid, errors, warnings, validated_fields = (
            batch_service.validate_asset_data(data=data)
        )

        assert is_valid is True

        # 然后执行批量更新
        mock_asset = MagicMock(id="asset_1")
        mock_asset_crud.get.return_value = mock_asset
        mock_asset_crud.update.return_value = mock_asset

        with patch("src.services.asset.batch_service.history_crud"):
            result = batch_service.batch_update(
                asset_ids=["asset_1"],
                updates=data,
            )

            assert result.success_count == 1
