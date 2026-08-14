"""Contract extraction workflow unit tests (payment_cycle / rent_terms mapping)."""

from datetime import date
from decimal import Decimal
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


@pytest.mark.asyncio
async def test_create_contract_builds_rent_terms_for_lease_with_monthly_rent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """确认月租金后必须生成 RentTerm，否则台账生成被跳过。

    回归（2026-08-14 验收 ACC-008）：generate_ledger_on_activation 以 rent_terms 为
    台账展开源，确认链路此前只写 lease_detail 不写 rent_terms，导致「人工确认补录
    租金条款 → 生成经营台账」闭环缺失（台账查询恒空）。
    """
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
    await workflow._create_contract(
        db=AsyncMock(),
        context={
            "project_id": "project-1",
            "revenue_mode": "lease",
            "contract_direction": "承租",
            "group_relation_type": "上游",
        },
        values={
            "contract_number": "HT-2026-001",
            "sign_date": date(2026, 8, 1),
            "effective_from": date(2026, 9, 1),
            "effective_to": date(2027, 8, 31),
            "monthly_rent": Decimal("68000"),
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

    _, kwargs = add_contract.call_args
    obj_in = kwargs["obj_in"]
    assert len(obj_in.rent_terms) == 1
    rent_term = obj_in.rent_terms[0]
    assert rent_term.start_date == date(2026, 9, 1)
    assert rent_term.end_date == date(2027, 8, 31)
    assert rent_term.monthly_rent == Decimal("68000")
    assert rent_term.sort_order == 1


@pytest.mark.asyncio
async def test_create_contract_skips_rent_terms_without_monthly_rent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """未确认月租金（如无租金条款的合同）不构造 RentTerm。"""
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
    await workflow._create_contract(
        db=AsyncMock(),
        context={
            "project_id": "project-1",
            "revenue_mode": "lease",
            "contract_direction": "承租",
            "group_relation_type": "上游",
        },
        values={
            "contract_number": "HT-2026-002",
            "sign_date": date(2026, 8, 1),
            "effective_from": date(2026, 9, 1),
            "effective_to": date(2027, 8, 31),
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

    _, kwargs = add_contract.call_args
    obj_in = kwargs["obj_in"]
    assert obj_in.rent_terms == []


@pytest.mark.asyncio
async def test_create_contract_normalizes_float_monthly_rent_into_rent_terms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """浮点月租金（如 LLM 返回）必须归一为 Decimal 并照常构造 RentTerm。

    回归（2026-08-14 两轴复核 D8）：此前以 isinstance(monthly_rent, Decimal) 类型门
    决定是否构造 rent_terms，非 Decimal 输入会静默跳过，导致台账生成被跳过且无任何
    报错。月租金必须归一化到 Decimal，任何可数值化输入都走同一条台账闭环。
    """
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
    await workflow._create_contract(
        db=AsyncMock(),
        context={
            "project_id": "project-1",
            "revenue_mode": "lease",
            "contract_direction": "承租",
            "group_relation_type": "上游",
        },
        values={
            "contract_number": "HT-2026-003",
            "sign_date": date(2026, 8, 1),
            "effective_from": date(2026, 9, 1),
            "effective_to": date(2027, 8, 31),
            "monthly_rent": 68000.0,
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

    _, kwargs = add_contract.call_args
    obj_in = kwargs["obj_in"]
    assert len(obj_in.rent_terms) == 1
    assert obj_in.rent_terms[0].monthly_rent == Decimal("68000")
    assert obj_in.lease_detail.rent_amount == Decimal("68000")


@pytest.mark.asyncio
async def test_create_contract_rejects_unparseable_monthly_rent_loudly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """不可解析的月租金必须显式失败（invalid_field_value），不得静默跳过台账。

    回归（2026-08-14 两轴复核 D8）：isinstance 类型门会把非法值静默当作「未确认
    月租金」处理；归一化后不可解析值必须报错，保证问题可见。
    """
    import src.services.document.contract_extraction_workflow as workflow_module
    from src.services.document.candidate_review import CandidateReviewError

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
    monkeypatch.setattr(
        workflow_module.contract_group_service, "add_contract_to_group", AsyncMock()
    )

    workflow = _build_workflow()
    with pytest.raises(CandidateReviewError) as exc_info:
        await workflow._create_contract(
            db=AsyncMock(),
            context={
                "project_id": "project-1",
                "revenue_mode": "lease",
                "contract_direction": "承租",
                "group_relation_type": "上游",
            },
            values={
                "contract_number": "HT-2026-004",
                "sign_date": date(2026, 8, 1),
                "effective_from": date(2026, 9, 1),
                "monthly_rent": "not-a-number",
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
    assert str(exc_info.value) == "invalid_field_value"
