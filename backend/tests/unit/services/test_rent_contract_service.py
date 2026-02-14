from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import BusinessValidationError
from src.models.rent_contract import RentContract
from src.schemas.rent_contract import RentContractCreate, RentTermCreate
from src.services.rent_contract.service import RentContractService


@pytest.fixture
def service():
    return RentContractService()


def _build_contract_create(*, contract_number: str | None) -> RentContractCreate:
    return RentContractCreate(
        contract_number=contract_number,
        asset_ids=[],
        ownership_id="ownership_123",
        tenant_name="测试承租方",
        sign_date=date(2024, 1, 1),
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        rent_terms=[
            RentTermCreate(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                monthly_rent=Decimal("1000"),
            )
        ],
    )


class TestRentContractService:
    @pytest.mark.asyncio
    async def test_get_contract_by_id_async_delegates_to_crud(self, service, mock_db):
        mock_contract = MagicMock(spec=RentContract)
        with patch(
            "src.services.rent_contract.service.rent_contract_crud.get_async",
            new=AsyncMock(return_value=mock_contract),
        ) as mock_get:
            result = await service.get_contract_by_id_async(
                mock_db, contract_id="contract_123"
            )

        assert result is mock_contract
        mock_get.assert_awaited_once_with(mock_db, id="contract_123")

    @pytest.mark.asyncio
    async def test_get_contract_page_async_delegates_to_crud(self, service, mock_db):
        mock_contract = MagicMock(spec=RentContract)
        with patch(
            "src.services.rent_contract.service.rent_contract_crud.get_multi_with_filters_async",
            new=AsyncMock(return_value=([mock_contract], 1)),
        ) as mock_get_page:
            items, total = await service.get_contract_page_async(
                mock_db,
                skip=5,
                limit=20,
                contract_number="CT-2026",
            )

        assert items == [mock_contract]
        assert total == 1
        mock_get_page.assert_awaited_once_with(
            db=mock_db,
            skip=5,
            limit=20,
            contract_number="CT-2026",
            tenant_name=None,
            asset_id=None,
            ownership_id=None,
            contract_status=None,
            start_date=None,
            end_date=None,
        )

    @pytest.mark.asyncio
    async def test_get_asset_contracts_async_returns_items(self, service, mock_db):
        mock_contract = MagicMock(spec=RentContract)
        with patch.object(
            service,
            "get_contract_page_async",
            new=AsyncMock(return_value=([mock_contract], 9)),
        ) as mock_get_page:
            result = await service.get_asset_contracts_async(
                mock_db,
                asset_id="asset_001",
                limit=200,
            )

        assert result == [mock_contract]
        mock_get_page.assert_awaited_once_with(
            db=mock_db,
            skip=0,
            limit=200,
            asset_id="asset_001",
        )

    @pytest.mark.asyncio
    async def test_create_contract_async_rejects_empty_contract_number(
        self, service, mock_db
    ):
        obj_in = _build_contract_create(contract_number=None)

        with pytest.raises(BusinessValidationError, match="合同编号不能为空"):
            await service.create_contract_async(mock_db, obj_in=obj_in)
