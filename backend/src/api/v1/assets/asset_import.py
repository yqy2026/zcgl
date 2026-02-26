"""资产导入API路由模块。"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import forbidden, internal_error
from ....database import get_async_db
from ....middleware.auth import AuthzContext, get_current_active_user
from ....models.auth import User
from ....schemas.asset import AssetImportRequest, AssetImportResponse
from ....services.asset.asset_service import AsyncAssetService
from ....services.asset.import_service import AsyncAssetImportService
from ....services.authz import authz_service

# 创建导入路由器
router = APIRouter()
_ASSET_IMPORT_UNSCOPED_PARTY_ID = "__unscoped__:asset:import"


def _normalize_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized == "":
        return None
    return normalized


async def _resolve_owner_party_scope_by_ownership_id(
    *,
    db: AsyncSession,
    ownership_id: str | None,
) -> str | None:
    normalized_ownership_id = _normalize_optional_str(ownership_id)
    if normalized_ownership_id is None:
        return None
    resolved_party_id = await AsyncAssetService(
        db
    ).resolve_owner_party_scope_by_ownership_id_async(
        ownership_id=normalized_ownership_id
    )
    return _normalize_optional_str(resolved_party_id)


async def _resolve_organization_party_scope_by_organization_id(
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


async def _build_asset_import_resource_context(
    *,
    db: AsyncSession,
    record: dict[str, Any],
    ownership_scope_cache: dict[str, str | None],
    organization_scope_cache: dict[str, str | None],
) -> dict[str, Any]:
    owner_party_id = _normalize_optional_str(record.get("owner_party_id"))
    manager_party_id = _normalize_optional_str(record.get("manager_party_id"))
    ownership_id = _normalize_optional_str(record.get("ownership_id"))
    organization_id = _normalize_optional_str(record.get("organization_id"))

    resource_context: dict[str, Any] = {}
    if owner_party_id is not None:
        resource_context["owner_party_id"] = owner_party_id
        resource_context["party_id"] = owner_party_id
    if manager_party_id is not None:
        resource_context["manager_party_id"] = manager_party_id
        if "party_id" not in resource_context:
            resource_context["party_id"] = manager_party_id
    if ownership_id is not None:
        resource_context["ownership_id"] = ownership_id
    if organization_id is not None:
        resource_context["organization_id"] = organization_id

    if owner_party_id is None and ownership_id is not None:
        if ownership_id not in ownership_scope_cache:
            ownership_scope_cache[ownership_id] = (
                await _resolve_owner_party_scope_by_ownership_id(
                    db=db,
                    ownership_id=ownership_id,
                )
            )
        resolved_owner_party_id = ownership_scope_cache.get(ownership_id)
        if resolved_owner_party_id is not None:
            resource_context["owner_party_id"] = resolved_owner_party_id
            if "party_id" not in resource_context:
                resource_context["party_id"] = resolved_owner_party_id

    if "party_id" not in resource_context and organization_id is not None:
        if organization_id not in organization_scope_cache:
            organization_scope_cache[organization_id] = (
                await _resolve_organization_party_scope_by_organization_id(
                    db=db,
                    organization_id=organization_id,
                )
            )
        resolved_organization_party_id = organization_scope_cache.get(organization_id)
        resource_context["party_id"] = (
            resolved_organization_party_id
            if resolved_organization_party_id is not None
            else organization_id
        )

    if "party_id" not in resource_context:
        # Fail-closed sentinel: block scoped packages when import rows carry no resolvable scope keys.
        resource_context["party_id"] = _ASSET_IMPORT_UNSCOPED_PARTY_ID

    return resource_context


async def _require_asset_import_create_authz(
    request: AssetImportRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    unique_resource_contexts: list[dict[str, Any]] = []
    seen_context_keys: set[tuple[tuple[str, str], ...]] = set()
    ownership_scope_cache: dict[str, str | None] = {}
    organization_scope_cache: dict[str, str | None] = {}

    for item in request.data:
        if not isinstance(item, dict):
            continue
        resource_context = await _build_asset_import_resource_context(
            db=db,
            record=item,
            ownership_scope_cache=ownership_scope_cache,
            organization_scope_cache=organization_scope_cache,
        )
        normalized_key = tuple(
            sorted(
                (str(key), str(value))
                for key, value in resource_context.items()
            )
        )
        if normalized_key in seen_context_keys:
            continue
        seen_context_keys.add(normalized_key)
        unique_resource_contexts.append(resource_context)

    if len(unique_resource_contexts) == 0:
        unique_resource_contexts.append({"party_id": _ASSET_IMPORT_UNSCOPED_PARTY_ID})

    for resource_context in unique_resource_contexts:
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
        resource_context={"checked_scope_count": len(unique_resource_contexts)},
        allowed=True,
        reason_code="allow",
    )


@router.post("/import", response_model=AssetImportResponse, summary="导入资产数据")
async def import_assets(
    request: AssetImportRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_asset_import_create_authz),
) -> AssetImportResponse:
    """
    批量导入资产数据

    - **data**: 待导入的资产数据列表
    - **import_mode**: 导入模式（create/merge/update）
    - **skip_errors**: 是否跳过错误数据
    - **dry_run**: 是否仅验证不实际导入
    """

    try:
        service = AsyncAssetImportService(db)
        return await service.import_assets(request=request, current_user=current_user)
    except Exception as e:
        raise internal_error(f"资产导入失败: {str(e)}")
