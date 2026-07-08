"""Unit tests for operational payment flow service."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.core.exception_handler import BusinessValidationError

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
            data={
                "flow_type": flow_type,
                "occurred_on": "2026-07-01",
                "amount": "1000.00",
                "registered_by": "user-1",
            },
            commit=False,
        )

    assert result == created_flow
    payload = mock_create.await_args.kwargs["data"]
    assert payload["flow_type"] == flow_type
    assert payload["amount"] == Decimal("1000.00")
    assert payload["status"] == "active"
    mock_create.assert_awaited_once()


async def test_create_flow_rejects_unsupported_flow_type(mock_db) -> None:
    from src.services.contract.payment_flow_service import payment_flow_service

    with pytest.raises(BusinessValidationError, match="unsupported payment flow type"):
        await payment_flow_service.create_flow(
            mock_db,
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
