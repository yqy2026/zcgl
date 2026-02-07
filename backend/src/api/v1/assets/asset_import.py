"""
资产导入API路由模块

从 assets.py 中提取的导入相关端点
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.exception_handler import internal_error
from ....crud.asset import asset_crud
from ....database import get_async_db
from ....middleware.auth import require_permission
from ....models.asset import Asset
from ....models.auth import User
from ....models.ownership import Ownership
from ....schemas.asset import (
    AssetCreate,
    AssetImportRequest,
    AssetImportResponse,
    AssetUpdate,
    AssetValidationRequest,
    BatchProcessingError,
)
from ....services.asset.batch_service import AsyncAssetBatchService
from ....services.enum_validation_service import get_enum_validation_service_async

# 创建导入路由器
router = APIRouter()


@router.post("/import", response_model=AssetImportResponse, summary="导入资产数据")
async def import_assets(
    request: AssetImportRequest,
    db: AsyncSession = Depends(get_async_db),
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
        import_id = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        success_count = 0
        failed_count = 0
        total_count = len(request.data)
        errors: list[BatchProcessingError] = []
        imported_assets: list[str] = []

        operator = (
            getattr(current_user, "username", None)
            or getattr(current_user, "id", None)
            or "system"
        )
        operator_value = str(operator) if operator is not None else None
        service = AsyncAssetBatchService(db)
        enum_service = get_enum_validation_service_async(db)
        ownership_ids_to_load = {
            str(item.get("ownership_id")).strip()
            for item in request.data
            if item.get("ownership_id") is not None
            and str(item.get("ownership_id")).strip() != ""
        }
        ownership_names_to_load = {
            str(item.get("ownership_entity")).strip()
            for item in request.data
            if item.get("ownership_entity") is not None
            and str(item.get("ownership_entity")).strip() != ""
        }
        property_names_to_load = {
            str(item.get("property_name")).strip()
            for item in request.data
            if item.get("property_name") is not None
            and str(item.get("property_name")).strip() != ""
        }

        ownership_by_id: dict[str, Ownership] = {}
        if ownership_ids_to_load:
            ownership_rows = list(
                (
                    await db.execute(
                        select(Ownership).where(
                            Ownership.id.in_(list(ownership_ids_to_load))
                        )
                    )
                )
                .scalars()
                .all()
            )
            ownership_by_id = {str(ownership.id): ownership for ownership in ownership_rows}

        ownership_by_name: dict[str, Ownership] = {}
        if ownership_names_to_load:
            ownership_rows = list(
                (
                    await db.execute(
                        select(Ownership).where(
                            Ownership.name.in_(list(ownership_names_to_load))
                        )
                    )
                )
                .scalars()
                .all()
            )
            ownership_by_name = {
                str(ownership.name): ownership for ownership in ownership_rows
            }

        existing_assets_by_name: dict[str, Asset] = {}
        if property_names_to_load:
            existing_asset_rows = list(
                (
                    await db.execute(
                        select(Asset).where(
                            Asset.property_name.in_(list(property_names_to_load)),
                            Asset.data_status != "已删除",
                        )
                    )
                )
                .scalars()
                .all()
            )
            existing_assets_by_name = {
                str(asset.property_name): asset
                for asset in existing_asset_rows
                if getattr(asset, "property_name", None) is not None
            }

        for index, asset_data in enumerate(request.data):
            try:
                validation_request = AssetValidationRequest(
                    data=asset_data, validate_rules=None
                )
                is_valid, validation_errors, _, _ = await service.validate_asset_data(
                    data=validation_request.data,
                    validate_rules=validation_request.validate_rules,
                    enum_validation_service=enum_service,
                )

                error_models: list[BatchProcessingError] = []
                for error in validation_errors:
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

                if not is_valid and not request.should_skip_errors:
                    for error_model in error_models:
                        errors.append(
                            BatchProcessingError(
                                id=None,
                                row_index=index + 1,
                                field=error_model.field,
                                message=error_model.message,
                                code=error_model.code,
                            )
                        )
                    failed_count += 1
                    continue

                existing_asset = None
                property_name = (
                    str(asset_data.get("property_name")).strip()
                    if asset_data.get("property_name") is not None
                    else ""
                )
                if request.import_mode in ["merge", "update"]:
                    if property_name != "":
                        existing_asset = existing_assets_by_name.get(property_name)

                ownership_id_raw = asset_data.get("ownership_id")
                ownership_id = (
                    str(ownership_id_raw).strip()
                    if ownership_id_raw is not None
                    else ""
                )
                ownership_entity_raw = asset_data.get("ownership_entity")
                ownership_entity = (
                    str(ownership_entity_raw).strip()
                    if ownership_entity_raw is not None
                    else ""
                )

                if ownership_entity != "" and ownership_id == "":
                    ownership = ownership_by_name.get(ownership_entity)
                    if not ownership:
                        errors.append(
                            BatchProcessingError(
                                id=None,
                                row_index=index + 1,
                                field="ownership_entity",
                                message="权属方不存在",
                                code="INVALID_OWNERSHIP",
                            )
                        )
                        failed_count += 1
                        continue
                    ownership_id = str(ownership.id)
                    ownership_by_id[ownership_id] = ownership

                if ownership_id != "":
                    ownership = ownership_by_id.get(ownership_id)
                    if not ownership:
                        errors.append(
                            BatchProcessingError(
                                id=None,
                                row_index=index + 1,
                                field="ownership_id",
                                message="权属方不存在",
                                code="INVALID_OWNERSHIP",
                            )
                        )
                        failed_count += 1
                        continue

                    if (
                        ownership_entity != ""
                        and ownership_entity != str(ownership.name)
                    ):
                        errors.append(
                            BatchProcessingError(
                                id=None,
                                row_index=index + 1,
                                field="ownership_entity",
                                message="权属方名称与ID不一致",
                                code="OWNERSHIP_MISMATCH",
                            )
                        )
                        failed_count += 1
                        continue

                    asset_data["ownership_id"] = str(ownership.id)

                asset_data.pop("ownership_entity", None)

                if property_name:
                    existing_by_name = existing_assets_by_name.get(property_name)
                    if existing_by_name and (
                        not existing_asset
                        or str(existing_by_name.id) != str(existing_asset.id)
                    ):
                        errors.append(
                            BatchProcessingError(
                                id=None,
                                row_index=index + 1,
                                field="property_name",
                                message="物业名称已存在",
                                code="DUPLICATE_RESOURCE",
                            )
                        )
                        failed_count += 1
                        continue

                if request.is_dry_run:
                    success_count += 1
                    continue

                new_asset: Asset | None = None
                if request.import_mode == "create":
                    asset_create = AssetCreate(**asset_data)
                    new_asset = await asset_crud.create_with_history_async(
                        db=db, obj_in=asset_create, operator=operator_value
                    )
                    assert new_asset is not None
                    if getattr(new_asset, "property_name", None) is not None:
                        existing_assets_by_name[str(new_asset.property_name)] = new_asset
                    imported_assets.append(new_asset.id)
                    success_count += 1

                elif request.import_mode == "merge" and existing_asset:
                    asset_update = AssetUpdate(
                        **{
                            k: v
                            for k, v in asset_data.items()
                            if k not in ["id", "created_at"]
                        }
                    )
                    updated_asset = await asset_crud.update_with_history_async(
                        db=db,
                        db_obj=existing_asset,
                        obj_in=asset_update,
                        operator=operator_value,
                    )
                    if getattr(updated_asset, "property_name", None) is not None:
                        existing_assets_by_name[str(updated_asset.property_name)] = (
                            updated_asset
                        )
                    imported_assets.append(str(updated_asset.id))
                    success_count += 1

                elif request.import_mode == "update" and existing_asset:
                    asset_update = AssetUpdate(**asset_data)
                    updated_asset = await asset_crud.update_with_history_async(
                        db=db,
                        db_obj=existing_asset,
                        obj_in=asset_update,
                        operator=operator_value,
                    )
                    if getattr(updated_asset, "property_name", None) is not None:
                        existing_assets_by_name[str(updated_asset.property_name)] = (
                            updated_asset
                        )
                    imported_assets.append(str(updated_asset.id))
                    success_count += 1

                else:
                    asset_create = AssetCreate(**asset_data)
                    new_asset = await asset_crud.create_with_history_async(
                        db=db, obj_in=asset_create, operator=operator_value
                    )
                    assert new_asset is not None
                    if getattr(new_asset, "property_name", None) is not None:
                        existing_assets_by_name[str(new_asset.property_name)] = new_asset
                    imported_assets.append(new_asset.id)
                    success_count += 1

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
