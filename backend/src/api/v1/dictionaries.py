"""
统一的字典管理API
整合系统字典和枚举字段功能，提供简化的使用接口
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import uuid

from ...database import get_db
from ...models.enum_field import EnumFieldType, EnumFieldValue
from ...models.asset import SystemDictionary
from ...crud.enum_field import get_enum_field_type_crud, get_enum_field_value_crud
from ...schemas.enum_field import EnumFieldTypeCreate, EnumFieldValueCreate
from pydantic import BaseModel

router = APIRouter(prefix="/dictionaries", tags=["统一字典管理"])


def fix_chinese_label(dict_type: str, value: str, original_label: str) -> str:
    """
    修复中文标签，如果数据库中的标签是乱码，则返回正确的中文标签
    """
    # 定义正确的中文标签映射
    correct_labels = {
        'property_nature': {
            'commercial': '经营性',
            'non_commercial': '非经营性'
        },
        'usage_status': {
            'rented': '出租',
            'vacant': '空置',
            'self_use': '自用',
            'public_housing': '公房',
            'pending_transfer': '待移交',
            'pending_disposal': '待处置',
            'other': '其他'
        },
        'ownership_status': {
            'confirmed': '已确权',
            'unconfirmed': '未确权',
            'partial': '部分确权'
        },
        'business_category': {
            'commercial': '商业',
            'office': '办公',
            'residential': '住宅',
            'warehouse': '仓储',
            'industrial': '工业',
            'other': '其他'
        },
        'tenant_type': {
            'individual': '个人',
            'enterprise': '企业',
            'government': '政府机构',
            'other': '其他'
        },
        'contract_status': {
            'active': '生效中',
            'expired': '已到期',
            'terminated': '已终止',
            'pending': '待签署'
        },
        'business_model': {
            'sublease': '承租转租',
            'entrusted': '委托经营',
            'self_operated': '自营',
            'other': '其他'
        },
        'operation_status': {
            'normal': '正常经营',
            'suspended': '停业整顿',
            'renovating': '装修中',
            'vacant_for_rent': '待招租'
        },
        'ownership_category': {
            'state_owned': '国有资产',
            'collective': '集体资产',
            'private': '私有资产',
            'mixed': '混合所有制',
            'other': '其他'
        },
        'certificated_usage': {
            'commercial': '商业',
            'office': '办公',
            'residential': '住宅',
            'industrial': '工业',
            'other': '其他'
        },
        'actual_usage': {
            'commercial': '商业',
            'office': '办公',
            'residential': '住宅',
            'industrial': '工业',
            'other': '其他'
        }
    }

    # 直接替换已知乱码值
    # 检查原标签是否包含常见乱码字符特征
    corrupted_patterns = [
        '\udca7', '\udc80', '\u30e6', '\u93ac', '\u60c0', '\u5fda', '\u7f01',
        '\u9480', '\u70b5', '\u95c8', '\u7ca1', '\u30e6', '\u77e3', '\u7d5e'
    ]

    is_corrupted = any(pattern in original_label for pattern in corrupted_patterns)

    # 如果有乱码且存在正确的映射，则返回正确的中文标签
    if is_corrupted and dict_type in correct_labels and value in correct_labels[dict_type]:
        return correct_labels[dict_type][value]

    # 如果原标签是英文但应该显示中文，也进行替换
    if dict_type in correct_labels and value in correct_labels[dict_type]:
        if original_label == value or original_label.isascii():  # 如果标签和value相同或是纯ASCII
            return correct_labels[dict_type][value]

    # 默认返回原标签
    return original_label


class DictionaryOptionResponse(BaseModel):
    """字典选项响应模型"""
    label: str
    value: str
    code: Optional[str] = None
    sort_order: int = 0
    color: Optional[str] = None
    icon: Optional[str] = None


class SimpleDictionaryCreate(BaseModel):
    """简单字典创建模型"""
    options: List[Dict[str, Any]]
    description: Optional[str] = None


@router.get("/{dict_type}/options", response_model=List[DictionaryOptionResponse])
async def get_dictionary_options(
    dict_type: str = Path(..., description="字典类型"),
    is_active: bool = Query(True, description="是否只返回启用的选项"),
    db: Session = Depends(get_db)
):
    """
    获取字典选项（统一接口）
    支持从枚举字段和系统字典两个来源获取数据
    """
    try:
        # 优先从枚举字段获取
        enum_type_crud = get_enum_field_type_crud(db)
        enum_type = enum_type_crud.get_by_code(dict_type)
        
        if enum_type:
            # 从枚举字段获取
            enum_value_crud = get_enum_field_value_crud(db)
            enum_values = enum_value_crud.get_by_type(
                enum_type.id, 
                is_active=is_active if is_active is not None else None
            )
            
            return [
                DictionaryOptionResponse(
                    label=fix_chinese_label(dict_type, value.value, value.label),
                    value=value.value,
                    code=value.code,
                    sort_order=value.sort_order,
                    color=value.color,
                    icon=value.icon
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
            SystemDictionary.sort_order, 
            SystemDictionary.created_at
        ).all()
        
        return [
            DictionaryOptionResponse(
                label=item.dict_label,
                value=item.dict_value,
                code=item.dict_code,
                sort_order=item.sort_order
            )
            for item in system_dicts
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取字典选项失败: {str(e)}")


@router.post("/{dict_type}/quick-create")
async def quick_create_dictionary(
    dict_type: str = Path(..., description="字典类型"),
    dictionary_data: SimpleDictionaryCreate = ...,
    db: Session = Depends(get_db)
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
            name=dict_type.replace('_', ' ').title(),
            code=dict_type,
            category="简单字典",
            description=dictionary_data.description or f"{dict_type} 字典",
            is_system=False,
            is_hierarchical=False,
            is_multiple=False,
            created_by="系统"
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
                created_by="系统"
            )
            
            created_value = enum_value_crud.create(enum_value_create)
            created_values.append(created_value)
        
        return {
            "message": f"字典 {dict_type} 创建成功",
            "type_id": enum_type.id,
            "values_count": len(created_values)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建简单字典失败: {str(e)}")


@router.get("/types", response_model=List[str])
async def get_dictionary_types(db: Session = Depends(get_db)):
    """获取所有字典类型列表"""
    try:
        # 从枚举字段获取
        enum_types = db.query(EnumFieldType.code).filter(
            EnumFieldType.is_deleted == False
        ).all()
        
        # 从系统字典获取（向后兼容）
        system_types = db.query(SystemDictionary.dict_type).distinct().all()
        
        all_types = set()
        all_types.update([t[0] for t in enum_types if t[0]])
        all_types.update([t[0] for t in system_types if t[0]])
        
        return sorted(list(all_types))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取字典类型失败: {str(e)}")


@router.post("/{dict_type}/values")
async def add_dictionary_value(
    dict_type: str = Path(..., description="字典类型"),
    value_data: Dict[str, Any] = ...,
    db: Session = Depends(get_db)
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
            enum_type.id, 
            value_data.get("value", "")
        )
        if existing_value:
            raise HTTPException(
                status_code=400, 
                detail=f"值 {value_data.get('value')} 已存在"
            )
        
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
            created_by="系统"
        )
        
        created_value = enum_value_crud.create(enum_value_create)
        
        return {
            "message": "字典值添加成功",
            "value_id": created_value.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加字典值失败: {str(e)}")


@router.delete("/{dict_type}")
async def delete_dictionary_type(
    dict_type: str = Path(..., description="字典类型"),
    db: Session = Depends(get_db)
):
    """删除字典类型及其所有值"""
    try:
        enum_type_crud = get_enum_field_type_crud(db)
        enum_type = enum_type_crud.get_by_code(dict_type)
        
        if not enum_type:
            raise HTTPException(status_code=404, detail=f"字典类型 {dict_type} 不存在")
        
        # 软删除枚举类型（会级联删除枚举值）
        success = enum_type_crud.delete(enum_type.id, deleted_by="系统")
        
        if not success:
            raise HTTPException(status_code=500, detail="删除失败")
        
        return {"message": f"字典类型 {dict_type} 删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除字典类型失败: {str(e)}")