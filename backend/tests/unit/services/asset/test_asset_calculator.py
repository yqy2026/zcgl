"""
资产计算器单元测试

测试 AssetCalculator 和 OccupancyRateCalculator 的纯计算逻辑
"""

from src.services.asset.asset_calculator import (
    AssetCalculator,
    OccupancyRateCalculator,
)


# ============================================================================
# AssetCalculator.calculate_occupancy_rate 测试
# ============================================================================
class TestCalculateOccupancyRate:
    """测试出租率计算"""

    def test_normal_calculation(self):
        """测试正常情况下的出租率计算"""
        # 100平米中租了50平米，应该是50%
        result = AssetCalculator.calculate_occupancy_rate(100.0, 50.0)
        assert result == 50.0

    def test_fully_occupied(self):
        """测试全部出租"""
        result = AssetCalculator.calculate_occupancy_rate(100.0, 100.0)
        assert result == 100.0

    def test_fully_vacant(self):
        """测试全部空置"""
        result = AssetCalculator.calculate_occupancy_rate(100.0, 0.0)
        assert result == 0.0

    def test_rounding(self):
        """测试四舍五入 - 保留2位小数"""
        # 33.333...% 应该四舍五入为 33.33%
        result = AssetCalculator.calculate_occupancy_rate(300.0, 100.0)
        assert result == 33.33

    def test_rounding_up(self):
        """测试四舍五入 - 应该进位"""
        # 66.666...% 应该四舍五入为 66.67%
        result = AssetCalculator.calculate_occupancy_rate(300.0, 200.0)
        assert result == 66.67

    def test_rented_area_exceeds_rentable(self):
        """测试已出租面积大于可出租面积 - 应该被限制"""
        # 已出租面积大于可出租面积，应该被限制为100%
        result = AssetCalculator.calculate_occupancy_rate(100.0, 150.0)
        assert result == 100.0

    def test_no_rentable_area(self):
        """测试无可出租面积 - 应该返回0"""
        result = AssetCalculator.calculate_occupancy_rate(0.0, 50.0)
        assert result == 0.0

    def test_negative_rentable_area(self):
        """测试负的可出租面积 - 应该返回0"""
        result = AssetCalculator.calculate_occupancy_rate(-100.0, 50.0)
        assert result == 0.0

    def test_no_rented_area(self):
        """测试无已出租面积 - 应该返回0"""
        result = AssetCalculator.calculate_occupancy_rate(100.0, 0.0)
        assert result == 0.0

    def test_negative_rented_area(self):
        """测试负的已出租面积 - 应该返回0"""
        result = AssetCalculator.calculate_occupancy_rate(100.0, -50.0)
        assert result == 0.0

    def test_none_rentable_area(self):
        """测试可出租面积为None - 应该返回0"""
        result = AssetCalculator.calculate_occupancy_rate(None, 50.0)
        assert result == 0.0

    def test_none_rented_area(self):
        """测试已出租面积为None - 应该返回0"""
        result = AssetCalculator.calculate_occupancy_rate(100.0, None)
        assert result == 0.0

    def test_both_none(self):
        """测试两者都为None - 应该返回0"""
        result = AssetCalculator.calculate_occupancy_rate(None, None)
        assert result == 0.0

    def test_precise_calculation(self):
        """测试精确计算"""
        # 75.555...%
        result = AssetCalculator.calculate_occupancy_rate(900.0, 680.0)
        assert result == 75.56


# ============================================================================
# AssetCalculator.calculate_unrented_area 测试
# ============================================================================
class TestCalculateUnrentedArea:
    """测试未出租面积计算"""

    def test_normal_calculation(self):
        """测试正常情况"""
        # 100平米中租了50平米，剩余50平米
        result = AssetCalculator.calculate_unrented_area(100.0, 50.0)
        assert result == 50.0

    def test_fully_occupied(self):
        """测试全部出租 - 剩余0"""
        result = AssetCalculator.calculate_unrented_area(100.0, 100.0)
        assert result == 0.0

    def test_fully_vacant(self):
        """测试全部空置 - 剩余100"""
        result = AssetCalculator.calculate_unrented_area(100.0, 0.0)
        assert result == 100.0

    def test_rented_area_exceeds_rentable(self):
        """测试已出租面积大于可出租面积 - 应该返回0"""
        result = AssetCalculator.calculate_unrented_area(100.0, 150.0)
        assert result == 0.0

    def test_no_rentable_area(self):
        """测试无可出租面积 - 应该返回0"""
        result = AssetCalculator.calculate_unrented_area(0.0, 50.0)
        assert result == 0.0

    def test_negative_rentable_area(self):
        """测试负的可出租面积 - 应该返回0"""
        result = AssetCalculator.calculate_unrented_area(-100.0, 50.0)
        assert result == 0.0

    def test_no_rented_area_none(self):
        """测试已出租面积为None或0 - 应该返回可出租面积"""
        result = AssetCalculator.calculate_unrented_area(100.0, 0.0)
        assert result == 100.0

        result = AssetCalculator.calculate_unrented_area(100.0, None)
        assert result == 100.0

    def test_negative_rented_area(self):
        """测试负的已出租面积 - 应该返回可出租面积"""
        result = AssetCalculator.calculate_unrented_area(100.0, -50.0)
        assert result == 100.0

    def test_none_rentable_area(self):
        """测试可出租面积为None - 应该返回0"""
        result = AssetCalculator.calculate_unrented_area(None, 50.0)
        assert result == 0.0

    def test_decimal_result(self):
        """测试小数结果"""
        result = AssetCalculator.calculate_unrented_area(100.5, 33.33)
        assert abs(result - 67.17) < 0.01  # 允许小的浮点误差


# ============================================================================
# AssetCalculator.validate_area_consistency 测试
# ============================================================================
class TestValidateAreaConsistency:
    """测试面积一致性验证"""

    def test_valid_areas(self):
        """测试有效的面积数据"""
        data = {"rentable_area": 100.0, "rented_area": 50.0}
        errors = AssetCalculator.validate_area_consistency(data)
        assert len(errors) == 0

    def test_rented_exceeds_rentable(self):
        """测试已出租面积大于可出租面积"""
        data = {"rentable_area": 100.0, "rented_area": 150.0}
        errors = AssetCalculator.validate_area_consistency(data)
        assert len(errors) == 1
        assert "已出租面积不能大于可出租面积" in errors[0]

    def test_equal_areas(self):
        """测试相等面积（边界情况）"""
        data = {"rentable_area": 100.0, "rented_area": 100.0}
        errors = AssetCalculator.validate_area_consistency(data)
        assert len(errors) == 0

    def test_missing_rentable_area(self):
        """测试缺少可出租面积"""
        data = {"rented_area": 50.0}
        errors = AssetCalculator.validate_area_consistency(data)
        assert len(errors) == 0

    def test_missing_rented_area(self):
        """测试缺少已出租面积"""
        data = {"rentable_area": 100.0}
        errors = AssetCalculator.validate_area_consistency(data)
        assert len(errors) == 0

    def test_both_missing(self):
        """测试两者都缺失"""
        data = {}
        errors = AssetCalculator.validate_area_consistency(data)
        assert len(errors) == 0

    def test_negative_values(self):
        """测试负值 - 会触发一致性错误"""
        data = {"rentable_area": -100.0, "rented_area": -50.0}
        errors = AssetCalculator.validate_area_consistency(data)
        assert len(errors) == 1  # -50 > -100 为True，会触发错误


# ============================================================================
# AssetCalculator.auto_calculate_fields 测试
# ============================================================================
class TestAutoCalculateFields:
    """测试自动计算字段"""

    def test_returns_empty_dict(self):
        """测试返回空字典（简化版本不自动计算任何字段）"""
        data = {
            "rentable_area": 100.0,
            "rented_area": 50.0,
        }
        result = AssetCalculator.auto_calculate_fields(data)
        assert result == {}

    def test_does_not_modify_input(self):
        """测试不修改输入数据"""
        data = {
            "rentable_area": 100.0,
            "rented_area": 50.0,
        }
        original_data = data.copy()
        AssetCalculator.auto_calculate_fields(data)
        assert data == original_data


# ============================================================================
# AssetCalculator.enrich_asset_with_calculations 测试
# ============================================================================
class TestEnrichAssetWithCalculations:
    """测试资产数据丰富"""

    def test_enriches_asset_data(self):
        """测试丰富资产数据"""
        asset_data = {
            "id": 1,
            "property_name": "测试物业",
            "rentable_area": 100.0,
            "rented_area": 50.0,
        }
        result = AssetCalculator.enrich_asset_with_calculations(asset_data)

        # 应该包含原始数据
        assert result["id"] == 1
        assert result["property_name"] == "测试物业"
        assert result["rentable_area"] == 100.0
        assert result["rented_area"] == 50.0

    def test_does_not_modify_original(self):
        """测试不修改原始数据"""
        asset_data = {
            "id": 1,
            "property_name": "测试物业",
        }
        original_data = asset_data.copy()
        AssetCalculator.enrich_asset_with_calculations(asset_data)
        assert asset_data == original_data


# ============================================================================
# OccupancyRateCalculator.calculate_overall_occupancy_rate 测试
# ============================================================================
class MockAsset:
    """模拟资产对象"""

    def __init__(
        self,
        rentable_area: float | None = None,
        rented_area: float | None = None,
        include_in_occupancy_rate: bool = True,
    ):
        self.rentable_area = rentable_area
        self.rented_area = rented_area
        self.include_in_occupancy_rate = include_in_occupancy_rate


class TestCalculateOverallOccupancyRate:
    """测试整体出租率计算"""

    def test_normal_calculation(self):
        """测试正常计算"""
        assets = [
            MockAsset(rentable_area=100.0, rented_area=50.0),  # 50%
            MockAsset(rentable_area=100.0, rented_area=75.0),  # 75%
            MockAsset(rentable_area=100.0, rented_area=25.0),  # 25%
        ]
        # 总计: 300平米可租，150平米已租 = 50%
        result = OccupancyRateCalculator.calculate_overall_occupancy_rate(assets)

        assert result["overall_occupancy_rate"] == 50.0
        assert result["total_rentable_area"] == 300.0
        assert result["total_rented_area"] == 150.0
        assert result["total_unrented_area"] == 150.0
        assert result["included_assets_count"] == 3
        assert result["total_assets_count"] == 3

    def test_excludes_assets_not_included(self):
        """测试排除不计入出租率的资产"""
        assets = [
            MockAsset(rentable_area=100.0, rented_area=50.0, include_in_occupancy_rate=True),
            MockAsset(rentable_area=100.0, rented_area=100.0, include_in_occupancy_rate=False),  # 应该被排除
            MockAsset(rentable_area=100.0, rented_area=0.0, include_in_occupancy_rate=True),
        ]
        # 只计算前两个和最后一个: 200平米可租，50平米已租 = 25%
        result = OccupancyRateCalculator.calculate_overall_occupancy_rate(assets)

        assert result["overall_occupancy_rate"] == 25.0
        assert result["total_rentable_area"] == 200.0
        assert result["total_rented_area"] == 50.0
        assert result["included_assets_count"] == 2
        assert result["total_assets_count"] == 3

    def test_empty_asset_list(self):
        """测试空资产列表"""
        result = OccupancyRateCalculator.calculate_overall_occupancy_rate([])

        assert result["overall_occupancy_rate"] is None
        assert result["total_rentable_area"] == 0.0
        assert result["total_rented_area"] == 0.0
        assert result["total_unrented_area"] == 0.0
        assert result["included_assets_count"] == 0
        assert result["total_assets_count"] == 0

    def test_all_zero_rentable_area(self):
        """测试所有资产可出租面积为0"""
        assets = [
            MockAsset(rentable_area=0.0, rented_area=0.0),
            MockAsset(rentable_area=0.0, rented_area=0.0),
        ]
        result = OccupancyRateCalculator.calculate_overall_occupancy_rate(assets)

        assert result["overall_occupancy_rate"] is None
        assert result["total_rentable_area"] == 0.0
        assert result["included_assets_count"] == 0  # 不包含任何有效资产

    def test_handles_rented_exceeding_rentable(self):
        """测试处理已出租面积超过可出租面积的情况"""
        assets = [
            MockAsset(rentable_area=100.0, rented_area=150.0),  # 超出，应该被限制为100
        ]
        result = OccupancyRateCalculator.calculate_overall_occupancy_rate(assets)

        assert result["overall_occupancy_rate"] == 100.0
        assert result["total_rented_area"] == 100.0  # 被限制


# ============================================================================
# OccupancyRateCalculator.calculate_occupancy_by_category 测试
# ============================================================================
class TestCalculateOccupancyByCategory:
    """测试按类别计算出租率"""

    def test_normal_calculation(self):
        """测试正常计算"""
        assets = [
            MockAsset(rentable_area=100.0, rented_area=50.0),  # 默认"未分类"
            MockAsset(rentable_area=200.0, rented_area=100.0),  # 默认"未分类"
        ]

        # 手动添加类别属性
        assets[0].asset_category = "商业"
        assets[1].asset_category = "商业"

        result = OccupancyRateCalculator.calculate_occupancy_by_category(assets)

        assert "商业" in result
        assert result["商业"]["occupancy_rate"] == 50.0
        assert result["商业"]["rentable_area"] == 300.0
        assert result["商业"]["rented_area"] == 150.0
        assert result["商业"]["unrented_area"] == 150.0
        assert result["商业"]["asset_count"] == 2

    def test_multiple_categories(self):
        """测试多个类别"""
        assets = [
            MockAsset(rentable_area=100.0, rented_area=50.0),
            MockAsset(rentable_area=200.0, rented_area=200.0),
            MockAsset(rentable_area=50.0, rented_area=0.0),
        ]

        # 设置不同类别
        assets[0].asset_category = "商业"
        assets[1].asset_category = "住宅"
        assets[2].asset_category = "商业"

        result = OccupancyRateCalculator.calculate_occupancy_by_category(assets)

        assert "商业" in result
        assert "住宅" in result

        # 商业: 150平米可租，50平米已租 = 33.33%
        assert result["商业"]["occupancy_rate"] == 33.33
        assert result["商业"]["asset_count"] == 2

        # 住宅: 200平米可租，200平米已租 = 100%
        assert result["住宅"]["occupancy_rate"] == 100.0
        assert result["住宅"]["asset_count"] == 1

    def test_default_category(self):
        """测试默认分类"""
        assets = [
            MockAsset(rentable_area=100.0, rented_area=50.0),
        ]
        # 不设置类别
        result = OccupancyRateCalculator.calculate_occupancy_by_category(assets)

        assert "未分类" in result

    def test_excludes_assets_not_included(self):
        """测试排除不计入的资产"""
        assets = [
            MockAsset(
                rentable_area=100.0, rented_area=50.0, include_in_occupancy_rate=True
            ),
            MockAsset(
                rentable_area=100.0, rented_area=100.0, include_in_occupancy_rate=False
            ),
        ]

        assets[0].asset_category = "商业"
        assets[1].asset_category = "商业"

        result = OccupancyRateCalculator.calculate_occupancy_by_category(assets)

        # 只应该计算第一个资产
        assert result["商业"]["rentable_area"] == 100.0
        assert result["商业"]["rented_area"] == 50.0
        assert result["商业"]["asset_count"] == 1

    def test_custom_category_field(self):
        """测试自定义分类字段"""
        assets = [
            MockAsset(rentable_area=100.0, rented_area=50.0),
        ]
        assets[0].property_nature = "办公"

        result = OccupancyRateCalculator.calculate_occupancy_by_category(
            assets, category_field="property_nature"
        )

        assert "办公" in result
        assert "未分类" not in result
