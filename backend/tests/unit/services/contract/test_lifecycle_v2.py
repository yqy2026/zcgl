"""Unit tests for the minimal contract lifecycle service."""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import InvalidRequestError, OperationNotAllowedError
from src.models.contract_group import Contract, ContractLifecycleStatus
from src.services.contract.contract_group_service import ContractGroupService

pytestmark = pytest.mark.asyncio


def _make_contract(
    *,
    contract_id: str = "contract-001",
    status: ContractLifecycleStatus = ContractLifecycleStatus.ACTIVE,
    sign_date: date | None = date(2026, 3, 1),
    data_status: str = "正常",
) -> MagicMock:
    contract = MagicMock(spec=Contract)
    contract.contract_id = contract_id
    contract.contract_group_id = "group-001"
    contract.status = status
    contract.sign_date = sign_date
    contract.data_status = data_status
    contract.lessor_party_id = "party-lessor"
    contract.lessee_party_id = "party-lessee"
    contract.correction_source_contract_id = None
    contract.updated_by = None
    contract.updated_at = datetime(2026, 3, 1, 10, 0, 0)
    return contract


def _apply_update(db_obj: MagicMock, data: dict) -> MagicMock:
    for key, value in data.items():
        setattr(db_obj, key, value)
    return db_obj


class TestContractLifecycleV2:
    async def test_expire_is_not_a_contract_operation(self) -> None:
        service = ContractGroupService()

        assert not hasattr(service, "expire")

    async def test_terminate_requires_reason(self) -> None:
        service = ContractGroupService()
        contract = _make_contract(status=ContractLifecycleStatus.ACTIVE)

        with patch.object(
            service,
            "_get_contract_or_raise",
            new=AsyncMock(return_value=contract),
        ):
            with pytest.raises(InvalidRequestError, match="reason"):
                await service.terminate_contract_v2(
                    AsyncMock(),
                    contract_id=contract.contract_id,
                    reason="",
                    current_user="user-001",
                    operator_name="tester",
                )

    async def test_void_rejects_active_contract_even_without_ledger(self) -> None:
        service = ContractGroupService()
        contract = _make_contract(status=ContractLifecycleStatus.ACTIVE)

        with (
            patch.object(
                service,
                "_get_contract_or_raise",
                new=AsyncMock(return_value=contract),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.has_contract_ledger_entries",
                new=AsyncMock(return_value=False),
            ),
        ):
            with pytest.raises(OperationNotAllowedError):
                await service.void_contract(
                    AsyncMock(),
                    contract_id=contract.contract_id,
                    reason="void for test",
                    current_user="user-001",
                    operator_name="tester",
                )

    async def test_finalize_correction_replaces_source_and_generates_ledger(
        self,
    ) -> None:
        service = ContractGroupService()
        draft_contract = _make_contract(
            contract_id="draft-001",
            status=ContractLifecycleStatus.DRAFT,
        )
        draft_contract.correction_source_contract_id = "source-001"
        source_contract = _make_contract(
            contract_id="source-001",
            status=ContractLifecycleStatus.ACTIVE,
        )

        with (
            patch.object(
                service,
                "_get_contract_or_raise",
                new=AsyncMock(return_value=draft_contract),
            ),
            patch.object(
                service,
                "_build_party_name_snapshots",
                new=AsyncMock(
                    return_value={
                        "lessor_name_snapshot": "甲方",
                        "lessee_name_snapshot": "乙方",
                    }
                ),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.get",
                new=AsyncMock(return_value=source_contract),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_crud.update",
                new=AsyncMock(
                    side_effect=lambda db, db_obj, data, commit=False: _apply_update(
                        db_obj, data
                    )
                ),
            ),
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.create_audit_log",
                new=AsyncMock(),
            ) as mock_create_audit_log,
            patch(
                "src.services.contract.contract_group_service.contract_group_crud.list_rent_terms_by_contract",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.services.contract.contract_group_service.ledger_service_v2.reverse_correction_source_entries",
                new=AsyncMock(return_value=["entry-001"]),
            ) as mock_reverse_entries,
            patch(
                "src.services.contract.contract_group_service.ledger_service_v2.generate_ledger_on_activation",
                new=AsyncMock(return_value=[]),
            ) as mock_generate_ledger,
        ):
            db = AsyncMock()
            result = await service.finalize_correction(
                db,
                contract_id=draft_contract.contract_id,
                reason="rent terms changed",
                current_user="reviewer-001",
                operator_name="operator",
            )

        assert result.status == ContractLifecycleStatus.ACTIVE
        assert source_contract.status == ContractLifecycleStatus.TERMINATED
        mock_reverse_entries.assert_awaited_once()
        mock_generate_ledger.assert_awaited_once()
        db.commit.assert_awaited_once()
        contexts = [
            call.kwargs["data"].get("context")
            for call in mock_create_audit_log.await_args_list
        ]
        assert contexts[0]["voided_entry_ids"] == ["entry-001"]
        assert {
            call.kwargs["data"]["action"]
            for call in mock_create_audit_log.await_args_list
        } == {"finalize_correction"}

    async def test_finalize_correction_rejects_non_correction_draft(self) -> None:
        service = ContractGroupService()
        draft_contract = _make_contract(
            contract_id="draft-001",
            status=ContractLifecycleStatus.DRAFT,
        )
        draft_contract.correction_source_contract_id = None

        with patch.object(
            service,
            "_get_contract_or_raise",
            new=AsyncMock(return_value=draft_contract),
        ):
            with pytest.raises(OperationNotAllowedError):
                await service.finalize_correction(
                    AsyncMock(),
                    contract_id=draft_contract.contract_id,
                )
