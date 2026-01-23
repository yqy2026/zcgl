"""
测试 ExcelImportService (Excel导入服务)
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from src.core.exception_handler import BusinessValidationError
from src.services.excel.excel_import_service import FIELD_MAPPING, ExcelImportService


@pytest.fixture
def mock_db():
    """创建模拟数据库会话"""
    return MagicMock(spec=Session)


@pytest.fixture
def excel_service(mock_db):
    """创建 ExcelImportService 实例"""
    return ExcelImportService(mock_db)


class TestExcelImportServiceErrorHandling:
    """测试 ExcelImportService 错误处理"""

    @pytest.mark.asyncio
    async def test_import_empty_file(self, excel_service):
        """测试导入空文件"""
        with patch("pandas.read_excel") as mock_read:
            mock_read.return_value = pd.DataFrame()

            result = await excel_service.import_assets_from_excel(file_path="test.xlsx")

            assert result["total"] == 0
            assert result["success"] == 0
            assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_import_with_validation_errors_skip_mode(self, excel_service):
        """测试验证失败时跳过错误模式"""
        # Mock 数据帧
        with patch("pandas.read_excel") as mock_read:
            mock_read.return_value = pd.DataFrame(
                {
                    "物业名称": ["", "有效资产"],  # 第一行空名称
                    "物业地址": ["地址1", "地址2"],
                }
            )

            # Mock 验证器返回失败
            excel_service.validator.validate_all = MagicMock(
                side_effect=[
                    (False, [{"field": "property_name", "error": "不能为空"}], [], []),
                    (True, [], [], ["property_name"]),
                ]
            )

            # Mock _map_excel_row_to_asset_data (returns tuple)
            excel_service._map_excel_row_to_asset_data = MagicMock(
                side_effect=[
                    ({"property_name": "", "address": "地址1"}, []),
                    ({"property_name": "有效资产", "address": "地址2"}, []),
                ]
            )

            result = await excel_service.import_assets_from_excel(
                file_path="test.xlsx",
                should_validate_data=True,
                should_create_assets=False,
                should_skip_errors=True,
            )

            assert result["total"] == 2
            # Row 1: validation error → failed
            # Row 2: passes validation, counted as success (even though not created due to create_assets=False)
            assert result["failed"] == 1
            assert result["success"] == 1
            assert (
                result["created_assets"] == 0
            )  # Nothing created because create_assets=False
            assert len(result["errors"]) == 1
            assert "property_name" in result["errors"][0]["error"]

    @pytest.mark.asyncio
    async def test_import_with_validation_errors_strict_mode(self, excel_service):
        """测试验证失败时严格模式抛出异常"""
        with patch("pandas.read_excel") as mock_read:
            mock_read.return_value = pd.DataFrame(
                {
                    "物业名称": [""],
                    "物业地址": ["地址1"],
                }
            )

            excel_service.validator.validate_all = MagicMock(
                return_value=(
                    False,
                    [{"field": "property_name", "error": "不能为空"}],
                    [],
                    [],
                )
            )

            excel_service._map_excel_row_to_asset_data = MagicMock(
                return_value=({"property_name": "", "address": "地址1"}, [])
            )

            with pytest.raises(BusinessValidationError) as excinfo:
                await excel_service.import_assets_from_excel(
                    file_path="test.xlsx",
                    should_validate_data=True,
                    should_create_assets=False,
                    should_skip_errors=False,
                )

            assert "验证失败" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_import_with_duplicate_assets(self, excel_service, mock_db):
        """测试导入重复资产时跳过"""
        with patch("pandas.read_excel") as mock_read:
            mock_read.return_value = pd.DataFrame(
                {
                    "物业名称": ["已存在资产"],
                    "物业地址": ["地址1"],
                }
            )

            excel_service.validator.validate_all = MagicMock(
                return_value=(True, [], [], ["property_name"])
            )

            excel_service._map_excel_row_to_asset_data = MagicMock(
                return_value=({"property_name": "已存在资产", "address": "地址1"}, [])
            )

            # Mock 找到已存在的资产
            excel_service._find_existing_asset = MagicMock(
                return_value=MagicMock(id="existing_id")
            )

            result = await excel_service.import_assets_from_excel(
                file_path="test.xlsx",
                should_validate_data=True,
                should_create_assets=True,
                should_update_existing=False,
            )

            assert result["success"] == 1
            assert result["created_assets"] == 0
            assert len(result["warnings"]) == 1
            assert "已存在" in result["warnings"][0]["warning"]

    @pytest.mark.asyncio
    async def test_import_batch_commit_strategy(self, excel_service, mock_db):
        """测试批量提交策略"""
        # 创建150行数据，batch_size=50
        with patch("pandas.read_excel") as mock_read:
            mock_read.return_value = pd.DataFrame(
                {
                    "物业名称": [f"资产{i}" for i in range(150)],
                    "物业地址": [f"地址{i}" for i in range(150)],
                }
            )

            excel_service.validator.validate_all = MagicMock(
                return_value=(True, [], [], ["property_name"])
            )

            # 提供完整的资产数据（包含必填字段）
            def make_asset_data(row, idx):
                return (
                    {
                        "property_name": f"资产{idx}",
                        "address": f"地址{idx}",
                        "ownership_entity": "测试单位",
                        "ownership_status": "自有",
                        "property_nature": "商业",
                        "usage_status": "使用中",
                    },
                    [],  # parse_warnings
                )

            excel_service._map_excel_row_to_asset_data = MagicMock(
                side_effect=make_asset_data
            )

            excel_service._find_existing_asset = MagicMock(return_value=None)

            with patch(
                "src.services.excel.excel_import_service.asset_crud"
            ) as mock_crud:
                mock_crud.create.return_value = MagicMock(id="new_id")

                result = await excel_service.import_assets_from_excel(
                    file_path="test.xlsx",
                    should_validate_data=True,
                    should_create_assets=True,
                    should_skip_errors=True,
                    batch_size=50,
                )

                assert result["total"] == 150
                assert result["success"] == 150
                assert result["committed_batches"] >= 3  # 多批次提交
                # 验证 commit 被调用多次
                assert mock_db.commit.call_count >= 3

    @pytest.mark.asyncio
    async def test_import_rollback_on_error_strict_mode(self, excel_service, mock_db):
        """测试严格模式下错误时回滚"""
        with patch("pandas.read_excel") as mock_read:
            mock_read.return_value = pd.DataFrame(
                {
                    "物业名称": ["资产1", "资产2"],
                    "物业地址": ["地址1", "地址2"],
                }
            )

            excel_service.validator.validate_all = MagicMock(
                return_value=(True, [], [], ["property_name"])
            )

            # 提供完整的资产数据（包含必填字段）
            complete_assets = [
                (
                    {
                        "property_name": "资产1",
                        "address": "地址1",
                        "ownership_entity": "测试单位",
                        "ownership_status": "自有",
                        "property_nature": "商业",
                        "usage_status": "使用中",
                    },
                    [],  # parse_warnings
                ),
                (
                    {
                        "property_name": "资产2",
                        "address": "地址2",
                        "ownership_entity": "测试单位",
                        "ownership_status": "自有",
                        "property_nature": "商业",
                        "usage_status": "使用中",
                    },
                    [],  # parse_warnings
                ),
            ]

            excel_service._map_excel_row_to_asset_data = MagicMock(
                side_effect=complete_assets
            )

            excel_service._find_existing_asset = MagicMock(return_value=None)

            with patch(
                "src.services.excel.excel_import_service.asset_crud"
            ) as mock_crud:
                # 第一个成功，第二个失败
                mock_crud.create.side_effect = [
                    MagicMock(id="id1"),
                    Exception("创建失败"),
                ]

                with pytest.raises(Exception) as excinfo:
                    await excel_service.import_assets_from_excel(
                        file_path="test.xlsx",
                        should_validate_data=True,
                        should_create_assets=True,
                        should_skip_errors=False,
                    )

                assert "创建失败" in str(excinfo.value)
                mock_db.rollback.assert_called()

    @pytest.mark.asyncio
    async def test_import_date_parsing_failure(self, excel_service):
        """测试日期解析失败处理"""
        with patch("pandas.read_excel") as mock_read:
            mock_read.return_value = pd.DataFrame(
                {
                    "物业名称": ["资产1"],
                    "物业地址": ["地址1"],
                    "(当前)接收协议开始日期": ["invalid_date"],
                }
            )

            # Mock _map_excel_row_to_asset_data 正常处理
            excel_service._map_excel_row_to_asset_data = MagicMock(
                return_value=(
                    {
                        "property_name": "资产1",
                        "address": "地址1",
                        "operation_agreement_start_date": None,  # 日期解析失败返回None
                    },
                    [],  # parse_warnings
                )
            )

            excel_service.validator.validate_all = MagicMock(
                return_value=(True, [], [], ["property_name"])
            )

            result = await excel_service.import_assets_from_excel(
                file_path="test.xlsx",
                should_validate_data=True,
                should_create_assets=False,
            )

            # 日期解析失败不应导致整行失败
            assert result["success"] == 1
            assert result["failed"] == 0


# ============================================================================
# Test _map_excel_row_to_asset_data - Field Mapping
# ============================================================================
class TestFieldMapping:
    """测试字段映射功能"""

    def test_map_all_fields(self, excel_service):
        """测试映射所有字段"""
        row = pd.Series(
            {
                "权属方": "测试权属方",
                "权属类别": "国有",
                "项目名称": "测试项目",
                "物业名称": "测试物业",
                "物业地址": "测试地址",
                "土地面积(平方米)": 1000.0,
                "实际房产面积(平方米)": 800.0,
                "非经营物业面积(平方米)": 200.0,
                "可出租面积(平方米)": 600.0,
                "已出租面积(平方米)": 400.0,
                "确权状态（已确权、未确权、部分确权）": "已确权",
                "证载用途（商业、住宅、办公、厂房、车库等）": "商业",
                "实际用途（商业、住宅、办公、厂房、车库等）": "商业",
                "业态类别": "零售",
                "使用状态（出租、闲置、自用、公房、其他）": "出租",
                "是否涉诉": "是",
                "物业性质（经营类、非经营类）": "经营类",
                "是否计入出租率": "是",
                "接收模式": "租赁",
                "(当前)接收协议开始日期": "2024-01-01",
                "(当前)接收协议结束日期": "2024-12-31",
            }
        )

        asset_data, warnings = excel_service._map_excel_row_to_asset_data(row, 1)

        assert asset_data["ownership_entity"] == "测试权属方"
        assert asset_data["ownership_category"] == "国有"
        assert asset_data["project_name"] == "测试项目"
        assert asset_data["property_name"] == "测试物业"
        assert asset_data["address"] == "测试地址"
        assert asset_data["land_area"] == 1000.0
        assert asset_data["actual_property_area"] == 800.0
        assert asset_data["non_commercial_area"] == 200.0
        assert asset_data["rentable_area"] == 600.0
        assert asset_data["rented_area"] == 400.0
        assert asset_data["ownership_status"] == "已确权"
        assert asset_data["certificate_usage"] == "商业"
        assert asset_data["actual_usage"] == "商业"
        assert asset_data["business_category"] == "零售"
        assert asset_data["usage_status"] == "出租"
        assert asset_data["is_litigated"] is True
        assert asset_data["property_nature"] == "经营类"
        assert asset_data["include_in_occupancy_rate"] is True
        assert asset_data["reception_mode"] == "租赁"
        assert (
            asset_data["operation_agreement_start_date"] == datetime(2024, 1, 1).date()
        )
        assert (
            asset_data["operation_agreement_end_date"] == datetime(2024, 12, 31).date()
        )
        assert len(warnings) == 0

    def test_map_boolean_fields_true(self, excel_service):
        """测试布尔字段为True的情况"""
        row = pd.Series(
            {
                "物业名称": "测试",
                "物业地址": "地址",
                "是否涉诉": "是",
                "是否计入出租率": "True",
            }
        )

        asset_data, _ = excel_service._map_excel_row_to_asset_data(row, 1)

        assert asset_data["is_litigated"] is True
        assert asset_data["include_in_occupancy_rate"] is True

    def test_map_boolean_fields_false(self, excel_service):
        """测试布尔字段为False的情况"""
        row = pd.Series(
            {
                "物业名称": "测试",
                "物业地址": "地址",
                "是否涉诉": "否",
                "是否计入出租率": "false",
            }
        )

        asset_data, _ = excel_service._map_excel_row_to_asset_data(row, 1)

        assert asset_data["is_litigated"] is False
        assert asset_data["include_in_occupancy_rate"] is False

    def test_map_numeric_fields_invalid(self, excel_service):
        """测试无效数值字段"""
        row = pd.Series(
            {
                "物业名称": "测试",
                "物业地址": "地址",
                "土地面积(平方米)": "invalid",
                "可出租面积(平方米)": "abc",
            }
        )

        asset_data, warnings = excel_service._map_excel_row_to_asset_data(row, 1)

        assert asset_data["land_area"] is None
        assert asset_data["rentable_area"] is None
        assert len(warnings) == 2
        assert all("无法解析为数值" in w["warning"] for w in warnings)

    def test_map_date_fields_valid_string(self, excel_service):
        """测试有效日期字符串"""
        row = pd.Series(
            {
                "物业名称": "测试",
                "物业地址": "地址",
                "(当前)接收协议开始日期": "2024-01-15",
                "(当前)接收协议结束日期": "2024-12-31",
            }
        )

        asset_data, warnings = excel_service._map_excel_row_to_asset_data(row, 1)

        assert (
            asset_data["operation_agreement_start_date"] == datetime(2024, 1, 15).date()
        )
        assert (
            asset_data["operation_agreement_end_date"] == datetime(2024, 12, 31).date()
        )
        assert len(warnings) == 0

    def test_map_date_fields_invalid_string(self, excel_service):
        """测试无效日期字符串"""
        row = pd.Series(
            {
                "物业名称": "测试",
                "物业地址": "地址",
                "(当前)接收协议开始日期": "2024/01/15",  # 错误格式
                "(当前)接收协议结束日期": "invalid",
            }
        )

        asset_data, warnings = excel_service._map_excel_row_to_asset_data(row, 1)

        assert asset_data["operation_agreement_start_date"] is None
        assert asset_data["operation_agreement_end_date"] is None
        assert len(warnings) == 2
        assert all("日期格式无效" in w["warning"] for w in warnings)

    def test_map_date_fields_datetime_object(self, excel_service):
        """测试datetime对象"""
        test_date = datetime(2024, 6, 15, 10, 30, 0)
        row = pd.Series(
            {
                "物业名称": "测试",
                "物业地址": "地址",
                "(当前)接收协议开始日期": test_date,
            }
        )

        asset_data, warnings = excel_service._map_excel_row_to_asset_data(row, 1)

        assert asset_data["operation_agreement_start_date"] == test_date.date()
        assert len(warnings) == 0

    def test_map_missing_optional_fields(self, excel_service):
        """测试缺少可选字段"""
        row = pd.Series({"物业名称": "测试", "物业地址": "地址"})

        asset_data, warnings = excel_service._map_excel_row_to_asset_data(row, 1)

        assert asset_data["property_name"] == "测试"
        assert asset_data["address"] == "地址"
        assert "ownership_entity" not in asset_data
        assert "land_area" not in asset_data
        assert len(warnings) == 0

    def test_map_nan_values(self, excel_service):
        """测试NaN值"""
        row = pd.Series(
            {
                "物业名称": "测试",
                "物业地址": "地址",
                "土地面积(平方米)": None,
                "是否涉诉": None,
            }
        )

        asset_data, warnings = excel_service._map_excel_row_to_asset_data(row, 1)

        assert asset_data["property_name"] == "测试"
        assert "land_area" not in asset_data
        assert "is_litigated" not in asset_data


# ============================================================================
# Test _find_existing_asset
# ============================================================================
class TestFindExistingAsset:
    """测试查找已存在资产"""

    @pytest.mark.asyncio
    async def test_find_existing_asset_found(self, excel_service, mock_db):
        """测试找到已存在资产"""
        asset_data = {"property_name": "测试物业", "address": "测试地址"}

        with patch("src.services.excel.excel_import_service.asset_crud") as mock_crud:
            mock_asset = MagicMock(id="existing_123")
            mock_crud.get_multi_with_search.return_value = ([mock_asset], 1)

            result = excel_service._find_existing_asset(asset_data)

            assert result is not None
            assert result.id == "existing_123"
            mock_crud.get_multi_with_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_existing_asset_not_found(self, excel_service, mock_db):
        """测试未找到资产"""
        asset_data = {"property_name": "新物业", "address": "新地址"}

        with patch("src.services.excel.excel_import_service.asset_crud") as mock_crud:
            mock_crud.get_multi_with_search.return_value = ([], 0)

            result = excel_service._find_existing_asset(asset_data)

            assert result is None

    @pytest.mark.asyncio
    async def test_find_existing_asset_no_db(self, excel_service):
        """测试无数据库会话"""
        excel_service.db = None
        asset_data = {"property_name": "测试", "address": "地址"}

        result = excel_service._find_existing_asset(asset_data)

        assert result is None

    @pytest.mark.asyncio
    async def test_find_existing_asset_exception(self, excel_service, mock_db):
        """测试查找异常"""
        asset_data = {"property_name": "测试", "address": "地址"}

        with patch("src.services.excel.excel_import_service.asset_crud") as mock_crud:
            mock_crud.get_multi_with_search.side_effect = Exception("DB error")

            result = excel_service._find_existing_asset(asset_data)

            assert result is None


# ============================================================================
# Test Update Existing Assets
# ============================================================================
class TestUpdateExistingAssets:
    """测试更新已存在资产"""

    @pytest.mark.asyncio
    async def test_update_existing_asset(self, excel_service, mock_db):
        """测试更新已存在资产"""
        with patch("pandas.read_excel") as mock_read:
            mock_read.return_value = pd.DataFrame(
                {
                    "物业名称": ["已存在资产"],
                    "物业地址": ["地址1"],
                    "权属方": "新权属方",
                }
            )

            excel_service.validator.validate_all = MagicMock(
                return_value=(True, [], [], ["property_name"])
            )

            excel_service._map_excel_row_to_asset_data = MagicMock(
                return_value=(
                    {
                        "property_name": "已存在资产",
                        "address": "地址1",
                        "ownership_entity": "新权属方",
                    },
                    [],
                )
            )

            existing_asset = MagicMock(id="existing_id")
            excel_service._find_existing_asset = MagicMock(return_value=existing_asset)

            with patch(
                "src.services.excel.excel_import_service.asset_crud"
            ) as mock_crud:
                result = await excel_service.import_assets_from_excel(
                    file_path="test.xlsx",
                    should_validate_data=True,
                    should_create_assets=True,
                    should_update_existing=True,
                )

                assert result["updated_assets"] == 1
                assert result["created_assets"] == 0
                mock_crud.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_existing_asset_without_update(self, excel_service, mock_db):
        """测试不更新时跳过已存在资产"""
        with patch("pandas.read_excel") as mock_read:
            mock_read.return_value = pd.DataFrame(
                {
                    "物业名称": ["已存在资产"],
                    "物业地址": ["地址1"],
                }
            )

            excel_service.validator.validate_all = MagicMock(
                return_value=(True, [], [], ["property_name"])
            )

            excel_service._map_excel_row_to_asset_data = MagicMock(
                return_value=(
                    {"property_name": "已存在资产", "address": "地址1"},
                    [],
                )
            )

            existing_asset = MagicMock(id="existing_id")
            excel_service._find_existing_asset = MagicMock(return_value=existing_asset)

            with patch(
                "src.services.excel.excel_import_service.asset_crud"
            ) as mock_crud:
                result = await excel_service.import_assets_from_excel(
                    file_path="test.xlsx",
                    should_validate_data=True,
                    should_create_assets=True,
                    should_update_existing=False,
                )

                assert result["updated_assets"] == 0
                assert result["created_assets"] == 0
                assert len(result["warnings"]) == 1
                assert "已存在" in result["warnings"][0]["warning"]
                mock_crud.update.assert_not_called()


# ============================================================================
# Test validate_excel_file
# ============================================================================
class TestValidateExcelFile:
    """测试Excel文件验证"""

    def test_validate_file_not_exists(self, excel_service):
        """测试文件不存在"""
        with patch("os.path.exists", return_value=False):
            result = excel_service.validate_excel_file("nonexistent.xlsx")

            assert result["valid"] is False
            assert "不存在" in result["errors"][0]

    def test_validate_file_empty(self, excel_service):
        """测试空文件"""
        with patch("os.path.exists", return_value=True):
            with patch("pandas.read_excel") as mock_read:
                mock_read.return_value = pd.DataFrame()

                result = excel_service.validate_excel_file("empty.xlsx")

                assert result["valid"] is False
                assert "没有数据" in result["errors"][0]

    def test_validate_file_missing_required_columns(self, excel_service):
        """测试缺少必需列"""
        with patch("os.path.exists", return_value=True):
            with patch("pandas.read_excel") as mock_read:
                mock_read.return_value = pd.DataFrame({"权属方": ["测试"]})

                result = excel_service.validate_excel_file("invalid.xlsx")

                assert result["valid"] is False
                assert "缺少必需列" in result["errors"][0]
                assert "物业名称" in result["errors"][0]
                assert "物业地址" in result["errors"][0]

    def test_validate_file_success(self, excel_service):
        """测试验证成功"""
        with patch("os.path.exists", return_value=True):
            with patch("pandas.read_excel") as mock_read:
                mock_read.return_value = pd.DataFrame(
                    {
                        "物业名称": ["测试"],
                        "物业地址": ["地址"],
                        "权属方": ["权属"],
                    }
                )

                result = excel_service.validate_excel_file("valid.xlsx")

                assert result["valid"] is True
                assert result["total_rows"] == 1
                assert len(result["columns"]) == 3

    def test_validate_file_exception(self, excel_service):
        """测试验证异常"""
        with patch("os.path.exists", return_value=True):
            with patch("pandas.read_excel", side_effect=Exception("Read error")):
                result = excel_service.validate_excel_file("error.xlsx")

                assert result["valid"] is False
                assert "验证失败" in result["errors"][0]


# ============================================================================
# Test preview_excel_file
# ============================================================================
class TestPreviewExcelFile:
    """测试Excel文件预览"""

    @pytest.mark.asyncio
    async def test_preview_success(self, excel_service):
        """测试预览成功"""
        with patch("pandas.read_excel") as mock_read:
            mock_read.return_value = pd.DataFrame(
                {
                    "物业名称": ["资产1", "资产2", "资产3"],
                    "物业地址": ["地址1", "地址2", "地址3"],
                    "权属方": ["权属1", "权属2", "权属3"],
                }
            )

            result = await excel_service.preview_excel_file("test.xlsx", max_rows=2)

            assert result["total_rows"] == 3
            assert result["preview_rows"] == 2
            assert len(result["preview_data"]) == 2
            assert result["preview_data"][0]["物业名称"] == "资产1"
            assert result["preview_data"][1]["物业名称"] == "资产2"

    @pytest.mark.asyncio
    async def test_preview_with_nan_values(self, excel_service):
        """测试预览包含NaN值"""
        with patch("pandas.read_excel") as mock_read:
            mock_read.return_value = pd.DataFrame(
                {
                    "物业名称": ["资产1", None, "资产3"],
                    "物业地址": ["地址1", "地址2", None],
                }
            )

            result = await excel_service.preview_excel_file("test.xlsx")

            assert result["preview_data"][0]["物业名称"] == "资产1"
            assert result["preview_data"][1]["物业名称"] is None
            assert result["preview_data"][2]["物业地址"] is None

    @pytest.mark.asyncio
    async def test_preview_with_datetime(self, excel_service):
        """测试预览包含日期时间"""
        test_date = datetime(2024, 6, 15)
        with patch("pandas.read_excel") as mock_read:
            mock_read.return_value = pd.DataFrame(
                {
                    "物业名称": ["资产1"],
                    "创建日期": [test_date],
                }
            )

            result = await excel_service.preview_excel_file("test.xlsx")

            # datetime对象应该被转换为字符串
            assert isinstance(result["preview_data"][0]["创建日期"], str)

    @pytest.mark.asyncio
    async def test_preview_exception(self, excel_service):
        """测试预览异常"""
        with patch("pandas.read_excel", side_effect=Exception("Read error")):
            with pytest.raises(BusinessValidationError) as excinfo:
                await excel_service.preview_excel_file("error.xlsx")

            assert "预览Excel文件失败" in str(excinfo.value)


# ============================================================================
# Test Warnings Collection
# ============================================================================
class TestWarningsCollection:
    """测试警告收集"""

    @pytest.mark.asyncio
    async def test_parse_warnings_collection(self, excel_service):
        """测试解析警告收集"""
        with patch("pandas.read_excel") as mock_read:
            mock_read.return_value = pd.DataFrame(
                {
                    "物业名称": ["资产1"],
                    "物业地址": ["地址1"],
                    "土地面积(平方米)": ["invalid"],
                }
            )

            excel_service._map_excel_row_to_asset_data = MagicMock(
                return_value=(
                    {"property_name": "资产1", "address": "地址1"},
                    [
                        {
                            "field": "land_area",
                            "value": "invalid",
                            "warning": "无法解析为数值",
                        }
                    ],
                )
            )

            excel_service.validator.validate_all = MagicMock(
                return_value=(True, [], [], ["property_name"])
            )

            result = await excel_service.import_assets_from_excel(
                file_path="test.xlsx",
                should_validate_data=True,
                should_create_assets=False,
            )

            assert len(result["warnings"]) == 1
            assert result["warnings"][0]["field"] == "land_area"
            assert "无法解析为数值" in result["warnings"][0]["warning"]


# ============================================================================
# Test FIELD_MAPPING
# ============================================================================
class TestFieldMappingConstant:
    """测试字段映射常量"""

    def test_field_mapping_complete(self):
        """测试字段映射完整性"""
        assert "权属方" in FIELD_MAPPING
        assert "权属类别" in FIELD_MAPPING
        assert "项目名称" in FIELD_MAPPING
        assert "物业名称" in FIELD_MAPPING
        assert "物业地址" in FIELD_MAPPING

    def test_field_mapping_values(self):
        """测试字段映射值"""
        assert FIELD_MAPPING["权属方"] == "ownership_entity"
        assert FIELD_MAPPING["物业名称"] == "property_name"
        assert FIELD_MAPPING["物业地址"] == "address"

    def test_field_mapping_count(self):
        """测试字段映射数量"""
        assert len(FIELD_MAPPING) == 21
