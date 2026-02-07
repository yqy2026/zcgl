from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.rent_contract import GenerateLedgerRequest
from src.services.rent_contract.ledger_service import RentContractLedgerService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def mock_contract() -> MagicMock:
    contract = MagicMock()
    contract.id = "contract_123"
    contract.start_date = date(2025, 1, 1)
    contract.end_date = date(2025, 3, 31)
    contract.ownership_id = "ownership_123"
    return contract


@pytest.fixture
def mock_term() -> MagicMock:
    term = MagicMock()
    term.start_date = date(2025, 1, 1)
    term.end_date = date(2025, 12, 31)
    term.monthly_rent = Decimal("1000")
    term.total_monthly_amount = Decimal("1200")
    return term


class TestGenerateMonthlyLedgerAsync:
    async def test_uses_bulk_existing_month_lookup(
        self, mock_db: AsyncMock, mock_contract: MagicMock, mock_term: MagicMock
    ) -> None:
        service = RentContractLedgerService()
        request = GenerateLedgerRequest(
            contract_id="contract_123",
            start_year_month="2025-01",
            end_year_month="2025-03",
        )

        with patch(
            "src.services.rent_contract.ledger_service.rent_contract.get_async",
            new=AsyncMock(return_value=mock_contract),
        ), patch(
            "src.services.rent_contract.ledger_service.rent_term.get_by_contract_async",
            new=AsyncMock(return_value=[mock_term]),
        ), patch(
            "src.services.rent_contract.ledger_service.rent_ledger.get_existing_year_months_async",
            new=AsyncMock(return_value={"2025-02"}),
        ) as mock_get_existing_months, patch(
            "src.services.rent_contract.ledger_service.rent_ledger.get_by_contract_and_month_async",
            new=AsyncMock(return_value=None),
        ) as mock_get_single_month:
            ledgers = await service.generate_monthly_ledger_async(mock_db, request=request)

        assert [ledger.year_month for ledger in ledgers] == ["2025-01", "2025-03"]
        mock_get_existing_months.assert_awaited_once_with(
            mock_db,
            contract_id="contract_123",
            year_months=["2025-01", "2025-02", "2025-03"],
        )
        mock_get_single_month.assert_not_awaited()
        assert mock_db.add.call_count == 2
        mock_db.refresh.assert_not_awaited()

    async def test_all_months_existing_returns_empty(
        self, mock_db: AsyncMock, mock_contract: MagicMock, mock_term: MagicMock
    ) -> None:
        service = RentContractLedgerService()
        request = GenerateLedgerRequest(
            contract_id="contract_123",
            start_year_month="2025-01",
            end_year_month="2025-02",
        )

        with patch(
            "src.services.rent_contract.ledger_service.rent_contract.get_async",
            new=AsyncMock(return_value=mock_contract),
        ), patch(
            "src.services.rent_contract.ledger_service.rent_term.get_by_contract_async",
            new=AsyncMock(return_value=[mock_term]),
        ), patch(
            "src.services.rent_contract.ledger_service.rent_ledger.get_existing_year_months_async",
            new=AsyncMock(return_value={"2025-01", "2025-02"}),
        ):
            ledgers = await service.generate_monthly_ledger_async(mock_db, request=request)

        assert ledgers == []
        mock_db.add.assert_not_called()

