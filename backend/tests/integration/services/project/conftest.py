"""
Project Service 测试配置
使用简化的数据库设置，避免alembic迁移冲突
"""

import os

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

# 设置测试数据库URL为 PostgreSQL
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    pytest.skip(
        "TEST_DATABASE_URL is required for integration tests", allow_module_level=True
    )
if not TEST_DATABASE_URL.startswith("postgresql"):
    raise RuntimeError("测试必须使用 PostgreSQL")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from src import database as database
from src.database import Base


@pytest.fixture(scope="session")
def test_database_url():
    """覆盖root conftest的数据库URL"""
    return TEST_DATABASE_URL


@pytest.fixture(scope="function")
async def db_session(test_database_url):
    """创建异步数据库会话，并在测试结束后回滚事务。"""
    async_database_url = database.get_async_database_url()
    async_engine = create_async_engine(
        async_database_url,
        echo=False,
        poolclass=NullPool,
    )
    async with async_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with async_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
            await async_engine.dispose()
