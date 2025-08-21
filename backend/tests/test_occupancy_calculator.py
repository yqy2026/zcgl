"""
出租率自动计算功能单元测试
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from src.services.occupancy_calculator import (
    OccupancyRateCalculator, 
    OccupancyTrendAnalyzer, 
    OccupancyService,
    OccupancyCalculationError
)
from src.models.asset import Asset


class TestOccupancyRateCalculator:
    """出租率计算器测试"""
    
    def test_calculate_individual_occupancy_rate_normal(self):
        """测试正常情况下的单个资产出租率计算"""
        calculator = OccupancyRateCalculator()
        
        # 测试正常情况
        rate = calculator.calculate_individual_occupancy_rate(1000.0, 750.0)
        assert rate == 75.0
        
        # 测试满租情况
        rate = calculator.calculate_individual_occupancy_rate(1000.0, 1000.0)
        assert rate == 100.0
        
        # 测试空置情况
        rate = calculator.calculate_individual_occupancy_rate(1000.0, 0.0)
        assert rate == 0.0
    
    def test_calculate_individual_occupancy_rate_edge_cases(self):
        """测试边界情况"""
        calculator = OccupancyRateCalculator()
        
        # 测试可出租面积为0
        rate = calculator.calculate_individual_occupancy_rate(0.0, 100.0)
        assert rate == 0.0
        
        # 测试可出租面积为负数
        rate = calculator.calculate_individual_occupancy_rate(-100.0, 50.0)
        assert rate == 0.0
        
        # 测试已出租面积为负数
        rate = calculator.calculate_individual_occupancy_rate(1000.0, -50.0)
        assert rate == 0.0
        
        # 测试已出租面积超过可出租面积
        rate = calculator.calculate_individual_occupancy_rate(1000.0, 1200.0)
        assert rate == 100.0  # 应该限制在100%
        
        # 测试None值
        rate = calculator.calculate_individual_occupancy_rate(None, 100.0)
        assert rate == 0.0
        
        rate = calculator.calculate_individual_occupancy_rate(1000.0, None)
        assert rate == 0.0
    
    def test_calculate_overall_occupancy_rate_empty_list(self):
        """测试空资产列表"""
        calculator = OccupancyRateCalculator()
        
        result = calculator.calculate_overall_occupancy_rate([])
        
        assert result["overall_rate"] == 0.0
        assert result["total_rentable_area"] == 0.0
        assert result["total_rented_area"] == 0.0
        assert result["asset_count"] == 0
        assert result["rentable_asset_count"] == 0
    
    def test_calculate_overall_occupancy_rate_normal(self):
        """测试正常资产列表的整体出租率计算"""
        calculator = OccupancyRateCalculator()
        
        # 创建模拟资产
        assets = [
            Mock(rentable_area=1000.0, rented_area=800.0),
            Mock(rentable_area=500.0, rented_area=300.0),
            Mock(rentable_area=2000.0, rented_area=1500.0),
        ]
        
        result = calculator.calculate_overall_occupancy_rate(assets)
        
        # 总可出租面积: 1000 + 500 + 2000 = 3500
        # 总已出租面积: 800 + 300 + 1500 = 2600
        # 出租率: 2600 / 3500 * 100 = 74.29%
        assert result["overall_rate"] == 74.29
        assert result["total_rentable_area"] == 3500.0
        assert result["total_rented_area"] == 2600.0
        assert result["total_unrented_area"] == 900.0
        assert result["asset_count"] == 3
        assert result["rentable_asset_count"] == 3
    
    def test_calculate_overall_occupancy_rate_with_invalid_assets(self):
        """测试包含无效资产的情况"""
        calculator = OccupancyRateCalculator()
        
        # 创建包含无效资产的列表
        assets = [
            Mock(rentable_area=1000.0, rented_area=800.0),
            Mock(rentable_area=0.0, rented_area=300.0),  # 无可出租面积
            Mock(rentable_area=None, rented_area=500.0),  # None值
            Mock(rentable_area=2000.0, rented_area=1500.0),
        ]
        
        result = calculator.calculate_overall_occupancy_rate(assets)
        
        # 只有第1和第4个资产有效
        # 总可出租面积: 1000 + 2000 = 3000
        # 总已出租面积: 800 + 1500 = 2300
        # 出租率: 2300 / 3000 * 100 = 76.67%
        assert result["overall_rate"] == 76.67
        assert result["total_rentable_area"] == 3000.0
        assert result["total_rented_area"] == 2300.0
        assert result["asset_count"] == 4
        assert result["rentable_asset_count"] == 2
    
    def test_calculate_occupancy_by_category(self):
        """测试按分类计算出租率"""
        calculator = OccupancyRateCalculator()
        
        # 创建不同分类的资产
        assets = [
            Mock(rentable_area=1000.0, rented_area=800.0, property_nature="经营类"),
            Mock(rentable_area=500.0, rented_area=300.0, property_nature="经营类"),
            Mock(rentable_area=2000.0, rented_area=1500.0, property_nature="办公类"),
            Mock(rentable_area=1500.0, rented_area=1200.0, property_nature="办公类"),
        ]
        
        result = calculator.calculate_occupancy_by_category(assets, "property_nature")
        
        assert "经营类" in result
        assert "办公类" in result
        
        # 经营类: (800 + 300) / (1000 + 500) * 100 = 73.33%
        assert result["经营类"]["overall_rate"] == 73.33
        assert result["经营类"]["asset_count"] == 2
        
        # 办公类: (1500 + 1200) / (2000 + 1500) * 100 = 77.14%
        assert result["办公类"]["overall_rate"] == 77.14
        assert result["办公类"]["asset_count"] == 2
    
    def test_analyze_occupancy_distribution(self):
        """测试出租率分布分析"""
        calculator = OccupancyRateCalculator()
        
        # 创建不同出租率的资产
        assets = [
            Mock(rentable_area=1000.0, rented_area=100.0),   # 10% - 极低出租率
            Mock(rentable_area=1000.0, rented_area=400.0),   # 40% - 低出租率
            Mock(rentable_area=1000.0, rented_area=700.0),   # 70% - 中等出租率
            Mock(rentable_area=1000.0, rented_area=900.0),   # 90% - 高出租率
            Mock(rentable_area=1000.0, rented_area=1000.0),  # 100% - 满租
        ]
        
        result = calculator.analyze_occupancy_distribution(assets)
        
        assert "distribution" in result
        assert "statistics" in result
        assert "chart_data" in result
        
        # 检查统计数据
        stats = result["statistics"]
        assert stats["min_rate"] == 10.0
        assert stats["max_rate"] == 100.0
        assert stats["avg_rate"] == 62.0  # 实际计算结果
        assert stats["total_assets"] == 5


class TestOccupancyTrendAnalyzer:
    """出租率趋势分析器测试"""
    
    def test_calculate_trend_change(self):
        """测试趋势变化计算"""
        analyzer = OccupancyTrendAnalyzer()
        
        # 测试上升趋势
        result = analyzer.calculate_trend_change(80.0, 70.0)
        assert result["change"] == 10.0
        assert result["change_percentage"] == 14.29
        assert result["trend"] == "up"
        
        # 测试下降趋势
        result = analyzer.calculate_trend_change(60.0, 70.0)
        assert result["change"] == -10.0
        assert result["change_percentage"] == -14.29
        assert result["trend"] == "down"
        
        # 测试稳定趋势
        result = analyzer.calculate_trend_change(70.05, 70.0)
        assert result["trend"] == "stable"
        
        # 测试从0开始
        result = analyzer.calculate_trend_change(50.0, 0.0)
        assert result["change"] == 50.0
        assert result["change_percentage"] == 100.0
        assert result["trend"] == "up"
    
    def test_analyze_monthly_trend(self):
        """测试月度趋势分析"""
        analyzer = OccupancyTrendAnalyzer()
        
        # 创建模拟资产
        assets = [
            Mock(rentable_area=1000.0, rented_area=800.0),
            Mock(rentable_area=500.0, rented_area=300.0),
        ]
        
        result = analyzer.analyze_monthly_trend(assets, 6)
        
        assert "monthly_data" in result
        assert "trend_info" in result
        assert "avg_growth_rate" in result
        assert len(result["monthly_data"]) == 6
        assert result["period"] == "6个月"
    
    def test_predict_future_occupancy(self):
        """测试未来出租率预测"""
        analyzer = OccupancyTrendAnalyzer()
        
        # 创建模拟历史数据
        monthly_data = [
            {"month": "2024-01", "rate": 70.0},
            {"month": "2024-02", "rate": 72.0},
            {"month": "2024-03", "rate": 74.0},
            {"month": "2024-04", "rate": 76.0},
        ]
        
        predictions = analyzer.predict_future_occupancy(monthly_data, 3)
        
        assert len(predictions) == 3
        for pred in predictions:
            assert "month" in pred
            assert "predicted_rate" in pred
            assert "confidence" in pred
            assert 0 <= pred["confidence"] <= 1
        
        # 测试数据不足的情况
        predictions = analyzer.predict_future_occupancy([{"month": "2024-01", "rate": 70.0}], 3)
        assert len(predictions) == 0


class TestOccupancyService:
    """出租率服务测试"""
    
    @pytest.fixture
    def occupancy_service(self):
        """创建出租率服务实例"""
        return OccupancyService()
    
    @pytest.fixture
    def mock_assets(self):
        """创建模拟资产数据"""
        return [
            Mock(
                id="1",
                property_name="资产1",
                rentable_area=1000.0,
                rented_area=800.0,
                property_nature="经营类",
                ownership_entity="公司A",
                usage_status="正常使用"
            ),
            Mock(
                id="2",
                property_name="资产2",
                rentable_area=500.0,
                rented_area=300.0,
                property_nature="办公类",
                ownership_entity="公司B",
                usage_status="正常使用"
            ),
        ]
    
    async def test_calculate_comprehensive_occupancy(self, occupancy_service, mock_assets):
        """测试综合出租率分析"""
        # 模拟数据库会话
        mock_db = Mock()
        mock_db.commit = Mock()
        mock_db.rollback = Mock()
        
        # 模拟获取资产数据
        with patch.object(occupancy_service, '_get_filtered_assets', return_value=mock_assets):
            result = await occupancy_service.calculate_comprehensive_occupancy(db=mock_db)
            
            assert result["success"] is True
            assert "data" in result
            assert "overall_statistics" in result["data"]
            assert "by_property_nature" in result["data"]
            assert "distribution_analysis" in result["data"]
    
    async def test_calculate_comprehensive_occupancy_no_assets(self, occupancy_service):
        """测试没有资产数据的情况"""
        # 模拟数据库会话
        mock_db = Mock()
        mock_db.commit = Mock()
        mock_db.rollback = Mock()
        
        # 模拟没有资产数据
        with patch.object(occupancy_service, '_get_filtered_assets', return_value=[]):
            result = await occupancy_service.calculate_comprehensive_occupancy(db=mock_db)
            
            assert result["success"] is False
            assert "没有找到符合条件的资产数据" in result["message"]
    
    async def test_update_asset_occupancy_rates(self, occupancy_service, mock_assets):
        """测试更新资产出租率"""
        # 模拟数据库会话
        mock_db = Mock()
        mock_db.commit = Mock()
        mock_db.rollback = Mock()
        
        # 模拟CRUD操作
        mock_crud = Mock()
        mock_crud.get_multi.return_value = mock_assets
        mock_crud.update.return_value = None
        occupancy_service.asset_crud = mock_crud
        
        result = await occupancy_service.update_asset_occupancy_rates(db=mock_db)
        
        assert result["success"] is True
        assert result["updated_count"] == 2
        assert result["total_assets"] == 2
        
        # 验证update方法被调用
        assert mock_crud.update.call_count == 2
    
    async def test_get_occupancy_insights(self, occupancy_service, mock_assets):
        """测试出租率洞察分析"""
        # 模拟数据库会话
        mock_db = Mock()
        mock_db.commit = Mock()
        mock_db.rollback = Mock()
        
        # 模拟获取资产数据
        with patch.object(occupancy_service, '_get_filtered_assets', return_value=mock_assets):
            result = await occupancy_service.get_occupancy_insights(db=mock_db)
            
            assert result["success"] is True
            assert "data" in result
            assert "insights" in result["data"]
            assert "summary" in result["data"]
            assert isinstance(result["data"]["insights"], list)


class TestOccupancyCalculationError:
    """出租率计算异常测试"""
    
    def test_occupancy_calculation_error(self):
        """测试出租率计算异常"""
        error = OccupancyCalculationError("测试错误")
        assert str(error) == "测试错误"
        assert isinstance(error, Exception)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])