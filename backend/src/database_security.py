"""
数据库安全增强模块
"""

import sqlite3

from sqlalchemy import event
from sqlalchemy.engine import Engine

from .core.config import settings


def enhance_sqlite_security(engine: Engine):
    """增强SQLite数据库安全"""

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()

            # 启用外键约束
            cursor.execute("PRAGMA foreign_keys=ON")

            # 设置WAL模式以提高并发性能
            cursor.execute("PRAGMA journal_mode=WAL")

            # 启用同步以确保数据完整性
            cursor.execute("PRAGMA synchronous=NORMAL")

            # 设置缓存大小
            cursor.execute("PRAGMA cache_size=10000")

            # 启用自动清理
            cursor.execute("PRAGMA auto_vacuum=FULL")

            cursor.close()


def enhance_database_security(engine: Engine):
    """增强数据库安全配置"""
    if "sqlite" in settings.DATABASE_URL.lower():
        enhance_sqlite_security(engine)
    # 可以在这里添加其他数据库的安全增强配置
    # 例如PostgreSQL、MySQL等
