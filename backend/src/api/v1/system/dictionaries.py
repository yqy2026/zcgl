"""
统一的字典管理API
整合系统字典和枚举字段功能，提供简化的使用接口

重构说明：
- API 层只负责路由转发和参数验证
- 所有业务逻辑已下沉至 Service 层
- 使用类型安全的 Schema 替代 dict[str, Any]
- 操作人信息从当前用户获取，不再硬编码
"""

import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, Path, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....database import get_async_db
from ....middleware.auth import get_current_active_user
from ....models.auth import User
from ....schemas.dictionary import (
    DictionaryOptionResponse,
    DictionaryValueCreate,
    SimpleDictionaryCreate,
)
from ....services.common_dictionary_service import common_dictionary_service
from ..utils import handle_api_errors

# 创建logger
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/system/dictionaries",
    tags=["统一字典管理"],
    dependencies=[Depends(get_current_active_user)],
)


@router.get("/{dict_type}/options", response_model=list[DictionaryOptionResponse])
@handle_api_errors
async def get_dictionary_options(
    dict_type: str = Path(..., description="字典类型"),
    is_active: bool = Query(True, description="是否只返回启用的选项"),
    db: AsyncSession = Depends(get_async_db),
) -> list[DictionaryOptionResponse]:
    """
    获取字典选项（统一接口）
    支持从枚举字段和系统字典两个来源获取数据

    重构：业务逻辑已下沉至 Service 层
    """

    return await common_dictionary_service.get_combined_options_async(
        db, dict_type, is_active
    )


@router.post("/{dict_type}/quick-create")
@handle_api_errors
async def quick_create_dictionary(
    dict_type: str = Path(..., description="字典类型"),
    dictionary_data: SimpleDictionaryCreate = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """
    快速创建字典（兼容原系统字典功能）
    自动创建枚举类型和枚举值

    重构：
    - 业务逻辑已下沉至 Service 层
    - 操作人从当前用户获取，不再硬编码
    - 使用类型安全的 Schema
    """

    operator = getattr(current_user, "full_name", None)
    if not isinstance(operator, str) or not operator:
        operator = "系统"
    result = await common_dictionary_service.quick_create_enum_dictionary_async(
        db, dict_type, dictionary_data, operator=operator
    )
    return JSONResponse(status_code=200, content=result)


@router.get("/types", response_model=list[str])
@handle_api_errors
async def get_dictionary_types(db: AsyncSession = Depends(get_async_db)) -> list[str]:
    """
    获取所有字典类型列表

    注意：已废弃旧的system_dictionaries表，统一使用enum_field表
    """

    return await common_dictionary_service.get_all_dictionary_types_async(db)


@router.get("/validation/stats", summary="获取枚举验证统计信息")
@handle_api_errors
async def get_validation_statistics(
    enum_type: str | None = Query(None, description="枚举类型编码（可选）"),
    db: AsyncSession = Depends(get_async_db),
) -> JSONResponse:
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

    from ....services.enum_validation_service import get_enum_validation_service_async

    enum_service = get_enum_validation_service_async(db)
    stats = enum_service.get_validation_stats(enum_type)

    result: dict[str, dict[str, Any]] = {}
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

    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "data": result,
            "total_enum_types": len(result),
        },
    )


@router.post("/{dict_type}/values")
@handle_api_errors
async def add_dictionary_value(
    dict_type: str = Path(..., description="字典类型"),
    value_data: DictionaryValueCreate = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """
    为指定字典类型添加新的选项值

    重构：
    - 业务逻辑已下沉至 Service 层
    - 使用类型安全的 Schema
    - 操作人从当前用户获取
    """

    operator = getattr(current_user, "full_name", None)
    if not isinstance(operator, str) or not operator:
        operator = "系统"
    result = await common_dictionary_service.add_dictionary_value_async(
        db, dict_type, value_data, operator=operator
    )
    return JSONResponse(status_code=200, content=result)


@router.delete("/{dict_type}")
@handle_api_errors
async def delete_dictionary_type(
    dict_type: str = Path(..., description="字典类型"),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    """
    删除字典类型及其所有值

    重构：业务逻辑已下沉至 Service 层
    """

    operator = getattr(current_user, "full_name", None)
    if not isinstance(operator, str) or not operator:
        operator = "系统"
    result = await common_dictionary_service.delete_dictionary_type_async(
        db, dict_type, operator=operator
    )
    return JSONResponse(status_code=200, content=result)
