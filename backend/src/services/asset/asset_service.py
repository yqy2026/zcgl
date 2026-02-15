import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from ...constants.business_constants import DataStatusValues
from ...core.exception_handler import (
    DuplicateResourceError,
    ResourceNotFoundError,
    conflict,
    operation_not_allowed,
    validation_error,
)
from ...crud.history import history_crud
from ...crud.ownership import ownership
from ...crud.query_builder import TenantFilter
from ...models.asset import Asset
from ...models.asset_history import AssetHistory
from ...models.auth import User
from ...schemas.asset import AssetCreate, AssetUpdate
from ...services.asset.asset_calculator import AssetCalculator
from ...services.enum_validation_service import get_enum_validation_service_async

logger = logging.getLogger(__name__)


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


def _get_default_asset_crud() -> Any:
    from ...crud import asset as asset_module

    return asset_module.asset_crud


class AssetService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        asset_crud_override: Any | None = None,
    ) -> None:
        self.db = db
        self.asset_crud = (
            asset_crud_override
            if asset_crud_override is not None
            else _get_default_asset_crud()
        )

    async def _resolve_tenant_filter(
        self,
        *,
        current_user_id: str | None = None,
        tenant_filter: TenantFilter | None = None,
    ) -> TenantFilter | None:
        if tenant_filter is not None:
            return tenant_filter
        if current_user_id is None or current_user_id.strip() == "":
            return None

        try:
            from ..organization_permission_service import OrganizationPermissionService

            org_service = OrganizationPermissionService(self.db)
            org_ids = await org_service.get_user_accessible_organizations(
                current_user_id
            )
            return TenantFilter(organization_ids=[str(org_id) for org_id in org_ids])
        except Exception:
            logger.exception(
                "Failed to resolve tenant filter for user %s, fallback to fail-closed",
                current_user_id,
            )
            return TenantFilter(organization_ids=[])

    @staticmethod
    def _is_fail_closed_tenant_filter(tenant_filter: TenantFilter | None) -> bool:
        if tenant_filter is None:
            return False
        return (
            len(
                [
                    org_id
                    for org_id in tenant_filter.organization_ids
                    if str(org_id).strip() != ""
                ]
            )
            == 0
        )

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
            ownership_obj = await ownership.get(self.db, id=ownership_id)
            if not ownership_obj:
                raise validation_error(
                    "权属方不存在", field_errors={"ownership_id": "权属方不存在"}
                )

        data["ownership_id"] = ownership_id
        return data

    async def _ensure_asset_not_linked(self, asset_id: str) -> None:
        asset_crud = self.asset_crud

        has_contract = await asset_crud.has_rent_contracts_async(self.db, asset_id)
        if has_contract:
            raise operation_not_allowed(
                "资产已关联合同，禁止删除",
                reason="asset_has_contracts",
            )

        has_certificate = await asset_crud.has_property_certs_async(self.db, asset_id)
        if has_certificate:
            raise operation_not_allowed(
                "资产已关联产权证，禁止删除",
                reason="asset_has_certificates",
            )

        has_ledger = await asset_crud.has_rent_ledger_async(self.db, asset_id)
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
        tenant_filter: TenantFilter | None = None,
        current_user_id: str | None = None,
    ) -> tuple[list[Asset], int]:
        asset_crud = self.asset_crud
        resolved_tenant_filter = await self._resolve_tenant_filter(
            current_user_id=current_user_id,
            tenant_filter=tenant_filter,
        )
        if self._is_fail_closed_tenant_filter(resolved_tenant_filter):
            return ([], 0)
        query_kwargs: dict[str, Any] = {
            "skip": skip,
            "limit": limit,
            "search": search,
            "filters": filters,
            "sort_field": sort_field,
            "sort_order": sort_order,
            "include_relations": include_relations,
        }
        if resolved_tenant_filter is not None:
            query_kwargs["tenant_filter"] = resolved_tenant_filter
        result = cast(
            tuple[list[Asset], int],
            await asset_crud.get_multi_with_search_async(
                self.db,
                **query_kwargs,
            ),
        )
        return result

    async def get_assets_by_ids(
        self,
        ids: list[str],
        *,
        include_relations: bool = False,
    ) -> list[Asset]:
        """根据 ID 列表批量获取资产。"""
        asset_crud = self.asset_crud
        assets = cast(
            list[Asset],
            await asset_crud.get_multi_by_ids_async(
                db=self.db,
                ids=ids,
                include_relations=include_relations,
            ),
        )
        return assets

    async def get_asset(
        self,
        asset_id: str,
        *,
        use_cache: bool = True,
        tenant_filter: TenantFilter | None = None,
        current_user_id: str | None = None,
    ) -> Asset:
        asset_crud = self.asset_crud
        resolved_tenant_filter = await self._resolve_tenant_filter(
            current_user_id=current_user_id,
            tenant_filter=tenant_filter,
        )
        if self._is_fail_closed_tenant_filter(resolved_tenant_filter):
            raise ResourceNotFoundError("Asset", asset_id)

        query_kwargs: dict[str, Any] = {
            "db": self.db,
            "id": asset_id,
            "use_cache": use_cache,
        }
        if resolved_tenant_filter is not None:
            query_kwargs["tenant_filter"] = resolved_tenant_filter
        asset = cast(
            Asset | None,
            await asset_crud.get_async(**query_kwargs),
        )
        if not asset or asset.data_status == DataStatusValues.ASSET_DELETED:
            raise ResourceNotFoundError("Asset", asset_id)
        return asset

    async def get_asset_history_records(
        self,
        asset_id: str,
        *,
        tenant_filter: TenantFilter | None = None,
        current_user_id: str | None = None,
    ) -> list[AssetHistory]:
        await self.get_asset(
            asset_id,
            tenant_filter=tenant_filter,
            current_user_id=current_user_id,
        )
        history_records = await history_crud.get_by_asset_id_async(
            self.db,
            asset_id=asset_id,
        )
        return history_records

    async def get_distinct_field_values(
        self,
        field_name: str,
        *,
        tenant_filter: TenantFilter | None = None,
        current_user_id: str | None = None,
    ) -> list[str]:
        asset_crud = self.asset_crud
        resolved_tenant_filter = await self._resolve_tenant_filter(
            current_user_id=current_user_id,
            tenant_filter=tenant_filter,
        )
        if self._is_fail_closed_tenant_filter(resolved_tenant_filter):
            return []
        query_kwargs: dict[str, Any] = {}
        if resolved_tenant_filter is not None:
            query_kwargs["tenant_filter"] = resolved_tenant_filter
        values = await asset_crud.get_distinct_field_values(
            self.db, field_name, **query_kwargs
        )
        return [str(value) for value in values]

    async def get_ownership_entity_names(self) -> list[str]:
        """获取所有正常状态的权属方名称列表"""
        return await ownership.get_names_by_status_async(
            self.db, data_status=DataStatusValues.ASSET_NORMAL
        )

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
        default_org_id = getattr(current_user, "default_organization_id", None)
        organization_id = (
            str(default_org_id)
            if default_org_id is not None and str(default_org_id).strip() != ""
            else None
        )

        async with self._transaction():
            asset_crud = self.asset_crud
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
                    organization_id=organization_id,
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
                asset_crud = self.asset_crud
                # 1. 存在性检查
                user_id = getattr(current_user, "id", None)
                asset = await self.get_asset(
                    asset_id,
                    use_cache=False,
                    current_user_id=str(user_id) if user_id is not None else None,
                )

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
                user_id = getattr(current_user, "id", None)
                asset = await self.get_asset(
                    asset_id,
                    use_cache=False,
                    current_user_id=str(user_id) if user_id is not None else None,
                )
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
                asset.data_status = DataStatusValues.ASSET_DELETED
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
                asset_crud = self.asset_crud
                asset = cast(
                    Asset | None,
                    await asset_crud.get_async(
                        db=self.db,
                        id=asset_id,
                        include_deleted=True,
                    ),
                )
                if not asset:
                    raise ResourceNotFoundError("Asset", asset_id)
                if asset.data_status != DataStatusValues.ASSET_DELETED:
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
                asset.data_status = DataStatusValues.ASSET_NORMAL
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
                asset_crud = self.asset_crud
                asset = cast(
                    Asset | None,
                    await asset_crud.get_async(
                        db=self.db,
                        id=asset_id,
                        include_deleted=True,
                    ),
                )
                if not asset:
                    raise ResourceNotFoundError("Asset", asset_id)
                if asset.data_status != DataStatusValues.ASSET_DELETED:
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
