"""
统计和报表功能测试
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import Mock, patch
import json

from src.main import app
from src.database import get_db
from src.models.asset import Asset
from src.services.statistics import AssetStatisticsAnalyzer, ReportService, StatisticsError


# 测试客户端
client = TestClient(app)


# 测试数据
@pytest.fixture
def sample_assets():
    """创建测试资产数据"""
    assets = []
    
    # 资产1 - 已确权经营类
    asset1 = Asset(
        id=1,
        property_name="测试办公楼A",
        ownership_status="已确权",
        property_nature="经营类",
        usage_status="出租",
        ownership_entity="国资集团",
        actual_property_area=1000.0,
        rentable_area=800.0,
        rented_area=600.0,
        unrented_area=200.0,
        non_commercial_area=200.0
    )
    assets.append(asset1)
    
    # 资产2 - 未确权经营类
    asset2 = Asset(
        id=2,
        property_name="测试商场B",
        ownership_status="未确权",
        property_nature="经营类",
        usage_status="自用",
        ownership_entity="子公司A",
        actual_property_area=2000.0,
        rentable_area=1500.0,
        rented_area=1200.0,
        unrented_area=300.0,
        non_commercial_area=500.0
    )
    assets.append(asset2)
    
    # 资产3 - 已确权办公类
    asset3 = Asset(
        id=3,
        property_name="测试写字楼C",
        ownership_status="已确权",
        property_nature="办公类",
        usage_status="出租",
        ownership_entity="国资集团",
        actual_property_area=1500.0,
        rentable_area=1200.0,
        rented_area=1000.0,
        unrented_area=200.0,
        non_commercial_area=300.0
    )
    assets.append(asset3)
    
    return assets


class TestAssetStatisticsAnalyzer:
    """资产统计分析器测试"""
    
    def test_calculate_basic_statistics_empty_list(self):
        """测试空资产列表的基础统计"""
        result = AssetStatisticsAnalyzer.calculate_basic_statistics([])
        
        assert result["total_count"] == 0
        assert result["total_area"] == 0.0
        assert result["avg_area"] == 0.0
        assert result["overall_occupancy_rate"] == 0.0
    
    def test_calculate_basic_statistics_with_data(self, sample_assets):
        """测试有数据的基础统计"""
        result = AssetStatisticsAnalyzer.calculate_basic_statistics(sample_assets)
        
        assert result["total_count"] == 3
        assert result["total_area"] == 4500.0  # 1000 + 2000 + 1500
        assert result["avg_area"] == 1500.0    # 4500 / 3
        assert result["total_rentable_area"] == 3500.0  # 800 + 1500 + 1200
        assert result["total_rented_area"] == 2800.0    # 600 + 1200 + 1000
        assert result["total_unrented_area"] == 700.0   # 200 + 300 + 200
        assert result["overall_occupancy_rate"] == 80.0  # 2800 / 3500 * 100
    
    def test_analyze_ownership_distribution(self, sample_assets):
        """测试确权状态分布分析"""
        result = AssetStatisticsAnalyzer.analyze_ownership_distribution(sample_assets)
        
        assert "distribution" in result
        assert "chart_data" in result
        
        # 检查分布数据
        distribution = result["distribution"]
        assert "已确权" in distribution
        assert "未确权" in distribution
        assert distribution["已确权"]["count"] == 2
        assert distribution["未确权"]["count"] == 1
        assert distribution["已确权"]["percentage"] == 66.67
        assert distribution["未确权"]["percentage"] == 33.33
    
    def test_analyze_property_nature_distribution(self, sample_assets):
        """测试物业性质分布分析"""
        result = AssetStatisticsAnalyzer.analyze_property_nature_distribution(sample_assets)
        
        assert "distribution" in result
        assert "chart_data" in result
        
        # 检查分布数据
        distribution = result["distribution"]
        assert "经营类" in distribution
        assert "办公类" in distribution
        assert distribution["经营类"]["count"] == 2
        assert distribution["办公类"]["count"] == 1
        assert distribution["经营类"]["total_area"] == 3000.0  # 1000 + 2000
        assert distribution["办公类"]["total_area"] == 1500.0
    
    def test_analyze_usage_status_distribution(self, sample_assets):
        """测试使用状态分布分析"""
        result = AssetStatisticsAnalyzer.analyze_usage_status_distribution(sample_assets)
        
        assert "distribution" in result
        assert "chart_data" in result
        
        # 检查分布数据
        distribution = result["distribution"]
        assert "出租" in distribution
        assert "自用" in distribution
        assert distribution["出租"]["count"] == 2
        assert distribution["自用"]["count"] == 1
    
    def test_analyze_ownership_entity_distribution(self, sample_assets):
        """测试权属方分布分析"""
        result = AssetStatisticsAnalyzer.analyze_ownership_entity_distribution(sample_assets)
        
        assert "distribution" in result
        assert "chart_data" in result
        
        # 检查分布数据
        distribution = result["distribution"]
        assert "国资集团" in distribution
        assert "子公司A" in distribution
        assert distribution["国资集团"]["count"] == 2
        assert distribution["子公司A"]["count"] == 1
        assert distribution["国资集团"]["total_area"] == 2500.0  # 1000 + 1500
        assert distribution["子公司A"]["total_area"] == 2000.0
    
    def test_analyze_area_distribution(self, sample_assets):
        """测试面积分布分析"""
        result = AssetStatisticsAnalyzer.analyze_area_distribution(sample_assets)
        
        assert "area_ranges" in result
        assert "chart_data" in result
        assert "statistics" in result
        
        # 检查统计数据
        stats = result["statistics"]
        assert stats["min_area"] == 1000.0
        assert stats["max_area"] == 2000.0
        assert stats["avg_area"] == 1500.0
        assert stats["total_area"] == 4500.0
        assert stats["total_count"] == 3
    
    def test_generate_occupancy_analysis(self, sample_assets):
        """测试出租率分析"""
        result = AssetStatisticsAnalyzer.generate_occupancy_analysis(sample_assets)
        
        assert "overall_occupancy" in result
        assert "by_property_nature" in result
        assert "by_ownership_entity" in result
        assert "occupancy_ranges" in result
        assert "chart_data" in result
        
        # 检查整体出租率
        assert result["overall_occupancy"] == 80.0  # 2800 / 3500 * 100
        
        # 检查按物业性质分析
        by_nature = result["by_property_nature"]
        assert "经营类" in by_nature
        assert "办公类" in by_nature
        
        # 检查按权属方分析
        by_entity = result["by_ownership_entity"]
        assert "国资集团" in by_entity
        assert "子公司A" in by_entity


class TestReportService:
    """报表服务测试"""
    
    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def report_service(self):
        """创建报表服务实例"""
        return ReportService()
    
    @patch('src.services.statistics.get_db')
    def test_generate_dashboard_data_success(self, mock_get_db, report_service, sample_assets, mock_db):
        """测试成功生成仪表板数据"""
        # 模拟数据库返回
        mock_get_db.return_value = mock_db
        report_service.asset_crud.get_multi = Mock(return_value=sample_assets)
        
        # 执行测试
        result = report_service.generate_dashboard_data(db=mock_db)
        
        # 验证结果
        assert result["success"] is True
        assert "data" in result
        assert "key_metrics" in result["data"]
        assert "charts" in result["data"]
        
        # 验证关键指标
        key_metrics = result["data"]["key_metrics"]
        assert key_metrics["total_assets"] == 3
        assert key_metrics["total_area"] == 4500.0
        assert key_metrics["overall_occupancy_rate"] == 80.0
    
    @patch('src.services.statistics.get_db')
    def test_generate_dashboard_data_no_assets(self, mock_get_db, report_service, mock_db):
        """测试没有资产数据时的仪表板生成"""
        # 模拟数据库返回空列表
        mock_get_db.return_value = mock_db
        report_service.asset_crud.get_multi = Mock(return_value=[])
        
        # 执行测试
        result = report_service.generate_dashboard_data(db=mock_db)
        
        # 验证结果
        assert result["success"] is False
        assert "没有资产数据" in result["message"]
    
    @patch('src.services.statistics.get_db')
    def test_generate_comprehensive_report_success(self, mock_get_db, report_service, sample_assets, mock_db):
        """测试成功生成综合报表"""
        # 模拟数据库返回
        mock_get_db.return_value = mock_db
        report_service._get_filtered_assets = Mock(return_value=sample_assets)
        
        # 执行测试
        filters = {"ownership_status": "已确权"}
        result = report_service.generate_comprehensive_report(filters=filters, db=mock_db)
        
        # 验证结果
        assert result["success"] is True
        assert "data" in result
        
        # 验证报表数据结构
        data = result["data"]
        assert "basic_statistics" in data
        assert "ownership_distribution" in data
        assert "property_nature_distribution" in data
        assert "usage_status_distribution" in data
        assert "ownership_entity_distribution" in data
        assert "area_distribution" in data
        assert "occupancy_analysis" in data
        assert "generated_at" in data
        assert "filters_applied" in data
        assert data["filters_applied"] == filters
    
    def test_get_filtered_assets_no_filters(self, report_service, sample_assets, mock_db):
        """测试无筛选条件获取资产"""
        # 模拟CRUD返回
        report_service.asset_crud.get_multi = Mock(return_value=sample_assets)
        
        # 执行测试
        result = report_service._get_filtered_assets(None, mock_db)
        
        # 验证结果
        assert len(result) == 3
        report_service.asset_crud.get_multi.assert_called_once_with(mock_db, limit=10000)
    
    def test_get_filtered_assets_with_filters(self, report_service, sample_assets, mock_db):
        """测试有筛选条件获取资产"""
        # 模拟CRUD返回
        report_service.asset_crud.get_multi_with_search = Mock(return_value=sample_assets)
        
        # 执行测试
        filters = {"ownership_status": "已确权", "property_nature": "经营类"}
        result = report_service._get_filtered_assets(filters, mock_db)
        
        # 验证结果
        assert len(result) == 3
        report_service.asset_crud.get_multi_with_search.assert_called_once_with(
            db=mock_db,
            search=None,
            filters=filters,
            skip=0,
            limit=10000
        )


class TestStatisticsAPI:
    """统计API测试"""
    
    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return Mock(spec=Session)
    
    def test_get_dashboard_data_success(self, mock_db_session):
        """测试成功获取仪表板数据"""
        with patch('src.api.v1.statistics.get_db', return_value=mock_db_session):
            with patch('src.api.v1.statistics.ReportService') as mock_service:
                # 模拟服务返回
                mock_instance = mock_service.return_value
                mock_instance.generate_dashboard_data.return_value = {
                    "success": True,
                    "message": "成功生成仪表板数据",
                    "data": {
                        "key_metrics": {
                            "total_assets": 100,
                            "total_area": 50000.0,
                            "overall_occupancy_rate": 75.5
                        },
                        "charts": {
                            "ownership_distribution": []
                        }
                    }
                }
                
                # 发送请求
                response = client.get("/api/v1/statistics/dashboard")
                
                # 验证响应
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "data" in data
                assert "key_metrics" in data["data"]
    
    def test_generate_comprehensive_report_success(self, mock_db_session):
        """测试成功生成综合报表"""
        with patch('src.api.v1.statistics.get_db', return_value=mock_db_session):
            with patch('src.api.v1.statistics.ReportService') as mock_service:
                # 模拟服务返回
                mock_instance = mock_service.return_value
                mock_instance.generate_comprehensive_report.return_value = {
                    "success": True,
                    "message": "成功生成综合报表",
                    "data": {
                        "basic_statistics": {"total_count": 100},
                        "ownership_distribution": {"distribution": {}},
                        "generated_at": "2024-01-01T12:00:00"
                    }
                }
                
                # 发送请求
                request_data = {
                    "filters": {
                        "ownership_status": "已确权",
                        "property_nature": "经营类"
                    }
                }
                response = client.post("/api/v1/statistics/report", json=request_data)
                
                # 验证响应
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "data" in data
    
    def test_get_basic_statistics_with_filters(self, mock_db_session):
        """测试带筛选条件获取基础统计"""
        with patch('src.api.v1.statistics.get_db', return_value=mock_db_session):
            with patch('src.api.v1.statistics.ReportService') as mock_service:
                # 模拟服务返回
                mock_instance = mock_service.return_value
                mock_instance._get_filtered_assets.return_value = []  # 空列表测试
                
                # 发送请求
                response = client.get(
                    "/api/v1/statistics/basic",
                    params={
                        "ownership_status": "已确权",
                        "property_nature": "经营类"
                    }
                )
                
                # 验证响应
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is False
                assert "没有找到符合条件的资产数据" in data["message"]
    
    def test_get_ownership_distribution(self, mock_db_session):
        """测试获取确权状态分布"""
        with patch('src.api.v1.statistics.get_db', return_value=mock_db_session):
            with patch('src.api.v1.statistics.ReportService') as mock_service:
                # 模拟服务返回
                mock_instance = mock_service.return_value
                mock_instance._get_filtered_assets.return_value = []
                
                # 发送请求
                response = client.get("/api/v1/statistics/distribution/ownership")
                
                # 验证响应
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is False
    
    def test_api_error_handling(self, mock_db_session):
        """测试API错误处理"""
        with patch('src.api.v1.statistics.get_db', return_value=mock_db_session):
            with patch('src.api.v1.statistics.ReportService') as mock_service:
                # 模拟服务抛出异常
                mock_instance = mock_service.return_value
                mock_instance.generate_dashboard_data.side_effect = Exception("测试异常")
                
                # 发送请求
                response = client.get("/api/v1/statistics/dashboard")
                
                # 验证响应
                assert response.status_code == 500
                data = response.json()
                assert "获取仪表板数据失败" in data["detail"]


class TestStatisticsError:
    """统计异常测试"""
    
    def test_statistics_error_creation(self):
        """测试统计异常创建"""
        error = StatisticsError("测试错误消息")
        assert str(error) == "测试错误消息"
    
    def test_statistics_error_inheritance(self):
        """测试统计异常继承"""
        error = StatisticsError("测试")
        assert isinstance(error, Exception)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])