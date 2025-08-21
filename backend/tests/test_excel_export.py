"""
Excel导出功能测试
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
from src.services.excel_export import ExcelExportService, AssetDataExporter, ExcelExportError
from src.models.asset import Asset
from src.database import get_db

client = TestClient(app)


class TestAssetDataExporter:
    """测试资产数据导出器"""
    
    def test_field_to_column_mapping(self):
        """测试字段到列名的映射"""
        exporter = AssetDataExporter()
        
        # 测试基本映射
        assert "权属方" in exporter.FIELD_TO_COLUMN_MAPPING.values()
        assert "物业名称" in exporter.FIELD_TO_COLUMN_MAPPING.values()
        assert "实际房产面积\n(平方米)" in exporter.FIELD_TO_COLUMN_MAPPING.values()
        
        # 测试映射关系
        assert exporter.FIELD_TO_COLUMN_MAPPING["ownership_entity"] == "权属方"
        assert exporter.FIELD_TO_COLUMN_MAPPING["property_name"] == "物业名称"
        assert exporter.FIELD_TO_COLUMN_MAPPING["actual_property_area"] == "实际房产面积\n(平方米)"
    
    def test_convert_empty_assets_to_dataframe(self):
        """测试转换空资产列表"""
        exporter = AssetDataExporter()
        
        # 测试空列表
        df = exporter.convert_assets_to_dataframe([])
        
        assert len(df) == 0
        assert len(df.columns) > 0  # 应该有列结构
        assert "ownership_entity" in df.columns
        assert "property_name" in df.columns
    
    def test_convert_assets_to_dataframe(self):
        """测试转换资产列表为DataFrame"""
        # 创建模拟资产对象
        class MockAsset:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        assets = [
            MockAsset(
                ownership_entity="国资集团",
                property_name="测试物业1",
                address="测试地址1",
                actual_property_area=1000.0,
                rentable_area=800.0,
                rented_area=600.0,
                unrented_area=200.0,
                non_commercial_area=200.0,
                ownership_status="已确权",
                actual_usage="商业",
                usage_status="出租",
                is_litigated="否",
                property_nature="经营类",
                occupancy_rate="75%",
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            MockAsset(
                ownership_entity="市政府",
                property_name="测试物业2",
                address="测试地址2",
                actual_property_area=2000.0,
                rentable_area=1500.0,
                rented_area=1000.0,
                unrented_area=500.0,
                non_commercial_area=500.0,
                ownership_status="未确权",
                actual_usage="办公",
                usage_status="闲置",
                is_litigated="否",
                property_nature="经营类",
                occupancy_rate="67%",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
        
        exporter = AssetDataExporter()
        df = exporter.convert_assets_to_dataframe(assets)
        
        assert len(df) == 2
        assert "ownership_entity" in df.columns
        assert "property_name" in df.columns
        
        # 验证数据内容
        ownership_entities = df["ownership_entity"].to_list()
        assert "国资集团" in ownership_entities
        assert "市政府" in ownership_entities
        
        property_names = df["property_name"].to_list()
        assert "测试物业1" in property_names
        assert "测试物业2" in property_names
    
    def test_convert_assets_with_custom_columns(self):
        """测试使用自定义列转换资产"""
        class MockAsset:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        assets = [
            MockAsset(
                ownership_entity="国资集团",
                property_name="测试物业",
                address="测试地址",
                actual_property_area=1000.0
            )
        ]
        
        # 只导出指定列
        custom_columns = ["ownership_entity", "property_name", "actual_property_area"]
        
        exporter = AssetDataExporter()
        df = exporter.convert_assets_to_dataframe(assets, custom_columns)
        
        assert len(df) == 1
        assert len(df.columns) == 3
        assert "ownership_entity" in df.columns
        assert "property_name" in df.columns
        assert "actual_property_area" in df.columns
        assert "address" not in df.columns  # 不在自定义列中
    
    def test_rename_columns_for_export(self):
        """测试重命名列为导出格式"""
        # 创建测试DataFrame
        test_data = {
            "ownership_entity": ["国资集团"],
            "property_name": ["测试物业"],
            "actual_property_area": [1000.0]
        }
        
        df = pl.DataFrame(test_data)
        exporter = AssetDataExporter()
        
        # 测试包含表头
        df_with_headers = exporter.rename_columns_for_export(df, include_headers=True)
        
        assert "权属方" in df_with_headers.columns
        assert "物业名称" in df_with_headers.columns
        assert "实际房产面积\n(平方米)" in df_with_headers.columns
        
        # 测试不包含表头
        df_without_headers = exporter.rename_columns_for_export(df, include_headers=False)
        
        assert "ownership_entity" in df_without_headers.columns
        assert "property_name" in df_without_headers.columns
        assert "actual_property_area" in df_without_headers.columns
    
    def test_export_to_excel(self):
        """测试导出到Excel文件"""
        # 创建测试DataFrame
        test_data = {
            "权属方": ["国资集团", "市政府"],
            "物业名称": ["测试物业1", "测试物业2"],
            "实际房产面积\n(平方米)": [1000.0, 2000.0]
        }
        
        df = pl.DataFrame(test_data)
        exporter = AssetDataExporter()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_file_path = temp_file.name
        
        try:
            # 导出到Excel
            exporter.export_to_excel(df, temp_file_path, "测试工作表")
            
            # 验证文件存在
            assert os.path.exists(temp_file_path)
            assert os.path.getsize(temp_file_path) > 0
            
            # 验证可以读取
            df_read = pl.read_excel(temp_file_path, sheet_name="测试工作表")
            assert len(df_read) == 2
            assert "权属方" in df_read.columns
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def test_calculate_export_stats(self):
        """测试计算导出统计信息"""
        # 创建测试DataFrame
        test_data = {
            "ownership_entity": ["国资集团", "市政府", "国资集团"],
            "property_name": ["物业1", "物业2", "物业3"],
            "actual_property_area": [1000.0, 2000.0, 1500.0],
            "ownership_status": ["已确权", "未确权", "已确权"],
            "property_nature": ["经营类", "经营类", "非经营类"]
        }
        
        df = pl.DataFrame(test_data)
        exporter = AssetDataExporter()
        
        stats = exporter.calculate_export_stats(df)
        
        # 验证基本统计
        assert stats["total_records"] == 3
        assert stats["total_columns"] == 5
        assert "export_time" in stats
        
        # 验证面积统计
        assert stats["total_area"] == 4500.0
        assert stats["avg_area"] == 1500.0
        assert stats["max_area"] == 2000.0
        assert stats["min_area"] == 1000.0
        
        # 验证分布统计
        assert "ownership_distribution" in stats
        assert stats["ownership_distribution"]["已确权"] == 2
        assert stats["ownership_distribution"]["未确权"] == 1
        
        assert "nature_distribution" in stats
        assert stats["nature_distribution"]["经营类"] == 2
        assert stats["nature_distribution"]["非经营类"] == 1


class TestExcelExportService:
    """测试Excel导出服务"""
    
    @pytest.fixture
    def export_service(self):
        """创建导出服务实例"""
        return ExcelExportService()
    
    @pytest.mark.asyncio
    async def test_get_export_template_info(self, export_service):
        """测试获取导出模板信息"""
        info = await export_service.get_export_template_info()
        
        assert "available_columns" in info
        assert "column_descriptions" in info
        assert "default_columns" in info
        assert "supported_formats" in info
        assert "max_export_records" in info
        assert "export_options" in info
        
        # 验证支持的格式
        assert "xlsx" in info["supported_formats"]
        assert "xls" in info["supported_formats"]
        assert "csv" in info["supported_formats"]
        
        # 验证最大导出记录数
        assert info["max_export_records"] == 10000
        
        # 验证可用列
        assert "ownership_entity" in info["available_columns"]
        assert "property_name" in info["available_columns"]
    
    @pytest.mark.asyncio
    async def test_export_assets_no_data(self, export_service):
        """测试导出空数据"""
        # 使用不存在的筛选条件
        filters = {"ownership_entity": "不存在的权属方"}
        
        result = await export_service.export_assets_to_excel(filters=filters)
        
        assert result["success"] is False
        assert "没有找到符合条件的资产数据" in result["message"]
        assert result["file_path"] is None
        assert result["stats"]["total_records"] == 0
    
    def test_cleanup_export_file(self, export_service):
        """测试清理导出文件"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_file_path = temp_file.name
        
        # 验证文件存在
        assert os.path.exists(temp_file_path)
        
        # 清理文件
        success = export_service.cleanup_export_file(temp_file_path)
        
        assert success is True
        assert not os.path.exists(temp_file_path)
        
        # 测试清理不存在的文件
        success = export_service.cleanup_export_file(temp_file_path)
        assert success is False


class TestExcelExportAPI:
    """测试Excel导出API"""
    
    def test_get_export_info(self):
        """测试获取导出信息API"""
        response = client.get("/api/v1/excel/export/info")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "data" in data
        assert "available_columns" in data["data"]
        assert "supported_formats" in data["data"]
    
    def test_export_excel_empty_request(self):
        """测试导出Excel（空请求）"""
        export_request = {
            "filters": None,
            "columns": None,
            "format": "xlsx",
            "include_headers": True
        }
        
        response = client.post("/api/v1/excel/export", json=export_request)
        
        # 可能返回400（没有数据）或200（有数据）
        assert response.status_code in [200, 400]
        
        if response.status_code == 200:
            data = response.json()
            assert "file_url" in data
            assert "file_name" in data
            assert "file_size" in data
            assert "total_records" in data
    
    def test_export_excel_with_filters(self):
        """测试带筛选条件的导出"""
        export_request = {
            "filters": {
                "ownership_status": "已确权",
                "property_nature": "经营类"
            },
            "columns": ["ownership_entity", "property_name", "address"],
            "format": "xlsx",
            "include_headers": True
        }
        
        response = client.post("/api/v1/excel/export", json=export_request)
        
        # 可能返回400（没有数据）或200（有数据）
        assert response.status_code in [200, 400]
    
    def test_export_excel_invalid_format(self):
        """测试无效格式的导出请求"""
        export_request = {
            "filters": None,
            "columns": None,
            "format": "invalid_format",  # 无效格式
            "include_headers": True
        }
        
        response = client.post("/api/v1/excel/export", json=export_request)
        
        assert response.status_code == 422  # 验证错误
    
    def test_download_nonexistent_file(self):
        """测试下载不存在的文件"""
        response = client.get("/api/v1/excel/download/nonexistent_file.xlsx")
        
        assert response.status_code == 404
        data = response.json()
        assert "文件不存在或已过期" in data.get("detail", data.get("message", ""))
    
    def test_download_invalid_filename(self):
        """测试下载无效文件名"""
        response = client.get("/api/v1/excel/download/invalid_file.txt")
        
        # 可能返回400（无效文件名）或404（文件不存在）
        assert response.status_code in [400, 404]
        data = response.json()
        error_message = data.get("detail", data.get("message", ""))
        assert "无效的文件名" in error_message or "文件不存在" in error_message
    
    def test_cleanup_invalid_filename(self):
        """测试清理无效文件名"""
        response = client.delete("/api/v1/excel/cleanup/invalid_file.txt")
        
        assert response.status_code == 400
        data = response.json()
        error_message = data.get("detail", data.get("message", ""))
        assert "无效的文件名" in error_message
    
    def test_cleanup_nonexistent_file(self):
        """测试清理不存在的文件"""
        response = client.delete("/api/v1/excel/cleanup/资产导出_20240101_120000.xlsx")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "文件不存在或清理失败" in data["message"]


class TestExportDataProcessing:
    """测试导出数据处理"""
    
    def test_date_formatting(self):
        """测试日期格式化"""
        class MockAsset:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        test_date = datetime(2024, 1, 15, 10, 30, 0)
        assets = [
            MockAsset(
                ownership_entity="国资集团",
                property_name="测试物业",
                created_at=test_date,
                updated_at=test_date
            )
        ]
        
        exporter = AssetDataExporter()
        df = exporter.convert_assets_to_dataframe(
            assets, 
            ["ownership_entity", "property_name", "created_at", "updated_at"]
        )
        
        # 验证日期格式化
        created_at_values = df["created_at"].to_list()
        assert created_at_values[0] == "2024年01月15日"
    
    def test_null_value_handling(self):
        """测试空值处理"""
        class MockAsset:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        assets = [
            MockAsset(
                ownership_entity="国资集团",
                property_name="测试物业",
                management_entity=None,  # 空值
                land_area=None,  # 空值
                description=""  # 空字符串
            )
        ]
        
        exporter = AssetDataExporter()
        df = exporter.convert_assets_to_dataframe(
            assets, 
            ["ownership_entity", "property_name", "management_entity", "land_area", "description"]
        )
        
        # 验证空值处理
        management_entities = df["management_entity"].to_list()
        assert management_entities[0] == ""
        
        land_areas = df["land_area"].to_list()
        assert land_areas[0] == ""
        
        descriptions = df["description"].to_list()
        assert descriptions[0] == ""
    
    def test_numeric_value_handling(self):
        """测试数值处理"""
        class MockAsset:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        assets = [
            MockAsset(
                ownership_entity="国资集团",
                property_name="测试物业",
                actual_property_area=1000.5,  # 浮点数
                rentable_area=800,  # 整数
                rented_area=0.0  # 零值
            )
        ]
        
        exporter = AssetDataExporter()
        df = exporter.convert_assets_to_dataframe(
            assets, 
            ["ownership_entity", "property_name", "actual_property_area", "rentable_area", "rented_area"]
        )
        
        # 验证数值处理
        areas = df["actual_property_area"].to_list()
        assert areas[0] == 1000.5
        
        rentable_areas = df["rentable_area"].to_list()
        assert rentable_areas[0] == 800
        
        rented_areas = df["rented_area"].to_list()
        assert rented_areas[0] == 0.0


class TestExportPerformance:
    """测试导出性能"""
    
    def test_large_dataset_export(self):
        """测试大数据集导出性能"""
        # 创建大量模拟数据
        class MockAsset:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        size = 1000
        assets = []
        for i in range(size):
            assets.append(MockAsset(
                ownership_entity=f"权属方{i % 10}",
                property_name=f"测试物业{i}",
                address=f"测试地址{i}",
                actual_property_area=1000.0 + i,
                rentable_area=800.0 + i,
                rented_area=600.0 + i,
                unrented_area=200.0,
                non_commercial_area=200.0,
                ownership_status="已确权",
                actual_usage="商业",
                usage_status="出租",
                is_litigated="否",
                property_nature="经营类",
                occupancy_rate="75%"
            ))
        
        exporter = AssetDataExporter()
        
        # 测试转换性能
        import time
        start_time = time.time()
        
        df = exporter.convert_assets_to_dataframe(assets)
        df = exporter.rename_columns_for_export(df)
        stats = exporter.calculate_export_stats(df)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 验证结果
        assert len(df) == size
        assert stats["total_records"] == size
        
        # 性能要求：处理1000条记录应该在3秒内完成
        assert processing_time < 3.0, f"导出处理时间过长: {processing_time}秒"
        
        print(f"导出处理 {size} 条记录耗时: {processing_time:.2f}秒")