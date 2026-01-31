"""
资产导入API路由模块

从 assets.py 中提取的导入相关端点
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ....core.exception_handler import internal_error
from ....crud.asset import asset_crud
from ....crud.history import history_crud
from ....database import get_db
from ....middleware.auth import require_permission
from ....models.asset import Asset
from ....models.auth import User
from ....schemas.asset import (
    AssetCreate,
    AssetImportRequest,
    AssetImportResponse,
    AssetUpdate,
    AssetValidationRequest,
    BatchProcessingError,
)

# 创建导入路由器
router = APIRouter()


@router.post("/import", response_model=AssetImportResponse, summary="导入资产数据")
async def import_assets(
    request: AssetImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("asset", "create")),
) -> AssetImportResponse:
    """
    批量导入资产数据

    - **data**: 待导入的资产数据列表
    - **import_mode**: 导入模式（create/merge/update）
    - **skip_errors**: 是否跳过错误数据
    - **dry_run**: 是否仅验证不实际导入
    """
    try:
        # 延迟导入以避免循环依赖
        from .asset_batch import validate_asset_data

        import_id = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        success_count = 0
        failed_count = 0
        total_count = len(request.data)
        errors: list[BatchProcessingError] = []
        imported_assets: list[str] = []

        for index, asset_data in enumerate(request.data):
            try:
                # 验证数据
                validation_request = AssetValidationRequest(
                    data=asset_data, validate_rules=None
                )
                validation_result = validate_asset_data(
                    validation_request, db, current_user
                )

                if not validation_result.is_valid and not request.should_skip_errors:
                    for error in validation_result.errors:
                        errors.append(
                            BatchProcessingError(
                                id=None,
                                row_index=index + 1,
                                field=error.field,
                                message=error.message,
                                code=error.code,
                            )
                        )
                    failed_count += 1
                    continue

                # 检查重复项（仅在merge和update模式下）
                existing_asset = None
                if request.import_mode in ["merge", "update"]:
                    if "property_name" in asset_data and "address" in asset_data:
                        # 按物业名称和地址查找重复项
                        assets, _ = asset_crud.get_multi_with_search(
                            db=db,
                            search=f"{asset_data.get('property_name', '')} {asset_data.get('address', '')}",
                            limit=1,
                        )
                        if assets:
                            existing_asset = assets[0]

                if request.is_dry_run:
                    # 仅验证，不实际导入
                    success_count += 1
                    continue

                # 根据模式处理数据
                new_asset: Asset | None = None
                if request.import_mode == "create":
                    # 创建新资产
                    asset_create = AssetCreate(**asset_data)
                    new_asset = asset_crud.create(db=db, obj_in=asset_create)
                    assert new_asset is not None  # nosec B101  # Type narrowing for mypy
                    imported_assets.append(new_asset.id)
                    success_count += 1

                elif request.import_mode == "merge" and existing_asset:
                    # 更新现有资产
                    asset_update = AssetUpdate(
                        **{
                            k: v
                            for k, v in asset_data.items()
                            if k not in ["id", "created_at"]
                        }
                    )
                    updated_asset = asset_crud.update(
                        db=db, db_obj=existing_asset, obj_in=asset_update
                    )
                    imported_assets.append(str(updated_asset.id))
                    success_count += 1

                elif request.import_mode == "update" and existing_asset:
                    # 强制更新现有资产
                    asset_update = AssetUpdate(**asset_data)
                    updated_asset = asset_crud.update(
                        db=db, db_obj=existing_asset, obj_in=asset_update
                    )
                    imported_assets.append(str(updated_asset.id))
                    success_count += 1

                else:
                    # 创建新资产（默认情况）
                    asset_create = AssetCreate(**asset_data)
                    new_asset = asset_crud.create(db=db, obj_in=asset_create)
                    assert new_asset is not None  # nosec B101  # Type narrowing for mypy
                    imported_assets.append(new_asset.id)
                    success_count += 1

                # 记录历史
                operator = (
                    getattr(current_user, "username", None)
                    or getattr(current_user, "id", None)
                    or "system"
                )
                history_crud.create(
                    db=db,
                    asset_id=imported_assets[-1] if imported_assets else "unknown",
                    operation_type="批量导入",
                    description="通过批量导入创建/更新资产",
                    operator=str(operator) if operator is not None else None,
                )

            except Exception as e:
                errors.append(
                    BatchProcessingError(
                        id=None,
                        row_index=index + 1,
                        field=None,
                        message=str(e),
                        code=type(e).__name__,
                    )
                )
                failed_count += 1

        return AssetImportResponse(
            success_count=success_count,
            failed_count=failed_count,
            total_count=total_count,
            errors=errors,
            imported_assets=imported_assets,
            import_id=import_id if not request.is_dry_run else None,
        )

    except Exception as e:
        raise internal_error(f"资产导入失败: {str(e)}")
