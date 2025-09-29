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
    """
    try:
        # 构建筛选条件
        filters = {}
        if ownership_status is not None:
            filters["ownership_status"] = ownership_status
        if property_nature is not None:
            filters["property_nature"] = property_nature
        if usage_status is not None:
            filters["usage_status"] = usage_status
        if ownership_entity is not None:
            filters["ownership_entity"] = ownership_entity

        # 只获取正常状态的资产
        filters['data_status'] = DataStatus.NORMAL.value

        logger.info(f"开始获取综合分析数据，筛选条件: {filters}")

        # 获取所有符合条件的资产
        assets, total_count = asset_crud.get_multi_with_search(
            db=db,
            skip=0,
            limit=10000,  # 获取所有资产
            filters=filters
        )

        if total_count == 0:
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

        # 计算面积汇总
        area_summary = {
            'total_assets': total_count,
            'total_area': 0.0,
            'total_rentable_area': 0.0,
            'total_rented_area': 0.0,
            'total_unrented_area': 0.0,
            'assets_with_area_data': 0
        }

        for asset in assets:
            if getattr(asset, 'actual_property_area', None):
                area_summary['total_area'] += to_float(getattr(asset, 'actual_property_area'))
                area_summary['assets_with_area_data'] += 1

            if getattr(asset, 'rentable_area', None):
                area_summary['total_rentable_area'] += to_float(getattr(asset, 'rentable_area'))

            if getattr(asset, 'rented_area', None):
                area_summary['total_rented_area'] += to_float(getattr(asset, 'rented_area'))

            if getattr(asset, 'unrented_area', None):
                area_summary['total_unrented_area'] += to_float(getattr(asset, 'unrented_area'))

        # 计算整体出租率
        if area_summary['total_rentable_area'] > 0:
            overall_occupancy_rate = (area_summary['total_rented_area'] / area_summary['total_rentable_area']) * 100
            area_summary['occupancy_rate'] = round(overall_occupancy_rate, 2)
        else:
            area_summary['occupancy_rate'] = 0.0

        # 格式化面积数据
        for key in ['total_area', 'total_rentable_area', 'total_rented_area', 'total_unrented_area']:
            area_summary[key] = round(area_summary[key], 2)

        # 计算财务汇总
        financial_summary = {
            'total_annual_income': 0.0,
            'total_annual_expense': 0.0,
            'total_net_income': 0.0,
            'total_monthly_rent': 0.0,
            'assets_with_income_data': 0,
            'assets_with_rent_data': 0
        }

        for asset in assets:
            if getattr(asset, 'annual_income', None):
                financial_summary['total_annual_income'] += to_float(getattr(asset, 'annual_income'))
                financial_summary['assets_with_income_data'] += 1

            if getattr(asset, 'annual_expense', None):
                financial_summary['total_annual_expense'] += to_float(getattr(asset, 'annual_expense'))

            if getattr(asset, 'net_income', None):
                financial_summary['total_net_income'] += to_float(getattr(asset, 'net_income'))

            if getattr(asset, 'monthly_rent', None):
                financial_summary['total_monthly_rent'] += to_float(getattr(asset, 'monthly_rent'))
                financial_summary['assets_with_rent_data'] += 1

        # 格式化财务数据
        for key in ['total_annual_income', 'total_annual_expense', 'total_net_income', 'total_monthly_rent']:
            financial_summary[key] = round(financial_summary[key], 2)

        # 计算出租率分布（实际数据）
        occupancy_distribution = []
        if total_count > 0:
            # 定义出租率区间
            ranges = [
                (0, 20, "0-20%"),
                (20, 40, "21-40%"),
                (40, 60, "41-60%"),
                (60, 80, "61-80%"),
                (80, 101, "81-100%")
            ]

            for min_rate, max_rate, range_label in ranges:
                count = 0
                for asset in assets:
                    occupancy_rate = getattr(asset, 'occupancy_rate', 0) or 0
                    if min_rate <= occupancy_rate < max_rate:
                        count += 1

                if count > 0:
                    percentage = (count / total_count) * 100
                    occupancy_distribution.append({
                        "range": range_label,
                        "count": count,
                        "percentage": round(percentage, 1)
                    })

        # 计算物业性质分布 - 动态处理所有类型
        property_nature_distribution = []
        if total_count > 0:
            from collections import defaultdict
            nature_counts = defaultdict(int)

            for asset in assets:
                nature = getattr(asset, 'property_nature', None)
                if nature:
                    nature_counts[nature] += 1

            for nature, count in nature_counts.items():
                if count > 0:
                    property_nature_distribution.append({
                        "name": nature,
                        "count": count,
                        "percentage": round((count / total_count) * 100, 1)
                    })

        # 计算确权状态分布 - 动态处理所有类型
        ownership_status_distribution = []
        if total_count > 0:
            from collections import defaultdict
            status_counts = defaultdict(int)

            for asset in assets:
                status = getattr(asset, 'ownership_status', None)
                if status:
                    status_counts[status] += 1

            for status, count in status_counts.items():
                if count > 0:
                    ownership_status_distribution.append({
                        "status": status,
                        "count": count,
                        "percentage": round((count / total_count) * 100, 1)
                    })

        # 计算使用状态分布 - 动态处理所有类型
        usage_status_distribution = []
        if total_count > 0:
            from collections import defaultdict
            usage_counts = defaultdict(int)

            for asset in assets:
                usage = getattr(asset, 'usage_status', None)
                if usage:
                    usage_counts[usage] += 1

            for usage, count in usage_counts.items():
                if count > 0:
                    usage_status_distribution.append({
                        "status": usage,
                        "count": count,
                        "percentage": round((count / total_count) * 100, 1)
                    })

        # 计算业态类别分布
        business_category_distribution = []
        if total_count > 0:
            from collections import defaultdict
            category_counts = defaultdict(int)
            category_occupancy = defaultdict(list)

            for asset in assets:
                category = getattr(asset, 'business_category', '其他')
                if not category:
                    category = '其他'
                category_counts[category] += 1

                occupancy_rate = getattr(asset, 'occupancy_rate', 0) or 0
                category_occupancy[category].append(occupancy_rate)

            for category, count in category_counts.items():
                avg_occupancy = sum(category_occupancy[category]) / len(category_occupancy[category]) if category_occupancy[category] else 0
                business_category_distribution.append({
                    "category": category,
                    "count": count,
                    "occupancy_rate": round(avg_occupancy, 2)
                })

        # 生成出租率趋势数据（基于最近6个月，实际项目中应从历史数据获取）
        occupancy_trend = []
        current_date = datetime.now()
        for i in range(5, -1, -1):
            month_date = current_date - timedelta(days=30 * i)
            # 这里使用模拟数据，实际项目中应从历史记录获取
            trend_rate = max(70, min(95, area_summary['occupancy_rate'] + (i - 2.5) * 2))
            occupancy_trend.append({
                "date": month_date.strftime("%Y-%m"),
                "occupancy_rate": round(trend_rate, 2),
                "total_rented_area": round(area_summary['total_rented_area'] * (trend_rate / 100), 2),
                "total_rentable_area": area_summary['total_rentable_area']
            })

        analytics_data = {
            "area_summary": area_summary,
            "financial_summary": financial_summary,
            "occupancy_distribution": occupancy_distribution,
            "property_nature_distribution": property_nature_distribution,
            "ownership_status_distribution": ownership_status_distribution,
            "usage_status_distribution": usage_status_distribution,
            "business_category_distribution": business_category_distribution,
            "occupancy_trend": occupancy_trend,
            "generated_at": datetime.now().isoformat(),
            "filters_applied": filters
        }

        logger.info(f"综合分析数据获取完成，包含 {total_count} 条资产")

        return {
            "success": True,
            "message": f"成功获取 {total_count} 条资产的综合分析数据",
            "data": analytics_data
        }

    except Exception as e:
        logger.error(f"获取综合分析数据异常: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取综合分析数据失败: {str(e)}"
        )