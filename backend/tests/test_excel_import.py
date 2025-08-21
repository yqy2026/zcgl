"""
Excel导入功能测试
"""

import pytest
import tempfile
import os
from pathlib import Path
import polars as pl
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.services.excel_import import ExcelImportService, AssetDataProcessor, ExcelImportError
from src.schemas.asset import AssetCreate
from src.database import get_db
# from tests.conftest import override_get_db

client = TestClient(app)


class TestAssetDataProcessor:
    """测试资产数据处理器"""
    
    def test_column_mapping(self):
        """测试列名映射"""
        processor = AssetDataProcessor()
        
        # 测试基本映射
        assert "ownership_entity" in processor.COLUMN_MAPPING.values()
        assert "property_name" in processor.COLUMN_MAPPING.values()
        assert "actual_property_area" in processor.COLUMN_MAPPING.values()
        
        # 测试特殊字符处理
        assert processor.COLUMN_MAPPING["权属方"] == "ownership_entity"
        assert processor.COLUMN_MAPPING["土地面积\n(平方米)"] == "land_area"
    
    def test_read_excel_file_success(self):
        """测试成功读取Excel文件"""
        # 创建测试Excel文件
        test_data = {
            "权属方": ["国资集团", "市政府"],
            "物业名称": ["测试物业1", "测试物业2"],
            "所在地址": ["测试地址1", "测试地址2"],
            "实际房产面积\n(平方米)": [100.0, 200.0],
            "经营性物业可出租面积\n(平方米)": [80.0, 150.0],
            "经营性物业已出租面积\n(平方米)": [60.0, 100.0],
            "经营性物业未出租面积\n(平方米)": [20.0, 50.0],
            "非经营物业面积\n(平方米)": [20.0, 50.0],
            "是否确权\n（已确权、未确权、部分确权）": ["已确权", "未确权"],
            "实际用途\n（商业、住宅、办公、厂房、车位..）": ["商业", "办公"],
            "物业使用状态\n（出租、闲置、自用、公房、其他）": ["出租", "闲置"],
            "是否涉诉": ["否", "否"],
            "物业性质（经营类、非经营类）": ["经营类", "经营类"],
            "出租率": ["75%", "67%"]
        }
        
        df = pl.DataFrame(test_data)
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            df.write_excel(temp_file.name, worksheet="物业总表")
            temp_file_path = temp_file.name
        
        try:
            processor = AssetDataProcessor()
            result_df = processor.read_excel_file(temp_file_path, "物业总表")
            
            assert len(result_df) == 2
            assert "权属方" in result_df.columns
            assert "物业名称" in result_df.columns
            
        finally:
            os.unlink(temp_file_path)
    
    def test_read_excel_file_not_found(self):
        """测试读取不存在的Excel文件"""
        processor = AssetDataProcessor()
        
        with pytest.raises(ExcelImportError) as exc_info:
            processor.read_excel_file("nonexistent.xlsx")
        
        assert "读取Excel文件失败" in str(exc_info.value)
    
    def test_clean_and_transform_data(self):
        """测试数据清洗和转换"""
        # 创建测试数据
        test_data = {
            "权属方": ["国资集团", "  市政府  ", ""],
            "物业名称": ["测试物业1", "测试物业2", "测试物业3"],
            "所在地址": ["测试地址1", "测试地址2", "测试地址3"],
            "实际房产面积\n(平方米)": ["100.0", "200.5", ""],
            "经营性物业可出租面积\n(平方米)": ["80.0", "150.0", "0"],
            "经营性物业已出租面积\n(平方米)": ["60.0", "100.0", "0"],
            "经营性物业未出租面积\n(平方米)": ["20.0", "50.0", "0"],
            "非经营物业面积\n(平方米)": ["20.0", "50.0", "0"],
            "是否确权\n（已确权、未确权、部分确权）": ["已确权", "未确权", ""],
            "实际用途\n（商业、住宅、办公、厂房、车位..）": ["商业", "办公", "住宅"],
            "物业使用状态\n（出租、闲置、自用、公房、其他）": ["出租", "闲置", ""],
            "是否涉诉": ["否", "否", ""],
            "物业性质（经营类、非经营类）": ["经营类", "经营类", ""],
            "出租率": ["75%", "67%", "0%"],
            "现合同开始日期": ["2024年1月1日", "2023年6月15日", ""],
            "现合同结束日期": ["2026年12月31日", "2025年6月14日", ""]
        }
        
        df = pl.DataFrame(test_data)
        processor = AssetDataProcessor()
        
        result_df = processor.clean_and_transform_data(df)
        
        # 验证列名重命名
        assert "ownership_entity" in result_df.columns
        assert "property_name" in result_df.columns
        assert "actual_property_area" in result_df.columns
        
        # 验证数据清洗
        ownership_entities = result_df["ownership_entity"].to_list()
        assert ownership_entities[0] == "国资集团"
        assert ownership_entities[1] == "市政府"  # 空白字符被清理
        assert ownership_entities[2] == ""  # None被转换为空字符串
        
        # 验证数值转换
        areas = result_df["actual_property_area"].to_list()
        assert areas[0] == 100.0
        assert areas[1] == 200.5
        assert areas[2] == 0.0  # None被转换为0.0
    
    def test_validate_data_success(self):
        """测试数据验证成功"""
        test_data = {
            "ownership_entity": ["国资集团", "市政府"],
            "property_name": ["测试物业1", "测试物业2"],
            "address": ["测试地址1", "测试地址2"],
            "actual_property_area": [100.0, 200.0],
            "rentable_area": [80.0, 150.0],
            "rented_area": [60.0, 100.0],
            "unrented_area": [20.0, 50.0],
            "non_commercial_area": [20.0, 50.0],
            "ownership_status": ["已确权", "未确权"],
            "actual_usage": ["商业", "办公"],
            "usage_status": ["出租", "闲置"],
            "property_nature": ["经营类", "经营类"]
        }
        
        df = pl.DataFrame(test_data)
        processor = AssetDataProcessor()
        
        errors = processor.validate_data(df)
        assert len(errors) == 0
    
    def test_validate_data_with_errors(self):
        """测试数据验证失败"""
        test_data = {
            "ownership_entity": ["", "市政府"],  # 第一行为空
            "property_name": ["测试物业1", ""],  # 第二行为空
            "address": ["测试地址1", "测试地址2"],
            "actual_property_area": [-100.0, 200.0],  # 第一行为负数
            "rentable_area": [80.0, 150.0],
            "rented_area": [60.0, 100.0],
            "unrented_area": [20.0, 50.0],
            "non_commercial_area": [20.0, 50.0],
            "ownership_status": ["无效状态", "未确权"],  # 第一行无效
            "actual_usage": ["商业", "办公"],
            "usage_status": ["出租", "闲置"],
            "property_nature": ["经营类", "经营类"]
        }
        
        df = pl.DataFrame(test_data)
        processor = AssetDataProcessor()
        
        errors = processor.validate_data(df)
        assert len(errors) > 0
        
        # 检查具体错误
        error_text = " ".join(errors)
        assert "ownership_entity" in error_text
        assert "property_name" in error_text
        assert "actual_property_area" in error_text
        assert "确权状态字段" in error_text
    
    def test_convert_to_asset_models(self):
        """测试转换为资产模型"""
        test_data = {
            "ownership_entity": ["国资集团"],
            "property_name": ["测试物业"],
            "address": ["测试地址"],
            "actual_property_area": [100.0],
            "rentable_area": [80.0],
            "rented_area": [60.0],
            "unrented_area": [20.0],
            "non_commercial_area": [20.0],
            "ownership_status": ["已确权"],
            "actual_usage": ["商业"],
            "usage_status": ["出租"],
            "is_litigated": ["否"],
            "property_nature": ["经营类"],
            "occupancy_rate": ["75%"]
        }
        
        df = pl.DataFrame(test_data)
        processor = AssetDataProcessor()
        
        assets = processor.convert_to_asset_models(df)
        
        assert len(assets) == 1
        assert isinstance(assets[0], AssetCreate)
        assert assets[0].ownership_entity == "国资集团"
        assert assets[0].property_name == "测试物业"
        assert assets[0].actual_property_area == 100.0


class TestExcelImportService:
    """测试Excel导入服务"""
    
    @pytest.fixture
    def import_service(self):
        """创建导入服务实例"""
        return ExcelImportService()
    
    @pytest.fixture
    def sample_excel_file(self):
        """创建示例Excel文件"""
        test_data = {
            "权属方": ["国资集团", "市政府"],
            "物业名称": ["测试物业1", "测试物业2"],
            "所在地址": ["测试地址1", "测试地址2"],
            "实际房产面积\n(平方米)": [100.0, 200.0],
            "经营性物业可出租面积\n(平方米)": [80.0, 150.0],
            "经营性物业已出租面积\n(平方米)": [60.0, 100.0],
            "经营性物业未出租面积\n(平方米)": [20.0, 50.0],
            "非经营物业面积\n(平方米)": [20.0, 50.0],
            "是否确权\n（已确权、未确权、部分确权）": ["已确权", "未确权"],
            "实际用途\n（商业、住宅、办公、厂房、车位..）": ["商业", "办公"],
            "物业使用状态\n（出租、闲置、自用、公房、其他）": ["出租", "闲置"],
            "是否涉诉": ["否", "否"],
            "物业性质（经营类、非经营类）": ["经营类", "经营类"],
            "出租率": ["75%", "67%"]
        }
        
        df = pl.DataFrame(test_data)
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            df.write_excel(temp_file.name, worksheet="物业总表")
            yield temp_file.name
        
        # 清理临时文件
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
    
    @pytest.mark.asyncio
    async def test_import_assets_success(self, import_service, sample_excel_file):
        """测试成功导入资产"""
        # 使用默认数据库连接进行测试
        result = await import_service.import_assets_from_excel(
            file_path=sample_excel_file
        )
        
        # 验证结果结构（不验证具体数值，因为可能有重复数据）
        assert "success" in result
        assert "failed" in result
        assert "total" in result
        assert "errors" in result
        assert result["total"] == 2
    
    @pytest.mark.asyncio
    async def test_import_assets_with_invalid_file(self, import_service):
        """测试导入无效文件"""
        result = await import_service.import_assets_from_excel(
            file_path="nonexistent.xlsx"
        )
        
        assert result["success"] == 0
        assert result["failed"] == 0
        assert result["total"] == 0
        assert len(result["errors"]) > 0
        assert "导入失败" in result["errors"][0]


class TestExcelImportAPI:
    """测试Excel导入API"""
    
    @pytest.fixture
    def sample_excel_content(self):
        """创建示例Excel文件内容"""
        test_data = {
            "权属方": ["国资集团"],
            "物业名称": ["API测试物业"],
            "所在地址": ["API测试地址"],
            "实际房产面积\n(平方米)": [100.0],
            "经营性物业可出租面积\n(平方米)": [80.0],
            "经营性物业已出租面积\n(平方米)": [60.0],
            "经营性物业未出租面积\n(平方米)": [20.0],
            "非经营物业面积\n(平方米)": [20.0],
            "是否确权\n（已确权、未确权、部分确权）": ["已确权"],
            "实际用途\n（商业、住宅、办公、厂房、车位..）": ["商业"],
            "物业使用状态\n（出租、闲置、自用、公房、其他）": ["出租"],
            "是否涉诉": ["否"],
            "物业性质（经营类、非经营类）": ["经营类"],
            "出租率": ["75%"]
        }
        
        df = pl.DataFrame(test_data)
        
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_file_path = temp_file.name
        
        try:
            df.write_excel(temp_file_path, worksheet="物业总表")
            
            with open(temp_file_path, 'rb') as f:
                content = f.read()
            
            return content
        finally:
            # 确保文件被删除
            try:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
            except PermissionError:
                # 在Windows上可能会有权限问题，稍后再试
                import time
                time.sleep(0.1)
                try:
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                except:
                    pass  # 忽略清理失败
    
    def test_import_excel_success(self, sample_excel_content):
        """测试成功导入Excel文件"""
        response = client.post(
            "/api/v1/excel/import",
            files={"file": ("test.xlsx", sample_excel_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data
        assert "failed" in data
        assert "total" in data
        assert "message" in data
    
    def test_import_excel_invalid_file_type(self):
        """测试导入无效文件类型"""
        response = client.post(
            "/api/v1/excel/import",
            files={"file": ("test.txt", b"invalid content", "text/plain")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "文件格式不支持" in data["message"]
    
    def test_validate_excel_success(self, sample_excel_content):
        """测试Excel文件验证成功"""
        response = client.post(
            "/api/v1/excel/validate",
            files={"file": ("test.xlsx", sample_excel_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "valid" in data
        assert "total_rows" in data
        assert "total_columns" in data
        assert "errors" in data
        assert "columns" in data
        assert "message" in data
    
    def test_validate_excel_invalid_file_type(self):
        """测试验证无效文件类型"""
        response = client.post(
            "/api/v1/excel/validate",
            files={"file": ("test.txt", b"invalid content", "text/plain")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "文件格式不支持" in data["message"]
    
    def test_download_template_success(self):
        """测试下载模板成功"""
        response = client.get("/api/v1/excel/import/template")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert "attachment" in response.headers["content-disposition"]
        assert "filename*=UTF-8''" in response.headers["content-disposition"]
    
    def test_get_import_status_success(self):
        """测试获取导入状态成功"""
        response = client.get("/api/v1/excel/import/status/test-task-id")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "task_id" in data
        assert "status" in data
        assert "progress" in data
        assert "message" in data
        assert data["task_id"] == "test-task-id"


class TestDataProcessingEdgeCases:
    """测试数据处理边界情况"""
    
    def test_empty_dataframe(self):
        """测试空数据框"""
        df = pl.DataFrame()
        processor = AssetDataProcessor()
        
        # 清洗空数据框不应该报错
        result_df = processor.clean_and_transform_data(df)
        assert len(result_df) == 0
        
        # 验证空数据框
        errors = processor.validate_data(df)
        assert len(errors) > 0  # 应该有缺少必填字段的错误
        
        # 转换空数据框
        assets = processor.convert_to_asset_models(df)
        assert len(assets) == 0
    
    def test_large_dataset_performance(self):
        """测试大数据集性能"""
        # 创建较大的测试数据集（1000行）
        size = 1000
        test_data = {
            "权属方": ["国资集团"] * size,
            "物业名称": [f"测试物业{i}" for i in range(size)],
            "所在地址": [f"测试地址{i}" for i in range(size)],
            "实际房产面积\n(平方米)": [100.0 + i for i in range(size)],
            "经营性物业可出租面积\n(平方米)": [80.0 + i for i in range(size)],
            "经营性物业已出租面积\n(平方米)": [60.0 + i for i in range(size)],
            "经营性物业未出租面积\n(平方米)": [20.0] * size,
            "非经营物业面积\n(平方米)": [20.0] * size,
            "是否确权\n（已确权、未确权、部分确权）": ["已确权"] * size,
            "实际用途\n（商业、住宅、办公、厂房、车位..）": ["商业"] * size,
            "物业使用状态\n（出租、闲置、自用、公房、其他）": ["出租"] * size,
            "是否涉诉": ["否"] * size,
            "物业性质（经营类、非经营类）": ["经营类"] * size,
            "出租率": ["75%"] * size
        }
        
        df = pl.DataFrame(test_data)
        processor = AssetDataProcessor()
        
        # 测试处理时间（应该很快）
        import time
        start_time = time.time()
        
        result_df = processor.clean_and_transform_data(df)
        errors = processor.validate_data(result_df)
        assets = processor.convert_to_asset_models(result_df)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 验证结果
        assert len(result_df) == size
        assert len(errors) == 0  # 数据应该是有效的
        assert len(assets) == size
        
        # 性能要求：处理1000行数据应该在5秒内完成
        assert processing_time < 5.0, f"处理时间过长: {processing_time}秒"
    
    def test_special_characters_handling(self):
        """测试特殊字符处理"""
        test_data = {
            "权属方": ["国资集团", "市政府\n换行", "特殊字符@#$%"],
            "物业名称": ["正常物业", "包含\t制表符", "包含\"引号\""],
            "所在地址": ["正常地址", "地址,包含逗号", "地址;包含分号"],
            "实际房产面积\n(平方米)": [100.0, 200.0, 300.0],
            "经营性物业可出租面积\n(平方米)": [80.0, 150.0, 250.0],
            "经营性物业已出租面积\n(平方米)": [60.0, 100.0, 200.0],
            "经营性物业未出租面积\n(平方米)": [20.0, 50.0, 50.0],
            "非经营物业面积\n(平方米)": [20.0, 50.0, 50.0],
            "是否确权\n（已确权、未确权、部分确权）": ["已确权", "未确权", "部分确权"],
            "实际用途\n（商业、住宅、办公、厂房、车位..）": ["商业", "办公", "住宅"],
            "物业使用状态\n（出租、闲置、自用、公房、其他）": ["出租", "闲置", "自用"],
            "是否涉诉": ["否", "否", "是"],
            "物业性质（经营类、非经营类）": ["经营类", "经营类", "非经营类"],
            "出租率": ["75%", "67%", "80%"]
        }
        
        df = pl.DataFrame(test_data)
        processor = AssetDataProcessor()
        
        # 处理特殊字符
        result_df = processor.clean_and_transform_data(df)
        errors = processor.validate_data(result_df)
        assets = processor.convert_to_asset_models(result_df)
        
        # 验证特殊字符被正确处理
        assert len(errors) == 0
        assert len(assets) == 3
        
        # 检查特殊字符是否被保留（但清理了多余空白）
        ownership_entities = result_df["ownership_entity"].to_list()
        assert "国资集团" in ownership_entities
        assert "特殊字符@#$%" in ownership_entities