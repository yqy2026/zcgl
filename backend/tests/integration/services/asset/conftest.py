"""
Asset Service 测试配置
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
if TEST_DATABASE_URL.startswith("sqlite"):
    raise RuntimeError("SQLite 已移除，测试必须使用 PostgreSQL")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from src.database import Base
from src.models.enum_field import EnumFieldType, EnumFieldValue


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

    # 初始化枚举数据
    session = sessionmaker(bind=engine)()
    _init_enum_data(session)
    session.commit()
    session.close()

    yield engine
    engine.dispose()


def _init_enum_data(session):
    """初始化测试所需的枚举数据"""
    # 创建确权状态枚举类型
    ownership_status_type = EnumFieldType(
        name="确权状态", code="ownership_status", is_system=True, status="active"
    )
    session.add(ownership_status_type)
    session.flush()

    # 添加确权状态值
    for value in ["已确权", "未确权", "确权中"]:
        session.add(
            EnumFieldValue(
                enum_type_id=ownership_status_type.id, label=value, value=value
            )
        )

    # 创建使用状态枚举类型
    usage_status_type = EnumFieldType(
        name="使用状态", code="usage_status", is_system=True, status="active"
    )
    session.add(usage_status_type)
    session.flush()

    # 添加使用状态值
    for value in ["在用", "空置", "自用", "出租中"]:
        session.add(
            EnumFieldValue(enum_type_id=usage_status_type.id, label=value, value=value)
        )

    # 创建物业性质枚举类型
    property_nature_type = EnumFieldType(
        name="物业性质", code="property_nature", is_system=True, status="active"
    )
    session.add(property_nature_type)
    session.flush()

    # 添加物业性质值
    for value in ["住宅", "商业", "办公", "工业", "综合"]:
        session.add(
            EnumFieldValue(
                enum_type_id=property_nature_type.id, label=value, value=value
            )
        )

    # 创建数据状态枚举类型
    data_status_type = EnumFieldType(
        name="数据状态", code="data_status", is_system=True, status="active"
    )
    session.add(data_status_type)
    session.flush()

    # 添加数据状态值
    for value in ["正常", "草稿", "已审核", "已发布"]:
        session.add(
            EnumFieldValue(enum_type_id=data_status_type.id, label=value, value=value)
        )


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
