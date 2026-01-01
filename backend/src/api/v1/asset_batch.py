"""
资产批量操作API路由模块

从 assets.py 中提取的批量操作相关端点
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...crud.asset import asset_crud
from ...crud.history import history_crud
from ...database import get_db
from ...middleware.auth import get_current_active_user, require_permission
from ...models.auth import User
from ...schemas.asset import (
    AssetBatchUpdateRequest,
    AssetBatchUpdateResponse,
    AssetResponse,
    AssetUpdate,
    AssetValidationRequest,
    AssetValidationResponse,
    BatchCustomFieldUpdateRequest,
    BatchCustomFieldUpdateResponse,
)
from ...services.enum_validation_service import get_enum_validation_service

# 创建批量操作路由器
router = APIRouter()


@router.post(
    "/batch-update", response_model=AssetBatchUpdateResponse, summary="批量更新资产"
)
async def batch_update_assets(
    request: AssetBatchUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset", "update")),
):
    """
    批量更新资产信息

    - **asset_ids**: 资产ID列表
    - **updates**: 更新数据字典
    - **update_all**: 是否更新所有资产
    """
    try:
        # 如果更新所有资产，获取所有资产ID
        if request.update_all:
            all_assets, _ = asset_crud.get_multi_with_search(db=db, skip=0, limit=10000)
            asset_ids = [asset.id for asset in all_assets]
        else:
            asset_ids = request.asset_ids

        total_count = len(asset_ids)
        success_count = 0
        failed_count = 0
        errors = []
        updated_assets = []

        for asset_id in asset_ids:
            try:
                # 获取现有资产
                asset = asset_crud.get(db=db, id=asset_id)
                if not asset:
                    errors.append({"asset_id": asset_id, "error": "资产不存在"})
                    failed_count += 1
                    continue

                # 更新资产 - 将dict转换为AssetUpdate模型
                update_schema = AssetUpdate(**request.updates)
                asset_crud.update(db=db, db_obj=asset, obj_in=update_schema)

                success_count += 1
                updated_assets.append(asset_id)

                # 记录历史
                history_crud.create(
                    db=db,
                    obj_in={
                        "asset_id": asset_id,
                        "operation_type": "批量更新",
                        "description": f"批量更新字段: {', '.join(request.updates.keys())}",
                        "operator": "system",
                    },
                )

            except Exception as e:
                errors.append({"asset_id": asset_id, "error": str(e)})
                failed_count += 1

        return AssetBatchUpdateResponse(
            success_count=success_count,
            failed_count=failed_count,
            total_count=total_count,
            errors=errors,
            updated_assets=updated_assets,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量更新失败: {str(e)}")


@router.post(
    "/validate", response_model=AssetValidationResponse, summary="验证资产数据"
)
async def validate_asset_data(
    request: AssetValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    验证资产数据的完整性和正确性

    - **data**: 待验证的资产数据
    - **validate_rules**: 验证规则列表
    """
    try:
        errors = []
        warnings = []
        validated_fields = []

        data = request.data
        validate_rules = request.validate_rules or ["required_fields", "data_format"]

        # 验证必填字段
        if "required_fields" in validate_rules:
            required_fields = [
                "property_name",
                "address",
                "ownership_status",
                "property_nature",
                "usage_status",
            ]

            for field in required_fields:
                if field not in data or not data[field]:
                    errors.append({"field": field, "error": f"{field}为必填字段"})
                else:
                    validated_fields.append(field)

        # 验证数据格式
        if "data_format" in validate_rules:
            # 验证枚举值 - 使用 EnumValidationService
            if "ownership_status" in data:
                enum_service = get_enum_validation_service(db)

                # 构建上下文信息，用于追踪验证失败
                validation_context = {
                    "api_endpoint": "/assets/validate",
                    "user_id": current_user.id if current_user else "anonymous",
                    "user_name": current_user.username if current_user else "anonymous",
                    "action": "validate_asset_data",
                }

                is_valid, error_msg = enum_service.validate_value(
                    "ownership_status",
                    data["ownership_status"],
                    allow_empty=False,
                    context=validation_context,
                )
                if not is_valid:
                    errors.append(
                        {
                            "field": "ownership_status",
                            "error": error_msg,
                        }
                    )
                else:
                    validated_fields.append("ownership_status")

            # 验证数值字段
            numeric_fields = [
                "land_area",
                "actual_property_area",
                "rentable_area",
                "rented_area",
                "annual_income",
                "annual_expense",
                "monthly_rent",
                "deposit",
            ]

            for field in numeric_fields:
                if field in data and data[field] is not None:
                    try:
                        float(data[field])
                        validated_fields.append(field)
                    except (ValueError, TypeError):
                        errors.append(
                            {"field": field, "error": f"{field}必须是有效的数字"}
                        )

            # 验证日期字段
            date_fields = [
                "contract_start_date",
                "contract_end_date",
                "operation_agreement_start_date",
                "operation_agreement_end_date",
            ]

            for field in date_fields:
                if field in data and data[field] is not None:
                    try:
                        # 简单的日期格式验证
                        if isinstance(data[field], str):
                            # 验证 YYYY-MM-DD 格式
                            import re

                            if not re.match(r"^\d{4}-\d{2}-\d{2}$", data[field]):
                                errors.append(
                                    {
                                        "field": field,
                                        "error": f"{field}日期格式应为 YYYY-MM-DD",
                                    }
                                )
                            else:
                                validated_fields.append(field)
                    except Exception:
                        errors.append({"field": field, "error": f"{field}日期格式无效"})

        # 添加建议性警告
        suggestion_fields = [
            ("land_area", "建议填写土地面积"),
            ("annual_income", "建议填写年收入"),
            ("annual_expense", "建议填写年支出"),
            ("tenant_name", "建议填写租户信息（如果是已出租资产）"),
        ]

        for field, suggestion in suggestion_fields:
            if field not in data or data[field] is None:
                warnings.append({"field": field, "message": suggestion})

        is_valid = len(errors) == 0

        return AssetValidationResponse(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            validated_fields=validated_fields,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据验证失败: {str(e)}")


@router.post(
    "/batch-custom-fields",
    response_model=BatchCustomFieldUpdateResponse,
    summary="批量更新自定义字段",
)
async def batch_update_custom_fields(
    request: BatchCustomFieldUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset", "update")),
):
    """
    批量更新资产的自定义字段

    - **asset_ids**: 资产ID列表
    - **field_values**: 自定义字段值字典
    """
    try:
        total_count = len(request.asset_ids)
        success_count = 0
        failed_count = 0
        errors = []

        for asset_id in request.asset_ids:
            try:
                # 检查资产是否存在
                asset = asset_crud.get(db=db, id=asset_id)
                if not asset:
                    errors.append({"asset_id": asset_id, "error": "资产不存在"})
                    failed_count += 1
                    continue

                # 这里简化处理，实际项目中应该有专门的自定义字段表
                # 可以将自定义字段存储在JSON格式的字段中
                success_count += 1

            except Exception as e:
                errors.append({"asset_id": asset_id, "error": str(e)})
                failed_count += 1

        return BatchCustomFieldUpdateResponse(
            success_count=success_count,
            failed_count=failed_count,
            total_count=total_count,
            errors=errors,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量更新自定义字段失败: {str(e)}")


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
    limit: int = Query(10000, ge=1, le=50000, description="最大返回数量"),
):
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
    - **limit**: 最大返回数量限制
    """
    try:
        # 构建查询过滤器
        filters = {}
        if search:
            filters["search"] = search
        if ownership_status:
            filters["ownership_status"] = ownership_status
        if usage_status:
            filters["usage_status"] = usage_status
        if property_nature:
            filters["property_nature"] = property_nature
        if business_category:
            filters["business_category"] = business_category

        # 排序
        order_by = None
        if sort_by and sort_order:
            if sort_order.lower() == "desc":
                order_by = f"{sort_by} desc"
            else:
                order_by = f"{sort_by} asc"

        # 获取所有资产（不分页）
        assets = asset_crud.get_multi(
            db=db, filters=filters if filters else None, order_by=order_by, limit=limit
        )

        # 转换为响应格式
        asset_responses = []
        for asset in assets:
            asset_dict = asset.__dict__.copy()
            asset_dict["_sa_instance_state"] = None  # 移除SQLAlchemy实例状态

            # 确保计算字段包含在响应中
            if hasattr(asset, "unrented_area"):
                asset_dict["unrented_area"] = float(asset.unrented_area)
            if hasattr(asset, "occupancy_rate"):
                asset_dict["occupancy_rate"] = float(asset.occupancy_rate)

            asset_responses.append(AssetResponse.model_validate(asset_dict))

        # 返回统一格式，符合前端期望
        return {
            "success": True,
            "data": asset_responses,
            "message": f"成功获取{len(asset_responses)}个资产",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资产列表失败: {str(e)}")


@router.post("/by-ids", summary="根据ID列表获取资产")
async def get_assets_by_ids(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    根据资产ID列表批量获取资产信息

    - **ids**: 资产ID列表
    """
    try:
        asset_ids = request.get("ids", [])
        if not asset_ids:
            return []

        # 批量查询资产
        assets = asset_crud.get_multi_by_ids(db=db, ids=asset_ids)

        # 转换为响应格式
        asset_responses = []
        for asset in assets:
            asset_dict = asset.__dict__.copy()
            asset_dict["_sa_instance_state"] = None  # 移除SQLAlchemy实例状态

            # 确保计算字段包含在响应中
            if hasattr(asset, "unrented_area"):
                asset_dict["unrented_area"] = float(asset.unrented_area)
            if hasattr(asset, "occupancy_rate"):
                asset_dict["occupancy_rate"] = float(asset.occupancy_rate)

            asset_responses.append(AssetResponse.model_validate(asset_dict))

        # 返回统一格式，符合前端期望
        return {
            "success": True,
            "data": asset_responses,
            "message": f"成功获取{len(asset_responses)}个资产",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"根据ID列表获取资产失败: {str(e)}")


@router.post("/batch-delete", summary="批量删除资产")
async def batch_delete_assets(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    批量删除资产

    - **asset_ids**: 要删除的资产ID列表
    """
    try:
        asset_ids = request.get("asset_ids", [])
        if not asset_ids:
            raise HTTPException(status_code=400, detail="未提供要删除的资产ID列表")

        # 批量删除资产
        deleted_count = 0
        for asset_id in asset_ids:
            try:
                asset = asset_crud.get(db=db, id=asset_id)
                if asset:
                    asset_crud.remove(db=db, id=asset_id)
                    deleted_count += 1
            except Exception:  # nosec - B112: Continue on individual failures during batch operations
                continue  # 即使单个资产删除失败也继续处理其他资产

        return {
            "success": True,
            "data": {"deleted_count": deleted_count},
            "message": f"成功删除{deleted_count}个资产",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量删除资产失败: {str(e)}")
