"""
系统字典管理 API 路由
"""

from typing import Any

from fastapi import APIRouter, Depends, Path, Query
from fastapi.params import Depends as DependsParam
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import BaseBusinessError, internal_error, not_found
from ....database import get_async_db
from ....middleware.auth import require_admin
from ....models.auth import User
from ....schemas.asset import (
    SystemDictionaryCreate,
    SystemDictionaryResponse,
    SystemDictionaryUpdate,
)
from ....services.system_dictionary import (
    SystemDictionaryService,
    get_system_dictionary_service,
)

router = APIRouter()


def _resolve_service(
    service: SystemDictionaryService | Any,
) -> SystemDictionaryService | Any:
    if isinstance(service, DependsParam):
        return get_system_dictionary_service()
    return service


@router.get(
    "/", response_model=list[SystemDictionaryResponse], summary="获取系统字典列表"
)
async def get_system_dictionaries(
    dict_type: str | None = Query(None, description="字典类型筛选"),
    is_active: bool | None = Query(None, description="是否启用筛选"),
    db: AsyncSession = Depends(get_async_db),
    service: SystemDictionaryService = Depends(get_system_dictionary_service),
) -> list[SystemDictionaryResponse]:
    try:
        resolved_service = _resolve_service(service)
        dictionaries = await resolved_service.get_dictionaries_async(
            db=db,
            dict_type=dict_type,
            is_active=is_active,
        )
        return [SystemDictionaryResponse.model_validate(d) for d in dictionaries]
    except Exception as e:
        raise internal_error(f"获取系统字典列表失败: {str(e)}")


@router.get(
    "/{dictionary_id}",
    response_model=SystemDictionaryResponse,
    summary="获取系统字典详情",
)
async def get_system_dictionary(
    dictionary_id: str = Path(..., description="字典ID"),
    db: AsyncSession = Depends(get_async_db),
    service: SystemDictionaryService = Depends(get_system_dictionary_service),
) -> SystemDictionaryResponse:
    try:
        resolved_service = _resolve_service(service)
        dictionary = await resolved_service.get_dictionary_async(
            db=db,
            id=dictionary_id,
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
    dictionary_in: SystemDictionaryCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    service: SystemDictionaryService = Depends(get_system_dictionary_service),
) -> SystemDictionaryResponse:
    try:
        _ = current_user
        resolved_service = _resolve_service(service)
        dictionary = await resolved_service.create_dictionary_async(
            db=db, obj_in=dictionary_in
        )
        return SystemDictionaryResponse.model_validate(dictionary)
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
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    service: SystemDictionaryService = Depends(get_system_dictionary_service),
) -> SystemDictionaryResponse:
    try:
        _ = current_user
        resolved_service = _resolve_service(service)
        updated_dictionary = await resolved_service.update_dictionary_async(
            db=db, id=dictionary_id, obj_in=dictionary_in
        )
        return SystemDictionaryResponse.model_validate(updated_dictionary)
    except Exception as e:
        if isinstance(e, BaseBusinessError):
            raise
        raise internal_error(f"更新系统字典失败: {str(e)}")


@router.delete("/{dictionary_id}", summary="删除系统字典")
async def delete_system_dictionary(
    dictionary_id: str = Path(..., description="字典ID"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    service: SystemDictionaryService = Depends(get_system_dictionary_service),
) -> dict[str, str]:
    try:
        _ = current_user
        resolved_service = _resolve_service(service)
        await resolved_service.delete_dictionary_async(db=db, id=dictionary_id)
        return {"message": f"字典 {dictionary_id} 已成功删除"}
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
    updates: list[dict[str, Any]],
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(require_admin),
    service: SystemDictionaryService = Depends(get_system_dictionary_service),
) -> list[SystemDictionaryResponse]:
    try:
        _ = current_user
        resolved_service = _resolve_service(service)
        updated_dictionaries: list[SystemDictionaryResponse] = []
        for update in updates:
            dictionary_id = update.get("id")
            update_data = update.get("data", {})
            if not dictionary_id:
                continue
            try:
                updated = await resolved_service.update_dictionary_async(
                    db=db,
                    id=dictionary_id,
                    obj_in=SystemDictionaryUpdate(**update_data),
                )
                updated_dictionaries.append(
                    SystemDictionaryResponse.model_validate(updated)
                )
            except BaseBusinessError:
                continue
        return updated_dictionaries
    except Exception as e:
        raise internal_error(f"批量更新系统字典失败: {str(e)}")


@router.get("/types/list", summary="获取字典类型列表")
async def get_dictionary_types(
    db: AsyncSession = Depends(get_async_db),
    service: SystemDictionaryService = Depends(get_system_dictionary_service),
) -> dict[str, list[str]]:
    try:
        resolved_service = _resolve_service(service)
        types = await resolved_service.get_types_async(db=db)
        return {"types": types}
    except Exception as e:
        raise internal_error(f"获取字典类型失败: {str(e)}")
