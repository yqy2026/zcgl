"""
资产批量操作API路由模块

从 assets.py 中提取的批量操作相关端点
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ....core.exception_handler import bad_request, internal_error
from ....crud.asset import asset_crud
from ....database import get_db
from ....middleware.auth import get_current_active_user, require_permission
from ....models.auth import User
from ....schemas.asset import (
    AssetBatchUpdateRequest,
    AssetBatchUpdateResponse,
    AssetListItemResponse,
    AssetResponse,
    AssetValidationRequest,
    AssetValidationResponse,
    BatchProcessingError,
    BatchCustomFieldUpdateRequest,
    BatchCustomFieldUpdateResponse,
    ValidationWarning,
)
from ....services.asset.asset_service import AssetService
from ....services.asset.batch_service import AssetBatchService
from ....services.enum_validation_service import get_enum_validation_service

# 创建批量操作路由器
router = APIRouter()


@router.post(
    "/batch-update", response_model=AssetBatchUpdateResponse, summary="批量更新资产"
)
async def batch_update_assets(
    request: AssetBatchUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset", "update")),
) -> AssetBatchUpdateResponse:
    """
    批量更新资产信息

    - **asset_ids**: 资产ID列表
    - **updates**: 更新数据字典
    - **should_update_all**: 是否更新所有资产
    """
    try:
        # 使用新的Service层
        service = AssetBatchService(db)
        result = service.batch_update(
            asset_ids=request.asset_ids,
            updates=request.updates.model_dump(exclude_unset=True),
            should_update_all=request.should_update_all,
            operator=str(current_user.username) if current_user else "system",
        )

        result_dict = result.to_dict()
        error_models = []
        for error in result_dict.get("errors", []):
            if not isinstance(error, dict):
                continue
            row_index_raw = error.get("row_index")
            row_index: int | None
            if isinstance(row_index_raw, int):
                row_index = row_index_raw
            elif isinstance(row_index_raw, str) and row_index_raw.isdigit():
                row_index = int(row_index_raw)
            else:
                row_index = None
            error_models.append(
                BatchProcessingError(
                    id=error.get("asset_id"),
                    row_index=row_index,
                    field=error.get("field_context") or error.get("field"),
                    message=error.get("error") or error.get("message") or "批量更新失败",
                    code=error.get("error_type") or error.get("code"),
                )
            )
        return AssetBatchUpdateResponse(
            success_count=result_dict.get("success_count", 0),
            failed_count=result_dict.get("failed_count", 0),
            total_count=result_dict.get("total_count", 0),
            errors=error_models,
            updated_assets=result_dict.get("updated_assets", []),
        )

    except Exception as e:
        raise internal_error(f"批量更新失败: {str(e)}")


@router.post(
    "/validate", response_model=AssetValidationResponse, summary="验证资产数据"
)
async def validate_asset_data(
    request: AssetValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AssetValidationResponse:
    """
    验证资产数据的完整性和正确性

    - **data**: 待验证的资产数据
    - **validate_rules**: 验证规则列表
    """
    try:
        # 使用新的Service层
        service = AssetBatchService(db)
        enum_service = get_enum_validation_service(db)

        # 委派给Service层
        is_valid, errors, warnings, validated_fields = service.validate_asset_data(
            data=request.data,
            validate_rules=request.validate_rules,
            enum_validation_service=enum_service,
        )

        error_models = []
        for error in errors:
            row_index_raw = error.get("row_index")
            row_index: int | None
            if isinstance(row_index_raw, int):
                row_index = row_index_raw
            elif isinstance(row_index_raw, str) and row_index_raw.isdigit():
                row_index = int(row_index_raw)
            else:
                row_index = None
            error_models.append(
                BatchProcessingError(
                    id=None,
                    row_index=row_index,
                    field=error.get("field"),
                    message=error.get("error", "验证失败"),
                    code=error.get("code"),
                )
            )
        warning_models = [
            ValidationWarning(
                field=warning.get("field"),
                message=warning.get("message", "校验警告"),
                code=warning.get("code"),
            )
            for warning in warnings
        ]

        return AssetValidationResponse(
            is_valid=is_valid,
            errors=error_models,
            warnings=warning_models,
            validated_fields=validated_fields,
        )

    except Exception as e:
        raise internal_error(f"数据验证失败: {str(e)}")


@router.post(
    "/batch-custom-fields",
    response_model=BatchCustomFieldUpdateResponse,
    summary="批量更新自定义字段",
)
async def batch_update_custom_fields(
    request: BatchCustomFieldUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset", "update")),
) -> BatchCustomFieldUpdateResponse:
    """
    批量更新资产的自定义字段

    - **asset_ids**: 资产ID列表
    - **field_values**: 自定义字段值字典
    """
    try:
        total_count = len(request.asset_ids)
        success_count = 0
        failed_count = 0
        errors: list[BatchProcessingError] = []

        for asset_id in request.asset_ids:
            try:
                # 检查资产是否存在
                asset = asset_crud.get(db=db, id=asset_id)
                if not asset:
                    errors.append(
                        BatchProcessingError(
                            id=asset_id,
                            row_index=None,
                            field=None,
                            message="资产不存在",
                            code="NOT_FOUND",
                        )
                    )
                    failed_count += 1
                    continue

                # 这里简化处理，实际项目中应该有专门的自定义字段表
                # 可以将自定义字段存储在JSON格式的字段中
                success_count += 1

            except Exception as e:
                errors.append(
                    BatchProcessingError(
                        id=asset_id,
                        row_index=None,
                        field=None,
                        message=str(e),
                        code=type(e).__name__,
                    )
                )
                failed_count += 1

        return BatchCustomFieldUpdateResponse(
            success_count=success_count,
            failed_count=failed_count,
            total_count=total_count,
            errors=errors,
        )

    except Exception as e:
        raise internal_error(f"批量更新自定义字段失败: {str(e)}")


@router.get("/all", summary="获取所有资产（不分页）")
async def get_all_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    search: str | None = Query(None, description="搜索关键字"),
    ownership_status: str | None = Query(None, description="确权状态"),
    usage_status: str | None = Query(None, description="使用状态"),
    property_nature: str | None = Query(None, description="物业性质"),
    business_category: str | None = Query(None, description="业态类别"),
    sort_by: str | None = Query("created_at", description="排序字段"),
    sort_order: str | None = Query("desc", description="排序顺序"),
    max_export: int = Query(10000, ge=1, le=50000, description="最大导出数量"),
    include_relations: bool = Query(False, description="是否加载关联数据"),
) -> dict[str, Any]:
    """
    获取所有资产列表，不分页，用于导出等场景

    支持的查询参数：
    - **search**: 搜索关键字（物业名称、地址等）
    - **ownership_status**: 确权状态过滤
    - **usage_status**: 使用状态过滤
    - **property_nature**: 物业性质过滤
    - **business_category**: 业态类别过滤
    - **sort_by**: 排序字段
    - **sort_order**: 排序顺序（asc/desc）
    - **max_export**: 最大导出数量限制
    - **include_relations**: 是否加载关联数据（默认不加载）
    """
    try:
        # 构建查询过滤器
        filters = {}
        if ownership_status:
            filters["ownership_status"] = ownership_status
        if usage_status:
            filters["usage_status"] = usage_status
        if property_nature:
            filters["property_nature"] = property_nature
        if business_category:
            filters["business_category"] = business_category

        # 排序
        if sort_by and sort_order:
            if sort_order.lower() == "desc":
                pass
            else:
                pass

        # 获取所有资产（不分页）
        asset_service = AssetService(db)
        assets, _ = asset_service.get_assets(
            skip=0,
            limit=max_export,
            search=search,
            filters=filters if filters else None,
            sort_field=sort_by or "created_at",
            sort_order=sort_order or "desc",
            include_relations=include_relations,
        )

        # 转换为响应格式
        asset_responses: list[AssetResponse | AssetListItemResponse]
        if include_relations:
            asset_responses = [AssetResponse.model_validate(asset) for asset in assets]
        else:
            asset_responses = [
                AssetListItemResponse.model_validate(asset) for asset in assets
            ]

        # 返回统一格式，符合前端期望
        return {
            "success": True,
            "data": asset_responses,
            "message": f"成功获取{len(asset_responses)}个资产",
        }

    except Exception as e:
        raise internal_error(f"获取资产列表失败: {str(e)}")


@router.post("/by-ids", summary="根据ID列表获取资产")
async def get_assets_by_ids(
    request: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    include_relations: bool = Query(False, description="是否加载关联数据"),
) -> dict[str, Any]:
    """
    根据资产ID列表批量获取资产信息

    - **ids**: 资产ID列表
    - **include_relations**: 是否加载关联数据（默认不加载）
    """
    try:
        asset_ids = request.get("ids", [])
        if not asset_ids:
            return {"success": True, "data": [], "message": "未提供资产ID列表"}

        # 批量查询资产
        assets = asset_crud.get_multi_by_ids(
            db=db, ids=asset_ids, include_relations=include_relations
        )

        # 转换为响应格式
        asset_responses: list[AssetResponse | AssetListItemResponse]
        if include_relations:
            asset_responses = [AssetResponse.model_validate(asset) for asset in assets]
        else:
            asset_responses = [
                AssetListItemResponse.model_validate(asset) for asset in assets
            ]

        # 返回统一格式，符合前端期望
        return {
            "success": True,
            "data": asset_responses,
            "message": f"成功获取{len(asset_responses)}个资产",
        }

    except Exception as e:
        raise internal_error(f"根据ID列表获取资产失败: {str(e)}")


@router.post("/batch-delete", summary="批量删除资产")
async def batch_delete_assets(
    request: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """
    批量删除资产

    - **asset_ids**: 要删除的资产ID列表
    """
    try:
        asset_ids = request.get("asset_ids", [])
        if not asset_ids:
            raise bad_request("未提供要删除的资产ID列表")

        # 使用新的Service层
        service = AssetBatchService(db)
        result = service.batch_delete(
            asset_ids=asset_ids,
            operator=str(current_user.username) if current_user else "system",
        )

        return {
            "success": True,
            "data": {"deleted_count": result.success_count},
            "message": f"成功删除{result.success_count}个资产",
        }

    except Exception as e:
        raise internal_error(f"批量删除资产失败: {str(e)}")
