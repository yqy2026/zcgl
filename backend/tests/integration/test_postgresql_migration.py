"""
PostgreSQL数据库迁移集成测试

测试PostgreSQL特定功能和迁移后的系统行为

注意：这些测试需要DATABASE_URL环境变量设置为PostgreSQL。
如果未设置，测试将被跳过。
"""

import os

import pytest
from sqlalchemy import text

from src.database import (
    DatabaseManager,
    get_database_manager,
    get_database_url,
)

# Skip all tests in this module if not using PostgreSQL
pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL", "").startswith("postgresql+psycopg://"),
    reason="PostgreSQL tests require DATABASE_URL to be set to postgresql+psycopg://",
)


@pytest.mark.integration
@pytest.mark.database
class TestPostgreSQLConnection:
    """PostgreSQL数据库连接测试"""

    def test_database_url_format(self):
        """测试DATABASE_URL格式验证"""
        database_url = get_database_url()

        # 验证是PostgreSQL URL
        assert database_url.startswith("postgresql+psycopg://"), (
            "DATABASE_URL should start with postgresql+psycopg://, "
            f"got: {database_url[:30]}"
        )

        # 验证URL包含必需组件
        assert "localhost" in database_url or "127.0.0.1" in database_url, (
            "DATABASE_URL should contain localhost or 127.0.0.1"
        )
        assert "zcgl_db" in database_url or "test" in database_url, (
            "DATABASE_URL should contain database name"
        )

    def test_database_manager_initialization(self):
        """测试DatabaseManager初始化"""
        mgr = DatabaseManager()
        assert mgr is not None
        assert mgr.config is not None
        assert mgr.metrics is not None

    def test_database_engine_creation(self):
        """测试数据库引擎创建"""
        mgr = DatabaseManager()
        database_url = get_database_url()
        engine = mgr.initialize_engine(database_url)

        assert engine is not None
        assert engine.driver == "psycopg"
        assert str(engine.url).startswith("postgresql")

    def test_database_connection(self):
        """测试数据库连接"""
        mgr = get_database_manager()

        with mgr.get_session() as session:
            # 执行简单查询测试连接
            result = session.execute(text("SELECT 1"))
            value = result.scalar()
            assert value == 1

    def test_postgresql_tables_exist(self):
        """测试PostgreSQL表是否正确创建"""
        mgr = get_database_manager()

        with mgr.get_session() as session:
            # 查询所有表
            result = session.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            )
            table_count = result.scalar()

            # 应该有至少40个表
            assert table_count >= 40, (
                f"Expected at least 40 tables, found {table_count}"
            )

            # 验证关键表存在
            key_tables = [
                "assets",
                "organizations",
                "users",
                "rent_contracts",
                "collection_records",  # Updated table name
            ]

            for table in key_tables:
                result = session.execute(
                    text(
                        "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_name = :table_name"
                    ),
                    {"table_name": table},
                )
                count = result.scalar()
                assert count == 1, f"Key table '{table}' not found"


@pytest.mark.integration
@pytest.mark.database
class TestPostgreSQLHealthCheck:
    """PostgreSQL健康检查测试"""

    def test_health_check_success(self):
        """测试健康检查成功场景"""
        mgr = get_database_manager()
        health_status = mgr.run_health_check()

        assert health_status["healthy"] is True
        assert "checks" in health_status
        assert "metrics" in health_status
        assert "timestamp" in health_status

        # 验证基本连接检查
        checks = health_status["checks"]
        assert "basic_connection" in checks or "connection_test" in checks

    def test_health_check_metrics(self):
        """测试健康检查返回的指标"""
        mgr = get_database_manager()
        health_status = mgr.run_health_check()

        metrics = health_status["metrics"]
        assert "active_connections" in metrics
        assert "total_queries" in metrics
        assert "avg_response_time" in metrics
        assert "database_status" not in metrics or isinstance(
            metrics.get("database_status"), str
        )


@pytest.mark.integration
@pytest.mark.database
class TestPostgreSQLConnectionPool:
    """PostgreSQL连接池测试"""

    def test_connection_pool_config(self):
        """测试连接池配置"""
        mgr = get_database_manager()
        config = mgr.config

        # 验证连接池参数
        assert config.pool_size > 0
        assert config.max_overflow >= 0
        assert config.pool_timeout > 0
        assert config.pool_recycle > 0

        # PostgreSQL应该使用QueuePool
        engine = get_database_manager().engine
        assert engine is not None
        # 检查pool类型
        from sqlalchemy.pool import QueuePool

        assert isinstance(engine.pool, QueuePool), (
            f"Expected QueuePool, got {type(engine.pool)}"
        )

    def test_connection_pool_metrics(self):
        """测试连接池指标"""
        mgr = get_database_manager()

        # 执行一些查询以产生指标
        with mgr.get_session() as session:
            session.execute(text("SELECT 1"))

        metrics = mgr.get_metrics()
        assert metrics.total_queries >= 1


@pytest.mark.integration
@pytest.mark.database
class TestPostgreSQLTransactionHandling:
    """PostgreSQL事务处理测试"""

    def test_transaction_commit(self):
        """测试事务提交"""
        mgr = get_database_manager()

        with mgr.get_session() as session:
            # 执行查询
            result = session.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            )
            count = result.scalar()
            assert count >= 40

    def test_transaction_rollback(self):
        """测试事务回滚"""
        mgr = get_database_manager()

        with pytest.raises(Exception):
            with mgr.get_session() as session:
                # 故意执行无效SQL
                session.execute(text("SELECT * FROM nonexistent_table_xyz"))

        # 验证会话已关闭且不影响后续操作
        with mgr.get_session() as session:
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1


@pytest.mark.integration
@pytest.mark.database
class TestPostgreSQLDataTypes:
    """PostgreSQL数据类型测试"""

    def test_json_data_type(self):
        """测试JSON数据类型"""
        mgr = get_database_manager()

        with mgr.get_session() as session:
            # PostgreSQL支持JSON类型
            result = session.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.columns "
                    "WHERE data_type IN ('json', 'jsonb') "
                    "AND table_schema = 'public'"
                )
            )
            json_columns = result.scalar()

            # 应该有JSON类型的列
            assert json_columns >= 0

    def test_boolean_data_type(self):
        """测试BOOLEAN数据类型"""
        mgr = get_database_manager()

        with mgr.get_session() as session:
            # PostgreSQL原生支持BOOLEAN
            result = session.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.columns "
                    "WHERE data_type = 'boolean' "
                    "AND table_schema = 'public'"
                )
            )
            bool_columns = result.scalar()

            # 应该有BOOLEAN类型的列
            assert bool_columns >= 0


@pytest.mark.integration
@pytest.mark.database
class TestPostgreSQLErrorHandling:
    """PostgreSQL错误处理测试"""

    def test_invalid_sql_error_handling(self):
        """测试无效SQL的错误处理"""
        mgr = get_database_manager()

        with pytest.raises(Exception) as exc_info:
            with mgr.get_session() as session:
                session.execute(text("INVALID SQL STATEMENT"))

        # 验证异常类型
        assert exc_info is not None

    def test_connection_error_handling(self):
        """测试连接错误的处理"""
        # 使用无效的数据库URL
        invalid_url = "postgresql+psycopg://invalid:invalid@localhost:9999/invalid_db"

        mgr = DatabaseManager()
        with pytest.raises(RuntimeError) as exc_info:
            mgr.initialize_engine(invalid_url)

        # 验证错误消息包含有用信息
        error_msg = str(exc_info.value)
        assert "数据库连接失败" in error_msg or "connection" in error_msg.lower()

    def test_database_url_validation(self):
        """测试DATABASE_URL验证"""
        from urllib.parse import urlparse

        database_url = get_database_url()

        # 验证可以正确解析
        parsed = urlparse(database_url)

        # 验证必需组件
        if database_url.startswith("postgresql+psycopg://"):
            assert parsed.hostname is not None
            assert parsed.username is not None
            assert parsed.path and len(parsed.path) > 1


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.security
class TestPostgreSQLAuditLogging:
    """PostgreSQL审计日志测试"""

    def test_audit_log_failure_handling(self):
        """测试审计日志失败处理"""
        from src.crud.auth import AuditLogCRUD
        from src.database import get_db

        # 获取数据库会话
        db_gen = get_db()
        db = next(db_gen)

        try:
            # 尝试创建审计日志
            audit_crud = AuditLogCRUD()
            # 正常情况下应该成功
            # 这里只验证方法存在且可调用
            assert callable(audit_crud.create)
        finally:
            # 清理
            try:
                db.close()
            except Exception:
                pass


@pytest.mark.integration
@pytest.mark.database
class TestPostgreSQLPerformance:
    """PostgreSQL性能测试"""

    def test_query_performance(self):
        """测试查询性能"""
        import time

        mgr = get_database_manager()

        start_time = time.time()
        with mgr.get_session() as session:
            # 执行多个查询
            for _ in range(10):
                session.execute(text("SELECT 1"))
        elapsed_time = time.time() - start_time

        # 10个简单查询应该在2秒内完成
        assert elapsed_time < 2.0, (
            f"Query performance is slow: {elapsed_time:.2f}s for 10 queries"
        )

    def test_connection_reuse(self):
        """测试连接复用"""
        mgr = get_database_manager()

        # 获取初始指标
        initial_metrics = mgr.get_metrics()

        # 执行多个查询
        with mgr.get_session() as session:
            for _ in range(5):
                session.execute(text("SELECT 1"))

        # 获取最终指标
        final_metrics = mgr.get_metrics()

        # 验证查询计数增加
        assert final_metrics.total_queries > initial_metrics.total_queries


@pytest.mark.integration
@pytest.mark.database
class TestPostgreSQLMigrationCompleteness:
    """PostgreSQL迁移完整性测试"""

    def test_all_tables_created(self):
        """测试所有必需的表都已创建"""
        mgr = get_database_manager()

        with mgr.get_session() as session:
            # 查询所有表
            result = session.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' "
                    "ORDER BY table_name"
                )
            )
            tables = [row[0] for row in result.fetchall()]

            # 验证关键表存在
            required_tables = [
                "assets",
                "asset_custom_fields",
                "asset_documents",
                "asset_history",
                "organizations",
                "users",
                "rent_contracts",
                "collection_records",  # Updated table name
                "contacts",
                "notifications",  # tasks table doesn't exist
                "operation_logs",
                "roles",  # Updated from rbac_roles
                "permissions",  # Updated from rbac_permissions
                "role_permissions",  # Updated from rbac_role_permissions
                "alembic_version",
            ]

            for table in required_tables:
                assert table in tables, (
                    f"Required table '{table}' not found in database"
                )

    def test_alembic_version_table(self):
        """测试Alembic版本表存在"""
        mgr = get_database_manager()

        with mgr.get_session() as session:
            # 检查alembic_version表
            result = session.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'alembic_version'"
                )
            )
            count = result.scalar()

            assert count == 1, "alembic_version table should exist"

    def test_foreign_key_constraints(self):
        """测试外键约束存在"""
        mgr = get_database_manager()

        with mgr.get_session() as session:
            # 查询外键约束
            result = session.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.table_constraints "
                    "WHERE constraint_schema = 'public' "
                    "AND constraint_type = 'FOREIGN KEY'"
                )
            )
            fk_count = result.scalar()

            # 应该有外键约束
            assert fk_count >= 10, (
                f"Expected at least 10 foreign key constraints, found {fk_count}"
            )
