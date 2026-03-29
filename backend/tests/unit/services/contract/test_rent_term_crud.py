"""
单元测试：ContractRentTerm CRUD（M2-T1）。
"""

from importlib import import_module
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.contract_group import ContractLifecycleStatus
from src.services.contract.contract_group_service import ContractGroupService

pytestmark = pytest.mark.asyncio


def _schema_class(name: str):
    module = import_module("src.schemas.contract_group")
    schema = getattr(module, name, None)
    assert schema is not None, f"{name} 尚未实现"
    return schema


class TestContractRentTermCrud:
    async def test_create_rent_term_calculates_total_monthly_amount(self):
        service = ContractGroupService()
        create_rent_term = getattr(service, "create_rent_term", None)
        assert create_rent_term is not None, (
            "ContractGroupService.create_rent_term 尚未实现"
        )

        create_schema = _schema_class("ContractRentTermCreate")
        payload = create_schema(
            sort_order=1,
            start_date="2026-03-01",
            end_date="2026-03-31",
            monthly_rent="1000.00",
            management_fee="200.00",
            other_fees="50.00",
            notes="首期",
        )

        created = MagicMock(total_monthly_amount="1250.00")

        with (
            patch.object(
                service,
                "_get_contract_or_raise",
                new=AsyncMock(
                    return_value=MagicMock(
                        contract_id="contract-001",
                        status=ContractLifecycleStatus.DRAFT,
                        data_status="正常",
                    )
                ),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.create_rent_term",
                new=AsyncMock(return_value=created),
            ) as mock_create_rent_term,
        ):
            result = await create_rent_term(
                AsyncMock(),
                contract_id="contract-001",
                obj_in=payload,
            )

        assert result is created
        saved = mock_create_rent_term.await_args.kwargs["data"]
        assert str(saved["total_monthly_amount"]) == "1250.00"

    async def test_update_rent_term_recalculates_total_monthly_amount(self):
        service = ContractGroupService()
        update_rent_term = getattr(service, "update_rent_term", None)
        assert update_rent_term is not None, (
            "ContractGroupService.update_rent_term 尚未实现"
        )

        update_schema = _schema_class("ContractRentTermUpdate")
        payload = update_schema(
            monthly_rent="1500.00",
            management_fee="100.00",
            other_fees="25.00",
        )

        term = MagicMock(
            rent_term_id="term-001",
            contract_id="contract-001",
            start_date="2026-03-01",
            end_date="2026-03-31",
            monthly_rent="1000.00",
            management_fee="100.00",
            other_fees="0.00",
            total_monthly_amount="1100.00",
        )

        with (
            patch.object(
                service,
                "_get_contract_or_raise",
                new=AsyncMock(
                    return_value=MagicMock(
                        contract_id="contract-001",
                        status=ContractLifecycleStatus.DRAFT,
                        data_status="正常",
                    )
                ),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get_rent_term",
                new=AsyncMock(return_value=term),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.update_rent_term",
                new=AsyncMock(side_effect=lambda db, db_obj, data: data),
            ) as mock_update_rent_term,
        ):
            result = await update_rent_term(
                AsyncMock(),
                contract_id="contract-001",
                rent_term_id="term-001",
                obj_in=payload,
            )

        saved = mock_update_rent_term.await_args.kwargs["data"]
        assert str(saved["total_monthly_amount"]) == "1625.00"
        assert result["total_monthly_amount"] == saved["total_monthly_amount"]
