"""
资产分析API路由 - 提供综合的统计分析数据

遵循最佳实践：
- 代码模块化和可重用
- 完善的错误处理
- 性能优化
- 清晰的日志记录
- 数据验证和一致性检查
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...database import get_db
from ...crud.asset import asset_crud
from ...services.asset_calculator import OccupancyRateCalculator
from ...schemas.asset import DataStatus

logger = logging.getLogger(__name__)

router = APIRouter()


class AnalyticsError(Exception):
    """分析服务专用异常"""
    pass


def to_float(value: Any) -> float:
    """安全转换为float，带有类型检查"""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError, ArithmeticError):
        logger.warning(f"无法将值 {value} 转换为float")
        return 0.0


def calculate_percentage(count: int, total: int) -> float:
    """安全计算百分比"""
    if total <= 0:
        return 0.0
    return round((count / total) * 100, 1)


class DistributionCalculator:
    """分布数据计算器 - 遵循单一职责原则"""

    @staticmethod
    def calculate_distribution(assets: List[Any], field_name: str,
                           result_key: str = None, value_key: str = "name") -> List[Dict[str, Any]]:
        """
        通用分布计算方法

        Args:
            assets: 资产列表
            field_name: 要统计的字段名
            result_key: 结果中的键名（默认为value_key）
            value_key: 值的键名

        Returns:
            分布数据列表
        """
        if not assets:
            return []

        result_key = result_key or value_key
        distribution_counts = defaultdict(int)

        # 统计各类型的数量
        for asset in assets:
            field_value = getattr(asset, field_name, None)
            if field_value and str(field_value).strip():
                distribution_counts[field_value] += 1

        total_count = len(assets)
        distribution = []

        # 生成分布数据
        for category, count in distribution_counts.items():
            if count > 0:  # 只包含有数据的类别
                distribution.append({
                    result_key: category,
                    "count": count,
                    "percentage": calculate_percentage(count, total_count)
                })

        # 按数量降序排列
        distribution.sort(key=lambda x: x["count"], reverse=True)

        logger.info(f"{field_name}分布计算完成，共{len(distribution)}个类别")
        return distribution

    @staticmethod
    def calculate_property_nature_distribution(assets: List[Any]) -> List[Dict[str, Any]]:
        """计算物业性质分布"""
        return DistributionCalculator.calculate_distribution(assets, "property_nature")

    @staticmethod
    def calculate_ownership_status_distribution(assets: List[Any]) -> List[Dict[str, Any]]:
        """计算确权状态分布"""
        return DistributionCalculator.calculate_distribution(assets, "ownership_status", "status")

    @staticmethod
    def calculate_usage_status_distribution(assets: List[Any]) -> List[Dict[str, Any]]:
        """计算使用状态分布"""
        return DistributionCalculator.calculate_distribution(assets, "usage_status", "status")

    @staticmethod
    def calculate_business_category_distribution(assets: List[Any]) -> List[Dict[str, Any]]:
        """计算业态类别分布（包含出租率计算）"""
        if not assets:
            return []

        category_stats = defaultdict(lambda: {"count": 0, "occupancy_rates": []})

        for asset in assets:
            category = getattr(asset, "business_category", None)
            if not category or not str(category).strip():
                category = "其他"

            category_stats[category]["count"] += 1

            # 收集出租率数据
            occupancy_rate = getattr(asset, "occupancy_rate", None) or 0
            category_stats[category]["occupancy_rates"].append(occupancy_rate)

        distribution = []
        for category, stats in category_stats.items():
            count = stats["count"]
            occupancy_rates = stats["occupancy_rates"]

            # 计算平均出租率
            avg_occupancy = sum(occupancy_rates) / len(occupancy_rates) if occupancy_rates else 0.0

            distribution.append({
                "category": category,
                "count": count,
                "occupancy_rate": round(avg_occupancy, 2)
            })

        # 按数量降序排列
        distribution.sort(key=lambda x: x["count"], reverse=True)

        logger.info(f"业态类别分布计算完成，共{len(distribution)}个类别")
        return distribution


class AreaSummaryCalculator:
    """面积汇总计算器"""

    @staticmethod
    def calculate_area_summary(assets: List[Any]) -> Dict[str, Any]:
        """计算面积汇总信息"""
        if not assets:
            return {
                "total_assets": 0,
                "total_area": 0.0,
                "total_rentable_area": 0.0,
                "total_rented_area": 0.0,
                "total_unrented_area": 0.0,
                "occupancy_rate": 0.0
            }

        summary = {
            "total_assets": len(assets),
            "total_area": 0.0,
            "total_rentable_area": 0.0,
            "total_rented_area": 0.0,
            "total_unrented_area": 0.0,
            "assets_with_area_data": 0
        }

        # 累计各种面积数据
        for asset in assets:
            has_area_data = False

            # 实际物业面积
            if getattr(asset, "actual_property_area", None):
                summary["total_area"] += to_float(getattr(asset, "actual_property_area"))
                has_area_data = True

            # 土地面积（作为备用）
            elif getattr(asset, "land_area", None):
                summary["total_area"] += to_float(getattr(asset, "land_area"))
                has_area_data = True

            # 可租面积
            if getattr(asset, "rentable_area", None):
                summary["total_rentable_area"] += to_float(getattr(asset, "rentable_area"))
                has_area_data = True

            # 已租面积
            if getattr(asset, "rented_area", None):
                summary["total_rented_area"] += to_float(getattr(asset, "rented_area"))

            # 未租面积
            if getattr(asset, "unrented_area", None):
                summary["total_unrented_area"] += to_float(getattr(asset, "unrented_area"))

            if has_area_data:
                summary["assets_with_area_data"] += 1

        # 计算整体出租率
        if summary["total_rentable_area"] > 0:
            occupancy_rate = (summary["total_rented_area"] / summary["total_rentable_area"]) * 100
            summary["occupancy_rate"] = round(occupancy_rate, 2)
        else:
            summary["occupancy_rate"] = 0.0

        # 格式化数据
        for key in ["total_area", "total_rentable_area", "total_rented_area", "total_unrented_area"]:
            summary[key] = round(summary[key], 2)

        logger.info(f"面积汇总计算完成，总面积: {summary['total_area']}㎡，出租率: {summary['occupancy_rate']}%")
        return summary


class FinancialSummaryCalculator:
    """财务汇总计算器"""

    @staticmethod
    def calculate_financial_summary(assets: List[Any]) -> Dict[str, Any]:
        """计算财务汇总信息"""
        if not assets:
            return {
                "total_annual_income": 0.0,
                "total_annual_expense": 0.0,
                "total_net_income": 0.0,
                "total_monthly_rent": 0.0,
                "assets_with_income_data": 0,
                "assets_with_rent_data": 0
            }

        summary = {
            "total_annual_income": 0.0,
            "total_annual_expense": 0.0,
            "total_net_income": 0.0,
            "total_monthly_rent": 0.0,
            "total_deposit": 0.0,
            "assets_with_income_data": 0,
            "assets_with_rent_data": 0
        }

        for asset in assets:
            # 年收入数据
            if getattr(asset, "annual_income", None):
                summary["total_annual_income"] += to_float(getattr(asset, "annual_income"))
                summary["assets_with_income_data"] += 1

            # 年支出数据
            if getattr(asset, "annual_expense", None):
                summary["total_annual_expense"] += to_float(getattr(asset, "annual_expense"))

            # 月租金数据
            if getattr(asset, "monthly_rent", None):
                summary["total_monthly_rent"] += to_float(getattr(asset, "monthly_rent"))
                summary["assets_with_rent_data"] += 1

            # 押金数据
            if getattr(asset, "deposit", None):
                summary["total_deposit"] += to_float(getattr(asset, "deposit"))

        # 计算净收益
        summary["total_net_income"] = summary["total_annual_income"] - summary["total_annual_expense"]

        # 格式化数据
        for key in ["total_annual_income", "total_annual_expense", "total_net_income",
                   "total_monthly_rent", "total_deposit"]:
            summary[key] = round(summary[key], 2)

        logger.info(f"财务汇总计算完成，年收入: {summary['total_annual_income']}，净收益: {summary['total_net_income']}")
        return summary


class OccupancyDistributionCalculator:
    """出租率分布计算器"""

    @staticmethod
    def calculate_occupancy_distribution(assets: List[Any]) -> List[Dict[str, Any]]:
        """计算出租率区间分布"""
        if not assets:
            return []

        # 定义出租率区间
        ranges = [
            (0, 20, "0-20%"),
            (20, 40, "20-40%"),
            (40, 60, "40-60%"),
            (60, 80, "60-80%"),
            (80, 101, "80-100%")
        ]

        total_count = len(assets)
        occupancy_distribution = []

        for min_rate, max_rate, range_label in ranges:
            count = 0
            for asset in assets:
                occupancy_rate = getattr(asset, 'occupancy_rate', 0) or 0
                if min_rate <= occupancy_rate < max_rate:
                    count += 1

            if count > 0:
                percentage = calculate_percentage(count, total_count)
                occupancy_distribution.append({
                    "range": range_label,
                    "count": count,
                    "percentage": percentage
                })

        logger.info(f"出租率分布计算完成，共{len(occupancy_distribution)}个区间")
        return occupancy_distribution


class OccupancyTrendGenerator:
    """出租率趋势生成器"""

    @staticmethod
    def generate_occupancy_trend(assets: List[Any]) -> List[Dict[str, Any]]:
        """生成出租率趋势数据（模拟6个月趋势）"""
        if not assets:
            return []

        # 基于当前数据生成趋势数据
        current_area_summary = AreaSummaryCalculator.calculate_area_summary(assets)
        current_rate = current_area_summary["occupancy_rate"]
        current_rented = current_area_summary["total_rented_area"]
        current_rentable = current_area_summary["total_rentable_area"]

        # 生成模拟的趋势数据（实际项目中应从历史数据获取）
        trend_data = []
        base_variation = 0.05  # 5%的基准变化

        for i in range(5, -1, -1):
            # 模拟月份
            month_date = datetime.now() - timedelta(days=30 * i)
            month_label = f"{month_date.month}月"

            # 添加一些随机变化，保持总体趋势
            variation = (1 + base_variation * (i - 2.5) / 2.5)  # 中心为当前值
            simulated_rate = max(0, min(100, current_rate * variation))
            simulated_rented = current_rentable * simulated_rate / 100

            trend_data.append({
                "date": month_label,
                "occupancy_rate": round(simulated_rate, 2),
                "total_rented_area": round(simulated_rented, 2),
                "total_rentable_area": current_rentable
            })

        logger.info(f"出租率趋势数据生成完成，共{len(trend_data)}个月")
        return trend_data


def validate_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    """验证和清理筛选条件"""
    validated_filters = {}

    for key, value in filters.items():
        if value is not None and str(value).strip():
            validated_filters[key] = str(value).strip()

    # 添加数据状态筛选
    validated_filters['data_status'] = DataStatus.NORMAL.value

    logger.info(f"筛选条件验证完成: {validated_filters}")
    return validated_filters


def create_empty_response() -> Dict[str, Any]:
    """创建空数据响应"""
    return {
        "success": True,
        "message": "没有找到符合条件的资产数据",
        "data": {
            "area_summary": {
                "total_assets": 0,
                "total_area": 0.0,
                "total_rentable_area": 0.0,
                "total_rented_area": 0.0,
                "total_unrented_area": 0.0,
                "occupancy_rate": 0.0
            },
            "financial_summary": {
                "total_annual_income": 0.0,
                "total_annual_expense": 0.0,
                "total_net_income": 0.0,
                "total_monthly_rent": 0.0,
                "assets_with_income_data": 0,
                "assets_with_rent_data": 0
            },
            "occupancy_distribution": [],
            "property_nature_distribution": [],
            "ownership_status_distribution": [],
            "usage_status_distribution": [],
            "business_category_distribution": [],
            "occupancy_trend": []
        }
    }


@router.get("/comprehensive", summary="获取综合统计分析数据")
async def get_comprehensive_analytics(
    ownership_status: Optional[str] = Query(None, description="确权状态筛选"),
    property_nature: Optional[str] = Query(None, description="物业性质筛选"),
    usage_status: Optional[str] = Query(None, description="使用状态筛选"),
    ownership_entity: Optional[str] = Query(None, description="权属方筛选"),
    db: Session = Depends(get_db)
):
    """
    获取综合统计分析数据，包含所有必要的分析指标

    返回数据包括：
    - 面积汇总统计
    - 财务汇总统计
    - 各种分类分布数据
    - 出租率趋势分析
    """
    try:
        # 构建和验证筛选条件
        raw_filters = {
            "ownership_status": ownership_status,
            "property_nature": property_nature,
            "usage_status": usage_status,
            "ownership_entity": ownership_entity
        }

        filters = validate_filters(raw_filters)
        logger.info(f"开始获取综合分析数据，筛选条件: {filters}")

        # 获取所有符合条件的资产
        assets, total_count = asset_crud.get_multi_with_search(
            db=db,
            skip=0,
            limit=10000,  # 获取所有资产
            filters=filters
        )

        if total_count == 0:
            logger.info("未找到符合条件的资产数据")
            return create_empty_response()

        logger.info(f"成功获取{total_count}条资产数据，开始计算分析指标")

        # 使用专门的计算器进行各项统计计算
        area_summary = AreaSummaryCalculator.calculate_area_summary(assets)
        financial_summary = FinancialSummaryCalculator.calculate_financial_summary(assets)

        # 计算各种分布数据
        property_nature_distribution = DistributionCalculator.calculate_property_nature_distribution(assets)
        ownership_status_distribution = DistributionCalculator.calculate_ownership_status_distribution(assets)
        usage_status_distribution = DistributionCalculator.calculate_usage_status_distribution(assets)
        business_category_distribution = DistributionCalculator.calculate_business_category_distribution(assets)

        # 计算出租率分布和趋势
        occupancy_distribution = OccupancyDistributionCalculator.calculate_occupancy_distribution(assets)
        occupancy_trend = OccupancyTrendGenerator.generate_occupancy_trend(assets)

        # 构建响应数据
        response_data = {
            "area_summary": area_summary,
            "financial_summary": financial_summary,
            "occupancy_distribution": occupancy_distribution,
            "property_nature_distribution": property_nature_distribution,
            "ownership_status_distribution": ownership_status_distribution,
            "usage_status_distribution": usage_status_distribution,
            "business_category_distribution": business_category_distribution,
            "occupancy_trend": occupancy_trend
        }

        logger.info(f"综合分析数据计算完成，资产总数: {total_count}，出租率: {area_summary['occupancy_rate']}%")

        return {
            "success": True,
            "message": f"成功获取 {total_count} 条资产的综合分析数据",
            "data": response_data
        }

    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"获取综合分析数据时发生异常: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"获取综合分析数据失败: {str(e)}"
        )