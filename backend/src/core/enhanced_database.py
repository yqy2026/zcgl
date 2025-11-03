#!/usr/bin/env python3
from typing import Any
"""
增强的数据库连接管理模块
提供连接池、查询优化、性能监控和健康检查功能
"""

import logging
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from queue import Empty, Queue


from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

from .config_manager import get_config

logger = logging.getLogger(__name__)


@dataclass
class DatabaseMetrics:
    """数据库性能指标"""

    active_connections: int = 0
    total_queries: int = 0
    slow_queries: int = 0
    avg_response_time: float = 0.0
    total_response_time: float = 0.0
    connection_errors: int = 0
    last_activity: datetime | None = None
    pool_hits: int = 0
    pool_misses: int = 0


@dataclass
class ConnectionPoolConfig:
    """连接池配置"""

    pool_size: int = 20
    max_overflow: int = 30
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    echo: bool = False
    connect_args: dict[str, Any] = field(default_factory=dict)


class EnhancedDatabaseManager:
    """增强的数据库管理器"""

    def __init__(self):
        self.engine: Engine | None = None
        self.session_factory: sessionmaker | None = None
        self.config: ConnectionPoolConfig = self._load_config()
        self.metrics: DatabaseMetrics = DatabaseMetrics()
        self.query_history: Queue = Queue(maxsize=1000)
        self._metrics_lock = threading.Lock()
        self._pool_configured = False

        # 性能监控
        self.slow_query_threshold = 100.0  # ms
        self.enable_query_logging = get_config("database.enable_query_logging", False)

    def _load_config(self) -> ConnectionPoolConfig:
        """加载数据库配置"""
        return ConnectionPoolConfig(
            pool_size=get_config("database.pool_size", 20),
            max_overflow=get_config("database.max_overflow", 30),
            pool_timeout=get_config("database.pool_timeout", 30),
            pool_recycle=get_config("database.pool_recycle", 3600),
            pool_pre_ping=get_config("database.pool_pre_ping", True),
            echo=get_config("database.echo", False),
            connect_args={},
        )

    def initialize_engine(self, database_url: str) -> Engine:
        """初始化数据库引擎"""

        logger.info(f"正在初始化数据库引擎: {database_url}")

        # 创建引擎配置
        engine_kwargs = {
            "echo": self.config.echo,
            "future": True,
        }

        # 根据数据库类型配置连接池
        if "sqlite" in database_url.lower():
            engine_kwargs.update(
                {
                    "poolclass": StaticPool,
                    "connect_args": {
                        "check_same_thread": False,
                        "timeout": 20,
                        "isolation_level": None,
                    },
                }
            )
        else:
            engine_kwargs.update(
                {
                    "poolclass": QueuePool,
                    "pool_size": self.config.pool_size,
                    "max_overflow": self.config.max_overflow,
                    "pool_timeout": self.config.pool_timeout,
                    "pool_recycle": self.config.pool_recycle,
                    "pool_pre_ping": self.config.pool_pre_ping,
                    "connect_args": self.config.connect_args,
                }
            )

        # 创建引擎
        self.engine = create_engine(database_url, **engine_kwargs)

        # 设置事件监听器
        self._setup_event_listeners()

        # 创建会话工厂
        self.session_factory = sessionmaker(
            bind=self.engine, autocommit=False, autoflush=False, expire_on_commit=False
        )

        logger.info("数据库引擎初始化完成")
        return self.engine

    def _setup_event_listeners(self):
        """设置数据库事件监听器"""

        @event.listens_for(self.engine, "connect")
        def on_connect(dbapi_connection: DBAPIConnection, connection_record):
            """连接事件"""
            with self._metrics_lock:
                self.metrics.active_connections += 1
                self.metrics.last_activity = datetime.now()

                # 针对特定数据库类型的优化
                if self.engine and "sqlite" in str(self.engine.url).lower():
                    self._optimize_sqlite_connection(dbapi_connection)

        @event.listens_for(self.engine, "checkout")
        def on_checkout(
            dbapi_connection: DBAPIConnection, connection_record, connection_proxy
        ):
            """检出连接事件"""
            with self._metrics_lock:
                if connection_record and hasattr(connection_record, "info"):
                    if connection_record.info.get("origin", "") == "pool":
                        self.metrics.pool_hits += 1
                    else:
                        self.metrics.pool_misses += 1

        @event.listens_for(self.engine, "checkin")
        def on_checkin(dbapi_connection: DBAPIConnection, connection_record):
            """检入连接事件"""
            with self._metrics_lock:
                self.metrics.active_connections -= 1

        @event.listens_for(self.engine, "close")
        def on_close(dbapi_connection, connection_record):
            """关闭连接事件"""
            with self._metrics_lock:
                if self.metrics.active_connections > 0:
                    self.metrics.active_connections -= 1

        @event.listens_for(self.engine, "before_execute")
        def on_execute(conn, clauseelement, multiparams, params, execution_options):
            """执行查询事件"""
            conn.info.setdefault("query_start_time", time.time())

        @event.listens_for(self.engine, "after_execute")
        def after_execute(
            conn, clauseelement, multiparams, params, execution_options, result
        ):
            """查询执行后事件"""
            try:
                start_time = conn.info.pop("query_start_time", time.time())
                execution_time = (time.time() - start_time) * 1000  # ms

                # 更新指标
                with self._metrics_lock:
                    self.metrics.total_queries += 1
                    self.metrics.total_response_time += execution_time
                    self.metrics.avg_response_time = (
                        self.metrics.total_response_time / self.metrics.total_queries
                    )

                    if execution_time > self.slow_query_threshold:
                        self.metrics.slow_queries += 1

                    self.metrics.last_activity = datetime.now()

                # 记录查询历史
                if self.enable_query_logging:
                    query_info = {
                        "query": str(clauseelement),
                        "execution_time_ms": execution_time,
                        "timestamp": datetime.now(),
                        "params": params,
                    }

                    try:
                        self.query_history.put_nowait(query_info)
                    except:
                        # 如果队列满了，移除最旧的记录
                        try:
                            self.query_history.get_nowait()
                            self.query_history.put_nowait(query_info)
                        except Empty:
                            pass

            except Exception as e:
                logger.error(f"记录查询指标时出错: {e}")

    def _optimize_sqlite_connection(self, dbapi_connection):
        """优化SQLite连接"""
        cursor = dbapi_connection.cursor()
        try:
            # 启用外键约束
            cursor.execute("PRAGMA foreign_keys=ON")

            # 设置WAL模式以提高并发性能
            cursor.execute("PRAGMA journal_mode=WAL")

            # 优化同步模式
            cursor.execute("PRAGMA synchronous=NORMAL")

            # 增大缓存大小
            cursor.execute("PRAGMA cache_size=10000")

            # 启用内存临时存储
            cursor.execute("PRAGMA temp_store=MEMORY")

            # 优化查询计划器
            cursor.execute("PRAGMA optimize")

            # 设置WAL自动检查点
            cursor.execute("PRAGMA wal_autocheckpoint=1000")

            logger.debug("SQLite连接优化完成")

        except Exception as e:
            logger.error(f"优化SQLite连接时出错: {e}")
        finally:
            cursor.close()

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """获取数据库会话"""
        if not self.session_factory:
            raise RuntimeError("数据库引擎未初始化")

        session = self.session_factory()
        try:
            yield session
        except Exception as e:
            session.rollback()
            logger.error(f"数据库会话异常: {e}")
            raise
        finally:
            session.close()

    def get_engine(self) -> Engine:
        """获取数据库引擎"""
        if not self.engine:
            raise RuntimeError("数据库引擎未初始化")
        return self.engine

    def get_metrics(self) -> DatabaseMetrics:
        """获取数据库性能指标"""
        with self._metrics_lock:
            return DatabaseMetrics(**self.metrics.__dict__)

    def get_slow_queries(self, limit: int = 50) -> list[dict[str, Any]]:
        """获取慢查询列表"""
        slow_queries = []

        # 从查询历史中获取慢查询
        temp_queries = []
        try:
            # 获取所有查询
            while not self.query_history.empty():
                temp_queries.append(self.query_history.get_nowait())
        except Empty:
            pass

        # 筛选慢查询
        for query in temp_queries:
            if query["execution_time_ms"] > self.slow_query_threshold:
                slow_queries.append(query)

        # 按执行时间排序并限制数量
        slow_queries.sort(key=lambda x: x["execution_time_ms"], reverse=True)
        return slow_queries[:limit]

    def get_connection_pool_status(self) -> dict[str, Any]:
        """获取连接池状态"""
        if not self.engine or not self.engine.pool:
            return {"status": "未初始化"}

        pool = self.engine.pool

        # 检查是否为SQLite StaticPool
        if hasattr(pool, "size"):
            # 标准连接池（如MySQL/PostgreSQL）
            status = {
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid(),
                "pool_type": "QueuePool",
            }

            # 计算连接使用率
            if pool.size() > 0:
                status["utilization"] = (pool.checkedout() / pool.size()) * 100
            else:
                status["utilization"] = 0
        else:
            # SQLite StaticPool
            status = {
                "pool_size": 1,  # SQLite单连接
                "checked_in": 1,
                "checked_out": 0,
                "overflow": 0,
                "invalid": 0,
                "pool_type": "StaticPool",
                "utilization": 0,
            }

        # 添加指标信息
        metrics = self.get_metrics()
        status.update(
            {
                "active_connections": metrics.active_connections,
                "total_queries": metrics.total_queries,
                "slow_queries": metrics.slow_queries,
                "avg_response_time_ms": metrics.avg_response_time,
                "pool_hits": metrics.pool_hits,
                "pool_misses": metrics.pool_misses,
                "pool_hit_rate": (
                    metrics.pool_hits / (metrics.pool_hits + metrics.pool_misses) * 100
                    if (metrics.pool_hits + metrics.pool_misses) > 0
                    else 0
                ),
            }
        )

        return status

    def run_health_check(self) -> dict[str, Any]:
        """运行数据库健康检查"""
        health_status = {
            "healthy": True,
            "checks": {},
            "timestamp": datetime.now().isoformat(),
            "metrics": self.get_metrics().__dict__,
        }

        try:
            with self.get_session() as session:
                # 检查基本连接
                start_time = time.time()
                session.execute(text("SELECT 1"))
                response_time = (time.time() - start_time) * 1000

                health_status["checks"]["basic_connection"] = {
                    "status": "healthy" if response_time < 1000 else "degraded",
                    "response_time_ms": response_time,
                }

                # 检查表是否存在
                tables_query = text("""
                    SELECT name FROM sqlite_master
                    WHERE type='table'
                    ORDER BY name
                """)
                tables = [row[0] for row in session.execute(tables_query)]

                health_status["checks"]["table_access"] = {
                    "status": "healthy",
                    "table_count": len(tables),
                    "tables": tables[:10],  # 限制显示数量
                }

                # 检查数据库大小
                size_query = text(
                    "SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()"
                )
                try:
                    size_result = session.execute(size_query).fetchone()
                    if size_result:
                        db_size_bytes = size_result[0]
                        health_status["checks"]["database_size"] = {
                            "status": "healthy",
                            "size_bytes": db_size_bytes,
                            "size_mb": round(db_size_bytes / (1024 * 1024), 2),
                        }
                except:
                    health_status["checks"]["database_size"] = {
                        "status": "unknown",
                        "message": "无法获取数据库大小",
                    }

        except Exception as e:
            health_status["healthy"] = False
            health_status["checks"]["connection_test"] = {
                "status": "failed",
                "error": str(e),
            }
            logger.error(f"数据库健康检查失败: {e}")

        # 检查连接池状态
        pool_status = self.get_connection_pool_status()
        health_status["checks"]["connection_pool"] = pool_status

        # 检查是否有过多的慢查询
        metrics = self.get_metrics()
        if metrics.slow_queries > metrics.total_queries * 0.1:  # 超过10%的查询是慢查询
            health_status["checks"]["slow_queries"] = {
                "status": "warning",
                "slow_queries": metrics.slow_queries,
                "total_queries": metrics.total_queries,
                "slow_query_rate": round(
                    metrics.slow_queries / max(metrics.total_queries, 1) * 100, 2
                ),
            }
        else:
            health_status["checks"]["slow_queries"] = {
                "status": "healthy",
                "slow_queries": metrics.slow_queries,
                "total_queries": metrics.total_queries,
            }

        return health_status

    def cleanup_old_sessions(self, days: int = 7) -> int:
        """清理旧的会话数据"""
        if not self.engine:
            return 0

        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0

        try:
            with self.get_session() as session:
                # 清理旧的查询历史（如果存在查询历史表）
                try:
                    cleanup_query = text("""
                        DELETE FROM query_history
                        WHERE timestamp < :cutoff_date
                    """)
                    result = session.execute(
                        cleanup_query, {"cutoff_date": cutoff_date}
                    )
                    cleaned_count += result.rowcount
                    session.commit()
                except Exception:
                    # 如果查询历史表不存在，跳过
                    pass

                # SQLite数据库清理
                if self.engine and "sqlite" in str(self.engine.url).lower():
                    session.execute(text("VACUUM"))
                    session.commit()
                    cleaned_count += 1

                logger.info(f"清理了 {cleaned_count} 条旧数据")

        except Exception as e:
            logger.error(f"清理旧数据时出错: {e}")

        return cleaned_count

    def optimize_database(self) -> dict[str, Any]:
        """优化数据库性能"""
        optimization_results = {
            "timestamp": datetime.now().isoformat(),
            "actions_taken": [],
            "recommendations": [],
        }

        try:
            with self.get_session() as session:
                # 分析慢查询
                slow_queries = self.get_slow_queries(limit=10)
                if slow_queries:
                    optimization_results["actions_taken"].append(
                        f"分析了 {len(slow_queries)} 个慢查询"
                    )
                    optimization_results["recommendations"].append(
                        "考虑添加适当的索引来优化慢查询"
                    )

                # 更新统计信息
                if self.engine and "sqlite" in str(self.engine.url).lower():
                    session.execute(text("ANALYZE"))
                    session.commit()
                    optimization_results["actions_taken"].append("更新了SQLite统计信息")

                # 检查连接池使用情况
                pool_status = self.get_connection_pool_status()
                if pool_status.get("utilization", 0) > 80:
                    optimization_results["recommendations"].append(
                        "连接池使用率过高，考虑增加连接池大小"
                    )

                logger.info("数据库优化完成")

        except Exception as e:
            logger.error(f"数据库优化时出错: {e}")
            optimization_results["error"] = str(e)

        return optimization_results


# 全局数据库管理器实例
database_manager = EnhancedDatabaseManager()


def get_database_manager() -> EnhancedDatabaseManager:
    """获取数据库管理器实例"""
    return database_manager


def get_enhanced_db_session() -> Generator[Session, None, None]:
    """获取增强的数据库会话"""
    return database_manager.get_session()


# 为了向后兼容，保留原始的get_db函数
def get_db():
    """获取数据库会话（向后兼容）"""
    return get_enhanced_db_session()


def get_database_engine() -> Engine:
    """获取数据库引擎"""
    return database_manager.get_engine()


def initialize_enhanced_database(database_url: str) -> Engine:
    """初始化增强的数据库连接"""
    return database_manager.initialize_engine(database_url)
