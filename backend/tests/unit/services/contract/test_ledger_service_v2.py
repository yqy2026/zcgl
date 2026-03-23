"""
单元测试：合同台账 V2（M2-T2）。
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.contract_group import ContractLifecycleStatus, ContractReviewStatus
from src.services.contract.contract_group_service import ContractGroupService

pytestmark = pytest.mark.asyncio


def _make_contract(
    *,
    contract_id: str = "contract-001",
    payment_cycle: str = "月付",
) -> MagicMock:
    contract = MagicMock()
    contract.contract_id = contract_id
    contract.status = ContractLifecycleStatus.PENDING_REVIEW
    contract.review_status = ContractReviewStatus.PENDING
    contract.sign_date = date(2026, 1, 1)
    contract.currency_code = "CNY"
    contract.is_tax_included = True
    contract.tax_rate = Decimal("0.09")
    contract.data_status = "正常"
    contract.review_by = None
    contract.reviewed_at = None
    contract.review_reason = None
    contract.lease_detail = MagicMock(payment_cycle=payment_cycle)
    contract.agency_detail = None
    return contract


def _make_rent_term(
    *,
    start_date: date,
    end_date: date,
    monthly_rent: str,
    total_monthly_amount: str | None = None,
    sort_order: int = 1,
) -> MagicMock:
    rent_term = MagicMock()
    rent_term.contract_id = "contract-001"
    rent_term.sort_order = sort_order
    rent_term.start_date = start_date
    rent_term.end_date = end_date
    rent_term.monthly_rent = Decimal(monthly_rent)
    rent_term.total_monthly_amount = (
        Decimal(total_monthly_amount) if total_monthly_amount is not None else None
    )
    return rent_term


class TestLedgerServiceV2:
    async def test_generate_ledger_on_activation_creates_missing_months(self):
        from src.services.contract import ledger_service_v2 as ledger_module

        service = getattr(ledger_module, "ledger_service_v2", None)
        assert service is not None, "ledger_service_v2 尚未实现"

        contract = _make_contract(payment_cycle="季付")
        rent_terms = [
            _make_rent_term(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 2, 28),
                monthly_rent="1000.00",
                total_monthly_amount="1200.00",
                sort_order=1,
            ),
            _make_rent_term(
                start_date=date(2026, 3, 1),
                end_date=date(2026, 3, 31),
                monthly_rent="1500.00",
                total_monthly_amount="1800.00",
                sort_order=2,
            ),
        ]

        created_entries: list[dict] = []

        async def _create_ledger_entry(db, *, data, commit=False):  # noqa: ANN001
            created_entries.append(data)
            entry = MagicMock()
            entry.year_month = data["year_month"]
            entry.amount_due = data["amount_due"]
            entry.due_date = data["due_date"]
            return entry

        with (
            patch(
                "src.services.contract.ledger_service_v2.contract_crud.get",
                new=AsyncMock(return_value=contract),
            ),
            patch(
                "src.services.contract.ledger_service_v2.contract_group_crud.list_rent_terms_by_contract",
                new=AsyncMock(return_value=rent_terms),
            ),
            patch(
                "src.services.contract.ledger_service_v2.contract_group_crud.get_existing_ledger_year_months",
                new=AsyncMock(return_value={"2026-02"}),
            ),
            patch(
                "src.services.contract.ledger_service_v2.contract_group_crud.create_ledger_entry",
                new=_create_ledger_entry,
            ),
        ):
            result = await service.generate_ledger_on_activation(
                AsyncMock(),
                contract_id="contract-001",
            )

        assert [entry.year_month for entry in result] == ["2026-01", "2026-03"]
        assert [entry["year_month"] for entry in created_entries] == [
            "2026-01",
            "2026-03",
        ]
        assert str(created_entries[0]["amount_due"]) == "1200.00"
        assert str(created_entries[1]["amount_due"]) == "1800.00"
        assert created_entries[1]["due_date"] == date(2026, 1, 1)

    async def test_generate_ledger_on_activation_without_rent_terms_returns_empty(self):
        from src.services.contract import ledger_service_v2 as ledger_module

        service = getattr(ledger_module, "ledger_service_v2", None)
        assert service is not None, "ledger_service_v2 尚未实现"

        contract = _make_contract()

        with (
            patch(
                "src.services.contract.ledger_service_v2.contract_crud.get",
                new=AsyncMock(return_value=contract),
            ),
            patch(
                "src.services.contract.ledger_service_v2.contract_group_crud.list_rent_terms_by_contract",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.services.contract.ledger_service_v2.logger.warning"
            ) as mock_warning,
        ):
            result = await service.generate_ledger_on_activation(
                AsyncMock(),
                contract_id="contract-001",
            )

        assert result == []
        mock_warning.assert_called_once()

    async def test_generate_ledger_on_activation_includes_first_partial_month(self):
        from src.services.contract import ledger_service_v2 as ledger_module

        service = getattr(ledger_module, "ledger_service_v2", None)
        assert service is not None, "ledger_service_v2 尚未实现"

        contract = _make_contract(payment_cycle="月付")
        rent_terms = [
            _make_rent_term(
                start_date=date(2026, 1, 15),
                end_date=date(2026, 2, 14),
                monthly_rent="1000.00",
                total_monthly_amount="1200.00",
                sort_order=1,
            )
        ]

        created_entries: list[dict] = []

        async def _create_ledger_entry(db, *, data, commit=False):  # noqa: ANN001
            created_entries.append(data)
            entry = MagicMock()
            entry.year_month = data["year_month"]
            return entry

        with (
            patch(
                "src.services.contract.ledger_service_v2.contract_crud.get",
                new=AsyncMock(return_value=contract),
            ),
            patch(
                "src.services.contract.ledger_service_v2.contract_group_crud.list_rent_terms_by_contract",
                new=AsyncMock(return_value=rent_terms),
            ),
            patch(
                "src.services.contract.ledger_service_v2.contract_group_crud.get_existing_ledger_year_months",
                new=AsyncMock(return_value=set()),
            ),
            patch(
                "src.services.contract.ledger_service_v2.contract_group_crud.create_ledger_entry",
                new=_create_ledger_entry,
            ),
        ):
            result = await service.generate_ledger_on_activation(
                AsyncMock(),
                contract_id="contract-001",
            )

        assert [entry.year_month for entry in result] == ["2026-01", "2026-02"]
        assert [entry["year_month"] for entry in created_entries] == [
            "2026-01",
            "2026-02",
        ]

    async def test_approve_calls_generate_ledger_on_activation(self):
        service = ContractGroupService()
        contract = _make_contract()

        with (
            patch(
                "src.services.contract.contract_group_service.contract_crud.get",
                new=AsyncMock(return_value=contract),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.update",
                new=AsyncMock(
                    side_effect=lambda db, db_obj, data, commit=False: db_obj
                ),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.create_audit_log",
                new=AsyncMock(),
            ),
            patch(
                "src.services.contract.contract_group_service.ledger_service_v2.generate_ledger_on_activation",
                new=AsyncMock(return_value=[]),
            ) as mock_generate_ledger,
        ):
            await service.approve(
                AsyncMock(),
                contract_id="contract-001",
                current_user="reviewer-001",
                operator_name="审核员",
            )

        mock_generate_ledger.assert_awaited_once()

    async def test_batch_update_status_delegates_and_returns_updated_entries(self):
        from src.services.contract import ledger_service_v2 as ledger_module

        service = getattr(ledger_module, "ledger_service_v2", None)
        assert service is not None, "ledger_service_v2 尚未实现"

        updated_entries = [MagicMock(entry_id="entry-001"), MagicMock(entry_id="entry-002")]

        with patch(
            "src.services.contract.ledger_service_v2.contract_group_crud.batch_update_ledger_status",
            new=AsyncMock(return_value=updated_entries),
        ) as mock_batch_update:
            result = await service.batch_update_status(
                AsyncMock(),
                contract_id="contract-001",
                entry_ids=["entry-001", "entry-002"],
                payment_status="paid",
                paid_amount=Decimal("3000.00"),
            )

        assert result is updated_entries
        mock_batch_update.assert_awaited_once()
