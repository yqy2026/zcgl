import json
import re
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from ...crud.custom_field import custom_field_crud
from ...models.asset import AssetCustomField
from ...schemas.asset import AssetCustomFieldCreate, AssetCustomFieldUpdate


class CustomFieldService:
    """自定义字段服务层"""

    def create_custom_field(
        self, db: Session, *, obj_in: AssetCustomFieldCreate
    ) -> AssetCustomField:
        """创建自定义字段"""
        existing = custom_field_crud.get_by_field_name(db, field_name=obj_in.field_name)
        if existing:
            raise ValueError(f"字段名 {obj_in.field_name} 已存在")

        return custom_field_crud.create(db, obj_in=obj_in)

    def update_custom_field(
        self, db: Session, *, id: str, obj_in: AssetCustomFieldUpdate
    ) -> AssetCustomField:
        """更新自定义字段"""
        field = custom_field_crud.get(db, id)
        if not field:
            raise ValueError(f"字段 {id} 不存在")

        if obj_in.field_name and obj_in.field_name != field.field_name:
            existing = custom_field_crud.get_by_field_name(
                db, field_name=obj_in.field_name
            )
            if existing and existing.id != id:
                raise ValueError(f"字段名 {obj_in.field_name} 已存在")

        return custom_field_crud.update(db, db_obj=field, obj_in=obj_in)

    def delete_custom_field(self, db: Session, *, id: str) -> AssetCustomField:
        """删除自定义字段"""
        field = custom_field_crud.get(db, id)
        if not field:
            raise ValueError(f"字段 {id} 不存在")
        return custom_field_crud.remove(db, id=id)

    def validate_field_value(
        self, field: AssetCustomField, value: Any
    ) -> tuple[bool, str | None]:
        """验证字段值是否符合配置要求 (Refactored from CRUD)"""
        try:
            # 必填验证
            if field.is_required and (value is None or value == ""):
                return False, f"字段 {field.display_name} 为必填项"

            # 如果值为空且非必填，则通过验证
            if value is None or value == "":
                return True, None

            # 根据字段类型验证
            if field.field_type == "text":
                if not isinstance(value, str):
                    return False, f"字段 {field.display_name} 必须为文本类型"

                # 检查长度限制
                if field.validation_rules:
                    rules_str: str | None = (
                        field.validation_rules
                        if isinstance(field.validation_rules, str)
                        else None
                    )
                    rules = json.loads(rules_str) if rules_str else field.validation_rules
                    max_length = rules.get("max_length")
                    min_length = rules.get("min_length")

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
                        rules_str: str | None = (
                            field.validation_rules
                            if isinstance(field.validation_rules, str)
                            else None
                        )
                        rules = json.loads(rules_str) if rules_str else field.validation_rules
                        max_value = rules.get("max_value")
                        min_value = rules.get("min_value")

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
                        rules_str: str | None = (
                            field.validation_rules
                            if isinstance(field.validation_rules, str)
                            else None
                        )
                        rules = json.loads(rules_str) if rules_str else field.validation_rules
                        max_value = rules.get("max_value")
                        min_value = rules.get("min_value")

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
                    options_list = (
                        json.loads(field_options_str) if field_options_str else None
                    )
                    options = options_list if options_list else field.field_options
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

    def update_asset_field_values(
        self, db: Session, *, asset_id: str, values: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """更新资产的自定义字段值 (Refactored from CRUD)"""
        updated_values: list[dict[str, Any]] = []

        for value_data in values:
            field_id = value_data.get("field_id")
            field_value = value_data.get("value")

            if not field_id:
                continue

            # 获取字段配置
            field = custom_field_crud.get(db, field_id)
            if not field:
                continue

            # 验证字段值
            is_valid, error_message = self.validate_field_value(field, field_value)
            if not is_valid:
                raise ValueError(error_message)

            # NOTE: logic to update database is currently a stub in original CRUD too.
            # Keeping the stub behavior.
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

    def get_asset_field_values(
        self, db: Session, *, asset_id: str
    ) -> list[dict[str, Any]]:
        """获取资产的自定义字段值"""
        # Delegating to CRUD or implementing logic.
        # Original CRUD logic was empty stub.
        return custom_field_crud.get_asset_field_values(db, asset_id=asset_id)

    def toggle_active_status(self, db: Session, *, id: str) -> AssetCustomField:
        """切换启用状态"""
        field = custom_field_crud.get(db, id)
        if not field:
            raise ValueError(f"字段 {id} 不存在")

        field.is_active = not field.is_active
        db.add(field)
        db.commit()
        db.refresh(field)
        return field

    def update_sort_orders(
        self, db: Session, *, sort_data: list[dict[str, Any]]
    ) -> list[AssetCustomField]:
        """批量更新排序"""
        updated_fields: list[AssetCustomField] = []

        for item in sort_data:
            field_id = item.get("id")
            sort_order = item.get("sort_order")

            if field_id and sort_order is not None:
                field = custom_field_crud.get(db, field_id)
                if field:
                    field.sort_order = sort_order
                    db.add(field)
                    updated_fields.append(field)

        db.commit()
        for field in updated_fields:
            db.refresh(field)

        return updated_fields


custom_field_service = CustomFieldService()
