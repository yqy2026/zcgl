"""
pytest全局配置文件
提供所有测试共享的fixtures和配置
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from typing import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# 添加backend根目录到Python路径
backend_root = Path(__file__).parent
sys.path.insert(0, str(backend_root))

# =============================================================================
# 数据库Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def test_engine():
    """创建测试数据库引擎（内存SQLite）"""
    from src.database import Base
    
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db(test_engine) -> Generator[Session, None, None]:
    """创建测试数据库会话"""
    from src.database import SessionLocal
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture(scope="function")
def test_client(test_db):
    """创建测试API客户端"""
    from src.main import app
    from src.database import get_db
    
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()


# =============================================================================
# 认证Fixtures
# =============================================================================

@pytest.fixture
def test_user(test_db):
    """创建测试用户"""
    from src.models.auth import User
    
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password",
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_admin(test_db):
    """创建测试管理员"""
    from src.models.auth import User
    
    admin = User(
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        hashed_password="hashed_password",
        is_active=True,
        is_superuser=True,
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)
    return admin


@pytest.fixture
def auth_headers(test_user):
    """生成认证头"""
    import jwt
    from datetime import datetime, timedelta
    
    token_data = {
        "sub": test_user.username,
        "user_id": str(test_user.id),
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    token = jwt.encode(token_data, "test-secret", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# 测试数据Fixtures
# =============================================================================

@pytest.fixture
def sample_asset_data():
    """示例资产数据"""
    return {
        "ownership_entity": "测试权属人",
        "management_entity": "测试管理人",
        "property_name": "测试物业",
        "address": "测试地址123号",
        "actual_property_area": 1000.0,
        "rentable_area": 800.0,
        "rented_area": 600.0,
        "ownership_status": "已确权",
        "property_nature": "商业用途",
        "usage_status": "使用中",
        "is_litigated": False,
    }


@pytest.fixture
def sample_asset(test_db, sample_asset_data):
    """创建示例资产"""
    from src.models.asset import Asset
    
    asset = Asset(**sample_asset_data)
    test_db.add(asset)
    test_db.commit()
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
def mock_ocr_service():
    """Mock OCR服务"""
    ocr_mock = AsyncMock()
    ocr_mock.extract_text = AsyncMock(return_value="提取的文本内容")
    ocr_mock.extract_structure = AsyncMock(return_value={})
    return ocr_mock


# =============================================================================
# 性能测试Fixtures
# =============================================================================

@pytest.fixture
def benchmark_logger():
    """性能基准测试日志记录器"""
    results = []
    
    def log_result(test_name: str, duration: float, metadata: dict = None):
        results.append({
            "test_name": test_name,
            "duration": duration,
            "metadata": metadata or {},
        })
    
    yield log_result
    
    # 输出性能报告
    if results:
        print("\n" + "=" * 60)
        print("性能测试报告")
        print("=" * 60)
        for result in results:
            print(f"{result['test_name']}: {result['duration']:.4f}s")
        print("=" * 60)
