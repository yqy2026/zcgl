"""
pytest全局配置文件
提供所有测试共享的fixtures和配置
"""

import os
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# 添加backend根目录到Python路径
backend_root = Path(__file__).parent
sys.path.insert(0, str(backend_root))

# 设置测试模式环境变量（在导入app之前）
os.environ["TESTING_MODE"] = "true"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DEBUG"] = "true"  # 启用调试模式以允许访问调试端点

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if TEST_DATABASE_URL:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
elif not os.getenv("DATABASE_URL"):
    # Fallback placeholder to satisfy settings import in non-DB tests
    os.environ["DATABASE_URL"] = (
        "postgresql+psycopg://user:pass@localhost:5432/zcgl_test"
    )
    TEST_DATABASE_URL = None

# 设置测试环境必需的环境变量
if "SECRET_KEY" not in os.environ or os.environ["SECRET_KEY"].startswith("<generate"):
    os.environ["SECRET_KEY"] = (
        "E0ocpsl2ek0uCNqh65GUSKwMUy9m20BAMXiTGXvkxm4"  # 强密钥用于测试
    )
if "DATA_ENCRYPTION_KEY" not in os.environ or os.environ[
    "DATA_ENCRYPTION_KEY"
].startswith("<generate"):
    os.environ["DATA_ENCRYPTION_KEY"] = (
        "test-encryption-key-for-testing-only-min-32-chars-long"
    )


# 确保测试产物目录存在
def pytest_configure(config):
    artifacts_root = backend_root.parent / "test-results" / "backend"
    coverage_root = artifacts_root / "coverage"
    junit_root = artifacts_root / "junit"
    for directory in (coverage_root, coverage_root / "html", junit_root):
        directory.mkdir(parents=True, exist_ok=True)


# =============================================================================
# 数据库Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def test_engine():
    """创建测试数据库引擎（PostgreSQL）"""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is required for database tests")

    import src.models  # noqa: F401 - Trigger model registration
    from src.database import Base

    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    yield engine
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception:
        # Ignore errors during teardown (e.g. circular dependencies)
        pass
    engine.dispose()


@pytest.fixture(scope="function")
def test_db(test_engine) -> Generator[Session, None, None]:
    """创建测试数据库会话"""

    testing_session_local = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    db = testing_session_local()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture(scope="function")
async def test_client(test_db, test_user):
    """创建测试API客户端"""
    from src.database import get_db
    from src.main import app
    from src.middleware.auth import get_current_active_user, get_current_user

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    async def override_get_auth():
        """Mock认证依赖，直接返回测试用户"""
        return test_user

    # Override both dependencies in the chain
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_auth
    app.dependency_overrides[get_current_active_user] = override_get_auth

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def test_client_no_auth(test_db):
    """创建测试API客户端（无认证覆盖，用于测试未授权访问）"""
    from src.database import get_db
    from src.main import app

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    # Only override database, not authentication
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        yield client

    app.dependency_overrides.clear()


# =============================================================================
# 认证Fixtures
# =============================================================================


@pytest.fixture
def test_user(test_db):
    """创建测试用户"""
    from src.models.auth import User
    from src.services.core.password_service import PasswordService

    # Check if user already exists to avoid UNIQUE constraint errors
    existing_user = test_db.query(User).filter(User.username == "testuser").first()
    if existing_user:
        return existing_user

    # Create proper password hash with special character
    password_service = PasswordService()
    password_hash = password_service.get_password_hash("Admin@123")

    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        password_hash=password_hash,
        is_active=True,
        role="admin",  # 设为管理员以便测试有权限要求的端点
    )
    test_db.add(user)
    test_db.flush()  # Use flush instead of commit so test_db rollback can clean up
    test_db.refresh(user)
    return user


@pytest.fixture
def test_admin(test_db):
    """创建测试管理员"""
    from src.models.auth import User
    from src.services.core.password_service import PasswordService

    # Check if admin already exists to avoid UNIQUE constraint errors
    existing_admin = test_db.query(User).filter(User.username == "admin").first()
    if existing_admin:
        return existing_admin

    # Create proper password hash with special character
    password_service = PasswordService()
    password_hash = password_service.get_password_hash("Admin@123")

    admin = User(
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        password_hash=password_hash,
        is_active=True,
        role="admin",
    )
    test_db.add(admin)
    test_db.flush()  # Use flush instead of commit
    test_db.refresh(admin)
    return admin


@pytest.fixture
def auth_headers(test_user):
    """生成认证头"""
    from datetime import datetime, timedelta

    import jwt

    from src.core.config import settings

    now = datetime.utcnow()
    token_data = {
        "sub": str(test_user.id),  # sub should be user_id
        "user_id": str(test_user.id),  # legacy field
        "username": test_user.username,
        "role": test_user.role or "user",
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "iat": int(now.timestamp()),
        "jti": str(test_user.id),  # JWT ID
        "aud": settings.JWT_AUDIENCE,  # audience
        "iss": settings.JWT_ISSUER,  # issuer
    }
    # 使用应用的SECRET_KEY
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# 测试数据Fixtures
# =============================================================================


@pytest.fixture
def sample_asset_data():
    """示例资产数据"""
    return {
        "ownership_entity": "测试权属人",
        "property_name": "测试物业",
        "address": "测试地址123号",
        "actual_property_area": 1000.0,
        "rentable_area": 800.0,
        "rented_area": 600.0,
        "ownership_status": "已确权",  # OwnershipStatus.CONFIRMED
        "property_nature": "经营性",  # PropertyNature.COMMERCIAL
        "usage_status": "出租",  # UsageStatus.RENTED
        "is_litigated": False,
    }


@pytest.fixture
def sample_ownership(test_db):
    """创建示例权属方"""
    from src.models.asset import Ownership

    ownership = Ownership(name="测试权属方", code=f"OWN-{uuid4().hex[:8]}")
    test_db.add(ownership)
    test_db.flush()
    test_db.refresh(ownership)
    return ownership


@pytest.fixture
def sample_asset_with_ownership(test_db, sample_asset_data, sample_ownership):
    """创建示例资产（绑定权属方）"""
    from src.models.asset import Asset

    asset_data = dict(sample_asset_data)
    asset_data["ownership_id"] = sample_ownership.id
    asset = Asset(**asset_data)
    test_db.add(asset)
    test_db.flush()
    test_db.refresh(asset)
    return asset


@pytest.fixture
def sample_asset(test_db, sample_asset_data):
    """创建示例资产"""
    from src.models.asset import Asset

    asset = Asset(**sample_asset_data)
    test_db.add(asset)
    test_db.flush()  # Use flush instead of commit
    test_db.refresh(asset)
    return asset


# =============================================================================
# 文件处理Fixtures
# =============================================================================


@pytest.fixture
def temp_file():
    """创建临时文件"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pdf") as f:
        f.write("Mock PDF content")
        temp_path = f.name

    yield temp_path

    # 清理
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_upload_dir():
    """创建临时上传目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_redis():
    """Mock Redis客户端"""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=True)
    redis_mock.exists = AsyncMock(return_value=False)
    return redis_mock


@pytest.fixture
def mock_vision_service():
    """Mock Vision服务"""
    vision_mock = AsyncMock()
    vision_mock.extract_text = AsyncMock(return_value="提取的文本内容")
    vision_mock.extract_structure = AsyncMock(return_value={})
    return vision_mock


# =============================================================================
# 性能测试Fixtures
# =============================================================================


@pytest.fixture
def benchmark_logger():
    """性能基准测试日志记录器"""
    results = []

    def log_result(test_name: str, duration: float, metadata: dict = None):
        results.append(
            {
                "test_name": test_name,
                "duration": duration,
                "metadata": metadata or {},
            }
        )

    yield log_result

    # 输出性能报告
    if results:
        print("\n" + "=" * 60)
        print("性能测试报告")
        print("=" * 60)
        for result in results:
            print(f"{result['test_name']}: {result['duration']:.4f}s")
        print("=" * 60)
