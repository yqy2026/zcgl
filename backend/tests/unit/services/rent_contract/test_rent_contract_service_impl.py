from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.constants.rent_contract_constants import PaymentStatus
from src.core.enums import ContractStatus
from src.core.exception_handler import BusinessValidationError, ResourceConflictError
from src.models.rent_contract import RentContract, RentLedger, RentTerm
from src.schemas.rent_contract import (
    GenerateLedgerRequest,
    RentContractCreate,
    RentContractUpdate,
    RentLedgerBatchUpdate,
    RentStatisticsQuery,
    RentTermCreate,
    RentTermUpdate,
)
from src.services.rent_contract.service import RentContractService


@pytest.fixture
def service():
    return RentContractService()


def _build_contract_create(
    *, contract_number: str = "CT-2026-001", total_deposit: Decimal = Decimal("0")
) -> RentContractCreate:
    return RentContractCreate(
        contract_number=contract_number,
        asset_ids=["asset_001"],
        ownership_id="ownership_001",
        tenant_name="test tenant",
        sign_date=date(2026, 1, 1),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        total_deposit=total_deposit,
        rent_terms=[
            RentTermCreate(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                monthly_rent=Decimal("1000"),
                management_fee=Decimal("100"),
            )
        ],
    )


class TestRentContractLifecycle:
    @pytest.mark.asyncio
    async def test_create_contract_async_raises_conflict(self, service, mock_db):
        obj_in = _build_contract_create()
        conflicts = [
            {
                "asset_name": "资产A",
                "contract_number": "CT-OLD-001",
                "contract_start_date": "2025-01-01",
                "contract_end_date": "2026-06-30",
                "asset_ids": ["asset_001"],
                "contract_id": "contract_old",
            }
        ]

        with patch.object(
            service,
            "_check_asset_rent_conflicts_async",
            new=AsyncMock(return_value=conflicts),
        ) as mock_check:
            with pytest.raises(ResourceConflictError, match="资产租金冲突检测"):
                await service.create_contract_async(mock_db, obj_in=obj_in)

        mock_check.assert_awaited_once_with(
            mock_db,
            asset_ids=["asset_001"],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            exclude_contract_id=None,
        )

    @pytest.mark.asyncio
    async def test_create_contract_async_persists_contract_and_terms(
        self, service, mock_db
    ):
        obj_in = _build_contract_create(contract_number="  CT-TRIM-001  ")
        with patch.object(
            service,
            "_check_asset_rent_conflicts_async",
            new=AsyncMock(return_value=[]),
        ), patch(
            "src.services.rent_contract.lifecycle_service.asset_crud.get_multi_by_ids_async",
            new=AsyncMock(return_value=[]),
        ) as mock_get_assets, patch.object(
            service, "_create_history_async", new=AsyncMock()
        ) as mock_history:
            result = await service.create_contract_async(mock_db, obj_in=obj_in)

        assert result.contract_number == "CT-TRIM-001"
        added_models = [call.args[0] for call in mock_db.add.call_args_list]
        assert any(isinstance(model, RentContract) for model in added_models)
        assert any(isinstance(model, RentTerm) for model in added_models)
        mock_get_assets.assert_awaited_once_with(
            mock_db,
            ["asset_001"],
            include_relations=False,
            include_deleted=False,
            decrypt=False,
        )
        mock_db.flush.assert_awaited_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()
        mock_history.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_contract_async_replaces_terms_and_assets(
        self, service, mock_db
    ):
        db_obj = RentContract(
            contract_number="CT-OLD-001",
            ownership_id="ownership_001",
            tenant_name="old tenant",
            sign_date=date(2026, 1, 1),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        db_obj.id = "contract_001"

        update_data = RentContractUpdate(
            tenant_name="new tenant",
            asset_ids=["asset_002"],
            rent_terms=[
                RentTermUpdate(
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 12, 31),
                    monthly_rent=Decimal("1200"),
                    management_fee=Decimal("80"),
                )
            ],
        )

        with patch(
            "src.services.rent_contract.lifecycle_service.asset_crud.get_multi_by_ids_async",
            new=AsyncMock(return_value=[]),
        ), patch.object(
            service, "_create_history_async", new=AsyncMock()
        ) as mock_history:
            result = await service.update_contract_async(
                mock_db, db_obj=db_obj, obj_in=update_data
            )

        assert result.tenant_name == "new tenant"
        assert len(result.rent_terms) == 1
        assert result.rent_terms[0].monthly_rent == Decimal("1200")
        assert mock_db.commit.await_count == 1
        assert mock_db.refresh.await_count == 1
        mock_history.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_contract_async_should_fail_when_owner_ownership_mapping_mismatch(
        self, service, mock_db
    ):
        obj_in = _build_contract_create()
        obj_in.owner_party_id = "party_001"
        obj_in.ownership_id = "ownership_001"

        with patch.object(
            service,
            "_check_asset_rent_conflicts_async",
            new=AsyncMock(return_value=[]),
        ), patch(
            "src.services.rent_contract.lifecycle_service.asset_crud.get_multi_by_ids_async",
            new=AsyncMock(return_value=[]),
        ), patch.object(
            service,
            "resolve_owner_party_scope_by_ownership_id_async",
            new=AsyncMock(return_value="party_002"),
        ), patch.object(
            service,
            "resolve_ownership_id_by_owner_party_id_async",
            new=AsyncMock(return_value="ownership_001"),
        ), patch.object(
            service, "_create_history_async", new=AsyncMock()
        ):
            with pytest.raises(BusinessValidationError, match="对应关系不一致"):
                await service.create_contract_async(mock_db, obj_in=obj_in)

        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_contract_async_should_fail_when_owner_ownership_mapping_mismatch(
        self, service, mock_db
    ):
        db_obj = RentContract(
            contract_number="CT-OLD-001",
            ownership_id="ownership_legacy",
            owner_party_id="party_legacy",
            tenant_name="old tenant",
            sign_date=date(2026, 1, 1),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        db_obj.id = "contract_001"

        update_data = RentContractUpdate(
            owner_party_id="party_001",
            ownership_id="ownership_001",
        )

        with patch.object(
            service,
            "resolve_owner_party_scope_by_ownership_id_async",
            new=AsyncMock(return_value="party_002"),
        ), patch.object(
            service,
            "resolve_ownership_id_by_owner_party_id_async",
            new=AsyncMock(return_value="ownership_001"),
        ), patch.object(
            service, "_create_history_async", new=AsyncMock()
        ):
            with pytest.raises(BusinessValidationError, match="对应关系不一致"):
                await service.update_contract_async(
                    mock_db, db_obj=db_obj, obj_in=update_data
                )

        mock_db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_contract_async_should_keep_owner_party_when_only_owner_party_updated(
        self, service, mock_db
    ):
        db_obj = RentContract(
            contract_number="CT-OLD-001",
            ownership_id="ownership_legacy",
            owner_party_id="party_legacy",
            tenant_name="old tenant",
            sign_date=date(2026, 1, 1),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        db_obj.id = "contract_001"

        update_data = RentContractUpdate(
            owner_party_id="party_001",
        )

        with patch.object(
            service,
            "resolve_ownership_id_by_owner_party_id_async",
            new=AsyncMock(return_value="ownership_001"),
        ) as mock_resolve_ownership, patch.object(
            service,
            "resolve_owner_party_scope_by_ownership_id_async",
            new=AsyncMock(return_value="party_001"),
        ), patch.object(
            service, "_create_history_async", new=AsyncMock()
        ) as mock_history:
            result = await service.update_contract_async(
                mock_db, db_obj=db_obj, obj_in=update_data
            )

        assert result.owner_party_id == "party_001"
        assert result.ownership_id == "party_001"
        assert result.owner_party_id != "ownership_001"
        mock_resolve_ownership.assert_awaited_once_with(
            db=mock_db, owner_party_id="party_001"
        )
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(db_obj)
        mock_history.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_renew_contract_async_transfers_deposit_and_updates_original(
        self, service, mock_db
    ):
        original_contract = MagicMock(spec=RentContract)
        original_contract.id = "contract_old"
        original_contract.total_deposit = Decimal("5000")
        original_contract.contract_status = ContractStatus.ACTIVE.value
        original_contract.end_date = date(2026, 12, 31)

        renewed_contract = MagicMock(spec=RentContract)
        renewed_contract.id = "contract_new"
        renewed_contract.start_date = date(2026, 7, 1)

        with patch.object(
            service,
            "get_contract_with_details_async",
            new=AsyncMock(return_value=original_contract),
        ), patch.object(
            service,
            "create_contract_async",
            new=AsyncMock(return_value=renewed_contract),
        ) as mock_create, patch.object(
            service, "_create_history_async", new=AsyncMock()
        ) as mock_history:
            new_contract_data = _build_contract_create(total_deposit=Decimal("0"))
            new_contract_data.total_deposit = None

            result = await service.renew_contract_async(
                mock_db,
                original_contract_id="contract_old",
                new_contract_data=new_contract_data,
            )

        create_payload = mock_create.await_args.kwargs["obj_in"]
        assert create_payload.total_deposit == Decimal("5000")
        assert original_contract.contract_status == ContractStatus.TERMINATED.value
        assert original_contract.end_date == date(2026, 7, 1)
        mock_db.add.assert_any_call(original_contract)
        mock_db.commit.assert_awaited_once()
        mock_history.assert_awaited_once()
        assert result is renewed_contract

    @pytest.mark.asyncio
    async def test_renew_contract_async_should_propagate_mapping_validation_error(
        self, service, mock_db
    ):
        original_contract = MagicMock(spec=RentContract)
        original_contract.id = "contract_old"
        original_contract.total_deposit = Decimal("5000")
        original_contract.contract_status = ContractStatus.ACTIVE.value
        original_contract.end_date = date(2026, 12, 31)

        mapping_validation_error = BusinessValidationError(
            "owner_party_id 与 ownership_id 对应关系不一致，请修正后重试",
            field_errors={
                "owner_party_id": ["与 ownership_id 映射不一致"],
                "ownership_id": ["与 owner_party_id 映射不一致"],
            },
        )

        with patch.object(
            service,
            "get_contract_with_details_async",
            new=AsyncMock(return_value=original_contract),
        ), patch.object(
            service,
            "create_contract_async",
            new=AsyncMock(side_effect=mapping_validation_error),
        ), patch.object(
            service, "_create_history_async", new=AsyncMock()
        ) as mock_history:
            with pytest.raises(BusinessValidationError, match="对应关系不一致"):
                await service.renew_contract_async(
                    mock_db,
                    original_contract_id="contract_old",
                    new_contract_data=_build_contract_create(total_deposit=Decimal("0")),
                )

        assert original_contract.contract_status == ContractStatus.ACTIVE.value
        assert original_contract.end_date == date(2026, 12, 31)
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_awaited()
        mock_history.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_terminate_contract_async_updates_status_and_notes(
        self, service, mock_db
    ):
        contract = MagicMock(spec=RentContract)
        contract.id = "contract_123"
        contract.contract_status = ContractStatus.ACTIVE.value
        contract.contract_notes = "old notes"

        with patch.object(
            service,
            "get_contract_by_id_async",
            new=AsyncMock(return_value=contract),
        ), patch.object(
            service, "_create_history_async", new=AsyncMock()
        ) as mock_history:
            result = await service.terminate_contract_async(
                mock_db,
                contract_id="contract_123",
                termination_date=date(2026, 6, 30),
                should_refund_deposit=False,
                deduction_amount=Decimal("300"),
                termination_reason="提前解约",
            )

        assert result is contract
        assert contract.contract_status == ContractStatus.TERMINATED.value
        assert contract.end_date == date(2026, 6, 30)
        assert contract.contract_notes
        assert "300" in contract.contract_notes
        mock_db.add.assert_any_call(contract)
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(contract)
        mock_history.assert_awaited_once()


class TestRentContractOwnerOwnershipBridge:
    @pytest.mark.asyncio
    async def test_resolve_ownership_id_by_owner_party_id_prefers_external_ref(
        self, service, mock_db
    ) -> None:
        owner_party = MagicMock()
        owner_party.external_ref = "ownership-external"
        owner_party.code = None
        owner_party.name = None

        with patch(
            "src.services.rent_contract.service.party_crud.get_party",
            new=AsyncMock(return_value=owner_party),
        ), patch(
            "src.services.rent_contract.service.ownership_crud.get",
            new=AsyncMock(side_effect=[MagicMock(id="ownership-external"), None]),
        ):
            result = await service.resolve_ownership_id_by_owner_party_id_async(
                mock_db,
                owner_party_id="party-1",
            )

        assert result == "ownership-external"
        mock_db.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_resolve_ownership_id_by_owner_party_id_returns_none_on_ambiguous_code(
        self, service, mock_db
    ) -> None:
        owner_party = MagicMock()
        owner_party.external_ref = None
        owner_party.code = "OWN-CODE"
        owner_party.name = None

        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = ["ownership-1", "ownership-2"]
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        with patch(
            "src.services.rent_contract.service.party_crud.get_party",
            new=AsyncMock(return_value=owner_party),
        ), patch(
            "src.services.rent_contract.service.ownership_crud.get",
            new=AsyncMock(return_value=None),
        ):
            result = await service.resolve_ownership_id_by_owner_party_id_async(
                mock_db,
                owner_party_id="party-1",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_ownership_id_by_owner_party_id_filters_inactive_or_deleted_rows(
        self, service, mock_db
    ) -> None:
        owner_party = MagicMock()
        owner_party.external_ref = None
        owner_party.code = "OWN-CODE"
        owner_party.name = None

        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = ["ownership-active"]
        mock_db.execute = AsyncMock(return_value=mock_execute_result)

        with patch(
            "src.services.rent_contract.service.party_crud.get_party",
            new=AsyncMock(return_value=owner_party),
        ), patch(
            "src.services.rent_contract.service.ownership_crud.get",
            new=AsyncMock(return_value=None),
        ):
            result = await service.resolve_ownership_id_by_owner_party_id_async(
                mock_db,
                owner_party_id="party-1",
            )

        assert result == "ownership-active"
        (stmt,) = mock_db.execute.await_args.args
        compiled_stmt = str(stmt)
        assert "ownerships.is_active" in compiled_stmt
        assert "ownerships.data_status" in compiled_stmt
        assert "正常" in stmt.compile().params.values()

    @pytest.mark.asyncio
    async def test_resolve_ownership_id_by_owner_party_id_keeps_high_confidence_match_when_code_is_ambiguous(
        self, service, mock_db
    ) -> None:
        owner_party = MagicMock()
        owner_party.external_ref = "ownership-external"
        owner_party.code = "OWN-CODE"
        owner_party.name = None

        with patch(
            "src.services.rent_contract.service.party_crud.get_party",
            new=AsyncMock(return_value=owner_party),
        ), patch(
            "src.services.rent_contract.service.ownership_crud.get",
            new=AsyncMock(side_effect=[MagicMock(id="ownership-external"), None]),
        ):
            result = await service.resolve_ownership_id_by_owner_party_id_async(
                mock_db,
                owner_party_id="party-1",
            )

        assert result == "ownership-external"
        mock_db.execute.assert_not_awaited()


class TestRentContractLedger:
    @pytest.mark.asyncio
    async def test_generate_monthly_ledger_async_requires_rent_terms(
        self, service, mock_db
    ):
        request = GenerateLedgerRequest(contract_id="contract_001")
        mock_contract = MagicMock(spec=RentContract)
        mock_contract.start_date = date(2026, 1, 1)
        mock_contract.end_date = date(2026, 12, 31)

        with patch(
            "src.services.rent_contract.ledger_service.rent_contract.get_async",
            new=AsyncMock(return_value=mock_contract),
        ), patch(
            "src.services.rent_contract.ledger_service.rent_term.get_by_contract_async",
            new=AsyncMock(return_value=[]),
        ):
            with pytest.raises(BusinessValidationError, match="合同没有租金条款"):
                await service.generate_monthly_ledger_async(mock_db, request=request)

    @pytest.mark.asyncio
    async def test_batch_update_payment_async_calculates_overdue(self, service, mock_db):
        ledger = MagicMock(spec=RentLedger)
        ledger.id = "ledger_001"
        ledger.due_amount = Decimal("1000")
        ledger.paid_amount = Decimal("700")
        ledger.overdue_amount = Decimal("0")
        ledger.payment_status = PaymentStatus.UNPAID.value

        request = RentLedgerBatchUpdate(
            ledger_ids=["ledger_001"],
            payment_status=PaymentStatus.PARTIAL.value,
            notes="部分回款",
        )

        with patch(
            "src.services.rent_contract.ledger_service.rent_ledger.get_multi_by_ids_async",
            new=AsyncMock(return_value=[ledger]),
        ) as mock_get_ledgers, patch.object(
            service, "_calculate_service_fee_for_ledger_async", new=AsyncMock()
        ) as mock_service_fee:
            result = await service.batch_update_payment_async(mock_db, request=request)

        assert result == [ledger]
        assert ledger.payment_status == PaymentStatus.PARTIAL.value
        assert ledger.overdue_amount == Decimal("300")
        mock_get_ledgers.assert_awaited_once_with(mock_db, ledger_ids=["ledger_001"])
        mock_service_fee.assert_awaited_once_with(mock_db, ledger)
        mock_db.commit.assert_awaited_once()


class TestRentContractStatistics:
    @pytest.mark.asyncio
    async def test_get_statistics_async_assembles_response(self, service, mock_db):
        query = RentStatisticsQuery()
        status_row = MagicMock()
        status_row.payment_status = PaymentStatus.PAID.value
        status_row.count = 2
        status_row.due_amount = Decimal("1000")
        status_row.paid_amount = Decimal("900")

        monthly_row = MagicMock()
        monthly_row.year_month = "2026-01"
        monthly_row.due_amount = Decimal("1000")
        monthly_row.paid_amount = Decimal("900")
        monthly_row.overdue_amount = Decimal("100")

        with patch(
            "src.services.rent_contract.statistics_service.rent_ledger_crud.get_ledger_statistics_async",
            new=AsyncMock(return_value=(Decimal("1000"), Decimal("900"), Decimal("100"), 3)),
        ), patch(
            "src.services.rent_contract.statistics_service.rent_ledger_crud.get_ledger_status_breakdown_async",
            new=AsyncMock(return_value=[status_row]),
        ), patch(
            "src.services.rent_contract.statistics_service.rent_ledger_crud.get_ledger_monthly_breakdown_async",
            new=AsyncMock(return_value=[monthly_row]),
        ), patch.object(
            service, "_calculate_average_unit_price_async", new=AsyncMock(return_value=Decimal("2.50"))
        ), patch.object(
            service, "_calculate_renewal_rate_async", new=AsyncMock(return_value=Decimal("12.34"))
        ):
            result = await service.get_statistics_async(mock_db, query_params=query)

        assert result["total_due"] == Decimal("1000")
        assert result["total_paid"] == Decimal("900")
        assert result["payment_rate"] == Decimal("90")
        assert result["average_unit_price"] == Decimal("2.50")
        assert result["renewal_rate"] == Decimal("12.34")
        assert result["status_breakdown"][0]["status"] == PaymentStatus.PAID.value
        assert result["monthly_breakdown"][0]["year_month"] == "2026-01"

    @pytest.mark.asyncio
    async def test_get_statistics_async_should_pass_deprecated_ownership_ids(
        self, service, mock_db
    ) -> None:
        query = RentStatisticsQuery(ownership_ids=["ownership-1"])

        with patch(
            "src.services.rent_contract.statistics_service.rent_ledger_crud.get_ledger_statistics_async",
            new=AsyncMock(return_value=(Decimal("0"), Decimal("0"), Decimal("0"), 0)),
        ) as mock_ledger_stats, patch(
            "src.services.rent_contract.statistics_service.rent_ledger_crud.get_ledger_status_breakdown_async",
            new=AsyncMock(return_value=[]),
        ) as mock_status_breakdown, patch(
            "src.services.rent_contract.statistics_service.rent_ledger_crud.get_ledger_monthly_breakdown_async",
            new=AsyncMock(return_value=[]),
        ) as mock_monthly_breakdown, patch.object(
            service,
            "_calculate_average_unit_price_async",
            new=AsyncMock(return_value=Decimal("0")),
        ), patch.object(
            service,
            "_calculate_renewal_rate_async",
            new=AsyncMock(return_value=Decimal("0")),
        ):
            await service.get_statistics_async(mock_db, query_params=query)

        mock_ledger_stats.assert_awaited_once_with(
            mock_db,
            start_date=None,
            end_date=None,
            owner_party_ids=None,
            manager_party_ids=None,
            ownership_ids=["ownership-1"],
            asset_ids=None,
        )
        mock_status_breakdown.assert_awaited_once_with(
            mock_db,
            start_date=None,
            end_date=None,
            owner_party_ids=None,
            manager_party_ids=None,
            ownership_ids=["ownership-1"],
            asset_ids=None,
        )
        mock_monthly_breakdown.assert_awaited_once_with(
            mock_db,
            start_date=None,
            end_date=None,
            owner_party_ids=None,
            manager_party_ids=None,
            ownership_ids=["ownership-1"],
            asset_ids=None,
        )

    @pytest.mark.asyncio
    async def test_get_ownership_statistics_async_should_merge_legacy_rows(
        self, service, mock_db
    ) -> None:
        owner_party_row = MagicMock()
        owner_party_row.id = "party-1"
        owner_party_row.name = "主体A"
        owner_party_row.contract_count = 2
        owner_party_row.total_due_amount = Decimal("200")
        owner_party_row.total_paid_amount = Decimal("150")
        owner_party_row.total_overdue_amount = Decimal("50")

        legacy_row = MagicMock()
        legacy_row.id = "ownership-legacy-1"
        legacy_row.name = "历史权属A"
        legacy_row.short_name = "历史A"
        legacy_row.contract_count = 1
        legacy_row.total_due_amount = Decimal("100")
        legacy_row.total_paid_amount = Decimal("80")
        legacy_row.total_overdue_amount = Decimal("20")

        start_date = date(2026, 1, 1)
        end_date = date(2026, 12, 31)
        owner_party_ids = ["party-1"]

        with patch(
            "src.services.rent_contract.statistics_service.rent_ledger_crud.get_owner_party_statistics_async",
            new=AsyncMock(return_value=[owner_party_row]),
        ) as mock_owner_stats, patch(
            "src.services.rent_contract.statistics_service.rent_contract_crud.get_distinct_ownership_ids_by_owner_party_ids_async",
            new=AsyncMock(return_value=["ownership-legacy-1"]),
        ) as mock_owner_mapping, patch(
            "src.services.rent_contract.statistics_service.rent_ledger_crud.get_ownership_statistics_async",
            new=AsyncMock(return_value=[legacy_row]),
        ) as mock_legacy_stats:
            result = await service.get_ownership_statistics_async(
                mock_db,
                start_date=start_date,
                end_date=end_date,
                owner_party_ids=owner_party_ids,
            )

        result_by_id = {item["owner_party_id"]: item for item in result}

        assert set(result_by_id.keys()) == {"party-1", "ownership-legacy-1"}
        assert result_by_id["party-1"]["owner_party_name"] == "主体A"
        assert result_by_id["party-1"]["ownership_id"] is None
        assert result_by_id["party-1"]["ownership_name"] is None
        assert result_by_id["party-1"]["occupancy_rate"] == Decimal("75")

        legacy_result = result_by_id["ownership-legacy-1"]
        assert legacy_result["owner_party_name"] == "历史权属A"
        assert legacy_result["ownership_id"] == "ownership-legacy-1"
        assert legacy_result["ownership_name"] == "历史权属A"
        assert legacy_result["occupancy_rate"] == Decimal("80")

        mock_owner_stats.assert_awaited_once_with(
            mock_db,
            start_date=start_date,
            end_date=end_date,
            owner_party_ids=owner_party_ids,
            manager_party_ids=None,
        )
        mock_owner_mapping.assert_awaited_once_with(
            mock_db,
            owner_party_ids=owner_party_ids,
        )
        mock_legacy_stats.assert_awaited_once_with(
            mock_db,
            start_date=start_date,
            end_date=end_date,
            manager_party_ids=None,
            ownership_ids=["ownership-legacy-1"],
            legacy_only=True,
        )

    @pytest.mark.asyncio
    async def test_get_ownership_statistics_async_should_use_explicit_ownership_ids(
        self, service, mock_db
    ) -> None:
        legacy_row = MagicMock()
        legacy_row.id = "ownership-legacy-1"
        legacy_row.name = "历史权属A"
        legacy_row.contract_count = 1
        legacy_row.total_due_amount = Decimal("100")
        legacy_row.total_paid_amount = Decimal("80")
        legacy_row.total_overdue_amount = Decimal("20")

        with patch(
            "src.services.rent_contract.statistics_service.rent_ledger_crud.get_owner_party_statistics_async",
            new=AsyncMock(return_value=[]),
        ), patch(
            "src.services.rent_contract.statistics_service.rent_contract_crud.get_distinct_ownership_ids_by_owner_party_ids_async",
            new=AsyncMock(return_value=["ownership-from-party"]),
        ) as mock_owner_mapping, patch(
            "src.services.rent_contract.statistics_service.rent_ledger_crud.get_ownership_statistics_async",
            new=AsyncMock(return_value=[legacy_row]),
        ) as mock_legacy_stats:
            await service.get_ownership_statistics_async(
                mock_db,
                owner_party_ids=["party-1"],
                ownership_ids=["ownership-legacy-1"],
            )

        mock_owner_mapping.assert_not_awaited()
        mock_legacy_stats.assert_awaited_once_with(
            mock_db,
            start_date=None,
            end_date=None,
            manager_party_ids=None,
            ownership_ids=["ownership-legacy-1"],
            legacy_only=True,
        )

    @pytest.mark.asyncio
    async def test_get_ownership_statistics_async_should_map_owner_party_ids_from_ownership_ids(
        self, service, mock_db
    ) -> None:
        owner_party_row = MagicMock()
        owner_party_row.id = "party-1"
        owner_party_row.name = "主体A"
        owner_party_row.contract_count = 2
        owner_party_row.total_due_amount = Decimal("200")
        owner_party_row.total_paid_amount = Decimal("150")
        owner_party_row.total_overdue_amount = Decimal("50")

        with patch(
            "src.services.rent_contract.statistics_service.rent_contract_crud.get_distinct_owner_party_ids_by_ownership_ids_async",
            new=AsyncMock(return_value=["party-1"]),
        ) as mock_party_mapping, patch(
            "src.services.rent_contract.statistics_service.rent_ledger_crud.get_owner_party_statistics_async",
            new=AsyncMock(return_value=[owner_party_row]),
        ) as mock_owner_stats, patch(
            "src.services.rent_contract.statistics_service.rent_ledger_crud.get_ownership_statistics_async",
            new=AsyncMock(return_value=[]),
        ) as mock_legacy_stats:
            result = await service.get_ownership_statistics_async(
                mock_db,
                ownership_ids=["ownership-1"],
            )

        assert [item["owner_party_id"] for item in result] == ["party-1"]
        mock_party_mapping.assert_awaited_once_with(
            mock_db,
            ownership_ids=["ownership-1"],
        )
        mock_owner_stats.assert_awaited_once_with(
            mock_db,
            start_date=None,
            end_date=None,
            owner_party_ids=["party-1"],
            manager_party_ids=None,
        )
        mock_legacy_stats.assert_awaited_once_with(
            mock_db,
            start_date=None,
            end_date=None,
            manager_party_ids=None,
            ownership_ids=["ownership-1"],
            legacy_only=True,
        )

    @pytest.mark.asyncio
    async def test_get_ownership_statistics_async_should_skip_owner_party_query_when_no_mapping(
        self, service, mock_db
    ) -> None:
        with patch(
            "src.services.rent_contract.statistics_service.rent_contract_crud.get_distinct_owner_party_ids_by_ownership_ids_async",
            new=AsyncMock(return_value=[]),
        ) as mock_party_mapping, patch(
            "src.services.rent_contract.statistics_service.rent_ledger_crud.get_owner_party_statistics_async",
            new=AsyncMock(return_value=[]),
        ) as mock_owner_stats, patch(
            "src.services.rent_contract.statistics_service.rent_ledger_crud.get_ownership_statistics_async",
            new=AsyncMock(return_value=[]),
        ) as mock_legacy_stats:
            result = await service.get_ownership_statistics_async(
                mock_db,
                ownership_ids=["ownership-missing"],
            )

        assert result == []
        mock_party_mapping.assert_awaited_once_with(
            mock_db,
            ownership_ids=["ownership-missing"],
        )
        mock_owner_stats.assert_not_awaited()
        mock_legacy_stats.assert_awaited_once_with(
            mock_db,
            start_date=None,
            end_date=None,
            manager_party_ids=None,
            ownership_ids=["ownership-missing"],
            legacy_only=True,
        )
