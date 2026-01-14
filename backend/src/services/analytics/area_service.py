"""
面积汇总计算服务 - 迁移自 statistics.py

提供面积汇总统计功能，支持数据库聚合和内存降级
"""

import logging
from typing import Any

from sqlalchemy import Float, case, func
from sqlalchemy import cast as sql_cast
from sqlalchemy.orm import Session

from ...crud.asset import asset_crud
from ...utils.numeric import to_float

logger = logging.getLogger(__name__)


class AreaCalculationError(Exception):
    """面积计算异常"""

    pass


class AreaService:
    """
    面积汇总计算服务

    提供整体面积汇总统计功能
    使用数据库聚合查询优化性能，支持降级到内存计算
    """

    def __init__(self, db: Session):
        """
        初始化面积服务

        Args:
            db: 数据库会话
        """
        self.db = db

    def calculate_summary_with_aggregation(
        self, filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        使用数据库聚合查询计算面积汇总 (原 _calculate_area_summary_with_aggregation)

        Args:
            filters: 筛选条件字典

        Returns:
            面积汇总统计结果，包含:
            - total_assets: 总资产数
            - total_land_area: 总土地面积
            - total_rentable_area: 总可出租面积
            - total_rented_area: 总已出租面积
            - total_unrented_area: 总未出租面积
            - total_non_commercial_area: 总非商业面积
            - assets_with_area_data: 有面积数据的资产数
            - overall_occupancy_rate: 整体出租率
        """
        try:
            from ...models.asset import Asset

            # 构建基础查询
            query = self.db.query(Asset)

            # 应用筛选条件
            if filters:
                for key, value in filters.items():
                    if hasattr(Asset, key) and value is not None:
                        query = query.filter(getattr(Asset, key) == value)

            # 使用数据库聚合函数计算
            result = query.with_entities(
                func.count(Asset.id).label("total_assets"),
                sql_cast(func.sum(func.coalesce(Asset.land_area, 0)), Float).label(
                    "total_land_area"
                ),
                sql_cast(func.sum(func.coalesce(Asset.rentable_area, 0)), Float).label(
                    "total_rentable_area"
                ),
                sql_cast(func.sum(func.coalesce(Asset.rented_area, 0)), Float).label(
                    "total_rented_area"
                ),
                sql_cast(
                    func.sum(func.coalesce(Asset.non_commercial_area, 0)), Float
                ).label("total_non_commercial_area"),
                func.count(case((Asset.land_area.isnot(None), 1))).label(
                    "assets_with_area_data"
                ),
            ).first()

            # 提取并转换结果
            if result is None:
                return {
                    "total_assets": 0,
                    "total_land_area": 0.0,
                    "total_rentable_area": 0.0,
                    "total_rented_area": 0.0,
                    "total_unrented_area": 0.0,
                    "total_non_commercial_area": 0.0,
                    "assets_with_area_data": 0,
                    "overall_occupancy_rate": 0.0,
                    "calculation_method": "aggregation",
                }

            total_assets = int(result.total_assets or 0)
            total_land_area = to_float(result.total_land_area)
            total_rentable_area = to_float(result.total_rentable_area)
            total_rented_area = to_float(result.total_rented_area)
            # 计算未出租面积（可出租面积 - 已出租面积）
            total_unrented_area = max(total_rentable_area - total_rented_area, 0.0)
            total_non_commercial_area = to_float(result.total_non_commercial_area)
            assets_with_area_data = int(result.assets_with_area_data or 0)

            # 计算整体出租率
            overall_occupancy_rate = (
                (total_rented_area / total_rentable_area * 100)
                if total_rentable_area > 0
                else 0.0
            )

            logger.info(
                f"数据库聚合查询完成面积汇总: 总资产={total_assets}, "
                f"有面积数据={assets_with_area_data}"
            )

            return {
                "total_assets": total_assets,
                "total_land_area": round(total_land_area, 2),
                "total_rentable_area": round(total_rentable_area, 2),
                "total_rented_area": round(total_rented_area, 2),
                "total_unrented_area": round(total_unrented_area, 2),
                "total_non_commercial_area": round(total_non_commercial_area, 2),
                "assets_with_area_data": assets_with_area_data,
                "overall_occupancy_rate": round(overall_occupancy_rate, 2),
                "calculation_method": "aggregation",
            }

        except Exception as e:
            logger.error(f"面积汇总数据库聚合查询失败: {str(e)}，降级到内存计算")
            # 降级到内存计算
            memory_result = self._calculate_summary_in_memory(filters)
            memory_result["calculation_method"] = "memory_fallback"
            return memory_result

    def _calculate_summary_in_memory(
        self, filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        内存计算面积汇总 (原 _calculate_area_summary_in_memory)

        Args:
            filters: 筛选条件字典

        Returns:
            面积汇总统计结果
        """
        try:
            # 分批获取数据
            batch_size = 1000
            offset = 0
            all_assets = []

            while True:
                assets_batch, _ = asset_crud.get_multi_with_search(
                    db=self.db, skip=offset, limit=batch_size, filters=filters
                )

                if not assets_batch:
                    break

                all_assets.extend(assets_batch)
                offset += batch_size

                if len(assets_batch) < batch_size:
                    break

            logger.info(f"面积汇总内存计算模式：获取到 {len(all_assets)} 个资产")

            # 计算面积汇总
            summary = {
                "total_assets": len(all_assets),
                "total_land_area": 0.0,
                "total_rentable_area": 0.0,
                "total_rented_area": 0.0,
                "total_unrented_area": 0.0,
                "total_non_commercial_area": 0.0,
                "assets_with_area_data": 0,
            }

            for asset in all_assets:
                if getattr(asset, "land_area", None):
                    summary["total_land_area"] += to_float(getattr(asset, "land_area"))
                    summary["assets_with_area_data"] += 1

                if getattr(asset, "rentable_area", None):
                    summary["total_rentable_area"] += to_float(
                        getattr(asset, "rentable_area")
                    )

                if getattr(asset, "rented_area", None):
                    summary["total_rented_area"] += to_float(
                        getattr(asset, "rented_area")
                    )

                if getattr(asset, "unrented_area", None):
                    summary["total_unrented_area"] += to_float(
                        getattr(asset, "unrented_area")
                    )

                if getattr(asset, "non_commercial_area", None):
                    summary["total_non_commercial_area"] += to_float(
                        getattr(asset, "non_commercial_area")
                    )

            # 计算整体出租率
            if summary["total_rentable_area"] > 0:
                overall_occupancy_rate = (
                    summary["total_rented_area"] / summary["total_rentable_area"]
                ) * 100
                summary["overall_occupancy_rate"] = round(overall_occupancy_rate, 2)
            else:
                summary["overall_occupancy_rate"] = 0.0

            # 格式化数据
            for key in [
                "total_land_area",
                "total_rentable_area",
                "total_rented_area",
                "total_unrented_area",
                "total_non_commercial_area",
            ]:
                summary[key] = round(summary[key], 2)

            return summary

        except Exception as e:
            logger.error(f"面积汇总内存计算失败: {str(e)}")
            raise AreaCalculationError(f"面积汇总计算失败: {str(e)}")
