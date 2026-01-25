"""
系统字典管理API路由
"""

from typing import Any

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from ...core.exception_handler import (
    BaseBusinessError,
    bad_request,
    internal_error,
    not_found,
)
from ...crud.system_dictionary import system_dictionary_crud
from ...database import get_db
from ...schemas.asset import (
    SystemDictionaryCreate,
    SystemDictionaryResponse,
    SystemDictionaryUpdate,
)
from ...services.system_dictionary import system_dictionary_service

# 创建系统字典路由器
router = APIRouter()


@router.get(
    "/", response_model=list[SystemDictionaryResponse], summary="获取系统字典列表"
)
async def get_system_dictionaries(
    dict_type: str | None = Query(None, description="字典类型筛选"),
    is_active: bool | None = Query(None, description="是否启用筛选"),
    db: Session = Depends(get_db),
) -> list[SystemDictionaryResponse]:
    """
    获取系统字典列表，支持按类型和状态筛选

    - **dict_type**: 字典类型
    - **is_active**: 是否启用
    """
    try:
        filters: dict[str, Any] = {}
        if dict_type:
            filters["dict_type"] = dict_type
        if is_active is not None:
            filters["is_active"] = is_active

        # FastAPI will convert SystemDictionary to SystemDictionaryResponse via response_model
        dictionaries = system_dictionary_crud.get_multi_with_filters(
            db=db, filters=filters
        )
        # Use explicit conversion to satisfy mypy's invariance check
        return [SystemDictionaryResponse.model_validate(d) for d in dictionaries]

    except Exception as e:
        raise internal_error(f"获取系统字典列表失败: {str(e)}")


@router.get(
    "/{dictionary_id}",
    response_model=SystemDictionaryResponse,
    summary="获取系统字典详情",
)
async def get_system_dictionary(
    dictionary_id: str = Path(..., description="字典ID"), db: Session = Depends(get_db)
) -> SystemDictionaryResponse:
    """
    根据ID获取单个系统字典的详细信息

    - **dictionary_id**: 字典ID
    """
    try:
        from ...models.asset import SystemDictionary

        dictionary: SystemDictionary | None = system_dictionary_crud.get(
            db=db, id=dictionary_id
        )
        if not dictionary:
            raise not_found(
                f"字典 {dictionary_id} 不存在",
                resource_type="system_dictionary",
                resource_id=dictionary_id,
            )
        return SystemDictionaryResponse.model_validate(dictionary)

    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"获取系统字典详情失败: {str(e)}")


@router.post(
    "/",
    response_model=SystemDictionaryResponse,
    summary="创建系统字典",
    status_code=201,
)
async def create_system_dictionary(
    dictionary_in: SystemDictionaryCreate, db: Session = Depends(get_db)
) -> SystemDictionaryResponse:
    """
    创建新的系统字典项

    - **dictionary_in**: 字典创建数据
    """
    try:
        dictionary = system_dictionary_service.create_dictionary(
            db=db, obj_in=dictionary_in
        )
        return SystemDictionaryResponse.model_validate(dictionary)

    except ValueError as e:
        raise bad_request(str(e))
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"创建系统字典失败: {str(e)}")


@router.put(
    "/{dictionary_id}", response_model=SystemDictionaryResponse, summary="更新系统字典"
)
async def update_system_dictionary(
    dictionary_in: SystemDictionaryUpdate,
    dictionary_id: str = Path(..., description="字典ID"),
    db: Session = Depends(get_db),
) -> SystemDictionaryResponse:
    """
    更新系统字典信息

    - **dictionary_id**: 字典ID
    - **dictionary_in**: 字典更新数据
    """
    try:
        updated_dictionary = system_dictionary_service.update_dictionary(
            db=db, id=dictionary_id, obj_in=dictionary_in
        )
        return SystemDictionaryResponse.model_validate(updated_dictionary)

    except ValueError as e:
        if "不存在" in str(e):
            raise not_found(str(e), resource_type="system_dictionary")
        raise bad_request(str(e))
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"更新系统字典失败: {str(e)}")


@router.delete("/{dictionary_id}", summary="删除系统字典")
async def delete_system_dictionary(
    dictionary_id: str = Path(..., description="字典ID"), db: Session = Depends(get_db)
) -> dict[str, str]:
    """
    删除系统字典项

    - **dictionary_id**: 字典ID
    """
    try:
        system_dictionary_service.delete_dictionary(db=db, id=dictionary_id)
        return {"message": f"字典 {dictionary_id} 已成功删除"}

    except ValueError as e:
        raise not_found(
            str(e), resource_type="system_dictionary", resource_id=dictionary_id
        )
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"删除系统字典失败: {str(e)}")


@router.post(
    "/batch-update",
    response_model=list[SystemDictionaryResponse],
    summary="批量更新系统字典",
)
async def batch_update_system_dictionaries(
    updates: list[dict[str, Any]], db: Session = Depends(get_db)
) -> list[SystemDictionaryResponse]:
    """
    批量更新系统字典

    - **updates**: 更新数据列表，格式: [{"id": "xxx", "data": {...}}]
    - 注意：此端点原逻辑是混合更新，现在主要用于排序。
    - 如果需要通用批量更新，应该拆分或明确用途。
    - 原有系统似乎用于排序：`update_sort_orders` in CRUD was specific.
    - 但 `system_dictionaries.py` line 186-213 was generic update.
    - Let's keep it generic using service loop or specific batch method if needed.
    - If strictly existing logic: it was looping and updating.
    - I can forward to a loop in Service or keep loop here calling update.
    """
    try:
        updated_dictionaries: list[SystemDictionaryResponse] = []

        for update in updates:
            dictionary_id = update.get("id")
            update_data = update.get("data", {})

            if not dictionary_id:
                continue

            # Calling service update for each
            try:
                updated = system_dictionary_service.update_dictionary(
                    db=db,
                    id=dictionary_id,
                    obj_in=SystemDictionaryUpdate(**update_data),
                )
                updated_dictionaries.append(
                    SystemDictionaryResponse.model_validate(updated)
                )
            except ValueError:
                continue

        return updated_dictionaries

    except Exception as e:
        raise internal_error(f"批量更新系统字典失败: {str(e)}")


@router.get("/types/list[Any]", summary="获取字典类型列表")
async def get_dictionary_types(db: Session = Depends(get_db)) -> dict[str, list[str]]:
    """
    获取所有字典类型列表
    """
    try:
        types = system_dictionary_crud.get_types(db=db)
        return {"types": types}

    except Exception as e:
        raise internal_error(f"获取字典类型失败: {str(e)}")
