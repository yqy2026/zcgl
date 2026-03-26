"""
分层约束测试：contract_groups 路由（REQ-RNT-001 M3）

验证：
  1. 路由模块不直接调用 CRUD（不绕过 Service 层）
  2. 全部端点接入 require_authz
  3. group_code 由 Service 生成（不在 API 层硬编码）
  4. 创建 / 详情 / 列表 / 删除端点委托给 contract_group_service
  5. 错误 group_id 返回 404（ResourceNotFoundError 被正确处理）
  6. group_id 路径与请求体不一致时返回 422
"""

from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.api

# ─────────────────────── 路由源码读取 ─────────────────────────────────────


def _module_source() -> str:
    from src.api.v1.contracts import contract_groups as mod

    return Path(mod.__file__).read_text(encoding="utf-8")


# ─────────────────────── 分层约束（静态检查）─────────────────────────────


def test_module_should_not_import_crud_directly() -> None:
    """API 模块不得在任何位置直接引用 CRUD 单例（contract_group_crud / contract_crud）。"""
    source = _module_source()
    assert "contract_group_crud" not in source, "API 层不得直接使用 contract_group_crud"
    assert "contract_crud" not in source, "API 层不得直接使用 contract_crud"


def test_module_should_use_require_authz() -> None:
    """所有端点必须接入 require_authz。"""
    source = _module_source()
    assert "require_authz" in source
    assert "AuthzContext" in source


def test_module_should_use_party_service_for_code_generation() -> None:
    """创建合同组时必须通过 party_service 获取 operator_party_code。"""
    source = _module_source()
    assert "party_service" in source
    assert "generate_group_code" in source


def test_module_calls_contract_group_service_for_all_mutations() -> None:
    """创建 / 更新 / 删除 / 列表 / 合同删除端点均委托 contract_group_service。"""
    source = _module_source()
    assert "contract_group_service.create_contract_group" in source
    assert "contract_group_service.update_contract_group" in source
    assert "contract_group_service.soft_delete_group" in source
    assert "contract_group_service.add_contract_to_group" in source
    assert "contract_group_service.list_contracts_in_group" in source
    assert "contract_group_service.soft_delete_contract" in source


def test_all_write_endpoints_check_base_business_error() -> None:
    """写操作端点必须有 BaseBusinessError re-raise 逻辑。"""
    source = _module_source()
    assert "except BaseBusinessError:" in source
    assert "raise" in source


# ─────────────────────── 端点行为测试（mock service）────────────────────────


def _mock_group_detail(group_id: str = "grp-001") -> MagicMock:
    detail = MagicMock()
    detail.contract_group_id = group_id
    detail.group_code = "GRP-TEST0001-202603-0001"
    detail.derived_status = "筹备中"
    detail.contracts = []
    detail.upstream_contract_ids = []
    detail.downstream_contract_ids = []
    detail.model_dump = lambda: {
        "contract_group_id": group_id,
        "group_code": detail.group_code,
        "derived_status": detail.derived_status,
        "contracts": [],
        "upstream_contract_ids": [],
        "downstream_contract_ids": [],
    }
    return detail


async def _mock_get_party(db: ANY, *, party_id: str):  # noqa: ANN001
    party = MagicMock()
    party.id = party_id
    party.code = "TESTPARTY"
    return party


@pytest.mark.asyncio
async def test_create_contract_group_delegates_to_service(
    client: ANY,
) -> None:
    """POST /contract-groups 成功路径：调用了 party_service 和 contract_group_service。"""
    mock_create = AsyncMock(return_value=MagicMock(contract_group_id="grp-001"))
    mock_detail = AsyncMock(side_effect=Exception("测试终止"))

    with (
        patch(
            "src.api.v1.contracts.contract_groups.party_service.get_party",
            new=_mock_get_party,
        ),
        patch(
            "src.api.v1.contracts.contract_groups.contract_group_service.generate_group_code",
            new_callable=AsyncMock,
            return_value="GRP-TEST0001-202603-0001",
        ),
        patch(
            "src.api.v1.contracts.contract_groups.contract_group_service.create_contract_group",
            new=mock_create,
        ),
        patch(
            "src.api.v1.contracts.contract_groups.contract_group_service.get_group_detail",
            new=mock_detail,
        ),
    ):
        payload = {
            "revenue_mode": "lease",
            "operator_party_id": "party-operator-001",
            "owner_party_id": "party-owner-001",
            "effective_from": "2026-01-01",
            "settlement_rule": {
                "version": "v1",
                "cycle": "月付",
                "settlement_mode": "固定",
                "amount_rule": {"base": 1000},
                "payment_rule": {"due_day": 10},
            },
        }
        client.post("/api/v1/contract-groups", json=payload)
        # 只要 create_contract_group 被调用就证明路由委托正确
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_create_contract_group_404_when_party_missing(
    client: ANY,
) -> None:
    """POST /contract-groups 当 operator_party 不存在时返回 404。"""
    with patch(
        "src.api.v1.contracts.contract_groups.party_service.get_party",
        new_callable=AsyncMock,
        return_value=None,
    ):
        payload = {
            "revenue_mode": "lease",
            "operator_party_id": "nonexistent-party",
            "owner_party_id": "party-owner-001",
            "effective_from": "2026-01-01",
            "settlement_rule": {
                "version": "v1",
                "cycle": "月付",
                "settlement_mode": "固定",
                "amount_rule": {},
                "payment_rule": {},
            },
        }
        resp = client.post("/api/v1/contract-groups", json=payload)
        assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_create_contract_group_404_when_owner_party_missing(
    client: ANY,
) -> None:
    """POST /contract-groups 当 owner_party 不存在时返回 404。"""

    async def _get_party_with_missing_owner(db: ANY, *, party_id: str):  # noqa: ANN001
        if party_id == "nonexistent-owner-party":
            return None
        party = MagicMock()
        party.id = party_id
        party.code = "TESTPARTY"
        return party

    with patch(
        "src.api.v1.contracts.contract_groups.party_service.get_party",
        new=_get_party_with_missing_owner,
    ):
        payload = {
            "revenue_mode": "lease",
            "operator_party_id": "party-operator-001",
            "owner_party_id": "nonexistent-owner-party",
            "effective_from": "2026-01-01",
            "settlement_rule": {
                "version": "v1",
                "cycle": "月付",
                "settlement_mode": "固定",
                "amount_rule": {},
                "payment_rule": {},
            },
        }
        resp = client.post("/api/v1/contract-groups", json=payload)
        assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_get_contract_group_route_exists(
    client: ANY,
) -> None:
    """GET /contract-groups/{id} 路由存在，未找到时返回 404。"""
    from src.core.exception_handler import ResourceNotFoundError

    with (
        patch(
            "src.api.v1.contracts.contract_groups.contract_group_service.get_group_detail",
            new_callable=AsyncMock,
            side_effect=ResourceNotFoundError("合同组", "grp-notexist"),
        ),
        patch(
            "src.middleware.auth.RBACService.is_admin",
            new=AsyncMock(return_value=True),
        ),
    ):
        resp = client.get(
            "/api/v1/contract-groups/grp-notexist",
            headers={"X-Perspective": "manager"},
        )
        # service 抛出 ResourceNotFoundError 应被映射为 404
        assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_add_contract_group_id_mismatch_returns_422(
    client: ANY,
) -> None:
    """POST /contract-groups/{group_id}/contracts 路径 id 与 body 不一致时 422。

    必须使用正确的枚举 value（"出租"/"上游"）才能通过 Pydantic 校验，
    确保 422 是由 group_id 不一致触发，而非 schema 校验失败。
    """
    payload = {
        "contract_group_id": "different-group-id",  # 故意与路径 id 不同
        "contract_number": "HT-2026-0001",
        "contract_direction": "出租",    # ContractDirection.LESSOR.value
        "group_relation_type": "上游",   # GroupRelationType.UPSTREAM.value
        "lessor_party_id": "party-a",
        "lessee_party_id": "party-b",
        "effective_from": "2026-01-01",
    }
    resp = client.post(
        "/api/v1/contract-groups/correct-group-id/contracts", json=payload
    )
    assert resp.status_code == 422, resp.text


def test_route_paths_cover_all_spec_endpoints() -> None:
    """路由表应覆盖技术方案要求的全部9条端点。"""
    from src.api.v1.contracts.contract_groups import router

    paths = {r.path for r in router.routes}  # type: ignore[attr-defined]
    required = {
        "/contract-groups",
        "/contract-groups/{group_id}",
        "/contract-groups/{group_id}/contracts",
        "/contracts/{contract_id}",
    }
    assert required.issubset(paths), f"缺少路径: {required - paths}"
