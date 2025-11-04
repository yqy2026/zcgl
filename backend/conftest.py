"""
pytest配置文件 - 提供API测试所需的fixtures
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# 创建模拟的FastAPI应用
@pytest.fixture(scope="session")
def app():
    """模拟FastAPI应用"""
    mock_app = Mock()

    # 模拟路由注册
    mock_app.routes = []

    # 模拟中间件
    mock_app.middleware = Mock()

    # 模拟依赖注入
    mock_app.dependency_overrides = {}

    return mock_app


@pytest.fixture(scope="session")
def client(app):
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture(scope="session")
def mock_db_session():
    """模拟数据库会话"""
    session = Mock(spec=Session)
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.refresh = Mock()
    session.delete = Mock()
    session.query = Mock(return_value=Mock())
    session.execute = Mock(return_value=Mock())
    session.flush = Mock()
    return session


@pytest.fixture(scope="session")
def mock_user():
    """模拟用户对象"""
    user = Mock()
    user.id = "test_user_id"
    user.username = "testuser"
    user.email = "test@example.com"
    user.is_active = True
    user.is_superuser = False
    return user


@pytest.fixture(scope="session")
def sample_headers():
    """示例请求头"""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "pytest-client"
    }


@pytest.fixture(autouse=True)
def mock_environment():
    """自动应用的环境模拟"""
    import os
    # 设置测试环境变量
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    yield

    # 清理环境变量
    os.environ.pop("TESTING", None)
    os.environ.pop("DATABASE_URL", None)