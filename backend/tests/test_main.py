"""
主应用测试
"""

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_root():
    """测试根路径"""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_health_check():
    """测试健康检查"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data