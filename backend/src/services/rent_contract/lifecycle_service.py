from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import (
    BusinessValidationError,
    ResourceConflictError,
)
from ...models.asset import Asset
from ...models.rent_contract import (
    RentContract,
    RentTerm,
)
from ...schemas.rent_contract import RentContractCreate, RentContractUpdate
from ...utils.model_utils import model_to_dict
from .helpers import RentContractHelperMixin


class RentContractLifecycleService(RentContractHelperMixin):
    """合同生命周期相关服务"""

    async def create_contract_async(
        self, db: AsyncSession, *, obj_in: RentContractCreate
    ) -> RentContract:
        if not obj_in.contract_number or not obj_in.contract_number.strip():
            raise BusinessValidationError(
                "合同编号不能为空，请手工录入",
                field_errors={"contract_number": ["不能为空"]},
            )
        obj_in.contract_number = obj_in.contract_number.strip()

        if obj_in.asset_ids:
            conflicts = await self._check_asset_rent_conflicts_async(
                db,
                asset_ids=obj_in.asset_ids,
                start_date=obj_in.start_date,
                end_date=obj_in.end_date,
                exclude_contract_id=None,
            )
            if conflicts:
                conflict_details = [
                    f"资产 {c['asset_name']} 已被合同 {c['contract_number']} 覆盖 "
                    f"({c['contract_start_date']} 至 {c['contract_end_date']})"
                    for c in conflicts
                ]
                raise ResourceConflictError(
                    message=(
                        "资产租金冲突检测:\n"
                        + "\n".join(conflict_details)
                        + "\n\n是否仍要创建? 如果确认创建,请联系管理员或使用强制覆盖功能。"
                    ),
                    resource_type="asset",
                    details={"conflicts": conflicts},
                )

        asset_ids = obj_in.asset_ids or []
        contract_data = obj_in.model_dump(exclude={"rent_terms", "asset_ids"})
        db_contract = RentContract(**contract_data)

        if asset_ids:
            assets = list(
                (await db.execute(select(Asset).where(Asset.id.in_(asset_ids))))
                .scalars()
                .all()
            )
            sa_assets = [
                asset for asset in assets if hasattr(asset, "_sa_instance_state")
            ]
            if sa_assets:
                setattr(db_contract, "assets", sa_assets)

        db.add(db_contract)
        await db.flush()

        for term_data in obj_in.rent_terms:
            term_data_dict = term_data.model_dump()
            if term_data_dict.get("total_monthly_amount") is None:
                monthly_rent = term_data_dict.get("monthly_rent", Decimal("0"))
                management_fee = term_data_dict.get("management_fee", Decimal("0"))
                other_fees = term_data_dict.get("other_fees", Decimal("0"))
                term_data_dict["total_monthly_amount"] = (
                    monthly_rent + management_fee + other_fees
                )

            term_data_dict["contract_id"] = db_contract.id
            db_term = RentTerm(**term_data_dict)
            db.add(db_term)

        await db.commit()
        await db.refresh(db_contract)

        await self._create_history_async(
            db,
            contract_id=db_contract.id,
            change_type="创建",
            change_description="创建新合同",
            new_data=model_to_dict(db_contract),
        )

        return db_contract

    async def update_contract_async(
        self, db: AsyncSession, *, db_obj: RentContract, obj_in: RentContractUpdate
    ) -> RentContract:
        old_data = model_to_dict(db_obj)

        update_data = obj_in.model_dump(
            exclude_unset=True, exclude={"rent_terms", "asset_ids"}
        )
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        if obj_in.asset_ids is not None:
            assets = list(
                (await db.execute(select(Asset).where(Asset.id.in_(obj_in.asset_ids))))
                .scalars()
                .all()
            )
            sa_assets = [
                asset for asset in assets if hasattr(asset, "_sa_instance_state")
            ]
            if sa_assets:
                setattr(db_obj, "assets", sa_assets)

        if obj_in.rent_terms is not None:
            await db.execute(delete(RentTerm).where(RentTerm.contract_id == db_obj.id))

            for term_data in obj_in.rent_terms:
                term_data_dict = term_data.model_dump()
                term_data_dict["contract_id"] = db_obj.id
                db_term = RentTerm(**term_data_dict)
                db.add(db_term)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        await self._create_history_async(
            db,
            contract_id=db_obj.id,
            change_type="更新",
            change_description="更新合同信息",
            old_data=old_data,
            new_data=model_to_dict(db_obj),
        )

        return db_obj

