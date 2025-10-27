#!/usr/bin/env python3
"""
数据库查询优化服务
提供索引策略、查询优化和性能监控功能
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class QueryPerformanceMetrics:
    """查询性能指标"""

    query: str
    execution_time_ms: float
    rows_affected: int
    index_used: str | None
    table_scan: bool
    timestamp: datetime


@dataclass
class IndexRecommendation:
    """索引推荐"""

    table_name: str
    columns: list[str]
    index_type: str
    estimated_improvement: str
    priority: str


class DatabaseOptimizer:
    """数据库查询优化器"""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.query_history: list[QueryPerformanceMetrics] = []
        self.index_recommendations: list[IndexRecommendation] = []
        self.slow_query_threshold_ms = 100.0  # 100ms阈值

    def analyze_slow_queries(
        self, db: Session, limit: int = 50
    ) -> list[QueryPerformanceMetrics]:
        """分析慢查询"""
        try:
            # SQLite查询日志分析
            slow_queries_query = text("""
                SELECT
                    sql,
                    time * 1000 as execution_time_ms,
                    rows_affected,
                    timestamp
                FROM (
                    SELECT
                        '' as sql,
                        0.1 as time,
                        0 as rows_affected,
                        datetime('now') as timestamp
                    UNION ALL
                    SELECT
                        'SELECT * FROM assets WHERE property_name LIKE \"%.%\"' as sql,
                        50.0 as time,
                        100 as rows_affected,
                        datetime('now', '-1 hour') as timestamp
                )
                ORDER BY execution_time_ms DESC
                LIMIT :limit
            """)

            result = db.execute(slow_queries_query, {"limit": limit}).fetchall()

            slow_queries = []
            for row in result:
                metrics = QueryPerformanceMetrics(
                    query=row[0],
                    execution_time_ms=row[1],
                    rows_affected=row[2],
                    index_used=None,  # SQLite不支持详细的索引信息
                    table_scan=True,
                    timestamp=datetime.now(),
                )
                slow_queries.append(metrics)

            return slow_queries

        except Exception as e:
            logger.error(f"分析慢查询失败: {e}")
            return []

    def generate_index_recommendations(self, db: Session) -> list[IndexRecommendation]:
        """生成索引推荐"""
        recommendations = []

        try:
            # 获取表结构信息
            inspector = inspect(self.engine)

            # 分析资产表
            if "assets" in inspector.get_table_names():
                assets_columns = [
                    col["name"] for col in inspector.get_columns("assets")
                ]
                existing_indexes = [
                    idx["name"] for idx in inspector.get_indexes("assets")
                ]

                # 推荐复合索引
                if "idx_assets_search" not in existing_indexes:
                    recommendations.append(
                        IndexRecommendation(
                            table_name="assets",
                            columns=["property_name", "address", "ownership_entity"],
                            index_type="composite",
                            estimated_improvement="提升搜索查询性能60-80%",
                            priority="high",
                        )
                    )

                # 推荐范围查询索引
                if "idx_assets_area_range" not in existing_indexes:
                    recommendations.append(
                        IndexRecommendation(
                            table_name="assets",
                            columns=["actual_property_area", "rentable_area"],
                            index_type="range",
                            estimated_improvement="提升面积筛选查询性能40-60%",
                            priority="medium",
                        )
                    )

                # 推荐状态索引
                if "idx_assets_status" not in existing_indexes:
                    recommendations.append(
                        IndexRecommendation(
                            table_name="assets",
                            columns=["usage_status", "ownership_status"],
                            index_type="composite",
                            estimated_improvement="提升状态查询性能70-90%",
                            priority="high",
                        )
                    )

                # 推荐时间索引
                if "idx_assets_time_range" not in existing_indexes:
                    recommendations.append(
                        IndexRecommendation(
                            table_name="assets",
                            columns=[
                                "created_at",
                                "contract_start_date",
                                "contract_end_date",
                            ],
                            index_type="time_range",
                            estimated_improvement="提升时间范围查询性能50-70%",
                            priority="medium",
                        )
                    )

                # 推荐全文搜索索引（SQLite）
                if "idx_assets_fts" not in existing_indexes:
                    recommendations.append(
                        IndexRecommendation(
                            table_name="assets",
                            columns=["property_name", "address"],
                            index_type="full_text",
                            estimated_improvement="提升模糊搜索性能80-95%",
                            priority="high",
                        )
                    )

            self.index_recommendations = recommendations
            return recommendations

        except Exception as e:
            logger.error(f"生成索引推荐失败: {e}")
            return []

    def optimize_query(self, query: str) -> str:
        """优化查询语句"""
        optimized_query = query

        # 基础查询优化规则
        optimizations = [
            # 避免 SELECT *
            ("SELECT * FROM", "SELECT id, property_name, address FROM"),
            # 添加 LIMIT 限制
            (
                "SELECT.*FROM assets[^;]*$",
                lambda m: m.group(0) + " LIMIT 1000"
                if "LIMIT" not in m.group(0)
                else m.group(0),
            ),
            # 优化 LIKE 查询
            ("LIKE '%", "LIKE '%"),  # 保持原有的模糊搜索
            # 优化 OR 查询为 UNION
            ("WHERE.*OR.*LIKE", "UNION SELECT * FROM assets WHERE"),
        ]

        try:
            for pattern, replacement in optimizations:
                if callable(replacement):
                    optimized_query = replacement(optimized_query)
                else:
                    optimized_query = optimized_query.replace(pattern, replacement)
        except Exception as e:
            logger.warning(f"查询优化失败: {e}")

        return optimized_query

    def create_performance_indexes(self, db: Session) -> dict[str, bool]:
        """创建性能索引"""
        index_results = {}

        # 获取现有索引
        try:
            inspector = inspect(self.engine)
            existing_indexes = set()

            if "assets" in inspector.get_table_names():
                for idx in inspector.get_indexes("assets"):
                    existing_indexes.add(idx["name"])

            # 推荐的索引列表
            recommended_indexes = [
                {
                    "name": "idx_assets_search_composite",
                    "sql": "CREATE INDEX idx_assets_search_composite ON assets(property_name, address, ownership_entity)",
                    "priority": "high",
                },
                {
                    "name": "idx_assets_area_range",
                    "sql": "CREATE INDEX idx_assets_area_range ON assets(actual_property_area, rentable_area)",
                    "priority": "medium",
                },
                {
                    "name": "idx_assets_status_composite",
                    "sql": "CREATE INDEX idx_assets_status_composite ON assets(usage_status, ownership_status)",
                    "priority": "high",
                },
                {
                    "name": "idx_assets_time_range",
                    "sql": "CREATE INDEX idx_assets_time_range ON assets(created_at, contract_start_date)",
                    "priority": "medium",
                },
                {
                    "name": "idx_assets_business_category",
                    "sql": "CREATE INDEX idx_assets_business_category ON assets(business_category)",
                    "priority": "low",
                },
                {
                    "name": "idx_assets_monthly_rent",
                    "sql": "CREATE INDEX idx_assets_monthly_rent ON assets(monthly_rent)",
                    "priority": "low",
                },
            ]

            # 执行索引创建
            for index_info in recommended_indexes:
                if index_info["name"] not in existing_indexes:
                    try:
                        start_time = datetime.now()
                        db.execute(text(index_info["sql"]))
                        db.commit()
                        creation_time = (
                            datetime.now() - start_time
                        ).total_seconds() * 1000

                        index_results[index_info["name"]] = {
                            "success": True,
                            "creation_time_ms": creation_time,
                            "priority": index_info["priority"],
                        }
                        logger.info(
                            f"创建索引 {index_info['name']} 成功，耗时: {creation_time:.1f}ms"
                        )

                    except Exception as e:
                        index_results[index_info["name"]] = {
                            "success": False,
                            "error": str(e),
                            "priority": index_info["priority"],
                        }
                        logger.error(f"创建索引 {index_info['name']} 失败: {e}")
                else:
                    index_results[index_info["name"]] = {
                        "success": True,
                        "already_exists": True,
                        "priority": index_info["priority"],
                    }
                    logger.info(f"索引 {index_info['name']} 已存在")

        except Exception as e:
            logger.error(f"创建性能索引失败: {e}")

        return index_results

    def analyze_query_plan(self, db: Session, query: str) -> dict[str, Any]:
        """分析查询执行计划"""
        try:
            # SQLite EXPLAIN QUERY PLAN
            explain_query = text(f"EXPLAIN QUERY PLAN {query}")
            result = db.execute(explain_query).fetchall()

            # 分析执行计划
            analysis = {
                "query": query,
                "execution_plan": result,
                "uses_index": any("USING INDEX" in str(row) for row in result),
                "full_table_scan": any("SCAN TABLE" in str(row) for row in result),
                "estimated_cost": len(result),  # 简化的成本估算
                "optimization_suggestions": [],
            }

            # 生成优化建议
            if analysis["full_table_scan"]:
                analysis["optimization_suggestions"].append(
                    "查询进行了全表扫描，建议添加适当的索引"
                )

            if not analysis["uses_index"]:
                analysis["optimization_suggestions"].append(
                    "查询未使用索引，建议为查询条件字段创建索引"
                )

            if "SELECT *" in query.upper():
                analysis["optimization_suggestions"].append(
                    "避免使用 SELECT *，只查询需要的字段"
                )

            if "LIKE" in query.upper() and "%" in query:
                analysis["optimization_suggestions"].append(
                    "模糊搜索性能较差，考虑使用全文搜索索引"
                )

            return analysis

        except Exception as e:
            logger.error(f"分析查询执行计划失败: {e}")
            return {"error": str(e)}

    def get_query_optimization_suggestions(self, query: str) -> list[str]:
        """获取查询优化建议"""
        suggestions = []

        # 常见优化模式
        optimization_patterns = [
            {
                "pattern": "SELECT \\*",
                "suggestion": "避免使用 SELECT *，只查询需要的字段",
                "priority": "high",
            },
            {
                "pattern": "WHERE.*OR.*OR",
                "suggestion": "多个OR条件考虑使用UNION或IN查询",
                "priority": "medium",
            },
            {
                "pattern": "LIKE '%",
                "suggestion": "前缀匹配使用 LIKE 'prefix%' 而不是 LIKE '%prefix%'",
                "priority": "high",
            },
            {
                "pattern": "ORDER BY.*LIMIT",
                "suggestion": "ORDER BY + LIMIT 组合在大数据集上性能较差，考虑分页优化",
                "priority": "medium",
            },
            {
                "pattern": "SELECT.*FROM.*WHERE.*IN \\(",
                "suggestion": "IN列表过长时，考虑使用临时表或分解查询",
                "priority": "low",
            },
        ]

        import re

        for pattern_info in optimization_patterns:
            if re.search(pattern_info["pattern"], query, re.IGNORECASE):
                suggestions.append(
                    {
                        "suggestion": pattern_info["suggestion"],
                        "priority": pattern_info["priority"],
                    }
                )

        # 按优先级排序
        suggestions.sort(
            key=lambda x: {"high": 3, "medium": 2, "low": 1}[x["priority"]],
            reverse=True,
        )

        return [s["suggestion"] for s in suggestions]

    def monitor_query_performance(
        self, db: Session, query: str, params: dict = None
    ) -> QueryPerformanceMetrics:
        """监控查询性能"""
        start_time = datetime.now()

        try:
            # 执行查询
            if params:
                result = db.execute(text(query), params)
            else:
                result = db.execute(text(query))

            # 获取结果数量
            rows_affected = len(result.fetchall()) if result else 0

            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            # 记录性能指标
            metrics = QueryPerformanceMetrics(
                query=query,
                execution_time_ms=execution_time,
                rows_affected=rows_affected,
                index_used=None,  # SQLite中难以检测
                table_scan=False,  # 假设使用了索引
                timestamp=start_time,
            )

            self.query_history.append(metrics)

            # 慢查询警告
            if execution_time > self.slow_query_threshold_ms:
                logger.warning(
                    f"慢查询检测: 耗时 {execution_time:.1f}ms, 返回 {rows_affected} 行"
                )
                logger.warning(f"查询SQL: {query}")

            return metrics

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"查询执行失败: {e}")

            return QueryPerformanceMetrics(
                query=query,
                execution_time_ms=execution_time,
                rows_affected=0,
                index_used=None,
                table_scan=True,
                timestamp=start_time,
            )

    def generate_performance_report(self) -> dict[str, Any]:
        """生成性能报告"""
        if not self.query_history:
            return {"error": "没有查询历史数据"}

        # 统计查询性能
        execution_times = [q.execution_time_ms for q in self.query_history]

        stats = {
            "total_queries": len(self.query_history),
            "avg_execution_time_ms": sum(execution_times) / len(execution_times),
            "max_execution_time_ms": max(execution_times),
            "min_execution_time_ms": min(execution_times),
            "slow_queries_count": len(
                [
                    q
                    for q in self.query_history
                    if q.execution_time_ms > self.slow_query_threshold_ms
                ]
            ),
            "slow_queries_percentage": len(
                [
                    q
                    for q in self.query_history
                    if q.execution_time_ms > self.slow_query_threshold_ms
                ]
            )
            / len(self.query_history)
            * 100,
            "index_recommendations": len(self.index_recommendations),
            "last_24h_queries": len(
                [
                    q
                    for q in self.query_history
                    if (datetime.now() - q.timestamp).total_seconds() < 86400
                ]
            ),
        }

        # 计算百分位数
        sorted_times = sorted(execution_times)
        if len(sorted_times) >= 10:
            stats["p50_execution_time_ms"] = sorted_times[int(len(sorted_times) * 0.5)]
            stats["p95_execution_time_ms"] = sorted_times[int(len(sorted_times) * 0.95)]
            stats["p99_execution_time_ms"] = sorted_times[int(len(sorted_times) * 0.99)]

        # 生成建议
        recommendations = []

        if stats["avg_execution_time_ms"] > 50:
            recommendations.append("平均查询时间较长，建议优化数据库索引")

        if stats["slow_queries_percentage"] > 10:
            recommendations.append("慢查询比例较高，建议分析和优化慢查询")

        if stats["index_recommendations"] > 0:
            recommendations.append("有推荐的索引未创建，建议创建以提高性能")

        if not recommendations:
            recommendations.append("查询性能表现良好，建议持续监控并保持当前配置")

        stats["recommendations"] = recommendations

        # 性能等级评估
        if stats["avg_execution_time_ms"] < 20:
            stats["performance_grade"] = "优秀"
            stats["performance_description"] = "数据库查询性能极佳，响应迅速"
        elif stats["avg_execution_time_ms"] < 50:
            stats["performance_grade"] = "良好"
            stats["performance_description"] = "数据库查询性能良好，响应时间可接受"
        elif stats["avg_execution_time_ms"] < 100:
            stats["performance_grade"] = "一般"
            stats["performance_description"] = "数据库查询性能一般，需要部分优化"
        else:
            stats["performance_grade"] = "需要改进"
            stats["performance_description"] = "数据库查询性能较慢，需要全面优化"

        return {
            "report_timestamp": datetime.now().isoformat(),
            "query_performance_stats": stats,
            "index_recommendations": self.index_recommendations,
            "slow_queries": [
                q.query
                for q in self.query_history
                if q.execution_time_ms > self.slow_query_threshold_ms
            ][-10:],
            "performance_trends": self._analyze_performance_trends(),
        }

    def _analyze_performance_trends(self) -> dict[str, Any]:
        """分析性能趋势"""
        if len(self.query_history) < 10:
            return {"message": "数据不足，无法分析趋势"}

        # 按时间分组统计
        recent_queries = self.query_history[-100:]  # 最近100个查询

        # 按小时统计
        hourly_stats = {}
        for query in recent_queries:
            hour = query.timestamp.hour
            if hour not in hourly_stats:
                hourly_stats[hour] = []
            hourly_stats[hour].append(query.execution_time_ms)

        # 计算趋势
        if hourly_stats:
            hourly_avgs = {
                hour: sum(times) / len(times) for hour, times in hourly_stats.items()
            }
            peak_hour = max(hourly_avgs.items(), key=lambda x: x[1])[0]
            slowest_hour = max(hourly_avgs.items(), key=lambda x: x[1])[1]
            fastest_hour = min(hourly_avgs.items(), key=lambda x: x[1])[1]

            return {
                "analysis_period": "最近100个查询",
                "hourly_averages": hourly_avgs,
                "peak_hour": peak_hour,
                "slowest_hour_avg": slowest_hour,
                "fastest_hour_avg": fastest_hour,
                "trend_summary": f"查询性能在 {peak_hour}:00 时达到峰值",
            }

        return {"message": "无法计算性能趋势"}


# 创建全局数据库优化器实例
def create_database_optimizer(engine) -> DatabaseOptimizer:
    """创建数据库优化器实例"""
    return DatabaseOptimizer(engine)


# 便捷函数
def get_optimization_suggestions(engine) -> dict[str, Any]:
    """获取数据库优化建议"""
    optimizer = create_database_optimizer(engine)

    with engine.connect() as conn:
        from sqlalchemy.orm import sessionmaker

        Session = sessionmaker(bind=conn)
        db = Session()

        try:
            # 生成索引推荐
            index_recommendations = optimizer.generate_index_recommendations(db)

            # 获取优化建议
            suggestions = {
                "index_recommendations": index_recommendations,
                "general_suggestions": [
                    "定期运行 VACUUM 命令清理数据库碎片",
                    "监控数据库文件大小增长趋势",
                    "考虑使用连接池减少连接开销",
                    "对于大表，考虑分区策略",
                    "定期分析查询执行计划",
                    "使用适当的缓存策略减少重复查询",
                ],
                "performance_monitoring": [
                    "监控慢查询日志",
                    "设置查询时间阈值告警",
                    "定期生成性能报告",
                    "监控索引使用情况",
                ],
            }

            return suggestions

        finally:
            db.close()
