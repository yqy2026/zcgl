"""
出租率计算服务 - 迁移自 statistics.py

采用 OccupancyRateCalculator 的静态方法模式
"""

import logging
from typing import Any

from sqlalchemy import Float, case, func
from sqlalchemy import cast as sql_cast
from sqlalchemy.orm import Session

from ...crud.asset import asset_crud
from ...services.asset.occupancy_calculator import OccupancyRateCalculator
from ...utils.numeric import to_float

logger = logging.getLogger(__name__)


class OccupancyCalculationError(Exception):
    """出租率计算异常"""

    pass


class OccupancyService:
    """
    出租率计算服务

    提供整体出租率计算和分类出租率计算功能
    使用数据库聚合查询优化性能，支持降级到内存计算
    """

    def __init__(self, db: Session):
        """
        初始化出租率服务

        Args:
            db: 数据库会话
        """
        self.db = db

    def calculate_with_aggregation(
        self, filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        使用数据库聚合查询计算出租率 (原 _calculate_occupancy_with_aggregation)

        优点: 性能好，不加载所有数据到内存
        降级: 失败时自动回退到内存计算

        Args:
            filters: 筛选条件字典

        Returns:
            出租率统计结果，包含:
            - overall_rate: 整体出租率
            - total_rentable_area: 总可出租面积
            - total_rented_area: 总已出租面积
            - total_assets: 总资产数
            - rentable_assets_count: 可出租资产数
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

            # 使用数据库聚合函数计算 - 避免加载所有数据到内存
            result = query.with_entities(
                sql_cast(
                    func.sum(func.coalesce(Asset.rentable_area, 0)), Float
                ).label("total_rentable_area"),
                sql_cast(
                    func.sum(func.coalesce(Asset.rented_area, 0)), Float
                ).label("total_rented_area"),
                func.count(Asset.id).label("total_assets"),
                func.count(case((Asset.rentable_area > 0, 1))).label(
                    "rentable_assets_count"
                ),
            ).first()

            # 提取结果并转换为float
            if result is None:
                return {
                    "overall_rate": 0.0,
                    "total_rentable_area": 0.0,
                    "total_rented_area": 0.0,
                    "total_assets": 0,
                    "rentable_assets_count": 0,
                    "calculation_method": "aggregation",
                }

            total_rentable_area = to_float(result.total_rentable_area)
            total_rented_area = to_float(result.total_rented_area)
            total_assets = int(result.total_assets or 0)
            rentable_assets_count = int(result.rentable_assets_count or 0)

            # 计算出租率
            overall_rate = (
                (total_rented_area / total_rentable_area * 100)
                if total_rentable_area > 0
                else 0.0
            )

            logger.info(
                f"数据库聚合查询完成: 总资产={total_assets}, "
                f"可出租资产={rentable_assets_count}"
            )

            return {
                "overall_rate": round(overall_rate, 2),
                "total_rentable_area": round(total_rentable_area, 2),
                "total_rented_area": round(total_rented_area, 2),
                "total_assets": total_assets,
                "rentable_assets_count": rentable_assets_count,
                "calculation_method": "aggregation",
            }

        except Exception as e:
            logger.error(f"数据库聚合查询失败: {str(e)}，降级到内存计算")
            # 降级到内存计算
            memory_result = self._calculate_in_memory(filters)
            memory_result["calculation_method"] = "memory_fallback"
            return memory_result

    def _calculate_in_memory(
        self, filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        内存计算模式 (原 _calculate_occupancy_in_memory)

        使用现有的 OccupancyRateCalculator 进行计算

        Args:
            filters: 筛选条件字典

        Returns:
            出租率统计结果
        """
        try:
            # 分批获取数据以避免内存问题
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

                # 防止无限循环
                if len(assets_batch) < batch_size:
                    break

            logger.info(f"内存计算模式：获取到 {len(all_assets)} 个资产")

            # 使用现有的 OccupancyRateCalculator
            stats = OccupancyRateCalculator.calculate_overall_occupancy_rate(all_assets)

            return stats

        except Exception as e:
            logger.error(f"内存计算失败: {str(e)}")
            raise OccupancyCalculationError(f"出租率计算失败: {str(e)}")

    def calculate_category_with_aggregation(
        self, category_field: str, filters: dict[str, Any] | None = None
    ) -> dict[str, dict[str, Any]]:
        """
        使用数据库聚合查询计算分类出租率 (原 _calculate_category_occupancy_with_aggregation)

        Args:
            category_field: 分类字段名
            filters: 筛选条件字典

        Returns:
            按分类的出租率统计字典
        """
        try:
            from ...models.asset import Asset

            query = self.db.query(Asset)

            # 应用筛选条件
            if filters:
                for key, value in filters.items():
                    if hasattr(Asset, key) and value is not None:
                        query = query.filter(getattr(Asset, key) == value)

            # 按分类字段聚合查询
            results = (
                query.with_entities(
                    getattr(Asset, category_field).label("category"),
                    sql_cast(
                        func.sum(func.coalesce(Asset.rentable_area, 0)), Float
                    ).label("total_rentable_area"),
                    sql_cast(
                        func.sum(func.coalesce(Asset.rented_area, 0)), Float
                    ).label("total_rented_area"),
                    func.count(Asset.id).label("total_assets"),
                    func.count(case((Asset.rentable_area > 0, 1))).label(
                        "rentable_assets_count"
                    ),
                )
                .group_by(getattr(Asset, category_field))
                .all()
            )

            categories = {}
            for result in results:
                category = result.category or "未知"
                total_rentable = to_float(result.total_rentable_area)
                total_rented = to_float(result.total_rented_area)
                total_assets = int(result.total_assets or 0)
                rentable_assets = int(result.rentable_assets_count or 0)

                overall_rate = (
                    (total_rented / total_rentable * 100) if total_rentable > 0 else 0.0
                )
                total_unrented = max(total_rentable - total_rented, 0.0)

                categories[category] = {
                    "overall_rate": round(overall_rate, 2),
                    "total_rentable_area": round(total_rentable, 2),
                    "total_rented_area": round(total_rented, 2),
                    "total_unrented_area": round(total_unrented, 2),
                    "asset_count": total_assets,
                    "rentable_asset_count": rentable_assets,
                }

            return categories

        except Exception as e:
            logger.error(f"数据库分类聚合查询失败: {str(e)}")
            # 降级到内存计算
            return self._calculate_category_in_memory(category_field, filters)

    def _calculate_category_in_memory(
        self, category_field: str, filters: dict[str, Any] | None = None
    ) -> dict[str, dict[str, Any]]:
        """
        内存计算分类出租率 (原 _calculate_category_occupancy_in_memory)

        使用现有的 OccupancyRateCalculator 进行计算

        Args:
            category_field: 分类字段名
            filters: 筛选条件字典

        Returns:
            按分类的出租率统计字典
        """
        try:
            # 分批获取数据以避免内存问题
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

            logger.info(
                f"内存分类计算模式：获取到 {len(all_assets)} 个资产， "
                f"分类字段={category_field}"
            )

            # 使用现有的 OccupancyRateCalculator
            return OccupancyRateCalculator.calculate_occupancy_by_category(
                all_assets, category_field
            )

        except Exception as e:
            logger.error(f"内存分类计算失败: {str(e)}")
            raise OccupancyCalculationError(f"分类出租率计算失败: {str(e)}")
