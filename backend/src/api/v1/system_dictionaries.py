"""
系统字典管理API路由
"""


from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from ...crud.system_dictionary import system_dictionary_crud
from ...database import get_db
from ...schemas.asset import (
    SystemDictionaryCreate,
    SystemDictionaryResponse,
    SystemDictionaryUpdate,
)

# 创建系统字典路由器
router = APIRouter()


@router.get(
    "/", response_model=list[SystemDictionaryResponse], summary="获取系统字典列表"
)
async def get_system_dictionaries(
    dict_type: str | None = Query(None, description="字典类型筛选"),
    is_active: bool | None = Query(None, description="是否启用筛选"),
    db: Session = Depends(get_db),
):
    """
    获取系统字典列表，支持按类型和状态筛选

    - **dict_type**: 字典类型
    - **is_active**: 是否启用
    """
    try:
        filters = {}
        if dict_type:
            filters["dict_type"] = dict_type
        if is_active is not None:
            filters["is_active"] = is_active

        dictionaries = system_dictionary_crud.get_multi_with_filters(
            db=db, filters=filters
        )
        return dictionaries

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统字典列表失败: {str(e)}")


@router.get(
    "/{dictionary_id}",
    response_model=SystemDictionaryResponse,
    summary="获取系统字典详情",
)
async def get_system_dictionary(
    dictionary_id: str = Path(..., description="字典ID"), db: Session = Depends(get_db)
):
    """
    根据ID获取单个系统字典的详细信息

    - **dictionary_id**: 字典ID
    """
    try:
        dictionary = system_dictionary_crud.get(db=db, id=dictionary_id)
        if not dictionary:
            raise HTTPException(status_code=404, detail=f"字典 {dictionary_id} 不存在")
        return dictionary

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统字典详情失败: {str(e)}")


@router.post(
    "/",
    response_model=SystemDictionaryResponse,
    summary="创建系统字典",
    status_code=201,
)
async def create_system_dictionary(
    dictionary_in: SystemDictionaryCreate, db: Session = Depends(get_db)
):
    """
    创建新的系统字典项

    - **dictionary_in**: 字典创建数据
    """
    try:
        # 检查是否存在相同的类型和代码
        existing = system_dictionary_crud.get_by_type_and_code(
            db=db, dict_type=dictionary_in.dict_type, dict_code=dictionary_in.dict_code
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"类型 {dictionary_in.dict_type} 中已存在代码 {dictionary_in.dict_code}",
            )

        dictionary = system_dictionary_crud.create(db=db, obj_in=dictionary_in)
        return dictionary

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建系统字典失败: {str(e)}")


@router.put(
    "/{dictionary_id}", response_model=SystemDictionaryResponse, summary="更新系统字典"
)
async def update_system_dictionary(
    dictionary_in: SystemDictionaryUpdate,
    dictionary_id: str = Path(..., description="字典ID"),
    db: Session = Depends(get_db),
):
    """
    更新系统字典信息

    - **dictionary_id**: 字典ID
    - **dictionary_in**: 字典更新数据
    """
    try:
        # 检查字典是否存在
        dictionary = system_dictionary_crud.get(db=db, id=dictionary_id)
        if not dictionary:
            raise HTTPException(status_code=404, detail=f"字典 {dictionary_id} 不存在")

        # 如果更新了类型或代码，检查是否重复
        if (
            dictionary_in.dict_type and dictionary_in.dict_type != dictionary.dict_type
        ) or (
            dictionary_in.dict_code and dictionary_in.dict_code != dictionary.dict_code
        ):
            dict_type = dictionary_in.dict_type or dictionary.dict_type
            dict_code = dictionary_in.dict_code or dictionary.dict_code
            existing = system_dictionary_crud.get_by_type_and_code(
                db=db, dict_type=dict_type, dict_code=dict_code
            )
            if existing and existing.id != dictionary_id:
                raise HTTPException(
                    status_code=400, detail=f"类型 {dict_type} 中已存在代码 {dict_code}"
                )

        updated_dictionary = system_dictionary_crud.update(
            db=db, db_obj=dictionary, obj_in=dictionary_in
        )
        return updated_dictionary

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新系统字典失败: {str(e)}")


@router.delete("/{dictionary_id}", summary="删除系统字典")
async def delete_system_dictionary(
    dictionary_id: str = Path(..., description="字典ID"), db: Session = Depends(get_db)
):
    """
    删除系统字典项

    - **dictionary_id**: 字典ID
    """
    try:
        # 检查字典是否存在
        dictionary = system_dictionary_crud.get(db=db, id=dictionary_id)
        if not dictionary:
            raise HTTPException(status_code=404, detail=f"字典 {dictionary_id} 不存在")

        # 删除字典
        system_dictionary_crud.remove(db=db, id=dictionary_id)
        return {"message": f"字典 {dictionary_id} 已成功删除"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除系统字典失败: {str(e)}")


@router.post(
    "/batch-update",
    response_model=list[SystemDictionaryResponse],
    summary="批量更新系统字典",
)
async def batch_update_system_dictionaries(
    updates: list[dict], db: Session = Depends(get_db)
):
    """
    批量更新系统字典

    - **updates**: 更新数据列表，格式: [{"id": "xxx", "data": {...}}]
    """
    try:
        updated_dictionaries = []

        for update in updates:
            dictionary_id = update.get("id")
            update_data = update.get("data", {})

            if not dictionary_id:
                continue

            dictionary = system_dictionary_crud.get(db=db, id=dictionary_id)
            if not dictionary:
                continue

            updated_dictionary = system_dictionary_crud.update(
                db=db, db_obj=dictionary, obj_in=SystemDictionaryUpdate(**update_data)
            )
            updated_dictionaries.append(updated_dictionary)

        return updated_dictionaries

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量更新系统字典失败: {str(e)}")


@router.get("/types/list", summary="获取字典类型列表")
async def get_dictionary_types(db: Session = Depends(get_db)):
    """
    获取所有字典类型列表
    """
    try:
        types = system_dictionary_crud.get_types(db=db)
        return {"types": types}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取字典类型失败: {str(e)}")
