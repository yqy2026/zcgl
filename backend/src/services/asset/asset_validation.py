"""
资产验证与工具函数

纯函数 / 静态工具：数值转换、日期区间归一化、布尔过滤器解析、
地址拼接、``build_filters`` 静态方法、权属主体解析、关联检查等。
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from ...core.exception_handler import operation_not_allowed, validation_error
from ...utils.str import normalize_optional_str

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# 数值 / 日期工具
# ---------------------------------------------------------------------------


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
        normalized_start, _ = _month_bounds(period_end)  # type: ignore[arg-type]
        return normalized_start, period_end  # type: ignore[return-value]
    if period_end is None:
        _, normalized_end = _month_bounds(period_start)
        return period_start, normalized_end
    return period_start, period_end


# ---------------------------------------------------------------------------
# 布尔过滤器
# ---------------------------------------------------------------------------


def _normalize_bool_filter(value: bool | str | None, *, field_name: str) -> bool | None:
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


# ---------------------------------------------------------------------------
# 地址拼接
# ---------------------------------------------------------------------------

_ADDRESS_SUB_FIELDS = ("province_code", "city_code", "district_code", "address_detail")


def _compose_address(
    data: dict[str, Any], current_asset: Any | None = None
) -> str | None:
    """根据半结构化地址子字段拼接只读展示用 address.

    优先使用 data 中的字段，缺少时回退到 current_asset 的现有字段。
    若 address_detail 缺失，返回 None（不覆盖现有 address）。
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


# ---------------------------------------------------------------------------
# build_filters — 静态构建查询过滤字典
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# 权属主体解析（async — 需要 db session）
# ---------------------------------------------------------------------------


async def resolve_owner_party_scope_by_ownership_id(
    db: AsyncSession,
    *,
    ownership_id: str,
) -> str | None:
    """根据 legacy ownership_id 解析对应的 party_id。"""
    from ...crud.ownership import ownership
    from ...crud.party import party_crud

    normalized_ownership_id = normalize_optional_str(ownership_id)
    if normalized_ownership_id is None:
        return None

    ownership_obj = await ownership.get(db, id=normalized_ownership_id)
    ownership_code = normalize_optional_str(
        getattr(ownership_obj, "code", None) if ownership_obj is not None else None
    )
    ownership_name = normalize_optional_str(
        getattr(ownership_obj, "name", None) if ownership_obj is not None else None
    )

    resolved_party_id = await party_crud.resolve_legal_entity_party_id(
        db,
        ownership_id=normalized_ownership_id,
        ownership_code=ownership_code,
        ownership_name=ownership_name,
    )
    return normalize_optional_str(resolved_party_id)


async def resolve_ownership(
    db: AsyncSession,
    data: dict[str, Any],
    *,
    current_asset: Any | None = None,
) -> dict[str, Any]:
    """解析并验证权属主体 / 经营管理主体，返回修改后的 *data* 字典。"""
    from ...crud.party import party_crud

    owner_party_id = normalize_optional_str(data.get("owner_party_id"))
    legacy_ownership_id = normalize_optional_str(data.get("ownership_id"))
    if owner_party_id is None and legacy_ownership_id is not None:
        owner_party_id = await resolve_owner_party_scope_by_ownership_id(
            db, ownership_id=legacy_ownership_id
        )
    if owner_party_id is None and current_asset is not None:
        owner_party_id = normalize_optional_str(
            getattr(current_asset, "owner_party_id", None)
        )

    if not owner_party_id and current_asset is None:
        raise validation_error(
            "权属主体不能为空", field_errors={"owner_party_id": "权属主体不能为空"}
        )

    if owner_party_id:
        party_obj = await party_crud.get_party(db, party_id=owner_party_id)
        if party_obj is None and legacy_ownership_id is None:
            fallback_party_id = await resolve_owner_party_scope_by_ownership_id(
                db, ownership_id=owner_party_id
            )
            if fallback_party_id is not None and fallback_party_id != owner_party_id:
                owner_party_id = fallback_party_id
                party_obj = await party_crud.get_party(db, party_id=owner_party_id)
        if not party_obj:
            raise validation_error(
                "权属主体不存在", field_errors={"owner_party_id": "权属主体不存在"}
            )

    manager_party_id = normalize_optional_str(data.get("manager_party_id"))
    legacy_management_entity = normalize_optional_str(data.get("management_entity"))
    legacy_organization_id = normalize_optional_str(data.get("organization_id"))

    if manager_party_id is None and legacy_management_entity is not None:
        manager_party_id = legacy_management_entity

    if manager_party_id is None and legacy_organization_id is not None:
        resolved_org_party_id = await party_crud.resolve_organization_party_id(
            db, organization_id=legacy_organization_id
        )
        manager_party_id = (
            resolved_org_party_id
            if resolved_org_party_id is not None
            else legacy_organization_id
        )

    if manager_party_id is None and current_asset is not None:
        manager_party_id = normalize_optional_str(
            getattr(current_asset, "manager_party_id", None)
        )

    if manager_party_id is None and owner_party_id is not None:
        manager_party_id = owner_party_id

    if manager_party_id:
        manager_party_obj = await party_crud.get_party(db, party_id=manager_party_id)
        if manager_party_obj is None:
            fallback_manager_party_id = await resolve_owner_party_scope_by_ownership_id(
                db, ownership_id=manager_party_id
            )
            if (
                fallback_manager_party_id is not None
                and fallback_manager_party_id != manager_party_id
            ):
                manager_party_id = fallback_manager_party_id
                manager_party_obj = await party_crud.get_party(
                    db, party_id=manager_party_id
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


# ---------------------------------------------------------------------------
# 资产关联检查（async — 需要 db session + asset_crud）
# ---------------------------------------------------------------------------


async def ensure_asset_not_linked(
    db: AsyncSession, asset_id: str, asset_crud: Any
) -> None:
    """确保资产未关联合同 / 产权证 / 台账，否则抛出异常。"""
    has_contract = await asset_crud.has_contracts_async(db, asset_id)
    if has_contract:
        raise operation_not_allowed(
            "资产已关联合同，禁止删除",
            reason="asset_has_contracts",
        )

    has_certificate = await asset_crud.has_property_certs_async(db, asset_id)
    if has_certificate:
        raise operation_not_allowed(
            "资产已关联产权证，禁止删除",
            reason="asset_has_certificates",
        )

    has_ledger = await asset_crud.has_contract_ledger_entries_async(db, asset_id)
    if has_ledger:
        raise operation_not_allowed(
            "资产已有租金台账记录，禁止删除",
            reason="asset_has_ledger",
        )
