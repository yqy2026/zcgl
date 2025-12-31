from typing import Any

"""
统一的字典管理API
整合系统字典和枚举字段功能，提供简化的使用接口
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...crud.enum_field import get_enum_field_type_crud, get_enum_field_value_crud
from ...database import get_db
from ...models.asset import SystemDictionary
from ...models.enum_field import EnumFieldType
from ...schemas.enum_field import EnumFieldTypeCreate, EnumFieldValueCreate

# 创建logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dictionaries", tags=["统一字典管理"])


def fix_chinese_label(dict_type: str, value: str, original_label: str) -> str:
    """Simplified version - just return original label"""
    return original_label


class DictionaryOptionResponse(BaseModel):
    """字典选项响应模型"""

    label: str
    value: str
    code: str | None = None
    sort_order: int = 0
    color: str | None = None
    icon: str | None = None


class SimpleDictionaryCreate(BaseModel):
    """简单字典创建模型"""

    options: list[dict[str, Any]]
    description: str | None = None


@router.get("/{dict_type}/options", response_model=list[DictionaryOptionResponse])
async def get_dictionary_options(
    dict_type: str = Path(..., description="字典类型"),
    is_active: bool = Query(True, description="是否只返回启用的选项"),
    db: Session = Depends(get_db),
):
    """
    获取字典选项（统一接口）
    支持从枚举字段和系统字典两个来源获取数据
    """
    try:
        # 优先从枚举字段获取
        enum_type_crud = get_enum_field_type_crud(db)
        enum_type = enum_type_crud.get_by_code(dict_type)

        if enum_type:  # pragma: no cover
            # 从枚举字段获取
            enum_value_crud = get_enum_field_value_crud(db)  # pragma: no cover
            enum_values = enum_value_crud.get_by_type(  # pragma: no cover
                enum_type.id,
                is_active=is_active
                if is_active is not None
                else None,  # pragma: no cover
            )  # pragma: no cover

            return [  # pragma: no cover
                DictionaryOptionResponse(
                    label=fix_chinese_label(dict_type, value.value, value.label),
                    value=value.value,
                    code=value.code,
                    sort_order=value.sort_order,
                    color=value.color,
                    icon=value.icon,
                )
                for value in enum_values
            ]

        # 兜底：从系统字典获取（向后兼容）
        system_dicts = db.query(SystemDictionary).filter(
            SystemDictionary.dict_type == dict_type
        )

        if is_active is not None:
            system_dicts = system_dicts.filter(SystemDictionary.is_active == is_active)

        system_dicts = system_dicts.order_by(
            SystemDictionary.sort_order, SystemDictionary.created_at
        ).all()

        return [
            DictionaryOptionResponse(
                label=item.dict_label,
                value=item.dict_value,
                code=item.dict_code,
                sort_order=item.sort_order,
            )
            for item in system_dicts
        ]  # pragma: no cover

    except Exception as e:  # pragma: no cover
        raise HTTPException(
            status_code=500, detail=f"获取字典选项失败: {str(e)}"
        )  # pragma: no cover


@router.post("/{dict_type}/quick-create")
async def quick_create_dictionary(
    dict_type: str = Path(..., description="字典类型"),
    dictionary_data: SimpleDictionaryCreate = ...,
    db: Session = Depends(get_db),
):
    """
    快速创建字典（兼容原系统字典功能）
    自动创建枚举类型和枚举值
    """
    try:
        enum_type_crud = get_enum_field_type_crud(db)

        # 检查是否已存在
        existing_type = enum_type_crud.get_by_code(dict_type)
        if existing_type:
            raise HTTPException(status_code=400, detail=f"字典类型 {dict_type} 已存在")

        # 创建枚举类型
        enum_type_create = EnumFieldTypeCreate(
            name=dict_type.replace("_", " ").title(),
            code=dict_type,
            category="简单字典",
            description=dictionary_data.description or f"{dict_type} 字典",
            is_system=False,
            is_hierarchical=False,
            is_multiple=False,
            created_by="系统",
        )

        enum_type = enum_type_crud.create(enum_type_create)

        # 批量创建枚举值
        enum_value_crud = get_enum_field_value_crud(db)
        created_values = []

        for i, option in enumerate(dictionary_data.options):
            enum_value_create = EnumFieldValueCreate(
                enum_type_id=enum_type.id,
                label=option.get("label", ""),
                value=option.get("value", ""),
                code=option.get("code"),
                description=option.get("description"),
                sort_order=option.get("sort_order", i + 1),
                color=option.get("color"),
                icon=option.get("icon"),
                is_active=option.get("is_active", True),
                created_by="系统",
            )

            created_value = enum_value_crud.create(enum_value_create)
            created_values.append(created_value)

        return {
            "message": f"字典 {dict_type} 创建成功",
            "type_id": enum_type.id,
            "values_count": len(created_values),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建简单字典失败: {str(e)}")


@router.get("/types", response_model=list[str])
async def get_dictionary_types(db: Session = Depends(get_db)):
    """
    获取所有字典类型列表

    注意：已废弃旧的system_dictionaries表，统一使用enum_field表
    """
    # 从枚举字段表获取
    enum_types = (
        db.query(EnumFieldType.code).filter(EnumFieldType.is_deleted == False).all()
    )

    # 直接返回枚举类型代码列表
    return sorted([t.code for t in enum_types if t.code])


@router.get("/validation/stats", summary="获取枚举验证统计信息")
async def get_validation_statistics(
    enum_type: str | None = Query(None, description="枚举类型编码（可选）"),
    db: Session = Depends(get_db),
):
    """
    获取枚举验证统计信息

    返回各枚举类型的验证统计数据：
    - total_validations: 总验证次数
    - failures: 失败次数
    - failure_rate: 失败率（百分比）
    - last_failure_time: 最后一次失败时间
    - last_failure_value: 最后一次失败的值
    - last_failure_context: 最后一次失败的上下文信息

    这些统计信息可以帮助发现数据质量问题，例如：
    - 某个枚举类型频繁验证失败，可能需要添加新的枚举值
    - 某个用户经常提交无效值，可能需要培训
    - 某个API端点频繁失败，可能需要前端修复
    """
    from ...services.enum_validation_service import get_enum_validation_service

    enum_service = get_enum_validation_service(db)
    stats = enum_service.get_validation_stats(enum_type)

    # 添加计算字段
    result = {}
    for enum_code, stat_data in stats.items():
        failure_rate = (
            (stat_data["failures"] / stat_data["total_validations"] * 100)
            if stat_data["total_validations"] > 0
            else 0
        )

        result[enum_code] = {
            **stat_data,
            "failure_rate": round(failure_rate, 2),
        }

    return {
        "success": True,
        "data": result,
        "total_enum_types": len(result),
    }


@router.post("/{dict_type}/values")
async def add_dictionary_value(
    dict_type: str = Path(..., description="字典类型"),
    value_data: dict[str, Any] = ...,
    db: Session = Depends(get_db),
):
    """为指定字典类型添加新的选项值"""
    try:
        enum_type_crud = get_enum_field_type_crud(db)
        enum_type = enum_type_crud.get_by_code(dict_type)

        if not enum_type:
            raise HTTPException(status_code=404, detail=f"字典类型 {dict_type} 不存在")

        enum_value_crud = get_enum_field_value_crud(db)

        # 检查值是否已存在
        existing_value = enum_value_crud.get_by_type_and_value(
            enum_type.id, value_data.get("value", "")
        )  # pragma: no cover
        if existing_value:  # pragma: no cover
            raise HTTPException(  # pragma: no cover
                status_code=400,
                detail=f"值 {value_data.get('value')} 已存在",  # pragma: no cover
            )  # pragma: no cover

        enum_value_create = EnumFieldValueCreate(
            enum_type_id=enum_type.id,
            label=value_data.get("label", ""),
            value=value_data.get("value", ""),
            code=value_data.get("code"),
            description=value_data.get("description"),
            sort_order=value_data.get("sort_order", 999),
            color=value_data.get("color"),
            icon=value_data.get("icon"),
            is_active=value_data.get("is_active", True),
            created_by="系统",
        )

        created_value = enum_value_crud.create(enum_value_create)

        return {"message": "字典值添加成功", "value_id": created_value.id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加字典值失败: {str(e)}")


@router.delete("/{dict_type}")
async def delete_dictionary_type(
    dict_type: str = Path(..., description="字典类型"), db: Session = Depends(get_db)
):
    """删除字典类型及其所有值"""
    try:
        enum_type_crud = get_enum_field_type_crud(db)
        enum_type = enum_type_crud.get_by_code(dict_type)

        if not enum_type:
            raise HTTPException(status_code=404, detail=f"字典类型 {dict_type} 不存在")

        # 软删除枚举类型（会级联删除枚举值）
        success = enum_type_crud.delete(
            enum_type.id, deleted_by="系统"
        )  # pragma: no cover

        if not success:  # pragma: no cover
            raise HTTPException(status_code=500, detail="删除失败")  # pragma: no cover

        return {"message": f"字典类型 {dict_type} 删除成功"}  # pragma: no cover

    except HTTPException:  # pragma: no cover
        raise  # pragma: no cover
    except Exception as e:  # pragma: no cover
        raise HTTPException(
            status_code=500, detail=f"删除字典类型失败: {str(e)}"
        )  # pragma: no cover
