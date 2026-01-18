"""
PostgreSQL数据库设置脚本
创建zcgl_db和zcgl_test数据库
"""

import sys

import psycopg
from psycopg import sql

# PostgreSQL连接配置
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "asdf",
    "dbname": "postgres",  # 连接到默认数据库
}


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
            print(f"[OK] Database '{db_name}' already exists")
        else:
            # 创建数据库
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name))
            )
            print(f"[OK] Successfully created database '{db_name}'")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"[FAIL] Failed to create database '{db_name}': {e}")
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
        print(f"[OK] Successfully connected to database '{db_name}'")
        print(f"  Version: {version.split(',')[0]}")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"[FAIL] Failed to connect to database '{db_name}': {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("PostgreSQL Database Setup")
    print("=" * 60)

    # 创建数据库
    databases = ["zcgl_db", "zcgl_test"]
    for db in databases:
        if not create_database(db):
            print(f"\n[ERROR] Database creation failed: {db}")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("Verifying Database Connections")
    print("=" * 60)

    # 验证连接
    for db in databases:
        if not verify_connection(db):
            print(f"\n[ERROR] Database connection failed: {db}")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("[SUCCESS] All databases created and verified!")
    print("=" * 60)
