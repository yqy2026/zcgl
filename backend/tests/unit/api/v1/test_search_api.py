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
                        "route_path": "/assets/asset-1",
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
                        "route_path": "/customers/party-1",
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


def test_global_search_should_allow_missing_perspective_header(search_client):
    response = search_client.get("/api/v1/search?q=测试")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["items"][0]["route_path"] == "/assets/asset-1"


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
    assert payload["data"]["items"][1]["route_path"] == "/customers/party-1"
    assert payload["data"]["groups"][1]["object_type"] == "customer"


def _override_search_scope(monkeypatch, *, is_unrestricted, effective_party_ids):
    """用显式 DataScopeContext 覆盖搜索端点的数据范围依赖（跳过中间件）。"""
    from src.api.v1 import search as search_module
    from src.middleware.data_scope import DataScopeContext

    route = next(
        route for route in search_module.router.routes if "GET" in route.methods
    )
    scope_dependency = next(
        dep for dep in route.dependant.dependencies if dep.name == "_scope_ctx"
    )
    from src.main import app

    app.dependency_overrides[scope_dependency.call] = lambda: DataScopeContext(
        scope_mode="manager",
        allowed_binding_types=["manager"],
        owner_party_ids=[],
        manager_party_ids=[],
        effective_party_ids=effective_party_ids,
        source="auto",
        is_unrestricted=is_unrestricted,
    )


def test_global_search_fails_closed_403_when_empty_scope_is_not_unrestricted(
    monkeypatch
) -> None:
    """空主体范围 + 非 unrestricted 在 API 层必须 403，且不执行任何搜索。

    回归（2026-08-14 两轴复核 D6）：服务层自校验 is_unrestricted，数据范围中间件
    即使失效（正常用户拿到空范围），也不得按无范围搜索全部对象。
    """
    from src.main import app
    from src.services.search.service import search_service

    async def override_get_db():
        yield AsyncMock()

    mock_user = SimpleNamespace(
        id="search-user-1", username="searcher", is_active=True
    )
    app.dependency_overrides[get_async_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    _override_search_scope(
        monkeypatch,
        is_unrestricted=False,
        effective_party_ids=[],
    )
    collect = AsyncMock(return_value=[])
    monkeypatch.setattr(search_service, "_collect_results", collect)

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/search?q=测试")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["success"] is False
    collect.assert_not_awaited()


def test_global_search_unrestricted_empty_scope_still_searches(monkeypatch) -> None:
    """空主体范围 + unrestricted（内建管理员豁免）照常执行搜索。

    回归（2026-08-14 验收 D6）：管理员全局搜索不得被空范围短路为恒空。
    """
    from src.main import app
    from src.services.search.service import search_service

    async def override_get_db():
        yield AsyncMock()

    mock_user = SimpleNamespace(
        id="search-user-1", username="searcher", is_active=True
    )
    app.dependency_overrides[get_async_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    _override_search_scope(
        monkeypatch,
        is_unrestricted=True,
        effective_party_ids=[],
    )
    collect = AsyncMock(return_value=[])
    monkeypatch.setattr(search_service, "_collect_results", collect)

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/search?q=测试")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["total"] == 0
    collect.assert_awaited_once()
