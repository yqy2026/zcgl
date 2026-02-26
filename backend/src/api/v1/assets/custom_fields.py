"""
自定义字段管理API路由
"""

from typing import Any

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import (
    BaseBusinessError,
    internal_error,
    not_found,
)
from ....database import get_async_db
from ....middleware.auth import AuthzContext, get_current_active_user, require_authz
from ....models.auth import User
from ....schemas.asset import (
    AssetCustomFieldCreate,
    AssetCustomFieldResponse,
    AssetCustomFieldUpdate,
    CustomFieldValueUpdate,
)
from ....services.custom_field import custom_field_service

# 创建自定义字段路由器
router = APIRouter()
_ASSET_CUSTOM_FIELD_CREATE_UNSCOPED_PARTY_ID = "__unscoped__:asset_custom_field:create"
_ASSET_CUSTOM_FIELD_CREATE_RESOURCE_CONTEXT: dict[str, str] = {
    "party_id": _ASSET_CUSTOM_FIELD_CREATE_UNSCOPED_PARTY_ID,
    "owner_party_id": _ASSET_CUSTOM_FIELD_CREATE_UNSCOPED_PARTY_ID,
    "manager_party_id": _ASSET_CUSTOM_FIELD_CREATE_UNSCOPED_PARTY_ID,
}
_ASSET_CUSTOM_FIELD_BATCH_UPDATE_UNSCOPED_PARTY_ID = (
    "__unscoped__:asset_custom_field:batch_update_values"
)
_ASSET_CUSTOM_FIELD_BATCH_UPDATE_RESOURCE_CONTEXT: dict[str, str] = {
    "party_id": _ASSET_CUSTOM_FIELD_BATCH_UPDATE_UNSCOPED_PARTY_ID,
    "owner_party_id": _ASSET_CUSTOM_FIELD_BATCH_UPDATE_UNSCOPED_PARTY_ID,
    "manager_party_id": _ASSET_CUSTOM_FIELD_BATCH_UPDATE_UNSCOPED_PARTY_ID,
}


@router.get(
    "/", response_model=list[AssetCustomFieldResponse], summary="获取自定义字段列表"
)
async def get_custom_fields(
    asset_id: str | None = Query(None, description="资产ID筛选"),
    field_type: str | None = Query(None, description="字段类型筛选"),
    is_required: bool | None = Query(None, description="是否必填筛选"),
    is_active: bool | None = Query(None, description="是否启用筛选"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="custom_field",
        )
    ),
) -> list[AssetCustomFieldResponse]:
    """
    获取自定义字段配置列表，支持筛选

    - **asset_id**: 资产ID
    - **field_type**: 字段类型
    - **is_required**: 是否必填
    - **is_active**: 是否启用
    """

    try:
        filters: dict[str, Any] = {}
        if asset_id:
            filters["asset_id"] = asset_id
        if field_type:
            filters["field_type"] = field_type
        if is_required is not None:
            filters["is_required"] = is_required
        if is_active is not None:
            filters["is_active"] = is_active

        fields = await custom_field_service.get_custom_fields_async(
            db=db,
            filters=filters,
            current_user_id=str(current_user.id),
        )
        return [AssetCustomFieldResponse.model_validate(f) for f in fields]

    except Exception as e:
        raise internal_error(f"获取自定义字段列表失败: {str(e)}")


@router.get(
    "/{field_id}", response_model=AssetCustomFieldResponse, summary="获取自定义字段详情"
)
async def get_custom_field(
    field_id: str = Path(..., description="字段ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="custom_field",
            resource_id="{field_id}",
        )
    ),
) -> AssetCustomFieldResponse:
    """
    根据ID获取单个自定义字段的详细信息

    - **field_id**: 字段ID
    """

    try:
        field = await custom_field_service.get_custom_field_async(
            db=db,
            field_id=field_id,
            current_user_id=str(current_user.id),
        )
        if not field:
            raise not_found(
                f"字段 {field_id} 不存在",
                resource_type="custom_field",
                resource_id=field_id,
            )
        return AssetCustomFieldResponse.model_validate(field)

    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"获取自定义字段详情失败: {str(e)}")


@router.post(
    "/",
    response_model=AssetCustomFieldResponse,
    summary="创建自定义字段",
    status_code=201,
)
async def create_custom_field(
    field_in: AssetCustomFieldCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="create",
            resource_type="asset",
            resource_context=_ASSET_CUSTOM_FIELD_CREATE_RESOURCE_CONTEXT,
        )
    ),
) -> AssetCustomFieldResponse:
    """
    创建新的自定义字段配置

    - **field_in**: 字段创建数据
    """

    try:
        field = await custom_field_service.create_custom_field_async(
            db=db, obj_in=field_in
        )
        return AssetCustomFieldResponse.model_validate(field)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"创建自定义字段失败: {str(e)}")


@router.put(
    "/{field_id}", response_model=AssetCustomFieldResponse, summary="更新自定义字段"
)
async def update_custom_field(
    field_in: AssetCustomFieldUpdate,
    field_id: str = Path(..., description="字段ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="asset",
            resource_id="{field_id}",
        )
    ),
) -> AssetCustomFieldResponse:
    """
    更新自定义字段配置

    - **field_id**: 字段ID
    - **field_in**: 字段更新数据
    """

    try:
        updated_field = await custom_field_service.update_custom_field_async(
            db=db, id=field_id, obj_in=field_in
        )
        return AssetCustomFieldResponse.model_validate(updated_field)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"更新自定义字段失败: {str(e)}")


@router.delete("/{field_id}", summary="删除自定义字段")
async def delete_custom_field(
    field_id: str = Path(..., description="字段ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="delete",
            resource_type="asset",
            resource_id="{field_id}",
        )
    ),
) -> dict[str, str]:
    """
    删除自定义字段配置

    - **field_id**: 字段ID
    """

    try:
        await custom_field_service.delete_custom_field_async(db=db, id=field_id)
        return {"message": f"字段 {field_id} 已成功删除"}
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"删除自定义字段失败: {str(e)}")


@router.post("/validate", summary="验证自定义字段值")
async def validate_custom_field_value(
    field_id: str,
    value: Any,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="custom_field",
        )
    ),
) -> dict[str, Any]:
    """
    验证自定义字段值是否符合配置要求

    - **field_id**: 字段ID
    - **value**: 字段值
    """

    try:
        is_valid, error_message = await custom_field_service.validate_custom_field_value_async(
            db=db,
            field_id=field_id,
            value=value,
        )

        if is_valid:
            return {"valid": True, "message": "验证通过"}
        else:
            return {"valid": False, "error": error_message}

    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"验证字段值失败: {str(e)}")


@router.get("/types", summary="获取字段类型列表")
@router.get("/types/list[Any]", include_in_schema=False)
def get_field_types(
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="read",
            resource_type="asset",
        )
    ),
) -> dict[str, Any]:
    """
    获取支持的字段类型列表
    """
    try:
        field_types = [
            {"value": "text", "label": "文本"},
            {"value": "number", "label": "数字"},
            {"value": "decimal", "label": "小数"},
            {"value": "boolean", "label": "布尔值"},
            {"value": "date", "label": "日期"},
            {"value": "datetime", "label": "日期时间"},
            {"value": "select", "label": "单选"},
            {"value": "multiselect", "label": "多选"},
            {"value": "textarea", "label": "多行文本"},
            {"value": "url", "label": "链接"},
            {"value": "email", "label": "邮箱"},
            {"value": "phone", "label": "电话"},
        ]
        return {"field_types": field_types}

    except Exception as e:
        raise internal_error(f"获取字段类型失败: {str(e)}")


# 资产自定义字段值相关接口
@router.get("/assets/{asset_id}/values", summary="获取资产自定义字段值")
async def get_asset_custom_field_values(
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
    获取指定资产的所有自定义字段值

    - **asset_id**: 资产ID
    """

    try:
        values = await custom_field_service.get_asset_field_values_async(
            db=db,
            asset_id=asset_id,
        )
        return {"asset_id": asset_id, "values": values}

    except Exception as e:
        raise internal_error(f"获取资产自定义字段值失败: {str(e)}")


@router.put("/assets/{asset_id}/values", summary="更新资产自定义字段值")
async def update_asset_custom_field_values(
    values_update: CustomFieldValueUpdate,
    asset_id: str = Path(..., description="资产ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="asset",
            resource_id="{asset_id}",
        )
    ),
) -> dict[str, Any]:
    """
    更新指定资产的自定义字段值

    - **asset_id**: 资产ID
    - **values_update**: 字段值更新数据
    """

    try:
        updated_values = await custom_field_service.update_asset_field_values_async(
            db=db, asset_id=asset_id, values=values_update.values
        )
        return {"asset_id": asset_id, "values": updated_values}
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"更新资产自定义字段值失败: {str(e)}")


@router.post("/assets/batch-values", summary="批量设置自定义字段值")
async def batch_set_custom_field_values(
    updates: list[dict[str, Any]],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    _authz_ctx: AuthzContext = Depends(
        require_authz(
            action="update",
            resource_type="asset",
            resource_context=_ASSET_CUSTOM_FIELD_BATCH_UPDATE_RESOURCE_CONTEXT,
        )
    ),
) -> dict[str, Any]:
    """
    批量设置多个资产的自定义字段值

    - **updates**: 更新数据列表，格式: [{"asset_id": "xxx", "values": [...]}]
    """

    try:
        results = []

        for update in updates:
            asset_id = update.get("asset_id")
            values = update.get("values", [])

            if not asset_id:
                continue

            try:
                updated_values = await custom_field_service.update_asset_field_values_async(
                    db=db, asset_id=asset_id, values=values
                )
                results.append(
                    {
                        "asset_id": asset_id,
                        "success": True,
                        "values": updated_values,
                    }
                )
            except Exception as e:
                results.append(
                    {"asset_id": asset_id, "success": False, "error": str(e)}
                )

        return {"results": results}

    except Exception as e:
        raise internal_error(f"批量设置自定义字段值失败: {str(e)}")
