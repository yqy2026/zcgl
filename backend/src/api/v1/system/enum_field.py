"""
枚举字段管理API路由
"""

from typing import Any

from fastapi import APIRouter, Depends, Path, Query
from fastapi.params import Depends as DependsParam
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from ....database import get_async_db
from ....middleware.auth import AuthzContext, get_current_active_user, require_authz
from ....schemas.enum_field import (
    EnumFieldBatchCreate,
    EnumFieldHistoryResponse,
    EnumFieldStatistics,
    EnumFieldTree,
    EnumFieldTypeCreate,
    EnumFieldTypeResponse,
    EnumFieldTypeUpdate,
    EnumFieldUsageCreate,
    EnumFieldUsageResponse,
    EnumFieldUsageUpdate,
    EnumFieldValueCreate,
    EnumFieldValueResponse,
    EnumFieldValueUpdate,
)
from ....security.route_guards import debug_only, require_localhost
from ....services.enum_field.service import EnumFieldService, get_enum_field_service

router = APIRouter(
    prefix="/enum-fields",
    tags=["枚举字段管理"],
    dependencies=[Depends(get_current_active_user)],
)
_ENUM_FIELD_TYPE_CREATE_UNSCOPED_PARTY_ID = "__unscoped__:enum_field_type:create"
_ENUM_FIELD_TYPE_CREATE_RESOURCE_CONTEXT: dict[str, str] = {
    "party_id": _ENUM_FIELD_TYPE_CREATE_UNSCOPED_PARTY_ID,
    "owner_party_id": _ENUM_FIELD_TYPE_CREATE_UNSCOPED_PARTY_ID,
    "manager_party_id": _ENUM_FIELD_TYPE_CREATE_UNSCOPED_PARTY_ID,
}
_ENUM_FIELD_USAGE_CREATE_UNSCOPED_PARTY_ID = "__unscoped__:enum_field_usage:create"
_ENUM_FIELD_USAGE_CREATE_RESOURCE_CONTEXT: dict[str, str] = {
    "party_id": _ENUM_FIELD_USAGE_CREATE_UNSCOPED_PARTY_ID,
    "owner_party_id": _ENUM_FIELD_USAGE_CREATE_UNSCOPED_PARTY_ID,
    "manager_party_id": _ENUM_FIELD_USAGE_CREATE_UNSCOPED_PARTY_ID,
}


def _strip_enum_children(enum_values: list[Any] | None) -> None:
    """Remove children relationships to avoid async lazy-load in response models."""
    if not enum_values:
        return
    for value in enum_values:
        try:
            set_committed_value(value, "children", [])
        except Exception:
            try:
                object.__setattr__(value, "children", [])
            except Exception:
                try:
                    setattr(value, "children", [])
                except Exception:
                    continue


def _resolve_service(service: EnumFieldService | Any) -> EnumFieldService | Any:
    if isinstance(service, DependsParam):
        return get_enum_field_service()
    return service


# Debug endpoint for testing
@router.get("/debug", dependencies=[Depends(require_localhost)])
@debug_only
async def debug_endpoint() -> dict[str, str]:
    """Debug endpoint to test basic API functionality"""
    return {"message": "Debug endpoint working", "timestamp": "2025-10-17T22:07:00Z"}


# 枚举字段类型管理
@router.get("/types", response_model=list[EnumFieldTypeResponse])
async def get_enum_field_types(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=1000, description="每页记录数"),
    category: str | None = Query(None, description="类别筛选"),
    status: str | None = Query(None, description="状态筛选"),
    is_system: bool | None = Query(None, description="是否系统内置"),
    keyword: str | None = Query(None, description="搜索关键词"),
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="enum_field",
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> list[EnumFieldTypeResponse]:
    """获取枚举字段类型列表"""
    resolved_service = _resolve_service(service)
    return await resolved_service.get_enum_field_types(
        db=db,
        page=page,
        page_size=page_size,
        category=category,
        status=status,
        is_system=is_system,
        keyword=keyword,
    )


@router.get("/types/statistics", response_model=EnumFieldStatistics)
async def get_enum_field_statistics(
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="enum_field",
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> EnumFieldStatistics:
    """获取枚举字段统计信息"""
    resolved_service = _resolve_service(service)
    return await resolved_service.get_enum_field_statistics(db)


@router.get("/types/{type_id}", response_model=EnumFieldTypeResponse)
async def get_enum_field_type(
    type_id: str = Path(..., description="枚举类型ID"),
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="enum_field",
            resource_id="{type_id}",
            deny_as_not_found=True,
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> EnumFieldTypeResponse:
    """根据ID获取枚举字段类型详情"""
    resolved_service = _resolve_service(service)
    return await resolved_service.get_enum_field_type(db, type_id=type_id)


@router.post("/types", response_model=EnumFieldTypeResponse)
async def create_enum_field_type(
    enum_type: EnumFieldTypeCreate,
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="create",
            resource_type="enum_field",
            resource_context=_ENUM_FIELD_TYPE_CREATE_RESOURCE_CONTEXT,
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> EnumFieldTypeResponse:
    """创建枚举字段类型"""
    resolved_service = _resolve_service(service)
    return await resolved_service.create_enum_field_type(db=db, enum_type=enum_type)


@router.put("/types/{type_id}", response_model=EnumFieldTypeResponse)
async def update_enum_field_type(
    type_id: str,
    enum_type: EnumFieldTypeUpdate,
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="enum_field",
            resource_id="{type_id}",
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> EnumFieldTypeResponse:
    """更新枚举字段类型"""
    resolved_service = _resolve_service(service)
    return await resolved_service.update_enum_field_type(
        db=db,
        type_id=type_id,
        enum_type=enum_type,
    )


@router.delete("/types/{type_id}")
async def delete_enum_field_type(
    type_id: str,
    deleted_by: str | None = Query(None, description="删除人"),
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="delete",
            resource_type="enum_field",
            resource_id="{type_id}",
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> dict[str, str]:
    """删除枚举字段类型"""
    resolved_service = _resolve_service(service)
    return await resolved_service.delete_enum_field_type(
        db=db,
        type_id=type_id,
        deleted_by=deleted_by,
    )


@router.get("/types/categories/list[Any]")
async def get_enum_field_categories(
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="enum_field",
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> dict[str, list[str]]:
    """获取枚举字段类别列表"""
    resolved_service = _resolve_service(service)
    return await resolved_service.get_enum_field_categories(db)


@router.get("/types/{type_id}/values", response_model=list[EnumFieldValueResponse])
async def get_enum_field_values(
    type_id: str,
    parent_id: str | None = Query(None, description="父级枚举值ID"),
    is_active: bool | None = Query(None, description="是否启用"),
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="enum_field",
            resource_id="{type_id}",
            deny_as_not_found=True,
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> list[EnumFieldValueResponse]:
    """获取枚举字段值列表"""
    resolved_service = _resolve_service(service)
    return await resolved_service.get_enum_field_values(
        db=db,
        type_id=type_id,
        parent_id=parent_id,
        is_active=is_active,
    )


@router.get("/types/{type_id}/values/tree", response_model=list[EnumFieldTree])
async def get_enum_field_values_tree(
    type_id: str,
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="enum_field",
            resource_id="{type_id}",
            deny_as_not_found=True,
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> list[EnumFieldTree]:
    """获取枚举字段值树形结构"""
    resolved_service = _resolve_service(service)
    return await resolved_service.get_enum_field_values_tree(db=db, type_id=type_id)


@router.get("/values/{value_id}", response_model=EnumFieldValueResponse)
async def get_enum_field_value(
    value_id: str = Path(..., description="枚举值ID"),
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="enum_field",
            resource_id="{value_id}",
            deny_as_not_found=True,
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> EnumFieldValueResponse:
    """根据ID获取枚举字段值详情"""
    resolved_service = _resolve_service(service)
    return await resolved_service.get_enum_field_value(db=db, value_id=value_id)


@router.post("/types/{type_id}/values", response_model=EnumFieldValueResponse)
async def create_enum_field_value(
    type_id: str,
    enum_value: EnumFieldValueCreate,
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="create",
            resource_type="enum_field",
            resource_id="{type_id}",
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> EnumFieldValueResponse:
    """创建枚举字段值"""
    resolved_service = _resolve_service(service)
    return await resolved_service.create_enum_field_value(
        db=db,
        type_id=type_id,
        enum_value=enum_value,
    )


@router.put("/values/{value_id}", response_model=EnumFieldValueResponse)
async def update_enum_field_value(
    value_id: str,
    enum_value: EnumFieldValueUpdate,
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="enum_field",
            resource_id="{value_id}",
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> EnumFieldValueResponse:
    """更新枚举字段值"""
    resolved_service = _resolve_service(service)
    return await resolved_service.update_enum_field_value(
        db=db,
        value_id=value_id,
        enum_value=enum_value,
    )


@router.delete("/values/{value_id}")
async def delete_enum_field_value(
    value_id: str,
    deleted_by: str | None = Query(None, description="删除人"),
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="delete",
            resource_type="enum_field",
            resource_id="{value_id}",
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> dict[str, str]:
    """删除枚举字段值"""
    resolved_service = _resolve_service(service)
    return await resolved_service.delete_enum_field_value(
        db=db,
        value_id=value_id,
        deleted_by=deleted_by,
    )


@router.post(
    "/types/{type_id}/values/batch", response_model=list[EnumFieldValueResponse]
)
async def batch_create_enum_field_values(
    type_id: str,
    batch_data: EnumFieldBatchCreate,
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="create",
            resource_type="enum_field",
            resource_id="{type_id}",
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> list[EnumFieldValueResponse]:
    """批量创建枚举字段值"""
    resolved_service = _resolve_service(service)
    return await resolved_service.batch_create_enum_field_values(
        db=db,
        type_id=type_id,
        batch_data=batch_data,
    )


@router.get("/usage", response_model=list[EnumFieldUsageResponse])
async def get_enum_field_usage(
    enum_type_id: str | None = Query(None, description="枚举类型ID"),
    table_name: str | None = Query(None, description="表名"),
    module_name: str | None = Query(None, description="模块名"),
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="enum_field",
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> list[EnumFieldUsageResponse]:
    """获取枚举字段使用记录"""
    resolved_service = _resolve_service(service)
    return await resolved_service.get_enum_field_usage(
        db=db,
        enum_type_id=enum_type_id,
        table_name=table_name,
        module_name=module_name,
    )


@router.post("/usage", response_model=EnumFieldUsageResponse)
async def create_enum_field_usage(
    usage: EnumFieldUsageCreate,
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="create",
            resource_type="enum_field",
            resource_context=_ENUM_FIELD_USAGE_CREATE_RESOURCE_CONTEXT,
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> EnumFieldUsageResponse:
    """创建枚举字段使用记录"""
    resolved_service = _resolve_service(service)
    return await resolved_service.create_enum_field_usage(db=db, usage=usage)


@router.put("/usage/{usage_id}", response_model=EnumFieldUsageResponse)
async def update_enum_field_usage(
    usage_id: str,
    usage: EnumFieldUsageUpdate,
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="enum_field",
            resource_id="{usage_id}",
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> EnumFieldUsageResponse:
    """更新枚举字段使用记录"""
    resolved_service = _resolve_service(service)
    return await resolved_service.update_enum_field_usage(
        db=db,
        usage_id=usage_id,
        usage=usage,
    )


@router.delete("/usage/{usage_id}")
async def delete_enum_field_usage(
    usage_id: str,
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="delete",
            resource_type="enum_field",
            resource_id="{usage_id}",
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> dict[str, str]:
    """删除枚举字段使用记录"""
    resolved_service = _resolve_service(service)
    return await resolved_service.delete_enum_field_usage(db=db, usage_id=usage_id)


@router.get("/types/{type_id}/history", response_model=list[EnumFieldHistoryResponse])
async def get_enum_field_type_history(
    type_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=1000, description="每页记录数"),
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="enum_field",
            resource_id="{type_id}",
            deny_as_not_found=True,
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> list[EnumFieldHistoryResponse]:
    """获取枚举字段类型变更历史"""
    resolved_service = _resolve_service(service)
    return await resolved_service.get_enum_field_type_history(
        db=db,
        type_id=type_id,
        page=page,
        page_size=page_size,
    )


@router.get("/values/{value_id}/history", response_model=list[EnumFieldHistoryResponse])
async def get_enum_field_value_history(
    value_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=1000, description="每页记录数"),
    db: AsyncSession = Depends(get_async_db),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="enum_field",
            resource_id="{value_id}",
            deny_as_not_found=True,
        )
    ),
    service: EnumFieldService = Depends(get_enum_field_service),
) -> list[EnumFieldHistoryResponse]:
    """获取枚举字段值变更历史"""
    resolved_service = _resolve_service(service)
    return await resolved_service.get_enum_field_value_history(
        db=db,
        value_id=value_id,
        page=page,
        page_size=page_size,
    )
