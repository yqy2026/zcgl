"""
合同组生命周期 Mixin（提审/审批/驳回/到期/终止/作废/批量提审）及租金条款 CRUD。

从 contract_group_service.py 拆出，减少单文件行数。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exception_handler import (
    InvalidRequestError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from src.crud.contract import contract_crud
from src.crud.contract_group import contract_group_crud
from src.crud.query_builder import PartyFilter
from src.models.asset import Asset, AssetReviewStatus
from src.models.associations import contract_assets
from src.models.contract_group import (
    Contract,
    ContractAuditLog,
    ContractLifecycleStatus,
    ContractRentTerm,
    ContractReviewStatus,
)
from src.schemas.contract_group import (
    ContractDetail,
    ContractRentTermCreate,
    ContractRentTermUpdate,
)
from src.services.contract.ledger_service_v2 import ledger_service_v2
from src.services.party import party_service


class ContractGroupLifecycleMixin:
    """Lifecycle + rent-term 方法，由 ContractGroupService 继承。"""

    # ─── Lifecycle infrastructure ────────────────────────────────────────
    async def _get_contract_or_raise(
        self, db: AsyncSession, *, contract_id: str
    ) -> Contract:
        contract = await contract_crud.get(db, contract_id, load_details=True)
        if contract is None:
            raise ResourceNotFoundError("合同", contract_id)
        return contract

    async def _append_audit_log(
        self,
        db: AsyncSession,
        *,
        contract: Contract,
        action: str,
        old_status: ContractLifecycleStatus | None,
        new_status: ContractLifecycleStatus | None,
        old_review_status: ContractReviewStatus | None,
        new_review_status: ContractReviewStatus | None,
        reason: str | None,
        current_user: str | None,
        operator_name: str | None,
        related_entry_id: str | None = None,
    ) -> ContractAuditLog:
        from src.services.contract.contract_group_service import _utcnow

        data = {
            "log_id": str(uuid.uuid4()),
            "contract_id": contract.contract_id,
            "action": action,
            "old_status": old_status.name if old_status is not None else None,
            "new_status": new_status.name if new_status is not None else None,
            "review_status_old": (
                old_review_status.name if old_review_status is not None else None
            ),
            "review_status_new": (
                new_review_status.name if new_review_status is not None else None
            ),
            "reason": reason,
            "operator_id": current_user,
            "operator_name": operator_name,
            "related_entry_id": related_entry_id,
            "created_at": _utcnow(),
        }
        return await contract_group_crud.create_audit_log(db, data=data, commit=False)

    async def _transition_contract(
        self,
        db: AsyncSession,
        *,
        contract: Contract,
        allowed_statuses: set[ContractLifecycleStatus],
        action: str,
        new_status: ContractLifecycleStatus,
        new_review_status: ContractReviewStatus | None,
        current_user: str | None,
        operator_name: str | None,
        reason: str | None = None,
        related_entry_id: str | None = None,
        review_by: str | None = None,
        reviewed_at: datetime | None = None,
        extra_updates: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> Contract:
        from src.core.exception_handler import OperationNotAllowedError

        if contract.status not in allowed_statuses:
            allowed = sorted(status.value for status in allowed_statuses)
            raise OperationNotAllowedError(
                f"{action} 仅允许在以下状态执行：{allowed}，当前状态：{contract.status.value}"
            )

        old_status = contract.status
        old_review_status = contract.review_status
        update_data: dict[str, Any] = {
            "status": new_status,
            "updated_by": current_user,
        }
        if new_review_status is not None:
            update_data["review_status"] = new_review_status
        if review_by is not None:
            update_data["review_by"] = review_by
        if reviewed_at is not None:
            update_data["reviewed_at"] = reviewed_at
        if reason is not None:
            update_data["review_reason"] = reason
        if extra_updates:
            update_data.update(extra_updates)

        updated_contract = await contract_crud.update(
            db,
            db_obj=contract,
            data=update_data,
            commit=False,
        )
        await self._append_audit_log(
            db,
            contract=updated_contract,
            action=action,
            old_status=old_status,
            new_status=new_status,
            old_review_status=old_review_status,
            new_review_status=updated_contract.review_status,
            reason=reason,
            current_user=current_user,
            operator_name=operator_name,
            related_entry_id=related_entry_id,
        )
        if commit:
            await db.commit()
        return updated_contract

    # ─── Lifecycle ──────────────────────────────────────────────────────

    async def submit_review(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        current_user: str | None = None,
        operator_name: str | None = None,
        commit: bool = True,
    ) -> tuple[Contract, list[str]]:
        from src.services.contract.contract_group_service import (
            validate_sign_date_for_status,
        )

        contract = await self._get_contract_or_raise(db, contract_id=contract_id)
        group = await contract_group_crud.get(db, contract.contract_group_id)
        if group is None:
            raise ResourceNotFoundError("合同组", contract.contract_group_id)
        await party_service.assert_parties_approved(
            db,
            party_ids=[
                contract.lessor_party_id,
                contract.lessee_party_id,
                group.operator_party_id,
                group.owner_party_id,
            ],
            operation="合同提审",
        )
        validate_sign_date_for_status(
            ContractLifecycleStatus.PENDING_REVIEW, contract.sign_date
        )
        stmt = (
            select(Asset.asset_name, Asset.review_status)
            .join(contract_assets, contract_assets.c.asset_id == Asset.id)
            .where(
                contract_assets.c.contract_id == contract_id,
                Asset.review_status != AssetReviewStatus.APPROVED.value,
            )
        )
        non_approved_assets = (await db.execute(stmt)).all()
        asset_warnings = [
            f"关联资产 {row.asset_name} 尚未审核通过（当前状态：{row.review_status}），请注意核实"
            for row in non_approved_assets
        ]

        updated_contract = await self._transition_contract(
            db,
            contract=contract,
            allowed_statuses={ContractLifecycleStatus.DRAFT},
            action="submit_review",
            new_status=ContractLifecycleStatus.PENDING_REVIEW,
            new_review_status=ContractReviewStatus.PENDING,
            current_user=current_user,
            operator_name=operator_name,
            commit=commit,
        )
        return updated_contract, asset_warnings

    async def approve(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        current_user: str | None = None,
        operator_name: str | None = None,
        commit: bool = True,
    ) -> Contract:
        from src.services.contract.contract_group_service import _utcnow

        contract = await self._get_contract_or_raise(db, contract_id=contract_id)
        reviewer = operator_name or current_user
        updated_contract = await self._transition_contract(
            db,
            contract=contract,
            allowed_statuses={ContractLifecycleStatus.PENDING_REVIEW},
            action="approve",
            new_status=ContractLifecycleStatus.ACTIVE,
            new_review_status=ContractReviewStatus.APPROVED,
            current_user=current_user,
            operator_name=operator_name,
            review_by=reviewer,
            reviewed_at=_utcnow(),
            extra_updates={"review_reason": None},
            commit=False,
        )
        await ledger_service_v2.generate_ledger_on_activation(
            db,
            contract_id=contract_id,
        )
        if commit:
            await db.commit()
        return updated_contract

    async def reject(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        reason: str | None,
        current_user: str | None = None,
        operator_name: str | None = None,
        commit: bool = True,
    ) -> Contract:
        from src.services.contract.contract_group_service import _require_reason

        contract = await self._get_contract_or_raise(db, contract_id=contract_id)
        normalized_reason = _require_reason("驳回", reason)
        return await self._transition_contract(
            db,
            contract=contract,
            allowed_statuses={ContractLifecycleStatus.PENDING_REVIEW},
            action="reject",
            new_status=ContractLifecycleStatus.DRAFT,
            new_review_status=ContractReviewStatus.DRAFT,
            current_user=current_user,
            operator_name=operator_name,
            reason=normalized_reason,
            commit=commit,
        )

    async def expire(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        current_user: str | None = None,
        operator_name: str | None = None,
        commit: bool = True,
    ) -> Contract:
        contract = await self._get_contract_or_raise(db, contract_id=contract_id)
        return await self._transition_contract(
            db,
            contract=contract,
            allowed_statuses={ContractLifecycleStatus.ACTIVE},
            action="expire",
            new_status=ContractLifecycleStatus.EXPIRED,
            new_review_status=None,
            current_user=current_user,
            operator_name=operator_name,
            commit=commit,
        )

    async def terminate_contract_v2(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        reason: str | None,
        current_user: str | None = None,
        operator_name: str | None = None,
        commit: bool = True,
    ) -> Contract:
        from src.services.contract.contract_group_service import _require_reason

        contract = await self._get_contract_or_raise(db, contract_id=contract_id)
        normalized_reason = _require_reason("终止", reason)
        return await self._transition_contract(
            db,
            contract=contract,
            allowed_statuses={
                ContractLifecycleStatus.ACTIVE,
                ContractLifecycleStatus.EXPIRED,
            },
            action="terminate",
            new_status=ContractLifecycleStatus.TERMINATED,
            new_review_status=None,
            current_user=current_user,
            operator_name=operator_name,
            reason=normalized_reason,
            commit=commit,
        )

    async def void_contract(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        reason: str | None,
        current_user: str | None = None,
        operator_name: str | None = None,
        related_entry_id: str | None = None,
    ) -> Contract:
        from src.services.contract.contract_group_service import _require_reason

        contract = await self._get_contract_or_raise(db, contract_id=contract_id)
        normalized_reason = _require_reason("作废", reason)
        if contract.status == ContractLifecycleStatus.ACTIVE:
            raise OperationNotAllowedError("ACTIVE 合同必须先终止后才能作废，请先终止")
        has_ledger_entries = await contract_group_crud.has_contract_ledger_entries(
            db,
            contract_id=contract_id,
        )
        if has_ledger_entries:
            raise OperationNotAllowedError("合同已存在台账，请先冲销台账后再作废")

        old_status = contract.status
        old_review_status = contract.review_status
        updated_contract = await contract_crud.update(
            db,
            db_obj=contract,
            data={
                "data_status": "已作废",
                "updated_by": current_user,
                "review_reason": normalized_reason,
            },
            commit=False,
        )
        await self._append_audit_log(
            db,
            contract=updated_contract,
            action="void",
            old_status=old_status,
            new_status=old_status,
            old_review_status=old_review_status,
            new_review_status=old_review_status,
            reason=normalized_reason,
            current_user=current_user,
            operator_name=operator_name,
            related_entry_id=related_entry_id,
        )
        await db.commit()
        return updated_contract

    async def submit_group_review(
        self,
        db: AsyncSession,
        *,
        group_id: str,
        current_user: str | None = None,
        operator_name: str | None = None,
    ) -> dict[str, Any]:
        group = await contract_group_crud.get(db, group_id)
        if group is None:
            raise ResourceNotFoundError("合同组", group_id)

        contracts = await contract_crud.list_by_group(db, group_id=group_id)
        draft_contracts = [
            contract
            for contract in contracts
            if contract.data_status == "正常"
            and contract.status == ContractLifecycleStatus.DRAFT
        ]

        validation_errors: list[str] = []
        for contract in draft_contracts:
            if contract.sign_date is None:
                validation_errors.append(f"{contract.contract_id}: sign_date 不能为空")

        if validation_errors:
            raise InvalidRequestError(
                "批量提审失败，请先补齐草稿合同签订日期: "
                + "; ".join(validation_errors),
                details={"contracts": validation_errors},
            )

        updated_contract_ids: list[str] = []
        warnings: list[str] = []
        for contract in draft_contracts:
            _, contract_warnings = await self.submit_review(
                db,
                contract_id=contract.contract_id,
                current_user=current_user,
                operator_name=operator_name,
                commit=False,
            )
            updated_contract_ids.append(contract.contract_id)
            warnings.extend(contract_warnings)

        if updated_contract_ids:
            await db.commit()

        return {
            "updated_count": len(updated_contract_ids),
            "skipped_count": len(contracts) - len(updated_contract_ids),
            "contract_ids": updated_contract_ids,
            "warnings": warnings,
        }

    # ─── Rent Terms ─────────────────────────────────────────────────────

    async def create_rent_term(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        obj_in: ContractRentTermCreate,
        commit: bool = True,
    ) -> ContractRentTerm:
        from src.services.contract.contract_group_service import (
            _compute_total_monthly_amount,
            _utcnow,
        )

        await self._get_contract_or_raise(db, contract_id=contract_id)
        now = _utcnow()
        total_monthly_amount = _compute_total_monthly_amount(
            obj_in.monthly_rent,
            obj_in.management_fee,
            obj_in.other_fees,
        )
        data = {
            "rent_term_id": str(uuid.uuid4()),
            "contract_id": contract_id,
            "sort_order": obj_in.sort_order,
            "start_date": obj_in.start_date,
            "end_date": obj_in.end_date,
            "monthly_rent": obj_in.monthly_rent,
            "management_fee": obj_in.management_fee,
            "other_fees": obj_in.other_fees,
            "total_monthly_amount": total_monthly_amount,
            "notes": obj_in.notes,
            "created_at": now,
            "updated_at": now,
        }
        return await contract_group_crud.create_rent_term(
            db,
            data=data,
            commit=commit,
        )

    async def list_rent_terms(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> list[ContractRentTerm]:
        await self._get_scoped_contract_or_raise(
            db,
            contract_id=contract_id,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        return await contract_group_crud.list_rent_terms_by_contract(
            db,
            contract_id=contract_id,
        )

    async def update_rent_term(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        rent_term_id: str,
        obj_in: ContractRentTermUpdate,
    ) -> ContractRentTerm:
        from src.services.contract.contract_group_service import (
            _compute_total_monthly_amount,
        )

        rent_term = await contract_group_crud.get_rent_term(
            db, rent_term_id=rent_term_id
        )
        if rent_term is None or rent_term.contract_id != contract_id:
            raise ResourceNotFoundError("租金条款", rent_term_id)

        start_date = (
            obj_in.start_date if obj_in.start_date is not None else rent_term.start_date
        )
        end_date = (
            obj_in.end_date if obj_in.end_date is not None else rent_term.end_date
        )
        if end_date < start_date:
            raise InvalidRequestError("租金条款结束日期不得早于开始日期")

        monthly_rent = (
            obj_in.monthly_rent
            if obj_in.monthly_rent is not None
            else rent_term.monthly_rent
        )
        management_fee = (
            obj_in.management_fee
            if obj_in.management_fee is not None
            else rent_term.management_fee
        )
        other_fees = (
            obj_in.other_fees if obj_in.other_fees is not None else rent_term.other_fees
        )
        data = obj_in.model_dump(exclude_unset=True)
        data["total_monthly_amount"] = _compute_total_monthly_amount(
            monthly_rent,
            management_fee,
            other_fees,
        )
        return await contract_group_crud.update_rent_term(
            db,
            db_obj=rent_term,
            data=data,
        )

    async def delete_rent_term(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        rent_term_id: str,
    ) -> None:
        rent_term = await contract_group_crud.get_rent_term(
            db, rent_term_id=rent_term_id
        )
        if rent_term is None or rent_term.contract_id != contract_id:
            raise ResourceNotFoundError("租金条款", rent_term_id)
        await contract_group_crud.delete_rent_term(db, db_obj=rent_term)

    # ─── Contract detail / delete ────────────────────────────────────────

    async def get_contract_detail(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> ContractDetail:
        """获取单合同详情（含明细）。"""
        contract = await self._get_scoped_contract_or_raise(
            db,
            contract_id=contract_id,
            current_user_id=current_user_id,
            party_filter=party_filter,
            load_details=True,
        )
        return ContractDetail.model_validate(contract)

    async def soft_delete_contract(
        self, db: AsyncSession, *, contract_id: str
    ) -> Contract:
        """
        逻辑删除合同。

        Raises:
            ResourceNotFoundError: 合同不存在
            OperationNotAllowedError: 合同处于生效状态时禁止删除
        """
        contract = await contract_crud.get(db, contract_id)
        if contract is None:
            raise ResourceNotFoundError("合同", contract_id)
        if contract.status == ContractLifecycleStatus.ACTIVE:
            raise OperationNotAllowedError(
                "生效中的合同不可直接删除，请先将合同状态变更为已终止后再操作"
            )
        return await contract_crud.soft_delete(db, db_obj=contract)
