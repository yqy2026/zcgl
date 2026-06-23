from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import OperationNotAllowedError
from src.models.contract_group import Contract, ContractLifecycleStatus
from src.schemas.contract_group import ContractRentTermUpdate
from src.services.contract.contract_group_service import ContractGroupService

pytestmark = pytest.mark.asyncio


def _make_contract(
    *,
    contract_id: str = "contract-001",
    contract_number: str = "HT-2026-0001",
    status: ContractLifecycleStatus = ContractLifecycleStatus.ACTIVE,
) -> MagicMock:
    contract = MagicMock(spec=Contract)
    contract.contract_id = contract_id
    contract.contract_group_id = "group-001"
    contract.contract_number = contract_number
    contract.status = status
    contract.sign_date = date(2026, 3, 1)
    contract.effective_from = date(2026, 3, 1)
    contract.effective_to = date(2026, 12, 31)
    contract.currency_code = "CNY"
    contract.tax_rate = Decimal("0.09")
    contract.is_tax_included = True
    contract.data_status = "正常"
    contract.contract_direction = "LESSOR"
    contract.group_relation_type = "UPSTREAM"
    contract.lessor_party_id = "party-lessor"
    contract.lessee_party_id = "party-lessee"
    contract.lessor_name_snapshot = "签署甲方"
    contract.lessee_name_snapshot = "签署乙方"
    contract.contract_notes = "原始备注"
    contract.source_session_id = None
    contract.correction_source_contract_id = None
    contract.lease_detail = SimpleNamespace(
        rent_amount=Decimal("10000"),
        total_deposit=Decimal("5000"),
        monthly_rent_base=Decimal("10000"),
        payment_cycle="月付",
        payment_terms="每月 5 日前支付",
        tenant_name="租户A",
        tenant_contact=None,
        tenant_phone=None,
        tenant_address=None,
        tenant_usage=None,
        owner_name="甲方A",
        owner_contact=None,
        owner_phone=None,
    )
    contract.agency_detail = None
    contract.assets = []
    return contract


class TestContractCorrectionFlow:
    async def test_start_correction_should_clone_active_contract_with_audit_context(
        self,
    ):
        service = ContractGroupService()
        source_contract = _make_contract(status=ContractLifecycleStatus.ACTIVE)
        cloned_contract = _make_contract(
            contract_id="contract-002",
            contract_number="HT-2026-0001-C01",
            status=ContractLifecycleStatus.DRAFT,
        )

        with (
            patch.object(
                service,
                "_get_contract_or_raise",
                new=AsyncMock(return_value=source_contract),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_rent_terms_by_contract",
                new=AsyncMock(
                    return_value=[
                        SimpleNamespace(
                            sort_order=1,
                            start_date=date(2026, 3, 1),
                            end_date=date(2026, 12, 31),
                            monthly_rent=Decimal("10000"),
                            management_fee=Decimal("0"),
                            other_fees=Decimal("0"),
                            notes=None,
                        )
                    ]
                ),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.create",
                new=AsyncMock(return_value=cloned_contract),
            ) as mock_create_contract,
            patch(
                "src.services.contract.contract_group_service.contract_crud.list_scan_documents_by_contract",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.create_audit_log",
                new=AsyncMock(),
            ) as mock_create_audit_log,
        ):
            result = await service.start_correction(
                AsyncMock(),
                contract_id=source_contract.contract_id,
                reason="租金条款调整",
                current_user="user-001",
                operator_name="测试用户",
            )

        assert result is cloned_contract
        assert mock_create_contract.await_args.kwargs["data"]["status"] == "DRAFT"
        assert (
            mock_create_contract.await_args.kwargs["data"]["lessor_name_snapshot"]
            == "签署甲方"
        )
        assert (
            mock_create_contract.await_args.kwargs["data"]["lessee_name_snapshot"]
            == "签署乙方"
        )
        assert (
            mock_create_contract.await_args.kwargs["lease_detail_data"]["tenant_name"]
            == "签署乙方"
        )
        assert "review_status" not in mock_create_contract.await_args.kwargs["data"]
        audit_payload = mock_create_audit_log.await_args.kwargs["data"]
        assert "review_status_old" not in audit_payload
        assert audit_payload["context"]["affected_contract_ids"] == [
            source_contract.contract_id,
            cloned_contract.contract_id,
        ]
        assert (
            audit_payload["context"]["correction_source_contract_id"]
            == source_contract.contract_id
        )

    async def test_start_correction_should_reject_non_active_contract(self):
        service = ContractGroupService()
        source_contract = _make_contract(status=ContractLifecycleStatus.TERMINATED)

        with patch.object(
            service,
            "_get_contract_or_raise",
            new=AsyncMock(return_value=source_contract),
        ):
            with pytest.raises(OperationNotAllowedError, match="生效中"):
                await service.start_correction(
                    AsyncMock(),
                    contract_id=source_contract.contract_id,
                    reason="租金条款调整",
                )

    async def test_update_rent_term_should_reject_non_draft_contract(self):
        service = ContractGroupService()
        rent_term = SimpleNamespace(
            rent_term_id="term-001",
            contract_id="contract-001",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
            monthly_rent=Decimal("10000"),
            management_fee=Decimal("0"),
            other_fees=Decimal("0"),
        )
        active_contract = _make_contract()

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get_rent_term",
                new=AsyncMock(return_value=rent_term),
            ),
            patch.object(
                service,
                "_get_contract_or_raise",
                new=AsyncMock(return_value=active_contract),
            ),
        ):
            with pytest.raises(OperationNotAllowedError, match="纠错草稿"):
                await service.update_rent_term(
                    AsyncMock(),
                    contract_id="contract-001",
                    rent_term_id="term-001",
                    obj_in=ContractRentTermUpdate(monthly_rent=Decimal("12000")),
                )

    async def test_finalize_correction_should_fail_closed_when_impacted_paid_entries_exist(
        self,
    ):
        service = ContractGroupService()
        draft_contract = _make_contract(
            contract_id="draft-001",
            contract_number="HT-2026-0001-C01",
            status=ContractLifecycleStatus.DRAFT,
        )
        draft_contract.correction_source_contract_id = "source-001"
        source_contract = _make_contract(
            contract_id="source-001",
            contract_number="HT-2026-0001",
            status=ContractLifecycleStatus.ACTIVE,
        )

        with (
            patch.object(
                service,
                "_get_contract_or_raise",
                new=AsyncMock(return_value=draft_contract),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.get",
                new=AsyncMock(return_value=source_contract),
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.get_party",
                new=AsyncMock(
                    side_effect=[
                        SimpleNamespace(id="party-lessor", name="签署甲方"),
                        SimpleNamespace(id="party-lessee", name="签署乙方"),
                    ]
                ),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_rent_terms_by_contract",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.services.contract.contract_group_service.ledger_service_v2.reverse_correction_source_entries",
                new=AsyncMock(
                    side_effect=OperationNotAllowedError("存在已支付账期，需先人工处理")
                ),
            ),
        ):
            with pytest.raises(OperationNotAllowedError, match="已支付账期"):
                await service.finalize_correction(
                    AsyncMock(),
                    contract_id=draft_contract.contract_id,
                    current_user="operator-001",
                    operator_name="操作员",
                )

    async def test_finalize_correction_should_refresh_party_name_snapshots(
        self,
    ) -> None:
        service = ContractGroupService()
        draft_contract = _make_contract(
            contract_id="draft-001",
            contract_number="HT-2026-0001-C01",
            status=ContractLifecycleStatus.DRAFT,
        )
        draft_contract.correction_source_contract_id = "source-001"
        draft_contract.lessor_name_snapshot = "旧甲方"
        draft_contract.lessee_name_snapshot = "旧乙方"
        source_contract = _make_contract(
            contract_id="source-001",
            contract_number="HT-2026-0001",
            status=ContractLifecycleStatus.ACTIVE,
        )

        async def _get_party(_db: MagicMock, *, party_id: str) -> SimpleNamespace:
            names = {
                "party-lessor": "定稿时甲方",
                "party-lessee": "定稿时乙方",
            }
            return SimpleNamespace(id=party_id, name=names[party_id])

        with (
            patch.object(
                service,
                "_get_contract_or_raise",
                new=AsyncMock(return_value=draft_contract),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.get",
                new=AsyncMock(return_value=source_contract),
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.get_party",
                new=AsyncMock(side_effect=_get_party),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_rent_terms_by_contract",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.services.contract.contract_group_service.ledger_service_v2.reverse_correction_source_entries",
                new=AsyncMock(return_value=[]),
            ),
            patch.object(
                service,
                "_transition_contract",
                new=AsyncMock(side_effect=[source_contract, draft_contract]),
            ) as mock_transition,
            patch(
                "src.services.contract.contract_group_service.ledger_service_v2.generate_ledger_on_activation",
                new=AsyncMock(return_value=[]),
            ),
        ):
            result = await service.finalize_correction(
                AsyncMock(),
                contract_id=draft_contract.contract_id,
                current_user="operator-001",
                operator_name="操作员",
            )

        assert result is draft_contract
        assert draft_contract.lease_detail.tenant_name == "定稿时乙方"
        assert mock_transition.await_args_list[1].kwargs["extra_updates"] == {
            "lessor_name_snapshot": "定稿时甲方",
            "lessee_name_snapshot": "定稿时乙方",
        }
