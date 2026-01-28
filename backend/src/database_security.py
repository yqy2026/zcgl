"""
数据库安全增强模块
"""

import logging
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def enhance_database_security(engine: Engine) -> None:
    """
    增强数据库安全配置

    说明:
        SQLite 已移除。PostgreSQL 相关安全设置应在数据库层配置，
        如需在应用层补充，可在此处扩展。
    """
    logger.debug("Database security enhancements are handled by PostgreSQL configuration.")
    _ = engine
