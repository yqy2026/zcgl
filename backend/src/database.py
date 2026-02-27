"""
数据库配置和连接管理
统一数据库服务，整合连接池、性能监控和健康检查功能
"""

import importlib
import logging
import threading
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from queue import Empty, Queue

from sqlalchemy import event, text
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import declarative_base

from src.constants.message_constants import ErrorIDs
from src.constants.storage_constants import DatabasePoolConfig

from .core.config import settings
from .core.exception_handler import (
    BaseBusinessError,
    ConfigurationError,
    InternalServerError,
    ServiceUnavailableError,
)
from .database_url import get_async_database_url as resolve_async_database_url
from .database_url import get_database_url as resolve_database_url

logger = logging.getLogger(__name__)


async def _handle_session_exception(session: AsyncSession, error: Exception) -> None:
    """Rollback session and log only unexpected infrastructure exceptions."""
    await session.rollback()
    if isinstance(error, BaseBusinessError):
        return

    logger.critical(
        "数据库会话异常",
        exc_info=True,
        extra={
            "error_id": ErrorIDs.Database.SESSION_ERROR,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "session_id": id(session),
        },
    )


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

    pool_size: int = DatabasePoolConfig.SIZE_DEFAULT
    max_overflow: int = DatabasePoolConfig.MAX_OVERFLOW
    pool_timeout: int = DatabasePoolConfig.TIMEOUT_SECONDS
    pool_recycle: int = DatabasePoolConfig.RECYCLE_SECONDS
    pool_pre_ping: bool = DatabasePoolConfig.PRE_PING_ENABLED
    echo: bool = DatabasePoolConfig.ECHO_ENABLED
    connect_args: dict[str, object] = field(default_factory=dict)


class DatabaseManager:
    """统一的数据库管理器，整合增强功能"""

    def __init__(self) -> None:
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None
        self.config: ConnectionPoolConfig = self._load_config()
        self.metrics: DatabaseMetrics = DatabaseMetrics()
        self.query_history: Queue[dict[str, object]] = Queue(
            maxsize=DatabasePoolConfig.QUERY_HISTORY_QUEUE_SIZE
        )
        self._metrics_lock = threading.Lock()
        self.slow_query_threshold = DatabasePoolConfig.SLOW_QUERY_THRESHOLD_MS
        self.enable_query_logging = DatabasePoolConfig.ENABLE_QUERY_LOGGING

    def _load_config(self) -> ConnectionPoolConfig:
        """加载数据库配置"""
        return ConnectionPoolConfig(
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_timeout=settings.DATABASE_POOL_TIMEOUT,
            pool_recycle=settings.DATABASE_POOL_RECYCLE,
            pool_pre_ping=settings.DATABASE_POOL_PRE_PING,
            echo=settings.DATABASE_ECHO,
            connect_args={},
        )

    def initialize_engine(self, database_url: str) -> AsyncEngine:
        """初始化数据库引擎"""
        logger.info(f"正在初始化数据库引擎: {database_url}")

        async_url = database_url
        if database_url.startswith("postgresql+psycopg://"):
            async_url = database_url.replace(
                "postgresql+psycopg://", "postgresql+asyncpg://", 1
            )

        engine_kwargs: dict[str, object] = {
            "echo": self.config.echo,
            "future": True,
            "pool_size": self.config.pool_size,
            "max_overflow": self.config.max_overflow,
            "pool_timeout": self.config.pool_timeout,
            "pool_recycle": self.config.pool_recycle,
            "pool_pre_ping": self.config.pool_pre_ping,
            "connect_args": self.config.connect_args,
        }

        try:
            self.engine = create_async_engine(async_url, **engine_kwargs)

            # 设置事件监听器
            self._setup_event_listeners()

            # 创建会话工厂
            self.session_factory = async_sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )

            logger.info("数据库引擎初始化完成")
            return self.engine

        except OperationalError as e:
            # ✅ 改进错误消息 - 解析错误字符串以提供具体提示
            error_str = str(e).lower()

            # 根据错误类型提供具体建议
            if "connection refused" in error_str:
                hint = "PostgreSQL服务未运行或端口配置错误"
                suggestion = (
                    "请检查: 1) PostgreSQL服务是否启动 2) DATABASE_URL中的端口是否正确"
                )
            elif "authentication failed" in error_str or "password" in error_str:
                hint = "数据库密码错误或用户不存在"
                suggestion = "请检查: 1) DATABASE_URL中的用户名和密码 2) 数据库用户是否存在 3) 用户密码是否正确"
            elif "database" in error_str and "does not exist" in error_str:
                hint = "数据库不存在"
                suggestion = (
                    "请先创建数据库: python scripts/setup_postgresql.py 或 createdb命令"
                )
            elif "timeout" in error_str:
                hint = "连接超时"
                suggestion = "请检查: 1) 网络连接 2) 防火墙设置 3) PostgreSQL服务器负载"
            elif (
                "no such host" in error_str
                or "could not translate host name" in error_str
            ):
                hint = "主机名无法解析"
                suggestion = "请检查DATABASE_URL中的主机名是否正确，DNS是否可解析"
            else:
                hint = "数据库连接失败"
                suggestion = "请检查PostgreSQL是否运行，且DATABASE_URL配置正确"

            # 解析DATABASE_URL以获取安全信息（不含密码）
            try:
                from urllib.parse import urlparse

                parsed = urlparse(database_url)
                safe_url = f"{parsed.scheme}://{parsed.username}@{parsed.hostname}:{parsed.port or 5432}{parsed.path}"
            except Exception:
                safe_url = (
                    database_url.split("@")[-1] if "@" in database_url else database_url
                )

            logger.critical(
                "无法连接到PostgreSQL数据库",
                extra={
                    "error_id": ErrorIDs.Database.CONNECTION_FAILED,
                    "database": safe_url,
                    "error_details": str(e),
                    "hint": hint,
                },
            )
            raise ServiceUnavailableError(
                message=(
                    "数据库连接失败\n"
                    f"  连接目标: {safe_url}\n"
                    f"  错误原因: {hint}\n"
                    f"  原始错误: {e}\n"
                    "  解决建议:\n"
                    f"    {suggestion}\n"
                    "  帮助文档: docs/POSTGRESQL_MIGRATION.md"
                ),
                service_name="PostgreSQL",
                details={
                    "error_id": ErrorIDs.Database.CONNECTION_FAILED,
                    "database": safe_url,
                    "hint": hint,
                },
            ) from e

        except (ValueError, AttributeError) as e:
            logger.critical(
                "DATABASE_URL配置错误",
                extra={
                    "error_id": ErrorIDs.Database.URL_MALFORMED,
                    "error_details": str(e),
                },
            )
            raise ConfigurationError(
                f"DATABASE_URL格式错误: {database_url}\n"
                f"正确格式: postgresql+psycopg://user:password@host:port/database\n"
                f"错误详情: {e}",
                config_key="DATABASE_URL",
            ) from e

    def _setup_event_listeners(self) -> None:
        """设置数据库事件监听器"""
        if not self.engine:  # pragma: no cover
            return  # pragma: no cover

        sync_engine = self.engine.sync_engine

        @event.listens_for(sync_engine, "connect")
        def on_connect(
            dbapi_connection: DBAPIConnection, connection_record: object
        ) -> None:
            """连接事件"""
            with self._metrics_lock:
                self.metrics.active_connections += 1
                self.metrics.last_activity = datetime.now()

        @event.listens_for(sync_engine, "checkout")
        def on_checkout(
            dbapi_connection: DBAPIConnection,
            connection_record: object,
            connection_proxy: object,
        ) -> None:
            """检出连接事件"""
            with self._metrics_lock:
                record_info = getattr(connection_record, "info", None)
                if isinstance(record_info, dict):  # pragma: no cover
                    if record_info.get("origin", "") == "pool":  # pragma: no cover
                        self.metrics.pool_hits += 1  # pragma: no cover
                    else:  # pragma: no cover
                        self.metrics.pool_misses += 1  # pragma: no cover

        @event.listens_for(sync_engine, "before_execute")
        def on_execute(
            conn: object,
            clauseelement: object,
            multiparams: object,
            params: object,
            execution_options: object,
        ) -> None:
            """执行查询事件"""
            conn_info = getattr(conn, "info", None)
            if isinstance(conn_info, dict):
                conn_info.setdefault("query_start_time", time.time())

        @event.listens_for(sync_engine, "after_execute")
        def after_execute(
            conn: object,
            clauseelement: object,
            multiparams: object,
            params: object,
            execution_options: object,
            result: object,
        ) -> None:
            """查询执行后事件"""
            try:
                conn_info = getattr(conn, "info", None)
                if not isinstance(conn_info, dict):
                    return

                raw_start_time = conn_info.pop("query_start_time", time.time())
                start_time = (
                    float(raw_start_time)
                    if isinstance(raw_start_time, (int, float))
                    else time.time()
                )
                execution_time = (time.time() - start_time) * 1000  # ms

                with self._metrics_lock:
                    self.metrics.total_queries += 1
                    self.metrics.total_response_time += execution_time
                    self.metrics.avg_response_time = (
                        self.metrics.total_response_time / self.metrics.total_queries
                    )
                    if execution_time > self.slow_query_threshold:  # pragma: no cover
                        self.metrics.slow_queries += 1  # pragma: no cover
                    self.metrics.last_activity = datetime.now()

                if self.enable_query_logging:  # pragma: no cover
                    query_info = {  # pragma: no cover
                        "query": str(clauseelement),  # pragma: no cover
                        "execution_time_ms": execution_time,  # pragma: no cover
                        "timestamp": datetime.now(),  # pragma: no cover
                        "params": params,  # pragma: no cover
                    }  # pragma: no cover
                    try:  # pragma: no cover
                        self.query_history.put_nowait(query_info)  # pragma: no cover
                    except Exception:  # pragma: no cover
                        try:  # pragma: no cover
                            self.query_history.get_nowait()  # pragma: no cover
                            self.query_history.put_nowait(
                                query_info
                            )  # pragma: no cover
                        except Empty:  # pragma: no cover
                            pass  # pragma: no cover
            except Exception as e:  # pragma: no cover
                logger.error(f"记录查询指标时出错: {e}")  # pragma: no cover

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话"""
        if not self.session_factory:
            raise InternalServerError("数据库引擎未初始化")

        async with self.session_factory() as session:
            try:
                yield session
            except Exception as e:
                await _handle_session_exception(session, e)
                raise

    async def dispose(self) -> None:
        """释放数据库引擎并清理会话工厂。"""
        engine = self.engine
        self.engine = None
        self.session_factory = None
        if engine is not None:
            await engine.dispose()

    def get_metrics(self) -> DatabaseMetrics:
        """获取数据库性能指标"""
        with self._metrics_lock:
            return DatabaseMetrics(**self.metrics.__dict__)

    async def run_health_check(self) -> dict[str, object]:
        """运行数据库健康检查"""
        health_status: dict[str, object] = {
            "healthy": True,
            "checks": {},
            "timestamp": datetime.now().isoformat(),
            "metrics": self.get_metrics().__dict__,
        }

        try:
            async with self.get_session() as session:
                start_time = time.time()
                await session.execute(text("SELECT 1"))
                response_time = (time.time() - start_time) * 1000

                checks = health_status["checks"]
                if isinstance(checks, dict):
                    checks["basic_connection"] = {
                        "status": "healthy" if response_time < 1000 else "degraded",
                        "response_time_ms": response_time,
                    }
        except OperationalError as e:
            health_status["healthy"] = False
            checks = health_status["checks"]
            if isinstance(checks, dict):
                checks["connection_test"] = {
                    "status": "failed",
                    "error": "数据库连接失败",
                    "error_details": str(e),
                }
            logger.critical(
                f"数据库健康检查失败 - 连接错误: {e}",
                extra={
                    "error_id": ErrorIDs.Database.HEALTH_CHECK_FAILED,
                    "error_type": "OperationalError",
                    "severity": "CRITICAL",
                },
            )
            # ✅ 重新抛出异常以确保失败时的可见性
            # 注意：这是breaking change恢复。如果需要返回healthy=False，
            # 调用者应该捕获这个异常并返回适当的HTTP状态码
            raise

        except Exception as e:
            health_status["healthy"] = False
            checks = health_status["checks"]
            if isinstance(checks, dict):
                checks["connection_test"] = {
                    "status": "failed",
                    "error": "未知数据库错误",
                    "error_details": str(e),
                }
            logger.critical(
                f"数据库健康检查失败 - 未知错误: {e}",
                exc_info=True,
                extra={
                    "error_id": ErrorIDs.Database.HEALTH_CHECK_UNKNOWN_ERROR,
                    "severity": "CRITICAL",
                },
            )
            # ✅ 重新抛出异常以确保失败时的可见性
            raise

        return health_status


# 数据库URL配置 - 保持向后兼容的模块级入口
def get_database_url() -> str:
    """获取数据库URL（支持动态环境变量）"""
    return resolve_database_url()


def get_async_database_url() -> str:
    """获取异步数据库URL"""
    return resolve_async_database_url()


# 向后兼容的模块级变量（现在通过函数获取）
DATABASE_URL = get_database_url()

# 全局数据库管理器实例（延迟初始化）
_database_manager: DatabaseManager | None = None


def _get_database_manager() -> DatabaseManager:
    """获取数据库管理器实例（延迟初始化）"""
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager()
        # 动态获取数据库URL，支持测试模式
        _database_manager.initialize_engine(get_database_url())
    return _database_manager


async def reset_database_manager() -> None:
    """Dispose and clear the global database manager instance."""
    global _database_manager
    manager = _database_manager
    _database_manager = None
    if manager is None:
        return

    try:
        await manager.dispose()
    except Exception as exc:  # pragma: no cover - best-effort cleanup
        logger.warning(
            "数据库管理器释放失败: %s",
            exc,
            exc_info=True,
        )


# 创建基础模型类
Base: DeclarativeMeta = declarative_base()


def get_database_manager() -> DatabaseManager:
    """获取数据库管理器（用于高级功能）"""
    return _get_database_manager()


def get_database_engine() -> AsyncEngine:
    """获取异步数据库引擎"""
    db_manager = _get_database_manager()
    if db_manager.engine is None:
        raise InternalServerError("Database engine is not initialized")
    return db_manager.engine


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    db_manager = _get_database_manager()
    session_factory = db_manager.session_factory
    if session_factory is None:
        raise InternalServerError("Async database session factory is not initialized")
    async with session_factory() as session:
        try:
            yield session
        except Exception as e:  # pragma: no cover
            await _handle_session_exception(session, e)  # pragma: no cover
            raise  # pragma: no cover


@asynccontextmanager
async def async_session_scope() -> AsyncGenerator[AsyncSession, None]:
    """获取异步数据库会话（非依赖场景的上下文管理器）"""
    db_manager = _get_database_manager()
    session_factory = db_manager.session_factory
    if session_factory is None:
        raise InternalServerError("Async database session factory is not initialized")
    async with session_factory() as session:
        try:
            yield session
        except Exception as e:  # pragma: no cover
            await _handle_session_exception(session, e)  # pragma: no cover
            raise  # pragma: no cover


async def create_tables() -> None:
    """创建所有数据库表"""
    db_manager = _get_database_manager()
    if db_manager.engine is None:
        raise InternalServerError("Database engine is not initialized")
    _ = importlib.import_module("src.models")
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表创建完成")


async def drop_tables() -> None:
    """删除所有数据库表"""
    db_manager = _get_database_manager()
    if db_manager.engine is None:
        raise InternalServerError("Database engine is not initialized")
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def get_database_status() -> dict[str, object]:
    """获取数据库状态信息"""
    manager = _get_database_manager()
    status = {
        "database_url": DATABASE_URL,
        "engine_type": type(manager.engine).__name__ if manager.engine else "Unknown",
        "metrics": manager.get_metrics().__dict__,
        "health_check": await manager.run_health_check(),
    }
    return status


async def init_db() -> None:
    """初始化数据库"""
    await create_tables()
    logger.info("数据库初始化完成")


if __name__ == "__main__":
    import asyncio

    asyncio.run(init_db())
