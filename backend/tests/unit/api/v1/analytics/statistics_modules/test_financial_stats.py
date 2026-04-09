"""
Financial Stats Module 测试 (修复版)
测试财务统计模块的端点 - 匹配实际 API 实现
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.database import get_async_db
from src.main import app
from src.middleware.auth import get_current_active_user
from src.models.auth import User


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_user():
    user = Mock(spec=User)
    user.id = "test_user_001"
    user.username = "testuser"
    user.is_active = True
    return user


@pytest.fixture
def client(mock_db, mock_user):
    async def override_get_db():
        yield mock_db

    def override_get_user():
        return mock_user

    app.dependency_overrides[get_async_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_user
    with (
        patch(
            "src.middleware.auth.authz_service.check_access",
            AsyncMock(return_value=SimpleNamespace(allowed=True, reason_code="ALLOW")),
        ),
        patch(
            "src.middleware.auth.authz_service.context_builder.build_subject_context",
            AsyncMock(
                return_value=SimpleNamespace(
                    owner_party_ids=["owner-party-1"],
                    manager_party_ids=[],
                    headquarters_party_ids=[],
                    role_ids=[],
                )
            ),
        ),
        patch("src.middleware.auth.RBACService.is_admin", AsyncMock(return_value=False)),
    ):
        with TestClient(app) as test_client:
            yield test_client

    app.dependency_overrides.clear()


class TestFinancialStatistics:
    """财务统计测试 - 修复版"""

    def test_get_financial_summary(self, client):
        """
        测试获取财务汇总

        Given: 用户已登录
        When: 调用 GET /api/v1/statistics/financial-summary
        Then: 返回财务汇总数据
        """
        # Arrange - Mock FinancialService.calculate_summary
        with patch(
            "src.services.analytics.financial_service.FinancialService.calculate_summary"
        ) as mock_calc:
            mock_calc.return_value = {
                "total_assets": 100,
                "total_annual_income": 1000000.0,
                "total_annual_expense": 200000.0,
                "net_annual_income": 800000.0,
                "income_per_sqm": 20.0,
                "expense_per_sqm": 4.0,
            }

            # Act
            response = client.get("/api/v1/statistics/financial-summary")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["total_assets"] == 100
            assert data["total_annual_income"] == 1000000.0

    def test_financial_summary_with_filters(self, client):
        """
        测试带筛选的财务汇总

        Given: 用户提供筛选条件
        When: 调用 GET /api/v1/statistics/financial-summary?should_include_deleted=true
        Then: 返回包含已删除数据的财务汇总
        """
        # Arrange - 确保提供所有必需字段
        with patch(
            "src.services.analytics.financial_service.FinancialService.calculate_summary"
        ) as mock_calc:
            mock_calc.return_value = {
                "total_assets": 120,
                "total_annual_income": 1200000.0,
                "total_annual_expense": 200000.0,
                "net_annual_income": 1000000.0,
                "income_per_sqm": 25.0,
                "expense_per_sqm": 5.0,
            }

            # Act
            response = client.get(
                "/api/v1/statistics/financial-summary?should_include_deleted=true"
            )

            # Assert
            assert response.status_code == 200
