from typing import Any
"""
自定义字段CRUD操作
"""

import json
from datetime import datetime
from decimal import Decimal


from sqlalchemy.orm import Session

from ..models.asset import AssetCustomField
from ..schemas.asset import AssetCustomFieldCreate, AssetCustomFieldUpdate
from .base import CRUDBase


class CRUDCustomField(
    CRUDBase[AssetCustomField, AssetCustomFieldCreate, AssetCustomFieldUpdate]
):
    """自定义字段CRUD操作类"""

    def get_by_field_name(
        self, db: Session, *, field_name: str
    ) -> AssetCustomField | None:
        """根据字段名获取字段配置"""
        return (
            db.query(AssetCustomField)
            .filter(AssetCustomField.field_name == field_name)
            .first()
        )

    def get_multi_with_filters(
        self,
        db: Session,
        *,
        filters: dict[str, Any] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AssetCustomField]:
        """根据筛选条件获取字段列表"""
        query = db.query(self.model)

        if filters:
            if "asset_id" in filters:
                # 这里可以扩展为根据资产ID获取相关字段
                pass
            if "field_type" in filters:
                query = query.filter(
                    AssetCustomField.field_type == filters["field_type"]
                )
            if "is_required" in filters:
                query = query.filter(
                    AssetCustomField.is_required == filters["is_required"]
                )
            if "is_active" in filters:
                query = query.filter(AssetCustomField.is_active == filters["is_active"])

        return (
            query.order_by(AssetCustomField.sort_order, AssetCustomField.created_at)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_active_fields(self, db: Session) -> list[AssetCustomField]:
        """获取所有启用的字段"""
        return (
            db.query(AssetCustomField)
            .filter(AssetCustomField.is_active)
            .order_by(AssetCustomField.sort_order, AssetCustomField.created_at)
            .all()
        )

    def validate_field_value(
        self, field: AssetCustomField, value: Any
    ) -> tuple[bool, str | None]:
        """验证字段值是否符合配置要求"""
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
                    rules = (
                        json.loads(field.validation_rules)
                        if isinstance(field.validation_rules, str)
                        else field.validation_rules
                    )
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
                        rules = (
                            json.loads(field.validation_rules)
                            if isinstance(field.validation_rules, str)
                            else field.validation_rules
                        )
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
                        rules = (
                            json.loads(field.validation_rules)
                            if isinstance(field.validation_rules, str)
                            else field.validation_rules
                        )
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
                    options = (
                        json.loads(field.field_options)
                        if isinstance(field.field_options, str)
                        else field.field_options
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
                import re

                email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                if not re.match(email_pattern, str(value)):
                    return False, f"字段 {field.display_name} 邮箱格式不正确"

            elif field.field_type == "phone":
                import re

                phone_pattern = r"^[0-9\-\+\(\)\s]{10,20}$"
                if not re.match(phone_pattern, str(value)):
                    return False, f"字段 {field.display_name} 电话格式不正确"

            elif field.field_type == "url":
                import re

                url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
                if not re.match(url_pattern, str(value)):
                    return False, f"字段 {field.display_name} URL格式不正确"

            return True, None

        except Exception as e:
            return False, f"验证字段 {field.display_name} 时发生错误: {str(e)}"

    def get_asset_field_values(
        self, db: Session, *, asset_id: str
    ) -> list[dict[str, Any]]:
        """获取资产的自定义字段值"""
        # 这里需要实现获取资产自定义字段值的逻辑
        # 由于我们还没有创建存储字段值的表，这里返回空列表
        # 在实际实现中，需要创建一个 asset_field_values 表来存储值
        return []

    def update_asset_field_values(
        self, db: Session, *, asset_id: str, values: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """更新资产的自定义字段值"""
        # 这里需要实现更新资产自定义字段值的逻辑
        # 在实际实现中，需要：
        # 1. 验证每个字段值
        # 2. 更新或插入到 asset_field_values 表
        # 3. 返回更新后的值

        updated_values = []

        for value_data in values:
            field_id = value_data.get("field_id")
            field_value = value_data.get("value")

            if not field_id:
                continue

            # 获取字段配置
            field = self.get(db=db, id=field_id)
            if not field:
                continue

            # 验证字段值
            is_valid, error_message = self.validate_field_value(field, field_value)
            if not is_valid:
                raise ValueError(error_message)

            # 这里应该更新数据库中的值
            # 暂时只返回验证通过的值
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

    def toggle_active_status(self, db: Session, *, id: str) -> AssetCustomField | None:
        """切换启用状态"""
        field = self.get(db=db, id=id)
        if field:
            field.is_active = not field.is_active
            db.add(field)
            db.commit()
            db.refresh(field)
        return field

    def update_sort_orders(
        self, db: Session, *, sort_data: list[dict[str, Any]]
    ) -> list[AssetCustomField]:
        """批量更新排序"""
        updated_fields = []

        for item in sort_data:
            field_id = item.get("id")
            sort_order = item.get("sort_order")

            if field_id and sort_order is not None:
                field = self.get(db=db, id=field_id)
                if field:
                    field.sort_order = sort_order
                    db.add(field)
                    updated_fields.append(field)

        db.commit()
        return updated_fields


# 创建自定义字段CRUD实例
custom_field_crud = CRUDCustomField(AssetCustomField)
