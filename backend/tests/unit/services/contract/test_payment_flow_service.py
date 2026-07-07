"""Unit tests for operational payment flow service."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.core.exception_handler import BusinessValidationError

pytestmark = pytest.mark.asyncio


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
    ledger_entry = SimpleNamespace(
        entry_id="entry-1",
        year_month="2026-07",
        paid_amount=Decimal("0"),
        amount_due=Decimal("1000.00"),
        updated_at=None,
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


async def test_save_allocations_resets_removed_target_paid_amount(mock_db) -> None:
    from src.services.contract.payment_flow_service import payment_flow_service

    flow = SimpleNamespace(
        flow_id="flow-1",
        flow_type="terminal_rent_receipt",
        amount=Decimal("1000.00"),
        status="active",
    )
    old_entry = SimpleNamespace(
        entry_id="entry-old",
        year_month="2026-07",
        paid_amount=Decimal("1000.00"),
        amount_due=Decimal("1000.00"),
        updated_at=None,
    )
    new_entry = SimpleNamespace(
        entry_id="entry-new",
        year_month="2026-07",
        paid_amount=Decimal("0"),
        amount_due=Decimal("1000.00"),
        updated_at=None,
    )
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
        ),
        patch(
            "src.services.contract.payment_flow_service.contract_group_crud.get_ledger_entries_by_ids",
            new=AsyncMock(return_value=[old_entry, new_entry]),
        ),
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
