"""
性能优化模块
提供数据库查询优化、缓存策略和性能监控功能
"""

import logging
import time
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Any

from sqlalchemy import Index, func
from sqlalchemy.orm import Session, joinedload

from .config_manager import get_config

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.slow_query_threshold = get_config("slow_query_threshold_ms", 1000)
        self.enabled = get_config("performance_monitoring_enabled", True)
        self.query_stats: dict[str, dict] = {}

    def record_query(
        self,
        query_name: str,
        duration_ms: float,
        parameters: dict | None = None,
        result_count: int | None = None,
    ):
        """记录查询性能数据"""
        if not self.enabled:
            return

        if query_name not in self.query_stats:
            self.query_stats[query_name] = {
                "count": 0,
                "total_duration_ms": 0,
                "avg_duration_ms": 0,
                "min_duration_ms": float("inf"),
                "max_duration_ms": 0,
                "slow_queries": 0,
                "result_counts": [],
            }

        stats = self.query_stats[query_name]
        stats["count"] += 1
        stats["total_duration_ms"] += duration_ms
        stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["count"]
        stats["min_duration_ms"] = min(stats["min_duration_ms"], duration_ms)
        stats["max_duration_ms"] = max(stats["max_duration_ms"], duration_ms)

        if duration_ms > self.slow_query_threshold:
            stats["slow_queries"] += 1
            logger.warning(
                f"Slow query detected: {query_name} took {duration_ms:.2f}ms "
                f"(threshold: {self.slow_query_threshold}ms)"
            )

        if result_count is not None:
            stats["result_counts"].append(result_count)
            stats["avg_result_count"] = sum(stats["result_counts"]) / len(
                stats["result_counts"]
            )

        # 定期清理旧数据
        if stats["count"] % 100 == 0:
            stats["result_counts"] = stats["result_counts"][-50:]  # 保留最近50条

    def get_stats(self) -> dict[str, Any]:
        """获取性能统计"""
        if not self.enabled:
            return {"enabled": False}

        return {
            "enabled": True,
            "threshold_ms": self.slow_query_threshold,
            "query_stats": self.query_stats,
            "total_queries": sum(stats["count"] for stats in self.query_stats.values()),
            "total_slow_queries": sum(
                stats["slow_queries"] for stats in self.query_stats.values()
            ),
        }

    def reset_stats(self):
        """重置统计信息"""
        self.query_stats.clear()
        logger.info("Performance statistics reset")


# 全局性能监控器
performance_monitor = PerformanceMonitor()


def monitor_query(query_name: str):
    """查询性能监控装饰器"""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                # 尝试获取结果数量
                result_count = None
                if hasattr(result, "__len__"):
                    result_count = len(result)
                elif isinstance(result, list):
                    result_count = len(result)

                performance_monitor.record_query(
                    query_name=query_name,
                    duration_ms=duration_ms,
                    result_count=result_count,
                )

                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                performance_monitor.record_query(
                    query_name=f"{query_name}_FAILED",
                    duration_ms=duration_ms,
                    parameters={"error": str(e)},
                )
                raise

        return wrapper

    return decorator


class QueryOptimizer:
    """查询优化器"""

    def __init__(self, db: Session):
        self.db = db
        self.cache_enabled = get_config("cache_enabled", False)
        self.cache_ttl = get_config("cache_ttl_seconds", 3600)

    @contextmanager
    def query_with_monitoring(self, query_name: str):
        """带监控的查询上下文管理器"""
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            performance_monitor.record_query(
                query_name=query_name, duration_ms=duration_ms
            )

    def optimize_asset_query(self, include_related: bool = False):
        """优化资产查询"""
        with self.query_with_monitoring("optimized_asset_query"):
            from ..models.asset import Asset

            query = self.db.query(Asset)

            if include_related:
                # 使用joinedload避免N+1查询
                query = query.options(
                    joinedload(Asset.project), joinedload(Asset.ownership)
                )

            return query

    def optimize_asset_list_query(
        self,
        search: str | None = None,
        filters: dict | None = None,
        order_by: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ):
        """优化资产列表查询"""
        from ..models.asset import Asset

        with self.query_with_monitoring("optimized_asset_list_query"):
            query = self.db.query(Asset)

            # 添加搜索条件
            if search:
                search_conditions = [
                    Asset.property_name.ilike(f"%{search}%"),
                    Asset.address.ilike(f"%{search}%"),
                    Asset.ownership_entity.ilike(f"%{search}%"),
                ]
                query = query.filter(*search_conditions)

            # 添加筛选条件
            if filters:
                for field, value in filters.items():
                    if hasattr(Asset, field):
                        query = query.filter(getattr(Asset, field) == value)

            # 添加排序
            if order_by:
                if order_by.startswith("-"):
                    field = order_by[1:]
                    query = query.order_by(getattr(Asset, field).desc())
                else:
                    query = query.order_by(getattr(Asset, order_by))

            # 添加分页
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            return query

    def optimize_batch_update_query(self, asset_ids: list[str], update_data: dict):
        """优化批量更新查询"""
        from ..models.asset import Asset

        with self.query_with_monitoring("optimized_batch_update_query"):
            # 批量更新使用单个查询而不是循环
            return (
                self.db.query(Asset)
                .filter(Asset.id.in_(asset_ids))
                .update(update_data, synchronize_session=False)
            )

    def optimize_statistics_query(self):
        """优化统计查询"""
        from ..models.asset import Asset

        with self.query_with_monitoring("optimized_statistics_query"):
            # 使用聚合查询减少数据库往返
            stats = self.db.query(
                func.count(Asset.id).label("total_assets"),
                func.count(Asset.id)
                .filter(Asset.usage_status == "出租")
                .label("rented_assets"),
                func.sum(Asset.land_area).label("total_land_area"),
                func.sum(Asset.actual_property_area).label("total_property_area"),
                func.sum(Asset.rentable_area).label("total_rentable_area"),
                func.sum(Asset.rented_area).label("total_rented_area"),
            ).first()

            return stats


class CacheManager:
    """缓存管理器"""

    def __init__(self):
        self.cache = {}
        self.cache_enabled = get_config("cache_enabled", False)
        self.default_ttl = get_config("cache_ttl_seconds", 3600)
        self.max_size = get_config("cache_max_size", 1000)

    def _is_expired(self, cache_item: dict) -> bool:
        """检查缓存是否过期"""
        if not cache_item:
            return True
        return datetime.now(UTC) > cache_item["expires_at"]

    def _cleanup_expired(self):
        """清理过期缓存"""
        expired_keys = [
            key for key, item in self.cache.items() if self._is_expired(item)
        ]
        for key in expired_keys:
            del self.cache[key]

        # 如果缓存太大，删除最旧的一半
        if len(self.cache) > self.max_size:
            sorted_items = sorted(self.cache.items(), key=lambda x: x[1]["created_at"])
            delete_count = len(sorted_items) // 2
            for key, _ in sorted_items[:delete_count]:
                del self.cache[key]

    def get(self, key: str) -> Any | None:
        """获取缓存值"""
        if not self.cache_enabled:
            return None

        self._cleanup_expired()

        cache_item = self.cache.get(key)
        if cache_item and not self._is_expired(cache_item):
            return cache_item["value"]

        return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """设置缓存值"""
        if not self.cache_enabled:
            return

        self._cleanup_expired()

        ttl = ttl or self.default_ttl

        self.cache[key] = {
            "value": value,
            "created_at": datetime.now(UTC),
            "expires_at": datetime.now(UTC) + timedelta(seconds=ttl),
            "ttl": ttl,
        }

    def delete(self, key: str) -> None:
        """删除缓存值"""
        if key in self.cache:
            del self.cache[key]

    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """获取缓存统计"""
        return {
            "enabled": self.cache_enabled,
            "total_items": len(self.cache),
            "max_size": self.max_size,
            "memory_usage": sum(
                len(str(item["value"])) for item in self.cache.values()
            ),
        }


# 全局缓存管理器
cache_manager = CacheManager()


def cached(ttl: int | None = None, key_prefix: str = ""):
    """缓存装饰器"""

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"

            # 尝试从缓存获取
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 执行函数
            result = func(*args, **kwargs)

            # 缓存结果
            cache_manager.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


class DatabaseOptimizer:
    """数据库优化器"""

    def __init__(self, db: Session):
        self.db = db
        self.query_optimizer = QueryOptimizer(db)

    def create_indexes(self):
        """创建数据库索引"""
        from ..models.asset import Asset

        indexes = [
            # 资产相关索引
            Index("idx_asset_property_name", Asset.property_name),
            Index("idx_asset_address", Asset.address),
            Index("idx_asset_ownership_status", Asset.ownership_status),
            Index("idx_asset_property_nature", Asset.property_nature),
            Index("idx_asset_usage_status", Asset.usage_status),
            Index("idx_asset_project_id", Asset.project_id),
            Index("idx_asset_created_at", Asset.created_at),
            # 复合索引
            Index("idx_asset_status_usage", Asset.ownership_status, Asset.usage_status),
            Index("idx_asset_search", Asset.property_name, Asset.address),
        ]

        for index in indexes:
            try:
                index.create(self.db.bind)
                logger.info(f"Created index: {index.name}")
            except Exception as e:
                logger.warning(f"Failed to create index {index.name}: {e}")

    def analyze_slow_queries(self) -> dict[str, Any]:
        """分析慢查询"""
        stats = performance_monitor.get_stats()

        slow_queries = []
        for query_name, query_stats in stats["query_stats"].items():
            if query_stats["avg_duration_ms"] > 200:  # 超过200ms的查询
                slow_queries.append(
                    {
                        "query_name": query_name,
                        "avg_duration_ms": query_stats["avg_duration_ms"],
                        "max_duration_ms": query_stats["max_duration_ms"],
                        "count": query_stats["count"],
                        "slow_queries": query_stats["slow_queries"],
                    }
                )

        return {
            "total_slow_queries": stats["total_slow_queries"],
            "slow_queries": sorted(
                slow_queries, key=lambda x: x["avg_duration_ms"], reverse=True
            ),
            "recommendations": self._generate_recommendations(slow_queries),
        }

    def _generate_recommendations(self, slow_queries: list[dict]) -> list[str]:
        """生成优化建议"""
        recommendations = []

        for query in slow_queries:
            query_name = query["query_name"]

            if "batch_update" in query_name and query["avg_duration_ms"] > 500:
                recommendations.append(
                    f"考虑优化批量更新操作: {query_name} (平均耗时: {query['avg_duration_ms']:.2f}ms)"
                )

            if "list" in query_name and query["avg_duration_ms"] > 300:
                recommendations.append(
                    f"考虑为列表查询添加分页和索引: {query_name} (平均耗时: {query['avg_duration_ms']:.2f}ms)"
                )

            if "statistics" in query_name and query["avg_duration_ms"] > 200:
                recommendations.append(
                    f"考虑缓存统计查询结果: {query_name} (平均耗时: {query['avg_duration_ms']:.2f}ms)"
                )

        if not recommendations:
            recommendations.append("查询性能良好，无需优化")

        return recommendations


# 便捷函数
def get_performance_stats() -> dict[str, Any]:
    """获取性能统计"""
    return performance_monitor.get_stats()


def reset_performance_stats():
    """重置性能统计"""
    performance_monitor.reset_stats()


def get_cache_stats() -> dict[str, Any]:
    """获取缓存统计"""
    try:
        return cache_manager.get_stats()
    except AttributeError:
        # 如果cache_manager没有get_stats方法，返回基本信息
        return {
            "backend_type": "CacheManager",
            "status": "active",
            "message": "缓存统计信息（基础版本）",
            "timestamp": datetime.now(UTC).isoformat(),
            "note": "使用临时实现"
        }


def clear_cache():
    """清空缓存"""
    cache_manager.clear()


if __name__ == "__main__":
    # 测试性能监控
    @monitor_query("test_query")
    def test_function():
        time.sleep(0.1)  # 模拟慢查询
        return {"result": "test"}

    result = test_function()
    print("Test result:", result)
    print("Performance stats:", get_performance_stats())
    print("Cache stats:", get_cache_stats())
