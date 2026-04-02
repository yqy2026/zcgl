from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.database import get_async_db
from src.main import app
from src.middleware.auth import get_current_active_user
from src.services.authz.context_builder import SubjectContext


@pytest.fixture
def search_client(monkeypatch):
    mock_user = SimpleNamespace(id="search-user-1", username="searcher", is_active=True)

    async def override_get_db():
        yield AsyncMock()

    monkeypatch.setattr(
        "src.services.search.service.search_service.search_global",
        AsyncMock(
            return_value={
                "query": "测试",
                "total": 2,
                "items": [
                    {
                        "object_type": "asset",
                        "object_id": "asset-1",
                        "title": "测试资产",
                        "subtitle": "AST-001",
                        "summary": "资产结果",
                        "keywords": ["asset_name"],
                        "route_path": "/manager/assets/asset-1",
                        "score": 90,
                        "business_rank": 50,
                        "group_label": "资产",
                    },
                    {
                        "object_type": "customer",
                        "object_id": "party-1",
                        "title": "终端租户甲",
                        "subtitle": "external",
                        "summary": "客户结果",
                        "keywords": ["customer_name"],
                        "route_path": "/manager/customers/party-1",
                        "score": 80,
                        "business_rank": 40,
                        "group_label": "客户",
                    },
                ],
                "groups": [
                    {"object_type": "asset", "label": "资产", "count": 1},
                    {"object_type": "customer", "label": "客户", "count": 1},
                ],
            }
        ),
    )

    app.dependency_overrides[get_async_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    monkeypatch.setattr(
        "src.middleware.auth.authz_service.context_builder.build_subject_context",
        AsyncMock(
            return_value=SubjectContext(
                user_id="search-user-1",
                owner_party_ids=["owner-party-1"],
                manager_party_ids=["manager-party-1"],
                headquarters_party_ids=[],
                role_ids=[],
            )
        ),
    )
    monkeypatch.setattr(
        "src.middleware.auth.RBACService.is_admin",
        AsyncMock(return_value=False),
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_global_search_should_require_perspective_header(search_client):
    response = search_client.get("/api/v1/search?q=测试")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_global_search_should_return_grouped_results(search_client):
    response = search_client.get(
        "/api/v1/search?q=测试",
        headers={"X-Perspective": "manager"},
    )

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["total"] == 2
    assert payload["data"]["items"][0]["object_type"] == "asset"
    assert payload["data"]["groups"][1]["object_type"] == "customer"
