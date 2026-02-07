from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from ...core.exception_handler import (
    DuplicateResourceError,
    ResourceNotFoundError,
    conflict,
    operation_not_allowed,
    validation_error,
)
from ...crud.history import history_crud
from ...models.asset import Asset, AssetHistory
from ...models.auth import User
from ...models.ownership import Ownership
from ...models.property_certificate import property_cert_assets
from ...models.rent_contract import RentLedger, rent_contract_assets
from ...schemas.asset import AssetCreate, AssetUpdate
from ...services.asset.asset_calculator import AssetCalculator
from ...services.enum_validation_service import get_enum_validation_service_async

_DEFAULT_ASSET_CRUD: object = object()
asset_crud: Any = _DEFAULT_ASSET_CRUD


def _utcnow_naive() -> datetime:
    """Return UTC now as naive datetime to match current DB column types."""
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize_bool_filter(
    value: bool | str | None, *, field_name: str
) -> bool | None:
    if isinstance(value, bool):
        return value

    if value is None:
        return None

    normalized = value.strip().lower()
    if normalized == "":
        return None

    if normalized in {"true", "1", "yes", "y", "是"}:
        return True
    if normalized in {"false", "0", "no", "n", "否"}:
        return False

    raise validation_error(
        f"{field_name} 参数无效，支持值: true/false/是/否",
        field_errors={field_name: "invalid_boolean_filter"},
    )


def _get_asset_crud() -> Any:
    if asset_crud is not _DEFAULT_ASSET_CRUD:
        return asset_crud

    from ...crud import asset as asset_module

    return asset_module.asset_crud


class AssetService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def build_filters(
        *,
        ownership_status: str | None = None,
        property_nature: str | None = None,
        usage_status: str | None = None,
        ownership_id: str | None = None,
        management_entity: str | None = None,
        business_category: str | None = None,
        data_status: str | None = None,
        min_area: float | None = None,
        max_area: float | None = None,
        min_occupancy_rate: float | None = None,
        max_occupancy_rate: float | None = None,
        is_litigated: bool | str | None = None,
    ) -> dict[str, Any] | None:
        filters: dict[str, Any] = {}
        if ownership_status is not None and ownership_status != "":
            filters["ownership_status"] = ownership_status
        if property_nature is not None and property_nature != "":
            filters["property_nature"] = property_nature
        if usage_status is not None and usage_status != "":
            filters["usage_status"] = usage_status
        if ownership_id is not None and ownership_id != "":
            filters["ownership_id"] = ownership_id
        if management_entity is not None and management_entity != "":
            filters["management_entity"] = management_entity
        if business_category is not None and business_category != "":
            filters["business_category"] = business_category
        if data_status is not None and data_status != "":
            filters["data_status"] = data_status
        if min_area is not None:
            filters["min_area"] = min_area
        if max_area is not None:
            filters["max_area"] = max_area
        if min_occupancy_rate is not None:
            filters["min_occupancy_rate"] = min_occupancy_rate
        if max_occupancy_rate is not None:
            filters["max_occupancy_rate"] = max_occupancy_rate
        normalized_is_litigated = _normalize_bool_filter(
            is_litigated,
            field_name="is_litigated",
        )
        if normalized_is_litigated is not None:
            filters["is_litigated"] = normalized_is_litigated
        return filters or None

    @asynccontextmanager
    async def _transaction(self) -> Any:
        if self.db.in_transaction():
            try:
                yield
                await self.db.commit()
            except Exception:
                await self.db.rollback()
                raise
        else:
            async with self.db.begin():
                yield

    async def _resolve_ownership(
        self,
        data: dict[str, Any],
        *,
        current_asset: Asset | None = None,
    ) -> dict[str, Any]:
        ownership_id = data.get("ownership_id") or (
            current_asset.ownership_id if current_asset else None
        )

        if not ownership_id and current_asset is None:
            raise validation_error(
                "权属方不能为空", field_errors={"ownership_id": "权属方不能为空"}
            )

        if ownership_id:
            result = await self.db.execute(
                select(Ownership).where(Ownership.id == ownership_id)
            )
            ownership = result.scalars().first()
            if not ownership:
                raise validation_error(
                    "权属方不存在", field_errors={"ownership_id": "权属方不存在"}
                )

        data["ownership_id"] = ownership_id
        return data

    async def _ensure_asset_not_linked(self, asset_id: str) -> None:
        has_contract = (
            await self.db.execute(
                select(rent_contract_assets.c.asset_id)
                .where(rent_contract_assets.c.asset_id == asset_id)
                .limit(1)
            )
        ).first() is not None
        if has_contract:
            raise operation_not_allowed(
                "资产已关联合同，禁止删除",
                reason="asset_has_contracts",
            )

        has_certificate = (
            await self.db.execute(
                select(property_cert_assets.c.asset_id)
                .where(property_cert_assets.c.asset_id == asset_id)
                .limit(1)
            )
        ).first() is not None
        if has_certificate:
            raise operation_not_allowed(
                "资产已关联产权证，禁止删除",
                reason="asset_has_certificates",
            )

        has_ledger = (
            await self.db.execute(
                select(RentLedger.id).where(RentLedger.asset_id == asset_id).limit(1)
            )
        ).first() is not None
        if has_ledger:
            raise operation_not_allowed(
                "资产已有租金台账记录，禁止删除",
                reason="asset_has_ledger",
            )

    async def get_assets(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        filters: dict[str, Any] | None = None,
        sort_field: str = "created_at",
        sort_order: str = "desc",
        include_relations: bool = False,
    ) -> tuple[list[Asset], int]:
        asset_crud = _get_asset_crud()
        result = cast(
            tuple[list[Asset], int],
            await asset_crud.get_multi_with_search_async(
                self.db,
                skip=skip,
                limit=limit,
                search=search,
                filters=filters,
                sort_field=sort_field,
                sort_order=sort_order,
                include_relations=include_relations,
            ),
        )
        return result

    async def get_asset(self, asset_id: str, *, use_cache: bool = True) -> Asset:
        asset_crud = _get_asset_crud()
        asset = cast(
            Asset | None,
            await asset_crud.get_async(db=self.db, id=asset_id),
        )
        if not asset or asset.data_status == "已删除":
            raise ResourceNotFoundError("Asset", asset_id)
        return asset

    async def get_distinct_field_values(self, field_name: str) -> list[str]:
        asset_crud = _get_asset_crud()
        values = await asset_crud.get_distinct_field_values(self.db, field_name)
        return [str(value) for value in values]

    async def create_asset(
        self,
        asset_in: AssetCreate,
        current_user: User | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> Asset:
        """
        创建新资产
        包含逻辑: 枚举验证, 名称查重, 自动计算, 面积一致性验证, 历史记录
        """
        operator = (
            getattr(current_user, "username", None)
            or getattr(current_user, "id", None)
            or "system"
        )

        async with self._transaction():
            asset_crud = _get_asset_crud()
            # 1. 枚举值验证
            validation_service = get_enum_validation_service_async(self.db)
            incoming_payload = asset_in.model_dump()
            is_valid, errors = await validation_service.validate_asset_data(
                incoming_payload
            )
            if not is_valid:
                raise validation_error(
                    f"枚举值验证失败: {'; '.join(errors)}", field_errors=errors
                )

            # 2. 名称查重
            existing_asset = await asset_crud.get_by_name_async(
                db=self.db, property_name=asset_in.property_name
            )
            if existing_asset:
                raise DuplicateResourceError(
                    "Asset", "property_name", asset_in.property_name
                )

            # 3. 自动计算与一致性验证
            asset_data = asset_in.model_dump()
            asset_data = await self._resolve_ownership(asset_data)
            calculated_fields = AssetCalculator.auto_calculate_fields(asset_data)
            final_data = {**asset_data, **calculated_fields}

            area_errors = AssetCalculator.validate_area_consistency(final_data)
            if area_errors:
                raise validation_error(
                    f"数据验证失败: {'; '.join(area_errors)}",
                    field_errors=area_errors,
                )

            calculated_asset_in = AssetCreate(**final_data)
            asset = cast(
                Asset,
                await asset_crud.create_with_history_async(
                    db=self.db,
                    obj_in=calculated_asset_in,
                    commit=False,
                    operator=str(operator) if operator is not None else None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    session_id=session_id,
                ),
            )
            return asset

    async def update_asset(
        self,
        asset_id: str,
        asset_in: AssetUpdate,
        current_user: User | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
    ) -> Asset:
        """
        更新资产
        包含逻辑: 存在性检查枚举验证, 名称查重, 自动计算, 面积一致性验证, 历史记录
        """
        operator = (
            getattr(current_user, "username", None)
            or getattr(current_user, "id", None)
            or "system"
        )

        try:
            async with self._transaction():
                asset_crud = _get_asset_crud()
                # 1. 存在性检查
                asset = await self.get_asset(asset_id, use_cache=False)

                # 2. 枚举值验证 (如果提供了更新数据)
                validation_service = get_enum_validation_service_async(self.db)
                # only validate fields that are present
                update_data_raw = asset_in.model_dump(exclude_unset=True)
                expected_version = update_data_raw.pop("version", None)
                if (
                    expected_version is not None
                    and hasattr(asset, "version")
                    and asset.version != expected_version
                ):
                    raise conflict(
                        "资产版本冲突，请刷新后重试",
                        resource_type="Asset",
                    )

                is_valid, enum_errors = await validation_service.validate_asset_data(
                    update_data_raw
                )
                if not is_valid:
                    raise validation_error(
                        f"枚举值验证失败: {'; '.join(enum_errors)}",
                        field_errors=enum_errors,
                    )

                update_data_raw = await self._resolve_ownership(
                    update_data_raw, current_asset=asset
                )

                # 3. 名称查重 (如果修改了名称)
                new_name = update_data_raw.get("property_name")
                if new_name and new_name != asset.property_name:
                    existing_asset = await asset_crud.get_by_name_async(
                        db=self.db, property_name=new_name
                    )
                    if existing_asset and existing_asset.id != asset_id:
                        raise DuplicateResourceError("Asset", "property_name", new_name)

                # 4. 自动计算与一致性验证
                # 需要合并当前数据和更新数据
                current_data = {}
                # 提取关键计算字段
                for field in [
                    "rentable_area",
                    "rented_area",
                    "annual_income",
                    "annual_expense",
                ]:
                    if hasattr(asset, field):
                        current_data[field] = getattr(asset, field)

                merged_data = {**current_data, **update_data_raw}
                calculated_data = AssetCalculator.auto_calculate_fields(merged_data)

                area_errors = AssetCalculator.validate_area_consistency(calculated_data)
                if area_errors:
                    raise validation_error(
                        f"数据验证失败: {'; '.join(area_errors)}",
                        field_errors=area_errors,
                    )

                # 合并计算字段到更新数据
                final_update = {
                    **update_data_raw,
                    **{
                        k: v
                        for k, v in calculated_data.items()
                        if k not in update_data_raw
                    },
                }
                calculated_asset_in = AssetUpdate(**final_update)

                updated = cast(
                    Asset,
                    await asset_crud.update_with_history_async(
                        db=self.db,
                        db_obj=asset,
                        obj_in=calculated_asset_in,
                        commit=False,
                        operator=str(operator) if operator is not None else None,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        session_id=session_id,
                    ),
                )
                return updated
        except StaleDataError as exc:
            raise conflict(
                "资产已被其他人更新，请刷新后重试",
                resource_type="Asset",
            ) from exc

    async def delete_asset(
        self, asset_id: str, current_user: User | None = None
    ) -> None:
        # 1. 存在性检查
        try:
            async with self._transaction():
                asset = await self.get_asset(asset_id, use_cache=False)
                await self._ensure_asset_not_linked(asset_id)
                operator = (
                    getattr(current_user, "username", None)
                    or getattr(current_user, "id", None)
                    or "system"
                )
                history = AssetHistory()
                history.asset_id = asset.id
                history.operation_type = "DELETE"
                history.description = f"删除资产: {asset.property_name}"
                history.operator = str(operator) if operator is not None else None
                self.db.add(history)
                asset.data_status = "已删除"
                asset.updated_by = str(operator) if operator is not None else None
                asset.updated_at = _utcnow_naive()
                self.db.add(asset)
                await self.db.flush()
        except StaleDataError as exc:
            raise conflict(
                "资产已被其他人更新，请刷新后重试",
                resource_type="Asset",
            ) from exc

    async def restore_asset(
        self, asset_id: str, current_user: User | None = None
    ) -> Asset:
        try:
            async with self._transaction():
                asset_crud = _get_asset_crud()
                asset = cast(
                    Asset | None,
                    await asset_crud.get_async(db=self.db, id=asset_id),
                )
                if not asset:
                    raise ResourceNotFoundError("Asset", asset_id)
                if asset.data_status != "已删除":
                    raise operation_not_allowed(
                        "资产未处于已删除状态，无法恢复",
                        reason="asset_not_deleted",
                    )
                operator = (
                    getattr(current_user, "username", None)
                    or getattr(current_user, "id", None)
                    or "system"
                )
                history = AssetHistory()
                history.asset_id = asset.id
                history.operation_type = "RESTORE"
                history.description = f"恢复资产: {asset.property_name}"
                history.operator = str(operator) if operator is not None else None
                self.db.add(history)
                asset.data_status = "正常"
                asset.updated_by = str(operator) if operator is not None else None
                asset.updated_at = _utcnow_naive()
                self.db.add(asset)
                await self.db.flush()
                return asset
        except StaleDataError as exc:
            raise conflict(
                "资产已被其他人更新，请刷新后重试",
                resource_type="Asset",
            ) from exc

    async def hard_delete_asset(
        self, asset_id: str, current_user: User | None = None
    ) -> None:
        try:
            async with self._transaction():
                asset_crud = _get_asset_crud()
                asset = cast(
                    Asset | None,
                    await asset_crud.get_async(db=self.db, id=asset_id),
                )
                if not asset:
                    raise ResourceNotFoundError("Asset", asset_id)
                if asset.data_status != "已删除":
                    raise operation_not_allowed(
                        "资产未处于已删除状态，无法彻底删除",
                        reason="asset_not_deleted",
                    )
                await self._ensure_asset_not_linked(asset_id)
                await history_crud.remove_by_asset_id_async(
                    db=self.db,
                    asset_id=asset.id,
                    commit=False,
                )
                await self.db.delete(asset)
                await self.db.flush()
        except StaleDataError as exc:
            raise conflict(
                "资产已被其他人更新，请刷新后重试",
                resource_type="Asset",
            ) from exc


AsyncAssetService = AssetService
