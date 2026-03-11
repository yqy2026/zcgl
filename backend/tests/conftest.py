"""
Root conftest.py - runs before any test collection
"""

import base64
import os
import sys
import unittest.mock as _mock
from datetime import UTC, datetime
from pathlib import Path

# Work around Python's MagicMock(spec=..., __dict__=...) init bug in tests.
_OriginalMagicMock = _mock.MagicMock


class _SafeMagicMock(_OriginalMagicMock):
    def __init__(self, *args, **kwargs):
        dict_override = kwargs.pop("__dict__", None)
        super().__init__(*args, **kwargs)
        if dict_override:
            object.__getattribute__(self, "__dict__").update(dict_override)


_mock.MagicMock = _SafeMagicMock

import pytest


def _resolve_test_database_url() -> str | None:
    """Resolve TEST_DATABASE_URL from env first, then backend/.env as fallback."""
    env_value = os.getenv("TEST_DATABASE_URL")
    if env_value:
        return env_value

    env_file = Path(__file__).resolve().parents[1] / ".env"
    if not env_file.exists():
        return None

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == "" or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != "TEST_DATABASE_URL":
            continue
        parsed_value = value.strip().strip("\"'")
        if parsed_value:
            return parsed_value
    return None


def _is_safe_test_database(database_url: str) -> bool:
    """Best-effort guard to avoid destructive fallback on non-test databases."""
    try:
        from sqlalchemy.engine import make_url

        parsed = make_url(database_url)
        database_name = (parsed.database or "").lower()
    except Exception:
        database_name = database_url.lower()

    return "test" in database_name


def _recreate_test_schema_from_models(database_url: str) -> None:
    """Recreate schema from ORM metadata for test DB fallback path."""
    if not _is_safe_test_database(database_url):
        raise RuntimeError(
            "Refusing to recreate schema for non-test database URL. "
            "Set TEST_DATABASE_URL to a dedicated *_test database."
        )

    from sqlalchemy import create_engine, text

    import src.models  # noqa: F401 - ensure all model tables are registered
    from src.database import Base

    engine = create_engine(database_url)
    try:
        if engine.dialect.name == "postgresql":
            with engine.begin() as conn:
                conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
                conn.execute(text("CREATE SCHEMA public"))
        else:
            Base.metadata.drop_all(bind=engine)

        Base.metadata.create_all(bind=engine)
    finally:
        engine.dispose()


def _reset_test_schema(database_url: str) -> None:
    """Reset schema to empty state before running Alembic migrations."""
    if not _is_safe_test_database(database_url):
        raise RuntimeError(
            "Refusing to reset schema for non-test database URL. "
            "Set TEST_DATABASE_URL to a dedicated *_test database."
        )

    from sqlalchemy import create_engine, text

    engine = create_engine(database_url)
    try:
        if engine.dialect.name == "postgresql":
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = current_database()
                          AND pid <> pg_backend_pid()
                        """
                    )
                )
                conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
                conn.execute(text("CREATE SCHEMA public"))
        else:
            from src.database import Base

            Base.metadata.drop_all(bind=engine)
    finally:
        engine.dispose()


def _ensure_baseline_enum_data(database_url: str) -> None:
    """Seed baseline enum-field data for integration/e2e API validations."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from src.models.enum_field import EnumFieldType, EnumFieldValue

    enum_defs: dict[str, tuple[str, list[str]]] = {
        "ownership_status": (
            "确权状态",
            ["已确权", "待确权", "部分确权", "未确权", "确权中", "其它"],
        ),
        "property_nature": (
            "物业性质",
            [
                "经营类",
                "非经营类",
                "经营性",
                "商业",
                "住宅",
                "工业",
                "办公",
                "综合",
                "公房",
                "自用",
                "其它",
            ],
        ),
        "usage_status": (
            "使用状态",
            ["出租", "闲置", "自用", "在用", "空置", "公房（出租）", "公房（闲置）", "其它"],
        ),
        "data_status": ("数据状态", ["正常", "冻结", "已删除", "已归档"]),
    }

    engine = create_engine(database_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        for code, (name, values) in enum_defs.items():
            enum_type = (
                session.query(EnumFieldType)
                .filter(EnumFieldType.code == code)
                .first()
            )
            if enum_type is None:
                enum_type = EnumFieldType(
                    name=name,
                    code=code,
                    category="资产管理",
                    description=f"测试基线枚举: {name}",
                    is_system=True,
                    status="active",
                    is_deleted=False,
                    created_by="test_fixture",
                    updated_by="test_fixture",
                )
                session.add(enum_type)
                session.flush()
            else:
                enum_type.name = name
                enum_type.status = "active"
                enum_type.is_deleted = False
                enum_type.updated_by = "test_fixture"

            existing_values = {
                value_obj.value: value_obj
                for value_obj in (
                    session.query(EnumFieldValue)
                    .filter(EnumFieldValue.enum_type_id == enum_type.id)
                    .all()
                )
            }

            for sort_order, value in enumerate(values, start=1):
                value_obj = existing_values.get(value)
                if value_obj is None:
                    session.add(
                        EnumFieldValue(
                            enum_type_id=enum_type.id,
                            label=value,
                            value=value,
                            sort_order=sort_order,
                            is_active=True,
                            is_deleted=False,
                            created_by="test_fixture",
                            updated_by="test_fixture",
                        )
                    )
                    continue

                value_obj.label = value
                value_obj.sort_order = sort_order
                value_obj.is_active = True
                value_obj.is_deleted = False
                value_obj.updated_by = "test_fixture"

        session.commit()
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def ensure_legacy_party_mapping_hooks() -> None:
    """Auto-sync legacy Organization/Ownership inserts to Party rows in tests."""
    from sqlalchemy import event, select

    from src.models.organization import Organization
    from src.models.ownership import Ownership
    from src.models.party import Party, PartyType

    party_table = Party.__table__

    def _utcnow_naive() -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    def _build_safe_code(
        connection, *, party_type: str, preferred_code: str | None, entity_id: str
    ) -> str:
        normalized_code = (preferred_code or "").strip()
        if normalized_code == "":
            normalized_code = f"{party_type[:3].upper()}-{str(entity_id)[:8]}"

        existing_party_id = connection.execute(
            select(party_table.c.id)
            .where(
                party_table.c.party_type == party_type,
                party_table.c.code == normalized_code,
            )
            .limit(1)
        ).scalar_one_or_none()
        if existing_party_id is None or str(existing_party_id) == str(entity_id):
            return normalized_code
        return f"{normalized_code}-{str(entity_id)[:8]}"

    def _ensure_party_row(
        connection,
        *,
        party_id: str,
        party_type: str,
        name: str | None,
        code: str | None,
        external_ref: str | None,
    ) -> None:
        existing = connection.execute(
            select(party_table.c.id).where(party_table.c.id == party_id).limit(1)
        ).scalar_one_or_none()
        if existing is not None:
            return

        safe_name = (name or "").strip() or f"{party_type}-{str(party_id)[:8]}"
        safe_code = _build_safe_code(
            connection,
            party_type=party_type,
            preferred_code=code,
            entity_id=party_id,
        )
        now = _utcnow_naive()
        connection.execute(
            party_table.insert().values(
                id=str(party_id),
                party_type=party_type,
                name=safe_name,
                code=safe_code,
                external_ref=(external_ref or "").strip() or str(party_id),
                status="active",
                created_at=now,
                updated_at=now,
            )
        )

    @event.listens_for(Organization, "after_insert")
    def _sync_organization_party(_mapper, connection, target) -> None:
        _ensure_party_row(
            connection,
            party_id=str(target.id),
            party_type=PartyType.ORGANIZATION.value,
            name=getattr(target, "name", None),
            code=getattr(target, "code", None),
            external_ref=str(target.id),
        )

    @event.listens_for(Ownership, "after_insert")
    def _sync_ownership_party(_mapper, connection, target) -> None:
        _ensure_party_row(
            connection,
            party_id=str(target.id),
            party_type=PartyType.LEGAL_ENTITY.value,
            name=getattr(target, "name", None),
            code=getattr(target, "code", None),
            external_ref=str(target.id),
        )

    yield

    event.remove(Organization, "after_insert", _sync_organization_party)
    event.remove(Ownership, "after_insert", _sync_ownership_party)


# Set environment variables at the earliest possible moment
# Use TEST_DATABASE_URL for database-backed tests
# Integration/E2E tests should set their own *_TEST_DATABASE_URL
# Performance improvement: 37min → <5min (estimated)
TEST_DATABASE_URL = _resolve_test_database_url()
if TEST_DATABASE_URL:
    os.environ["TEST_DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
elif "DATABASE_URL" not in os.environ:
    # Fallback placeholder to satisfy settings import in non-DB tests
    os.environ["DATABASE_URL"] = (
        "postgresql+psycopg://user:pass@localhost:5432/zcgl_test"
    )
    TEST_DATABASE_URL = None

# 为测试环境设置强密钥（使用固定种子确保可复现性，或动态生成）
# 这里使用动态生成，因为测试不应依赖于特定的密钥值
# 注意：必须使用真正随机的密钥，不能包含 "test", "secret", "key" 等弱模式
test_secret_key = os.getenv("SECRET_KEY")
if not test_secret_key or any(
    weak in test_secret_key.lower() for weak in ["test", "secret", "key", "changeme"]
):
    # 使用固定的测试密钥（确保无弱模式）
    # 53字符字符串，包含大写、小写、数字和特殊字符，满足Task 7验证器要求
    os.environ["SECRET_KEY"] = "aB3xK7mN9pQ2rS5tU8vW1xY4zZ6bC8dE0fG2hI4jK6!@#$%^&*"


def _is_valid_encryption_key(raw_key: str | None) -> bool:
    """Validate DATA_ENCRYPTION_KEY format: base64_key:version (supports multi-key)."""
    if not raw_key:
        return False

    key_parts = [part.strip() for part in raw_key.split(",") if part.strip()]
    if not key_parts:
        return False

    for part in key_parts:
        key_b64 = part
        if ":" in part:
            key_b64, version_str = part.rsplit(":", 1)
            try:
                int(version_str)
            except ValueError:
                return False
        try:
            key_bytes = base64.b64decode(key_b64)
        except Exception:
            return False
        if len(key_bytes) < 32:
            return False
    return True


if not _is_valid_encryption_key(os.getenv("DATA_ENCRYPTION_KEY")):
    # 设置测试数据加密密钥（base64 的 32-byte key + 版本号）
    os.environ["DATA_ENCRYPTION_KEY"] = (
        "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=:1"
    )

DEFAULT_TEST_DATA_ENCRYPTION_KEY = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=:1"

os.environ["DEBUG"] = "False"
os.environ["ENVIRONMENT"] = "testing"
os.environ["PYDANTIC_SETTINGS_IGNORE_DOT_ENV"] = "1"
# Keep Phase 4 migration deterministic in tests unless explicitly overridden.
os.environ.setdefault("PHASE4_TENANT_NOT_NULL_DECISION", "B")


def pytest_collection_modifyitems(items, config):
    """
    钩子：为特定目录下的测试自动应用标记

    这个钩子在测试收集完成后、测试执行前被调用
    """
    for item in items:
        # 获取测试文件的路径
        test_path = str(item.fspath)
        existing_marks = [mark.name for mark in item.iter_markers()]

        # 根据目录自动添加标记
        if "/tests/unit/" in test_path or "\\tests\\unit\\" in test_path:
            if "unit" not in existing_marks:
                item.add_marker(pytest.mark.unit)
        elif (
            "/tests/integration/" in test_path or "\\tests\\integration\\" in test_path
        ):
            if "integration" not in existing_marks:
                item.add_marker(pytest.mark.integration)
        elif "/tests/api/" in test_path or "\\tests\\api\\" in test_path:
            if "api" not in existing_marks:
                item.add_marker(pytest.mark.api)


@pytest.fixture(scope="session", autouse=True)
def hide_env_file():
    """
    Session-scoped fixture to temporarily hide .env file during tests.
    This prevents Pydantic Settings from reading DATA_ENCRYPTION_KEY from .env,
    allowing tests to control the encryption key via environment variables.

    The .env file is renamed to .env.backup before tests and restored after.
    """
    import shutil

    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    backup_path = env_path + ".backup"

    # Self-heal previous interrupted test runs that left only .env.backup
    if not os.path.exists(env_path) and os.path.exists(backup_path):
        shutil.move(backup_path, env_path)
        print("[*] Recovered orphaned .env from .env.backup before tests")

    # Check if .env file exists
    if os.path.exists(env_path):
        # Rename .env to .env.backup
        shutil.move(env_path, backup_path)
        print("[*] Temporarily hid .env file for tests (backed up as .env.backup)")

    yield

    # Restore .env file after all tests complete
    if os.path.exists(backup_path):
        shutil.move(backup_path, env_path)
        print("[*] Restored .env file after tests")


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Session-scoped fixture to set up the test database before any tests run.
    This ensures database tables exist for integration tests.

    Runs once per test session for performance.
    """
    import subprocess

    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        yield
        return

    cli_args = sys.argv[1:]
    marker_expr = ""
    if "-m" in cli_args:
        marker_index = cli_args.index("-m")
        if marker_index + 1 < len(cli_args):
            marker_expr = cli_args[marker_index + 1]

    is_unit_marker_run = "unit" in marker_expr
    is_unit_path_run = any(
        "/tests/unit/" in arg
        or "\\tests\\unit\\" in arg
        or arg.startswith("tests/unit/")
        or arg.startswith("tests\\unit\\")
        or arg == "tests/unit"
        or arg == "tests\\unit"
        or arg.endswith("/tests/unit")
        or arg.endswith("\\tests\\unit")
        for arg in cli_args
    )

    # 仅在非 unit 调用时执行迁移预热，避免 unit 选择性运行时产生长时间 DB 连接等待
    run_migrations = not (is_unit_marker_run or is_unit_path_run)

    if run_migrations and "postgresql" in database_url:
        backend_root = Path(__file__).resolve().parents[1]
        alembic_ini = backend_root / "alembic.ini"
        try:
            print(f"\n[*] Setting up test database: {database_url}")
            _reset_test_schema(database_url)
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "alembic",
                    "-c",
                    str(alembic_ini),
                    "upgrade",
                    "head",
                ],
                cwd=str(backend_root),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                print("[OK] Database migrations completed successfully")
            else:
                stderr_text = (result.stderr or "").strip()
                stdout_text = (result.stdout or "").strip()
                detail_text = "\n".join(
                    part for part in (stderr_text, stdout_text) if part != ""
                )
                if detail_text:
                    print(f"[!] Migration warnings:\n{detail_text}")
                else:
                    print("[!] Migration warnings: subprocess returned non-zero exit code")

                _recreate_test_schema_from_models(database_url)
                print("[OK] Database schema recreated from models (fallback)")

            _ensure_baseline_enum_data(database_url)
            print("[OK] Baseline enum data ensured")
        except Exception as e:
            print(f"[!] Database setup failed: {e}")
            try:
                _recreate_test_schema_from_models(database_url)
                print("[OK] Database schema recreated from models (fallback)")
                _ensure_baseline_enum_data(database_url)
                print("[OK] Baseline enum data ensured")
            except Exception as e2:
                print(f"[ERROR] Database setup failed completely: {e2}")

    yield


@pytest.fixture(autouse=True)
def reset_settings_debug():
    """
    Auto-used fixture to ensure settings.DEBUG is reset before each test.
    This prevents test isolation issues when tests modify the global settings object.
    This fixture applies to ALL tests in the entire test suite.
    """
    from src.core.config import settings

    original_debug = settings.DEBUG
    yield
    # Always restore to original value after test
    settings.DEBUG = original_debug


@pytest.fixture(autouse=True)
def reset_settings_secret_key():
    """
    Keep settings.SECRET_KEY aligned with the current environment for test isolation.
    Some test modules mutate os.environ; ensure the global settings object stays stable.
    """
    from src.core.config import settings

    def sync_secret_key() -> None:
        env_key = os.environ.get("SECRET_KEY")
        if env_key:
            settings.SECRET_KEY = env_key

    sync_secret_key()
    yield
    sync_secret_key()


@pytest.fixture(autouse=True)
def reset_encryption_key(monkeypatch):
    """
    Auto-used fixture to normalize DATA_ENCRYPTION_KEY before each test.
    Tests can still override or clear it explicitly when needed.
    """
    from src.core import config
    from src.core import encryption as encryption_module

    monkeypatch.setenv("DATA_ENCRYPTION_KEY", DEFAULT_TEST_DATA_ENCRYPTION_KEY)
    config.settings.DATA_ENCRYPTION_KEY = DEFAULT_TEST_DATA_ENCRYPTION_KEY
    encryption_module.settings.DATA_ENCRYPTION_KEY = DEFAULT_TEST_DATA_ENCRYPTION_KEY
    yield
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", DEFAULT_TEST_DATA_ENCRYPTION_KEY)
    config.settings.DATA_ENCRYPTION_KEY = DEFAULT_TEST_DATA_ENCRYPTION_KEY
    encryption_module.settings.DATA_ENCRYPTION_KEY = DEFAULT_TEST_DATA_ENCRYPTION_KEY


@pytest.fixture(autouse=True)
def reset_token_blacklist_state():
    """Reset in-memory token blacklist between tests to avoid cross-test pollution."""
    from src.security.token_blacklist import blacklist_manager

    blacklist_manager.clear_blacklist()
    yield
    blacklist_manager.clear_blacklist()


# =============================================================================
# Mock Factory Fixtures
# =============================================================================


@pytest.fixture
def mock_factory():
    """
    Mock 工厂 fixture
    提供统一的 Mock 对象创建方法
    """
    from tests.factories.mock_factory import MockFactory

    return MockFactory


@pytest.fixture
def mock_db(mock_factory):
    """
    Mock 数据库会话 fixture
    返回一个配置好的 Mock 数据库对象
    """
    return mock_factory.create_mock_db()


@pytest.fixture
def mock_user(mock_factory):
    """
    Mock 用户对象 fixture
    """
    return mock_factory.create_mock_user()


@pytest.fixture
def mock_asset(mock_factory):
    """
    Mock 资产对象 fixture
    """
    return mock_factory.create_mock_asset()


@pytest.fixture
def mock_contract(mock_factory):
    """
    Mock 合同对象 fixture
    """
    return mock_factory.create_mock_contract()


@pytest.fixture
def mock_ownership(mock_factory):
    """
    Mock 权属对象 fixture
    """
    return mock_factory.create_mock_ownership()


@pytest.fixture
def mock_organization(mock_factory):
    """
    Mock 组织机构对象 fixture
    """
    return mock_factory.create_mock_organization()


@pytest.fixture
def test_data_generator():
    """
    测试数据生成器 fixture
    使用 Faker 生成真实的测试数据
    """
    from tests.fixtures.test_data_generator import TestDataGenerator

    return TestDataGenerator
