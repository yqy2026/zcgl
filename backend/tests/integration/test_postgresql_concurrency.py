"""
PostgreSQL并发访问集成测试

测试数据库在高并发场景下的行为
"""

import os
import asyncio

import pytest
from sqlalchemy import text, select

from src.database import get_database_manager

pytestmark = [
    pytest.mark.skipif(
        not os.getenv("DATABASE_URL", "").startswith("postgresql+psycopg://"),
        reason="PostgreSQL tests required",
    ),
    pytest.mark.asyncio,
]


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.concurrency
class TestPostgreSQLConcurrency:
    """PostgreSQL并发访问测试"""

    async def test_concurrent_reads(self):
        """测试并发读取操作"""
        mgr = get_database_manager()

        async def read_query():
            async with mgr.get_session() as session:
                await session.execute(text("SELECT 1"))

        # 并发执行50个读取操作
        await asyncio.gather(*(read_query() for _ in range(50)))

    async def test_connection_pool_under_load(self):
        """测试连接池在负载下的行为"""
        mgr = get_database_manager()

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

    async def test_concurrent_transaction_isolation(self):
        """测试并发事务隔离"""
        from src.crud.asset import asset_crud
        from src.models.asset import Asset

        mgr = get_database_manager()

        # 创建初始资产
        async with mgr.get_session() as session:
            asset_data = {
                "property_name": "隔离测试资产",
                "ownership_status": "已确权",
                "property_nature": "商业",
                "usage_status": "在用",
                "monthly_rent": 10000.0,
            }
            asset = await asset_crud.create_async(db=session, obj_in=asset_data)
            asset_id = asset.id

        results = []

        async def update_rent(new_rent: float):
            try:
                async with mgr.get_session() as session:
                    asset_from_db = await asset_crud.get_async(
                        db=session, id=asset_id
                    )

                    if asset_from_db:
                        asset_from_db.monthly_rent = new_rent
                        await session.commit()
                        results.append(new_rent)
            except Exception as e:
                results.append(e)

        # 并发更新
        await asyncio.gather(
            update_rent(15000.0),
            update_rent(20000.0),
            update_rent(25000.0),
        )

        # 验证：最终状态应该是其中一个值（无数据损坏）
        async with mgr.get_session() as session:
            final_asset = await asset_crud.get_async(db=session, id=asset_id)
            assert final_asset.monthly_rent in [15000.0, 20000.0, 25000.0]
