"""
CRUD helpers for Contract（合同基表）。

单表操作，业务逻辑由 Service 层保证。
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.asset import Asset
from ..models.associations import contract_assets
from ..models.contract_group import (
    AgencyAgreementDetail,
    Contract,
    ContractLifecycleStatus,
    LeaseContractDetail,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CRUDContract:
    """Contract CRUD 操作。"""

    async def create(
        self,
        db: AsyncSession,
        *,
        data: dict[str, Any],
        lease_detail_data: dict[str, Any] | None = None,
        agency_detail_data: dict[str, Any] | None = None,
        asset_ids: list[str] | None = None,
        commit: bool = True,
    ) -> Contract:
        """创建合同，可选同步创建明细和资产关联。"""
        contract = Contract(**data)
        db.add(contract)
        await db.flush()

        if lease_detail_data is not None:
            detail = LeaseContractDetail(
                **lease_detail_data,
                lease_detail_id=str(uuid.uuid4()),
                contract_id=contract.contract_id,
            )
            db.add(detail)

        if agency_detail_data is not None:
            detail_agency = AgencyAgreementDetail(
                **agency_detail_data,
                agency_detail_id=str(uuid.uuid4()),
                contract_id=contract.contract_id,
            )
            db.add(detail_agency)

        if asset_ids:
            await self._replace_assets(db, contract.contract_id, asset_ids)

        if commit:
            await db.commit()
            await db.refresh(contract)
        return contract

    async def get(
        self,
        db: AsyncSession,
        contract_id: str,
        *,
        load_details: bool = True,
    ) -> Contract | None:
        stmt = select(Contract).where(Contract.contract_id == contract_id)
        if load_details:
            stmt = stmt.options(
                selectinload(Contract.lease_detail),
                selectinload(Contract.agency_detail),
            )
        return (await db.execute(stmt)).scalars().first()

    async def get_by_contract_number(
        self,
        db: AsyncSession,
        *,
        contract_number: str,
    ) -> Contract | None:
        stmt = select(Contract).where(Contract.contract_number == contract_number)
        return (await db.execute(stmt)).scalars().first()

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: Contract,
        data: dict[str, Any],
        commit: bool = True,
    ) -> Contract:
        for key, value in data.items():
            setattr(db_obj, key, value)
        db_obj.updated_at = _utcnow()
        db_obj.version = (db_obj.version or 0) + 1

        if commit:
            await db.commit()
            await db.refresh(db_obj)
        return db_obj

    async def soft_delete(
        self,
        db: AsyncSession,
        *,
        db_obj: Contract,
        commit: bool = True,
    ) -> Contract:
        db_obj.data_status = "已删除"
        db_obj.updated_at = _utcnow()
        if commit:
            await db.commit()
            await db.refresh(db_obj)
        return db_obj

    async def list_by_group(
        self,
        db: AsyncSession,
        *,
        group_id: str,
        data_status: str = "正常",
        load_details: bool = False,
    ) -> list[Contract]:
        stmt = select(Contract).where(
            Contract.contract_group_id == group_id,
            Contract.data_status == data_status,
        )
        if load_details:
            stmt = stmt.options(
                selectinload(Contract.lease_detail),
                selectinload(Contract.agency_detail),
            )
        return list((await db.execute(stmt)).scalars().all())

    async def count_active_in_group(
        self, db: AsyncSession, *, group_id: str
    ) -> int:
        """统计合同组内生效中（ACTIVE）的合同数量，用于删除前校验。"""
        stmt = select(func.count()).where(
            Contract.contract_group_id == group_id,
            Contract.status == ContractLifecycleStatus.ACTIVE,
            Contract.data_status == "正常",
        )
        return (await db.execute(stmt)).scalar_one()

    async def get_expiring_contracts_async(
        self,
        db: AsyncSession,
        *,
        today: Any,
        warning_date: Any,
    ) -> list[Contract]:
        stmt = (
            select(Contract)
            .where(
                Contract.status == ContractLifecycleStatus.ACTIVE,
                Contract.effective_to <= warning_date,
                Contract.effective_to >= today,
                Contract.data_status == "正常",
            )
            .options(
                selectinload(Contract.lease_detail),
                selectinload(Contract.lessee_party),
            )
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_active_by_asset_id(
        self,
        db: AsyncSession,
        *,
        asset_id: str,
        active_statuses: set[ContractLifecycleStatus] | list[ContractLifecycleStatus],
    ) -> list[Contract]:
        """按资产查询活跃合同，并预加载租赁/代理明细与承租方主体。"""
        normalized_statuses = list(active_statuses)
        if len(normalized_statuses) == 0:
            return []

        stmt = (
            select(Contract)
            .join(
                contract_assets,
                contract_assets.c.contract_id == Contract.contract_id,
            )
            .where(
                contract_assets.c.asset_id == asset_id,
                Contract.status.in_(normalized_statuses),
                Contract.data_status == "正常",
            )
            .options(
                selectinload(Contract.lease_detail),
                selectinload(Contract.agency_detail),
                selectinload(Contract.lessee_party),
            )
        )
        return list((await db.execute(stmt)).scalars().unique().all())

    async def _replace_assets(
        self,
        db: AsyncSession,
        contract_id: str,
        asset_ids: list[str],
    ) -> None:
        """整体替换合同的资产关联。"""
        await db.execute(
            contract_assets.delete().where(  # type: ignore[attr-defined]
                contract_assets.c.contract_id == contract_id
            )
        )
        if not asset_ids:
            return
        exist_stmt = select(Asset.id).where(Asset.id.in_(asset_ids))
        existing_ids = set((await db.execute(exist_stmt)).scalars().all())
        rows = [
            {"contract_id": contract_id, "asset_id": aid, "created_at": _utcnow()}
            for aid in asset_ids
            if aid in existing_ids
        ]
        if rows:
            await db.execute(contract_assets.insert(), rows)  # type: ignore[attr-defined]


contract_crud = CRUDContract()
