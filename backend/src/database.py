"""
数据库配置和连接管理 - 集成增强的数据库管理器
"""

import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

try:
    from .config_manager import get_config
    from .database_security import enhance_database_security
except ImportError:
    # 回退方案，当作为模块导入失败时

    from database_security import enhance_database_security

logger = logging.getLogger(__name__)

# 数据库URL配置
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/land_property.db")

# 尝试导入增强数据库管理器
try:
    from .enhanced_database import get_database_manager, initialize_enhanced_database
    ENHANCED_DB_AVAILABLE = True
except ImportError:
    logger.warning("Enhanced database manager not available, falling back to basic configuration")
    ENHANCED_DB_AVAILABLE = False

# 创建基础数据库引擎（作为回退）
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
    if "sqlite" in DATABASE_URL.lower()
    else {},
)

# 增强数据库安全
enhance_database_security(engine)

# 创建会话工厂（基础版本）
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()

# 全局变量，用于存储增强的数据库管理器状态
_database_manager_initialized = False


def initialize_enhanced_database_if_available():
    """如果可用，初始化增强的数据库管理器"""
    global _database_manager_initialized

    if ENHANCED_DB_AVAILABLE and not _database_manager_initialized:
        try:
            db_manager = get_database_manager()
            enhanced_engine = initialize_enhanced_database(DATABASE_URL)

            # 更新全局引擎和会话工厂
            global engine, SessionLocal
            engine = enhanced_engine
            SessionLocal = db_manager.session_factory

            _database_manager_initialized = True
            logger.info("Enhanced database manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize enhanced database manager: {e}")
            logger.info("Falling back to basic database configuration")


def get_db():
    """获取数据库会话 - 优先使用增强版本"""
    if ENHANCED_DB_AVAILABLE and _database_manager_initialized:
        try:
            from .enhanced_database import get_enhanced_db_session
            yield from get_enhanced_db_session()
            return
        except Exception as e:
            logger.warning(f"Enhanced database session failed, falling back: {e}")

    # 回退到基础会话
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
        "engine_type": type(engine).__name__
    }

    if ENHANCED_DB_AVAILABLE and _database_manager_initialized:
        try:
            db_manager = get_database_manager()
            metrics = db_manager.get_metrics()
            pool_status = db_manager.get_connection_pool_status()

            status.update({
                "enhanced_metrics": metrics.__dict__,
                "pool_status": pool_status,
                "health_check": db_manager.run_health_check()
            })
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
