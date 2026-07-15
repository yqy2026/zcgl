"""
分层约束测试：合同最小生命周期 / RentTerm API（M2-T1）。
"""

from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.api


def _module():
    return import_module("src.api.v1.contracts.contract_groups")


def _module_source() -> str:
    mod = _module()
    return Path(mod.__file__).read_text(encoding="utf-8")


def test_route_paths_cover_minimal_lifecycle_and_rent_term_endpoints() -> None:
    router = _module().router
    paths = {route.path for route in router.routes}  # type: ignore[attr-defined]
    required = {
        "/contracts/{contract_id}/start-correction",
        "/contracts/{contract_id}/finalize-correction",
        "/contracts/{contract_id}/audit-logs",
        "/contracts/{contract_id}/terminate",
        "/contracts/{contract_id}/void",
        "/contracts/{contract_id}/rent-terms",
        "/contracts/{contract_id}/rent-terms/{rent_term_id}",
        "/contracts/{contract_id}/ledger",
    }
    retired = {
        "/contract-groups/{group_id}/submit-review",
        "/contracts/{contract_id}/submit-review",
        "/contracts/{contract_id}/approve",
        "/contracts/{contract_id}/reject",
        "/contracts/{contract_id}/expire",
        "/contracts/{contract_id}/ledger/batch-update-status",
    }
    assert required.issubset(paths), f"缺少路径: {required - paths}"
    assert retired.isdisjoint(paths)
    source = _module_source()
    assert "submit_contract_review" not in source
    assert "approve_contract_review" not in source
    assert "reject_contract_review" not in source
    assert "expire_contract" not in source
    assert "contract_group_service.expire" not in source


@pytest.mark.asyncio
async def test_start_contract_correction_delegates_to_service() -> None:
    mod = _module()
    endpoint = getattr(mod, "start_contract_correction", None)
    assert endpoint is not None, "start_contract_correction 路由尚未实现"

    schema_module = import_module("src.schemas.contract_group")
    request_schema = getattr(schema_module, "ContractCorrectionStartRequest", None)
    assert request_schema is not None, "ContractCorrectionStartRequest 尚未实现"

    payload = request_schema(reason="租金条款调整")
    user = MagicMock(id="user-001", username="tester")
    detail = MagicMock(contract_id="contract-002")

    with (
        patch(
            "src.api.v1.contracts.contract_groups.contract_group_service.start_correction",
            new=AsyncMock(return_value=detail),
        ) as mock_start_correction,
        patch(
            "src.api.v1.contracts.contract_groups.contract_group_service.get_contract_detail",
            new=AsyncMock(return_value=detail),
        ) as mock_get_contract_detail,
    ):
        result = await endpoint(
            contract_id="contract-001",
            payload=payload,
            db=AsyncMock(),
            current_user=user,
            _authz=None,
        )

    assert result is detail
    mock_start_correction.assert_awaited_once()
    mock_get_contract_detail.assert_awaited_once()


@pytest.mark.asyncio
async def test_finalize_contract_correction_delegates_to_service() -> None:
    mod = _module()
    endpoint = getattr(mod, "finalize_contract_correction", None)
    assert endpoint is not None, "finalize_contract_correction 路由尚未实现"

    schema_module = import_module("src.schemas.contract_group")
    action_schema = getattr(schema_module, "ContractLifecycleAction", None)
    payload = action_schema(reason="纠错定稿")
    user = MagicMock(id="user-001", username="tester")
    contract = MagicMock(contract_id="contract-002")
    detail = MagicMock(contract_id="contract-002")

    with (
        patch(
            "src.api.v1.contracts.contract_groups.contract_group_service.finalize_correction",
            new=AsyncMock(return_value=contract),
        ) as mock_finalize,
        patch(
            "src.api.v1.contracts.contract_groups.contract_group_service.get_contract_detail",
            new=AsyncMock(return_value=detail),
        ) as mock_get_contract_detail,
    ):
        result = await endpoint(
            contract_id="contract-002",
            payload=payload,
            db=AsyncMock(),
            current_user=user,
            _authz=None,
        )

    assert result is detail
    mock_finalize.assert_awaited_once_with(
        AsyncMock.ANY if False else mock_finalize.await_args.args[0],
        contract_id="contract-002",
        reason="纠错定稿",
        current_user="user-001",
        operator_name="tester",
    )
    mock_get_contract_detail.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_contract_audit_logs_delegates_to_service() -> None:
    mod = _module()
    endpoint = getattr(mod, "list_contract_audit_logs", None)
    assert endpoint is not None, "list_contract_audit_logs 路由尚未实现"

    logs = [
        MagicMock(
            log_id="log-001",
            contract_id="contract-001",
            action="terminate",
            old_status="ACTIVE",
            new_status="TERMINATED",
            reason=None,
            operator_id="user-001",
            operator_name="测试用户",
            related_entry_id=None,
            context=None,
            created_at=datetime.now(UTC),
        ),
        MagicMock(
            log_id="log-002",
            contract_id="contract-001",
            action="finalize_correction",
            old_status="DRAFT",
            new_status="ACTIVE",
            reason="定稿",
            operator_id="user-002",
            operator_name="操作员",
            related_entry_id=None,
            context={"source": "unit-test"},
            created_at=datetime.now(UTC),
        ),
    ]

    with patch(
        "src.api.v1.contracts.contract_groups.contract_group_service.list_contract_audit_logs",
        new=AsyncMock(return_value=logs),
    ) as mock_list_logs:
        result = await endpoint(
            contract_id="contract-001",
            db=AsyncMock(),
            current_user=MagicMock(id="user-001"),
            _authz=None,
        )

    assert [item.log_id for item in result] == ["log-001", "log-002"]
    assert result[1].context == {"source": "unit-test"}
    mock_list_logs.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_contract_rent_term_delegates_to_service() -> None:
    mod = _module()
    endpoint = getattr(mod, "create_contract_rent_term", None)
    assert endpoint is not None, "create_contract_rent_term 路由尚未实现"

    schema_module = import_module("src.schemas.contract_group")
    create_schema = getattr(schema_module, "ContractRentTermCreate", None)
    payload = create_schema(
        sort_order=1,
        start_date="2026-03-01",
        end_date="2026-03-31",
        monthly_rent="1000.00",
        management_fee="100.00",
        other_fees="50.00",
    )

    response = MagicMock(rent_term_id="term-001")

    with patch(
        "src.api.v1.contracts.contract_groups.contract_group_service.create_rent_term",
        new=AsyncMock(return_value=response),
    ) as mock_create_rent_term:
        result = await endpoint(
            contract_id="contract-001",
            payload=payload,
            db=AsyncMock(),
            current_user=MagicMock(id="user-001"),
            _authz=None,
        )

    assert result is response
    mock_create_rent_term.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_contract_ledger_delegates_to_service() -> None:
    mod = _module()
    endpoint = getattr(mod, "get_contract_ledger", None)
    response = {
        "items": [{"entry_id": "entry-001"}],
        "total": 1,
        "offset": 0,
        "limit": 20,
    }

    with patch(
        "src.api.v1.contracts.contract_groups.ledger_service_v2.query_ledger",
        new=AsyncMock(return_value=response),
    ) as mock_query_ledger:
        result = await endpoint(
            contract_id="contract-001",
            year_month_start="2026-01",
            year_month_end="2026-03",
            offset=0,
            limit=20,
            db=AsyncMock(),
            current_user=MagicMock(id="user-001"),
            _authz=None,
        )

    assert result is response
    mock_query_ledger.assert_awaited_once()
