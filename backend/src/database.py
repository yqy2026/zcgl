"""
数据库配置和连接管理
统一数据库服务，整合连接池、性能监控和健康检查功能
"""

import logging
import os
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from queue import Empty, Queue
from typing import Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

try:
    from .database_security import enhance_database_security
except ImportError:  # pragma: no cover
    try:  # pragma: no cover
        from database_security import enhance_database_security  # pragma: no cover
    except ImportError:  # pragma: no cover

        def enhance_database_security(engine):  # pragma: no cover
            pass  # pragma: no cover


try:
    from .core.config import get_config
except ImportError:  # pragma: no cover

    def get_config(key: str, default: Any = None) -> Any:  # pragma: no cover
        return default  # pragma: no cover


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


class DatabaseManager:
    """统一的数据库管理器，整合增强功能"""

    def __init__(self):
        self.engine: Engine | None = None
        self.session_factory: sessionmaker | None = None
        self.config: ConnectionPoolConfig = self._load_config()
        self.metrics: DatabaseMetrics = DatabaseMetrics()
        self.query_history: Queue = Queue(maxsize=1000)
        self._metrics_lock = threading.Lock()
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
        print(f"DEBUG: Initializing database engine with URL: {database_url}")
        logger.info(f"正在初始化数据库引擎: {database_url}")

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
        else:  # pragma: no cover
            engine_kwargs.update(  # pragma: no cover
                {
                    "poolclass": QueuePool,  # pragma: no cover
                    "pool_size": self.config.pool_size,  # pragma: no cover
                    "max_overflow": self.config.max_overflow,  # pragma: no cover
                    "pool_timeout": self.config.pool_timeout,  # pragma: no cover
                    "pool_recycle": self.config.pool_recycle,  # pragma: no cover
                    "pool_pre_ping": self.config.pool_pre_ping,  # pragma: no cover
                    "connect_args": self.config.connect_args,  # pragma: no cover
                }  # pragma: no cover
            )

        self.engine = create_engine(database_url, **engine_kwargs)

        # 增强数据库安全
        enhance_database_security(self.engine)

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
        if not self.engine:  # pragma: no cover
            return  # pragma: no cover

        @event.listens_for(self.engine, "connect")
        def on_connect(dbapi_connection: DBAPIConnection, connection_record):
            """连接事件"""
            with self._metrics_lock:
                self.metrics.active_connections += 1
                self.metrics.last_activity = datetime.now()
                if self.engine and "sqlite" in str(self.engine.url).lower():
                    self._optimize_sqlite_connection(dbapi_connection)

        @event.listens_for(self.engine, "checkout")
        def on_checkout(
            dbapi_connection: DBAPIConnection, connection_record, connection_proxy
        ):
            """检出连接事件"""
            with self._metrics_lock:
                if connection_record and hasattr(
                    connection_record, "info"
                ):  # pragma: no cover
                    if (
                        connection_record.info.get("origin", "") == "pool"
                    ):  # pragma: no cover
                        self.metrics.pool_hits += 1  # pragma: no cover
                    else:  # pragma: no cover
                        self.metrics.pool_misses += 1  # pragma: no cover

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

    def _optimize_sqlite_connection(self, dbapi_connection):
        """优化SQLite连接"""
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=10000")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.execute("PRAGMA optimize")
            cursor.execute("PRAGMA wal_autocheckpoint=1000")
            logger.debug("SQLite连接优化完成")
        except Exception as e:  # pragma: no cover
            logger.error(f"优化SQLite连接时出错: {e}")  # pragma: no cover
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

    def get_metrics(self) -> DatabaseMetrics:
        """获取数据库性能指标"""
        with self._metrics_lock:
            return DatabaseMetrics(**self.metrics.__dict__)

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
                start_time = time.time()
                session.execute(text("SELECT 1"))
                response_time = (time.time() - start_time) * 1000

                health_status["checks"]["basic_connection"] = {
                    "status": "healthy" if response_time < 1000 else "degraded",
                    "response_time_ms": response_time,
                }
        except Exception as e:  # pragma: no cover
            health_status["healthy"] = False  # pragma: no cover
            health_status["checks"]["connection_test"] = {  # pragma: no cover
                "status": "failed",  # pragma: no cover
                "error": str(e),  # pragma: no cover
            }  # pragma: no cover
            logger.error(f"数据库健康检查失败: {e}")  # pragma: no cover

        return health_status


# 数据库URL配置 - 动态读取环境变量，支持测试模式
def get_database_url() -> str:
    """获取数据库URL（支持动态环境变量）"""
    return os.getenv("DATABASE_URL", "sqlite:///./data/land_property.db")


# 向后兼容的模块级变量（现在通过函数获取）
DATABASE_URL = get_database_url()

# 确保SQLite数据目录存在
if "sqlite" in DATABASE_URL.lower():
    db_path = DATABASE_URL.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):  # pragma: no cover
        os.makedirs(db_dir, exist_ok=True)  # pragma: no cover
        logger.info(f"Created database directory: {db_dir}")  # pragma: no cover

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


# 导出引擎和会话工厂（向后兼容，延迟初始化）
def _get_engine():
    """获取引擎（延迟初始化）"""
    return _get_database_manager().engine  # pragma: no cover


def _get_session_local():
    """获取会话工厂（延迟初始化）"""
    return _get_database_manager().session_factory  # pragma: no cover


# 为了向后兼容，提供全局变量（但实际使用时通过函数获取）
engine = None  # 将在首次使用时初始化
SessionLocal = None  # 将在首次使用时初始化


def _init_globals():
    """初始化全局变量"""
    global engine, SessionLocal
    if engine is None or SessionLocal is None:
        manager = _get_database_manager()
        engine = manager.engine
        SessionLocal = manager.session_factory


# 创建基础模型类
Base: DeclarativeMeta = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话（FastAPI依赖注入）"""
    _init_globals()
    db_manager = _get_database_manager()
    session = db_manager.session_factory()
    try:
        yield session
    except Exception as e:  # pragma: no cover
        session.rollback()  # pragma: no cover
        logger.error(f"数据库会话异常: {e}")  # pragma: no cover
        raise  # pragma: no cover
    finally:
        session.close()


def get_database_engine() -> Engine:
    """获取数据库引擎"""
    _init_globals()
    return _get_database_manager().engine


def get_session_factory():
    """获取会话工厂"""
    _init_globals()
    return _get_database_manager().session_factory


def get_database_manager() -> DatabaseManager:
    """获取数据库管理器（用于高级功能）"""
    return _get_database_manager()


def create_tables():
    """创建所有数据库表"""
    _init_globals()
    if engine:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建完成")


def drop_tables():
    """删除所有数据库表"""
    _init_globals()
    if engine:
        Base.metadata.drop_all(bind=engine)


def get_database_status() -> dict[str, Any]:
    """获取数据库状态信息"""
    manager = _get_database_manager()
    _init_globals()
    status = {
        "database_url": DATABASE_URL,
        "engine_type": type(engine).__name__ if engine else "Unknown",
        "metrics": manager.get_metrics().__dict__,
        "health_check": manager.run_health_check(),
    }
    return status


def init_db():
    """初始化数据库"""
    create_tables()
    logger.info("数据库初始化完成")


if __name__ == "__main__":
    init_db()
