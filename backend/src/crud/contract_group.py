"""
CRUD helpers for ContractGroup（合同组）。

单表操作，业务逻辑由 Service 层保证。
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.asset import Asset
from ..models.associations import contract_group_assets
from ..models.contract_group import ContractGroup


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CRUDContractGroup:
    """ContractGroup CRUD 操作。"""

    async def create(
        self,
        db: AsyncSession,
        *,
        data: dict[str, Any],
        asset_ids: list[str] | None = None,
        commit: bool = True,
    ) -> ContractGroup:
        """创建合同组，可选关联资产。"""
        group = ContractGroup(**data)
        db.add(group)
        await db.flush()

        if asset_ids:
            await self._replace_assets(db, group.contract_group_id, asset_ids)

        if commit:
            await db.commit()
            await db.refresh(group)
        return group

    async def get(
        self,
        db: AsyncSession,
        group_id: str,
        *,
        load_contracts: bool = False,
    ) -> ContractGroup | None:
        stmt = select(ContractGroup).where(
            ContractGroup.contract_group_id == group_id
        )
        if load_contracts:
            stmt = stmt.options(selectinload(ContractGroup.contracts))
        return (await db.execute(stmt)).scalars().first()

    async def get_by_code(
        self, db: AsyncSession, group_code: str
    ) -> ContractGroup | None:
        stmt = select(ContractGroup).where(ContractGroup.group_code == group_code)
        return (await db.execute(stmt)).scalars().first()

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ContractGroup,
        data: dict[str, Any],
        asset_ids: list[str] | None = None,
        commit: bool = True,
    ) -> ContractGroup:
        """更新合同组字段，可选整体替换资产关联。"""
        for key, value in data.items():
            setattr(db_obj, key, value)
        db_obj.updated_at = _utcnow()
        db_obj.version = (db_obj.version or 0) + 1

        if asset_ids is not None:
            await self._replace_assets(db, db_obj.contract_group_id, asset_ids)

        if commit:
            await db.commit()
            await db.refresh(db_obj)
        return db_obj

    async def soft_delete(
        self,
        db: AsyncSession,
        *,
        db_obj: ContractGroup,
        commit: bool = True,
    ) -> ContractGroup:
        """逻辑删除：data_status → '已删除'。"""
        db_obj.data_status = "已删除"
        db_obj.updated_at = _utcnow()
        if commit:
            await db.commit()
            await db.refresh(db_obj)
        return db_obj

    async def list_by_filters(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str | None = None,
        owner_party_id: str | None = None,
        revenue_mode: str | None = None,
        data_status: str = "正常",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ContractGroup], int]:
        """分页查询合同组，返回 (items, total)。"""
        stmt = select(ContractGroup).where(ContractGroup.data_status == data_status)

        if operator_party_id is not None:
            stmt = stmt.where(
                ContractGroup.operator_party_id == operator_party_id
            )
        if owner_party_id is not None:
            stmt = stmt.where(ContractGroup.owner_party_id == owner_party_id)
        if revenue_mode is not None:
            stmt = stmt.where(ContractGroup.revenue_mode == revenue_mode)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total: int = (await db.execute(count_stmt)).scalar_one()

        items_stmt = (
            stmt.order_by(ContractGroup.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list((await db.execute(items_stmt)).scalars().all())
        return items, total

    async def count_by_operator_month(
        self,
        db: AsyncSession,
        *,
        operator_party_id: str,
        year_month: str,
    ) -> int:
        """统计指定运营方当月已有的合同组数量（用于 group_code SEQ 生成）。"""
        stmt = select(func.count()).where(
            ContractGroup.operator_party_id == operator_party_id,
            ContractGroup.group_code.like(f"%-{year_month}-%"),
        )
        return (await db.execute(stmt)).scalar_one()

    async def _replace_assets(
        self,
        db: AsyncSession,
        group_id: str,
        asset_ids: list[str],
    ) -> None:
        """整体替换合同组的资产关联（先删后插）。"""
        await db.execute(
            contract_group_assets.delete().where(  # type: ignore[attr-defined]
                contract_group_assets.c.contract_group_id == group_id
            )
        )
        if not asset_ids:
            return
        # 验证资产存在
        exist_stmt = select(Asset.id).where(Asset.id.in_(asset_ids))
        existing_ids = set((await db.execute(exist_stmt)).scalars().all())
        rows = [
            {"contract_group_id": group_id, "asset_id": aid, "created_at": _utcnow()}
            for aid in asset_ids
            if aid in existing_ids
        ]
        if rows:
            await db.execute(contract_group_assets.insert(), rows)  # type: ignore[attr-defined]


contract_group_crud = CRUDContractGroup()
