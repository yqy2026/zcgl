from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.crud.query_builder import PartyFilter
from src.services.search.service import SearchService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def search_service():
    return SearchService()


async def test_search_global_should_fail_closed_when_scope_empty(search_service):
    result = await search_service.search_global(
        db=AsyncMock(),
        query="测试",
        scope_mode="manager",
        effective_party_ids=[],
    )

    assert result["items"] == []
    assert result["groups"] == []
    assert result["total"] == 0


async def test_search_global_should_sort_and_group_results(search_service):
    search_service._collect_results = AsyncMock(  # type: ignore[attr-defined]
        return_value=[
            {
                "object_type": "project",
                "object_id": "project-1",
                "title": "测试项目",
                "subtitle": "PRJ-001",
                "summary": "项目结果",
                "keywords": ["project_name"],
                "route_path": "/project/project-1",
                "score": 70,
                "business_rank": 40,
                "group_label": "项目",
            },
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
                "score": 60,
                "business_rank": 30,
                "group_label": "客户",
            },
        ]
    )

    result = await search_service.search_global(
        db=AsyncMock(),
        query="测试",
        scope_mode="manager",
        effective_party_ids=["party-manager-1"],
    )

    assert [item["object_type"] for item in result["items"]] == [
        "asset",
        "project",
        "customer",
    ]
    assert result["groups"] == [
        {"object_type": "asset", "label": "资产", "count": 1},
        {"object_type": "project", "label": "项目", "count": 1},
        {"object_type": "customer", "label": "客户", "count": 1},
    ]
    assert result["total"] == 3


async def test_search_assets_should_build_search_result_items(
    search_service, monkeypatch
):
    monkeypatch.setattr(
        "src.services.search.service.asset_crud.get_multi_with_search_async",
        AsyncMock(
            return_value=(
                [
                    SimpleNamespace(
                        id="asset-1",
                        asset_name="测试资产",
                        asset_code="AST-001",
                        address="上海市测试路 1 号",
                    )
                ],
                1,
            )
        ),
    )

    result = await search_service._search_assets(
        db=AsyncMock(),
        query="测试",
        scope_mode="manager",
        party_filter=PartyFilter(
            party_ids=["party-manager-1"],
            filter_mode="manager",
            owner_party_ids=[],
            manager_party_ids=["party-manager-1"],
        ),
    )

    assert result == [
        {
            "object_type": "asset",
            "object_id": "asset-1",
            "title": "测试资产",
            "subtitle": "AST-001",
            "summary": "上海市测试路 1 号",
            "keywords": ["asset_name"],
            "route_path": "/assets/asset-1",
            "score": 85,
            "business_rank": 0,
            "group_label": "资产",
        }
    ]


async def test_search_projects_should_build_search_result_items(
    search_service, monkeypatch
):
    monkeypatch.setattr(
        "src.services.search.service.project_service.search_projects",
        AsyncMock(
            return_value={
                "items": [
                    SimpleNamespace(
                        id="project-1",
                        project_name="测试项目",
                        project_code="PRJ-001",
                        status="active",
                    )
                ]
            }
        ),
    )

    result = await search_service._search_projects(
        db=AsyncMock(),
        query="测试",
        scope_mode="manager",
        party_filter=PartyFilter(
            party_ids=["party-manager-1"],
            filter_mode="manager",
            owner_party_ids=[],
            manager_party_ids=["party-manager-1"],
        ),
    )

    assert result == [
        {
            "object_type": "project",
            "object_id": "project-1",
            "title": "测试项目",
            "subtitle": "PRJ-001",
            "summary": "active",
            "keywords": ["project_name"],
            "route_path": "/project/project-1",
            "score": 85,
            "business_rank": 0,
            "group_label": "项目",
        }
    ]


async def test_build_party_filter_should_use_any_mode_for_all_scope(search_service):
    result = search_service._build_party_filter(
        scope_mode="all",
        effective_party_ids=["owner-1", "manager-1"],
    )

    assert result == PartyFilter(
        party_ids=["owner-1", "manager-1"],
        filter_mode="any",
        owner_party_ids=[],
        manager_party_ids=[],
    )
