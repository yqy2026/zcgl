from datetime import date
from typing import Any

from sqlalchemy import String, and_, cast, delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..constants.business_constants import DataStatusValues
from ..constants.rent_contract_constants import PaymentStatus
from ..core.enums import ContractStatus
from ..crud.asset import SensitiveDataHandler
from ..crud.base import CRUDBase
from ..models.associations import rent_contract_assets
from ..models.ownership import Ownership
from ..models.party import Party
from ..models.rent_contract import (
    ContractType,
    RentContract,
    RentDepositLedger,
    RentLedger,
    RentTerm,
    ServiceFeeLedger,
)
from ..schemas.rent_contract import (
    RentContractCreate,
    RentContractUpdate,
    RentLedgerCreate,
    RentLedgerUpdate,
    RentTermCreate,
    RentTermUpdate,
)


class CRUDRentContract(CRUDBase[RentContract, RentContractCreate, RentContractUpdate]):
    """租金合同CRUD操作 - 支持敏感字段加密"""

    def __init__(self, model: type[RentContract]) -> None:
        super().__init__(model)
        # RentContract 模型的敏感字段
        self.sensitive_data_handler = SensitiveDataHandler(
            searchable_fields={
                "owner_phone",  # 业主电话 - 敏感，需要搜索
                "tenant_phone",  # 租户电话 - 敏感，需要搜索
            }
        )

    async def get_async(
        self, db: AsyncSession, id: Any, use_cache: bool = False
    ) -> RentContract | None:
        stmt = select(RentContract).where(
            RentContract.id == id,
            or_(RentContract.data_status.is_(None), RentContract.data_status != "已删除"),
        )
        result = (await db.execute(stmt)).scalars().first()
        if result is not None:
            self.sensitive_data_handler.decrypt_data(result.__dict__)
        return result

    async def get_multi_async(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        use_cache: bool = False,
        **kwargs: Any,
    ) -> list[RentContract]:
        stmt = (
            select(RentContract)
            .where(
                or_(
                    RentContract.data_status.is_(None),
                    RentContract.data_status != "已删除",
                )
            )
            .offset(skip)
            .limit(limit)
        )
        results = list((await db.execute(stmt)).scalars().all())
        for item in results:
            self.sensitive_data_handler.decrypt_data(item.__dict__)
        return results

    async def create_async(
        self,
        db: AsyncSession,
        *,
        obj_in: RentContractCreate | dict[str, Any],
        **kwargs: Any,
    ) -> RentContract:
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            obj_in_data = obj_in.model_dump()
        encrypted_data = self.sensitive_data_handler.encrypt_data(obj_in_data)
        return await super().create(db=db, obj_in=encrypted_data, **kwargs)

    async def update_async(
        self,
        db: AsyncSession,
        *,
        db_obj: RentContract,
        obj_in: RentContractUpdate | dict[str, Any],
        commit: bool = True,
    ) -> RentContract:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        encrypted_data = self._encrypt_update_data(update_data)
        return await super().update(
            db=db, db_obj=db_obj, obj_in=encrypted_data, commit=commit
        )

    def _encrypt_update_data(self, update_data: dict[str, Any]) -> dict[str, Any]:
        """加密更新数据中的敏感字段"""
        encrypted_data = {}
        for field_name, value in update_data.items():
            if field_name in self.sensitive_data_handler.ALL_PII_FIELDS:
                encrypted_data[field_name] = self.sensitive_data_handler.encrypt_field(
                    field_name, value
                )
            else:
                encrypted_data[field_name] = value
        return encrypted_data

    async def get_with_details_async(
        self, db: AsyncSession, id: str
    ) -> RentContract | None:
        stmt = (
            select(RentContract)
            .options(
                selectinload(RentContract.assets),
                selectinload(RentContract.rent_terms),
            )
            .where(
                RentContract.id == id,
                or_(
                    RentContract.data_status.is_(None),
                    RentContract.data_status != "已删除",
                ),
            )
        )
        result = (await db.execute(stmt)).scalars().first()
        if result is not None:
            self.sensitive_data_handler.decrypt_data(result.__dict__)
        return result

    async def get_by_contract_numbers_async(
        self, db: AsyncSession, *, contract_numbers: list[str]
    ) -> list[RentContract]:
        if not contract_numbers:
            return []
        stmt = select(RentContract).where(
            RentContract.contract_number.in_(contract_numbers)
        )
        contracts = list((await db.execute(stmt)).scalars().all())
        for contract in contracts:
            self.sensitive_data_handler.decrypt_data(contract.__dict__)
        return contracts

    async def get_export_contracts_async(
        self,
        db: AsyncSession,
        *,
        contract_ids: list[str] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        owner_party_id: str | None = None,
        manager_party_id: str | None = None,
        owner_party_ids: list[str] | None = None,
        manager_party_ids: list[str] | None = None,
    ) -> list[RentContract]:
        stmt = select(RentContract).options(selectinload(RentContract.assets))
        if contract_ids:
            stmt = stmt.where(RentContract.id.in_(contract_ids))
        if start_date:
            stmt = stmt.where(RentContract.start_date >= start_date)
        if end_date:
            stmt = stmt.where(RentContract.end_date <= end_date)
        resolved_owner_party_ids = self._normalize_scope_ids(
            values=owner_party_ids,
            value=owner_party_id,
        )
        resolved_manager_party_ids = self._normalize_scope_ids(
            values=manager_party_ids,
            value=manager_party_id,
        )
        scope_filters: list[Any] = []
        if resolved_owner_party_ids:
            if len(resolved_owner_party_ids) == 1:
                scope_filters.append(
                    RentContract.owner_party_id == resolved_owner_party_ids[0]
                )
            else:
                scope_filters.append(
                    RentContract.owner_party_id.in_(resolved_owner_party_ids)
                )
        if resolved_manager_party_ids:
            if len(resolved_manager_party_ids) == 1:
                scope_filters.append(
                    RentContract.manager_party_id == resolved_manager_party_ids[0]
                )
            else:
                scope_filters.append(
                    RentContract.manager_party_id.in_(resolved_manager_party_ids)
                )
        if scope_filters:
            stmt = stmt.where(or_(*scope_filters))

        stmt = stmt.order_by(RentContract.created_at.desc())
        contracts = list((await db.execute(stmt)).scalars().all())
        for contract in contracts:
            self.sensitive_data_handler.decrypt_data(contract.__dict__)
        return contracts

    async def get_active_with_assets_async(
        self, db: AsyncSession, *, exclude_contract_id: str | None = None
    ) -> list[RentContract]:
        stmt = (
            select(RentContract)
            .options(selectinload(RentContract.assets))
            .where(RentContract.contract_status == ContractStatus.ACTIVE)
        )
        if exclude_contract_id:
            stmt = stmt.where(RentContract.id != exclude_contract_id)
        return list((await db.execute(stmt)).scalars().all())

    async def get_expiring_contracts_async(
        self, db: AsyncSession, *, today: date, warning_date: date
    ) -> list[RentContract]:
        stmt = select(RentContract).where(
            RentContract.contract_status == ContractStatus.ACTIVE,
            RentContract.end_date <= warning_date,
            RentContract.end_date >= today,
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_multi_with_filters_async(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        contract_number: str | None = None,
        tenant_name: str | None = None,
        asset_id: str | None = None,
        owner_party_id: str | None = None,
        manager_party_id: str | None = None,
        owner_party_ids: list[str] | None = None,
        manager_party_ids: list[str] | None = None,
        ownership_id: str | None = None,  # DEPRECATED alias
        contract_status: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        include_relations: bool = True,
    ) -> tuple[list[RentContract], int]:
        stmt = select(RentContract)
        if include_relations:
            stmt = stmt.options(
                selectinload(RentContract.assets),
                selectinload(RentContract.rent_terms),
            )
        stmt = self._apply_contract_filters_async(
            stmt,
            contract_number=contract_number,
            tenant_name=tenant_name,
            asset_id=asset_id,
            owner_party_id=owner_party_id,
            manager_party_id=manager_party_id,
            owner_party_ids=owner_party_ids,
            manager_party_ids=manager_party_ids,
            ownership_id=ownership_id,  # DEPRECATED alias
            contract_status=contract_status,
            start_date=start_date,
            end_date=end_date,
        )

        from sqlalchemy import desc

        stmt = stmt.order_by(desc(RentContract.created_at)).offset(skip).limit(limit)
        items = list((await db.execute(stmt)).scalars().all())
        for item in items:
            self.sensitive_data_handler.decrypt_data(item.__dict__)

        count_stmt = select(func.count(RentContract.id))
        count_stmt = self._apply_contract_filters_async(
            count_stmt,
            contract_number=contract_number,
            tenant_name=tenant_name,
            asset_id=asset_id,
            owner_party_id=owner_party_id,
            manager_party_id=manager_party_id,
            owner_party_ids=owner_party_ids,
            manager_party_ids=manager_party_ids,
            ownership_id=ownership_id,  # DEPRECATED alias
            contract_status=contract_status,
            start_date=start_date,
            end_date=end_date,
        )
        total = int((await db.execute(count_stmt)).scalar() or 0)

        return items, total

    def _apply_contract_filters_async(
        self,
        stmt: Any,
        *,
        contract_number: str | None,
        tenant_name: str | None,
        asset_id: str | None,
        owner_party_id: str | None,
        manager_party_id: str | None,
        owner_party_ids: list[str] | None,
        manager_party_ids: list[str] | None,
        ownership_id: str | None,  # DEPRECATED alias
        contract_status: str | None,
        start_date: date | None,
        end_date: date | None,
    ) -> Any:
        stmt = stmt.where(
            or_(
                RentContract.data_status.is_(None),
                RentContract.data_status != "已删除",
            )
        )
        if asset_id:
            stmt = stmt.join(
                rent_contract_assets,
                RentContract.id == rent_contract_assets.c.contract_id,
            ).where(rent_contract_assets.c.asset_id == asset_id)

        if contract_number:
            stmt = stmt.where(RentContract.contract_number.contains(contract_number))
        if tenant_name:
            stmt = stmt.where(RentContract.tenant_name.contains(tenant_name))
        if start_date:
            stmt = stmt.where(RentContract.start_date >= start_date)
        if end_date:
            stmt = stmt.where(RentContract.end_date <= end_date)

        resolved_owner_party_ids = self._normalize_scope_ids(
            values=owner_party_ids,
            value=owner_party_id,
        )
        resolved_manager_party_ids = self._normalize_scope_ids(
            values=manager_party_ids,
            value=manager_party_id,
        )

        scope_filters: list[Any] = []
        if resolved_owner_party_ids:
            if len(resolved_owner_party_ids) == 1:
                scope_filters.append(
                    RentContract.owner_party_id == resolved_owner_party_ids[0]
                )
            else:
                scope_filters.append(
                    RentContract.owner_party_id.in_(resolved_owner_party_ids)
                )
        if resolved_manager_party_ids:
            if len(resolved_manager_party_ids) == 1:
                scope_filters.append(
                    RentContract.manager_party_id == resolved_manager_party_ids[0]
                )
            else:
                scope_filters.append(
                    RentContract.manager_party_id.in_(resolved_manager_party_ids)
                )
        legacy_scope_filter = None
        if ownership_id:  # DEPRECATED alias
            legacy_scope_filter = and_(
                RentContract.ownership_id == ownership_id,  # DEPRECATED
                or_(
                    RentContract.owner_party_id.is_(None),
                    RentContract.owner_party_id == "",
                ),
                or_(
                    RentContract.manager_party_id.is_(None),
                    RentContract.manager_party_id == "",
                ),
            )
        if scope_filters:
            if legacy_scope_filter is not None:
                stmt = stmt.where(or_(or_(*scope_filters), legacy_scope_filter))
            else:
                stmt = stmt.where(or_(*scope_filters))
        elif ownership_id:  # DEPRECATED alias
            stmt = stmt.where(RentContract.ownership_id == ownership_id)  # DEPRECATED
        if contract_status:
            stmt = stmt.where(RentContract.contract_status == contract_status)

        return stmt

    @classmethod
    def _normalize_scope_ids(
        cls,
        *,
        values: list[str] | None,
        value: str | None,
    ) -> list[str]:
        normalized_values: list[str] = []
        seen: set[str] = set()

        for item in values or []:
            normalized = str(item).strip()
            if normalized == "" or normalized in seen:
                continue
            normalized_values.append(normalized)
            seen.add(normalized)

        normalized_value = str(value).strip() if value is not None else ""
        if normalized_value != "" and normalized_value not in seen:
            normalized_values.append(normalized_value)

        return normalized_values

    async def count_by_owner_party_async(
        self, db: AsyncSession, owner_party_id: str
    ) -> int:
        """统计产权主体的合同总数"""
        stmt = select(func.count(RentContract.id)).where(
            RentContract.owner_party_id == owner_party_id
        )
        result = await db.execute(stmt)
        return int(result.scalar() or 0)

    async def count_active_by_owner_party_async(
        self, db: AsyncSession, owner_party_id: str
    ) -> int:
        """统计产权主体的活跃合同数（状态为'有效'）"""
        from sqlalchemy import and_

        stmt = select(func.count(RentContract.id)).where(
            and_(
                RentContract.owner_party_id == owner_party_id,
                RentContract.contract_status == "有效",
            )
        )
        result = await db.execute(stmt)
        return int(result.scalar() or 0)

    async def count_by_ownership_async(  # DEPRECATED compatibility path
        self, db: AsyncSession, ownership_id: str  # DEPRECATED alias
    ) -> int:
        stmt = select(func.count(RentContract.id)).where(
            RentContract.ownership_id == ownership_id  # DEPRECATED legacy column
        )
        result = await db.execute(stmt)
        return int(result.scalar() or 0)

    async def count_active_by_ownership_async(  # DEPRECATED compatibility path
        self, db: AsyncSession, ownership_id: str  # DEPRECATED alias
    ) -> int:
        from sqlalchemy import and_

        stmt = select(func.count(RentContract.id)).where(
            and_(
                RentContract.ownership_id == ownership_id,  # DEPRECATED legacy column
                RentContract.contract_status == "有效",
            )
        )
        result = await db.execute(stmt)
        return int(result.scalar() or 0)

    async def get_distinct_ownership_ids_by_owner_party_ids_async(  # DEPRECATED bridge helper
        self,
        db: AsyncSession,
        *,
        owner_party_ids: list[str],
    ) -> list[str]:
        """DEPRECATED: Resolve legacy ownership IDs from owner-party scoped contracts."""
        if not owner_party_ids:
            return []

        stmt = select(func.distinct(RentContract.ownership_id)).where(  # DEPRECATED legacy column
            RentContract.owner_party_id.in_(owner_party_ids),
            RentContract.ownership_id.is_not(None),  # DEPRECATED legacy column
            RentContract.ownership_id != "",  # DEPRECATED legacy column
        )
        ownership_ids = (await db.execute(stmt)).scalars().all()  # DEPRECATED legacy identifiers
        return [str(ownership_id) for ownership_id in ownership_ids if ownership_id]  # DEPRECATED legacy identifiers

    async def get_distinct_owner_party_ids_by_ownership_ids_async(  # DEPRECATED bridge helper
        self,
        db: AsyncSession,
        *,
        ownership_ids: list[str],  # DEPRECATED alias
    ) -> list[str]:
        """DEPRECATED: Resolve owner-party IDs from legacy ownership-scoped contracts."""
        if not ownership_ids:  # DEPRECATED alias
            return []

        stmt = select(func.distinct(RentContract.owner_party_id)).where(
            RentContract.ownership_id.in_(ownership_ids),  # DEPRECATED legacy column + alias
            RentContract.owner_party_id.is_not(None),
            RentContract.owner_party_id != "",
        )
        owner_party_ids = (await db.execute(stmt)).scalars().all()
        return [str(owner_party_id) for owner_party_id in owner_party_ids if owner_party_id]

    async def get_contracts_for_price_calculation_async(
        self,
        db: AsyncSession,
        *,
        contract_type: ContractType | str | None = None,
        contract_status: ContractStatus | str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        owner_party_ids: list[str] | None = None,
        manager_party_ids: list[str] | None = None,
        ownership_ids: list[str] | None = None,  # DEPRECATED alias
    ) -> list[RentContract]:
        """获取用于单价计算的合同（含关联的资产和租金条款）"""
        stmt = select(RentContract).options(
            selectinload(RentContract.assets), selectinload(RentContract.rent_terms)
        )

        if contract_type is not None:
            contract_type_value = (
                contract_type.value
                if isinstance(contract_type, ContractType)
                else str(contract_type)
            )
            # 兼容数据库中 contract_type 仍为 varchar 的场景，避免 enum 类型比较报错
            stmt = stmt.where(
                cast(RentContract.contract_type, String) == contract_type_value
            )
        if contract_status is not None:
            contract_status_value = (
                contract_status.value
                if isinstance(contract_status, ContractStatus)
                else str(contract_status)
            )
            stmt = stmt.where(RentContract.contract_status == contract_status_value)

        if start_date and end_date:
            stmt = stmt.where(RentContract.start_date <= end_date)
        if end_date and start_date:
            stmt = stmt.where(RentContract.end_date >= start_date)

        scope_filters: list[Any] = []
        if owner_party_ids:
            scope_filters.append(RentContract.owner_party_id.in_(owner_party_ids))
        if manager_party_ids:
            scope_filters.append(RentContract.manager_party_id.in_(manager_party_ids))
        if scope_filters:
            stmt = stmt.where(or_(*scope_filters))
        elif ownership_ids:  # DEPRECATED alias
            stmt = stmt.where(RentContract.ownership_id.in_(ownership_ids))  # DEPRECATED

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_contract_status_counts_async(
        self,
        db: AsyncSession,
        *,
        owner_party_ids: list[str] | None = None,
        manager_party_ids: list[str] | None = None,
        ownership_ids: list[str] | None = None,  # DEPRECATED alias
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, int]:
        """按合同状态分组计数（用于续租率计算）"""
        stmt = select(
            RentContract.contract_status, func.count(RentContract.id)
        ).group_by(RentContract.contract_status)

        scope_filters: list[Any] = []
        if owner_party_ids:
            scope_filters.append(RentContract.owner_party_id.in_(owner_party_ids))
        if manager_party_ids:
            scope_filters.append(RentContract.manager_party_id.in_(manager_party_ids))
        if scope_filters:
            stmt = stmt.where(or_(*scope_filters))
        elif ownership_ids:  # DEPRECATED alias
            stmt = stmt.where(RentContract.ownership_id.in_(ownership_ids))  # DEPRECATED

        if start_date and end_date:
            stmt = stmt.where(
                RentContract.end_date.between(start_date, end_date)
            )

        result = await db.execute(stmt)
        return {str(row[0]): int(row[1]) for row in result.all()}


class CRUDRentTerm(CRUDBase[RentTerm, RentTermCreate, RentTermUpdate]):
    """租金条款CRUD操作"""

    async def get_by_contract_async(
        self, db: AsyncSession, contract_id: str
    ) -> list[RentTerm]:
        stmt = (
            select(RentTerm)
            .where(RentTerm.contract_id == contract_id)
            .order_by(RentTerm.start_date)
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_by_contract_ids_async(
        self, db: AsyncSession, *, contract_ids: list[str]
    ) -> list[RentTerm]:
        if not contract_ids:
            return []
        stmt = (
            select(RentTerm)
            .where(RentTerm.contract_id.in_(contract_ids))
            .order_by(RentTerm.contract_id, RentTerm.start_date)
        )
        return list((await db.execute(stmt)).scalars().all())

    async def delete_by_contract_async(self, db: AsyncSession, contract_id: str) -> None:
        stmt = delete(RentTerm).where(RentTerm.contract_id == contract_id)
        await db.execute(stmt)


class CRUDRentLedger(CRUDBase[RentLedger, RentLedgerCreate, RentLedgerUpdate]):
    """租金台账CRUD操作"""

    async def get_multi_with_filters_async(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        contract_id: str | None = None,
        asset_id: str | None = None,
        owner_party_id: str | None = None,
        manager_party_id: str | None = None,
        owner_party_ids: list[str] | None = None,
        manager_party_ids: list[str] | None = None,
        ownership_id: str | None = None,  # DEPRECATED alias
        year_month: str | None = None,
        payment_status: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[RentLedger], int]:
        stmt = select(RentLedger)
        stmt = self._apply_ledger_filters_async(
            stmt,
            contract_id=contract_id,
            asset_id=asset_id,
            owner_party_id=owner_party_id,
            manager_party_id=manager_party_id,
            owner_party_ids=owner_party_ids,
            manager_party_ids=manager_party_ids,
            ownership_id=ownership_id,  # DEPRECATED alias
            year_month=year_month,
            payment_status=payment_status,
            start_date=start_date,
            end_date=end_date,
        )

        from sqlalchemy import desc

        stmt = (
            stmt.order_by(desc(RentLedger.year_month), desc(RentLedger.due_date))
            .offset(skip)
            .limit(limit)
        )
        items = list((await db.execute(stmt)).scalars().all())

        count_stmt = select(func.count(RentLedger.id))
        count_stmt = self._apply_ledger_filters_async(
            count_stmt,
            contract_id=contract_id,
            asset_id=asset_id,
            owner_party_id=owner_party_id,
            manager_party_id=manager_party_id,
            owner_party_ids=owner_party_ids,
            manager_party_ids=manager_party_ids,
            ownership_id=ownership_id,  # DEPRECATED alias
            year_month=year_month,
            payment_status=payment_status,
            start_date=start_date,
            end_date=end_date,
        )
        total = int((await db.execute(count_stmt)).scalar() or 0)

        return items, total

    def _apply_ledger_filters_async(
        self,
        stmt: Any,
        *,
        contract_id: str | None,
        asset_id: str | None,
        owner_party_id: str | None,
        manager_party_id: str | None,
        owner_party_ids: list[str] | None,
        manager_party_ids: list[str] | None,
        ownership_id: str | None,  # DEPRECATED alias
        year_month: str | None,
        payment_status: str | None,
        start_date: date | None,
        end_date: date | None,
    ) -> Any:
        if contract_id:
            stmt = stmt.where(RentLedger.contract_id == contract_id)
        if asset_id:
            stmt = stmt.where(RentLedger.asset_id == asset_id)
        resolved_owner_party_ids = CRUDRentContract._normalize_scope_ids(
            values=owner_party_ids,
            value=owner_party_id,
        )
        resolved_manager_party_ids = CRUDRentContract._normalize_scope_ids(
            values=manager_party_ids,
            value=manager_party_id,
        )
        scope_filters: list[Any] = []
        if resolved_owner_party_ids:
            if len(resolved_owner_party_ids) == 1:
                scope_filters.append(
                    RentLedger.owner_party_id == resolved_owner_party_ids[0]
                )
            else:
                scope_filters.append(
                    RentLedger.owner_party_id.in_(resolved_owner_party_ids)
                )
        if resolved_manager_party_ids:
            stmt = stmt.join(RentContract, RentLedger.contract_id == RentContract.id)
            if len(resolved_manager_party_ids) == 1:
                scope_filters.append(
                    RentContract.manager_party_id == resolved_manager_party_ids[0]
                )
            else:
                scope_filters.append(
                    RentContract.manager_party_id.in_(resolved_manager_party_ids)
                )
        if scope_filters:
            stmt = stmt.where(or_(*scope_filters))
        elif ownership_id:  # DEPRECATED alias
            stmt = stmt.where(RentLedger.ownership_id == ownership_id)  # DEPRECATED
        if year_month:
            stmt = stmt.where(RentLedger.year_month == year_month)
        if payment_status:
            stmt = stmt.where(RentLedger.payment_status == payment_status)
        if start_date:
            stmt = stmt.where(RentLedger.due_date >= start_date)
        if end_date:
            stmt = stmt.where(RentLedger.due_date <= end_date)

        return stmt

    async def get_by_contract_and_month_async(
        self, db: AsyncSession, contract_id: str, year_month: str
    ) -> RentLedger | None:
        from sqlalchemy import and_

        stmt = select(RentLedger).where(
            and_(
                RentLedger.contract_id == contract_id,
                RentLedger.year_month == year_month,
            )
        )
        return (await db.execute(stmt)).scalars().first()

    async def get_multi_by_ids_async(
        self, db: AsyncSession, *, ledger_ids: list[str]
    ) -> list[RentLedger]:
        if not ledger_ids:
            return []
        stmt = select(RentLedger).where(RentLedger.id.in_(ledger_ids))
        return list((await db.execute(stmt)).scalars().all())

    async def get_by_contract_ids_async(
        self, db: AsyncSession, *, contract_ids: list[str]
    ) -> list[RentLedger]:
        if not contract_ids:
            return []
        stmt = (
            select(RentLedger)
            .where(RentLedger.contract_id.in_(contract_ids))
            .order_by(RentLedger.contract_id, RentLedger.year_month)
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_deposit_ledger_by_contract_async(
        self, db: AsyncSession, *, contract_id: str
    ) -> list[RentDepositLedger]:
        stmt = (
            select(RentDepositLedger)
            .where(RentDepositLedger.contract_id == contract_id)
            .order_by(desc(RentDepositLedger.created_at))
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_service_fee_ledger_by_contract_async(
        self, db: AsyncSession, *, contract_id: str
    ) -> list[ServiceFeeLedger]:
        stmt = (
            select(ServiceFeeLedger)
            .where(ServiceFeeLedger.contract_id == contract_id)
            .order_by(desc(ServiceFeeLedger.year_month))
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_service_fee_by_source_ledger_async(
        self, db: AsyncSession, *, source_ledger_id: str
    ) -> ServiceFeeLedger | None:
        stmt = select(ServiceFeeLedger).where(
            ServiceFeeLedger.source_ledger_id == source_ledger_id
        )
        return (await db.execute(stmt)).scalars().first()

    async def get_overdue_with_contract_async(
        self, db: AsyncSession, *, today: date
    ) -> list[RentLedger]:
        stmt = (
            select(RentLedger)
            .options(selectinload(RentLedger.contract))
            .where(
                RentLedger.payment_status.in_(
                    [PaymentStatus.UNPAID, PaymentStatus.PARTIAL]
                ),
                RentLedger.due_date < today,
                RentLedger.data_status == DataStatusValues.ASSET_NORMAL,
            )
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_due_soon_with_contract_async(
        self, db: AsyncSession, *, today: date, warning_date: date
    ) -> list[RentLedger]:
        stmt = (
            select(RentLedger)
            .options(selectinload(RentLedger.contract))
            .where(
                RentLedger.payment_status == PaymentStatus.UNPAID,
                RentLedger.due_date <= warning_date,
                RentLedger.due_date >= today,
                RentLedger.data_status == DataStatusValues.ASSET_NORMAL,
            )
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_existing_year_months_async(
        self, db: AsyncSession, *, contract_id: str, year_months: list[str]
    ) -> set[str]:
        if len(year_months) == 0:
            return set()

        stmt = select(RentLedger.year_month).where(
            RentLedger.contract_id == contract_id,
            RentLedger.year_month.in_(year_months),
        )
        rows = (await db.execute(stmt)).scalars().all()
        return {str(year_month) for year_month in rows if year_month is not None}

    async def sum_due_amount_by_owner_party_async(
        self, db: AsyncSession, owner_party_id: str
    ) -> float:
        """统计产权主体的应收总额（通过合同ID关联）"""
        # 子查询：获取该产权主体下所有合同ID
        contract_ids = select(RentContract.id).where(
            RentContract.owner_party_id == owner_party_id
        )
        # 聚合查询：统计应收总额
        stmt = select(func.coalesce(func.sum(RentLedger.due_amount), 0)).where(
            RentLedger.contract_id.in_(contract_ids)
        )
        result = await db.execute(stmt)
        return float(result.scalar() or 0)

    async def sum_paid_amount_by_owner_party_async(
        self, db: AsyncSession, owner_party_id: str
    ) -> float:
        """统计产权主体的实收总额（通过合同ID关联）"""
        contract_ids = select(RentContract.id).where(
            RentContract.owner_party_id == owner_party_id
        )
        stmt = select(func.coalesce(func.sum(RentLedger.paid_amount), 0)).where(
            RentLedger.contract_id.in_(contract_ids)
        )
        result = await db.execute(stmt)
        return float(result.scalar() or 0)

    async def sum_overdue_amount_by_owner_party_async(
        self, db: AsyncSession, owner_party_id: str
    ) -> float:
        """统计产权主体的欠款总额（通过合同ID关联）"""
        contract_ids = select(RentContract.id).where(
            RentContract.owner_party_id == owner_party_id
        )
        stmt = select(func.coalesce(func.sum(RentLedger.overdue_amount), 0)).where(
            RentLedger.contract_id.in_(contract_ids)
        )
        result = await db.execute(stmt)
        return float(result.scalar() or 0)

    async def sum_due_amount_by_ownership_async(  # DEPRECATED compatibility path
        self, db: AsyncSession, ownership_id: str  # DEPRECATED alias
    ) -> float:
        contract_ids = select(RentContract.id).where(
            RentContract.ownership_id == ownership_id  # DEPRECATED legacy column
        )
        stmt = select(func.coalesce(func.sum(RentLedger.due_amount), 0)).where(
            RentLedger.contract_id.in_(contract_ids)
        )
        result = await db.execute(stmt)
        return float(result.scalar() or 0)

    async def sum_paid_amount_by_ownership_async(  # DEPRECATED compatibility path
        self, db: AsyncSession, ownership_id: str  # DEPRECATED alias
    ) -> float:
        contract_ids = select(RentContract.id).where(
            RentContract.ownership_id == ownership_id  # DEPRECATED legacy column
        )
        stmt = select(func.coalesce(func.sum(RentLedger.paid_amount), 0)).where(
            RentLedger.contract_id.in_(contract_ids)
        )
        result = await db.execute(stmt)
        return float(result.scalar() or 0)

    async def sum_overdue_amount_by_ownership_async(  # DEPRECATED compatibility path
        self, db: AsyncSession, ownership_id: str  # DEPRECATED alias
    ) -> float:
        contract_ids = select(RentContract.id).where(
            RentContract.ownership_id == ownership_id  # DEPRECATED legacy column
        )
        stmt = select(func.coalesce(func.sum(RentLedger.overdue_amount), 0)).where(
            RentLedger.contract_id.in_(contract_ids)
        )
        result = await db.execute(stmt)
        return float(result.scalar() or 0)

    async def get_ledger_statistics_async(
        self,
        db: AsyncSession,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        owner_party_ids: list[str] | None = None,
        manager_party_ids: list[str] | None = None,
        ownership_ids: list[str] | None = None,  # DEPRECATED alias
        asset_ids: list[str] | None = None,
    ) -> tuple[Any, Any, Any, int]:
        """获取租金台账总体统计（总应收/实收/欠款/记录数）"""
        stmt = select(
            func.sum(RentLedger.due_amount).label("total_due"),
            func.sum(RentLedger.paid_amount).label("total_paid"),
            func.sum(RentLedger.overdue_amount).label("total_overdue"),
            func.count(RentLedger.id).label("total_records"),
        )

        filters = []
        if start_date:
            filters.append(RentLedger.due_date >= start_date)
        if end_date:
            filters.append(RentLedger.due_date <= end_date)
        scope_filters: list[Any] = []
        if owner_party_ids:
            scope_filters.append(RentLedger.owner_party_id.in_(owner_party_ids))
        if manager_party_ids:
            stmt = stmt.join(RentContract, RentLedger.contract_id == RentContract.id)
            scope_filters.append(RentContract.manager_party_id.in_(manager_party_ids))
        if scope_filters:
            filters.append(or_(*scope_filters))
        elif ownership_ids:  # DEPRECATED alias
            filters.append(RentLedger.ownership_id.in_(ownership_ids))  # DEPRECATED
        if asset_ids:
            filters.append(RentLedger.asset_id.in_(asset_ids))

        if filters:
            stmt = stmt.where(*filters)

        result = await db.execute(stmt)
        stats = result.first()

        if stats is None:
            return None, None, None, 0

        return (
            stats.total_due,
            stats.total_paid,
            stats.total_overdue,
            stats.total_records or 0,
        )

    async def get_ledger_status_breakdown_async(
        self,
        db: AsyncSession,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        owner_party_ids: list[str] | None = None,
        manager_party_ids: list[str] | None = None,
        ownership_ids: list[str] | None = None,  # DEPRECATED alias
        asset_ids: list[str] | None = None,
    ) -> list[Any]:
        """按支付状态分组统计"""
        stmt = select(
            RentLedger.payment_status,
            func.count(RentLedger.id).label("count"),
            func.sum(RentLedger.due_amount).label("due_amount"),
            func.sum(RentLedger.paid_amount).label("paid_amount"),
        ).group_by(RentLedger.payment_status)

        filters = []
        if start_date:
            filters.append(RentLedger.due_date >= start_date)
        if end_date:
            filters.append(RentLedger.due_date <= end_date)
        scope_filters: list[Any] = []
        if owner_party_ids:
            scope_filters.append(RentLedger.owner_party_id.in_(owner_party_ids))
        if manager_party_ids:
            stmt = stmt.join(RentContract, RentLedger.contract_id == RentContract.id)
            scope_filters.append(RentContract.manager_party_id.in_(manager_party_ids))
        if scope_filters:
            filters.append(or_(*scope_filters))
        elif ownership_ids:  # DEPRECATED alias
            filters.append(RentLedger.ownership_id.in_(ownership_ids))  # DEPRECATED
        if asset_ids:
            filters.append(RentLedger.asset_id.in_(asset_ids))

        if filters:
            stmt = stmt.where(*filters)

        result = await db.execute(stmt)
        return list(result.all())

    async def get_ledger_monthly_breakdown_async(
        self,
        db: AsyncSession,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        owner_party_ids: list[str] | None = None,
        manager_party_ids: list[str] | None = None,
        ownership_ids: list[str] | None = None,  # DEPRECATED alias
        asset_ids: list[str] | None = None,
    ) -> list[Any]:
        """按月份分组统计"""
        stmt = (
            select(
                RentLedger.year_month,
                func.sum(RentLedger.due_amount).label("due_amount"),
                func.sum(RentLedger.paid_amount).label("paid_amount"),
                func.sum(RentLedger.overdue_amount).label("overdue_amount"),
            )
            .group_by(RentLedger.year_month)
            .order_by(RentLedger.year_month)
        )

        filters = []
        if start_date:
            filters.append(RentLedger.due_date >= start_date)
        if end_date:
            filters.append(RentLedger.due_date <= end_date)
        scope_filters: list[Any] = []
        if owner_party_ids:
            scope_filters.append(RentLedger.owner_party_id.in_(owner_party_ids))
        if manager_party_ids:
            stmt = stmt.join(RentContract, RentLedger.contract_id == RentContract.id)
            scope_filters.append(RentContract.manager_party_id.in_(manager_party_ids))
        if scope_filters:
            filters.append(or_(*scope_filters))
        elif ownership_ids:  # DEPRECATED alias
            filters.append(RentLedger.ownership_id.in_(ownership_ids))  # DEPRECATED
        if asset_ids:
            filters.append(RentLedger.asset_id.in_(asset_ids))

        if filters:
            stmt = stmt.where(*filters)

        result = await db.execute(stmt)
        return list(result.all())

    async def get_owner_party_statistics_async(
        self,
        db: AsyncSession,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        owner_party_ids: list[str] | None = None,
        manager_party_ids: list[str] | None = None,
    ) -> list[Any]:
        """产权主体维度统计（JOIN Party + RentContract + RentLedger）"""
        stmt = (
            select(
                Party.id,
                Party.name,
                Party.code,
                func.count(func.distinct(RentContract.id)).label("contract_count"),
                func.sum(RentLedger.due_amount).label("total_due_amount"),
                func.sum(RentLedger.paid_amount).label("total_paid_amount"),
                func.sum(RentLedger.overdue_amount).label("total_overdue_amount"),
            )
            .join(RentContract, RentContract.owner_party_id == Party.id)
            .join(RentLedger, RentLedger.contract_id == RentContract.id)
            .group_by(Party.id, Party.name, Party.code)
        )

        if start_date:
            stmt = stmt.where(RentLedger.due_date >= start_date)
        if end_date:
            stmt = stmt.where(RentLedger.due_date <= end_date)
        if owner_party_ids:
            stmt = stmt.where(Party.id.in_(owner_party_ids))
        if manager_party_ids:
            stmt = stmt.where(RentContract.manager_party_id.in_(manager_party_ids))

        result = await db.execute(stmt)
        return list(result.all())

    async def get_ownership_statistics_async(  # DEPRECATED compatibility path
        self,
        db: AsyncSession,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        manager_party_ids: list[str] | None = None,
        ownership_ids: list[str] | None = None,  # DEPRECATED alias
        legacy_only: bool = False,
    ) -> list[Any]:
        stmt = (
            select(
                Ownership.id,
                Ownership.name,
                Ownership.short_name,
                func.count(RentContract.id).label("contract_count"),
                func.sum(RentLedger.due_amount).label("total_due_amount"),
                func.sum(RentLedger.paid_amount).label("total_paid_amount"),
                func.sum(RentLedger.overdue_amount).label("total_overdue_amount"),
            )
            .join(RentContract, RentContract.ownership_id == Ownership.id)  # DEPRECATED
            .join(RentLedger, RentLedger.contract_id == RentContract.id)
            .group_by(Ownership.id, Ownership.name, Ownership.short_name)
        )

        if start_date:
            stmt = stmt.where(RentLedger.due_date >= start_date)
        if end_date:
            stmt = stmt.where(RentLedger.due_date <= end_date)
        if manager_party_ids:
            stmt = stmt.where(RentContract.manager_party_id.in_(manager_party_ids))
        if ownership_ids:  # DEPRECATED alias
            stmt = stmt.where(Ownership.id.in_(ownership_ids))  # DEPRECATED
        if legacy_only:
            stmt = stmt.where(
                or_(
                    RentContract.owner_party_id.is_(None),
                    RentContract.owner_party_id == "",
                )
            )

        result = await db.execute(stmt)
        return list(result.all())

    async def get_asset_statistics_async(
        self,
        db: AsyncSession,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        owner_party_ids: list[str] | None = None,
        manager_party_ids: list[str] | None = None,
        asset_ids: list[str] | None = None,
    ) -> list[Any]:
        """资产维度统计（JOIN Asset + RentContract + RentLedger）"""
        from ..models.asset import Asset

        stmt = (
            select(
                Asset.id,
                Asset.property_name,
                Asset.address,
                func.count(RentContract.id).label("contract_count"),
                func.sum(RentLedger.due_amount).label("total_due_amount"),
                func.sum(RentLedger.paid_amount).label("total_paid_amount"),
                func.sum(RentLedger.overdue_amount).label("total_overdue_amount"),
            )
            .join(rent_contract_assets, rent_contract_assets.c.asset_id == Asset.id)
            .join(RentContract, RentContract.id == rent_contract_assets.c.contract_id)
            .join(RentLedger, RentLedger.contract_id == RentContract.id)
            .group_by(Asset.id, Asset.property_name, Asset.address)
        )

        if start_date:
            stmt = stmt.where(RentLedger.due_date >= start_date)
        if end_date:
            stmt = stmt.where(RentLedger.due_date <= end_date)
        scope_filters: list[Any] = []
        if owner_party_ids:
            scope_filters.append(RentContract.owner_party_id.in_(owner_party_ids))
        if manager_party_ids:
            scope_filters.append(RentContract.manager_party_id.in_(manager_party_ids))
        if scope_filters:
            stmt = stmt.where(or_(*scope_filters))
        if asset_ids:
            stmt = stmt.where(Asset.id.in_(asset_ids))

        result = await db.execute(stmt)
        return list(result.all())

    async def get_monthly_statistics_async(
        self,
        db: AsyncSession,
        *,
        year: int | None = None,
        start_month: str | None = None,
        end_month: str | None = None,
        owner_party_ids: list[str] | None = None,
        manager_party_ids: list[str] | None = None,
    ) -> list[Any]:
        """月度统计（年月维度聚合）"""
        stmt = (
            select(
                RentLedger.year_month,
                func.count(func.distinct(RentLedger.contract_id)).label("total_contracts"),
                func.sum(RentLedger.due_amount).label("total_due_amount"),
                func.sum(RentLedger.paid_amount).label("total_paid_amount"),
                func.sum(RentLedger.overdue_amount).label("total_overdue_amount"),
            )
            .group_by(RentLedger.year_month)
            .order_by(RentLedger.year_month)
        )

        if year:
            stmt = stmt.where(RentLedger.year_month.like(f"{year}%"))
        if start_month:
            stmt = stmt.where(RentLedger.year_month >= start_month)
        if end_month:
            stmt = stmt.where(RentLedger.year_month <= end_month)
        scope_filters: list[Any] = []
        if owner_party_ids:
            scope_filters.append(RentLedger.owner_party_id.in_(owner_party_ids))
        if manager_party_ids:
            stmt = stmt.join(RentContract, RentLedger.contract_id == RentContract.id)
            scope_filters.append(RentContract.manager_party_id.in_(manager_party_ids))
        if scope_filters:
            stmt = stmt.where(or_(*scope_filters))

        result = await db.execute(stmt)
        return list(result.all())


# 实例化CRUD对象
rent_contract = CRUDRentContract(RentContract)
rent_term = CRUDRentTerm(RentTerm)
rent_ledger = CRUDRentLedger(RentLedger)
