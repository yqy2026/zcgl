"""
PostgreSQL数据库设置脚本
创建zcgl_db和zcgl_test数据库
"""
import getpass
import logging
import os
import sys
from urllib.parse import urlparse

import psycopg
from psycopg import sql

# ✅ 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_config_from_env() -> dict:
    """从环境变量读取数据库配置"""
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        # 从DATABASE_URL解析连接信息
        parsed = urlparse(database_url)
        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 5432,
            "user": parsed.username or "postgres",
            "password": parsed.password or get_password_interactive(),
            "dbname": parsed.path.lstrip("/") or "postgres"
        }
    else:
        # 从单独的环境变量读取
        return {
            "host": os.getenv("PGHOST", "localhost"),
            "port": int(os.getenv("PGPORT", "5432")),
            "user": os.getenv("PGUSER", "postgres"),
            "password": os.getenv("PGPASSWORD") or get_password_interactive(),
            "dbname": os.getenv("PGDATABASE", "postgres")
        }

def get_password_interactive() -> str:
    """交互式获取密码"""
    password = getpass.getpass("请输入PostgreSQL密码 (用户: postgres): ")
    if not password:
        raise ValueError("密码不能为空")
    return password

# PostgreSQL连接配置（从环境变量读取）
DB_CONFIG = get_db_config_from_env()

def create_database(db_name: str) -> bool:
    """创建数据库（如果不存在）"""
    try:
        # 连接到PostgreSQL
        conn = psycopg.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()

        # 检查数据库是否已存在
        cursor.execute(
            sql.SQL("SELECT 1 FROM pg_database WHERE datname = {}").format(
                sql.Literal(db_name)
            )
        )
        exists = cursor.fetchone()

        if exists:
            logger.info(f"Database '{db_name}' already exists")
        else:
            # 创建数据库
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(db_name)
                )
            )
            logger.info(f"Successfully created database '{db_name}'")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        logger.error(f"Failed to create database '{db_name}': {e}")
        return False

def verify_connection(db_name: str) -> bool:
    """验证数据库连接"""
    try:
        config = DB_CONFIG.copy()
        config["dbname"] = db_name

        conn = psycopg.connect(**config)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        logger.info(f"Successfully connected to database '{db_name}'")
        logger.debug(f"  Version: {version.split(',')[0]}")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        logger.error(f"Failed to connect to database '{db_name}': {e}")
        return False

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("PostgreSQL Database Setup")
    logger.info("=" * 60)

    # 创建数据库
    databases = ["zcgl_db", "zcgl_test"]
    for db in databases:
        if not create_database(db):
            logger.error(f"Database creation failed: {db}")
            sys.exit(1)

    logger.info("=" * 60)
    logger.info("Verifying Database Connections")
    logger.info("=" * 60)

    # 验证连接
    for db in databases:
        if not verify_connection(db):
            logger.error(f"Database connection failed: {db}")
            sys.exit(1)

    logger.info("=" * 60)
    logger.info("[SUCCESS] All databases created and verified!")
    logger.info("=" * 60)
