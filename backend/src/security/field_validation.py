"""
Model field validation utilities.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from ..core.exception_handler import InvalidRequestError
from ..crud import field_whitelist as crud_field_whitelist
from ..models.asset import Asset
from ..models.contact import Contact
from ..models.organization import Organization
from ..models.rent_contract import RentContract

logger = logging.getLogger(__name__)

MODEL_REGISTRY: dict[str, type] = {
    "Asset": Asset,
    "RentContract": RentContract,
    "Organization": Organization,
    "Contact": Contact,
}


def _get_whitelist_for_model(model_class: type):
    """Resolve whitelist with test patch support."""
    security_module = sys.modules.get("src.security.security")
    if security_module is not None:
        get_whitelist = getattr(security_module, "get_whitelist_for_model", None)
        if callable(get_whitelist):
            return get_whitelist(model_class)
    return crud_field_whitelist.get_whitelist_for_model(model_class)


class FieldValidator:
    """
    统一的字段验证器

    Prevents arbitrary field access attacks by validating all field names
    against model-specific whitelists before allowing database queries.
    """

    @staticmethod
    def _get_model_class(model_name: str) -> type:
        """
        根据模型名称获取模型类

        Args:
            model_name: 模型名称

        Returns:
            type: 模型类
        """
        model_class = MODEL_REGISTRY.get(model_name)
        if not model_class:
            raise InvalidRequestError(
                f"未知的模型: {model_name}",
                details={
                    "model_name": model_name,
                    "available_models": list(MODEL_REGISTRY.keys()),
                },
            )

        return model_class

    @staticmethod
    def validate_field(
        model_name: str, field: str, raise_on_invalid: bool = True
    ) -> bool:
        """
        验证字段是否允许查询

        Args:
            model_name: 模型名称
            field: 字段名
            raise_on_invalid: 是否在无效时抛出异常

        Returns:
            bool: 字段是否有效
        """
        model_class = FieldValidator._get_model_class(model_name)
        whitelist = _get_whitelist_for_model(model_class)

        is_valid = whitelist.can_filter(field)

        if not is_valid and raise_on_invalid:
            logger.warning(
                f"Blocked attempt to filter by unauthorized field: {field} "
                f"for model {model_name}"
            )
            raise InvalidRequestError(
                f"不允许按字段查询: {field}",
                field=field,
                details={
                    "error": "Invalid filter field",
                },
            )

        return is_valid

    @staticmethod
    def validate_filter_fields(
        model_name: str, fields: list[str], raise_on_invalid: bool = True
    ) -> tuple[list[str], list[str]]:
        valid_fields: list[str] = []
        invalid_fields: list[str] = []

        for field in fields:
            if FieldValidator.validate_field(model_name, field, raise_on_invalid=False):
                valid_fields.append(field)
            else:
                invalid_fields.append(field)

        if invalid_fields and raise_on_invalid:
            raise InvalidRequestError(
                "不允许按字段查询",
                details={"invalid_fields": invalid_fields},
            )

        return valid_fields, invalid_fields

    @staticmethod
    def validate_sort_field(
        model_name: str, field: str, raise_on_invalid: bool = True
    ) -> bool:
        """
        验证排序字段是否允许

        Args:
            model_name: 模型名称
            field: 排序字段
            raise_on_invalid: 是否在无效时抛出异常

        Returns:
            bool: 字段是否有效
        """
        model_class = FieldValidator._get_model_class(model_name)
        whitelist = _get_whitelist_for_model(model_class)

        is_valid = whitelist.can_sort(field)

        if not is_valid and raise_on_invalid:
            logger.warning(
                f"Blocked attempt to sort by unauthorized field: {field} "
                f"for model {model_name}"
            )
            raise InvalidRequestError(
                f"不允许按字段排序: {field}",
                field=field,
                details={
                    "error": "Invalid sort field",
                },
            )

        return is_valid

    @staticmethod
    def validate_search_fields(
        model_name: str, fields: list[str], raise_on_invalid: bool = True
    ) -> tuple[list[str], list[str]]:
        valid_fields: list[str] = []
        invalid_fields: list[str] = []

        for field in fields:
            if FieldValidator.validate_search_field(
                model_name, field, raise_on_invalid=False
            ):
                valid_fields.append(field)
            else:
                invalid_fields.append(field)

        if invalid_fields and raise_on_invalid:
            raise InvalidRequestError(
                "不允许按字段搜索",
                details={"invalid_fields": invalid_fields},
            )

        return valid_fields, invalid_fields

    @staticmethod
    def validate_search_field(
        model_name: str, field: str, raise_on_invalid: bool = True
    ) -> bool:
        """
        验证搜索字段是否允许

        Args:
            model_name: 模型名称
            field: 搜索字段
            raise_on_invalid: 是否在无效时抛出异常

        Returns:
            bool: 字段是否有效
        """
        model_class = FieldValidator._get_model_class(model_name)
        whitelist = _get_whitelist_for_model(model_class)

        is_valid = whitelist.can_search(field)

        if not is_valid and raise_on_invalid:
            logger.warning(
                f"Blocked attempt to search by unauthorized field: {field} "
                f"for model {model_name}"
            )
            raise InvalidRequestError(
                f"不允许按字段搜索: {field}",
                field=field,
                details={
                    "error": "Invalid search field",
                },
            )

        return is_valid

    @staticmethod
    def validate_group_by_field(
        model_name: str, field: str, raise_on_invalid: bool = True
    ) -> bool:
        """
        验证分组字段是否允许

        Args:
            model_name: 模型名称
            field: Group by 字段
            raise_on_invalid: 是否在无效时抛出异常

        Returns:
            bool: 字段是否有效
        """
        model_class = FieldValidator._get_model_class(model_name)
        whitelist = _get_whitelist_for_model(model_class)

        is_valid = whitelist.can_filter(field)

        if not is_valid and raise_on_invalid:
            logger.warning(
                f"Blocked attempt to group by unauthorized field: {field} "
                f"for model {model_name}"
            )
            raise InvalidRequestError(
                f"不允许按字段分组: {field}",
                field=field,
                details={
                    "error": "Invalid group_by field",
                },
            )

        return is_valid

    @staticmethod
    def sanitize_filters(
        model_name: str, filters: dict[str, Any], strict: bool = False
    ) -> dict[str, Any]:
        valid_fields, invalid_fields = FieldValidator.validate_filter_fields(
            model_name, list(filters.keys()), raise_on_invalid=False
        )

        if invalid_fields and strict:
            raise InvalidRequestError(
                "不允许按字段查询",
                details={"invalid_fields": invalid_fields},
            )

        return {
            field: value for field, value in filters.items() if field in valid_fields
        }

    @staticmethod
    def get_allowed_fields(model_name: str, field_type: str) -> list[str]:
        model_class = FieldValidator._get_model_class(model_name)
        whitelist = _get_whitelist_for_model(model_class)

        if field_type == "filter":
            fields = whitelist.filter_fields
        elif field_type == "search":
            fields = whitelist.search_fields
        elif field_type == "sort":
            fields = whitelist.sort_fields
        else:
            raise InvalidRequestError(
                f"未知的字段类型: {field_type}",
                details={"field_type": field_type},
            )

        return sorted(fields)
