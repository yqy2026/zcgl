"""
SystemDictionary Service 测试配置
使用简化的数据库设置，避免alembic迁移冲突
"""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 设置测试数据库URL为 PostgreSQL
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    pytest.skip("TEST_DATABASE_URL is required for integration tests", allow_module_level=True)
if not TEST_DATABASE_URL.startswith("postgresql"):
    raise RuntimeError("测试必须使用 PostgreSQL")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from src.database import Base


@pytest.fixture(scope="session")
def test_database_url():
    """覆盖root conftest的数据库URL"""
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
def engine(test_database_url):
    """创建内存数据库引擎，不使用alembic迁移"""
    engine = create_engine(test_database_url, pool_pre_ping=True)
    # 直接创建所有表，跳过alembic迁移
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db_tables(engine):
    """覆盖root conftest的db_tables fixture，跳过迁移"""
    yield
    # 空实现，表已经在engine fixture中创建


@pytest.fixture(scope="function")
def db_session(engine):
    """创建数据库会话"""
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_local()

    # 开始事务
    connection = engine.connect()
    transaction = connection.begin()
    session.bind = connection

    yield session

    # 回滚事务
    try:
        session.close()
        transaction.rollback()
        connection.close()
    except Exception:
        pass
