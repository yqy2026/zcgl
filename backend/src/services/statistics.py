"""
数据统计和报表服务
使用Python内置功能进行数据分析和统计
"""

import logging
import statistics
from typing import Any

from sqlalchemy.orm import Session

from src.crud.asset import CRUDAsset
from src.models.asset import Asset

logger = logging.getLogger(__name__)


class StatisticsError(Exception):
    """统计分析异常"""

    pass


class AssetStatisticsAnalyzer:
    """资产数据统计分析器"""

    @staticmethod
    def calculate_basic_statistics(assets: list[Asset]) -> dict[str, Any]:
        """计算基础统计信息"""
        try:
            if not assets:
                return {
                    "total_count": 0,
                    "total_area": 0.0,
                    "avg_area": 0.0,
                    "total_rentable_area": 0.0,
                    "total_rented_area": 0.0,
                    "total_unrented_area": 0.0,
                    "overall_occupancy_rate": 0.0,
                }

            # 计算统计指标
            areas = [asset.actual_property_area or 0.0 for asset in assets]
            rentable_areas = [asset.rentable_area or 0.0 for asset in assets]
            rented_areas = [asset.rented_area or 0.0 for asset in assets]
            unrented_areas = [asset.unrented_area or 0.0 for asset in assets]
            non_commercial_areas = [
                asset.non_commercial_area or 0.0 for asset in assets
            ]

            stats = {
                "total_count": len(assets),
                "total_area": sum(areas),
                "avg_area": statistics.mean(areas) if areas else 0.0,
                "total_rentable_area": sum(rentable_areas),
                "total_rented_area": sum(rented_areas),
                "total_unrented_area": sum(unrented_areas),
                "total_non_commercial_area": sum(non_commercial_areas),
            }

            # 计算整体出租率
            total_rentable = stats["total_rentable_area"] or 0.0
            total_rented = stats["total_rented_area"] or 0.0
            overall_occupancy_rate = (
                (total_rented / total_rentable * 100) if total_rentable > 0 else 0.0
            )

            stats["overall_occupancy_rate"] = round(overall_occupancy_rate, 2)

            # 格式化数据
            for key in [
                "total_area",
                "avg_area",
                "total_rentable_area",
                "total_rented_area",
                "total_unrented_area",
                "total_non_commercial_area",
            ]:
                if stats[key] is not None:
                    stats[key] = round(stats[key], 2)
                else:
                    stats[key] = 0.0

            logger.info(f"计算基础统计完成，共 {stats['total_count']} 条资产")
            return stats

        except Exception as e:
            logger.error(f"计算基础统计失败: {str(e)}")
            raise StatisticsError(f"计算基础统计失败: {str(e)}")


class StatisticsService:
    """统计服务"""

    def __init__(self, db: Session):
        self.db = db
        self.analyzer = AssetStatisticsAnalyzer()
        self.asset_crud = CRUDAsset(Asset)

    def get_basic_statistics(self) -> dict[str, Any]:
        """获取基础统计信息"""
        try:
            assets = self.asset_crud.get_multi(self.db, limit=10000)
            return self.analyzer.calculate_basic_statistics(assets)
        except Exception as e:
            logger.error(f"获取基础统计失败: {str(e)}")
            raise StatisticsError(f"获取基础统计失败: {str(e)}")
