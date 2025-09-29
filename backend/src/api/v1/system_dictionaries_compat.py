"""
系统字典兼容性API
为了向后兼容，保留原有的系统字典API接口
内部实际调用统一的字典管理功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional

from ...database import get_db
from ...schemas.asset import SystemDictionaryCreate, SystemDictionaryUpdate, SystemDictionaryResponse
from .dictionaries import get_dictionary_options, quick_create_dictionary, SimpleDictionaryCreate
from ...models.asset import SystemDictionary

router = APIRouter(prefix="/system-dictionaries-compat", tags=["系统字典兼容"])


@router.get("/", response_model=List[SystemDictionaryResponse])
async def get_system_dictionaries_compat(
    dict_type: Optional[str] = Query(None, description="字典类型筛选"),
    is_active: Optional[bool] = Query(None, description="是否启用筛选"),
    db: Session = Depends(get_db)
):
    """
    获取系统字典列表（兼容接口）
    内部调用统一字典API
    """
    try:
        if dict_type:
            # 调用统一字典API获取选项
            options = await get_dictionary_options(dict_type, is_active or True, db)
            
            # 转换为系统字典格式
            return [
                SystemDictionaryResponse(
                    id=f"{dict_type}_{option.value}",
                    dict_type=dict_type,
                    dict_code=option.code or option.value,
                    dict_label=option.label,
                    dict_value=option.value,
                    sort_order=option.sort_order,
                    is_active=True,
                    created_at="2024-01-01T00:00:00",
                    updated_at="2024-01-01T00:00:00"
                )
                for option in options
            ]
        else:
            # 如果没有指定类型，返回空列表或从数据库查询
            return []
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统字典列表失败: {str(e)}")


@router.post("/", response_model=dict)
async def create_system_dictionary_compat(
    dictionary_in: SystemDictionaryCreate,
    db: Session = Depends(get_db)
):
    """
    创建系统字典项（兼容接口）
    内部转换为统一字典格式
    """
    try:
        # 检查字典类型是否已存在，如果不存在则创建
        try:
            await get_dictionary_options(dictionary_in.dict_type, True, db)
        except:
            # 字典类型不存在，创建新的字典类型
            dictionary_data = SimpleDictionaryCreate(
                options=[{
                    "label": dictionary_in.dict_label,
                    "value": dictionary_in.dict_value,
                    "code": dictionary_in.dict_code,
                    "sort_order": dictionary_in.sort_order,
                    "is_active": dictionary_in.is_active
                }],
                description=f"{dictionary_in.dict_type} 字典"
            )
            
            result = await quick_create_dictionary(
                dict_type=dictionary_in.dict_type,
                dictionary_data=dictionary_data,
                db=db
            )
            
            return {
                "id": f"{dictionary_in.dict_type}_{dictionary_in.dict_value}",
                "message": "字典项创建成功",
                "dict_type": dictionary_in.dict_type
            }
        
        # 如果字典类型已存在，添加新值
        from .dictionaries import add_dictionary_value
        
        value_data = {
            "label": dictionary_in.dict_label,
            "value": dictionary_in.dict_value,
            "code": dictionary_in.dict_code,
            "sort_order": dictionary_in.sort_order,
            "is_active": dictionary_in.is_active
        }
        
        result = await add_dictionary_value(dictionary_in.dict_type, value_data, db)
        
        return {
            "id": f"{dictionary_in.dict_type}_{dictionary_in.dict_value}",
            "message": "字典项创建成功",
            "dict_type": dictionary_in.dict_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建系统字典失败: {str(e)}")


@router.get("/migration-status")
async def get_migration_status(db: Session = Depends(get_db)):
    """
    获取迁移状态
    """
    try:
        # 检查是否还有系统字典数据
        system_dict_count = db.query(SystemDictionary).count()
        
        # 检查枚举字段数据
        from ...models.enum_field import EnumFieldType
        enum_type_count = db.query(EnumFieldType).filter(
            EnumFieldType.category == "系统字典迁移"
        ).count()
        
        return {
            "system_dictionary_count": system_dict_count,
            "migrated_enum_types": enum_type_count,
            "migration_completed": system_dict_count == 0 and enum_type_count > 0,
            "recommendation": "建议运行迁移脚本完成数据迁移" if system_dict_count > 0 else "迁移已完成"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取迁移状态失败: {str(e)}")


@router.post("/migrate")
async def trigger_migration(db: Session = Depends(get_db)):
    """
    触发数据迁移
    """
    try:
        # 这里可以调用迁移脚本的函数
        # 为了简化，返回提示信息
        return {
            "message": "请运行 python scripts/migrate_dictionaries.py 完成数据迁移",
            "status": "pending"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发迁移失败: {str(e)}")