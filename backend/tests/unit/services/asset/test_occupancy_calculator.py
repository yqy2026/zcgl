"""
Occupancy Calculator 单元测试

测试 OccupancyRateCalculator 的出租率计算功能
"""

from decimal import Decimal

import pytest

from src.services.asset.occupancy_calculator import (
    OccupancyCalculationError,
    OccupancyRateCalculator,
)


# ============================================================================
# Mock Helpers
# ============================================================================
class MockAsset:
    """模拟资产对象"""

    def __init__(
        self,
        id: str = "test-id",
        rentable_area: float | None = None,
        rented_area: float | None = None,
        include_in_occupancy_rate: bool = True,
        data_status: str = "正常",
    ):
        self.id = id
        self.rentable_area = (
            Decimal(str(rentable_area)) if rentable_area is not None else None
        )
        self.rented_area = (
            Decimal(str(rented_area)) if rented_area is not None else None
        )
        self.include_in_occupancy_rate = include_in_occupancy_rate
        self.data_status = data_status


# ============================================================================
# Test calculate_individual_occupancy_rate
# ============================================================================
class TestCalculateIndividualOccupancyRate:
    """测试单个资产出租率计算"""

    def test_normal_calculation(self):
        """测试正常计算 - 50%出租率"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(
            100.0, 50.0
        )
        assert result == 50.0

    def test_fully_occupied(self):
        """测试全部出租 - 100%"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(
            100.0, 100.0
        )
        assert result == 100.0

    def test_fully_vacant(self):
        """测试全部空置 - 0%"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(100.0, 0.0)
        assert result == 0.0

    def test_rounding_down(self):
        """测试四舍五入 - 33.33%"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(
            300.0, 100.0
        )
        assert result == 33.33

    def test_rounding_up(self):
        """测试四舍五入进位 - 66.67%"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(
            300.0, 200.0
        )
        assert result == 66.67

    def test_rented_exceeds_rentable_capped(self):
        """测试已出租面积超过可出租面积 - 应被限制"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(
            100.0, 150.0
        )
        assert result == 100.0

    def test_zero_rentable_area(self):
        """测试零可出租面积"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(0.0, 50.0)
        assert result == 0.0

    def test_negative_rentable_area(self):
        """测试负可出租面积"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(
            -100.0, 50.0
        )
        assert result == 0.0

    def test_zero_rented_area(self):
        """测试零已出租面积"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(100.0, 0.0)
        assert result == 0.0

    def test_negative_rented_area(self):
        """测试负已出租面积"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(
            100.0, -50.0
        )
        assert result == 0.0

    def test_none_rentable_area(self):
        """测试None可出租面积"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(None, 50.0)
        assert result == 0.0

    def test_none_rented_area(self):
        """测试None已出租面积"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(
            100.0, None
        )
        assert result == 0.0

    def test_both_none(self):
        """测试两者都为None"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(None, None)
        assert result == 0.0

    def test_empty_string_rentable(self):
        """测试空字符串可出租面积（falsy）"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(0, 50.0)
        assert result == 0.0

    def test_precise_calculation(self):
        """测试精确计算"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(
            900.0, 680.0
        )
        assert result == 75.56

    def test_very_small_occupancy(self):
        """测试极小出租率"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(
            10000.0, 1.0
        )
        assert result == 0.01

    def test_large_areas(self):
        """测试大面积数值"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(
            1000000.0, 750000.0
        )
        assert result == 75.0


# ============================================================================
# Test calculate_overall_occupancy_rate
# ============================================================================
class TestCalculateOverallOccupancyRate:
    """测试整体出租率计算"""

    def test_normal_calculation(self):
        """测试正常计算"""
        assets = [
            MockAsset(id="1", rentable_area=100.0, rented_area=50.0),
            MockAsset(id="2", rentable_area=100.0, rented_area=75.0),
            MockAsset(id="3", rentable_area=100.0, rented_area=25.0),
        ]

        result = OccupancyRateCalculator.calculate_overall_occupancy_rate(assets)

        assert result["overall_rate"] == 50.0
        assert result["total_rentable_area"] == 300.0
        assert result["total_rented_area"] == 150.0
        assert result["total_unrented_area"] == 150.0
        assert result["asset_count"] == 3
        assert result["rentable_asset_count"] == 3

    def test_empty_asset_list(self):
        """测试空资产列表"""
        result = OccupancyRateCalculator.calculate_overall_occupancy_rate([])

        assert result["overall_rate"] == 0.0
        assert result["total_rentable_area"] == 0.0
        assert result["total_rented_area"] == 0.0
        assert result["total_unrented_area"] == 0.0
        assert result["asset_count"] == 0
        assert result["rentable_asset_count"] == 0

    def test_all_assets_no_rentable_area(self):
        """测试所有资产无可出租面积"""
        assets = [
            MockAsset(id="1", rentable_area=0.0, rented_area=0.0),
            MockAsset(id="2", rentable_area=None, rented_area=None),
        ]

        result = OccupancyRateCalculator.calculate_overall_occupancy_rate(assets)

        assert result["overall_rate"] == 0.0
        assert result["total_rentable_area"] == 0.0
        assert result["total_rented_area"] == 0.0
        assert result["asset_count"] == 2
        assert result["rentable_asset_count"] == 0

    def test_assets_none_returns_zero(self):
        """测试None资产列表返回零值"""
        result = OccupancyRateCalculator.calculate_overall_occupancy_rate(assets=None)

        assert result["overall_rate"] == 0.0
        assert result["total_rentable_area"] == 0.0
        assert result["total_rented_area"] == 0.0
        assert result["asset_count"] == 0
        assert result["rentable_asset_count"] == 0

    def test_fully_occupied(self):
        """测试全部出租"""
        assets = [
            MockAsset(id="1", rentable_area=100.0, rented_area=100.0),
            MockAsset(id="2", rentable_area=100.0, rented_area=100.0),
        ]

        result = OccupancyRateCalculator.calculate_overall_occupancy_rate(assets)

        assert result["overall_rate"] == 100.0
        assert result["total_unrented_area"] == 0.0

    def test_fully_vacant(self):
        """测试全部空置"""
        assets = [
            MockAsset(id="1", rentable_area=100.0, rented_area=0.0),
            MockAsset(id="2", rentable_area=100.0, rented_area=0.0),
        ]

        result = OccupancyRateCalculator.calculate_overall_occupancy_rate(assets)

        assert result["overall_rate"] == 0.0
        assert result["total_unrented_area"] == 200.0

    def test_rounding_precision(self):
        """测试四舍五入精度"""
        assets = [MockAsset(id="1", rentable_area=100.0, rented_area=33.33)]

        result = OccupancyRateCalculator.calculate_overall_occupancy_rate(assets)

        assert result["overall_rate"] == 33.33  # 应该四舍五入

    def test_filters_by_include_in_occupancy_rate(self):
        """测试过滤include_in_occupancy_rate标志"""
        assets = [
            MockAsset(
                id="1",
                rentable_area=100.0,
                rented_area=50.0,
                include_in_occupancy_rate=True,
            ),
            MockAsset(
                id="2",
                rentable_area=100.0,
                rented_area=100.0,
                include_in_occupancy_rate=False,
            ),
        ]

        result = OccupancyRateCalculator.calculate_overall_occupancy_rate(assets)

        # 应该只计算第一个资产
        assert result["overall_rate"] == 50.0
        assert result["asset_count"] == 1

    def test_filters_by_data_status(self):
        """测试过滤data_status"""
        assets = [
            MockAsset(
                id="1", rentable_area=100.0, rented_area=50.0, data_status="正常"
            ),
            MockAsset(
                id="2", rentable_area=100.0, rented_area=100.0, data_status="正常数据"
            ),
            MockAsset(
                id="3", rentable_area=100.0, rented_area=0.0, data_status="已删除"
            ),
        ]

        result = OccupancyRateCalculator.calculate_overall_occupancy_rate(assets)

        # 应该只计算前两个
        assert result["overall_rate"] == 75.0

    def test_exception_handling(self):
        """测试异常处理"""
        class BadAsset:
            rentable_area = "bad"
            rented_area = 1
            include_in_occupancy_rate = True
            data_status = "正常"

        with pytest.raises(OccupancyCalculationError) as exc_info:
            OccupancyRateCalculator.calculate_overall_occupancy_rate([BadAsset()])

        assert "计算整体出租率失败" in str(exc_info.value)

    def test_large_scale_calculation(self):
        """测试大规模计算"""
        assets = [
            MockAsset(id=str(i), rentable_area=1000.0, rented_area=750.0)
            for i in range(1000)
        ]

        result = OccupancyRateCalculator.calculate_overall_occupancy_rate(assets)

        assert result["overall_rate"] == 75.0
        assert result["asset_count"] == 1000

    def test_mixed_valid_and_invalid_assets(self):
        """测试混合有效和无效资产"""
        assets = [
            MockAsset(id="1", rentable_area=100.0, rented_area=50.0),
            MockAsset(id="2", rentable_area=0.0, rented_area=0.0),
            MockAsset(id="3", rentable_area=200.0, rented_area=100.0),
            MockAsset(id="4", rentable_area=None, rented_area=None),
        ]

        result = OccupancyRateCalculator.calculate_overall_occupancy_rate(assets)

        assert result["overall_rate"] == 50.0
        assert result["asset_count"] == 2  # 只有2个有效资产


# ============================================================================
# Test calculate_occupancy_by_category
# ============================================================================
class TestCalculateOccupancyByCategory:
    """测试按分类计算出租率"""

    def test_single_category(self):
        """测试单个分类"""
        assets = [
            MockAsset(id="1", rentable_area=100.0, rented_area=50.0),
            MockAsset(id="2", rentable_area=200.0, rented_area=100.0),
        ]
        assets[0].ownership_category = "商业"
        assets[1].ownership_category = "商业"

        result = OccupancyRateCalculator.calculate_occupancy_by_category(
            assets, "ownership_category"
        )

        assert "商业" in result
        assert result["商业"]["overall_rate"] == 50.0
        assert result["商业"]["total_rentable_area"] == 300.0
        assert result["商业"]["total_rented_area"] == 150.0

    def test_multiple_categories(self):
        """测试多个分类"""
        assets = [
            MockAsset(id="1", rentable_area=100.0, rented_area=50.0),
            MockAsset(id="2", rentable_area=200.0, rented_area=100.0),
            MockAsset(id="3", rentable_area=200.0, rented_area=200.0),
        ]
        assets[0].ownership_category = "商业"
        assets[1].ownership_category = "商业"
        assets[2].ownership_category = "住宅"

        result = OccupancyRateCalculator.calculate_occupancy_by_category(
            assets, "ownership_category"
        )

        assert "商业" in result
        assert "住宅" in result
        assert result["商业"]["overall_rate"] == 50.0
        assert result["住宅"]["overall_rate"] == 100.0

    def test_unknown_category_for_none_values(self):
        """测试None值归类为'未知'"""
        assets = [
            MockAsset(id="1", rentable_area=100.0, rented_area=50.0),
        ]
        # 不设置分类字段，应该为None

        result = OccupancyRateCalculator.calculate_occupancy_by_category(
            assets, "ownership_category"
        )

        assert "未知" in result
        assert result["未知"]["overall_rate"] == 50.0

    def test_empty_asset_list(self):
        """测试空资产列表"""
        result = OccupancyRateCalculator.calculate_occupancy_by_category(
            [], "ownership_category"
        )

        assert result == {}

    def test_custom_category_field(self):
        """测试自定义分类字段"""
        assets = [
            MockAsset(id="1", rentable_area=100.0, rented_area=50.0),
        ]
        assets[0].property_nature = "办公"

        result = OccupancyRateCalculator.calculate_occupancy_by_category(
            assets, "property_nature"
        )

        assert "办公" in result

    def test_exception_propagation(self):
        """测试异常传播 - 当资产对象缺少必需属性时"""
        assets = [
            MockAsset(id="1", rentable_area=100.0, rented_area=50.0),
        ]
        # 不设置分类字段，访问不存在的属性应该不会抛出异常
        # 因为getattr有默认值"未知"

        # 测试访问不存在的分类字段（应该正常工作，使用"未知"作为分类）
        result = OccupancyRateCalculator.calculate_occupancy_by_category(
            assets, "nonexistent_field"
        )

        # 应该返回"未知"分类的结果
        assert "未知" in result
        assert result["未知"]["overall_rate"] == 50.0

    def test_category_with_no_rentable_assets(self):
        """测试包含无可出租面积的分类"""
        assets = [
            MockAsset(id="1", rentable_area=0.0, rented_area=0.0),
            MockAsset(id="2", rentable_area=None, rented_area=None),
        ]
        assets[0].ownership_category = "商业"
        assets[1].ownership_category = "商业"

        result = OccupancyRateCalculator.calculate_occupancy_by_category(
            assets, "ownership_category"
        )

        assert "商业" in result
        assert result["商业"]["overall_rate"] == 0.0


# ============================================================================
# Test Edge Cases and Numerical Precision
# ============================================================================
class TestNumericalPrecision:
    """测试数值精度和边界情况"""

    def test_very_small_percentage(self):
        """测试极小百分比"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(
            100000.0, 1.0
        )
        assert result == 0.0  # 应该四舍五入为0.0

    def test_very_large_areas(self):
        """测试极大面积数值"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(
            1e10, 7.5e9
        )
        assert result == 75.0

    def test_decimal_places_consistency(self):
        """测试小数位一致性"""
        result1 = OccupancyRateCalculator.calculate_individual_occupancy_rate(
            100.0, 33.333
        )
        result2 = OccupancyRateCalculator.calculate_individual_occupancy_rate(
            100.0, 66.666
        )

        # 都应该保留2位小数
        assert len(str(result1).split(".")[-1]) <= 2
        assert len(str(result2).split(".")[-1]) <= 2

    def test_near_100_percent(self):
        """测试接近100%的情况"""
        result = OccupancyRateCalculator.calculate_individual_occupancy_rate(
            100.0, 99.999
        )
        # 应该被限制为100.0
        assert result == 100.0


# ============================================================================
# Test Exception Class
# ============================================================================
class TestOccupancyCalculationError:
    """测试异常类"""

    def test_exception_creation(self):
        """测试异常创建"""
        error = OccupancyCalculationError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_exception_raising(self):
        """测试异常抛出"""
        with pytest.raises(OccupancyCalculationError) as exc_info:
            raise OccupancyCalculationError("Calculation failed")

        assert "Calculation failed" in str(exc_info.value)
