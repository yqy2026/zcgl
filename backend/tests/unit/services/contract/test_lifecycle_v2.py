"""
单元测试：合同生命周期 V2（M2-T1）。

覆盖范围：
  - submit_review / approve / reject / terminate / void
  - 合同组批量提审的原子校验
  - 审计日志写入
"""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import InvalidRequestError, OperationNotAllowedError
from src.models.contract_group import (
    Contract,
    ContractLifecycleStatus,
    ContractReviewStatus,
)
from src.services.contract.contract_group_service import ContractGroupService

pytestmark = pytest.mark.asyncio


def _make_contract(
    *,
    contract_id: str = "contract-001",
    status: ContractLifecycleStatus = ContractLifecycleStatus.DRAFT,
    review_status: ContractReviewStatus = ContractReviewStatus.DRAFT,
    sign_date: date | None = date(2026, 3, 1),
    data_status: str = "正常",
) -> MagicMock:
    contract = MagicMock(spec=Contract)
    contract.contract_id = contract_id
    contract.contract_group_id = "group-001"
    contract.status = status
    contract.review_status = review_status
    contract.sign_date = sign_date
    contract.data_status = data_status
    contract.lessor_party_id = "party-lessor"
    contract.lessee_party_id = "party-lessee"
    contract.review_by = None
    contract.review_reason = None
    contract.reviewed_at = None
    contract.updated_by = None
    contract.updated_at = datetime(2026, 3, 1, 10, 0, 0)
    contract.version = 1
    return contract


def _apply_update(db_obj: MagicMock, data: dict) -> MagicMock:
    for key, value in data.items():
        setattr(db_obj, key, value)
    return db_obj


class TestContractLifecycleV2:
    async def test_submit_review_updates_status_and_writes_audit_log(self):
        service = ContractGroupService()
        submit_review = getattr(service, "submit_review", None)
        assert submit_review is not None, "ContractGroupService.submit_review 尚未实现"

        contract = _make_contract()

        with (
            patch(
                "src.services.contract.contract_group_service.contract_crud.get",
                new=AsyncMock(return_value=contract),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new=AsyncMock(
                    return_value=MagicMock(
                        contract_group_id="group-001",
                        operator_party_id="party-operator",
                        owner_party_id="party-owner",
                    )
                ),
            ),
            patch(
                "src.services.contract.contract_group_service.party_service.assert_parties_approved",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.services.contract.contract_group_service.select",
                wraps=__import__("sqlalchemy").select,
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.update",
                new=AsyncMock(
                    side_effect=lambda db, db_obj, data, commit=False: _apply_update(
                        db_obj, data
                    )
                ),
            ) as mock_update,
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.create_audit_log",
                new=AsyncMock(),
            ) as mock_create_audit_log,
        ):
            db = AsyncMock()
            db.execute.return_value = MagicMock(all=MagicMock(return_value=[]))
            result, warnings = await submit_review(
                db,
                contract_id=contract.contract_id,
                current_user="user-001",
                operator_name="测试用户",
            )

        assert result.status == ContractLifecycleStatus.PENDING_REVIEW
        assert result.review_status == ContractReviewStatus.PENDING
        assert warnings == []
        mock_update.assert_awaited_once()
        audit_payload = mock_create_audit_log.await_args.kwargs["data"]
        assert audit_payload["action"] == "submit_review"
        assert audit_payload["old_status"] == ContractLifecycleStatus.DRAFT.name
        assert (
            audit_payload["new_status"] == ContractLifecycleStatus.PENDING_REVIEW.name
        )

    async def test_submit_review_rejects_missing_sign_date(self):
        service = ContractGroupService()
        submit_review = getattr(service, "submit_review", None)
        assert submit_review is not None, "ContractGroupService.submit_review 尚未实现"

        contract = _make_contract(sign_date=None)

        with patch(
            "src.services.contract.contract_group_service.contract_crud.get",
            new=AsyncMock(return_value=contract),
        ), patch(
            "src.services.contract.contract_group_service.contract_group_crud.get",
            new=AsyncMock(
                return_value=MagicMock(
                    contract_group_id="group-001",
                    operator_party_id="party-operator",
                    owner_party_id="party-owner",
                )
            ),
        ), patch(
            "src.services.contract.contract_group_service.party_service.assert_parties_approved",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(OperationNotAllowedError, match="sign_date"):
                await submit_review(
                    AsyncMock(),
                    contract_id=contract.contract_id,
                    current_user="user-001",
                    operator_name="测试用户",
                )

    async def test_approve_updates_review_metadata_and_audit_log(self):
        service = ContractGroupService()
        approve = getattr(service, "approve", None)
        assert approve is not None, "ContractGroupService.approve 尚未实现"

        contract = _make_contract(
            status=ContractLifecycleStatus.PENDING_REVIEW,
            review_status=ContractReviewStatus.PENDING,
        )

        with (
            patch(
                "src.services.contract.contract_group_service.contract_crud.get",
                new=AsyncMock(return_value=contract),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.update",
                new=AsyncMock(
                    side_effect=lambda db, db_obj, data, commit=False: _apply_update(
                        db_obj, data
                    )
                ),
            ) as mock_update,
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.create_audit_log",
                new=AsyncMock(),
            ) as mock_create_audit_log,
            patch(
                "src.services.contract.contract_group_service.ledger_service_v2.generate_ledger_on_activation",
                new=AsyncMock(return_value=[]),
            ) as mock_generate_ledger,
        ):
            result = await approve(
                AsyncMock(),
                contract_id=contract.contract_id,
                current_user="reviewer-001",
                operator_name="审核员",
            )

        assert result.status == ContractLifecycleStatus.ACTIVE
        assert result.review_status == ContractReviewStatus.APPROVED
        assert result.review_by == "审核员"
        mock_update.assert_awaited_once()
        mock_generate_ledger.assert_awaited_once()
        assert mock_create_audit_log.await_args.kwargs["data"]["action"] == "approve"

    async def test_reject_requires_reason(self):
        service = ContractGroupService()
        reject = getattr(service, "reject", None)
        assert reject is not None, "ContractGroupService.reject 尚未实现"

        contract = _make_contract(
            status=ContractLifecycleStatus.PENDING_REVIEW,
            review_status=ContractReviewStatus.PENDING,
        )

        with patch(
            "src.services.contract.contract_group_service.contract_crud.get",
            new=AsyncMock(return_value=contract),
        ):
            with pytest.raises(InvalidRequestError, match="reason"):
                await reject(
                    AsyncMock(),
                    contract_id=contract.contract_id,
                    reason="",
                    current_user="reviewer-001",
                    operator_name="审核员",
                )

    async def test_terminate_requires_reason(self):
        service = ContractGroupService()
        terminate_contract_v2 = getattr(service, "terminate_contract_v2", None)
        assert terminate_contract_v2 is not None, (
            "ContractGroupService.terminate_contract_v2 尚未实现"
        )

        contract = _make_contract(status=ContractLifecycleStatus.ACTIVE)

        with patch(
            "src.services.contract.contract_group_service.contract_crud.get",
            new=AsyncMock(return_value=contract),
        ):
            with pytest.raises(InvalidRequestError, match="reason"):
                await terminate_contract_v2(
                    AsyncMock(),
                    contract_id=contract.contract_id,
                    reason="",
                    current_user="user-001",
                    operator_name="测试用户",
                )

    async def test_void_rejects_active_contract_even_without_ledger(self):
        service = ContractGroupService()
        void_contract = getattr(service, "void_contract", None)
        assert void_contract is not None, "ContractGroupService.void_contract 尚未实现"

        contract = _make_contract(status=ContractLifecycleStatus.ACTIVE)

        with (
            patch(
                "src.services.contract.contract_group_service.contract_crud.get",
                new=AsyncMock(return_value=contract),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.has_contract_ledger_entries",
                new=AsyncMock(return_value=False),
            ),
        ):
            with pytest.raises(OperationNotAllowedError, match="先终止"):
                await void_contract(
                    AsyncMock(),
                    contract_id=contract.contract_id,
                    reason="测试作废",
                    current_user="user-001",
                    operator_name="测试用户",
                )

    async def test_submit_group_review_collects_validation_errors_before_mutation(self):
        service = ContractGroupService()
        submit_group_review = getattr(service, "submit_group_review", None)
        assert submit_group_review is not None, (
            "ContractGroupService.submit_group_review 尚未实现"
        )

        group = MagicMock(contract_group_id="group-001")
        draft_ok = _make_contract(contract_id="draft-ok")
        draft_bad = _make_contract(contract_id="draft-bad", sign_date=None)
        pending = _make_contract(
            contract_id="pending-001",
            status=ContractLifecycleStatus.PENDING_REVIEW,
            review_status=ContractReviewStatus.PENDING,
        )

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new=AsyncMock(return_value=group),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.list_by_group",
                new=AsyncMock(return_value=[draft_ok, draft_bad, pending]),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.update",
                new=AsyncMock(),
            ) as mock_update,
        ):
            with pytest.raises(InvalidRequestError, match="draft-bad"):
                await submit_group_review(
                    AsyncMock(),
                    group_id="group-001",
                    current_user="user-001",
                    operator_name="测试用户",
                )

        mock_update.assert_not_called()

    async def test_submit_group_review_should_aggregate_asset_warnings(self):
        service = ContractGroupService()
        submit_group_review = getattr(service, "submit_group_review", None)
        assert submit_group_review is not None, (
            "ContractGroupService.submit_group_review 尚未实现"
        )

        group = MagicMock(contract_group_id="group-001")
        draft_a = _make_contract(contract_id="draft-a")
        draft_b = _make_contract(contract_id="draft-b")

        with (
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.get",
                new=AsyncMock(return_value=group),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.list_by_group",
                new=AsyncMock(return_value=[draft_a, draft_b]),
            ),
            patch.object(
                service,
                "submit_review",
                new=AsyncMock(
                    side_effect=[
                        (draft_a, ["合同 A: 关联资产 A 尚未审核通过"]),
                        (draft_b, ["合同 B: 关联资产 B 尚未审核通过"]),
                    ]
                ),
            ) as mock_submit_review,
        ):
            db = AsyncMock()
            result = await submit_group_review(
                db,
                group_id="group-001",
                current_user="user-001",
                operator_name="测试用户",
            )

        assert result["updated_count"] == 2
        assert result["warnings"] == [
            "合同 A: 关联资产 A 尚未审核通过",
            "合同 B: 关联资产 B 尚未审核通过",
        ]
        mock_submit_review.assert_awaited()
        db.commit.assert_awaited_once()
