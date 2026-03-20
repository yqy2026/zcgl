"""
联系人管理 API 端点
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.params import Depends as DependsParam
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
from ....middleware.auth import AuthzContext, get_current_active_user, require_authz
from ....models.auth import User
from ....schemas.contact import (
    ContactCreate,
    ContactResponse,
    ContactUpdate,
    PrimaryContactResponse,
)
from ....services.authz import authz_service
from ....services.contact import ContactService, get_contact_service

router = APIRouter()


async def _resolve_contact_scope_context_by_entity(
    *,
    db: AsyncSession,
    entity_type: str,
    entity_id: str,
) -> dict[str, Any]:
    checker = require_authz(action="read", resource_type="contact")
    return await checker._load_contact_parent_scope_context(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
    )


async def _resolve_contact_scope_context_by_id(
    *,
    db: AsyncSession,
    contact_id: str,
) -> dict[str, Any]:
    checker = require_authz(action="read", resource_type="contact")
    return await checker._load_contact_scope_context(
        db=db,
        contact_id=contact_id,
        request_context={},
    )


async def _check_contact_access(
    *,
    db: AsyncSession,
    current_user: User,
    action: str,
    resource_id: str | None,
    resource_context: dict[str, Any],
    deny_as_not_found: bool = False,
) -> AuthzContext:
    decision = await authz_service.check_access(
        db,
        user_id=str(current_user.id),
        resource_type="contact",
        action=action,
        resource_id=resource_id,
        resource=resource_context,
    )
    if not decision.allowed:
        if deny_as_not_found:
            raise not_found(resource_type="contact", resource_id=resource_id)
        raise forbidden("权限不足")

    return AuthzContext(
        current_user=current_user,
        action=action,
        resource_type="contact",
        resource_id=resource_id,
        resource_context=resource_context,
        allowed=True,
        reason_code=decision.reason_code,
    )


async def _require_contact_create_authz(
    contact_in: ContactCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    resource_context = await _resolve_contact_scope_context_by_entity(
        db=db,
        entity_type=str(contact_in.entity_type),
        entity_id=str(contact_in.entity_id),
    )
    return await _check_contact_access(
        db=db,
        current_user=current_user,
        action="create",
        resource_id=str(contact_in.entity_id),
        resource_context=resource_context,
    )


async def _require_contact_entity_read_authz(
    entity_type: str,
    entity_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    resource_context = await _resolve_contact_scope_context_by_entity(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    return await _check_contact_access(
        db=db,
        current_user=current_user,
        action="read",
        resource_id=entity_id,
        resource_context=resource_context,
        deny_as_not_found=True,
    )


async def _require_contact_entity_create_authz(
    entity_type: str,
    entity_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    resource_context = await _resolve_contact_scope_context_by_entity(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    return await _check_contact_access(
        db=db,
        current_user=current_user,
        action="create",
        resource_id=entity_id,
        resource_context=resource_context,
    )


async def _require_contact_detail_authz(
    contact_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    resource_context = await _resolve_contact_scope_context_by_id(
        db=db,
        contact_id=contact_id,
    )
    return await _check_contact_access(
        db=db,
        current_user=current_user,
        action="read",
        resource_id=contact_id,
        resource_context=resource_context,
        deny_as_not_found=True,
    )


async def _require_contact_update_authz(
    contact_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    resource_context = await _resolve_contact_scope_context_by_id(
        db=db,
        contact_id=contact_id,
    )
    return await _check_contact_access(
        db=db,
        current_user=current_user,
        action="update",
        resource_id=contact_id,
        resource_context=resource_context,
    )


async def _require_contact_delete_authz(
    contact_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> AuthzContext:
    resource_context = await _resolve_contact_scope_context_by_id(
        db=db,
        contact_id=contact_id,
    )
    return await _check_contact_access(
        db=db,
        current_user=current_user,
        action="delete",
        resource_id=contact_id,
        resource_context=resource_context,
    )


def _resolve_service(service: ContactService | Any) -> ContactService | Any:
    if isinstance(service, DependsParam):
        return get_contact_service()
    return service


@router.post("/", response_model=ContactResponse, summary="创建联系人")
async def create_contact(
    *,
    db: AsyncSession = Depends(get_async_db),
    contact_in: ContactCreate,
    current_user: User = Depends(get_current_active_user),
    service: ContactService = Depends(get_contact_service),
) -> Any:
    """
    创建新的联系人

    - 如果 is_primary=True，会自动取消该实体的其他主要联系人
    - 支持权属方(ownership)、项目(project)、租户(tenant)等实体类型
    """

    contact_data = contact_in.model_dump()
    contact_data["created_by"] = current_user.username
    contact_data["updated_by"] = current_user.username

    try:
        await _require_contact_create_authz(
            contact_in=contact_in,
            current_user=current_user,
            db=db,
        )
        resolved_service = _resolve_service(service)
        contact = await resolved_service.create_contact(
            db=db,
            contact_data=contact_data,
        )
        return ContactResponse.model_validate(contact)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"创建联系人失败: {str(e)}")


@router.get("/{contact_id}", response_model=ContactResponse, summary="获取联系人详情")
async def get_contact(
    contact_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_contact_detail_authz),
    service: ContactService = Depends(get_contact_service),
) -> Any:
    """获取联系人详情"""
    _ = current_user
    resolved_service = _resolve_service(service)
    contact = await resolved_service.get_contact(db=db, contact_id=contact_id)
    if not contact:
        raise not_found("联系人不存在", resource_type="contact", resource_id=contact_id)
    return ContactResponse.model_validate(contact)


@router.get(
    "/entity/{entity_type}/{entity_id}",
    response_model=APIResponse[PaginatedData[ContactResponse]],
    summary="获取实体的所有联系人",
)
async def get_entity_contacts(
    entity_type: str,
    entity_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    _authz_ctx: AuthzContext = Depends(_require_contact_entity_read_authz),
    service: ContactService = Depends(get_contact_service),
) -> JSONResponse:
    """
    获取指定实体的所有联系人

    - entity_type: 实体类型 (ownership/project/tenant)
    - entity_id: 实体ID
    - 返回结果按主要联系人优先，然后按创建时间倒序
    """

    _ = current_user
    skip = (page - 1) * page_size
    resolved_service = _resolve_service(service)
    contacts, total = await resolved_service.get_entity_contacts(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
        skip=skip,
        limit=page_size,
    )

    items = [ContactResponse.model_validate(contact) for contact in contacts]
    return ResponseHandler.paginated(
        data=items,
        page=page,
        page_size=page_size,
        total=total,
        message="获取联系人列表成功",
    )


@router.get(
    "/entity/{entity_type}/{entity_id}/primary",
    response_model=PrimaryContactResponse,
    summary="获取实体的主要联系人",
)
async def get_primary_contact(
    entity_type: str,
    entity_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_contact_entity_read_authz),
    service: ContactService = Depends(get_contact_service),
) -> Any:
    """
    获取指定实体的主要联系人

    - entity_type: 实体类型 (ownership/project/tenant)
    - entity_id: 实体ID
    - 如果没有主要联系人，返回404
    """
    _ = current_user
    resolved_service = _resolve_service(service)
    contact = await resolved_service.get_primary_contact(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    if not contact:
        raise not_found("主要联系人不存在", resource_type="primary_contact")

    return PrimaryContactResponse.model_validate(contact)


@router.put("/{contact_id}", response_model=ContactResponse, summary="更新联系人")
async def update_contact(
    contact_id: str,
    *,
    db: AsyncSession = Depends(get_async_db),
    contact_in: ContactUpdate,
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_contact_update_authz),
    service: ContactService = Depends(get_contact_service),
) -> Any:
    """更新联系人信息"""

    update_data = contact_in.model_dump(exclude_unset=True)
    update_data["updated_by"] = current_user.username

    try:
        resolved_service = _resolve_service(service)
        updated_contact = await resolved_service.update_contact(
            db=db,
            contact_id=contact_id,
            update_data=update_data,
        )
        if not updated_contact:
            raise not_found(
                "联系人不存在",
                resource_type="contact",
                resource_id=contact_id,
            )
        return ContactResponse.model_validate(updated_contact)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"更新联系人失败: {str(e)}")


@router.delete("/{contact_id}", response_model=ContactResponse, summary="删除联系人")
async def delete_contact(
    contact_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_contact_delete_authz),
    service: ContactService = Depends(get_contact_service),
) -> Any:
    """
    删除联系人（软删除）

    - 设置 is_active=False
    - 数据保留在数据库中
    """

    _ = current_user
    resolved_service = _resolve_service(service)
    contact = await resolved_service.delete_contact(db=db, contact_id=contact_id)
    if not contact:
        raise not_found("联系人不存在", resource_type="contact", resource_id=contact_id)
    return ContactResponse.model_validate(contact)


@router.post(
    "/batch/{entity_type}/{entity_id}",
    response_model=list[ContactResponse],
    summary="批量创建联系人",
)
async def create_contacts_batch(
    entity_type: str,
    entity_id: str,
    *,
    db: AsyncSession = Depends(get_async_db),
    contacts_in: list[ContactCreate],
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(_require_contact_entity_create_authz),
    service: ContactService = Depends(get_contact_service),
) -> Any:
    """
    批量创建联系人

    - 支持一次创建多个联系人
    - 自动设置创建人信息
    """

    contacts_data = []
    for contact_in in contacts_in:
        contact_data = contact_in.model_dump()
        contact_data["entity_type"] = entity_type
        contact_data["entity_id"] = entity_id
        contact_data["created_by"] = current_user.username
        contact_data["updated_by"] = current_user.username
        contacts_data.append(contact_data)

    try:
        resolved_service = _resolve_service(service)
        contacts = await resolved_service.create_contacts_batch(
            db=db,
            contacts_data=contacts_data,
        )
        return [ContactResponse.model_validate(contact) for contact in contacts]
    except Exception as e:
        raise internal_error(f"批量创建失败: {str(e)}")
