"""资产导入服务。"""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.asset import asset_crud
from ...crud.ownership import ownership
from ...models.asset import Asset
from ...models.auth import User
from ...models.ownership import Ownership
from ...schemas.asset import (
    AssetCreate,
    AssetImportRequest,
    AssetImportResponse,
    AssetUpdate,
    AssetValidationRequest,
    BatchProcessingError,
)
from ..enum_validation_service import get_enum_validation_service_async
from .batch_service import AsyncAssetBatchService


class AsyncAssetImportService:
    """资产导入业务编排服务。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.batch_service = AsyncAssetBatchService(db)

    async def import_assets(
        self,
        *,
        request: AssetImportRequest,
        current_user: User | None = None,
    ) -> AssetImportResponse:
        """执行资产批量导入。"""
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
        default_org_id = getattr(current_user, "default_organization_id", None)  # DEPRECATED legacy org scope fallback
        organization_id = (  # DEPRECATED alias
            str(default_org_id)
            if default_org_id is not None and str(default_org_id).strip() != ""
            else None
        )
        enum_service = get_enum_validation_service_async(self.db)

        ownership_by_id, ownership_by_name = await self._load_ownership_maps(
            request.data
        )
        existing_assets_by_name = await self._load_existing_assets_map(request.data)

        for index, raw_asset_data in enumerate(request.data):
            asset_data = dict(raw_asset_data)
            try:
                validation_request = AssetValidationRequest(
                    data=asset_data, validate_rules=None
                )
                is_valid, validation_errors, _, _ = (
                    await self.batch_service.validate_asset_data(
                        data=validation_request.data,
                        validate_rules=validation_request.validate_rules,
                        enum_validation_service=enum_service,
                    )
                )

                error_models = [
                    self._build_batch_error(
                        row_index=index + 1,
                        field=error.get("field"),
                        message=error.get("error", "验证失败"),
                        code=error.get("code"),
                    )
                    for error in validation_errors
                ]

                if not is_valid and not request.should_skip_errors:
                    errors.extend(error_models)
                    failed_count += 1
                    continue

                existing_asset = None
                asset_name = self._normalize_string(asset_data.get("asset_name"))
                if request.import_mode in ["merge", "update"] and asset_name != "":
                    existing_asset = existing_assets_by_name.get(asset_name)

                ownership_id = self._normalize_string(asset_data.get("ownership_id"))
                ownership_entity = self._normalize_string(
                    asset_data.get("ownership_entity")
                )

                if ownership_entity != "" and ownership_id == "":
                    ownership = ownership_by_name.get(ownership_entity)
                    if not ownership:
                        errors.append(
                            self._build_batch_error(
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
                            self._build_batch_error(
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
                            self._build_batch_error(
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

                if asset_name:
                    existing_by_name = existing_assets_by_name.get(asset_name)
                    if existing_by_name and (
                        not existing_asset
                        or str(existing_by_name.id) != str(existing_asset.id)
                    ):
                        errors.append(
                            self._build_batch_error(
                                row_index=index + 1,
                                field="asset_name",
                                message="物业名称已存在",
                                code="DUPLICATE_RESOURCE",
                            )
                        )
                        failed_count += 1
                        continue

                if request.is_dry_run:
                    success_count += 1
                    continue

                if request.import_mode == "create":
                    asset_create = AssetCreate(**asset_data)
                    new_asset = await asset_crud.create_with_history_async(
                        db=self.db,
                        obj_in=asset_create,
                        operator=operator_value,
                        organization_id=organization_id,  # DEPRECATED alias
                    )
                    assert new_asset is not None
                    if getattr(new_asset, "asset_name", None) is not None:
                        existing_assets_by_name[str(new_asset.asset_name)] = new_asset
                    imported_assets.append(str(new_asset.id))
                    success_count += 1
                    continue

                if request.import_mode == "merge" and existing_asset:
                    asset_update = AssetUpdate(
                        **{
                            key: value
                            for key, value in asset_data.items()
                            if key not in ["id", "created_at"]
                        }
                    )
                    updated_asset = await asset_crud.update_with_history_async(
                        db=self.db,
                        db_obj=existing_asset,
                        obj_in=asset_update,
                        operator=operator_value,
                    )
                    if getattr(updated_asset, "asset_name", None) is not None:
                        existing_assets_by_name[str(updated_asset.asset_name)] = (
                            updated_asset
                        )
                    imported_assets.append(str(updated_asset.id))
                    success_count += 1
                    continue

                if request.import_mode == "update" and existing_asset:
                    asset_update = AssetUpdate(**asset_data)
                    updated_asset = await asset_crud.update_with_history_async(
                        db=self.db,
                        db_obj=existing_asset,
                        obj_in=asset_update,
                        operator=operator_value,
                    )
                    if getattr(updated_asset, "asset_name", None) is not None:
                        existing_assets_by_name[str(updated_asset.asset_name)] = (
                            updated_asset
                        )
                    imported_assets.append(str(updated_asset.id))
                    success_count += 1
                    continue

                asset_create = AssetCreate(**asset_data)
                new_asset = await asset_crud.create_with_history_async(
                    db=self.db,
                    obj_in=asset_create,
                    operator=operator_value,
                    organization_id=organization_id,  # DEPRECATED alias
                )
                assert new_asset is not None
                if getattr(new_asset, "asset_name", None) is not None:
                    existing_assets_by_name[str(new_asset.asset_name)] = new_asset
                imported_assets.append(str(new_asset.id))
                success_count += 1

            except Exception as exc:
                errors.append(
                    self._build_batch_error(
                        row_index=index + 1,
                        field=None,
                        message=str(exc),
                        code=type(exc).__name__,
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

    async def _load_ownership_maps(
        self,
        data: list[dict[str, Any]],
    ) -> tuple[dict[str, Ownership], dict[str, Ownership]]:
        ownership_ids_to_load = {
            self._normalize_string(item.get("ownership_id"))
            for item in data
            if self._normalize_string(item.get("ownership_id")) != ""
        }
        ownership_names_to_load = {
            self._normalize_string(item.get("ownership_entity"))
            for item in data
            if self._normalize_string(item.get("ownership_entity")) != ""
        }

        ownership_by_id: dict[str, Ownership] = {}
        if ownership_ids_to_load:
            ownership_rows = await ownership.get_by_ids_async(
                self.db, list(ownership_ids_to_load)
            )
            ownership_by_id = {str(o.id): o for o in ownership_rows}

        ownership_by_name: dict[str, Ownership] = {}
        if ownership_names_to_load:
            ownership_rows = await ownership.get_by_names_async(
                self.db, list(ownership_names_to_load)
            )
            ownership_by_name = {str(o.name): o for o in ownership_rows}

        return ownership_by_id, ownership_by_name

    async def _load_existing_assets_map(
        self,
        data: list[dict[str, Any]],
    ) -> dict[str, Asset]:
        asset_names_to_load = {
            self._normalize_string(item.get("asset_name"))
            for item in data
            if self._normalize_string(item.get("asset_name")) != ""
        }

        if not asset_names_to_load:
            return {}

        existing_asset_rows = await asset_crud.get_by_asset_names_async(
            self.db,
            list(asset_names_to_load),
            exclude_deleted=True,
            decrypt=False,
        )
        return {
            str(asset.asset_name): asset
            for asset in existing_asset_rows
            if getattr(asset, "asset_name", None) is not None
        }

    @staticmethod
    def _normalize_string(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _build_batch_error(
        *,
        row_index: int | None,
        field: str | None,
        message: str,
        code: str | None,
    ) -> BatchProcessingError:
        return BatchProcessingError(
            id=None,
            row_index=row_index,
            field=field,
            message=message,
            code=code,
        )
