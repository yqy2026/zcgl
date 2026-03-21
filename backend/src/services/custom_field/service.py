import json
import logging
import re
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ...constants.message_constants import EMPTY_STRING
from ...core.exception_handler import (
    BusinessValidationError,
    DuplicateResourceError,
    ResourceNotFoundError,
)
from ...crud.custom_field import custom_field_crud
from ...crud.query_builder import PartyFilter
from ...models.system_dictionary import AssetCustomField
from ...schemas.asset import (
    AssetCustomFieldCreate,
    AssetCustomFieldUpdate,
    CustomFieldValueItem,
)
from ...services.party_scope import resolve_user_party_filter

logger = logging.getLogger(__name__)


class CustomFieldService:
    """自定义字段服务层"""

    @staticmethod
    def _ordered_unique(values: Sequence[str | None]) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for raw in values:
            if raw is None:
                continue
            value = str(raw).strip()
            if value == "" or value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered

    async def _resolve_party_filter(
        self,
        db: AsyncSession,
        *,
        current_user_id: str | None = None,
        party_filter: PartyFilter | None = None,
    ) -> PartyFilter | None:
        return await resolve_user_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
            logger=logger,
            allow_legacy_default_organization_fallback=False,
        )

    async def create_custom_field_async(
        self, db: AsyncSession, *, obj_in: AssetCustomFieldCreate
    ) -> AssetCustomField:
        existing = await custom_field_crud.get_by_field_name_async(
            db, field_name=obj_in.field_name
        )
        if existing:
            raise DuplicateResourceError("字段", "field_name", obj_in.field_name)

        result: AssetCustomField = await custom_field_crud.create(db, obj_in=obj_in)
        return result

    async def get_custom_fields_async(
        self,
        db: AsyncSession,
        *,
        filters: dict[str, Any] | None = None,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> list[AssetCustomField]:
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        return await custom_field_crud.get_multi_with_filters_async(
            db=db,
            filters=filters or {},
            party_filter=resolved_party_filter,
        )

    async def get_custom_field_async(
        self,
        db: AsyncSession,
        *,
        field_id: str,
        party_filter: PartyFilter | None = None,
        current_user_id: str | None = None,
    ) -> AssetCustomField | None:
        resolved_party_filter = await self._resolve_party_filter(
            db,
            current_user_id=current_user_id,
            party_filter=party_filter,
        )
        if resolved_party_filter is None:
            return await custom_field_crud.get(db=db, id=field_id)

        records = await custom_field_crud.get_with_filters(
            db,
            filters={"id": field_id},
            skip=0,
            limit=1,
            party_filter=resolved_party_filter,
        )
        return records[0] if records else None

    async def update_custom_field_async(
        self, db: AsyncSession, *, id: str, obj_in: AssetCustomFieldUpdate
    ) -> AssetCustomField:
        field = await custom_field_crud.get(db, id)
        if not field:
            raise ResourceNotFoundError("字段", id)

        if obj_in.field_name and obj_in.field_name != field.field_name:
            existing = await custom_field_crud.get_by_field_name_async(
                db, field_name=obj_in.field_name
            )
            if existing and existing.id != id:
                raise DuplicateResourceError("字段", "field_name", obj_in.field_name)

        result: AssetCustomField = await custom_field_crud.update(
            db, db_obj=field, obj_in=obj_in
        )
        return result

    async def delete_custom_field_async(
        self, db: AsyncSession, *, id: str
    ) -> AssetCustomField:
        field = await custom_field_crud.get(db, id)
        if not field:
            raise ResourceNotFoundError("字段", id)
        result: AssetCustomField = await custom_field_crud.remove(db, id=id)
        return result

    def validate_field_value(
        self, field: AssetCustomField, value: Any
    ) -> tuple[bool, str | None]:
        """验证字段值是否符合配置要求 (Refactored from CRUD)"""
        try:
            # 必填验证
            if field.is_required and (value is None or value == EMPTY_STRING):
                return False, f"字段 {field.display_name} 为必填项"

            # 如果值为空且非必填，则通过验证
            if value is None or value == EMPTY_STRING:
                return True, None

            # 根据字段类型验证
            if field.field_type == "text":
                if not isinstance(value, str):
                    return False, f"字段 {field.display_name} 必须为文本类型"

                # 检查长度限制
                if field.validation_rules:
                    text_rules_str: str | None = (
                        field.validation_rules
                        if isinstance(field.validation_rules, str)
                        else None
                    )
                    text_rules: dict[str, Any] = cast(
                        dict[str, Any],
                        json.loads(text_rules_str)
                        if text_rules_str
                        else field.validation_rules,
                    )
                    max_length = text_rules.get("max_length")
                    min_length = text_rules.get("min_length")

                    if max_length and len(value) > max_length:
                        return (
                            False,
                            f"字段 {field.display_name} 长度不能超过 {max_length} 个字符",
                        )
                    if min_length and len(value) < min_length:
                        return (
                            False,
                            f"字段 {field.display_name} 长度不能少于 {min_length} 个字符",
                        )

            elif field.field_type == "number":
                try:
                    int_value = int(value)

                    # 检查数值范围
                    if field.validation_rules:
                        number_rules_str: str | None = (
                            field.validation_rules
                            if isinstance(field.validation_rules, str)
                            else None
                        )
                        number_rules: dict[str, Any] = cast(
                            dict[str, Any],
                            json.loads(number_rules_str)
                            if number_rules_str
                            else field.validation_rules,
                        )
                        max_value = number_rules.get("max_value")
                        min_value = number_rules.get("min_value")

                        if max_value is not None and int_value > max_value:
                            return (
                                False,
                                f"字段 {field.display_name} 值不能大于 {max_value}",
                            )
                        if min_value is not None and int_value < min_value:
                            return (
                                False,
                                f"字段 {field.display_name} 值不能小于 {min_value}",
                            )

                except (ValueError, TypeError):
                    return False, f"字段 {field.display_name} 必须为整数类型"

            elif field.field_type == "decimal":
                try:
                    decimal_value = Decimal(str(value))

                    # 检查数值范围
                    if field.validation_rules:
                        decimal_rules_str: str | None = (
                            field.validation_rules
                            if isinstance(field.validation_rules, str)
                            else None
                        )
                        decimal_rules: dict[str, Any] = cast(
                            dict[str, Any],
                            json.loads(decimal_rules_str)
                            if decimal_rules_str
                            else field.validation_rules,
                        )
                        max_value = decimal_rules.get("max_value")
                        min_value = decimal_rules.get("min_value")

                        if max_value is not None and decimal_value > Decimal(
                            str(max_value)
                        ):
                            return (
                                False,
                                f"字段 {field.display_name} 值不能大于 {max_value}",
                            )
                        if min_value is not None and decimal_value < Decimal(
                            str(min_value)
                        ):
                            return (
                                False,
                                f"字段 {field.display_name} 值不能小于 {min_value}",
                            )

                except (ValueError, TypeError):
                    return False, f"字段 {field.display_name} 必须为数字类型"

            elif field.field_type == "boolean":
                if not isinstance(value, bool):
                    # Allow string 'true'/'false' for APIs sometimes?
                    # Strict check as per original code
                    return False, f"字段 {field.display_name} 必须为布尔类型"

            elif field.field_type == "date":
                try:
                    if isinstance(value, str):
                        datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    return (
                        False,
                        f"字段 {field.display_name} 日期格式不正确，应为 YYYY-MM-DD",
                    )

            elif field.field_type == "datetime":
                try:
                    if isinstance(value, str):
                        datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    return False, f"字段 {field.display_name} 日期时间格式不正确"

            elif field.field_type in ["select", "multiselect"]:
                # 检查选项是否在允许的范围内
                if field.field_options:
                    field_options_str: str | None = (
                        field.field_options
                        if isinstance(field.field_options, str)
                        else None
                    )
                    options_list: list[dict[str, Any]] | None = (
                        json.loads(field_options_str) if field_options_str else None
                    )
                    # Handle both parsed JSON and already-parsed options
                    if options_list is not None:
                        options: list[dict[str, Any]] = options_list
                    else:
                        # Cast to expected type if already parsed
                        options = (
                            field.field_options
                            if isinstance(field.field_options, list)
                            else []
                        )
                    valid_values = [
                        opt.get("value") for opt in options if isinstance(opt, dict)
                    ]

                    if field.field_type == "select":
                        if value not in valid_values:
                            return (
                                False,
                                f"字段 {field.display_name} 选项不在允许范围内",
                            )
                    else:  # multiselect
                        if not isinstance(value, list):
                            return False, f"字段 {field.display_name} 必须为数组类型"
                        for v in value:
                            if v not in valid_values:
                                return (
                                    False,
                                    f"字段 {field.display_name} 包含不允许的选项: {v}",
                                )

            elif field.field_type == "email":
                email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                if not re.match(email_pattern, str(value)):
                    return False, f"字段 {field.display_name} 邮箱格式不正确"

            elif field.field_type == "phone":
                phone_pattern = r"^[0-9\-\+\(\)\s]{10,20}$"
                if not re.match(phone_pattern, str(value)):
                    return False, f"字段 {field.display_name} 电话格式不正确"

            elif field.field_type == "url":
                url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
                if not re.match(url_pattern, str(value)):
                    return False, f"字段 {field.display_name} URL格式不正确"

            return True, None

        except Exception as e:
            return False, f"验证字段 {field.display_name} 时发生错误: {str(e)}"

    async def update_asset_field_values_async(
        self,
        db: AsyncSession,
        *,
        asset_id: str,
        values: Sequence[CustomFieldValueItem | dict[str, Any]],
    ) -> list[dict[str, Any]]:
        _ = asset_id
        updated_values: list[dict[str, Any]] = []

        normalized_values: list[dict[str, Any]] = []
        for value_data in values:
            if isinstance(value_data, CustomFieldValueItem):
                normalized_values.append(
                    {
                        "field_id": None,
                        "field_name": value_data.field_name,
                        "value": value_data.value,
                    }
                )
            else:
                normalized_values.append(
                    {
                        "field_id": value_data.get("field_id"),
                        "field_name": value_data.get("field_name"),
                        "value": value_data.get("value"),
                    }
                )

        field_ids = self._ordered_unique(
            [
                item.get("field_id")
                for item in normalized_values
                if item.get("field_id") is not None
            ]
        )
        field_names = self._ordered_unique(
            [
                item.get("field_name")
                for item in normalized_values
                if item.get("field_id") is None and item.get("field_name") is not None
            ]
        )

        fields_by_id: dict[str, AssetCustomField] = {}
        if field_ids:
            fields = await custom_field_crud.get_multi_by_ids_async(db, field_ids)
            fields_by_id = {
                str(field.id): field for field in fields if field.id is not None
            }

        fields_by_name: dict[str, AssetCustomField] = {}
        if field_names:
            fields = await custom_field_crud.get_multi_by_field_names_async(
                db, field_names
            )
            fields_by_name = {
                str(field.field_name): field
                for field in fields
                if field.field_name is not None
            }

        for value_data in normalized_values:
            field_id_raw = value_data.get("field_id")
            field_name_raw = value_data.get("field_name")
            field_value: Any = value_data.get("value")

            field = None
            field_id = str(field_id_raw).strip() if field_id_raw is not None else None
            field_name = (
                str(field_name_raw).strip() if field_name_raw is not None else None
            )

            if field_id:
                field = fields_by_id.get(field_id)
            elif field_name:
                field = fields_by_name.get(field_name)
                if field:
                    field_id = field.id

            if not field or not field_id:
                continue

            is_valid, error_message = self.validate_field_value(field, field_value)
            if not is_valid:
                raise BusinessValidationError(
                    message=error_message or "字段值验证失败",
                    field_errors={"custom_fields": [error_message or "字段值无效"]},
                )

            updated_values.append(
                {
                    "field_id": field_id,
                    "field_name": field.field_name,
                    "display_name": field.display_name,
                    "value": field_value,
                    "field_type": field.field_type,
                }
            )

        return updated_values

    async def get_asset_field_values_async(
        self, db: AsyncSession, *, asset_id: str
    ) -> list[dict[str, Any]]:
        return await custom_field_crud.get_asset_field_values_async(
            db, asset_id=asset_id
        )

    async def validate_custom_field_value_async(
        self,
        db: AsyncSession,
        *,
        field_id: str,
        value: Any,
    ) -> tuple[bool, str | None]:
        field = await self.get_custom_field_async(db, field_id=field_id)
        if not field:
            raise ResourceNotFoundError("字段", field_id)
        return self.validate_field_value(field, value)

    async def toggle_active_status_async(
        self, db: AsyncSession, *, id: str
    ) -> AssetCustomField:
        field = await custom_field_crud.get(db, id)
        if not field:
            raise ResourceNotFoundError("字段", id)

        field.is_active = not field.is_active
        db.add(field)
        await db.commit()
        await db.refresh(field)
        return field

    async def update_sort_orders_async(
        self, db: AsyncSession, *, sort_data: list[dict[str, Any]]
    ) -> list[AssetCustomField]:
        updates_by_id: dict[str, int] = {}
        ordered_ids: list[str] = []
        for item in sort_data:
            field_id = item.get("id")
            sort_order = item.get("sort_order")
            if field_id is None or sort_order is None:
                continue
            normalized_id = str(field_id).strip()
            if normalized_id == "":
                continue
            if normalized_id not in updates_by_id:
                ordered_ids.append(normalized_id)
            updates_by_id[normalized_id] = sort_order

        if len(ordered_ids) == 0:
            return []

        fields = await custom_field_crud.get_multi_by_ids_async(db, ordered_ids)
        fields_by_id = {
            str(field.id): field for field in fields if field.id is not None
        }

        updated_fields: list[AssetCustomField] = []
        for field_id in ordered_ids:
            field = fields_by_id.get(field_id)
            if not field:
                continue
            field.sort_order = updates_by_id[field_id]
            db.add(field)
            updated_fields.append(field)

        await db.commit()
        return updated_fields


custom_field_service = CustomFieldService()
