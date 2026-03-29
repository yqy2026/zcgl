from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import OperationNotAllowedError
from src.models.contract_group import (
    Contract,
    ContractLifecycleStatus,
    ContractReviewStatus,
)
from src.services.contract.contract_group_service import ContractGroupService

pytestmark = pytest.mark.asyncio


def _make_contract(
    *,
    contract_id: str,
    status: ContractLifecycleStatus = ContractLifecycleStatus.DRAFT,
    review_status: ContractReviewStatus = ContractReviewStatus.DRAFT,
    contract_notes: str | None = None,
) -> MagicMock:
    contract = MagicMock(spec=Contract)
    contract.contract_id = contract_id
    contract.contract_group_id = "group-001"
    contract.status = status
    contract.review_status = review_status
    contract.sign_date = date(2026, 3, 1)
    contract.data_status = "正常"
    contract.lessor_party_id = "party-lessor"
    contract.lessee_party_id = "party-lessee"
    contract.contract_notes = contract_notes
    contract.review_by = None
    contract.review_reason = None
    contract.reviewed_at = None
    contract.version = 1
    return contract


class TestContractJointReview:
    async def test_submit_review_should_require_group_review_for_critical_change(self):
        service = ContractGroupService()
        draft_contract = _make_contract(contract_id="draft-correction")
        predecessor_contract = _make_contract(
            contract_id="source-contract",
            status=ContractLifecycleStatus.ACTIVE,
            review_status=ContractReviewStatus.APPROVED,
        )

        with (
            patch.object(
                service,
                "_get_contract_or_raise",
                new=AsyncMock(return_value=draft_contract),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new=AsyncMock(
                    return_value=SimpleNamespace(
                        contract_group_id="group-001",
                        operator_party_id="party-operator",
                        owner_party_id="party-owner",
                        revenue_share_rule={"ratio": "90/10"},
                    )
                ),
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.assert_parties_approved",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service,
                "_get_correction_source_contract",
                new=AsyncMock(return_value=predecessor_contract),
                create=True,
            ),
            patch.object(
                service,
                "_classify_change_categories",
                new=AsyncMock(return_value={"rent_terms", "assets"}),
                create=True,
            ),
        ):
            db = AsyncMock()
            db.execute.return_value = SimpleNamespace(all=lambda: [])
            with pytest.raises(OperationNotAllowedError, match="合同组联审"):
                await service.submit_review(
                    db,
                    contract_id=draft_contract.contract_id,
                    current_user="user-001",
                    operator_name="测试用户",
                )

    async def test_submit_review_should_allow_single_review_for_non_critical_change(self):
        service = ContractGroupService()
        draft_contract = _make_contract(
            contract_id="draft-text-only",
            contract_notes="修正备注",
        )
        predecessor_contract = _make_contract(
            contract_id="source-contract",
            status=ContractLifecycleStatus.ACTIVE,
            review_status=ContractReviewStatus.APPROVED,
            contract_notes="原备注",
        )

        with (
            patch.object(
                service,
                "_get_contract_or_raise",
                new=AsyncMock(return_value=draft_contract),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new=AsyncMock(
                    return_value=SimpleNamespace(
                        contract_group_id="group-001",
                        operator_party_id="party-operator",
                        owner_party_id="party-owner",
                        revenue_share_rule=None,
                    )
                ),
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.assert_parties_approved",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service,
                "_get_correction_source_contract",
                new=AsyncMock(return_value=predecessor_contract),
                create=True,
            ),
            patch.object(
                service,
                "_classify_change_categories",
                new=AsyncMock(return_value={"notes"}),
                create=True,
            ),
            patch(
                "src.services.contract.contract_group_service.select",
                wraps=__import__("sqlalchemy").select,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.update",
                new=AsyncMock(side_effect=lambda db, db_obj, data, commit=False: db_obj),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.create_audit_log",
                new=AsyncMock(),
            ) as mock_create_audit_log,
        ):
            db = AsyncMock()
            db.execute.return_value = SimpleNamespace(all=lambda: [])
            result, warnings = await service.submit_review(
                db,
                contract_id=draft_contract.contract_id,
                current_user="user-001",
                operator_name="测试用户",
            )

        assert result is draft_contract
        assert warnings == []
        audit_context = mock_create_audit_log.await_args.kwargs["data"].get("context")
        assert audit_context == {
            "review_scope": "single",
            "affected_contract_ids": [draft_contract.contract_id],
            "change_categories": ["notes"],
            "correction_source_contract_id": predecessor_contract.contract_id,
        }

    async def test_submit_review_should_allow_joint_review_for_critical_change_when_explicitly_requested(
        self,
    ):
        service = ContractGroupService()
        draft_contract = _make_contract(contract_id="draft-correction")
        predecessor_contract = _make_contract(
            contract_id="source-contract",
            status=ContractLifecycleStatus.ACTIVE,
            review_status=ContractReviewStatus.APPROVED,
        )

        with (
            patch.object(
                service,
                "_get_contract_or_raise",
                new=AsyncMock(return_value=draft_contract),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new=AsyncMock(
                    return_value=SimpleNamespace(
                        contract_group_id="group-001",
                        operator_party_id="party-operator",
                        owner_party_id="party-owner",
                        revenue_share_rule={"ratio": "90/10"},
                    )
                ),
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.assert_parties_approved",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service,
                "_get_correction_source_contract",
                new=AsyncMock(return_value=predecessor_contract),
                create=True,
            ),
            patch.object(
                service,
                "_classify_change_categories",
                new=AsyncMock(return_value={"rent_terms", "assets"}),
                create=True,
            ),
            patch(
                "src.services.contract.contract_group_service.select",
                wraps=__import__("sqlalchemy").select,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.update",
                new=AsyncMock(side_effect=lambda db, db_obj, data, commit=False: db_obj),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.create_audit_log",
                new=AsyncMock(),
            ) as mock_create_audit_log,
        ):
            db = AsyncMock()
            db.execute.return_value = SimpleNamespace(all=lambda: [])
            result, warnings = await service.submit_review(
                db,
                contract_id=draft_contract.contract_id,
                current_user="user-001",
                operator_name="测试用户",
                allow_joint_review=True,
                joint_review_contract_ids=["draft-correction", "sibling-001"],
            )

        assert result is draft_contract
        assert warnings == []
        audit_context = mock_create_audit_log.await_args.kwargs["data"].get("context")
        assert audit_context == {
            "review_scope": "joint",
            "affected_contract_ids": ["draft-correction", "sibling-001"],
            "change_categories": ["assets", "rent_terms"],
            "correction_source_contract_id": predecessor_contract.contract_id,
        }
