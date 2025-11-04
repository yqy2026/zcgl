from typing import Any

"""
自定义字段管理API路由
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from ...crud.custom_field import custom_field_crud
from ...database import get_db
from ...schemas.asset import (
    AssetCustomFieldCreate,
    AssetCustomFieldResponse,
    AssetCustomFieldUpdate,
    CustomFieldValueUpdate,
)

# 创建自定义字段路由器
router = APIRouter()


@router.get(
    "/", response_model=list[AssetCustomFieldResponse], summary="获取自定义字段列表"
)
async def get_custom_fields(
    asset_id: str | None = Query(None, description="资产ID筛选"),
    field_type: str | None = Query(None, description="字段类型筛选"),
    is_required: bool | None = Query(None, description="是否必填筛选"),
    is_active: bool | None = Query(None, description="是否启用筛选"),
    db: Session = Depends(get_db),
):
    """
    获取自定义字段配置列表，支持筛选

    - **asset_id**: 资产ID
    - **field_type**: 字段类型
    - **is_required**: 是否必填
    - **is_active**: 是否启用
    """
    try:
        filters = {}
        if asset_id:
            filters["asset_id"] = asset_id
        if field_type:
            filters["field_type"] = field_type
        if is_required is not None:
            filters["is_required"] = is_required
        if is_active is not None:
            filters["is_active"] = is_active

        fields = custom_field_crud.get_multi_with_filters(db=db, filters=filters)
        return fields

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取自定义字段列表失败: {str(e)}")


@router.get(
    "/{field_id}", response_model=AssetCustomFieldResponse, summary="获取自定义字段详情"
)
async def get_custom_field(
    field_id: str = Path(..., description="字段ID"), db: Session = Depends(get_db)
):
    """
    根据ID获取单个自定义字段的详细信息

    - **field_id**: 字段ID
    """
    try:
        field = custom_field_crud.get(db=db, id=field_id)
        if not field:
            raise HTTPException(status_code=404, detail=f"字段 {field_id} 不存在")
        return field

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取自定义字段详情失败: {str(e)}")


@router.post(
    "/",
    response_model=AssetCustomFieldResponse,
    summary="创建自定义字段",
    status_code=201,
)
async def create_custom_field(
    field_in: AssetCustomFieldCreate, db: Session = Depends(get_db)
):
    """
    创建新的自定义字段配置

    - **field_in**: 字段创建数据
    """
    try:
        # 检查是否存在相同的字段名
        existing = custom_field_crud.get_by_field_name(
            db=db, field_name=field_in.field_name
        )
        if existing:
            raise HTTPException(
                status_code=400, detail=f"字段名 {field_in.field_name} 已存在"
            )

        field = custom_field_crud.create(db=db, obj_in=field_in)
        return field

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建自定义字段失败: {str(e)}")


@router.put(
    "/{field_id}", response_model=AssetCustomFieldResponse, summary="更新自定义字段"
)
async def update_custom_field(
    field_in: AssetCustomFieldUpdate,
    field_id: str = Path(..., description="字段ID"),
    db: Session = Depends(get_db),
):
    """
    更新自定义字段配置

    - **field_id**: 字段ID
    - **field_in**: 字段更新数据
    """
    try:
        # 检查字段是否存在
        field = custom_field_crud.get(db=db, id=field_id)
        if not field:
            raise HTTPException(status_code=404, detail=f"字段 {field_id} 不存在")

        # 如果更新了字段名，检查是否重复
        if field_in.field_name and field_in.field_name != field.field_name:
            existing = custom_field_crud.get_by_field_name(
                db=db, field_name=field_in.field_name
            )
            if existing and existing.id != field_id:
                raise HTTPException(
                    status_code=400, detail=f"字段名 {field_in.field_name} 已存在"
                )

        updated_field = custom_field_crud.update(db=db, db_obj=field, obj_in=field_in)
        return updated_field

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新自定义字段失败: {str(e)}")


@router.delete("/{field_id}", summary="删除自定义字段")
async def delete_custom_field(
    field_id: str = Path(..., description="字段ID"), db: Session = Depends(get_db)
):
    """
    删除自定义字段配置

    - **field_id**: 字段ID
    """
    try:
        # 检查字段是否存在
        field = custom_field_crud.get(db=db, id=field_id)
        if not field:
            raise HTTPException(status_code=404, detail=f"字段 {field_id} 不存在")

        # 删除字段
        custom_field_crud.remove(db=db, id=field_id)
        return {"message": f"字段 {field_id} 已成功删除"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除自定义字段失败: {str(e)}")


@router.post("/validate", summary="验证自定义字段值")
async def validate_custom_field_value(
    field_id: str, value: Any, db: Session = Depends(get_db)
):
    """
    验证自定义字段值是否符合配置要求

    - **field_id**: 字段ID
    - **value**: 字段值
    """
    try:
        # 获取字段配置
        field = custom_field_crud.get(db=db, id=field_id)
        if not field:
            raise HTTPException(status_code=404, detail=f"字段 {field_id} 不存在")

        # 验证字段值
        is_valid, error_message = custom_field_crud.validate_field_value(field, value)

        if is_valid:
            return {"valid": True, "message": "验证通过"}
        else:
            return {"valid": False, "error": error_message}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"验证字段值失败: {str(e)}")


@router.get("/types/list", summary="获取字段类型列表")
async def get_field_types():
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
        raise HTTPException(status_code=500, detail=f"获取字段类型失败: {str(e)}")


# 资产自定义字段值相关接口
@router.get("/assets/{asset_id}/values", summary="获取资产自定义字段值")
async def get_asset_custom_field_values(
    asset_id: str = Path(..., description="资产ID"), db: Session = Depends(get_db)
):
    """
    获取指定资产的所有自定义字段值

    - **asset_id**: 资产ID
    """
    try:
        values = custom_field_crud.get_asset_field_values(db=db, asset_id=asset_id)
        return {"asset_id": asset_id, "values": values}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"获取资产自定义字段值失败: {str(e)}"
        )


@router.put("/assets/{asset_id}/values", summary="更新资产自定义字段值")
async def update_asset_custom_field_values(
    values_update: CustomFieldValueUpdate,
    asset_id: str = Path(..., description="资产ID"),
    db: Session = Depends(get_db),
):
    """
    更新指定资产的自定义字段值

    - **asset_id**: 资产ID
    - **values_update**: 字段值更新数据
    """
    try:
        updated_values = custom_field_crud.update_asset_field_values(
            db=db, asset_id=asset_id, values=values_update.values
        )
        return {"asset_id": asset_id, "values": updated_values}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"更新资产自定义字段值失败: {str(e)}"
        )


@router.post("/assets/batch-values", summary="批量设置自定义字段值")
async def batch_set_custom_field_values(
    updates: list[dict], db: Session = Depends(get_db)
):
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
                updated_values = custom_field_crud.update_asset_field_values(
                    db=db, asset_id=asset_id, values=values
                )
                results.append(
                    {"asset_id": asset_id, "success": True, "values": updated_values}
                )
            except Exception as e:
                results.append(
                    {"asset_id": asset_id, "success": False, "error": str(e)}
                )

        return {"results": results}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"批量设置自定义字段值失败: {str(e)}"
        )
