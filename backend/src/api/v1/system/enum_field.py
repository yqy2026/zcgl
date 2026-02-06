"""
枚举字段管理API路由
"""

from typing import Any

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from ....constants.message_constants import EMPTY_STRING
from ....core.exception_handler import bad_request, conflict, not_found
from ....crud.enum_field import (
    get_enum_field_history_crud,
    get_enum_field_type_crud,
    get_enum_field_usage_crud,
    get_enum_field_value_crud,
)
from ....database import get_async_db
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

router = APIRouter(prefix="/enum-fields", tags=["枚举字段管理"])


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
) -> list[EnumFieldTypeResponse]:
    """获取枚举字段类型列表"""
    # 显式处理Query参数，确保传递实际值而不是Query对象
    # 这解决了FastAPI Query(None)对象没有正确转换为None值的问题

    # 确保Query对象被正确转换为实际值
    # 处理可能的Query对象问题
    actual_skip = (page - 1) * page_size
    actual_limit = page_size

    # 对于Optional参数，确保None值被正确传递
    actual_category = (
        str(category) if category is not None and category != EMPTY_STRING else None
    )
    actual_status = (
        str(status) if status is not None and status != EMPTY_STRING else None
    )
    actual_keyword = (
        str(keyword) if keyword is not None and keyword != EMPTY_STRING else None
    )

    # 对于布尔值，需要特殊处理
    actual_is_system = None
    if is_system is not None:
        try:
            actual_is_system = bool(is_system)
        except (ValueError, TypeError):
            actual_is_system = None

    crud = get_enum_field_type_crud(db)
    enum_types = await crud.get_multi_async(
        db,
        skip=actual_skip,
        limit=actual_limit,
        category=actual_category,
        status=actual_status,
        is_system=actual_is_system,
        keyword=actual_keyword,
    )
    for enum_type in enum_types:
        _strip_enum_children(getattr(enum_type, "enum_values", None))
    return [EnumFieldTypeResponse.model_validate(enum_type) for enum_type in enum_types]


@router.get("/types/statistics", response_model=EnumFieldStatistics)
async def get_enum_field_statistics(
    db: AsyncSession = Depends(get_async_db),
) -> EnumFieldStatistics:
    """获取枚举字段统计信息"""

    type_crud = get_enum_field_type_crud(db)
    value_crud = get_enum_field_value_crud(db)
    usage_crud = get_enum_field_usage_crud(db)

    type_stats = await type_crud.get_statistics_async(db)

    total_values = await value_crud.count_all_async(db)
    active_values = await value_crud.count_active_async(db)

    usage_count = await usage_crud.count_active_async(db)

    return EnumFieldStatistics(
        total_types=type_stats["total_types"],
        active_types=type_stats["active_types"],
        total_values=total_values,
        active_values=active_values,
        usage_count=usage_count,
        categories=type_stats["categories"],
    )


@router.get("/types/{type_id}", response_model=EnumFieldTypeResponse)
async def get_enum_field_type(
    type_id: str = Path(..., description="枚举类型ID"),
    db: AsyncSession = Depends(get_async_db),
) -> EnumFieldTypeResponse:
    """根据ID获取枚举字段类型详情"""

    crud = get_enum_field_type_crud(db)
    enum_type = await crud.get_async(db, type_id)
    if not enum_type:
        raise not_found("枚举类型不存在", resource_type="enum_type", resource_id=type_id)
    _strip_enum_children(getattr(enum_type, "enum_values", None))
    return EnumFieldTypeResponse.model_validate(enum_type)


@router.post("/types", response_model=EnumFieldTypeResponse)
async def create_enum_field_type(
    enum_type: EnumFieldTypeCreate, db: AsyncSession = Depends(get_async_db)
) -> EnumFieldTypeResponse:
    """创建枚举字段类型"""

    crud = get_enum_field_type_crud(db)

    existing = await crud.get_by_code_async(db, enum_type.code)
    if existing:
        raise conflict(f"编码 {enum_type.code} 已存在", resource_type="enum_type")

    try:
        db_enum_type = await crud.create_async(db, enum_type)
        return EnumFieldTypeResponse.model_validate(db_enum_type)
    except ValueError as e:
        raise bad_request(str(e))


@router.put("/types/{type_id}", response_model=EnumFieldTypeResponse)
async def update_enum_field_type(
    type_id: str,
    enum_type: EnumFieldTypeUpdate,
    db: AsyncSession = Depends(get_async_db),
) -> EnumFieldTypeResponse:
    """更新枚举字段类型"""

    crud = get_enum_field_type_crud(db)

    db_enum_type = await crud.get_async(db, type_id)
    if not db_enum_type:
        raise not_found("枚举类型不存在", resource_type="enum_type", resource_id=type_id)

    if enum_type.code and enum_type.code != db_enum_type.code:
        existing = await crud.get_by_code_async(db, enum_type.code)
        if existing and existing.id != type_id:
            raise conflict(f"编码 {enum_type.code} 已存在", resource_type="enum_type")

    try:
        updated_enum_type = await crud.update_async(db, db_enum_type, enum_type)
        return EnumFieldTypeResponse.model_validate(updated_enum_type)
    except ValueError as e:
        raise bad_request(str(e))


@router.delete("/types/{type_id}")
async def delete_enum_field_type(
    type_id: str,
    deleted_by: str | None = Query(None, description="删除人"),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """删除枚举字段类型"""

    crud = get_enum_field_type_crud(db)

    try:
        success = await crud.delete_async(db, type_id, deleted_by=deleted_by)
        if not success:
            raise not_found("枚举类型不存在", resource_type="enum_type", resource_id=type_id)
        return {"message": "枚举类型删除成功"}
    except ValueError as e:
        raise bad_request(str(e))


@router.get("/types/categories/list[Any]")
async def get_enum_field_categories(
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, list[str]]:
    """获取枚举字段类别列表"""

    crud = get_enum_field_type_crud(db)
    categories = await crud.get_categories_async(db)
    return {"categories": categories}


@router.get("/types/{type_id}/values", response_model=list[EnumFieldValueResponse])
async def get_enum_field_values(
    type_id: str,
    parent_id: str | None = Query(None, description="父级枚举值ID"),
    is_active: bool | None = Query(None, description="是否启用"),
    db: AsyncSession = Depends(get_async_db),
) -> list[EnumFieldValueResponse]:
    """获取枚举字段值列表"""

    crud = get_enum_field_value_crud(db)
    enum_values = await crud.get_by_type_async(
        db, type_id, parent_id=parent_id, is_active=is_active
    )
    _strip_enum_children(enum_values)
    return [EnumFieldValueResponse.model_validate(value) for value in enum_values]


@router.get("/types/{type_id}/values/tree", response_model=list[EnumFieldTree])
async def get_enum_field_values_tree(
    type_id: str, db: AsyncSession = Depends(get_async_db)
) -> list[EnumFieldTree]:
    """获取枚举字段值树形结构"""

    crud = get_enum_field_value_crud(db)

    def build_tree_response(values: list[Any]) -> list[EnumFieldTree]:
        tree: list[EnumFieldTree] = []
        for value in values:
            children = build_tree_response(getattr(value, "children", []))
            tree_node = EnumFieldTree(
                id=value.id,
                label=value.label,
                value=value.value,
                code=value.code,
                level=value.level,
                sort_order=value.sort_order,
                is_active=value.is_active,
                color=value.color,
                icon=value.icon,
                children=children,
            )
            tree.append(tree_node)
        return tree

    tree_values = await crud.get_tree_async(db, type_id)
    return build_tree_response(tree_values)


@router.get("/values/{value_id}", response_model=EnumFieldValueResponse)
async def get_enum_field_value(
    value_id: str = Path(..., description="枚举值ID"),
    db: AsyncSession = Depends(get_async_db),
) -> EnumFieldValueResponse:
    """根据ID获取枚举字段值详情"""

    crud = get_enum_field_value_crud(db)
    enum_value = await crud.get_async(db, value_id)
    if not enum_value:
        raise not_found("枚举值不存在", resource_type="enum_value", resource_id=value_id)
    _strip_enum_children([enum_value])
    return EnumFieldValueResponse.model_validate(enum_value)


@router.post("/types/{type_id}/values", response_model=EnumFieldValueResponse)
async def create_enum_field_value(
    type_id: str,
    enum_value: EnumFieldValueCreate,
    db: AsyncSession = Depends(get_async_db),
) -> EnumFieldValueResponse:
    """创建枚举字段值"""

    crud = get_enum_field_value_crud(db)

    type_crud = get_enum_field_type_crud(db)
    enum_type = await type_crud.get_async(db, type_id)
    if not enum_type:
        raise not_found("枚举类型不存在", resource_type="enum_type", resource_id=type_id)

    existing = await crud.get_by_type_and_value_async(db, type_id, enum_value.value)
    if existing:
        raise conflict(f"值 {enum_value.value} 已存在", resource_type="enum_value")

    enum_value.enum_type_id = type_id

    try:
        db_enum_value = await crud.create_async(db, enum_value)
        return EnumFieldValueResponse.model_validate(db_enum_value)
    except ValueError as e:
        raise bad_request(str(e))


@router.put("/values/{value_id}", response_model=EnumFieldValueResponse)
async def update_enum_field_value(
    value_id: str,
    enum_value: EnumFieldValueUpdate,
    db: AsyncSession = Depends(get_async_db),
) -> EnumFieldValueResponse:
    """更新枚举字段值"""

    crud = get_enum_field_value_crud(db)

    db_enum_value = await crud.get_async(db, value_id)
    if not db_enum_value:
        raise not_found("枚举值不存在", resource_type="enum_value", resource_id=value_id)

    if enum_value.value and enum_value.value != db_enum_value.value:
        existing = await crud.get_by_type_and_value_async(
            db, getattr(db_enum_value, "enum_type_id", ""), enum_value.value
        )
        if existing and existing.id != value_id:
            raise conflict(f"值 {enum_value.value} 已存在", resource_type="enum_value")

    try:
        updated_enum_value = await crud.update_async(db, db_enum_value, enum_value)
        return EnumFieldValueResponse.model_validate(updated_enum_value)
    except ValueError as e:
        raise bad_request(str(e))


@router.delete("/values/{value_id}")
async def delete_enum_field_value(
    value_id: str,
    deleted_by: str | None = Query(None, description="删除人"),
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """删除枚举字段值"""

    crud = get_enum_field_value_crud(db)

    try:
        success = await crud.delete_async(db, value_id, deleted_by=deleted_by)
        if not success:
            raise not_found("枚举值不存在", resource_type="enum_value", resource_id=value_id)
        return {"message": "枚举值删除成功"}
    except ValueError as e:
        raise bad_request(str(e))


@router.post(
    "/types/{type_id}/values/batch", response_model=list[EnumFieldValueResponse]
)
async def batch_create_enum_field_values(
    type_id: str,
    batch_data: EnumFieldBatchCreate,
    db: AsyncSession = Depends(get_async_db),
) -> list[EnumFieldValueResponse]:
    """批量创建枚举字段值"""

    crud = get_enum_field_value_crud(db)

    type_crud = get_enum_field_type_crud(db)
    enum_type = await type_crud.get_async(db, type_id)
    if not enum_type:
        raise not_found("枚举类型不存在", resource_type="enum_type", resource_id=type_id)

    try:
        created_values = await crud.batch_create_async(
            db, type_id, batch_data.values, batch_data.created_by
        )
        return [
            EnumFieldValueResponse.model_validate(value) for value in created_values
        ]
    except ValueError as e:
        raise bad_request(str(e))


@router.get("/usage", response_model=list[EnumFieldUsageResponse])
async def get_enum_field_usage(
    enum_type_id: str | None = Query(None, description="枚举类型ID"),
    table_name: str | None = Query(None, description="表名"),
    module_name: str | None = Query(None, description="模块名"),
    db: AsyncSession = Depends(get_async_db),
) -> list[EnumFieldUsageResponse]:
    """获取枚举字段使用记录"""

    crud = get_enum_field_usage_crud(db)
    usage_records = (
        await crud.get_by_enum_type_async(db, enum_type_id) if enum_type_id else []
    )
    return [EnumFieldUsageResponse.model_validate(usage) for usage in usage_records]


@router.post("/usage", response_model=EnumFieldUsageResponse)
async def create_enum_field_usage(
    usage: EnumFieldUsageCreate, db: AsyncSession = Depends(get_async_db)
) -> EnumFieldUsageResponse:
    """创建枚举字段使用记录"""

    crud = get_enum_field_usage_crud(db)

    existing = await crud.get_by_field_async(db, usage.table_name, usage.field_name)
    if existing:
        raise conflict(
            f"表 {usage.table_name} 的字段 {usage.field_name} 已存在使用记录",
            resource_type="enum_usage",
        )

    db_usage = await crud.create_async(db, usage)
    return EnumFieldUsageResponse.model_validate(db_usage)


@router.put("/usage/{usage_id}", response_model=EnumFieldUsageResponse)
async def update_enum_field_usage(
    usage_id: str, usage: EnumFieldUsageUpdate, db: AsyncSession = Depends(get_async_db)
) -> EnumFieldUsageResponse:
    """更新枚举字段使用记录"""

    crud = get_enum_field_usage_crud(db)

    db_usage = await crud.get_async(db, usage_id)
    if not db_usage:
        raise not_found("使用记录不存在", resource_type="enum_usage", resource_id=usage_id)

    updated_usage = await crud.update_async(db, db_usage, usage)
    return EnumFieldUsageResponse.model_validate(updated_usage)


@router.delete("/usage/{usage_id}")
async def delete_enum_field_usage(
    usage_id: str, db: AsyncSession = Depends(get_async_db)
) -> dict[str, str]:
    """删除枚举字段使用记录"""

    crud = get_enum_field_usage_crud(db)

    success = await crud.delete_async(db, usage_id)
    if not success:
        raise not_found("使用记录不存在", resource_type="enum_usage", resource_id=usage_id)
    return {"message": "使用记录删除成功"}


@router.get("/types/{type_id}/history", response_model=list[EnumFieldHistoryResponse])
async def get_enum_field_type_history(
    type_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=1000, description="每页记录数"),
    db: AsyncSession = Depends(get_async_db),
) -> list[EnumFieldHistoryResponse]:
    """获取枚举字段类型变更历史"""

    skip = (page - 1) * page_size
    history_crud = get_enum_field_history_crud(db)
    history_records = await history_crud.get_multi_async(
        db, enum_type_id=type_id, skip=skip, limit=page_size
    )

    return [
        EnumFieldHistoryResponse.model_validate(history) for history in history_records
    ]


@router.get("/values/{value_id}/history", response_model=list[EnumFieldHistoryResponse])
async def get_enum_field_value_history(
    value_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=1000, description="每页记录数"),
    db: AsyncSession = Depends(get_async_db),
) -> list[EnumFieldHistoryResponse]:
    """获取枚举字段值变更历史"""

    skip = (page - 1) * page_size
    history_crud = get_enum_field_history_crud(db)
    history_records = await history_crud.get_multi_async(
        db, enum_value_id=value_id, skip=skip, limit=page_size
    )

    return [
        EnumFieldHistoryResponse.model_validate(history) for history in history_records
    ]
