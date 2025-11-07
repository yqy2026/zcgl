"""
数据库配置和连接管理 - 集成增强的数据库管理器
"""

import logging
import os
from typing import TYPE_CHECKING, Callable, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

if TYPE_CHECKING:
    from sqlalchemy.orm.session import sessionmaker as SessionMaker

try:
    from .database_security import enhance_database_security
except ImportError:
    # 回退方案，当作为模块导入失败时
    try:
        from database_security import enhance_database_security
    except ImportError:
        # 进一步回退，创建空函数
        def enhance_database_security(engine):
            pass


logger = logging.getLogger(__name__)

# 数据库URL配置
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/land_property.db")

# 确保SQLite数据目录存在
if "sqlite" in DATABASE_URL.lower():
    db_path = DATABASE_URL.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Created database directory: {db_dir}")

# 数据库连接配置
if "sqlite" in DATABASE_URL.lower():
    # SQLite 配置
    engine_kwargs = {
        "connect_args": {"check_same_thread": False}
    }
else:
    # PostgreSQL/MySQL 配置
    engine_kwargs = {
        "pool_size": 10,              # 连接池大小
        "max_overflow": 20,           # 最大溢出连接
        "pool_pre_ping": True,        # 连接健康检查
        "pool_recycle": 3600,         # 连接回收时间(秒)
        "echo": False,                # 生产环境关闭 SQL 输出
    }

# 尝试导入增强数据库管理器
try:
    from .core.enhanced_database import (
        get_database_manager,
        get_enhanced_db_session,
        initialize_enhanced_database,
    )

    ENHANCED_DB_AVAILABLE = True
except ImportError:
    logger.warning(
        "Enhanced database manager not available, falling back to basic configuration"
    )
    ENHANCED_DB_AVAILABLE = False
    # 提供类型安全的回退函数
    get_database_manager = None  # type: ignore
    get_enhanced_db_session = None  # type: ignore
    initialize_enhanced_database = None  # type: ignore

# 创建基础数据库引擎（作为回退）
engine = create_engine(DATABASE_URL, **engine_kwargs)

# 增强数据库安全
enhance_database_security(engine)

# 创建会话工厂（基础版本）
SessionLocal: Callable[[], Session] = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)

# 创建基础模型类
Base = declarative_base()

# 全局变量，用于存储增强的数据库管理器状态
_database_manager_initialized = False


def initialize_enhanced_database_if_available():
    """如果可用，初始化增强的数据库管理器"""
    global _database_manager_initialized

    if ENHANCED_DB_AVAILABLE and not _database_manager_initialized:
        try:
            if get_database_manager is None or initialize_enhanced_database is None:
                logger.warning("Enhanced database functions not available")
                return

            db_manager = get_database_manager()
            enhanced_engine = initialize_enhanced_database(DATABASE_URL)

            # 更新全局引擎和会话工厂
            global engine, SessionLocal
            engine = enhanced_engine
            if db_manager.session_factory is not None:
                SessionLocal = db_manager.session_factory  # type: ignore[assignment]

            _database_manager_initialized = True
            logger.info("Enhanced database manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize enhanced database manager: {e}")
            logger.info("Falling back to basic database configuration")


def get_db():
    """获取数据库会话 - 优先使用增强版本"""
    db = None
    try:
        if ENHANCED_DB_AVAILABLE and _database_manager_initialized:
            try:
                if get_enhanced_db_session is not None:
                    yield from get_enhanced_db_session()
                    return
            except Exception as e:
                logger.warning(f"Enhanced database session failed, falling back: {e}")

        # 回退到基础会话
        db = SessionLocal()
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        raise
    finally:
        if db is not None:
            try:
                db.close()
            except Exception as e:
                logger.error(f"Error closing database session: {e}")


def create_tables():
    """创建所有数据库表"""
    if ENHANCED_DB_AVAILABLE and _database_manager_initialized:
        try:
            # 使用增强引擎创建表
            Base.metadata.create_all(bind=engine)
            logger.info("Tables created using enhanced database engine")
            return
        except Exception as e:
            logger.warning(f"Enhanced table creation failed, falling back: {e}")

    # 使用基础引擎创建表
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created using basic database engine")


def get_database_engine():
    """获取当前数据库引擎"""
    return engine


def get_session_factory():
    """获取当前会话工厂"""
    return SessionLocal


def is_enhanced_database_active():
    """检查增强数据库管理器是否处于活跃状态"""
    return ENHANCED_DB_AVAILABLE and _database_manager_initialized


def get_database_status():
    """获取数据库状态信息"""
    status = {
        "enhanced_available": ENHANCED_DB_AVAILABLE,
        "enhanced_active": _database_manager_initialized,
        "database_url": DATABASE_URL,
        "engine_type": type(engine).__name__,
    }

    if ENHANCED_DB_AVAILABLE and _database_manager_initialized:
        try:
            if get_database_manager is not None:
                db_manager = get_database_manager()
                metrics = db_manager.get_metrics()
                pool_status = db_manager.get_connection_pool_status()

                status.update(
                    {
                        "enhanced_metrics": metrics.__dict__,
                        "pool_status": pool_status,
                        "health_check": db_manager.run_health_check(),
                    }
                )
        except Exception as e:
            status["enhanced_error"] = str(e)

    return status


def drop_tables():
    """删除所有数据库表"""
    Base.metadata.drop_all(bind=engine)


def init_db():
    """初始化数据库"""
    create_tables()
    print("数据库初始化完成")


if __name__ == "__main__":
    init_db()
