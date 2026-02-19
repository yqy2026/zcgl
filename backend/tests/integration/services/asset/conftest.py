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
    pytest.skip(
        "TEST_DATABASE_URL is required for integration tests", allow_module_level=True
    )
if not TEST_DATABASE_URL.startswith("postgresql"):
    raise RuntimeError("测试必须使用 PostgreSQL")
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
    def get_or_create_enum_type(type_name: str, type_code: str) -> EnumFieldType:
        existing = (
            session.query(EnumFieldType)
            .filter(EnumFieldType.code == type_code, EnumFieldType.is_deleted.is_(False))
            .first()
        )
        if existing is not None:
            return existing

        enum_type = EnumFieldType(
            name=type_name,
            code=type_code,
            is_system=True,
            status="active",
        )
        session.add(enum_type)
        session.flush()
        return enum_type

    def ensure_enum_values(enum_type_id: str, values: list[str]) -> None:
        existing_values = {
            row[0]
            for row in session.query(EnumFieldValue.value)
            .filter(
                EnumFieldValue.enum_type_id == enum_type_id,
                EnumFieldValue.is_deleted.is_(False),
            )
            .all()
        }
        for value in values:
            if value in existing_values:
                continue
            session.add(
                EnumFieldValue(
                    enum_type_id=enum_type_id,
                    label=value,
                    value=value,
                )
            )

    ownership_status_type = get_or_create_enum_type("确权状态", "ownership_status")
    ensure_enum_values(ownership_status_type.id, ["已确权", "未确权", "确权中"])

    usage_status_type = get_or_create_enum_type("使用状态", "usage_status")
    ensure_enum_values(usage_status_type.id, ["在用", "空置", "自用", "出租中"])

    property_nature_type = get_or_create_enum_type("物业性质", "property_nature")
    ensure_enum_values(property_nature_type.id, ["住宅", "商业", "办公", "工业", "综合"])

    data_status_type = get_or_create_enum_type("数据状态", "data_status")
    ensure_enum_values(data_status_type.id, ["正常", "草稿", "已审核", "已发布"])


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
