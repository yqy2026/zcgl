"""
Excel导出服务单元测试

测试 ExcelExportService 的资产数据导出功能
"""

import io
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.services.excel import excel_export_service as excel_export_service_module
from src.services.excel.excel_export_service import (
    EXPORT_FIELD_MAPPING,
    ExcelExportService,
)


def test_excel_export_service_module_avoids_datetime_utcnow() -> None:
    """服务模块不应直接调用 datetime.utcnow."""
    module_path = Path(excel_export_service_module.__file__)
    content = module_path.read_text(encoding="utf-8")

    assert "datetime.utcnow(" not in content

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def excel_service(mock_db):
    """Excel导出服务实例"""
    return ExcelExportService(mock_db)


@pytest.fixture
def sample_asset():
    """示例资产对象"""
    asset = Mock()
    asset.ownership_entity = "测试公司"
    asset.ownership_category = "国有"
    asset.project_name = "测试项目"
    asset.property_name = "测试物业"
    asset.address = "北京市朝阳区测试路123号"
    asset.land_area = 1000.0
    asset.actual_property_area = 2000.0
    asset.non_commercial_area = 500.0
    asset.rentable_area = 1500.0
    asset.rented_area = 800.0
    asset.ownership_status = "已确权"
    asset.property_nature = "商业"
    asset.usage_status = "在用"
    asset.business_category = "零售"
    asset.is_litigated = False
    asset.notes = "测试备注"
    asset.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    asset.updated_at = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
    return asset


# ============================================================================
# _convert_assets_to_export_format 测试
# ============================================================================
class TestConvertAssetsToExportFormat:
    """测试资产数据转换为导出格式"""

    def test_convert_single_asset_all_fields(self, excel_service, sample_asset):
        """测试转换单个资产（所有字段）"""
        assets = [sample_asset]
        result = excel_service._convert_assets_to_export_format(assets)

        assert len(result) == 1
        row = result[0]

        # 验证字段映射 - 使用映射后的中文字段名
        assert row["权属方"] == "测试公司"
        assert row["物业名称"] == "测试物业"
        assert row["物业地址"] == "北京市朝阳区测试路123号"
        assert row["土地面积(平方米)"] == 1000.0
        assert row["已出租面积(平方米)"] == 800.0
        assert row["是否涉诉"] == "否"
        assert "2024-01-01" in row["创建时间"]

    def test_convert_single_asset_specific_fields(self, excel_service, sample_asset):
        """测试转换单个资产（指定字段）"""
        assets = [sample_asset]
        fields = ["property_name", "address", "land_area"]
        result = excel_service._convert_assets_to_export_format(assets, fields=fields)

        assert len(result) == 1
        row = result[0]

        # 只包含指定字段
        assert "物业名称" in row
        assert "物业地址" in row
        assert "土地面积(平方米)" in row
        # 不包含未指定的字段
        assert "权属方" not in row

    def test_convert_asset_with_none_values(self, excel_service):
        """测试转换包含None值的资产"""
        asset = Mock()
        asset.property_name = "测试物业"
        asset.address = None
        asset.land_area = None
        asset.actual_property_area = None
        asset.non_commercial_area = None
        asset.rentable_area = None
        asset.rented_area = None
        asset.is_litigated = None
        asset.created_at = None
        asset.updated_at = None
        # 设置其他字段为None
        asset.ownership_entity = None
        asset.ownership_category = None
        asset.project_name = None
        asset.ownership_status = None
        asset.property_nature = None
        asset.usage_status = None
        asset.business_category = None
        asset.notes = None

        assets = [asset]
        result = excel_service._convert_assets_to_export_format(assets)

        assert len(result) == 1
        row = result[0]
        # None值应该转换为空字符串
        assert row["物业地址"] == ""
        assert row["土地面积(平方米)"] == ""

    def test_convert_asset_boolean_field(self, excel_service):
        """测试布尔字段转换"""
        asset = Mock()
        asset.is_litigated = True
        # 设置其他必需字段为None（避免float()错误）
        for field in EXPORT_FIELD_MAPPING.keys():
            if field != "is_litigated":
                setattr(asset, field, None)

        assets = [asset]
        result = excel_service._convert_assets_to_export_format(assets)

        assert result[0]["是否涉诉"] == "是"

    def test_convert_asset_date_format(self, excel_service, sample_asset):
        """测试日期格式化"""
        assets = [sample_asset]
        custom_format = "%Y/%m/%d"
        result = excel_service._convert_assets_to_export_format(
            assets, date_format=custom_format
        )

        assert "2024/01/01" in result[0]["创建时间"]

    def test_convert_multiple_assets(self, excel_service, sample_asset):
        """测试转换多个资产"""
        asset2 = Mock()
        for field in EXPORT_FIELD_MAPPING.keys():
            if hasattr(sample_asset, field):
                value = getattr(sample_asset, field)
            else:
                value = None
            setattr(asset2, field, value)

        asset2.property_name = "第二个物业"

        assets = [sample_asset, asset2]
        result = excel_service._convert_assets_to_export_format(assets)

        assert len(result) == 2
        assert result[0]["物业名称"] == "测试物业"
        assert result[1]["物业名称"] == "第二个物业"

    def test_convert_empty_asset_list(self, excel_service):
        """测试空资产列表"""
        result = excel_service._convert_assets_to_export_format([])
        assert result == []

    def test_convert_numeric_fields_precision(self, excel_service):
        """测试数值字段精度"""
        asset = Mock()
        asset.land_area = 1000.456
        asset.actual_property_area = 2000.789
        # 设置其他必需字段为None（避免类型错误）
        for field in EXPORT_FIELD_MAPPING.keys():
            if field not in ["land_area", "actual_property_area"]:
                setattr(asset, field, None)

        assets = [asset]
        result = excel_service._convert_assets_to_export_format(assets)

        # 数值应该转换为float（保留原始精度）
        assert isinstance(result[0]["土地面积(平方米)"], float)
        assert result[0]["土地面积(平方米)"] == 1000.456


# ============================================================================
# _get_empty_export_data 测试
# ============================================================================
class TestGetEmptyExportData:
    """测试获取空导出数据"""

    def test_empty_data_all_fields(self, excel_service):
        """测试获取所有字段的空数据"""
        result = excel_service._get_empty_export_data()

        assert len(result) == 1
        row = result[0]

        # 应该包含所有映射字段
        assert len(row) == len(EXPORT_FIELD_MAPPING)
        # 第一列应该有提示
        first_column = list(EXPORT_FIELD_MAPPING.values())[0]
        assert row[first_column] == "暂无数据"

    def test_empty_data_specific_fields(self, excel_service):
        """测试获取指定字段的空数据"""
        fields = ["property_name", "address", "land_area"]
        result = excel_service._get_empty_export_data(fields=fields)

        assert len(result) == 1
        row = result[0]

        # 应该只包含指定字段
        assert len(row) == len(fields)
        assert "物业名称" in row
        assert "物业地址" in row
        assert "土地面积(平方米)" in row

    def test_empty_data_invalid_field(self, excel_service):
        """测试无效字段被忽略"""
        fields = ["property_name", "invalid_field", "address"]
        result = excel_service._get_empty_export_data(fields=fields)

        # 无效字段应该被忽略
        assert len(result[0]) <= 2

    def test_empty_data_no_fields(self, excel_service):
        """测试空字段列表"""
        result = excel_service._get_empty_export_data(fields=[])

        assert len(result) == 1
        # 空字段列表应该返回空行
        row = result[0]
        assert (
            len(row) == 0
            or row.get(list(EXPORT_FIELD_MAPPING.values())[0]) == "暂无数据"
        )


# ============================================================================
# export_assets_to_excel 测试
# ============================================================================
class TestExportAssetsToExcel:
    """测试导出资产到Excel"""

    @patch("src.services.excel.excel_export_service.asset_crud")
    def test_export_success(self, mock_crud, excel_service, sample_asset):
        """测试成功导出"""
        mock_crud.get_multi_with_search.return_value = ([sample_asset], 1)

        buffer = excel_service.export_assets_to_excel()

        assert isinstance(buffer, io.BytesIO)
        # 验证buffer包含数据
        buffer.seek(0)
        data = buffer.read()
        assert len(data) > 0

    @patch("src.services.excel.excel_export_service.asset_crud")
    def test_export_with_filters(self, mock_crud, excel_service, sample_asset):
        """测试带筛选条件的导出"""
        mock_crud.get_multi_with_search.return_value = ([sample_asset], 1)

        filters = {"ownership_status": "已确权", "property_nature": "商业"}
        buffer = excel_service.export_assets_to_excel(filters=filters)

        assert isinstance(buffer, io.BytesIO)
        # 验证CRUD被调用时传入了筛选条件
        mock_crud.get_multi_with_search.assert_called_once()
        call_args = mock_crud.get_multi_with_search.call_args
        assert call_args.kwargs["filters"] == filters

    @patch("src.services.excel.excel_export_service.asset_crud")
    def test_export_with_search(self, mock_crud, excel_service, sample_asset):
        """测试带搜索关键词的导出"""
        mock_crud.get_multi_with_search.return_value = ([sample_asset], 1)

        buffer = excel_service.export_assets_to_excel(search="测试")

        assert isinstance(buffer, io.BytesIO)
        # 验证搜索关键词被传入
        mock_crud.get_multi_with_search.assert_called_once()
        call_args = mock_crud.get_multi_with_search.call_args
        assert call_args.kwargs["search"] == "测试"

    @patch("src.services.excel.excel_export_service.asset_crud")
    def test_export_with_asset_ids(self, mock_crud, excel_service, sample_asset):
        """测试指定资产ID的导出"""
        mock_crud.get_multi_with_search.return_value = ([sample_asset], 1)

        asset_ids = ["asset-1", "asset-2"]
        buffer = excel_service.export_assets_to_excel(asset_ids=asset_ids)

        assert isinstance(buffer, io.BytesIO)
        # 验证asset_ids被添加到筛选条件
        mock_crud.get_multi_with_search.assert_called_once()
        call_args = mock_crud.get_multi_with_search.call_args
        assert call_args.kwargs["filters"]["ids"] == asset_ids

    @patch("src.services.excel.excel_export_service.asset_crud")
    def test_export_with_fields(self, mock_crud, excel_service, sample_asset):
        """测试指定字段的导出"""
        mock_crud.get_multi_with_search.return_value = ([sample_asset], 1)

        fields = ["property_name", "address"]
        buffer = excel_service.export_assets_to_excel(fields=fields)

        assert isinstance(buffer, io.BytesIO)

    @patch("src.services.excel.excel_export_service.asset_crud")
    def test_export_with_custom_sheet_name(
        self, mock_crud, excel_service, sample_asset
    ):
        """测试自定义工作表名称"""
        mock_crud.get_multi_with_search.return_value = ([sample_asset], 1)

        buffer = excel_service.export_assets_to_excel(sheet_name="CustomSheet")

        assert isinstance(buffer, io.BytesIO)

    @patch("src.services.excel.excel_export_service.asset_crud")
    def test_export_with_limit(self, mock_crud, excel_service, sample_asset):
        """测试限制导出数量"""
        mock_crud.get_multi_with_search.return_value = ([sample_asset], 1)

        buffer = excel_service.export_assets_to_excel(limit=100)

        assert isinstance(buffer, io.BytesIO)
        # 验证limit被传入
        mock_crud.get_multi_with_search.assert_called_once()
        call_args = mock_crud.get_multi_with_search.call_args
        assert call_args.kwargs["limit"] == 100

    @patch("src.services.excel.excel_export_service.asset_crud")
    def test_export_empty_data(self, mock_crud, excel_service):
        """测试导出空数据"""
        mock_crud.get_multi_with_search.return_value = ([], 0)

        buffer = excel_service.export_assets_to_excel()

        assert isinstance(buffer, io.BytesIO)
        # 空数据也应该生成有效的Excel文件
        buffer.seek(0)
        data = buffer.read()
        assert len(data) > 0

    @patch("src.services.excel.excel_export_service.asset_crud")
    def test_export_handles_exception(self, mock_crud, excel_service):
        """测试导出异常处理"""
        mock_crud.get_multi_with_search.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            excel_service.export_assets_to_excel()


# ============================================================================
# export_assets_to_file 测试
# ============================================================================
class TestExportAssetsToFile:
    """测试导出资产到文件"""

    @patch("src.services.excel.excel_export_service.os.path.getsize")
    def test_export_to_file_success(self, mock_getsize, excel_service):
        """测试成功导出到文件"""
        mock_getsize.return_value = 1024

        # 创建真实的BytesIO缓冲区
        buffer = io.BytesIO(b"fake excel data")

        # Mock export_assets_to_excel 返回真实buffer
        with patch.object(excel_service, "export_assets_to_excel", return_value=buffer):
            # Mock文件写入
            with patch("builtins.open", create=True) as mock_open:
                mock_file = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file

                result = excel_service.export_assets_to_file("/tmp/test.xlsx")

                assert result["file_path"] == "/tmp/test.xlsx"
                assert result["file_name"] == "test.xlsx"
                assert result["file_size"] == 1024
                assert "export_time" in result
                # 验证write被调用
                mock_file.write.assert_called_once()

    @patch("src.services.excel.excel_export_service.asset_crud")
    @patch("builtins.open", new_callable=MagicMock)
    def test_export_to_file_handles_exception(
        self, mock_open, mock_crud, excel_service
    ):
        """测试导出文件异常处理"""
        mock_crud.get_multi_with_search.side_effect = Exception("Export failed")

        with pytest.raises(Exception, match="Export failed"):
            excel_service.export_assets_to_file("/tmp/test.xlsx")


# ============================================================================
# get_export_preview 测试
# ============================================================================
class TestGetExportPreview:
    """测试获取导出预览"""

    @patch("src.services.excel.excel_export_service.asset_crud")
    def test_get_preview_with_data(self, mock_crud, excel_service, sample_asset):
        """测试获取有数据的预览"""
        mock_crud.get_multi_with_search.return_value = ([sample_asset], 100)

        preview = excel_service.get_export_preview()

        assert preview["total_count"] == 100
        assert "sample_columns" in preview
        assert "sample_data" in preview
        assert len(preview["sample_columns"]) > 0
        assert preview["sample_data"] is not None

    @patch("src.services.excel.excel_export_service.asset_crud")
    def test_get_preview_no_data(self, mock_crud, excel_service):
        """测试获取无数据的预览"""
        mock_crud.get_multi_with_search.return_value = ([], 0)

        preview = excel_service.get_export_preview()

        assert preview["total_count"] == 0
        assert len(preview["sample_columns"]) > 0
        assert preview["sample_data"] is None

    @patch("src.services.excel.excel_export_service.asset_crud")
    def test_get_preview_with_filters(self, mock_crud, excel_service, sample_asset):
        """测试带筛选条件的预览"""
        mock_crud.get_multi_with_search.return_value = ([sample_asset], 10)

        filters = {"ownership_status": "已确权"}
        preview = excel_service.get_export_preview(filters=filters)

        assert preview["total_count"] == 10
        # 验证筛选条件被传入
        mock_crud.get_multi_with_search.assert_called_once()
        call_args = mock_crud.get_multi_with_search.call_args
        assert call_args.kwargs["filters"] == filters

    @patch("src.services.excel.excel_export_service.asset_crud")
    def test_get_preview_with_search(self, mock_crud, excel_service, sample_asset):
        """测试带搜索的预览"""
        mock_crud.get_multi_with_search.return_value = ([sample_asset], 5)

        preview = excel_service.get_export_preview(search="测试")

        assert preview["total_count"] == 5

    @patch("src.services.excel.excel_export_service.asset_crud")
    def test_get_preview_with_asset_ids(self, mock_crud, excel_service, sample_asset):
        """测试指定资产ID的预览"""
        mock_crud.get_multi_with_search.return_value = ([sample_asset], 2)

        asset_ids = ["asset-1", "asset-2"]
        preview = excel_service.get_export_preview(asset_ids=asset_ids)

        assert preview["total_count"] == 2
        # 验证asset_ids被添加到筛选条件
        mock_crud.get_multi_with_search.assert_called_once()
        call_args = mock_crud.get_multi_with_search.call_args
        assert call_args.kwargs["filters"]["ids"] == asset_ids

    @patch("src.services.excel.excel_export_service.asset_crud")
    def test_get_preview_exception_handling(self, mock_crud, excel_service):
        """测试预览异常处理"""
        mock_crud.get_multi_with_search.side_effect = Exception("Query failed")

        with pytest.raises(Exception, match="Query failed"):
            excel_service.get_export_preview()


# ============================================================================
# _set_column_widths 测试
# ============================================================================
class TestSetColumnWidths:
    """测试设置列宽"""

    def test_set_column_widths(self, excel_service):
        """测试设置Excel列宽"""
        mock_worksheet = Mock()
        mock_worksheet.column_dimensions = {"A": Mock(), "B": Mock(), "C": Mock()}

        excel_service._set_column_widths(mock_worksheet)

        # 验证A列宽度被设置
        assert mock_worksheet.column_dimensions["A"].width == 20
        # 验证B列宽度被设置
        assert mock_worksheet.column_dimensions["B"].width == 15

    def test_set_column_widths_partial_columns(self, excel_service):
        """测试只设置部分列宽"""
        mock_worksheet = Mock()
        # 只模拟A列存在
        mock_worksheet.column_dimensions = {"A": Mock()}

        excel_service._set_column_widths(mock_worksheet)

        # 只设置存在的列
        assert mock_worksheet.column_dimensions["A"].width == 20
