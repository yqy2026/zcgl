"""
资产批量操作服务

提供事务管理的批量更新、删除和验证功能
"""

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator
from pydantic_core import PydanticCustomError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.asset import asset_crud
from ...crud.history import history_crud
from ...crud.ownership import ownership
from ...models.asset import Asset
from ...schemas.asset import AssetUpdate
from .validators import AssetBatchValidator

logger = logging.getLogger(__name__)


def _utcnow_naive() -> datetime:
    """Return UTC now as naive datetime to match current DB column types."""
    return datetime.now(UTC).replace(tzinfo=None)


class BatchOperationResult(BaseModel):
    """批量操作结果 - Pydantic模型，带验证器确保数据一致性"""

    success_count: int = Field(default=0, ge=0, description="成功数量")
    failed_count: int = Field(default=0, ge=0, description="失败数量")
    total_count: int = Field(default=0, ge=0, description="总数量")
    errors: list[dict[str, Any]] = Field(
        default_factory=list[Any], description="错误列表"
    )
    updated_ids: list[str] = Field(
        default_factory=list[Any], description="已更新的资产ID"
    )

    model_config = {"frozen": False}

    @model_validator(mode="after")
    def validate_counts(self) -> "BatchOperationResult":
        """验证计数一致性：success + failed 不能超过 total"""
        if self.success_count + self.failed_count > self.total_count:
            raise PydanticCustomError(
                "count_mismatch",
                "success_count({success}) + failed_count({failed}) cannot exceed total_count({total})",
                {
                    "success": self.success_count,
                    "failed": self.failed_count,
                    "total": self.total_count,
                },
            )
        return self

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "total_count": self.total_count,
            "errors": self.errors,
            "updated_assets": self.updated_ids,
        }


class AsyncAssetBatchService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.validator = AssetBatchValidator()

    @staticmethod
    def _to_list_safely(value: Any) -> list[Any]:
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return list(value)
        return []

    async def _load_assets_map(self, asset_ids: list[str]) -> dict[str, Asset]:
        if not asset_ids:
            return {}
        assets = await asset_crud.get_multi_by_ids_async(
            self.db, ids=asset_ids, include_relations=False, include_deleted=False
        )
        return {str(asset.id): asset for asset in assets if getattr(asset, "id", None)}

    async def _find_linked_asset_errors(self, asset_ids: list[str]) -> dict[str, str]:
        if not asset_ids:
            return {}
        try:
            contract_asset_ids = await asset_crud.get_assets_with_rent_contracts_async(
                self.db, asset_ids
            )
            certificate_asset_ids = await asset_crud.get_assets_with_property_certs_async(
                self.db, asset_ids
            )
            ledger_asset_ids = await asset_crud.get_assets_with_rent_ledger_async(
                self.db, asset_ids
            )
        except Exception:
            return {}

        linked_errors: dict[str, str] = {}
        for asset_id in self._to_list_safely(contract_asset_ids):
            linked_errors[str(asset_id)] = "资产已关联合同，禁止删除"
        for asset_id in self._to_list_safely(certificate_asset_ids):
            linked_errors.setdefault(str(asset_id), "资产已关联产权证，禁止删除")
        for asset_id in self._to_list_safely(ledger_asset_ids):
            linked_errors.setdefault(str(asset_id), "资产已有租金台账记录，禁止删除")
        return linked_errors

    async def _ensure_asset_not_linked(self, asset_id: str) -> None:
        has_contract = await asset_crud.has_rent_contracts_async(self.db, asset_id)
        if has_contract:
            raise ValueError("资产已关联合同，禁止删除")

        has_certificate = await asset_crud.has_property_certs_async(self.db, asset_id)
        if has_certificate:
            raise ValueError("资产已关联产权证，禁止删除")

        has_ledger = await asset_crud.has_rent_ledger_async(self.db, asset_id)
        if has_ledger:
            raise ValueError("资产已有租金台账记录，禁止删除")

    async def _resolve_batch_ownership_id(
        self, updates: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """批量更新前置解析 ownership_id，避免循环内重复查库。"""
        if "ownership_id" not in updates:
            return False, None

        ownership_id_raw = updates.get("ownership_id")
        ownership_id = (
            str(ownership_id_raw).strip() if ownership_id_raw is not None else ""
        )
        if ownership_id == "":
            return True, None

        ownership_obj = await ownership.get_async(self.db, ownership_id)
        if not ownership_obj:
            raise ValueError("权属方不存在")

        return True, ownership_id

    async def batch_update(
        self,
        asset_ids: list[str] | None = None,
        updates: dict[str, Any] | None = None,
        should_update_all: bool = False,
        operator: str = "system",
    ) -> BatchOperationResult:
        if should_update_all:
            all_assets, _ = await asset_crud.get_multi_with_search_async(
                db=self.db, skip=0, limit=10000
            )
            asset_ids = [asset.id for asset in all_assets]

        if not asset_ids:
            return BatchOperationResult(total_count=0)

        result = BatchOperationResult(total_count=len(asset_ids))
        assets_by_id = await self._load_assets_map(asset_ids)
        base_updates: dict[str, Any] = updates.copy() if updates else {}
        has_ownership_update, batch_ownership_id = await self._resolve_batch_ownership_id(
            base_updates
        )

        property_name_owner_id: str | None = None
        property_name_raw = base_updates.get("property_name")
        property_name = (
            str(property_name_raw).strip() if property_name_raw is not None else ""
        )
        if property_name != "":
            base_updates["property_name"] = property_name
            existing_asset = await asset_crud.get_by_name_async(
                db=self.db, property_name=property_name
            )
            if existing_asset and getattr(existing_asset, "id", None):
                property_name_owner_id = str(existing_asset.id)

        for asset_id in asset_ids:
            savepoint = await self.db.begin_nested()
            try:
                asset = assets_by_id.get(asset_id)
                if not asset:
                    await savepoint.rollback()
                    result.errors.append(
                        {
                            "asset_id": asset_id,
                            "error": "资产不存在",
                            "error_type": "NotFoundError",
                        }
                    )
                    result.failed_count += 1
                    continue

                update_payload = base_updates.copy()
                if has_ownership_update:
                    if batch_ownership_id:
                        update_payload["ownership_id"] = batch_ownership_id
                    else:
                        update_payload["ownership_id"] = getattr(
                            asset, "ownership_id", None
                        )

                new_name = update_payload.get("property_name")
                if new_name and new_name != asset.property_name:
                    if (
                        property_name_owner_id is not None
                        and property_name_owner_id != str(asset_id)
                    ):
                        raise ValueError("物业名称已存在")
                    property_name_owner_id = str(asset_id)

                update_schema = AssetUpdate(**update_payload)
                await asset_crud.update_async(
                    db=self.db, db_obj=asset, obj_in=update_schema, commit=False
                )

                await history_crud.create_async(
                    db=self.db,
                    asset_id=asset_id,
                    operation_type="批量更新",
                    description=f"批量更新字段: {', '.join(update_payload.keys())}",
                    operator=operator,
                    commit=False,
                )

                await savepoint.commit()
                result.success_count += 1
                result.updated_ids.append(asset_id)

            except Exception as e:
                await savepoint.rollback()
                result.errors.append(
                    {
                        "asset_id": asset_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "field_context": self._extract_field_from_error(str(e)),
                    }
                )
                result.failed_count += 1
                logger.warning(f"资产 {asset_id} 更新失败: {e}")

        if result.success_count > 0:
            await self.db.commit()
            logger.info(
                f"批量更新完成: 成功={result.success_count}, 失败={result.failed_count}"
            )
        else:
            await self.db.rollback()
            logger.error(f"批量更新全部失败，已回滚: {len(result.errors)} 个错误")

        return result

    def _extract_field_from_error(self, error_msg: str) -> str | None:
        import re

        match = re.search(r"(\w+)\n\s+Field required|(\w+)\n\s+Value error", error_msg)
        if match:
            return match.group(1) or match.group(2)
        return None

    async def validate_asset_data(
        self,
        data: dict[str, Any],
        validate_rules: list[str] | None = None,
        enum_validation_service: Any = None,
    ) -> tuple[bool, list[dict[str, str]], list[dict[str, str]], list[str]]:
        is_valid, errors, warnings, validated_fields = self.validator.validate_all(
            data, validate_rules
        )

        if "ownership_status" in data and enum_validation_service:
            validation_context = {
                "service": "AsyncAssetBatchService",
                "action": "validate_asset_data",
            }

            is_enum_valid, error_msg = await enum_validation_service.validate_value(
                "ownership_status",
                data["ownership_status"],
                allow_empty=False,
                context=validation_context,
            )
            if not is_enum_valid:
                errors.append(
                    {
                        "field": "ownership_status",
                        "error": error_msg,
                    }
                )
            else:
                if "ownership_status" not in validated_fields:
                    validated_fields.append("ownership_status")

        is_valid = len(errors) == 0
        return is_valid, errors, warnings, validated_fields

    async def batch_delete(
        self,
        asset_ids: list[str],
        operator: str = "system",
    ) -> BatchOperationResult:
        if not asset_ids:
            return BatchOperationResult(total_count=0)

        result = BatchOperationResult(total_count=len(asset_ids))
        assets_by_id = await self._load_assets_map(asset_ids)
        linked_errors_by_asset_id = await self._find_linked_asset_errors(asset_ids)

        try:
            for asset_id in asset_ids:
                async with self.db.begin_nested():
                    asset = assets_by_id.get(asset_id)
                    if not asset:
                        result.errors.append(
                            {"asset_id": asset_id, "error": "资产不存在"}
                        )
                        result.failed_count += 1
                        continue

                    linked_error = linked_errors_by_asset_id.get(asset_id)
                    if linked_error:
                        result.errors.append({"asset_id": asset_id, "error": linked_error})
                        result.failed_count += 1
                        continue

                    await history_crud.create_async(
                        db=self.db,
                        asset_id=asset_id,
                        operation_type="DELETE",
                        description=f"批量删除资产: {asset.property_name}",
                        operator=operator,
                        commit=False,
                    )
                    asset.data_status = "已删除"
                    asset.updated_by = operator
                    asset.updated_at = _utcnow_naive()
                    self.db.add(asset)
                    await self.db.flush()
                    result.success_count += 1

            await self.db.commit()
            logger.info(
                f"批量删除完成: 成功={result.success_count}, 失败={result.failed_count}"
            )
            return result

        except Exception as e:
            result.errors.append(
                {
                    "asset_id": asset_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            result.failed_count += 1
            await self.db.rollback()
            logger.error(f"批量删除失败，已回滚: {str(e)}")
            raise
