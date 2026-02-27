"""
租金统计模块
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.enums import ContractStatus
from ....core.exception_handler import (
    BaseBusinessError,
    bad_request,
    forbidden,
    internal_error,
)
from ....database import get_async_db
from ....middleware.auth import AuthzContext, get_current_active_user, require_authz
from ....models.auth import User
from ....schemas.rent_contract import (
    AssetRentStatistics,
    MonthlyRentStatistics,
    OwnershipRentStatistics,
    RentStatisticsQuery,
)
from ....services.rent_contract import rent_contract_service

router = APIRouter()
_ADMIN_BYPASS_REASON_CODE = "rbac_admin_bypass"


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized == "":
        return None
    return normalized


def _normalize_identifier_list(value: list[str] | None) -> list[str] | None:
    if value is None:
        return None
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        normalized_item = _normalize_optional_str(item)
        if normalized_item is None:
            continue
        if normalized_item in seen:
            continue
        seen.add(normalized_item)
        normalized.append(normalized_item)
    return normalized


def _normalize_identifier_sequence(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized_values: list[str] = []
    for value in values:
        normalized = _normalize_optional_str(value)
        if normalized is None:
            continue
        normalized_values.append(normalized)
    return normalized_values


def _resolve_authz_scope_party_ids(
    *,
    authz_ctx: Any,
    field: str,
    list_field: str,
) -> list[str]:
    if not isinstance(authz_ctx, AuthzContext):
        return []
    if _normalize_optional_str(authz_ctx.reason_code) == _ADMIN_BYPASS_REASON_CODE:
        return []
    scope_ids = _normalize_identifier_sequence(
        authz_ctx.resource_context.get(list_field),
    )
    if scope_ids:
        return scope_ids
    scoped_party_id = _normalize_optional_str(authz_ctx.resource_context.get(field))
    if scoped_party_id is None:
        return []
    return [scoped_party_id]


def _resolve_effective_scope_filters(
    *,
    authz_ctx: Any,
    requested_owner_party_ids: list[str] | None,
) -> tuple[list[str] | None, list[str] | None]:
    scoped_owner_party_ids = _resolve_authz_scope_party_ids(
        authz_ctx=authz_ctx,
        field="owner_party_id",
        list_field="owner_party_ids",
    )
    scoped_manager_party_ids = _resolve_authz_scope_party_ids(
        authz_ctx=authz_ctx,
        field="manager_party_id",
        list_field="manager_party_ids",
    )
    requested_owner_ids = _normalize_identifier_list(requested_owner_party_ids)
    if requested_owner_ids == []:
        requested_owner_ids = None

    if requested_owner_ids is not None:
        if scoped_owner_party_ids and any(
            owner_id not in scoped_owner_party_ids for owner_id in requested_owner_ids
        ):
            raise forbidden("权限不足")
        if not scoped_owner_party_ids and scoped_manager_party_ids:
            # Manager-only scoped callers cannot inject owner filters.
            raise forbidden("权限不足")
        effective_owner_ids = requested_owner_ids
    elif scoped_owner_party_ids:
        effective_owner_ids = scoped_owner_party_ids
    else:
        effective_owner_ids = None

    effective_manager_ids: list[str] | None = None
    if requested_owner_ids is None and scoped_manager_party_ids:
        effective_manager_ids = scoped_manager_party_ids
    return effective_owner_ids, effective_manager_ids


@router.get("/statistics/overview", summary="获取租金统计概览")
async def get_rent_statistics(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="rent_contract",
        )
    ),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    owner_party_ids: list[str] | None = Query(None, description="产权方主体ID列表"),
    ownership_ids: list[str] | None = Query(  # DEPRECATED alias
        None,
        description="权属方ID列表（DEPRECATED）",
    ),
    asset_ids: list[str] | None = Query(None, description="资产ID列表"),
    contract_status: str | None = Query(None, description="合同状态"),
) -> Any:
    """
    获取租金统计概览信息
    """
    effective_owner_party_ids, effective_manager_party_ids = (
        _resolve_effective_scope_filters(
            authz_ctx=authz_ctx,
            requested_owner_party_ids=owner_party_ids,
        )
    )
    parsed_contract_status = None
    if contract_status:
        try:
            parsed_contract_status = ContractStatus(contract_status)
        except ValueError:
            raise bad_request("合同状态不合法", field="contract_status")

    query_params = RentStatisticsQuery(
        start_date=start_date,
        end_date=end_date,
        owner_party_ids=effective_owner_party_ids,
        manager_party_ids=effective_manager_party_ids,
        ownership_ids=ownership_ids,  # DEPRECATED alias
        asset_ids=asset_ids,
        contract_status=parsed_contract_status,
    )

    try:
        statistics = await rent_contract_service.get_statistics_async(
            db=db, query_params=query_params
        )
        return statistics
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"获取统计信息失败: {str(e)}")


@router.get(
    "/statistics/ownership",
    response_model=list[OwnershipRentStatistics],
    summary="权属方租金统计",
)
async def get_ownership_statistics(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="rent_contract",
        )
    ),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    owner_party_ids: list[str] | None = Query(None, description="产权方主体ID列表"),
    ownership_ids: list[str] | None = Query(  # DEPRECATED alias
        None,
        description="权属方ID列表（DEPRECATED）",
    ),
) -> Any:
    """
    按权属方统计租金情况
    """
    effective_owner_party_ids, effective_manager_party_ids = (
        _resolve_effective_scope_filters(
            authz_ctx=authz_ctx,
            requested_owner_party_ids=owner_party_ids,
        )
    )
    effective_ownership_ids = ownership_ids
    if effective_owner_party_ids is not None or effective_manager_party_ids is not None:
        # Avoid legacy ownership-id path widening scoped queries.
        effective_ownership_ids = None
    try:
        statistics = await rent_contract_service.get_ownership_statistics_async(
            db=db,
            start_date=start_date,
            end_date=end_date,
            owner_party_ids=effective_owner_party_ids,
            manager_party_ids=effective_manager_party_ids,
            ownership_ids=effective_ownership_ids,  # DEPRECATED alias
        )
        return statistics
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"获取权属方统计失败: {str(e)}")


@router.get(
    "/statistics/asset",
    response_model=list[AssetRentStatistics],
    summary="资产租金统计",
)
async def get_asset_statistics(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="rent_contract",
        )
    ),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    asset_ids: list[str] | None = Query(None, description="资产ID列表"),
) -> Any:
    """
    按资产统计租金情况
    """
    effective_owner_party_ids, effective_manager_party_ids = (
        _resolve_effective_scope_filters(
            authz_ctx=authz_ctx,
            requested_owner_party_ids=None,
        )
    )
    try:
        statistics = await rent_contract_service.get_asset_statistics_async(
            db=db,
            start_date=start_date,
            end_date=end_date,
            owner_party_ids=effective_owner_party_ids,
            manager_party_ids=effective_manager_party_ids,
            asset_ids=asset_ids,
        )
        return statistics
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"获取资产统计失败: {str(e)}")


@router.get(
    "/statistics/monthly",
    response_model=list[MonthlyRentStatistics],
    summary="月度租金统计",
)
async def get_monthly_statistics(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="rent_contract",
        )
    ),
    year: int | None = Query(None, description="年份"),
    start_month: str | None = Query(None, description="开始月份(YYYY-MM)"),
    end_month: str | None = Query(None, description="结束月份(YYYY-MM)"),
) -> Any:
    """
    获取月度租金统计
    """
    effective_owner_party_ids, effective_manager_party_ids = (
        _resolve_effective_scope_filters(
            authz_ctx=authz_ctx,
            requested_owner_party_ids=None,
        )
    )
    try:
        statistics = await rent_contract_service.get_monthly_statistics_async(
            db=db,
            year=year,
            start_month=start_month,
            end_month=end_month,
            owner_party_ids=effective_owner_party_ids,
            manager_party_ids=effective_manager_party_ids,
        )
        return statistics
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"获取月度统计失败: {str(e)}")


@router.get("/statistics/export", summary="导出统计数据")
async def export_statistics(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="rent_contract",
        )
    ),
    start_date: date | None = Query(None, description="开始日期"),
    end_date: date | None = Query(None, description="结束日期"),
    format: str = Query("excel", description="导出格式"),
) -> Any:
    """
    导出统计数据
    """
    try:
        from datetime import datetime

        from ..services.excel_export import export_statistics_report

        effective_owner_party_ids, effective_manager_party_ids = (
            _resolve_effective_scope_filters(
                authz_ctx=authz_ctx,
                requested_owner_party_ids=None,
            )
        )

        overview_stats = await rent_contract_service.get_statistics_async(
            db=db,
            query_params=RentStatisticsQuery(
                start_date=start_date,
                end_date=end_date,
                owner_party_ids=effective_owner_party_ids,
                manager_party_ids=effective_manager_party_ids,
                ownership_ids=None,  # DEPRECATED alias
                asset_ids=None,
                contract_status=None,
            ),
        )

        ownership_stats = await rent_contract_service.get_ownership_statistics_async(
            db=db,
            start_date=start_date,
            end_date=end_date,
            owner_party_ids=effective_owner_party_ids,
            manager_party_ids=effective_manager_party_ids,
            ownership_ids=None,  # DEPRECATED alias
        )

        asset_stats = await rent_contract_service.get_asset_statistics_async(
            db=db,
            start_date=start_date,
            end_date=end_date,
            owner_party_ids=effective_owner_party_ids,
            manager_party_ids=effective_manager_party_ids,
        )

        monthly_stats = await rent_contract_service.get_monthly_statistics_async(
            db=db,
            owner_party_ids=effective_owner_party_ids,
            manager_party_ids=effective_manager_party_ids,
        )

        excel_data = export_statistics_report(
            overview_data=overview_stats,
            ownership_data=ownership_stats,
            asset_data=asset_stats,
            monthly_data=monthly_stats,
            start_date=start_date,
            end_date=end_date,
        )

        filename = f"rent_statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return Response(
            content=excel_data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"导出统计数据失败: {str(e)}")
