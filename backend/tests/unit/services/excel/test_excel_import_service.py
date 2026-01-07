"""
测试 ExcelImportService (Excel导入服务) 错误处理
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from src.core.exception_handler import BusinessValidationError
from src.services.excel.excel_import_service import ExcelImportService


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

            # Mock _map_excel_row_to_asset_data
            excel_service._map_excel_row_to_asset_data = MagicMock(
                side_effect=[
                    {"property_name": "", "address": "地址1"},
                    {"property_name": "有效资产", "address": "地址2"},
                ]
            )

            result = await excel_service.import_assets_from_excel(
                file_path="test.xlsx",
                validate_data=True,
                create_assets=False,
                skip_errors=True,
            )

            assert result["total"] == 2
            assert result["failed"] == 1
            assert result["success"] == 1
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
                return_value={"property_name": "", "address": "地址1"}
            )

            with pytest.raises(BusinessValidationError) as excinfo:
                await excel_service.import_assets_from_excel(
                    file_path="test.xlsx",
                    validate_data=True,
                    create_assets=False,
                    skip_errors=False,
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
                return_value={"property_name": "已存在资产", "address": "地址1"}
            )

            # Mock 找到已存在的资产
            excel_service._find_existing_asset = MagicMock(
                return_value=MagicMock(id="existing_id")
            )

            result = await excel_service.import_assets_from_excel(
                file_path="test.xlsx",
                validate_data=True,
                create_assets=True,
                update_existing=False,
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
                return {
                    "property_name": f"资产{idx}",
                    "address": f"地址{idx}",
                    "ownership_entity": "测试单位",
                    "ownership_status": "自有",
                    "property_nature": "商业",
                    "usage_status": "使用中",
                }

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
                    validate_data=True,
                    create_assets=True,
                    skip_errors=True,
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
                {
                    "property_name": "资产1",
                    "address": "地址1",
                    "ownership_entity": "测试单位",
                    "ownership_status": "自有",
                    "property_nature": "商业",
                    "usage_status": "使用中",
                },
                {
                    "property_name": "资产2",
                    "address": "地址2",
                    "ownership_entity": "测试单位",
                    "ownership_status": "自有",
                    "property_nature": "商业",
                    "usage_status": "使用中",
                },
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
                        validate_data=True,
                        create_assets=True,
                        skip_errors=False,
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
                return_value={
                    "property_name": "资产1",
                    "address": "地址1",
                    "operation_agreement_start_date": None,  # 日期解析失败返回None
                }
            )

            excel_service.validator.validate_all = MagicMock(
                return_value=(True, [], [], ["property_name"])
            )

            result = await excel_service.import_assets_from_excel(
                file_path="test.xlsx",
                validate_data=True,
                create_assets=False,
            )

            # 日期解析失败不应导致整行失败
            assert result["success"] == 1
            assert result["failed"] == 0
