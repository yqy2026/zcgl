import logging
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
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
from ...crud.contract import contract_crud
from ...crud.history import history_crud
from ...crud.ownership import ownership
from ...crud.party import party_crud
from ...crud.query_builder import PartyFilter
from ...models.asset import Asset
from ...models.asset_history import AssetHistory
from ...models.auth import User
from ...models.contract_group import ContractLifecycleStatus, GroupRelationType
from ...schemas.asset import (
    AssetCreate,
    AssetLeaseSummaryResponse,
    AssetUpdate,
    ContractPartyItem,
    ContractTypeSummary,
)
from ...services.asset.asset_calculator import AssetCalculator
from ...services.enum_validation_service import get_enum_validation_service_async
from ...services.party_scope import resolve_user_party_filter

logger = logging.getLogger(__name__)
ACTIVE_CONTRACT_STATUSES = {ContractLifecycleStatus.ACTIVE}


def _utcnow_naive() -> datetime:
    """Return UTC now as naive datetime to match current DB column types."""
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized == "":
        return None
    return normalized


def _as_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _default_summary_period() -> tuple[date, date]:
    today = date.today()
    start = today.replace(day=1)
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return start, end


def _month_bounds(anchor: date) -> tuple[date, date]:
    start = anchor.replace(day=1)
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return start, end


def normalize_summary_period(
    period_start: date | None,
    period_end: date | None,
) -> tuple[date, date]:
    if period_start is None and period_end is None:
        return _default_summary_period()
    if period_start is None:
        normalized_start, _ = _month_bounds(period_end)
        return normalized_start, period_end
    if period_end is None:
        _, normalized_end = _month_bounds(period_start)
        return period_start, normalized_end
    return period_start, period_end


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


_ADDRESS_SUB_FIELDS = ("province_code", "city_code", "district_code", "address_detail")


def _compose_address(data: dict[str, Any], current_asset: "Asset | None" = None) -> str | None:
    """根据半结构化地址子字段拼接只读展示用 address.

    优先使用 data 中的字段，缺少时回退到 current_asset 的现有字段。
    若 address_detail 缺到，返回 None（不覆盖现有 address）。
    """
    def _get(key: str) -> str | None:
        if key in data and data[key] is not None:
            return str(data[key]).strip() or None
        if current_asset is not None:
            val = getattr(current_asset, key, None)
            return str(val).strip() if val else None
        return None

    detail = _get("address_detail")
    if not detail:
        return None  # 没有 address_detail 不拼接

    parts = [
        _get("province_code"),
        _get("city_code"),
        _get("district_code"),
        detail,
    ]
    return " ".join(p for p in parts if p)


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

    async def _resolve_party_filter(
        self,
        *,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> PartyFilter | None:
        return await resolve_user_party_filter(
            self.db,
            current_user_id=current_user_id,
            party_filter=party_filter,
            logger=logger,
            allow_legacy_default_organization_fallback=False,
        )

    @staticmethod
    def _is_fail_closed_party_filter(party_filter: PartyFilter | None) -> bool:
        if party_filter is None:
            return False
        return (
            len(
                [
                    org_id
                    for org_id in party_filter.party_ids
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
        owner_party_id = _normalize_optional_str(data.get("owner_party_id"))
        legacy_ownership_id = _normalize_optional_str(data.get("ownership_id"))
        if owner_party_id is None and legacy_ownership_id is not None:
            owner_party_id = await self.resolve_owner_party_scope_by_ownership_id_async(
                ownership_id=legacy_ownership_id,
            )
        if owner_party_id is None and current_asset is not None:
            owner_party_id = _normalize_optional_str(
                getattr(current_asset, "owner_party_id", None)
            )

        if not owner_party_id and current_asset is None:
            raise validation_error(
                "权属主体不能为空", field_errors={"owner_party_id": "权属主体不能为空"}
            )

        if owner_party_id:
            party_obj = await party_crud.get_party(self.db, party_id=owner_party_id)
            if party_obj is None and legacy_ownership_id is None:
                # 兼容误将 legacy ownership_id 透传到 owner_party_id 的调用方
                fallback_party_id = await self.resolve_owner_party_scope_by_ownership_id_async(
                    ownership_id=owner_party_id,
                )
                if (
                    fallback_party_id is not None
                    and fallback_party_id != owner_party_id
                ):
                    owner_party_id = fallback_party_id
                    party_obj = await party_crud.get_party(
                        self.db,
                        party_id=owner_party_id,
                    )
            if not party_obj:
                raise validation_error(
                    "权属主体不存在", field_errors={"owner_party_id": "权属主体不存在"}
                )

        manager_party_id = _normalize_optional_str(data.get("manager_party_id"))
        legacy_management_entity = _normalize_optional_str(data.get("management_entity"))
        legacy_organization_id = _normalize_optional_str(data.get("organization_id"))

        if manager_party_id is None and legacy_management_entity is not None:
            manager_party_id = legacy_management_entity

        if manager_party_id is None and legacy_organization_id is not None:
            resolved_org_party_id = await party_crud.resolve_organization_party_id(
                self.db,
                organization_id=legacy_organization_id,
            )
            manager_party_id = (
                resolved_org_party_id
                if resolved_org_party_id is not None
                else legacy_organization_id
            )

        if manager_party_id is None and current_asset is not None:
            manager_party_id = _normalize_optional_str(
                getattr(current_asset, "manager_party_id", None)
            )

        # Step4 兼容：历史调用方通常只提供 ownership_id，默认回填管理主体为产权主体。
        if manager_party_id is None and owner_party_id is not None:
            manager_party_id = owner_party_id

        if manager_party_id:
            manager_party_obj = await party_crud.get_party(
                self.db,
                party_id=manager_party_id,
            )
            if manager_party_obj is None:
                fallback_manager_party_id = (
                    await self.resolve_owner_party_scope_by_ownership_id_async(
                        ownership_id=manager_party_id,
                    )
                )
                if (
                    fallback_manager_party_id is not None
                    and fallback_manager_party_id != manager_party_id
                ):
                    manager_party_id = fallback_manager_party_id
                    manager_party_obj = await party_crud.get_party(
                        self.db,
                        party_id=manager_party_id,
                    )
            if manager_party_obj is None:
                raise validation_error(
                    "经营管理主体不存在",
                    field_errors={"manager_party_id": "经营管理主体不存在"},
                )

        data["owner_party_id"] = owner_party_id
        data["manager_party_id"] = manager_party_id
        data.pop("ownership_id", None)  # DEPRECATED alias
        data.pop("management_entity", None)  # DEPRECATED alias
        return data

    async def _ensure_asset_not_linked(self, asset_id: str) -> None:
        asset_crud = self.asset_crud

        has_contract = await asset_crud.has_contracts_async(self.db, asset_id)
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

        has_ledger = await asset_crud.has_contract_ledger_entries_async(
            self.db, asset_id
        )
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
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> tuple[list[Asset], int]:
        asset_crud = self.asset_crud
        resolved_party_filter = await self._resolve_party_filter(
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
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
        if resolved_party_filter is not None:
            query_kwargs["party_filter"] = resolved_party_filter
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
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> Asset:
        asset_crud = self.asset_crud
        resolved_party_filter = await self._resolve_party_filter(
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            raise ResourceNotFoundError("Asset", asset_id)

        query_kwargs: dict[str, Any] = {
            "db": self.db,
            "id": asset_id,
            "use_cache": use_cache,
        }
        if resolved_party_filter is not None:
            query_kwargs["party_filter"] = resolved_party_filter
        asset = cast(
            Asset | None,
            await asset_crud.get_async(**query_kwargs),
        )
        if not asset or asset.data_status == DataStatusValues.ASSET_DELETED:
            raise ResourceNotFoundError("Asset", asset_id)
        return asset

    async def get_asset_lease_summary(
        self,
        asset_id: str,
        *,
        period_start: date | None = None,
        period_end: date | None = None,
        current_user_id: str | None = None,
    ) -> AssetLeaseSummaryResponse:
        period_start, period_end = normalize_summary_period(period_start, period_end)

        asset = await self.get_asset(asset_id, current_user_id=current_user_id)
        contracts = await contract_crud.get_active_by_asset_id(
            self.db,
            asset_id=asset_id,
            active_statuses=ACTIVE_CONTRACT_STATUSES,
        )

        type_buckets: dict[str, list[Any]] = defaultdict(list)
        for contract in contracts:
            relation_type = getattr(contract, "group_relation_type", None)
            key = relation_type.value if isinstance(relation_type, GroupRelationType) else str(relation_type)
            type_buckets[key].append(contract)

        by_type: list[ContractTypeSummary] = []
        for relation_type, label in (
            ("上游", "上游承租"),
            ("下游", "下游转租"),
            ("委托", "委托协议"),
            ("直租", "直租合同"),
        ):
            bucket = type_buckets.get(relation_type, [])
            monthly_amount = sum(
                (
                    _as_decimal(getattr(contract.lease_detail, "monthly_rent_base", None))
                    for contract in bucket
                    if getattr(contract, "lease_detail", None) is not None
                ),
                start=Decimal("0"),
            )
            by_type.append(
                ContractTypeSummary(
                    group_relation_type=relation_type,
                    label=label,
                    contract_count=len(bucket),
                    total_area=0.0,
                    monthly_amount=float(monthly_amount),
                )
            )

        party_counter: dict[tuple[str, str], tuple[str | None, int]] = {}
        outbound_types = {
            GroupRelationType.DOWNSTREAM.value,
            GroupRelationType.DIRECT_LEASE.value,
        }
        for contract in contracts:
            relation_type = getattr(contract, "group_relation_type", None)
            relation_value = (
                relation_type.value
                if isinstance(relation_type, GroupRelationType)
                else str(relation_type)
            )
            if relation_value not in outbound_types:
                continue

            lease_detail = getattr(contract, "lease_detail", None)
            lessee_party = getattr(contract, "lessee_party", None)
            lessee_name = (
                getattr(lease_detail, "tenant_name", None)
                or getattr(lessee_party, "name", None)
                or "未知租户"
            )
            party_id = str(getattr(contract, "lessee_party_id", "")).strip() or None
            key = (lessee_name, relation_value)
            prev_party_id, prev_count = party_counter.get(key, (party_id, 0))
            party_counter[key] = (prev_party_id or party_id, prev_count + 1)

        customer_summary = [
            ContractPartyItem(
                party_id=party_id,
                party_name=party_name,
                group_relation_type=relation_type,
                contract_count=contract_count,
            )
            for (party_name, relation_type), (party_id, contract_count) in party_counter.items()
        ]

        rentable_area = _as_decimal(getattr(asset, "rentable_area", None))

        return AssetLeaseSummaryResponse(
            asset_id=str(getattr(asset, "id")),
            period_start=period_start,
            period_end=period_end,
            total_contracts=len(contracts),
            total_rented_area=0.0,
            rentable_area=float(rentable_area),
            occupancy_rate=0.0,
            by_type=by_type,
            customer_summary=customer_summary,
        )

    async def get_asset_history_records(
        self,
        asset_id: str,
        *,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> list[AssetHistory]:
        await self.get_asset(
            asset_id,
            party_filter=party_filter,
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
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> list[str]:
        asset_crud = self.asset_crud
        resolved_party_filter = await self._resolve_party_filter(
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if self._is_fail_closed_party_filter(resolved_party_filter):
            return []
        query_kwargs: dict[str, Any] = {}
        if resolved_party_filter is not None:
            query_kwargs["party_filter"] = resolved_party_filter
        values = await asset_crud.get_distinct_field_values(
            self.db, field_name, **query_kwargs
        )
        return [str(value) for value in values]

    async def get_ownership_entity_names(self) -> list[str]:
        """获取所有正常状态的权属方名称列表"""
        return await ownership.get_names_by_status_async(
            self.db, data_status=DataStatusValues.ASSET_NORMAL
        )

    async def resolve_owner_party_scope_by_ownership_id_async(
        self,
        *,
        ownership_id: str,
    ) -> str | None:
        normalized_ownership_id = _normalize_optional_str(ownership_id)
        if normalized_ownership_id is None:
            return None

        ownership_obj = await ownership.get(self.db, id=normalized_ownership_id)
        ownership_code = _normalize_optional_str(
            getattr(ownership_obj, "code", None) if ownership_obj is not None else None
        )
        ownership_name = _normalize_optional_str(
            getattr(ownership_obj, "name", None) if ownership_obj is not None else None
        )

        resolved_party_id = await party_crud.resolve_legal_entity_party_id(
            self.db,
            ownership_id=normalized_ownership_id,
            ownership_code=ownership_code,
            ownership_name=ownership_name,
        )
        return _normalize_optional_str(resolved_party_id)

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
        default_org_id = getattr(current_user, "default_organization_id", None)  # DEPRECATED legacy org scope fallback
        organization_id = (  # DEPRECATED alias
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
                db=self.db, asset_name=asset_in.asset_name
            )
            if existing_asset:
                raise DuplicateResourceError(
                    "Asset", "asset_name", asset_in.asset_name
                )

            # 3. 自动计算与一致性验证
            asset_data = asset_in.model_dump()
            asset_data = await self._resolve_ownership(asset_data)
            calculated_fields = AssetCalculator.auto_calculate_fields(asset_data)
            final_data = {**asset_data, **calculated_fields}

            # 3a. 拼接半结构化地址（address 为只读展示字段，创建时必须由子字段生成）
            composed_address = _compose_address(final_data)
            if composed_address is not None:
                final_data["address"] = composed_address
            else:
                raise validation_error(
                    "地址信息不完整：请提供 address_detail 以生成地址",
                    field_errors={"address_detail": "required_for_address_composition"},
                )

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
                    organization_id=organization_id,  # DEPRECATED alias
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
                new_name = update_data_raw.get("asset_name")
                if new_name and new_name != asset.asset_name:
                    existing_asset = await asset_crud.get_by_name_async(
                        db=self.db, asset_name=new_name
                    )
                    if existing_asset and existing_asset.id != asset_id:
                        raise DuplicateResourceError("Asset", "asset_name", new_name)

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

                # 4a. 如地址子字段有变更，重新拼接 address
                if any(f in final_update for f in _ADDRESS_SUB_FIELDS):
                    composed_address = _compose_address(final_update, current_asset=asset)
                    if composed_address:
                        final_update["address"] = composed_address

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
                history.description = f"删除资产: {asset.asset_name}"
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
                history.description = f"恢复资产: {asset.asset_name}"
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
