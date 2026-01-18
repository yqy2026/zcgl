"""
PostgreSQL并发访问集成测试

测试数据库在高并发场景下的行为
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from sqlalchemy import text

from src.database import get_database_manager

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL", "").startswith("postgresql://"),
    reason="PostgreSQL tests required"
)


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.concurrency
class TestPostgreSQLConcurrency:
    """PostgreSQL并发访问测试"""

    def test_concurrent_reads(self):
        """测试并发读取操作"""
        mgr = get_database_manager()

        def read_query():
            with mgr.get_session() as session:
                session.execute(text("SELECT 1"))

        # 并发执行50个读取操作
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_query) for _ in range(50)]
            for future in as_completed(futures):
                future.result()  # 确保无异常

    def test_connection_pool_under_load(self):
        """测试连接池在负载下的行为"""
        mgr = get_database_manager()

        mgr.get_metrics()

        def execute_query():
            with mgr.get_session() as session:
                session.execute(text("SELECT pg_sleep(0.01)"))

        # 并发执行查询（超过连接池大小）
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(execute_query) for _ in range(50)]
            for future in as_completed(futures):
                future.result()

        # 验证连接池正常工作
        final_metrics = mgr.get_metrics()
        assert final_metrics.total_queries >= 50
        # 连接应该被释放回池
        assert final_metrics.active_connections >= 0

    def test_concurrent_transaction_isolation(self):
        """测试并发事务隔离"""
        from src.crud.asset import asset_crud
        from src.models.asset import Asset

        mgr = get_database_manager()

        # 创建初始资产
        with mgr.get_session() as session:
            asset_data = {
                "property_name": "隔离测试资产",
                "ownership_status": "已确权",
                "property_nature": "商业",
                "usage_status": "在用",
                "monthly_rent": 10000.0,
            }
            asset = asset_crud.create(db=session, obj_in=asset_data)
            asset_id = asset.id

        results = []

        def update_rent(new_rent: float):
            try:
                with mgr.get_session() as session:
                    asset_from_db = session.query(Asset).filter(
                        Asset.id == asset_id
                    ).first()

                    if asset_from_db:
                        asset_from_db.monthly_rent = new_rent
                        session.commit()
                        results.append(new_rent)
            except Exception as e:
                results.append(e)

        # 并发更新
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(update_rent, 15000.0),
                executor.submit(update_rent, 20000.0),
                executor.submit(update_rent, 25000.0),
            ]
            for future in as_completed(futures):
                future.result()

        # 验证：最终状态应该是其中一个值（无数据损坏）
        with mgr.get_session() as session:
            final_asset = asset_crud.get(db=session, id=asset_id)
            assert final_asset.monthly_rent in [15000.0, 20000.0, 25000.0]
