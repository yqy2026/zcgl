"""
分层约束测试：合同生命周期 / RentTerm API（M2-T1）。
"""

from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Response

pytestmark = pytest.mark.api


def _module():
    return import_module("src.api.v1.contracts.contract_groups")


def _module_source() -> str:
    mod = _module()
    return Path(mod.__file__).read_text(encoding="utf-8")


def test_route_paths_cover_lifecycle_and_rent_term_endpoints() -> None:
    router = _module().router
    paths = {route.path for route in router.routes}  # type: ignore[attr-defined]
    required = {
        "/contract-groups/{group_id}/submit-review",
        "/contracts/{contract_id}/submit-review",
        "/contracts/{contract_id}/start-correction",
        "/contracts/{contract_id}/approve",
        "/contracts/{contract_id}/audit-logs",
        "/contracts/{contract_id}/reject",
        "/contracts/{contract_id}/expire",
        "/contracts/{contract_id}/terminate",
        "/contracts/{contract_id}/void",
        "/contracts/{contract_id}/rent-terms",
        "/contracts/{contract_id}/rent-terms/{rent_term_id}",
        "/contracts/{contract_id}/ledger",
        "/contracts/{contract_id}/ledger/batch-update-status",
    }
    assert required.issubset(paths), f"缺少路径: {required - paths}"


@pytest.mark.asyncio
async def test_submit_contract_review_delegates_to_service() -> None:
    mod = _module()
    endpoint = getattr(mod, "submit_contract_review", None)
    assert endpoint is not None, "submit_contract_review 路由尚未实现"

    user = MagicMock(id="user-001", username="tester")
    detail = MagicMock(contract_id="contract-001")
    response = Response()

    with (
        patch(
            "src.api.v1.contracts.contract_groups.contract_group_service.submit_review",
            new=AsyncMock(return_value=(MagicMock(contract_id="contract-001"), [])),
        ) as mock_submit_review,
        patch(
            "src.api.v1.contracts.contract_groups.contract_group_service.get_contract_detail",
            new=AsyncMock(return_value=detail),
        ) as mock_get_contract_detail,
    ):
        result = await endpoint(
            contract_id="contract-001",
            payload=None,
            response=response,
            db=AsyncMock(),
            current_user=user,
            _authz=None,
        )

    assert result is detail
    mock_submit_review.assert_awaited_once()
    mock_get_contract_detail.assert_awaited_once()


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
async def test_list_contract_audit_logs_delegates_to_service() -> None:
    mod = _module()
    endpoint = getattr(mod, "list_contract_audit_logs", None)
    assert endpoint is not None, "list_contract_audit_logs 路由尚未实现"

    logs = [
        MagicMock(
            log_id="log-001",
            contract_id="contract-001",
            action="status_change",
            old_status="draft",
            new_status="active",
            review_status_old=None,
            review_status_new=None,
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
            action="review",
            old_status=None,
            new_status=None,
            review_status_old="pending",
            review_status_new="approved",
            reason="通过",
            operator_id="user-002",
            operator_name="审核员",
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
    assert create_schema is not None, "ContractRentTermCreate 尚未实现"

    payload = create_schema(
        sort_order=1,
        start_date="2026-03-01",
        end_date="2026-03-31",
        monthly_rent="1000.00",
        management_fee="100.00",
        other_fees="50.00",
    )

    user = MagicMock(id="user-001")
    response = MagicMock(rent_term_id="term-001")

    with patch(
        "src.api.v1.contracts.contract_groups.contract_group_service.create_rent_term",
        new=AsyncMock(return_value=response),
    ) as mock_create_rent_term:
        result = await endpoint(
            contract_id="contract-001",
            payload=payload,
            db=AsyncMock(),
            current_user=user,
            _authz=None,
        )

    assert result is response
    mock_create_rent_term.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_contract_ledger_delegates_to_service() -> None:
    mod = _module()
    endpoint = getattr(mod, "get_contract_ledger", None)
    assert endpoint is not None, "get_contract_ledger 路由尚未实现"

    user = MagicMock(id="user-001")
    response = {"items": [{"entry_id": "entry-001"}], "total": 1, "offset": 0, "limit": 20}

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
            current_user=user,
            _authz=None,
        )

    assert result is response
    mock_query_ledger.assert_awaited_once()


@pytest.mark.asyncio
async def test_batch_update_contract_ledger_delegates_to_service() -> None:
    mod = _module()
    endpoint = getattr(mod, "batch_update_contract_ledger_status", None)
    assert endpoint is not None, "batch_update_contract_ledger_status 路由尚未实现"

    schema_module = import_module("src.schemas.contract_group")
    request_schema = getattr(schema_module, "ContractLedgerBatchUpdateRequest", None)
    assert request_schema is not None, "ContractLedgerBatchUpdateRequest 尚未实现"

    payload = request_schema(
        entry_ids=["entry-001", "entry-002"],
        payment_status="paid",
        paid_amount="2000.00",
        notes="批量回款",
    )

    user = MagicMock(id="user-001")
    response = [MagicMock(entry_id="entry-001"), MagicMock(entry_id="entry-002")]

    with patch(
        "src.api.v1.contracts.contract_groups.ledger_service_v2.batch_update_status",
        new=AsyncMock(return_value=response),
    ) as mock_batch_update:
        result = await endpoint(
            contract_id="contract-001",
            payload=payload,
            db=AsyncMock(),
            current_user=user,
            _authz=None,
        )

    assert result is response
    mock_batch_update.assert_awaited_once()
