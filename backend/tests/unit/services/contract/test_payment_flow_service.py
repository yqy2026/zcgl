"""Unit tests for operational payment flow service."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.core.exception_handler import BusinessValidationError, ResourceNotFoundError

pytestmark = pytest.mark.asyncio


def _contract_ledger_target(
    *,
    entry_id: str = "entry-1",
    year_month: str = "2026-07",
    amount_due: Decimal = Decimal("1000.00"),
    paid_amount: Decimal = Decimal("0"),
    payment_status: str = "unpaid",
    ledger_views: list[str] | None = None,
    project_id: str | None = "project-1",
    owner_party_id: str | None = "owner-1",
    operator_party_id: str | None = "operator-1",
    currency_code: str = "CNY",
) -> SimpleNamespace:
    return SimpleNamespace(
        entry_id=entry_id,
        year_month=year_month,
        paid_amount=paid_amount,
        amount_due=amount_due,
        payment_status=payment_status,
        ledger_views=["terminal_collection"] if ledger_views is None else ledger_views,
        attributed_project_id=project_id,
        attributed_owner_party_id=owner_party_id,
        attributed_operator_party_id=operator_party_id,
        currency_code=currency_code,
        updated_at=None,
    )


def _service_fee_target(
    *,
    service_fee_entry_id: str = "service-fee-1",
    year_month: str = "2026-07",
    amount_due: Decimal = Decimal("1000.00"),
    paid_amount: Decimal = Decimal("0"),
    payment_status: str = "unpaid",
    project_id: str | None = "project-1",
    owner_party_id: str | None = "owner-1",
    operator_party_id: str | None = "operator-1",
    currency_code: str = "CNY",
) -> SimpleNamespace:
    return SimpleNamespace(
        service_fee_entry_id=service_fee_entry_id,
        year_month=year_month,
        paid_amount=paid_amount,
        amount_due=amount_due,
        payment_status=payment_status,
        attributed_project_id=project_id,
        attributed_owner_party_id=owner_party_id,
        attributed_operator_party_id=operator_party_id,
        currency_code=currency_code,
        updated_at=None,
    )


async def test_create_flow_rejects_non_positive_amount(mock_db) -> None:
    from src.services.contract.payment_flow_service import payment_flow_service

    with pytest.raises(
        BusinessValidationError, match="payment flow amount must be greater than 0"
    ):
        await payment_flow_service.create_flow(
            mock_db,
            registered_by="user-1",
            data={
                "flow_type": "terminal_rent_receipt",
                "occurred_on": "2026-07-01",
                "amount": Decimal("0"),
                "registered_by": "user-1",
            },
        )


@pytest.mark.parametrize(
    "flow_type",
    [
        "terminal_rent_receipt",
        "service_fee_receipt",
        "upstream_cost_payment",
    ],
)
async def test_create_flow_supports_all_operational_flow_types(
    mock_db,
    flow_type: str,
) -> None:
    from src.services.contract.payment_flow_service import payment_flow_service

    created_flow = SimpleNamespace(flow_id=f"flow-{flow_type}")
    with patch(
        "src.services.contract.payment_flow_service.contract_group_crud.create_payment_flow",
        new=AsyncMock(return_value=created_flow),
    ) as mock_create:
        result = await payment_flow_service.create_flow(
            mock_db,
            registered_by="user-1",
            data={
                "flow_type": flow_type,
                "occurred_on": "2026-07-01",
                "amount": "1000.00",
                "registered_by": "forged-user",
            },
            commit=False,
        )

    assert result == created_flow
    payload = mock_create.await_args.kwargs["data"]
    assert payload["flow_type"] == flow_type
    assert payload["amount"] == Decimal("1000.00")
    assert payload["registered_by"] == "user-1"
    assert payload["status"] == "active"
    mock_create.assert_awaited_once()


async def test_create_flow_rejects_unsupported_flow_type(mock_db) -> None:
    from src.services.contract.payment_flow_service import payment_flow_service

    with pytest.raises(BusinessValidationError, match="unsupported payment flow type"):
        await payment_flow_service.create_flow(
            mock_db,
            registered_by="user-1",
            data={
                "flow_type": "manual_adjustment",
                "occurred_on": "2026-07-01",
                "amount": "1000.00",
                "registered_by": "user-1",
            },
        )


async def test_save_allocations_requires_sum_to_match_flow_amount(mock_db) -> None:
    from src.services.contract.payment_flow_service import payment_flow_service

    flow = SimpleNamespace(
        flow_id="flow-1",
        flow_type="terminal_rent_receipt",
        amount=Decimal("1000.00"),
        status="active",
    )

    with (
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_payment_flow",
            new=AsyncMock(return_value=flow),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_ledger_entries_by_ids",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.list_payment_allocations_by_flow",
            new=AsyncMock(return_value=[]),
        ),
    ):
        with pytest.raises(
            BusinessValidationError,
            match="allocation amount total must equal payment flow amount",
        ):
            await payment_flow_service.save_allocations(
                mock_db,
                flow_id="flow-1",
                allocations=[
                    {
                        "target_type": "contract_ledger_entry",
                        "target_id": "entry-1",
                        "year_month": "2026-07",
                        "amount": Decimal("999.00"),
                    }
                ],
            )


async def test_save_allocations_persists_valid_contract_ledger_allocation(
    mock_db,
) -> None:
    from src.services.contract.payment_flow_service import payment_flow_service

    flow = SimpleNamespace(
        flow_id="flow-1",
        flow_type="terminal_rent_receipt",
        amount=Decimal("1000.00"),
        status="active",
    )
    ledger_entry = _contract_ledger_target(entry_id="entry-1")
    created_allocations = [SimpleNamespace(allocation_id="alloc-1")]

    with (
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_payment_flow",
            new=AsyncMock(return_value=flow),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_ledger_entries_by_ids",
            new=AsyncMock(return_value=[ledger_entry]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.list_payment_allocations_by_flow",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_service_fee_entries_by_ids",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.replace_payment_allocations",
            new=AsyncMock(return_value=created_allocations),
        ) as mock_replace,
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.sum_active_allocations_by_target",
            new=AsyncMock(return_value=Decimal("1000.00")),
        ),
    ):
        result = await payment_flow_service.save_allocations(
            mock_db,
            flow_id="flow-1",
            allocations=[
                {
                    "target_type": "contract_ledger_entry",
                    "target_id": "entry-1",
                    "year_month": "2026-07",
                    "amount": Decimal("1000.00"),
                }
            ],
        )

    assert result == created_allocations
    assert ledger_entry.paid_amount == Decimal("1000.00")
    assert ledger_entry.payment_status == "paid"
    mock_replace.assert_awaited_once()


async def test_save_allocations_persists_valid_upstream_cost_allocation(
    mock_db,
) -> None:
    from src.services.contract.payment_flow_service import payment_flow_service

    flow = SimpleNamespace(
        flow_id="flow-1",
        flow_type="upstream_cost_payment",
        amount=Decimal("1000.00"),
        status="active",
    )
    ledger_entry = _contract_ledger_target(
        entry_id="entry-1",
        ledger_views=["operator_cost"],
    )
    created_allocations = [SimpleNamespace(allocation_id="alloc-1")]

    with (
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_payment_flow",
            new=AsyncMock(return_value=flow),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_ledger_entries_by_ids",
            new=AsyncMock(return_value=[ledger_entry]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.list_payment_allocations_by_flow",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.replace_payment_allocations",
            new=AsyncMock(return_value=created_allocations),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.sum_active_allocations_by_target",
            new=AsyncMock(return_value=Decimal("1000.00")),
        ),
    ):
        result = await payment_flow_service.save_allocations(
            mock_db,
            flow_id="flow-1",
            allocations=[
                {
                    "target_type": "contract_ledger_entry",
                    "target_id": "entry-1",
                    "year_month": "2026-07",
                    "amount": Decimal("1000.00"),
                }
            ],
        )

    assert result == created_allocations
    assert ledger_entry.paid_amount == Decimal("1000.00")
    assert ledger_entry.payment_status == "paid"


async def test_save_allocations_persists_valid_service_fee_allocation(
    mock_db,
) -> None:
    from src.services.contract.payment_flow_service import payment_flow_service

    flow = SimpleNamespace(
        flow_id="flow-1",
        flow_type="service_fee_receipt",
        amount=Decimal("1000.00"),
        status="active",
    )
    service_fee_entry = _service_fee_target(service_fee_entry_id="service-fee-1")
    created_allocations = [SimpleNamespace(allocation_id="alloc-1")]

    with (
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_payment_flow",
            new=AsyncMock(return_value=flow),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_service_fee_entries_by_ids",
            new=AsyncMock(return_value=[service_fee_entry]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.list_payment_allocations_by_flow",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.replace_payment_allocations",
            new=AsyncMock(return_value=created_allocations),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.sum_active_allocations_by_target",
            new=AsyncMock(return_value=Decimal("1000.00")),
        ),
    ):
        result = await payment_flow_service.save_allocations(
            mock_db,
            flow_id="flow-1",
            allocations=[
                {
                    "target_type": "service_fee_ledger",
                    "target_id": "service-fee-1",
                    "year_month": "2026-07",
                    "amount": Decimal("1000.00"),
                }
            ],
        )

    assert result == created_allocations
    assert service_fee_entry.paid_amount == Decimal("1000.00")
    assert service_fee_entry.payment_status == "paid"


async def test_save_allocations_rejects_terminal_receipt_outside_collection_view(
    mock_db,
) -> None:
    from src.services.contract.payment_flow_service import payment_flow_service

    flow = SimpleNamespace(
        flow_id="flow-1",
        flow_type="terminal_rent_receipt",
        amount=Decimal("1000.00"),
        status="active",
    )
    operator_cost_entry = _contract_ledger_target(
        entry_id="entry-1",
        ledger_views=["operator_cost"],
    )

    with (
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_payment_flow",
            new=AsyncMock(return_value=flow),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_ledger_entries_by_ids",
            new=AsyncMock(return_value=[operator_cost_entry]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.list_payment_allocations_by_flow",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.replace_payment_allocations",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.sum_active_allocations_by_target",
            new=AsyncMock(return_value=Decimal("1000.00")),
        ),
    ):
        with pytest.raises(
            BusinessValidationError,
            match="terminal rent receipt can only allocate to terminal collection",
        ):
            await payment_flow_service.save_allocations(
                mock_db,
                flow_id="flow-1",
                allocations=[
                    {
                        "target_type": "contract_ledger_entry",
                        "target_id": "entry-1",
                        "year_month": "2026-07",
                        "amount": Decimal("1000.00"),
                    }
                ],
            )


async def test_save_allocations_rejects_upstream_payment_outside_cost_view(
    mock_db,
) -> None:
    from src.services.contract.payment_flow_service import payment_flow_service

    flow = SimpleNamespace(
        flow_id="flow-1",
        flow_type="upstream_cost_payment",
        amount=Decimal("1000.00"),
        status="active",
    )
    collection_entry = _contract_ledger_target(
        entry_id="entry-1",
        ledger_views=["terminal_collection"],
    )

    with (
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_payment_flow",
            new=AsyncMock(return_value=flow),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_ledger_entries_by_ids",
            new=AsyncMock(return_value=[collection_entry]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.list_payment_allocations_by_flow",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.replace_payment_allocations",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.sum_active_allocations_by_target",
            new=AsyncMock(return_value=Decimal("1000.00")),
        ),
    ):
        with pytest.raises(
            BusinessValidationError,
            match="upstream cost payment can only allocate to operator cost",
        ):
            await payment_flow_service.save_allocations(
                mock_db,
                flow_id="flow-1",
                allocations=[
                    {
                        "target_type": "contract_ledger_entry",
                        "target_id": "entry-1",
                        "year_month": "2026-07",
                        "amount": Decimal("1000.00"),
                    }
                ],
            )


async def test_save_allocations_rejects_mixed_project_party_or_currency_scope(
    mock_db,
) -> None:
    from src.services.contract.payment_flow_service import payment_flow_service

    flow = SimpleNamespace(
        flow_id="flow-1",
        flow_type="terminal_rent_receipt",
        amount=Decimal("1000.00"),
        status="active",
    )
    first_entry = _contract_ledger_target(entry_id="entry-1")
    second_entry = _contract_ledger_target(
        entry_id="entry-2",
        project_id="project-2",
    )

    with (
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_payment_flow",
            new=AsyncMock(return_value=flow),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_ledger_entries_by_ids",
            new=AsyncMock(return_value=[first_entry, second_entry]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.list_payment_allocations_by_flow",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.replace_payment_allocations",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.sum_active_allocations_by_target",
            new=AsyncMock(return_value=Decimal("500.00")),
        ),
    ):
        with pytest.raises(
            BusinessValidationError,
            match="allocations must share the same project, owner, operator, and currency",
        ):
            await payment_flow_service.save_allocations(
                mock_db,
                flow_id="flow-1",
                allocations=[
                    {
                        "target_type": "contract_ledger_entry",
                        "target_id": "entry-1",
                        "year_month": "2026-07",
                        "amount": Decimal("500.00"),
                    },
                    {
                        "target_type": "contract_ledger_entry",
                        "target_id": "entry-2",
                        "year_month": "2026-07",
                        "amount": Decimal("500.00"),
                    },
                ],
            )


async def test_save_allocations_hides_out_of_scope_target(mock_db) -> None:
    from src.crud.query_builder import PartyFilter
    from src.services.contract.payment_flow_service import payment_flow_service

    flow = SimpleNamespace(
        flow_id="flow-1",
        flow_type="terminal_rent_receipt",
        amount=Decimal("1000.00"),
        status="active",
    )
    entry = _contract_ledger_target(
        entry_id="entry-1",
        owner_party_id="owner-1",
        operator_party_id="operator-1",
    )
    party_filter = PartyFilter(
        party_ids=["other-owner"],
        filter_mode="owner",
        owner_party_ids=["other-owner"],
    )

    with (
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_payment_flow",
            new=AsyncMock(return_value=flow),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_ledger_entries_by_ids",
            new=AsyncMock(return_value=[entry]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.list_payment_allocations_by_flow",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.replace_payment_allocations",
            new=AsyncMock(),
        ) as mock_replace,
    ):
        with pytest.raises(ResourceNotFoundError):
            await payment_flow_service.save_allocations(
                mock_db,
                flow_id="flow-1",
                allocations=[
                    {
                        "target_type": "contract_ledger_entry",
                        "target_id": "entry-1",
                        "year_month": "2026-07",
                        "amount": Decimal("1000.00"),
                    }
                ],
                current_user_id="user-1",
                party_filter=party_filter,
            )

    mock_replace.assert_not_awaited()


async def test_save_allocations_resets_removed_target_paid_amount(mock_db) -> None:
    from src.services.contract.payment_flow_service import payment_flow_service

    flow = SimpleNamespace(
        flow_id="flow-1",
        flow_type="terminal_rent_receipt",
        amount=Decimal("1000.00"),
        status="active",
    )
    old_entry = _contract_ledger_target(
        entry_id="entry-old",
        paid_amount=Decimal("1000.00"),
    )
    new_entry = _contract_ledger_target(entry_id="entry-new")
    old_allocation = SimpleNamespace(
        target_type="contract_ledger_entry",
        target_id="entry-old",
        year_month="2026-07",
        amount=Decimal("1000.00"),
    )

    async def _sum_by_target(db, *, target_type, target_id):  # noqa: ANN001
        return Decimal("1000.00") if target_id == "entry-new" else Decimal("0")

    with (
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_payment_flow",
            new=AsyncMock(return_value=flow),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.list_payment_allocations_by_flow",
            new=AsyncMock(return_value=[old_allocation]),
        ) as mock_existing_allocations,
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_ledger_entries_by_ids",
            new=AsyncMock(return_value=[old_entry, new_entry]),
        ) as mock_get_ledger_entries,
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_service_fee_entries_by_ids",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.replace_payment_allocations",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.sum_active_allocations_by_target",
            new=_sum_by_target,
        ),
    ):
        await payment_flow_service.save_allocations(
            mock_db,
            flow_id="flow-1",
            allocations=[
                {
                    "target_type": "contract_ledger_entry",
                    "target_id": "entry-new",
                    "year_month": "2026-07",
                    "amount": Decimal("1000.00"),
                }
            ],
        )

    assert old_entry.paid_amount == Decimal("0")
    assert old_entry.payment_status == "unpaid"
    assert new_entry.paid_amount == Decimal("1000.00")
    assert new_entry.payment_status == "paid"
    mock_existing_allocations.assert_awaited_once_with(mock_db, flow_id="flow-1")
    assert set(mock_get_ledger_entries.await_args.kwargs["entry_ids"]) == {
        "entry-old",
        "entry-new",
    }
    assert mock_get_ledger_entries.await_args.kwargs["for_update"] is True


async def test_void_flow_removes_its_allocations_from_paid_totals(mock_db) -> None:
    """作废必须在同一事务内锁定流水，并立即重算受影响台账。"""
    from src.services.contract.payment_flow_service import payment_flow_service

    flow = SimpleNamespace(
        flow_id="flow-1",
        flow_type="terminal_rent_receipt",
        amount=Decimal("1000.00"),
        status="active",
        status_changed_by=None,
        status_changed_at=None,
        status_change_reason=None,
    )
    allocation = SimpleNamespace(
        target_type="contract_ledger_entry",
        target_id="entry-1",
        year_month="2026-07",
        amount=Decimal("1000.00"),
    )
    entry = _contract_ledger_target(
        entry_id="entry-1",
        paid_amount=Decimal("1000.00"),
        payment_status="paid",
    )

    with (
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_payment_flow",
            new=AsyncMock(return_value=flow),
        ) as mock_get_flow,
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.list_payment_allocations_by_flow",
            new=AsyncMock(return_value=[allocation]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_ledger_entries_by_ids",
            new=AsyncMock(return_value=[entry]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.sum_active_allocations_by_target",
            new=AsyncMock(return_value=Decimal("0")),
        ),
    ):
        result = await payment_flow_service.void_flow(
            mock_db,
            flow_id="flow-1",
            reason="重复登记",
            actor_id="user-1",
        )

    assert result is flow
    assert flow.status == "voided"
    assert flow.status_changed_by == "user-1"
    assert flow.status_change_reason == "重复登记"
    assert flow.status_changed_at is not None
    assert entry.paid_amount == Decimal("0")
    assert entry.payment_status == "unpaid"
    mock_get_flow.assert_awaited_once_with(mock_db, flow_id="flow-1", for_update=True)
    mock_db.commit.assert_awaited_once()


async def test_void_flow_requires_a_nonblank_actor(mock_db) -> None:
    """审计操作人为空时必须在读取或修改流水前失败。"""
    from src.services.contract.payment_flow_service import payment_flow_service

    with pytest.raises(
        BusinessValidationError,
        match="payment flow lifecycle actor is required",
    ):
        await payment_flow_service.void_flow(
            mock_db,
            flow_id="flow-1",
            reason="重复登记",
            actor_id="  ",
        )

    mock_db.commit.assert_not_awaited()
    mock_db.rollback.assert_not_awaited()


async def test_correct_flow_replaces_active_flow_in_one_transaction(mock_db) -> None:
    """更正必须保留原流水，并以单次提交创建可追溯的新流水。"""
    from src.services.contract.payment_flow_service import payment_flow_service

    original = SimpleNamespace(
        flow_id="flow-original",
        flow_type="terminal_rent_receipt",
        amount=Decimal("1000.00"),
        status="active",
        status_changed_by=None,
        status_changed_at=None,
        status_change_reason=None,
    )
    replacement = SimpleNamespace(
        flow_id="flow-replacement",
        flow_type="terminal_rent_receipt",
        amount=Decimal("900.00"),
        status="active",
        corrected_from_flow_id="flow-original",
    )
    original_allocation = SimpleNamespace(
        target_type="contract_ledger_entry",
        target_id="entry-1",
        year_month="2026-07",
        amount=Decimal("1000.00"),
    )
    entry = _contract_ledger_target(
        entry_id="entry-1",
        amount_due=Decimal("1000.00"),
        paid_amount=Decimal("1000.00"),
        payment_status="paid",
    )

    with (
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_payment_flow",
            new=AsyncMock(return_value=original),
        ) as mock_get_flow,
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.list_payment_allocations_by_flow",
            new=AsyncMock(return_value=[original_allocation]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_ledger_entries_by_ids",
            new=AsyncMock(return_value=[entry]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.create_payment_flow",
            new=AsyncMock(return_value=replacement),
        ) as mock_create,
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.replace_payment_allocations",
            new=AsyncMock(
                return_value=[SimpleNamespace(allocation_id="allocation-new")]
            ),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.sum_active_allocations_by_target",
            new=AsyncMock(return_value=Decimal("900.00")),
        ),
    ):
        result = await payment_flow_service.correct_flow(
            mock_db,
            flow_id="flow-original",
            reason="金额录入错误",
            actor_id="user-1",
            replacement_data={
                "flow_type": "terminal_rent_receipt",
                "occurred_on": "2026-07-02",
                "amount": Decimal("900.00"),
            },
            allocations=[
                {
                    "target_type": "contract_ledger_entry",
                    "target_id": "entry-1",
                    "year_month": "2026-07",
                    "amount": Decimal("900.00"),
                }
            ],
        )

    assert result is replacement
    assert original.status == "corrected"
    assert original.status_changed_by == "user-1"
    assert original.status_change_reason == "金额录入错误"
    assert original.status_changed_at is not None
    assert entry.paid_amount == Decimal("900.00")
    assert entry.payment_status == "partial"
    assert mock_get_flow.await_args_list[0].kwargs["for_update"] is True
    assert mock_create.await_args.kwargs["data"]["corrected_from_flow_id"] == (
        "flow-original"
    )
    assert mock_create.await_args.kwargs["commit"] is False
    mock_db.commit.assert_awaited_once()
    mock_db.rollback.assert_not_awaited()


async def test_correct_flow_rejects_moving_fact_to_another_scope(mock_db) -> None:
    """A correction fixes a fact; it must not move that fact to another scope."""
    from src.services.contract.payment_flow_service import payment_flow_service

    original = SimpleNamespace(
        flow_id="flow-original",
        flow_type="terminal_rent_receipt",
        amount=Decimal("1000.00"),
        status="active",
        status_changed_by=None,
        status_changed_at=None,
        status_change_reason=None,
    )
    original_allocation = SimpleNamespace(
        target_type="contract_ledger_entry",
        target_id="entry-original",
        year_month="2026-07",
        amount=Decimal("1000.00"),
    )
    original_entry = _contract_ledger_target(entry_id="entry-original")
    other_project_entry = _contract_ledger_target(
        entry_id="entry-other-project",
        project_id="project-2",
    )

    with (
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_payment_flow",
            new=AsyncMock(return_value=original),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.list_payment_allocations_by_flow",
            new=AsyncMock(return_value=[original_allocation]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_ledger_entries_by_ids",
            new=AsyncMock(return_value=[original_entry, other_project_entry]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.create_payment_flow",
            new=AsyncMock(),
        ) as mock_create,
    ):
        with pytest.raises(
            BusinessValidationError,
            match="replacement allocations must remain in original project, owner, operator, and currency scope",
        ):
            await payment_flow_service.correct_flow(
                mock_db,
                flow_id="flow-original",
                reason="wrong target",
                actor_id="user-1",
                replacement_data={
                    "flow_type": "terminal_rent_receipt",
                    "occurred_on": "2026-07-02",
                    "amount": Decimal("1000.00"),
                },
                allocations=[
                    {
                        "target_type": "contract_ledger_entry",
                        "target_id": "entry-other-project",
                        "year_month": "2026-07",
                        "amount": Decimal("1000.00"),
                    }
                ],
            )

    mock_create.assert_not_awaited()
    mock_db.commit.assert_not_awaited()
    mock_db.rollback.assert_awaited_once()


async def test_correct_flow_locks_original_and_replacement_targets_in_stable_order(
    mock_db,
) -> None:
    """A single sorted lock set prevents opposite corrections from deadlocking."""
    from src.services.contract.payment_flow_service import payment_flow_service

    original = SimpleNamespace(
        flow_id="flow-original",
        flow_type="terminal_rent_receipt",
        amount=Decimal("1000.00"),
        status="active",
        status_changed_by=None,
        status_changed_at=None,
        status_change_reason=None,
    )
    replacement = SimpleNamespace(
        flow_id="flow-replacement",
        flow_type="terminal_rent_receipt",
        amount=Decimal("1000.00"),
        status="active",
    )
    original_allocation = SimpleNamespace(
        target_type="contract_ledger_entry",
        target_id="entry-z",
        year_month="2026-07",
        amount=Decimal("1000.00"),
    )
    original_entry = _contract_ledger_target(entry_id="entry-z")
    replacement_entry = _contract_ledger_target(entry_id="entry-a")

    with (
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_payment_flow",
            new=AsyncMock(return_value=original),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.list_payment_allocations_by_flow",
            new=AsyncMock(return_value=[original_allocation]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_ledger_entries_by_ids",
            new=AsyncMock(return_value=[replacement_entry, original_entry]),
        ) as mock_get_entries,
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.create_payment_flow",
            new=AsyncMock(return_value=replacement),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.replace_payment_allocations",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.sum_active_allocations_by_target",
            new=AsyncMock(return_value=Decimal("1000.00")),
        ),
    ):
        await payment_flow_service.correct_flow(
            mock_db,
            flow_id="flow-original",
            reason="wrong target",
            actor_id="user-1",
            replacement_data={
                "flow_type": "terminal_rent_receipt",
                "occurred_on": "2026-07-02",
                "amount": Decimal("1000.00"),
            },
            allocations=[
                {
                    "target_type": "contract_ledger_entry",
                    "target_id": "entry-a",
                    "year_month": "2026-07",
                    "amount": Decimal("1000.00"),
                }
            ],
        )

    mock_get_entries.assert_awaited_once_with(
        mock_db,
        entry_ids=["entry-a", "entry-z"],
        for_update=True,
    )


async def test_correct_flow_rejects_changing_payment_flow_type(mock_db) -> None:
    """Changing receipt/payment semantics requires a separate fact, not correction."""
    from src.services.contract.payment_flow_service import payment_flow_service

    original = SimpleNamespace(
        flow_id="flow-original",
        flow_type="terminal_rent_receipt",
        amount=Decimal("1000.00"),
        status="active",
    )
    with patch(
        "src.services.contract.payment_flow_service.contract_group_crud.get_payment_flow",
        new=AsyncMock(return_value=original),
    ):
        with pytest.raises(
            BusinessValidationError,
            match="replacement payment flow type must match original payment flow type",
        ):
            await payment_flow_service.correct_flow(
                mock_db,
                flow_id="flow-original",
                reason="wrong type",
                actor_id="user-1",
                replacement_data={
                    "flow_type": "upstream_cost_payment",
                    "occurred_on": "2026-07-02",
                    "amount": Decimal("1000.00"),
                },
                allocations=[],
            )

    mock_db.commit.assert_not_awaited()
    mock_db.rollback.assert_awaited_once()


@pytest.mark.parametrize("status", ["voided", "corrected"])
async def test_void_flow_rejects_repeated_terminal_action(
    mock_db,
    status: str,
) -> None:
    from src.services.contract.payment_flow_service import payment_flow_service

    flow = SimpleNamespace(flow_id="flow-1", status=status)
    with patch(
        "src.services.contract.payment_flow_service.contract_group_crud.get_payment_flow",
        new=AsyncMock(return_value=flow),
    ):
        with pytest.raises(
            BusinessValidationError,
            match="only active payment flows can be voided",
        ):
            await payment_flow_service.void_flow(
                mock_db,
                flow_id="flow-1",
                reason="重复操作",
                actor_id="user-1",
            )

    mock_db.commit.assert_not_awaited()
    mock_db.rollback.assert_awaited_once()


async def test_correct_flow_rejects_voided_flow(mock_db) -> None:
    from src.services.contract.payment_flow_service import payment_flow_service

    flow = SimpleNamespace(flow_id="flow-1", status="voided")
    with patch(
        "src.services.contract.payment_flow_service.contract_group_crud.get_payment_flow",
        new=AsyncMock(return_value=flow),
    ):
        with pytest.raises(
            BusinessValidationError,
            match="only active payment flows can be corrected",
        ):
            await payment_flow_service.correct_flow(
                mock_db,
                flow_id="flow-1",
                reason="尝试更正",
                actor_id="user-1",
                replacement_data={
                    "flow_type": "terminal_rent_receipt",
                    "occurred_on": "2026-07-02",
                    "amount": Decimal("900.00"),
                },
                allocations=[],
            )

    mock_db.commit.assert_not_awaited()
    mock_db.rollback.assert_awaited_once()


async def test_correct_flow_rejects_copying_vouchers_from_original(mock_db) -> None:
    """更正后继不能引用仍归原流水所有的凭证元数据。"""
    from src.services.contract.payment_flow_service import payment_flow_service

    with pytest.raises(
        BusinessValidationError,
        match="replacement voucher attachments must be uploaded after correction",
    ):
        await payment_flow_service.correct_flow(
            mock_db,
            flow_id="flow-original",
            reason="金额错误",
            actor_id="user-1",
            replacement_data={
                "flow_type": "terminal_rent_receipt",
                "occurred_on": "2026-07-02",
                "amount": Decimal("900.00"),
                "voucher_attachment_ids": ["attachment-original"],
            },
            allocations=[],
        )

    mock_db.commit.assert_not_awaited()
    mock_db.rollback.assert_not_awaited()


async def test_correct_flow_rolls_back_when_replacement_allocation_fails(
    mock_db,
) -> None:
    """新分摊失败时，原流水的终态变更不得提交。"""
    from src.services.contract.payment_flow_service import payment_flow_service

    original = SimpleNamespace(
        flow_id="flow-original",
        flow_type="terminal_rent_receipt",
        status="active",
        status_changed_by=None,
        status_changed_at=None,
        status_change_reason=None,
    )
    replacement = SimpleNamespace(flow_id="flow-replacement")
    original_allocation = SimpleNamespace(
        target_type="contract_ledger_entry",
        target_id="entry-1",
        year_month="2026-07",
        amount=Decimal("1000.00"),
    )
    entry = _contract_ledger_target(entry_id="entry-1")

    with (
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_payment_flow",
            new=AsyncMock(return_value=original),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.list_payment_allocations_by_flow",
            new=AsyncMock(return_value=[original_allocation]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_ledger_entries_by_ids",
            new=AsyncMock(return_value=[entry]),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.create_payment_flow",
            new=AsyncMock(return_value=replacement),
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.replace_payment_allocations",
            new=AsyncMock(side_effect=BusinessValidationError("allocation failed")),
        ),
    ):
        with pytest.raises(BusinessValidationError, match="allocation failed"):
            await payment_flow_service.correct_flow(
                mock_db,
                flow_id="flow-original",
                reason="金额错误",
                actor_id="user-1",
                replacement_data={
                    "flow_type": "terminal_rent_receipt",
                    "occurred_on": "2026-07-02",
                    "amount": Decimal("900.00"),
                },
                allocations=[
                    {
                        "target_type": "contract_ledger_entry",
                        "target_id": "entry-1",
                        "year_month": "2026-07",
                        "amount": Decimal("900.00"),
                    }
                ],
            )

    mock_db.commit.assert_not_awaited()
    mock_db.rollback.assert_awaited_once()
