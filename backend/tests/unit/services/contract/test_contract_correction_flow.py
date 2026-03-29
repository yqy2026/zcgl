from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import OperationNotAllowedError
from src.models.contract_group import (
    Contract,
    ContractLifecycleStatus,
    ContractRelationType,
    ContractReviewStatus,
)
from src.schemas.contract_group import ContractRentTermUpdate
from src.services.contract.contract_group_service import ContractGroupService

pytestmark = pytest.mark.asyncio


def _make_contract(
    *,
    contract_id: str = "contract-001",
    contract_number: str = "HT-2026-0001",
    status: ContractLifecycleStatus = ContractLifecycleStatus.ACTIVE,
    review_status: ContractReviewStatus = ContractReviewStatus.APPROVED,
) -> MagicMock:
    contract = MagicMock(spec=Contract)
    contract.contract_id = contract_id
    contract.contract_group_id = "group-001"
    contract.contract_number = contract_number
    contract.status = status
    contract.review_status = review_status
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
    contract.contract_notes = "原始备注"
    contract.source_session_id = None
    contract.review_reason = None
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
    return contract


class TestContractCorrectionFlow:
    async def test_start_correction_should_clone_contract_with_relation_and_audit_context(self):
        service = ContractGroupService()
        source_contract = _make_contract()
        cloned_contract = _make_contract(
            contract_id="contract-002",
            contract_number="HT-2026-0001-C01",
            status=ContractLifecycleStatus.DRAFT,
            review_status=ContractReviewStatus.DRAFT,
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
                "src.services.contract.contract_group_service.contract_group_crud.create_contract_relation",
                new=AsyncMock(),
                create=True,
            ) as mock_create_relation,
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
        assert mock_create_contract.await_args.kwargs["data"]["review_status"] == "DRAFT"
        assert mock_create_relation.await_args.kwargs["data"]["relation_type"] == ContractRelationType.RENEWAL.name
        audit_context = mock_create_audit_log.await_args.kwargs["data"].get("context")
        assert audit_context == {
            "review_scope": "correction",
            "affected_contract_ids": [source_contract.contract_id, cloned_contract.contract_id],
            "change_categories": [],
            "correction_source_contract_id": source_contract.contract_id,
        }

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

    async def test_approve_correction_should_reverse_source_and_activate_successor(self):
        service = ContractGroupService()
        draft_contract = _make_contract(
            contract_id="draft-001",
            contract_number="HT-2026-0001-C01",
            status=ContractLifecycleStatus.PENDING_REVIEW,
            review_status=ContractReviewStatus.PENDING,
        )
        draft_contract.review_reason = "租金条款调整"
        source_contract = _make_contract(
            contract_id="source-001",
            contract_number="HT-2026-0001",
            status=ContractLifecycleStatus.ACTIVE,
            review_status=ContractReviewStatus.APPROVED,
        )

        def apply_update(db_obj: MagicMock, data: dict) -> MagicMock:
            for key, value in data.items():
                setattr(db_obj, key, value)
            return db_obj

        with (
            patch.object(
                service,
                "_get_contract_or_raise",
                new=AsyncMock(return_value=draft_contract),
            ),
            patch.object(
                service,
                "_get_correction_source_contract",
                new=AsyncMock(return_value=source_contract),
                create=True,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.update",
                new=AsyncMock(side_effect=lambda db, db_obj, data, commit=False: apply_update(db_obj, data)),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.create_audit_log",
                new=AsyncMock(),
            ) as mock_create_audit_log,
            patch(
                "src.services.contract.contract_group_service.ledger_service_v2.reverse_correction_source_entries",
                new=AsyncMock(return_value=["entry-2026-04", "entry-2026-05"]),
                create=True,
            ) as mock_reverse_entries,
            patch(
                "src.services.contract.contract_group_service.ledger_service_v2.generate_ledger_on_activation",
                new=AsyncMock(return_value=[]),
            ) as mock_generate_ledger,
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_rent_terms_by_contract",
                new=AsyncMock(
                    return_value=[
                        SimpleNamespace(
                            sort_order=1,
                            start_date=date(2026, 4, 1),
                            end_date=date(2026, 12, 31),
                            monthly_rent=Decimal("12000"),
                            management_fee=Decimal("0"),
                            other_fees=Decimal("0"),
                            notes=None,
                        )
                    ]
                ),
            ),
        ):
            result = await service.approve(
                AsyncMock(),
                contract_id=draft_contract.contract_id,
                current_user="reviewer-001",
                operator_name="审核员",
            )

        assert result.status == ContractLifecycleStatus.ACTIVE
        assert result.review_status == ContractReviewStatus.APPROVED
        assert source_contract.status == ContractLifecycleStatus.TERMINATED
        assert source_contract.review_status == ContractReviewStatus.REVERSED
        assert source_contract.review_reason == "租金条款调整"
        mock_reverse_entries.assert_awaited_once()
        mock_generate_ledger.assert_awaited_once()
        latest_context = mock_create_audit_log.await_args_list[-2].kwargs["data"]["context"]
        assert latest_context == {
            "review_scope": "correction",
            "affected_contract_ids": ["source-001", "draft-001"],
            "change_categories": [],
            "correction_source_contract_id": "source-001",
            "voided_entry_ids": ["entry-2026-04", "entry-2026-05"],
        }

    async def test_approve_correction_should_fail_closed_when_impacted_paid_entries_exist(self):
        service = ContractGroupService()
        draft_contract = _make_contract(
            contract_id="draft-001",
            contract_number="HT-2026-0001-C01",
            status=ContractLifecycleStatus.PENDING_REVIEW,
            review_status=ContractReviewStatus.PENDING,
        )
        draft_contract.review_reason = "租金条款调整"
        source_contract = _make_contract(
            contract_id="source-001",
            contract_number="HT-2026-0001",
            status=ContractLifecycleStatus.ACTIVE,
            review_status=ContractReviewStatus.APPROVED,
        )

        with (
            patch.object(
                service,
                "_get_contract_or_raise",
                new=AsyncMock(return_value=draft_contract),
            ),
            patch.object(
                service,
                "_get_correction_source_contract",
                new=AsyncMock(return_value=source_contract),
                create=True,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_rent_terms_by_contract",
                new=AsyncMock(
                    return_value=[
                        SimpleNamespace(
                            sort_order=1,
                            start_date=date(2026, 4, 1),
                            end_date=date(2026, 12, 31),
                            monthly_rent=Decimal("12000"),
                            management_fee=Decimal("0"),
                            other_fees=Decimal("0"),
                            notes=None,
                        )
                    ]
                ),
            ),
            patch(
                "src.services.contract.contract_group_service.ledger_service_v2.reverse_correction_source_entries",
                new=AsyncMock(side_effect=OperationNotAllowedError("存在已支付账期，需先人工处理")),
                create=True,
            ),
        ):
            with pytest.raises(OperationNotAllowedError, match="已支付账期"):
                await service.approve(
                    AsyncMock(),
                    contract_id=draft_contract.contract_id,
                    current_user="reviewer-001",
                    operator_name="审核员",
                )
