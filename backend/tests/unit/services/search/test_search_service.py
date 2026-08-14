from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.crud.query_builder import PartyFilter
from src.services.search.service import SearchService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def search_service():
    return SearchService()


async def test_search_global_should_search_without_scope_restriction_when_party_ids_empty(
    search_service,
):
    """空 effective_party_ids 仅可能来自内建 admin/system_admin（unrestricted）。

    回归（2026-08-14 验收）：此前空主体范围被短路为恒空结果，管理员全局搜索 total
    恒为 0（数据范围中间件已对无范围普通用户失败关闭 403，能到服务层的空 ids 必为
    admin 豁免，REQ-SCH-003）。修复后必须照常收集并排序结果。
    """
    item = {
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
    }
    search_service._collect_results = AsyncMock(  # type: ignore[attr-defined]
        return_value=[item]
    )

    result = await search_service.search_global(
        db=AsyncMock(),
        query="测试",
        scope_mode="manager",
        effective_party_ids=[],
        is_unrestricted=True,
    )

    search_service._collect_results.assert_awaited_once()  # type: ignore[attr-defined]
    assert result["total"] == 1
    assert result["items"] == [item]


async def test_search_global_fails_closed_for_empty_scope_without_unrestricted(
    search_service,
) -> None:
    """空主体范围 + 非 unrestricted 必须显式拒绝，而不是按无范围搜索全部对象。

    回归（2026-08-14 两轴复核 D6）：此前空 effective_party_ids 无条件按无范围处理，
    只信任数据范围中间件已对普通用户失败关闭；若中间件失效，普通用户会看到全部对象。
    服务层必须自校验 is_unrestricted，不满足即抛 PermissionDeniedError（403）。
    """
    from src.core.exception_handler import PermissionDeniedError

    with pytest.raises(PermissionDeniedError):
        await search_service.search_global(
            db=AsyncMock(),
            query="测试",
            scope_mode="manager",
            effective_party_ids=[],
            is_unrestricted=False,
        )


async def test_build_party_filter_returns_none_for_empty_party_ids():
    assert (
        SearchService._build_party_filter(
            scope_mode="manager", effective_party_ids=[]
        )
        is None
    )
    assert (
        SearchService._build_party_filter(
            scope_mode="all", effective_party_ids=["p-1"]
        ).filter_mode
        == "any"
    )


async def test_apply_contract_group_scope_skips_filter_for_empty_party_ids():
    from sqlalchemy import select

    from src.models.contract_group import ContractGroup

    stmt = select(ContractGroup)
    out = SearchService._apply_contract_group_scope(
        stmt,
        scope_mode="manager",
        effective_party_ids=[],
    )
    compiled = str(out.compile(compile_kwargs={"literal_binds": True}))
    assert "operator_party_id IN" not in compiled
    assert "owner_party_id IN" not in compiled


async def test_search_assets_forwards_none_party_filter_when_unrestricted(search_service):
    from unittest.mock import patch

    with patch(
        "src.services.search.service.asset_crud.get_multi_with_search_async",
        AsyncMock(return_value=([], 0)),
    ) as mocked:
        await search_service._search_assets(
            db=AsyncMock(),
            query="测试",
            scope_mode="manager",
            party_filter=None,
        )

    assert mocked.await_args.kwargs["party_filter"] is None


async def test_search_projects_forwards_none_party_filter_when_unrestricted(search_service):
    from unittest.mock import patch

    with patch(
        "src.services.search.service.project_service.search_projects",
        AsyncMock(return_value={"items": [], "total": 0}),
    ) as mocked:
        await search_service._search_projects(
            db=AsyncMock(),
            query="测试",
            scope_mode="manager",
            party_filter=None,
        )

    assert mocked.await_args.kwargs["party_filter"] is None


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
        is_unrestricted=False,
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


async def test_collect_results_should_not_search_out_of_scope_property_certificates(
    search_service, monkeypatch
):
    """产权证为 Out of Scope，MVP 全局搜索不应访问产权证查询面。"""
    db = AsyncMock()
    monkeypatch.setattr(search_service, "_search_assets", AsyncMock(return_value=[]))
    monkeypatch.setattr(search_service, "_search_projects", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        search_service, "_search_contract_groups", AsyncMock(return_value=[])
    )
    monkeypatch.setattr(search_service, "_search_contracts", AsyncMock(return_value=[]))
    monkeypatch.setattr(search_service, "_search_customers", AsyncMock(return_value=[]))

    result = await search_service._collect_results(
        db=db,
        query="产权证",
        scope_mode="manager",
        effective_party_ids=["party-manager-1"],
    )

    assert result == []
    assert not hasattr(search_service, "_search_property_certificates")
    db.execute.assert_not_awaited()


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


async def test_search_contract_groups_should_use_contracts_and_agreements_label_and_contract_center_route(
    search_service,
):
    execute_result = SimpleNamespace(
        scalars=lambda: SimpleNamespace(
            all=lambda: [
                SimpleNamespace(
                    contract_group_id="group-1",
                    group_code="GRP-001",
                    revenue_mode=SimpleNamespace(name="LEASE"),
                    effective_from="2026-01-01",
                )
            ]
        )
    )
    db = SimpleNamespace(execute=AsyncMock(return_value=execute_result))

    result = await search_service._search_contract_groups(
        db=db,
        query="GRP",
        scope_mode="manager",
        effective_party_ids=["party-manager-1"],
    )

    assert result == [
        {
            "object_type": "contract_group",
            "object_id": "group-1",
            "title": "GRP-001",
            "subtitle": "LEASE",
            "summary": "2026-01-01",
            "keywords": ["group_code"],
            "route_path": "/contract-center/group-1",
            "score": 85,
            "business_rank": 40,
            "group_label": "合同与协议",
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
