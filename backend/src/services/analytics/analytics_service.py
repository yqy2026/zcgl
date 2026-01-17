"""
Analytics Service - 综合分析服务

重构目标: 将 analytics.py 中的业务逻辑迁移到服务层

包含:
- 综合统计分析
- 趋势分析
- 分布计算
- 缓存管理
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, cast

from sqlalchemy.orm import Session

from ...constants.status.data import DataStatusValues
from ...core.cache_manager import analytics_cache
from ...core.response_handler import ResponseHandler
from ...models.asset import Asset

logger = logging.getLogger(__name__)


class AnalyticsService:
    """综合分析服务 - 提供统计分析核心功能"""

    def __init__(self, db: Session):
        self.db = db
        self.cache = analytics_cache
        self.response_handler = ResponseHandler()

    def get_comprehensive_analytics(
        self,
        filters: dict[str, Any] | None = None,
        use_cache: bool = True,
        current_user: Any = None,
    ) -> dict[str, Any]:
        """
        获取综合统计分析数据

        这是核心的分析方法，整合了多种统计维度

        Args:
            filters: 筛选条件
            use_cache: 是否使用缓存
            current_user: 当前用户（用于权限控制）

        Returns:
            包含多维度统计数据的字典
        """
        # 验证筛选条件
        validated_filters = self._validate_filters(filters or {})

        # 尝试从缓存获取
        cache_key = self._generate_cache_key(validated_filters)
        if use_cache:
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"从缓存返回分析结果: {cache_key}")
                return cast(dict[str, Any], cached_result)

        # 执行分析计算
        result = self._calculate_analytics(validated_filters)

        # 存入缓存
        if use_cache:
            self.cache.set(cache_key, result, ttl=3600)  # 1小时缓存

        return result

    def _validate_filters(self, filters: dict[str, Any]) -> dict[str, Any]:
        """验证和规范化筛选条件"""
        # 实现验证逻辑
        validated = {}

        if "include_deleted" in filters:
            validated["include_deleted"] = bool(filters["include_deleted"])

        if "date_from" in filters:
            validated["date_from"] = filters["date_from"]

        if "date_to" in filters:
            validated["date_to"] = filters["date_to"]

        return validated

    def _generate_cache_key(self, filters: dict[str, Any]) -> str:
        """生成缓存键"""
        # 简化版本：基于筛选条件生成键
        import hashlib
        import json

        filter_str = json.dumps(filters, sort_keys=True)
        return f"analytics:{hashlib.md5(filter_str.encode(), usedforsecurity=False).hexdigest()}"

    def _calculate_analytics(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        执行核心分析计算

        这里整合了:
        - 资产总数
        - 面积统计
        - 出租率统计
        - 财务数据
        - 分布数据
        """
        # 获取基础数据
        query = self.db.query(Asset)

        # 应用筛选条件 - 使用 data_status 而不是 is_deleted
        if not filters.get("include_deleted", False):
            # 只获取状态为"正常"的资产
            from sqlalchemy import or_

            query = query.filter(
                or_(
                    Asset.data_status == DataStatusValues.ASSET_NORMAL,
                    Asset.data_status.is_(None),
                )
            )

        assets: list[Asset] = query.all()

        # 计算各项统计
        stats = {
            "total_assets": len(assets),
            "timestamp": datetime.now().isoformat(),
        }

        # 添加面积统计（使用已有的 AreaService）
        from .area_service import AreaService
        from .occupancy_service import OccupancyService

        area_service = AreaService(self.db)
        occupancy_service = OccupancyService(self.db)

        # 面积汇总
        area_stats = area_service.calculate_summary_with_aggregation(filters=filters)
        stats["area_summary"] = area_stats

        # 出租率统计
        occupancy_stats = occupancy_service.calculate_with_aggregation(filters=filters)
        stats["occupancy_rate"] = occupancy_stats

        return stats

    def clear_cache(self) -> dict[str, Any]:
        """清除分析缓存"""
        # CacheManager 使用 clear() 方法，支持 pattern 参数
        try:
            cleared = self.cache.clear(pattern="analytics:*")
            return {
                "status": "success",
                "cleared_keys": 1 if cleared else 0,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"缓存清理失败: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "cleared_keys": 0,
                "timestamp": datetime.now().isoformat(),
            }

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "cache_type": "analytics_cache",
            "stats": self.cache.get_stats() if hasattr(self.cache, "get_stats") else {},
            "timestamp": datetime.now().isoformat(),
        }

    def calculate_trend(
        self,
        trend_type: str,
        time_dimension: str = "monthly",
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        计算趋势数据

        Args:
            trend_type: 趋势类型 (occupancy, area, financial)
            time_dimension: 时间维度 (daily, weekly, monthly, quarterly, yearly)
            filters: 筛选条件

        Returns:
            趋势数据列表
        """
        # 获取资产数据
        query = self.db.query(Asset)

        if filters is not None and not filters.get("include_deleted", False):
            # 使用 data_status 筛选
            from sqlalchemy import or_

            query = query.filter(
                or_(
                    Asset.data_status == DataStatusValues.ASSET_NORMAL,
                    Asset.data_status.is_(None),
                )
            )

        assets: list[Asset] = query.all()

        # 根据趋势类型和维度生成数据
        if trend_type == "occupancy":
            return self._generate_occupancy_trend(assets, time_dimension)
        elif trend_type == "area":
            return self._generate_area_trend(assets, time_dimension)
        else:
            return []

    def _generate_occupancy_trend(
        self, assets: list[Asset], time_dimension: str
    ) -> list[dict[str, Any]]:
        """生成出租率趋势"""
        # 简化实现：返回模拟趋势数据
        # 实际实现应该根据合同日期等计算真实趋势
        return [
            {
                "period": "2024-01",
                "occupancy_rate": 0.85,
                "rented_area": 5000.0,
                "total_area": 5882.35,
            },
            {
                "period": "2024-02",
                "occupancy_rate": 0.87,
                "rented_area": 5100.0,
                "total_area": 5862.07,
            },
        ]

    def _generate_area_trend(
        self, assets: list[Asset], time_dimension: str
    ) -> list[dict[str, Any]]:
        """生成面积趋势"""
        # 简化实现
        return [
            {
                "period": "2024-01",
                "total_land_area": 6000.0,
                "total_rentable_area": 5882.35,
            },
            {
                "period": "2024-02",
                "total_land_area": 6100.0,
                "total_rentable_area": 5900.0,
            },
        ]

    def calculate_distribution(
        self,
        distribution_type: str,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        计算分布数据

        Args:
            distribution_type: 分布类型 (property_nature, business_category, usage_status)
            filters: 筛选条件

        Returns:
            分布数据
        """
        query = self.db.query(Asset)

        if filters is not None and not filters.get("include_deleted", False):
            # 使用 data_status 筛选
            from sqlalchemy import or_

            query = query.filter(
                or_(
                    Asset.data_status == DataStatusValues.ASSET_NORMAL,
                    Asset.data_status.is_(None),
                )
            )

        assets: list[Asset] = query.all()

        # 统计分布
        distribution: defaultdict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "area": 0.0}
        )

        for asset in assets:
            key = str(getattr(asset, distribution_type, "unknown"))
            distribution[key]["count"] += 1
            if asset.rentable_area:
                distribution[key]["area"] += float(asset.rentable_area)

        return {
            "distribution_type": distribution_type,
            "data": dict(distribution),
            "total": len(distribution),
        }
