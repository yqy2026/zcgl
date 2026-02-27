"""
租金合同CRUD操作模块
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import (
    BaseBusinessError,
    forbidden,
    internal_error,
    not_found,
)
from ....core.response_handler import APIResponse, PaginatedData, ResponseHandler
from ....database import get_async_db
from ....middleware.auth import (
    AuthzContext,
    get_current_active_user,
    require_authz,
)
from ....models.auth import User
from ....schemas.rent_contract import (
    RentContractCreate,
    RentContractResponse,
    RentContractUpdate,
)
from ....services.authz import authz_service
from ....services.rent_contract import rent_contract_service

router = APIRouter()
_CONTRACT_CREATE_UNSCOPED_PARTY_ID = "__unscoped__:rent_contract:create"
_CONTRACT_MUTATION_UNSCOPED_PARTY_ID = "__unscoped__:rent_contract:mutation"
_ADMIN_BYPASS_REASON_CODE = "rbac_admin_bypass"


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized == "":
        return None
    return normalized


def _resolve_authz_scope_party_id(
    *,
    authz_ctx: Any,
    field: str,
) -> str | None:
    if not isinstance(authz_ctx, AuthzContext):
        return None
    if _normalize_optional_str(authz_ctx.reason_code) == _ADMIN_BYPASS_REASON_CODE:
        return None
    return _normalize_optional_str(authz_ctx.resource_context.get(field))


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


async def _resolve_owner_party_scope_by_ownership_id(
    *,
    db: AsyncSession,
    ownership_id: str | None,
) -> str | None:
    normalized_ownership_id = _normalize_optional_str(ownership_id)
    if normalized_ownership_id is None:
        return None
    resolved_party_id = await rent_contract_service.resolve_owner_party_scope_by_ownership_id_async(
        db=db,
        ownership_id=normalized_ownership_id,
    )
    return _normalize_optional_str(resolved_party_id)


async def _infer_subject_manager_party_id(
    *,
    db: AsyncSession,
    user_id: str,
) -> str | None:
    try:
        subject_context = await authz_service.context_builder.build_subject_context(
            db,
            user_id=user_id,
        )
    except Exception:
        return None

    manager_party_ids = _normalize_identifier_sequence(
        getattr(subject_context, "manager_party_ids", []),
    )
    return manager_party_ids[0] if manager_party_ids else None


async def _require_contract_mutation_authz(
    *,
    action: str,
    contract_id: str,
    db: AsyncSession,
    current_user: User,
) -> AuthzContext:
    resolved_contract_id = _normalize_optional_str(contract_id)
    if resolved_contract_id is None:
        raise not_found("合同不存在", resource_type="contract", resource_id=contract_id)

    contract = await rent_contract_service.get_contract_with_details_async(
        db=db,
        contract_id=resolved_contract_id,
    )
    if not contract:
        raise not_found(
            "合同不存在",
            resource_type="contract",
            resource_id=resolved_contract_id,
        )

    resource_context: dict[str, Any] = {"contract_id": resolved_contract_id}
    owner_party_id = _normalize_optional_str(getattr(contract, "owner_party_id", None))
    if owner_party_id is not None:
        resource_context["owner_party_id"] = owner_party_id

    manager_party_id = _normalize_optional_str(
        getattr(contract, "manager_party_id", None)
    )
    if manager_party_id is not None:
        resource_context["manager_party_id"] = manager_party_id

    ownership_id = _normalize_optional_str(getattr(contract, "ownership_id", None))
    if ownership_id is not None:
        resource_context["ownership_id"] = ownership_id

    if owner_party_id is None and manager_party_id is None:
        resolved_owner_party_id = await _resolve_owner_party_scope_by_ownership_id(
            db=db,
            ownership_id=ownership_id,
        )
        if resolved_owner_party_id is not None:
            resource_context["owner_party_id"] = resolved_owner_party_id
            resource_context["party_id"] = resolved_owner_party_id

    has_party_scope = any(
        key in resource_context for key in ("owner_party_id", "manager_party_id", "party_id")
    )
    if not has_party_scope:
        resource_context["party_id"] = _CONTRACT_MUTATION_UNSCOPED_PARTY_ID

    try:
        decision = await authz_service.check_access(
            db,
            user_id=str(current_user.id),
            resource_type="rent_contract",
            action=action,
            resource_id=resolved_contract_id,
            resource=resource_context,
        )
    except Exception:
        raise forbidden("权限校验失败")

    if not decision.allowed:
        raise forbidden("权限不足")

    return AuthzContext(
        current_user=current_user,
        action=action,
        resource_type="rent_contract",
        resource_id=resolved_contract_id,
        resource_context=resource_context,
        allowed=True,
        reason_code=decision.reason_code,
    )


async def _require_contract_create_authz(
    contract_in: RentContractCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    owner_party_id = _normalize_optional_str(contract_in.owner_party_id)
    manager_party_id = _normalize_optional_str(contract_in.manager_party_id)
    ownership_id = _normalize_optional_str(contract_in.ownership_id)
    contract_in.owner_party_id = owner_party_id
    contract_in.manager_party_id = manager_party_id
    contract_in.ownership_id = ownership_id
    resource_context: dict[str, Any] = {}
    if owner_party_id is not None:
        resource_context["owner_party_id"] = owner_party_id
    if manager_party_id is not None:
        resource_context["manager_party_id"] = manager_party_id
    if manager_party_id is None:
        inferred_manager_party_id = _normalize_optional_str(
            await _infer_subject_manager_party_id(
                db=db,
                user_id=str(current_user.id),
            )
        )
        if inferred_manager_party_id is not None:
            manager_party_id = inferred_manager_party_id
            resource_context["manager_party_id"] = inferred_manager_party_id
    if ownership_id is not None:
        resource_context["ownership_id"] = ownership_id
    resolved_owner_party_id: str | None = None
    if owner_party_id is None and ownership_id is not None:
        resolved_owner_party_id = await _resolve_owner_party_scope_by_ownership_id(
            db=db,
            ownership_id=ownership_id,
        )
        if resolved_owner_party_id is not None:
            contract_in.owner_party_id = resolved_owner_party_id
            resource_context["owner_party_id"] = resolved_owner_party_id
    resolved_party_id = manager_party_id or owner_party_id or resolved_owner_party_id
    if resolved_party_id is not None:
        resource_context["party_id"] = resolved_party_id
    elif ownership_id is None:
        resource_context["party_id"] = _CONTRACT_CREATE_UNSCOPED_PARTY_ID

    try:
        decision = await authz_service.check_access(
            db,
            user_id=str(current_user.id),
            resource_type="rent_contract",
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
        resource_type="rent_contract",
        resource_id=None,
        resource_context=resource_context,
        allowed=True,
        reason_code=decision.reason_code,
    )


async def _require_contract_update_authz(
    contract_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    return await _require_contract_mutation_authz(
        action="update",
        contract_id=contract_id,
        db=db,
        current_user=current_user,
    )


async def _require_contract_delete_authz(
    contract_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    return await _require_contract_mutation_authz(
        action="delete",
        contract_id=contract_id,
        db=db,
        current_user=current_user,
    )


@router.post("/contracts", response_model=RentContractResponse, summary="创建租金合同")
async def create_contract(
    *,
    db: AsyncSession = Depends(get_async_db),
    contract_in: RentContractCreate,
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_contract_create_authz),
) -> Any:
    """
    创建新的租金合同，包含租金条款信息 - V2 支持多资产
    """
    try:
        if isinstance(_authz_ctx, AuthzContext):
            resolved_owner_party_id = _normalize_optional_str(
                _authz_ctx.resource_context.get("owner_party_id")
            )
            if (
                _normalize_optional_str(contract_in.owner_party_id) is None
                and resolved_owner_party_id is not None
            ):
                contract_in.owner_party_id = resolved_owner_party_id

        if contract_in.asset_ids:
            assets = await rent_contract_service.get_assets_by_ids_async(
                db=db,
                asset_ids=contract_in.asset_ids,
            )
            existing_asset_ids = {
                str(asset.id) for asset in assets if getattr(asset, "id", None) is not None
            }
            missing_asset_id = next(
                (asset_id for asset_id in contract_in.asset_ids if asset_id not in existing_asset_ids),
                None,
            )
            if missing_asset_id is not None:
                raise not_found(
                    f"关联的资产不存在: {missing_asset_id}",
                    resource_type="asset",
                    resource_id=missing_asset_id,
                )

        if contract_in.owner_party_id:
            owner_party = await rent_contract_service.get_owner_party_by_id_async(
                db=db,
                owner_party_id=contract_in.owner_party_id,
            )
            if not owner_party:
                raise not_found(
                    "关联的产权主体不存在",
                    resource_type="party",
                    resource_id=str(contract_in.owner_party_id),
                )
        if contract_in.ownership_id:  # DEPRECATED compatibility path
            # DEPRECATED: 兼容旧 ownership_id 校验链路。
            ownership_obj = await rent_contract_service.get_ownership_by_id_async(
                db=db,
                ownership_id=contract_in.ownership_id,  # DEPRECATED alias
            )
            if not ownership_obj:
                raise not_found(
                    "关联的权属方不存在",
                    resource_type="ownership",
                    resource_id=str(contract_in.ownership_id),  # DEPRECATED alias
                )

        contract = await rent_contract_service.create_contract_async(
            db=db, obj_in=contract_in
        )
        return contract
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"创建合同失败: {str(e)}")


@router.get(
    "/contracts/{contract_id}",
    response_model=RentContractResponse,
    summary="获取租金合同详情",
)
async def get_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="rent_contract",
            resource_id="{contract_id}",
            deny_as_not_found=True,
        )
    ),
) -> Any:
    """
    获取租金合同详情，包含租金条款信息
    """
    contract = await rent_contract_service.get_contract_with_details_async(
        db=db,
        contract_id=contract_id,
    )
    if not contract:
        raise not_found("合同不存在", resource_type="contract", resource_id=contract_id)
    return contract


@router.get(
    "/contracts",
    response_model=APIResponse[PaginatedData[RentContractResponse]],
    summary="获取租金合同列表",
)
async def get_contracts(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="rent_contract",
        )
    ),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    contract_number: str | None = Query(None, description="合同编号筛选"),
    tenant_name: str | None = Query(None, description="承租方名称筛选"),
    asset_id: str | None = Query(None, description="资产ID筛选"),
    owner_party_id: str | None = Query(None, description="产权方主体ID筛选"),
    ownership_id: str | None = Query(None, description="权属方ID筛选（DEPRECATED）"),
    contract_status: str | None = Query(None, description="合同状态筛选"),
    start_date: date | None = Query(None, description="开始日期筛选"),
    end_date: date | None = Query(None, description="结束日期筛选"),
) -> JSONResponse:
    """
    获取租金合同列表，支持分页和筛选
    """
    owner_party_id_value = owner_party_id if isinstance(owner_party_id, str) else None
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

    if owner_party_id_value is not None:
        if scoped_owner_party_ids and owner_party_id_value not in scoped_owner_party_ids:
            raise forbidden("权限不足")
        if not scoped_owner_party_ids and scoped_manager_party_ids:
            # Manager-only scoped callers cannot inject owner filter because the
            # current query layer combines owner/manager scope with OR.
            raise forbidden("权限不足")

    effective_owner_party_ids: list[str] | None = None
    if owner_party_id_value is not None:
        effective_owner_party_ids = [owner_party_id_value]
    elif scoped_owner_party_ids:
        effective_owner_party_ids = scoped_owner_party_ids

    effective_manager_party_ids: list[str] | None = None
    if owner_party_id_value is None and scoped_manager_party_ids:
        effective_manager_party_ids = scoped_manager_party_ids

    effective_owner_party_id = (
        effective_owner_party_ids[0] if effective_owner_party_ids else None
    )
    effective_manager_party_id = (
        effective_manager_party_ids[0] if effective_manager_party_ids else None
    )
    ownership_id_value = ownership_id if isinstance(ownership_id, str) else None  # DEPRECATED alias

    skip = (page - 1) * page_size
    contracts, total = await rent_contract_service.get_contract_page_async(
        db=db,
        skip=skip,
        limit=page_size,
        contract_number=contract_number,
        tenant_name=tenant_name,
        asset_id=asset_id,
        owner_party_id=effective_owner_party_id,
        manager_party_id=effective_manager_party_id,
        owner_party_ids=effective_owner_party_ids,
        manager_party_ids=effective_manager_party_ids,
        ownership_id=ownership_id_value,  # DEPRECATED alias
        contract_status=contract_status,
        start_date=start_date,
        end_date=end_date,
    )

    contract_responses = [RentContractResponse.model_validate(c) for c in contracts]

    return ResponseHandler.paginated(
        data=contract_responses,
        page=page,
        page_size=page_size,
        total=total,
        message="获取租金合同列表成功",
    )


@router.put(
    "/contracts/{contract_id}",
    response_model=RentContractResponse,
    summary="更新租金合同",
)
async def update_contract(
    contract_id: str,
    *,
    db: AsyncSession = Depends(get_async_db),
    contract_in: RentContractUpdate,
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_contract_update_authz),
) -> Any:
    """
    更新租金合同信息
    """
    try:

        contract = await rent_contract_service.get_contract_with_details_async(
            db=db,
            contract_id=contract_id,
        )
        if not contract:
            raise not_found(
                "合同不存在", resource_type="contract", resource_id=contract_id
            )
        updated_contract = await rent_contract_service.update_contract_async(
            db=db, db_obj=contract, obj_in=contract_in
        )
        if not updated_contract:
            raise not_found(
                "合同不存在", resource_type="contract", resource_id=contract_id
            )
        return updated_contract
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"更新合同失败: {str(e)}")


@router.delete("/contracts/{contract_id}", summary="删除租金合同")
async def delete_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_contract_delete_authz),
) -> Any:
    """
    删除租金合同（同时删除相关的租金条款和台账记录）。

    权限要求由 scoped contract ABAC 依赖统一处理。
    """
    contract = await rent_contract_service.get_contract_with_details_async(
        db=db,
        contract_id=contract_id,
    )
    if not contract:
        raise not_found("合同不存在", resource_type="contract", resource_id=contract_id)
    await rent_contract_service.delete_contract_by_id_async(
        db=db,
        contract_id=contract_id,
    )
    return {"message": "合同删除成功"}


@router.get(
    "/assets/{asset_id}/contracts",
    response_model=list[RentContractResponse],
    summary="获取资产合同",
)
async def get_asset_contracts(
    asset_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _asset_authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="asset",
            resource_id="{asset_id}",
            deny_as_not_found=True,
        )
    ),
    authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="rent_contract",
        )
    ),
) -> Any:
    """
    获取指定资产的所有合同
    """
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
    scoped_owner_party_id = scoped_owner_party_ids[0] if scoped_owner_party_ids else None
    scoped_manager_party_id = (
        scoped_manager_party_ids[0] if scoped_manager_party_ids else None
    )
    contracts = await rent_contract_service.get_asset_contracts_async(
        db=db,
        asset_id=asset_id,
        owner_party_id=scoped_owner_party_id,
        manager_party_id=scoped_manager_party_id,
        owner_party_ids=scoped_owner_party_ids or None,
        manager_party_ids=scoped_manager_party_ids or None,
        limit=1000,
    )
    return contracts
