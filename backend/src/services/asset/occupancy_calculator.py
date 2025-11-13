from typing import Any

"""
出租率自动计算服务
提供实时出租率计算、趋势分析和预测功能
"""

import logging

from src.models.asset import Asset

logger = logging.getLogger(__name__)


class OccupancyCalculationError(Exception):
    """出租率计算异常"""

    pass


class OccupancyRateCalculator:
    """出租率计算器"""

    @staticmethod
    def calculate_individual_occupancy_rate(
        rentable_area: float, rented_area: float
    ) -> float:
        """
        计算单个资产的出租率

        Args:
            rentable_area: 可出租面积
            rented_area: 已出租面积

        Returns:
            出租率（百分比）
        """
        if not rentable_area or rentable_area <= 0:
            return 0.0

        if not rented_area or rented_area < 0:
            return 0.0

        # 确保已出租面积不超过可出租面积
        actual_rented = min(rented_area, rentable_area)

        occupancy_rate = (actual_rented / rentable_area) * 100
        return round(occupancy_rate, 2)

    @staticmethod
    def calculate_overall_occupancy_rate(assets: list[Asset]) -> dict[str, Any]:
        """
        计算整体出租率

        Args:
            assets: 资产列表

        Returns:
            整体出租率统计信息
        """
        try:
            if not assets:
                return {
                    "overall_rate": 0.0,
                    "total_rentable_area": 0.0,
                    "total_rented_area": 0.0,
                    "total_unrented_area": 0.0,
                    "asset_count": 0,
                    "rentable_asset_count": 0,
                }

            # 筛选出有可出租面积的资产
            rentable_assets = [
                asset
                for asset in assets
                if asset.rentable_area and asset.rentable_area > 0
            ]

            if not rentable_assets:
                return {
                    "overall_rate": 0.0,
                    "total_rentable_area": 0.0,
                    "total_rented_area": 0.0,
                    "total_unrented_area": 0.0,
                    "asset_count": len(assets),
                    "rentable_asset_count": 0,
                }

            # 使用数据库聚合计算，避免在内存中加载所有数据
            from sqlalchemy import func

            from ...database import get_db

            # 获取数据库连接
            db = next(get_db())

            try:
                # 使用SQL聚合函数计算总面积
                occupancy_stats = (
                    db.query(
                        func.sum(func.coalesce(Asset.rentable_area, 0)).label(
                            "total_rentable"
                        ),
                        func.sum(func.coalesce(Asset.rented_area, 0)).label(
                            "total_rented"
                        ),
                        func.count(Asset.id).label("total_count"),
                        func.count(
                            func.case([(Asset.rentable_area > 0, Asset.id)])
                        ).label("rentable_count"),
                    )
                    .filter(
                        Asset.include_in_occupancy_rate,
                        Asset.data_status.in_(["正常", "正常数据"]),
                    )
                    .first()
                )

                total_rentable = float(occupancy_stats.total_rentable or 0)
                total_rented = float(occupancy_stats.total_rented or 0)
                total_unrented = total_rentable - total_rented
                asset_count = occupancy_stats.total_count or 0
                rentable_asset_count = occupancy_stats.rentable_count or 0

            finally:
                db.close()

            # 计算整体出租率
            overall_rate = (
                (total_rented / total_rentable * 100) if total_rentable > 0 else 0.0
            )

            return {
                "overall_rate": round(overall_rate, 2),
                "total_rentable_area": round(total_rentable, 2),
                "total_rented_area": round(total_rented, 2),
                "total_unrented_area": round(total_unrented, 2),
                "asset_count": asset_count,
                "rentable_asset_count": rentable_asset_count,
            }

        except Exception as e:
            logger.error(f"计算整体出租率失败: {str(e)}")
            raise OccupancyCalculationError(f"计算整体出租率失败: {str(e)}")

    @staticmethod
    def calculate_occupancy_by_category(
        assets: list[Asset], category_field: str
    ) -> dict[str, dict[str, Any]]:
        """
        按分类计算出租率

        Args:
            assets: 资产列表
            category_field: 分类字段名

        Returns:
            按分类的出租率统计
        """
        try:
            if not assets:
                return {}

            # 按分类分组
            categories = {}
            for asset in assets:
                category_value = getattr(asset, category_field, None) or "未知"
                if category_value not in categories:
                    categories[category_value] = []
                categories[category_value].append(asset)

            # 计算每个分类的出租率
            result = {}
            for category, category_assets in categories.items():
                category_stats = (
                    OccupancyRateCalculator.calculate_overall_occupancy_rate(
                        category_assets
                    )
                )
                result[category] = category_stats

            return result

        except Exception as e:
            logger.error(f"按分类计算出租率失败: {str(e)}")
            raise OccupancyCalculationError(f"按分类计算出租率失败: {str(e)}")