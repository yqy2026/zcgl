from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception_handler import (
    BusinessValidationError,
    ResourceConflictError,
)
from ...crud.asset import asset_crud
from ...crud.rent_contract import rent_term
from ...models.rent_contract import (
    RentContract,
    RentTerm,
)
from ...schemas.rent_contract import RentContractCreate, RentContractUpdate
from ...utils.model_utils import model_to_dict
from .helpers import RentContractHelperMixin


def _normalize_optional_str(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized == "":
        return None
    return normalized


class RentContractLifecycleService(RentContractHelperMixin):
    """合同生命周期相关服务"""

    async def _normalize_owner_ownership_mapping_async(
        self,
        db: AsyncSession,
        *,
        owner_party_id: str | None,
        ownership_id: str | None,
    ) -> tuple[str | None, str | None]:
        normalized_owner_party_id = _normalize_optional_str(owner_party_id)
        normalized_ownership_id = _normalize_optional_str(ownership_id)
        resolved_ownership_id_from_owner: str | None = None

        if normalized_ownership_id is None and normalized_owner_party_id is not None:
            resolved_ownership_id_from_owner = _normalize_optional_str(
                await self.resolve_ownership_id_by_owner_party_id_async(
                    db=db,
                    owner_party_id=normalized_owner_party_id,
                )
            )
            if resolved_ownership_id_from_owner is None:
                raise BusinessValidationError(
                    "当前产权主体未建立可用权属映射，请联系管理员补齐映射或显式传入 ownership_id",
                    field_errors={
                        "owner_party_id": ["未匹配到唯一权属方"],
                        "ownership_id": ["缺少有效权属映射"],
                    },
                )
            normalized_ownership_id = resolved_ownership_id_from_owner

        if (
            normalized_owner_party_id is not None
            and normalized_ownership_id is not None
        ):
            resolved_owner_party_id = _normalize_optional_str(
                await self.resolve_owner_party_scope_by_ownership_id_async(
                    db=db,
                    ownership_id=normalized_ownership_id,
                )
            )
            resolved_ownership_id = resolved_ownership_id_from_owner or _normalize_optional_str(
                await self.resolve_ownership_id_by_owner_party_id_async(
                    db=db,
                    owner_party_id=normalized_owner_party_id,
                )
            )

            if (
                resolved_owner_party_id is not None
                and resolved_owner_party_id != normalized_owner_party_id
            ):
                raise BusinessValidationError(
                    "owner_party_id 与 ownership_id 对应关系不一致，请修正后重试",
                    field_errors={
                        "owner_party_id": ["与 ownership_id 映射不一致"],
                        "ownership_id": ["与 owner_party_id 映射不一致"],
                    },
                )
            if (
                resolved_ownership_id is not None
                and resolved_ownership_id != normalized_ownership_id
            ):
                raise BusinessValidationError(
                    "owner_party_id 与 ownership_id 对应关系不一致，请修正后重试",
                    field_errors={
                        "owner_party_id": ["与 ownership_id 映射不一致"],
                        "ownership_id": ["与 owner_party_id 映射不一致"],
                    },
                )
            if resolved_owner_party_id is None and resolved_ownership_id is None:
                raise BusinessValidationError(
                    "无法验证 owner_party_id 与 ownership_id 的映射关系，请联系管理员补齐映射后重试",
                    field_errors={
                        "owner_party_id": ["映射关系不可验证"],
                        "ownership_id": ["映射关系不可验证"],
                    },
                )

        return normalized_owner_party_id, normalized_ownership_id

    async def create_contract_async(
        self, db: AsyncSession, *, obj_in: RentContractCreate
    ) -> RentContract:
        if not obj_in.contract_number or not obj_in.contract_number.strip():
            raise BusinessValidationError(
                "合同编号不能为空，请手工录入",
                field_errors={"contract_number": ["不能为空"]},
            )
        obj_in.contract_number = obj_in.contract_number.strip()
        (
            obj_in.owner_party_id,
            obj_in.ownership_id,
        ) = await self._normalize_owner_ownership_mapping_async(
            db=db,
            owner_party_id=obj_in.owner_party_id,
            ownership_id=obj_in.ownership_id,
        )

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
            assets = await asset_crud.get_multi_by_ids_async(
                db,
                asset_ids,
                include_relations=False,
                include_deleted=False,
                decrypt=False,
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
        incoming_fields = set(obj_in.model_fields_set)
        owner_party_updated = "owner_party_id" in incoming_fields
        ownership_updated = "ownership_id" in incoming_fields

        update_data = obj_in.model_dump(
            exclude_unset=True, exclude={"rent_terms", "asset_ids"}
        )
        if owner_party_updated or ownership_updated:
            target_owner_party_id = (
                obj_in.owner_party_id if owner_party_updated else db_obj.owner_party_id
            )
            target_ownership_id = (
                obj_in.ownership_id
                if ownership_updated
                else (None if owner_party_updated else db_obj.ownership_id)
            )
            (
                normalized_owner_party_id,
                normalized_ownership_id,
            ) = await self._normalize_owner_ownership_mapping_async(
                db=db,
                owner_party_id=target_owner_party_id,
                ownership_id=target_ownership_id,
            )
            resolved_owner_party_for_update = normalized_owner_party_id
            if (
                resolved_owner_party_for_update is None
                and ownership_updated
                and normalized_ownership_id is not None
            ):
                # Legacy compatibility: ownership_id-only payloads fallback to owner scope.
                resolved_owner_party_for_update = normalized_ownership_id
            if owner_party_updated or ownership_updated:
                update_data["owner_party_id"] = resolved_owner_party_for_update

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        if obj_in.asset_ids is not None:
            assets = await asset_crud.get_multi_by_ids_async(
                db,
                obj_in.asset_ids,
                include_relations=False,
                include_deleted=False,
                decrypt=False,
            )
            sa_assets = [
                asset for asset in assets if hasattr(asset, "_sa_instance_state")
            ]
            if sa_assets:
                setattr(db_obj, "assets", sa_assets)

        if obj_in.rent_terms is not None:
            await rent_term.delete_by_contract_async(db, db_obj.id)

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
