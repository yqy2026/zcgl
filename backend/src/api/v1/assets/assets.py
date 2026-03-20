"""
资产管理API路由聚合入口。

本文件保留资产核心 CRUD 与筛选辅助接口，
批量、导入、附件能力由子路由模块承载：
- asset_batch.py: 批量操作端点
- asset_import.py: 导入功能端点
- asset_attachments.py: 附件相关端点
"""

import logging
import os
from collections.abc import Sequence
from datetime import date
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    Path,
    Query,
    Request,
    Response,
)
from fastapi.encoders import jsonable_encoder
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_204_NO_CONTENT

from ....constants.api_constants import PaginationLimits
from ....constants.business_constants import DateTimeFields
from ....core.exception_handler import forbidden
from ....core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ....database import get_async_db
from ....middleware.auth import (
    AuthzContext,
    audit_action,
    get_current_active_user,
    require_admin,
    require_authz,
)
from ....middleware.security_middleware import get_client_ip
from ....models.auth import User
from ....schemas.asset import (
    AssetCreate,
    AssetLeaseSummaryResponse,
    AssetListItemResponse,
    AssetResponse,
    AssetReviewLogResponse,
    AssetReviewRejectRequest,
    AssetUpdate,
)
from ....services.asset.asset_service import (
    AssetService,
    AsyncAssetService,
)
from ....services.authz import authz_service
from ....services.view_scope import resolve_selected_view_party_filter_dependency
from ....utils.str import normalize_optional_str

# 导入子路由模块
from . import asset_attachments, asset_batch, asset_import

# 获取开发模式配置，但不完全绕过认证
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

# 创建资产路由器
router = APIRouter()
logger = logging.getLogger(__name__)

# 包含子路由器
router.include_router(asset_batch.router, tags=["资产批量操作"])
router.include_router(asset_import.router, tags=["资产导入"])
router.include_router(asset_attachments.router, tags=["资产附件"])

_asset_response_list_adapter = TypeAdapter(list[AssetResponse])
_asset_list_item_adapter = TypeAdapter(list[AssetListItemResponse])
_ASSET_CREATE_UNSCOPED_PARTY_ID = "__unscoped__:asset:create"


def _normalize_identifier_sequence(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized_values: list[str] = []
    for value in values:
        normalized_value = normalize_optional_str(value)
        if normalized_value is None:
            continue
        normalized_values.append(normalized_value)
    return normalized_values


def _resolve_operator_name(current_user: User) -> str:
    return (
        str(getattr(current_user, "full_name", "")).strip()
        or str(getattr(current_user, "username", "")).strip()
        or str(current_user.id)
    )


async def _resolve_owner_party_scope_by_ownership_id(
    *,
    db: AsyncSession,
    ownership_id: str | None,
) -> str | None:
    normalized_ownership_id = normalize_optional_str(ownership_id)
    if normalized_ownership_id is None:
        return None
    resolved_party_id = await AsyncAssetService(
        db
    ).resolve_owner_party_scope_by_ownership_id_async(
        ownership_id=normalized_ownership_id
    )
    return normalize_optional_str(resolved_party_id)


async def _build_subject_scope_hint(
    *,
    db: AsyncSession,
    user_id: str,
) -> dict[str, str]:
    try:
        subject_context = await authz_service.context_builder.build_subject_context(
            db,
            user_id=user_id,
        )
    except Exception:
        return {}

    owner_party_ids = _normalize_identifier_sequence(
        getattr(subject_context, "owner_party_ids", [])
    )
    manager_party_ids = _normalize_identifier_sequence(
        getattr(subject_context, "manager_party_ids", [])
    )
    scope_hint: dict[str, str] = {}
    if len(owner_party_ids) > 0:
        scope_hint["owner_party_id"] = owner_party_ids[0]
    if len(manager_party_ids) > 0:
        scope_hint["manager_party_id"] = manager_party_ids[0]

    party_candidates = [*owner_party_ids, *manager_party_ids]
    if len(party_candidates) > 0:
        scope_hint["party_id"] = party_candidates[0]
    return scope_hint


async def _require_asset_collection_read_authz(
    ownership_id: str | None = Query(None, description="权属方ID筛选"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    normalized_ownership_id = normalize_optional_str(ownership_id)
    resource_context: dict[str, Any] = {}
    if normalized_ownership_id is not None:
        resource_context["ownership_id"] = normalized_ownership_id
        resolved_owner_party_id = await _resolve_owner_party_scope_by_ownership_id(
            db=db,
            ownership_id=normalized_ownership_id,
        )
        if resolved_owner_party_id is not None:
            resource_context["owner_party_id"] = resolved_owner_party_id
            resource_context["party_id"] = resolved_owner_party_id

    subject_scope_hint = await _build_subject_scope_hint(
        db=db,
        user_id=str(current_user.id),
    )
    for key, value in subject_scope_hint.items():
        resource_context.setdefault(key, value)

    try:
        decision = await authz_service.check_access(
            db,
            user_id=str(current_user.id),
            resource_type="asset",
            action="read",
            resource_id=None,
            resource=resource_context,
        )
    except Exception:
        raise forbidden("权限校验失败")

    if not decision.allowed:
        raise forbidden("权限不足")

    return AuthzContext(
        current_user=current_user,
        action="read",
        resource_type="asset",
        resource_id=None,
        resource_context=resource_context,
        allowed=True,
        reason_code=decision.reason_code,
    )


async def _require_asset_create_authz(
    asset_in: AssetCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    owner_party_id = normalize_optional_str(asset_in.owner_party_id)
    manager_party_id = normalize_optional_str(asset_in.manager_party_id)
    ownership_id = normalize_optional_str(asset_in.ownership_id)
    organization_id = normalize_optional_str(asset_in.organization_id)
    asset_in.owner_party_id = owner_party_id
    asset_in.manager_party_id = manager_party_id
    asset_in.ownership_id = ownership_id
    asset_in.organization_id = organization_id
    resource_context: dict[str, Any] = {}
    if owner_party_id is not None:
        resource_context["owner_party_id"] = owner_party_id
    if manager_party_id is not None:
        resource_context["manager_party_id"] = manager_party_id
    if ownership_id is not None:
        resource_context["ownership_id"] = ownership_id
    if manager_party_id is None:
        subject_scope_hint = await _build_subject_scope_hint(
            db=db,
            user_id=str(current_user.id),
        )
        inferred_manager_party_id = normalize_optional_str(
            subject_scope_hint.get("manager_party_id")
        )
        if inferred_manager_party_id is not None:
            manager_party_id = inferred_manager_party_id
            resource_context["manager_party_id"] = inferred_manager_party_id
    resolved_owner_party_id: str | None = None
    if owner_party_id is None and ownership_id is not None:
        resolved_owner_party_id = await _resolve_owner_party_scope_by_ownership_id(
            db=db,
            ownership_id=ownership_id,
        )
        if resolved_owner_party_id is not None:
            asset_in.owner_party_id = resolved_owner_party_id
            resource_context["owner_party_id"] = resolved_owner_party_id
    if organization_id is not None:
        resource_context["organization_id"] = organization_id
    resolved_party_id = (
        manager_party_id
        or owner_party_id
        or resolved_owner_party_id
        or organization_id
        or _ASSET_CREATE_UNSCOPED_PARTY_ID
    )
    resource_context["party_id"] = resolved_party_id

    try:
        decision = await authz_service.check_access(
            db,
            user_id=str(current_user.id),
            resource_type="asset",
            action="create",
            resource_id=None,
            resource=resource_context,
        )
    except Exception:
        raise forbidden("权限校验失败")

    if not decision.allowed:
        raise forbidden("权限不足")

    return AuthzContext(
        current_user=current_user,
        action="create",
        resource_type="asset",
        resource_id=None,
        resource_context=resource_context,
        allowed=True,
        reason_code=decision.reason_code,
    )


async def _get_distinct_values(
    db: AsyncSession,
    field_name: str,
    current_user_id: str,
) -> list[str]:
    return await AsyncAssetService(db).get_distinct_field_values(
        field_name,
        current_user_id=current_user_id,
    )


@router.get(
    "",
    response_model=APIResponse[PaginatedData[AssetResponse | AssetListItemResponse]],
    summary="获取资产列表",
)
async def get_assets(
    request: Request,
    page: int = Query(PaginationLimits.DEFAULT_PAGE, ge=1, description="页码"),
    page_size: int = Query(
        PaginationLimits.DEFAULT_PAGE_SIZE,
        ge=PaginationLimits.MIN_PAGE_SIZE,
        le=PaginationLimits.MAX_PAGE_SIZE,
        description="每页记录数",
    ),
    search: str | None = Query(None, description="搜索关键词"),
    ownership_status: str | None = Query(None, description="确权状态筛选"),
    property_nature: str | None = Query(None, description="物业性质筛选"),
    usage_status: str | None = Query(None, description="使用状态筛选"),
    ownership_id: str | None = Query(None, description="权属方ID筛选"),
    management_entity: str | None = Query(None, description="经营管理方筛选"),
    business_category: str | None = Query(None, description="业态类别筛选"),
    data_status: str | None = Query(None, description="数据状态筛选"),
    min_area: float | None = Query(None, ge=0, description="最小面积筛选"),
    max_area: float | None = Query(None, ge=0, description="最大面积筛选"),
    min_occupancy_rate: float | None = Query(None, ge=0, description="最小出租率筛选"),
    max_occupancy_rate: float | None = Query(None, ge=0, description="最大出租率筛选"),
    is_litigated: bool | str | None = Query(
        None, description="是否涉诉筛选（支持 true/false 或 是/否）"
    ),
    include_relations: bool = Query(False, description="是否加载关联数据"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_asset_collection_read_authz),
    selected_view_party_filter=Depends(resolve_selected_view_party_filter_dependency),
    sort_field: str | None = Query(None, description="排序字段"),
    sort_by: str | None = Query(None, description="排序字段（兼容参数）"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
) -> Response:
    """
    获取资产列表，支持分页、搜索和筛选

    - **page**: 页码，从1开始
    - **limit**: 每页记录数，最多100
    - **search**: 搜索关键词，会在物业名称、地址、权属方等字段中搜索
    - **ownership_status**: 按确权状态筛选
    - **property_nature**: 按物业性质筛选
    - **usage_status**: 按使用状态筛选
    - **ownership_id**: 按权属方ID筛选
    - **sort_field**: 排序字段
    - **sort_by**: 排序字段（兼容参数）
    - **sort_order**: 排序方向（asc/desc）
    - **include_relations**: 是否加载关联数据（默认不加载）
    """
    resolved_sort_field = (
        sort_field
        if sort_field is not None and sort_field != ""
        else sort_by
        if sort_by is not None and sort_by != ""
        else DateTimeFields.CREATED_AT
    )

    filters = AssetService.build_filters(
        ownership_status=ownership_status,
        property_nature=property_nature,
        usage_status=usage_status,
        ownership_id=ownership_id,
        management_entity=management_entity,
        business_category=business_category,
        data_status=data_status,
        min_area=min_area,
        max_area=max_area,
        min_occupancy_rate=min_occupancy_rate,
        max_occupancy_rate=max_occupancy_rate,
        is_litigated=is_litigated,
    )

    asset_service = AsyncAssetService(db)
    assets, total = await asset_service.get_assets(
        skip=(page - 1) * page_size,
        limit=page_size,
        search=search,
        filters=filters,
        sort_field=resolved_sort_field,
        sort_order=sort_order,
        include_relations=include_relations,
        party_filter=selected_view_party_filter,
        current_user_id=str(current_user.id),
    )

    items: Sequence[AssetResponse | AssetListItemResponse]
    if include_relations:
        items = _asset_response_list_adapter.validate_python(
            assets, from_attributes=True
        )
    else:
        items = _asset_list_item_adapter.validate_python(assets, from_attributes=True)
    return ResponseHandler.paginated(
        data=list(items),
        page=page,
        page_size=page_size,
        total=total,
        message="获取资产列表成功",
    )


# ===== 搜索筛选辅助接口 ===== (必须在 /{asset_id} 路由之前)


@router.get("/ownership-entities", response_model=list[str], summary="获取权属方列表")
async def get_ownership_entities(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_asset_collection_read_authz),
) -> list[str]:
    """获取所有权属方列表，用于搜索筛选"""
    return await AsyncAssetService(db).get_ownership_entity_names()


@router.get(
    "/business-categories", response_model=list[str], summary="获取业态类别列表"
)
async def get_business_categories(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_asset_collection_read_authz),
) -> list[str]:
    """获取所有业态类别列表，用于搜索筛选"""
    return await _get_distinct_values(db, "business_category", str(current_user.id))


@router.get("/usage-statuses", response_model=list[str], summary="获取使用情况列表")
async def get_usage_statuses(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_asset_collection_read_authz),
) -> list[str]:
    """获取所有使用情况列表，用于搜索筛选"""
    return await _get_distinct_values(db, "usage_status", str(current_user.id))


@router.get("/property-natures", response_model=list[str], summary="获取物业性质列表")
async def get_property_natures(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_asset_collection_read_authz),
) -> list[str]:
    """获取所有物业性质列表，用于搜索筛选"""
    return await _get_distinct_values(db, "property_nature", str(current_user.id))


@router.get("/ownership-statuses", response_model=list[str], summary="获取确权状态列表")
async def get_ownership_statuses(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_asset_collection_read_authz),
) -> list[str]:
    """获取所有确权状态列表，用于搜索筛选"""
    return await _get_distinct_values(db, "ownership_status", str(current_user.id))


# ===== 单个资产操作接口 =====


@router.get("/{asset_id}", response_model=AssetResponse, summary="获取资产详情")
async def get_asset(
    request: Request,
    asset_id: str = Path(..., description="资产ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="asset",
            resource_id="{asset_id}",
            deny_as_not_found=True,
        )
    ),
    selected_view_party_filter=Depends(resolve_selected_view_party_filter_dependency),
) -> AssetResponse:
    """
    根据ID获取单个资产的详细信息

    - **asset_id**: 资产ID
    """
    asset_service = AsyncAssetService(db)
    asset = await asset_service.get_asset(
        asset_id,
        party_filter=selected_view_party_filter,
        current_user_id=str(current_user.id),
    )
    return AssetResponse.model_validate(asset)


@router.post(
    "/{asset_id}/submit-review",
    response_model=AssetResponse,
    summary="提交资产审核",
)
async def submit_asset_review(
    asset_id: str = Path(..., description="资产ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="asset",
            resource_id="{asset_id}",
        )
    ),
) -> AssetResponse:
    _ = _authz
    asset = await AsyncAssetService(db).submit_asset_review(
        asset_id,
        operator=_resolve_operator_name(current_user),
    )
    return AssetResponse.model_validate(asset)


@router.post(
    "/{asset_id}/approve-review",
    response_model=AssetResponse,
    summary="审核通过资产",
)
async def approve_asset_review(
    asset_id: str = Path(..., description="资产ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="asset",
            resource_id="{asset_id}",
        )
    ),
) -> AssetResponse:
    _ = _authz
    asset = await AsyncAssetService(db).approve_asset_review(
        asset_id,
        reviewer=_resolve_operator_name(current_user),
    )
    return AssetResponse.model_validate(asset)


@router.post(
    "/{asset_id}/reject-review",
    response_model=AssetResponse,
    summary="驳回资产审核",
)
async def reject_asset_review(
    payload: AssetReviewRejectRequest,
    asset_id: str = Path(..., description="资产ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="asset",
            resource_id="{asset_id}",
        )
    ),
) -> AssetResponse:
    _ = _authz
    asset = await AsyncAssetService(db).reject_asset_review(
        asset_id,
        reviewer=_resolve_operator_name(current_user),
        reason=payload.reason,
    )
    return AssetResponse.model_validate(asset)


@router.post(
    "/{asset_id}/reverse-review",
    response_model=AssetResponse,
    summary="反审核资产",
)
async def reverse_asset_review(
    payload: AssetReviewRejectRequest,
    asset_id: str = Path(..., description="资产ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="asset",
            resource_id="{asset_id}",
        )
    ),
) -> AssetResponse:
    _ = _authz
    asset = await AsyncAssetService(db).reverse_asset_review(
        asset_id,
        reviewer=_resolve_operator_name(current_user),
        reason=payload.reason,
    )
    return AssetResponse.model_validate(asset)


@router.post(
    "/{asset_id}/resubmit-review",
    response_model=AssetResponse,
    summary="重提资产审核",
)
async def resubmit_asset_review(
    asset_id: str = Path(..., description="资产ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="asset",
            resource_id="{asset_id}",
        )
    ),
) -> AssetResponse:
    _ = _authz
    asset = await AsyncAssetService(db).resubmit_asset_review(
        asset_id,
        operator=_resolve_operator_name(current_user),
    )
    return AssetResponse.model_validate(asset)


@router.get(
    "/{asset_id}/review-logs",
    response_model=list[AssetReviewLogResponse],
    summary="获取资产审核历史",
)
async def get_asset_review_logs(
    asset_id: str = Path(..., description="资产ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="asset",
            resource_id="{asset_id}",
            deny_as_not_found=True,
        )
    ),
) -> list[AssetReviewLogResponse]:
    _ = _authz
    return await AsyncAssetService(db).get_asset_review_logs(
        asset_id,
        current_user_id=str(current_user.id),
    )


@router.get(
    "/{asset_id}/lease-summary",
    response_model=APIResponse[AssetLeaseSummaryResponse],
    summary="获取资产租赁汇总",
)
async def get_asset_lease_summary(
    asset_id: str = Path(..., description="资产ID"),
    period_start: date | None = Query(None, description="展示周期开始"),
    period_end: date | None = Query(None, description="展示周期结束"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="asset",
            resource_id="{asset_id}",
            deny_as_not_found=True,
        )
    ),
) -> APIResponse[AssetLeaseSummaryResponse]:
    asset_service = AsyncAssetService(db)
    summary = await asset_service.get_asset_lease_summary(
        asset_id,
        period_start=period_start,
        period_end=period_end,
        current_user_id=str(current_user.id),
    )
    payload = jsonable_encoder(summary)
    return ResponseHandler.success(
        data=payload,
        message="获取资产租赁汇总成功",
    )


@router.post("", response_model=AssetResponse, summary="创建新资产", status_code=201)
async def create_asset(
    asset_in: AssetCreate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_asset_create_authz),
    audit_logger: Any = Depends(audit_action("asset_create", "asset")),
) -> AssetResponse:
    """
    创建新的资产记录

    - **asset_in**: 资产创建数据
    """
    asset_service = AsyncAssetService(db)
    if isinstance(_authz_ctx, AuthzContext):
        resolved_owner_party_id = normalize_optional_str(
            _authz_ctx.resource_context.get("owner_party_id")
        )
        if (
            normalize_optional_str(asset_in.owner_party_id) is None
            and resolved_owner_party_id is not None
        ):
            asset_in.owner_party_id = resolved_owner_party_id
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    session_id = request.headers.get("X-Session-ID") or request.headers.get(
        "X-Session-Id"
    )
    asset = await asset_service.create_asset(
        asset_in,
        current_user,
        ip_address=ip_address,
        user_agent=user_agent,
        session_id=session_id,
    )
    return AssetResponse.model_validate(asset)


@router.put("/{asset_id}", response_model=AssetResponse, summary="更新资产")
async def update_asset(
    asset_id: str,
    asset_in: AssetUpdate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="asset",
            resource_id="{asset_id}",
        )
    ),
    audit_logger: Any = Depends(audit_action("asset_update", "asset")),
) -> AssetResponse:
    """
    更新资产信息

    - **asset_id**: 资产ID
    - **asset_in**: 资产更新数据
    """
    asset_service = AsyncAssetService(db)
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    session_id = request.headers.get("X-Session-ID") or request.headers.get(
        "X-Session-Id"
    )
    asset = await asset_service.update_asset(
        asset_id,
        asset_in,
        current_user,
        ip_address=ip_address,
        user_agent=user_agent,
        session_id=session_id,
    )
    return AssetResponse.model_validate(asset)


@router.delete("/{asset_id}", summary="删除资产")
async def delete_asset(
    asset_id: str = Path(..., description="资产ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="delete",
            resource_type="asset",
            resource_id="{asset_id}",
        )
    ),
    audit_logger: Any = Depends(audit_action("asset_delete", "asset")),
) -> Response:
    """
    删除资产记录

    - **asset_id**: 资产ID
    """
    asset_service = AsyncAssetService(db)
    await asset_service.delete_asset(asset_id, current_user)
    return Response(status_code=HTTP_204_NO_CONTENT)


@router.post("/{asset_id}/restore", response_model=AssetResponse, summary="恢复资产")
async def restore_asset(
    asset_id: str = Path(..., description="资产ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="asset",
            resource_id="{asset_id}",
        )
    ),
    audit_logger: Any = Depends(audit_action("asset_restore", "asset")),
) -> AssetResponse:
    """
    恢复已删除的资产记录

    - **asset_id**: 资产ID
    """
    asset_service = AsyncAssetService(db)
    asset = await asset_service.restore_asset(asset_id, current_user)
    return AssetResponse.model_validate(asset)


@router.delete("/{asset_id}/hard-delete", summary="彻底删除资产")
async def hard_delete_asset(
    asset_id: str = Path(..., description="资产ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="delete",
            resource_type="asset",
            resource_id="{asset_id}",
        )
    ),
    audit_logger: Any = Depends(audit_action("asset_hard_delete", "asset")),
) -> Response:
    """
    彻底删除资产记录（物理删除）

    - **asset_id**: 资产ID
    """
    asset_service = AsyncAssetService(db)
    await asset_service.hard_delete_asset(asset_id, current_user)
    return Response(status_code=HTTP_204_NO_CONTENT)


@router.get("/{asset_id}/history", summary="获取资产历史")
async def get_asset_history(
    asset_id: str = Path(..., description="资产ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="asset",
            resource_id="{asset_id}",
            deny_as_not_found=True,
        )
    ),
) -> dict[str, Any]:
    """
    获取资产的变更历史记录

    - **asset_id**: 资产ID
    """
    asset_service = AsyncAssetService(db)
    history_records = await asset_service.get_asset_history_records(
        asset_id,
        current_user_id=str(current_user.id),
    )
    return {"asset_id": asset_id, "history": history_records}


@router.get("/{asset_id}/management-history", summary="获取资产经营方变更历史")
async def get_asset_management_history(
    asset_id: str = Path(..., description="资产ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="asset",
            resource_id="{asset_id}",
            deny_as_not_found=True,
        )
    ),
) -> dict[str, Any]:
    """获取资产的经营管理方变更历史记录。"""
    asset_service = AsyncAssetService(db)
    records = await asset_service.get_asset_management_history(
        asset_id,
        current_user_id=str(current_user.id),
    )
    return {"asset_id": asset_id, "management_history": records}


@router.get("/{asset_id}/project-history", summary="获取资产项目关联历史")
async def get_asset_project_history(
    asset_id: str = Path(..., description="资产ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="asset",
            resource_id="{asset_id}",
            deny_as_not_found=True,
        )
    ),
) -> dict[str, Any]:
    """获取资产的项目关联历史（含当前有效和已终止绑定）。"""
    asset_service = AsyncAssetService(db)
    records = await asset_service.get_asset_project_history(
        asset_id,
        current_user_id=str(current_user.id),
    )
    return {"asset_id": asset_id, "project_history": records}
