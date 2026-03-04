"""
权属方相关API端点
"""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import (
    BaseBusinessError,
    forbidden,
    internal_error,
    not_found,
)
from ....core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ....database import get_async_db
from ....middleware.auth import AuthzContext, get_current_active_user, require_authz
from ....models.auth import User
from ....models.ownership import Ownership
from ....schemas.ownership import (
    OwnershipCreate,
    OwnershipDeleteResponse,
    OwnershipResponse,
    OwnershipSearchRequest,
    OwnershipStatisticsResponse,
    OwnershipUpdate,
)
from ....services.authz import authz_service
from ....services.ownership import ownership_service

router = APIRouter()
_OWNERSHIP_CREATE_UNSCOPED_PARTY_ID = "__unscoped__:ownership:create"


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized == "":
        return None
    return normalized


def _resolve_current_user_organization_id(current_user: User) -> str | None:
    return _normalize_optional_str(getattr(current_user, "default_organization_id", None))


async def _resolve_organization_party_id(
    *,
    db: AsyncSession,
    organization_id: str | None,
) -> str | None:
    normalized_organization_id = _normalize_optional_str(organization_id)
    if normalized_organization_id is None:
        return None

    from ....models.party import Party, PartyType

    stmt = (
        select(Party.id.label("party_id"))
        .where(
            Party.party_type == PartyType.ORGANIZATION.value,
            or_(
                Party.id == normalized_organization_id,
                Party.external_ref == normalized_organization_id,
            ),
        )
        .order_by(Party.id)
        .limit(1)
    )
    row = (await db.execute(stmt)).mappings().one_or_none()
    return _normalize_optional_str(row.get("party_id") if row is not None else None)


async def _require_ownership_create_authz(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    resource_context: dict[str, Any] = {}
    organization_id = _resolve_current_user_organization_id(current_user)
    if organization_id is not None:
        resource_context["organization_id"] = organization_id
        scoped_party_id = await _resolve_organization_party_id(
            db=db,
            organization_id=organization_id,
        )
        resolved_party_id = (
            scoped_party_id if scoped_party_id is not None else organization_id
        )
        resource_context["party_id"] = resolved_party_id
        resource_context["owner_party_id"] = resolved_party_id
        resource_context["manager_party_id"] = resolved_party_id
    else:
        resource_context["party_id"] = _OWNERSHIP_CREATE_UNSCOPED_PARTY_ID
        resource_context["owner_party_id"] = _OWNERSHIP_CREATE_UNSCOPED_PARTY_ID
        resource_context["manager_party_id"] = _OWNERSHIP_CREATE_UNSCOPED_PARTY_ID

    try:
        decision = await authz_service.check_access(
            db,
            user_id=str(current_user.id),
            resource_type="ownership",
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
        resource_type="ownership",
        resource_id=None,
        resource_context=resource_context,
        allowed=True,
        reason_code=decision.reason_code,
    )


@router.get("/dropdown-options", summary="获取权属方选项列表")
async def get_ownership_dropdown_options(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    is_active: bool | None = Query(True, description="是否启用"),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="ownership",
            )
        ),
    ] = None,
) -> list[OwnershipResponse]:
    """获取权属方选项列表（用于下拉选择等）- V2修复is_active过滤"""
    try:
        # 调用服务层获取下拉选项
        dropdown_data = await ownership_service.get_ownership_dropdown_options(
            db, is_active=is_active
        )

        # 转换为响应格式
        responses: list[OwnershipResponse] = []
        for item_data in dropdown_data:
            # 创建临时Ownership对象以便model_validate使用
            temp_ownership = Ownership(
                **{
                    k: v
                    for k, v in item_data.items()
                    if k not in ["asset_count", "project_count"]
                }
            )
            response = OwnershipResponse.model_validate(temp_ownership)
            # 设置额外的计数字段
            response.asset_count = item_data["asset_count"]
            response.project_count = item_data["project_count"]
            responses.append(response)
        return responses
    except Exception as e:
        raise internal_error(f"获取权属方选项失败: {str(e)}")


@router.post("", response_model=OwnershipResponse, summary="创建权属方")
@router.post("/", response_model=OwnershipResponse, summary="创建权属方")
async def create_ownership(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    ownership_in: OwnershipCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz_ctx: AuthzContext = Depends(_require_ownership_create_authz),
) -> OwnershipResponse:
    """创建新权属方"""
    try:
        db_ownership = await ownership_service.create_ownership(db, obj_in=ownership_in)
        return OwnershipResponse.model_validate(db_ownership)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"创建权属方失败: {str(e)}")


@router.put("/{ownership_id}", response_model=OwnershipResponse, summary="更新权属方")
async def update_ownership(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    ownership_id: str,
    ownership_in: OwnershipUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="ownership",
                resource_id="{ownership_id}",
            )
        ),
    ] = None,
) -> OwnershipResponse:
    """更新权属方信息"""
    try:
        updated_ownership = await ownership_service.update_ownership_by_id(
            db,
            ownership_id=ownership_id,
            obj_in=ownership_in,
        )
        return OwnershipResponse.model_validate(updated_ownership)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"更新权属方失败: {str(e)}")


@router.put("/{ownership_id}/projects", summary="更新权属方关联项目")
async def update_ownership_projects(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    ownership_id: str,
    project_ids: list[str] = Body(..., description="关联项目ID列表"),
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="ownership",
                resource_id="{ownership_id}",
            )
        ),
    ] = None,
) -> OwnershipResponse:
    """更新权属方的关联项目"""
    db_ownership = await ownership_service.get_ownership(db, ownership_id=ownership_id)
    if not db_ownership:
        raise not_found(
            "权属方不存在", resource_type="ownership", resource_id=ownership_id
        )

    try:
        # 更新关联项目
        await ownership_service.update_related_projects(
            db, ownership_id=ownership_id, project_ids=project_ids
        )

        # 返回更新后的权属方信息
        updated_ownership = await ownership_service.get_ownership(
            db, ownership_id=ownership_id
        )
        response = OwnershipResponse.model_validate(updated_ownership)

        # 获取实际的项目计数
        actual_project_count = await ownership_service.get_project_count(
            db, ownership_id
        )
        response.project_count = actual_project_count
        return response
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"更新关联项目失败: {str(e)}")


@router.delete(
    "/{ownership_id}", response_model=OwnershipDeleteResponse, summary="删除权属方"
)
async def delete_ownership(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    ownership_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="delete",
                resource_type="ownership",
                resource_id="{ownership_id}",
            )
        ),
    ] = None,
) -> OwnershipDeleteResponse:
    """删除权属方"""
    try:
        # 先检查关联资产数量
        asset_count = await ownership_service.get_asset_count(db, ownership_id)

        deleted_ownership = await ownership_service.delete_ownership(
            db, id=ownership_id
        )
        return OwnershipDeleteResponse(
            message="权属方删除成功",
            id=deleted_ownership.id,
            affected_assets=asset_count,
        )
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"删除权属方失败: {str(e)}")


@router.get(
    "",
    response_model=APIResponse[PaginatedData[OwnershipResponse]],
    summary="获取权属方列表",
)
@router.get(
    "/",
    response_model=APIResponse[PaginatedData[OwnershipResponse]],
    summary="获取权属方列表",
)
async def get_ownerships(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_async_db)],
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    keyword: str | None = Query(None, description="搜索关键词"),
    is_active: bool | None = Query(None, description="是否启用"),
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="ownership",
            )
        ),
    ] = None,
) -> Any:
    """获取权属方列表"""
    search_params = OwnershipSearchRequest(
        page=page, page_size=page_size, keyword=keyword, is_active=is_active
    )

    result = await ownership_service.search_ownerships(db, search_params=search_params)

    # 转换为响应格式，并添加关联计数
    items: list[OwnershipResponse] = []
    for item in result["items"]:
        response = OwnershipResponse.model_validate(item)
        # 获取关联资产数量
        response.asset_count = await ownership_service.get_asset_count(db, item.id)
        # 获取关联项目数量
        response.project_count = await ownership_service.get_project_count(db, item.id)
        items.append(response)

    return ResponseHandler.paginated(
        data=items,
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
        message="获取权属方列表成功",
    )


@router.post(
    "/search",
    response_model=APIResponse[PaginatedData[OwnershipResponse]],
    summary="搜索权属方",
)
async def search_ownerships(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    search_params: OwnershipSearchRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="ownership",
            )
        ),
    ] = None,
) -> Any:
    """搜索权属方"""
    result = await ownership_service.search_ownerships(db, search_params=search_params)

    # 转换为响应格式，并添加关联计数
    items: list[OwnershipResponse] = []
    for item in result["items"]:
        response = OwnershipResponse.model_validate(item)
        # 获取关联资产数量
        response.asset_count = await ownership_service.get_asset_count(db, item.id)
        # 获取关联项目数量
        response.project_count = await ownership_service.get_project_count(db, item.id)
        items.append(response)

    return ResponseHandler.paginated(
        data=items,
        page=result["page"],
        page_size=result["page_size"],
        total=result["total"],
        message="搜索权属方成功",
    )


@router.get(
    "/statistics/summary",
    response_model=OwnershipStatisticsResponse,
    summary="获取权属方统计",
)
async def get_ownership_statistics(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="ownership",
            )
        ),
    ] = None,
) -> OwnershipStatisticsResponse:
    """获取权属方统计信息"""
    stats = await ownership_service.get_statistics(db)

    # 转换最近创建的权属方
    recent_created = [
        OwnershipResponse.model_validate(item) for item in stats["recent_created"]
    ]

    return OwnershipStatisticsResponse(
        total_count=stats["total_count"],
        active_count=stats["active_count"],
        inactive_count=stats["inactive_count"],
        recent_created=recent_created,
    )


@router.post(
    "/{ownership_id}/toggle-status",
    response_model=OwnershipResponse,
    summary="切换权属方状态",
)
async def toggle_ownership_status(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    ownership_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="update",
                resource_type="ownership",
                resource_id="{ownership_id}",
            )
        ),
    ] = None,
) -> OwnershipResponse:
    """切换权属方启用/禁用状态"""
    try:
        db_ownership = await ownership_service.toggle_status(db, id=ownership_id)
        return OwnershipResponse.model_validate(db_ownership)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"切换状态失败: {str(e)}")


@router.get(
    "/{ownership_id}/financial-summary",
    summary="获取权属方收支汇总",
)
async def get_ownership_financial_summary(
    ownership_id: str,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    _authz_ctx: Annotated[
        AuthzContext | None,
        Depends(
            require_authz(
                action="read",
                resource_type="ownership",
                resource_id="{ownership_id}",
                deny_as_not_found=True,
            )
        ),
    ] = None,
) -> dict[str, Any]:
    """
    获取权属方的收支汇总信息

    包括:
    - 总收入 (来自租金台账)
    - 总支出 (如果有的话)
    - 应收未收金额
    - 已收金额
    """

    from ....services.asset.ownership_financial_service import (
        OwnershipFinancialService,
    )

    # 验证权属方是否存在
    ownership_obj = await ownership_service.get_ownership(db, ownership_id=ownership_id)
    if not ownership_obj:
        raise not_found(
            "权属方不存在", resource_type="ownership", resource_id=ownership_id
        )

    # 使用 Service 层计算财务汇总
    service = OwnershipFinancialService()
    result = await service.get_financial_summary(
        db,
        ownership_id=ownership_id,
        ownership_name=ownership_obj.name,
    )

    return result.to_dict()
