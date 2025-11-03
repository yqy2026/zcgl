from typing import Any
"""
性能优化服务
"""

import logging
import time
from functools import wraps


from sqlalchemy import and_, asc, desc, func, or_, text
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql import Select

from models.asset import Asset, AssetHistory
from schemas.asset import AssetSearchParams

logger = logging.getLogger(__name__)


def performance_monitor(func):
    """性能监控装饰器"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            if execution_time > 1.0:  # 超过1秒的查询记录警告
                logger.warning(
                    f"Slow query detected: {func.__name__} took {execution_time:.2f}s"
                )
            else:
                logger.info(
                    f"Query performance: {func.__name__} took {execution_time:.3f}s"
                )

            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Query failed: {func.__name__} took {execution_time:.3f}s, error: {str(e)}"
            )
            raise

    return wrapper


class PerformanceService:
    """性能优化服务"""

    def __init__(self, db: Session):
        self.db = db

    @performance_monitor
    def get_assets_optimized(
        self, params: AssetSearchParams, page: int = 1, limit: int = 20
    ) -> tuple[list[Asset], int]:
        """
        优化的资产查询方法
        使用索引,预加载和查询优化
        """
        # 构建基础查询
        query = self.db.query(Asset)

        # 应用筛选条件(利用索引)
        query = self._apply_filters_optimized(query, params)

        # 获取总数(使用优化的计数查询)
        total = self._get_count_optimized(query)

        # 应用排序（利用索引）
        query = self._apply_sorting_optimized(query, params)

        # 应用分页
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        # 预加载关联数据(避免N+1查询)
        if params.include_history:
            query = query.options(selectinload(Asset.history))

        if params.include_documents:
            query = query.options(selectinload(Asset.documents))

        # 执行查询
        assets = query.all()

        return assets, total

    def _apply_filters_optimized(
        self, query: Select, params: AssetSearchParams
    ) -> Select:
        """应用优化的筛选条件"""
        conditions = []

        # 文本搜索(SQLite使用LIKE搜索)
        if params.search:
            search_term = f"%{params.search}%"
            search_condition = or_(
                Asset.property_name.ilike(search_term),
                Asset.ownership_entity.ilike(search_term),
                Asset.address.ilike(search_term),
                Asset.actual_usage.ilike(search_term),
                Asset.business_category.ilike(search_term),
                Asset.tenant_name.ilike(search_term),
                Asset.description.ilike(search_term),
            )
            conditions.append(search_condition)

        # 精确匹配筛选(利用索引)
        if params.ownership_status:
            conditions.append(Asset.ownership_status == params.ownership_status)

        if params.property_nature:
            conditions.append(Asset.property_nature == params.property_nature)

        if params.usage_status:
            conditions.append(Asset.usage_status == params.usage_status)

        if params.ownership_entity:
            conditions.append(Asset.ownership_entity == params.ownership_entity)

        if params.is_litigated is not None:
            conditions.append(Asset.is_litigated == str(params.is_litigated))

        # 范围筛选
        if params.area_min is not None:
            conditions.append(Asset.actual_property_area >= params.area_min)

        if params.area_max is not None:
            conditions.append(Asset.actual_property_area <= params.area_max)

        # 日期范围筛选(利用索引)
        if params.created_start:
            conditions.append(Asset.created_at >= params.created_start)

        if params.created_end:
            conditions.append(Asset.created_at <= params.created_end)

        # 应用所有条件
        if conditions:
            query = query.filter(and_(*conditions))

        return query

    def _get_count_optimized(self, query: Select) -> int:
        """优化的计数查询"""
        # 使用子查询避免加载所有数据
        count_query = query.statement.with_only_columns([func.count(Asset.id)])
        return self.db.execute(count_query).scalar()

    def _apply_sorting_optimized(
        self, query: Select, params: AssetSearchParams
    ) -> Select:
        """应用优化的排序(利用索引)"""
        sort_field = params.sort_field or "created_at"
        sort_order = params.sort_order or "desc"

        # 定义可排序字段(确保有索引)
        sortable_fields = {
            "created_at": Asset.created_at,
            "updated_at": Asset.updated_at,
            "property_name": Asset.property_name,
            "ownership_entity": Asset.ownership_entity,
            "actual_property_area": Asset.actual_property_area,
            "rentable_area": Asset.rentable_area,
        }

        if sort_field in sortable_fields:
            field = sortable_fields[sort_field]
            if sort_order == "desc":
                query = query.order_by(desc(field))
            else:
                query = query.order_by(asc(field))

        return query

    @performance_monitor
    def get_asset_statistics_optimized(self) -> dict[str, Any]:
        """优化的统计查询"""
        # 使用聚合查询一次性获取所有统计数据
        stats = self.db.query(
            func.count(Asset.id).label("total_count"),
            func.sum(Asset.actual_property_area).label("total_area"),
            func.avg(Asset.actual_property_area).label("avg_area"),
            func.sum(Asset.rentable_area).label("total_rentable_area"),
            func.sum(Asset.rented_area).label("total_rented_area"),
        ).first()

        # 按性质分组统计
        nature_stats = (
            self.db.query(
                Asset.property_nature,
                func.count(Asset.id).label("count"),
                func.sum(Asset.actual_property_area).label("total_area"),
            )
            .group_by(Asset.property_nature)
            .all()
        )

        # 按状态分组统计
        status_stats = (
            self.db.query(Asset.usage_status, func.count(Asset.id).label("count"))
            .group_by(Asset.usage_status)
            .all()
        )

        # 按确权状态分组统计
        ownership_stats = (
            self.db.query(Asset.ownership_status, func.count(Asset.id).label("count"))
            .group_by(Asset.ownership_status)
            .all()
        )

        return {
            "total_count": stats.total_count or 0,
            "total_area": float(stats.total_area or 0),
            "avg_area": float(stats.avg_area or 0),
            "total_rentable_area": float(stats.total_rentable_area or 0),
            "total_rented_area": float(stats.total_rented_area or 0),
            "occupancy_rate": (
                (stats.total_rented_area / stats.total_rentable_area * 100)
                if stats.total_rentable_area
                else 0
            ),
            "by_nature": [
                {
                    "nature": item.property_nature,
                    "count": item.count,
                    "total_area": float(item.total_area or 0),
                }
                for item in nature_stats
            ],
            "by_status": [
                {"status": item.usage_status, "count": item.count}
                for item in status_stats
            ],
            "by_ownership": [
                {"ownership_status": item.ownership_status, "count": item.count}
                for item in ownership_stats
            ],
        }

    @performance_monitor
    def get_asset_history_optimized(
        self, asset_id: str, page: int = 1, limit: int = 20
    ) -> tuple[list[AssetHistory], int]:
        """优化的历史记录查询"""
        # 使用索引查询
        query = (
            self.db.query(AssetHistory)
            .filter(AssetHistory.asset_id == asset_id)
            .order_by(desc(AssetHistory.changed_at))
        )

        # 获取总数
        total = query.count()

        # 分页
        offset = (page - 1) * limit
        history = query.offset(offset).limit(limit).all()

        return history, total

    @performance_monitor
    def search_assets_fulltext(self, search_term: str, limit: int = 10) -> list[Asset]:
        """全文搜索资产(SQLite版本)"""
        search_pattern = f"%{search_term}%"

        # 使用SQLite的LIKE搜索，按相关性排序
        query = (
            self.db.query(Asset)
            .filter(
                or_(
                    Asset.property_name.ilike(search_pattern),
                    Asset.ownership_entity.ilike(search_pattern),
                    Asset.address.ilike(search_pattern),
                    Asset.actual_usage.ilike(search_pattern),
                    Asset.business_category.ilike(search_pattern),
                    Asset.tenant_name.ilike(search_pattern),
                    Asset.description.ilike(search_pattern),
                )
            )
            .order_by(
                # 按物业名称匹配优先级排序
                Asset.property_name.ilike(search_pattern).desc(),
                Asset.ownership_entity.ilike(search_pattern).desc(),
                Asset.created_at.desc(),
            )
            .limit(limit)
        )

        return query.all()

    def analyze_query_performance(self, query_sql: str) -> dict[str, Any]:
        """分析查询性能"""
        try:
            # SQLite使用EXPLAIN QUERY PLAN
            explain_query = text(f"EXPLAIN QUERY PLAN {query_sql}")
            result = self.db.execute(explain_query)
            plan_rows = result.fetchall()

            return {
                "query_plan": [
                    {
                        "id": row[0],
                        "parent": row[1],
                        "notused": row[2],
                        "detail": row[3],
                    }
                    for row in plan_rows
                ],
                "analyzed_at": time.time(),
            }
        except Exception as e:
            logger.error(f"Query analysis failed: {str(e)}")
            return {"error": str(e)}

    def get_slow_queries(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取慢查询日志(需要配置PostgreSQL日志)"""
        # 这需要在PostgreSQL中启用慢查询日志
        # 这里返回模拟数据，实际实现需要读取PostgreSQL日志
        return [
            {
                "query": "SELECT * FROM assets WHERE ...",
                "duration": 2.5,
                "timestamp": "2024-01-01 10:00:00",
                "calls": 15,
            }
        ]

    def optimize_database(self) -> dict[str, Any]:
        """数据库优化建议"""
        results = {}

        try:
            # SQLite数据库优化
            # 1. 执行VACUUM清理数据库
            self.db.execute(text("VACUUM"))
            results["vacuum"] = "已执行VACUUM操作"

            # 2. 分析表统计信息
            self.db.execute(text("ANALYZE"))
            results["analyze"] = "已更新表统计信息"

            # 3. 获取表信息
            tables = self.db.execute(
                text("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            ).fetchall()

            table_info = []
            for table in tables:
                table_name = table[0]
                try:
                    count = self.db.execute(
                        text(f"SELECT COUNT(*) FROM {table_name}")
                    ).scalar()
                    table_info.append({"table": table_name, "row_count": count})
                except Exception as e:
                    logger.warning(f"无法获取表{table_name}的行数: {e}")

            results["table_info"] = table_info

            # 4. 获取索引信息
            indexes = self.db.execute(
                text("""
                SELECT name, sql FROM sqlite_master
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
            """)
            ).fetchall()

            results["indexes"] = [{"name": idx[0], "sql": idx[1]} for idx in indexes]

            # 5. 创建性能优化索引
            index_results = self.create_performance_indexes()
            results["index_creation"] = index_results

            self.db.commit()

        except Exception as e:
            logger.error(f"数据库优化失败: {e}")
            results["error"] = str(e)
            self.db.rollback()

        return results

    def create_performance_indexes(self) -> dict[str, Any]:
        """创建性能优化索引"""
        results = []

        try:
            # 检查表是否存在
            tables = self.db.execute(
                text("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name IN ('assets', 'asset_history', 'asset_documents')
            """)
            ).fetchall()

            table_names = [table[0] for table in tables]

            if "assets" in table_names:
                # 资产表索引
                indexes_to_create = [
                    ("idx_assets_property_name", "assets", "property_name"),
                    ("idx_assets_address", "assets", "address"),
                    ("idx_assets_ownership_entity", "assets", "ownership_entity"),
                    ("idx_assets_ownership_status", "assets", "ownership_status"),
                    ("idx_assets_property_nature", "assets", "property_nature"),
                    ("idx_assets_usage_status", "assets", "usage_status"),
                    ("idx_assets_business_category", "assets", "business_category"),
                    ("idx_assets_is_litigated", "assets", "is_litigated"),
                    (
                        "idx_assets_actual_property_area",
                        "assets",
                        "actual_property_area",
                    ),
                    ("idx_assets_created_at", "assets", "created_at"),
                    ("idx_assets_updated_at", "assets", "updated_at"),
                ]

                # 复合索引
                composite_indexes = [
                    (
                        "idx_assets_ownership_nature",
                        "assets",
                        "ownership_entity, property_nature",
                    ),
                    (
                        "idx_assets_status_nature",
                        "assets",
                        "usage_status, property_nature",
                    ),
                ]

                # 创建单列索引
                for index_name, table_name, column_name in indexes_to_create:
                    try:
                        self.db.execute(
                            text(f"""
                            CREATE INDEX IF NOT EXISTS {index_name}
                            ON {table_name} ({column_name})
                        """)
                        )
                        results.append(f"创建索引: {index_name}")
                    except Exception as e:
                        logger.warning(f"创建索引 {index_name} 失败: {e}")

                # 创建复合索引
                for index_name, table_name, columns in composite_indexes:
                    try:
                        self.db.execute(
                            text(f"""
                            CREATE INDEX IF NOT EXISTS {index_name}
                            ON {table_name} ({columns})
                        """)
                        )
                        results.append(f"创建复合索引: {index_name}")
                    except Exception as e:
                        logger.warning(f"创建复合索引 {index_name} 失败: {e}")

            if "asset_history" in table_names:
                # 历史记录表索引
                history_indexes = [
                    ("idx_asset_history_asset_id", "asset_history", "asset_id"),
                    ("idx_asset_history_changed_at", "asset_history", "changed_at"),
                    ("idx_asset_history_change_type", "asset_history", "change_type"),
                ]

                for index_name, table_name, column_name in history_indexes:
                    try:
                        self.db.execute(
                            text(f"""
                            CREATE INDEX IF NOT EXISTS {index_name}
                            ON {table_name} ({column_name})
                        """)
                        )
                        results.append(f"创建历史表索引: {index_name}")
                    except Exception as e:
                        logger.warning(f"创建历史表索引{index_name} 失败: {e}")

            if "asset_documents" in table_names:
                # 文档表索引
                document_indexes = [
                    ("idx_asset_documents_asset_id", "asset_documents", "asset_id"),
                    (
                        "idx_asset_documents_uploaded_at",
                        "asset_documents",
                        "uploaded_at",
                    ),
                ]

                for index_name, table_name, column_name in document_indexes:
                    try:
                        self.db.execute(
                            text(f"""
                            CREATE INDEX IF NOT EXISTS {index_name}
                            ON {table_name} ({column_name})
                        """)
                        )
                        results.append(f"创建文档表索引: {index_name}")
                    except Exception as e:
                        logger.warning(f"创建文档表索引{index_name} 失败: {e}")

            return {"created_indexes": results, "success": True}

        except Exception as e:
            logger.error(f"创建索引失败: {e}")
            return {"error": str(e), "success": False}
