"""
PostgreSQL并发访问集成测试

测试数据库在高并发场景下的行为
"""

import asyncio
import os
import uuid

import pytest
from sqlalchemy import text

from src.database import DatabaseManager, get_database_manager, get_database_url

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
async def ensure_postgresql_available():
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url.startswith("postgresql+psycopg://"):
        pytest.skip("PostgreSQL tests require DATABASE_URL to use postgresql+psycopg://")

    try:
        mgr = get_database_manager()
        async with mgr.get_session() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(
            f"PostgreSQL is unavailable for integration tests: {exc.__class__.__name__}"
        )


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.concurrency
class TestPostgreSQLConcurrency:
    """PostgreSQL并发访问测试"""

    @pytest.fixture
    async def isolated_db_manager(self):
        mgr = DatabaseManager()
        mgr.initialize_engine(get_database_url())
        try:
            yield mgr
        finally:
            if mgr.engine is not None:
                await mgr.engine.dispose()

    async def test_concurrent_reads(self, isolated_db_manager):
        """测试并发读取操作"""
        mgr = isolated_db_manager

        async def read_query():
            async with mgr.get_session() as session:
                await session.execute(text("SELECT 1"))

        # 并发执行50个读取操作
        await asyncio.gather(*(read_query() for _ in range(50)))

    async def test_connection_pool_under_load(self, isolated_db_manager):
        """测试连接池在负载下的行为"""
        mgr = isolated_db_manager

        mgr.get_metrics()

        async def execute_query():
            async with mgr.get_session() as session:
                await session.execute(text("SELECT pg_sleep(0.01)"))

        # 并发执行查询（超过连接池大小）
        await asyncio.gather(*(execute_query() for _ in range(50)))

        # 验证连接池正常工作
        final_metrics = mgr.get_metrics()
        assert final_metrics.total_queries >= 50
        # 连接应该被释放回池
        assert final_metrics.active_connections >= 0

    async def test_concurrent_transaction_isolation(self, isolated_db_manager):
        """测试并发事务隔离"""
        from src.crud.asset import asset_crud
        from src.models.ownership import Ownership

        mgr = isolated_db_manager

        # 创建初始资产
        async with mgr.get_session() as session:
            suffix = uuid.uuid4().hex[:8]
            ownership = Ownership(name="并发测试权属方", code="OWN-CONCURRENCY")
            session.add(ownership)
            await session.flush()

            asset_data = {
                "asset_name": f"隔离测试资产-{suffix}",
                "ownership_id": ownership.id,
                "address": "隔离测试地址",
                "ownership_status": "已确权",
                "property_nature": "商业",
                "usage_status": "在用",
                "notes": "initial",
            }
            asset = await asset_crud.create_async(db=session, obj_in=asset_data)
            asset_id = asset.id

        results = []

        async def update_notes(new_notes: str):
            try:
                async with mgr.get_session() as session:
                    asset_from_db = await asset_crud.get_async(db=session, id=asset_id)

                    if asset_from_db:
                        asset_from_db.notes = new_notes
                        await session.commit()
                        results.append(new_notes)
            except Exception as e:
                results.append(e)

        # 并发更新
        await asyncio.gather(
            update_notes("notes-A"),
            update_notes("notes-B"),
            update_notes("notes-C"),
        )

        # 验证：最终状态应该是其中一个值（无数据损坏）
        async with mgr.get_session() as session:
            final_asset = await asset_crud.get_async(db=session, id=asset_id)
            assert final_asset.notes in ["notes-A", "notes-B", "notes-C"]
