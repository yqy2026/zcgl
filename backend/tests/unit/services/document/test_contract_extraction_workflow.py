"""Contract extraction workflow unit tests (payment_cycle mapping)."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.services.document.contract_extraction_workflow import (
    ContractExtractionWorkflow,
)


def _build_workflow() -> ContractExtractionWorkflow:
    return ContractExtractionWorkflow(
        repository=Mock(),
        pipeline=Mock(),
        reviewer=Mock(),
        enricher=Mock(),
        lifecycle=Mock(),
    )


@pytest.mark.asyncio
async def test_create_contract_maps_payment_cycle_into_contract_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """付款周期经确认动作进入 ContractCreate（PRD §6.5 建议补全字段）。"""
    import src.services.document.contract_extraction_workflow as workflow_module

    monkeypatch.setattr(
        workflow_module.party_service,
        "get_party",
        AsyncMock(return_value=SimpleNamespace(code="P-001")),
    )
    monkeypatch.setattr(
        workflow_module.contract_group_service,
        "create_contract_group",
        AsyncMock(return_value=SimpleNamespace(contract_group_id="cg-1")),
    )
    monkeypatch.setattr(
        workflow_module.contract_group_service,
        "generate_group_code",
        AsyncMock(return_value="GC-2026-001"),
    )
    add_contract = AsyncMock(return_value=SimpleNamespace(contract_id="contract-1"))
    monkeypatch.setattr(
        workflow_module.contract_group_service, "add_contract_to_group", add_contract
    )

    workflow = _build_workflow()
    contract_id = await workflow._create_contract(
        db=AsyncMock(),
        context={
            "project_id": "project-1",
            "revenue_mode": "lease",
            "contract_direction": "出租",
            "group_relation_type": "下游",
        },
        values={
            "contract_number": "HT-2026-001",
            "sign_date": date(2026, 8, 1),
            "effective_from": date(2026, 8, 1),
            "payment_cycle": "季付",
        },
        party_ids={
            "operator_party_id": "op-1",
            "owner_party_id": "ow-1",
            "lessor_party_id": "lessor-1",
            "lessee_party_id": "lessee-1",
        },
        asset_ids=["asset-1"],
        current_user_id="user-1",
    )

    assert contract_id == "contract-1"
    _, kwargs = add_contract.call_args
    obj_in = kwargs["obj_in"]
    assert obj_in.payment_cycle == "季付"
