"""
字段验证框架 - 防止任意字段查询导致的数据泄露

提供统一的字段验证机制，确保 API 端点只允许查询白名单字段。

Security Design:
- Whitelist-based validation (默认拒绝)
- Per-model field whitelists
- Operation-specific validation (filter, search, sort, group_by)
- Clear error messages for debugging
- Integration with existing crud/field_whitelist.py

Usage:
    from src.security.field_validator import FieldValidator

    # Validate filter fields
    FieldValidator.validate_filter_fields("Asset", ["name", "status"])

    # Validate group_by field
    FieldValidator.validate_group_by_field("Asset", "ownership_status")
"""

import logging
from typing import Any

from ..core.api_errors import bad_request

from ..crud.field_whitelist import get_whitelist_for_model
from ..models.asset import Asset
from ..models.rent_contract import RentContract
from ..models.organization import Organization
from ..models.contact import Contact

logger = logging.getLogger(__name__)


# ============================================================================
# Model Registry - Map string names to model classes
# ============================================================================
MODEL_REGISTRY: dict[str, type] = {
    "Asset": Asset,
    "RentContract": RentContract,
    "Organization": Organization,
    "Contact": Contact,
}


class FieldValidator:
    """
    统一的字段验证器

    Prevents arbitrary field access attacks by validating all field names
    against model-specific whitelists before allowing database queries.
    """

    @staticmethod
    def _get_model_class(model_name: str) -> type:
        """
        Get model class from registry.

        Args:
            model_name: Model name (e.g., "Asset", "RentContract")

        Returns:
            Model class

        Raises:
            ValueError: If model not found in registry
        """
        if model_name not in MODEL_REGISTRY:
            raise ValueError(
                f"Unknown model: {model_name}. "
                f"Valid models: {', '.join(MODEL_REGISTRY.keys())}"
            )
        return MODEL_REGISTRY[model_name]

    @staticmethod
    def validate_filter_fields(
        model_name: str,
        fields: list[str],
        raise_on_invalid: bool = True
    ) -> tuple[list[str], list[str]]:
        """
        验证过滤字段是否在白名单中

        Args:
            model_name: 模型名称 (e.g., "Asset")
            fields: 要验证的字段列表
            raise_on_invalid: 是否在发现无效字段时抛出异常

        Returns:
            (valid_fields, invalid_fields) 元组

        Raises:
            HTTPException: 如果 raise_on_invalid=True 且发现无效字段
        """
        model_class = FieldValidator._get_model_class(model_name)
        whitelist = get_whitelist_for_model(model_class)

        valid_fields = []
        invalid_fields = []

        for field in fields:
            if whitelist.can_filter(field):
                valid_fields.append(field)
            else:
                invalid_fields.append(field)

        if invalid_fields and raise_on_invalid:
            logger.warning(
                f"Blocked attempt to filter on unauthorized fields: {invalid_fields} "
                f"for model {model_name}"
            )
            raise bad_request(
                f"不允许查询字段: {', '.join(invalid_fields)}。"
                "请检查 API 文档了解允许的过滤字段。",
                details={
                    "error": "Invalid filter fields",
                    "invalid_fields": invalid_fields,
                }
            )

        if invalid_fields:
            logger.info(
                f"Filtered out unauthorized fields: {invalid_fields} for {model_name}"
            )

        return valid_fields, invalid_fields

    @staticmethod
    def validate_search_fields(
        model_name: str,
        fields: list[str],
        raise_on_invalid: bool = True
    ) -> tuple[list[str], list[str]]:
        """
        验证搜索字段是否在白名单中

        Args:
            model_name: 模型名称
            fields: 要验证的字段列表
            raise_on_invalid: 是否在发现无效字段时抛出异常

        Returns:
            (valid_fields, invalid_fields) 元组
        """
        model_class = FieldValidator._get_model_class(model_name)
        whitelist = get_whitelist_for_model(model_class)

        valid_fields = []
        invalid_fields = []

        for field in fields:
            if whitelist.can_search(field):
                valid_fields.append(field)
            else:
                invalid_fields.append(field)

        if invalid_fields and raise_on_invalid:
            logger.warning(
                f"Blocked attempt to search on unauthorized fields: {invalid_fields} "
                f"for model {model_name}"
            )
            raise bad_request(
                f"不允许搜索字段: {', '.join(invalid_fields)}",
                details={
                    "error": "Invalid search fields",
                    "invalid_fields": invalid_fields,
                }
            )

        return valid_fields, invalid_fields

    @staticmethod
    def validate_sort_field(
        model_name: str,
        field: str,
        raise_on_invalid: bool = True
    ) -> bool:
        """
        验证排序字段是否在白名单中

        Args:
            model_name: 模型名称
            field: 排序字段
            raise_on_invalid: 是否在无效时抛出异常

        Returns:
            bool: 字段是否有效

        Raises:
            HTTPException: 如果字段无效且 raise_on_invalid=True
        """
        model_class = FieldValidator._get_model_class(model_name)
        whitelist = get_whitelist_for_model(model_class)

        is_valid = whitelist.can_sort(field)

        if not is_valid and raise_on_invalid:
            logger.warning(
                f"Blocked attempt to sort on unauthorized field: {field} "
                f"for model {model_name}"
            )
            raise bad_request(
                f"不允许按字段排序: {field}",
                field=field,
                details={
                    "error": "Invalid sort field",
                }
            )

        return is_valid

    @staticmethod
    def validate_group_by_field(
        model_name: str,
        field: str,
        raise_on_invalid: bool = True
    ) -> bool:
        """
        验证 group_by 字段是否在白名单中

        Note: Group_by uses filter_fields whitelist (same security level)

        Args:
            model_name: 模型名称
            field: Group by 字段
            raise_on_invalid: 是否在无效时抛出异常

        Returns:
            bool: 字段是否有效

        Raises:
            HTTPException: 如果字段无效且 raise_on_invalid=True
        """
        model_class = FieldValidator._get_model_class(model_name)
        whitelist = get_whitelist_for_model(model_class)

        # Group by should use filter fields (same security level)
        is_valid = whitelist.can_filter(field)

        if not is_valid and raise_on_invalid:
            logger.warning(
                f"Blocked attempt to group by unauthorized field: {field} "
                f"for model {model_name}"
            )
            raise bad_request(
                f"不允许按字段分组: {field}。"
                "请检查 API 文档了解允许的分组字段。",
                field=field,
                details={
                    "error": "Invalid group_by field",
                }
            )

        return is_valid

    @staticmethod
    def get_allowed_fields(
        model_name: str,
        operation: str = "filter"
    ) -> set[str]:
        """
        获取模型允许的字段列表

        Args:
            model_name: 模型名称
            operation: 操作类型 ("filter", "search", "sort")

        Returns:
            允许的字段集合
        """
        model_class = FieldValidator._get_model_class(model_name)
        whitelist = get_whitelist_for_model(model_class)

        if operation == "filter":
            return whitelist.filter_fields
        elif operation == "search":
            return whitelist.search_fields
        elif operation == "sort":
            return whitelist.sort_fields
        else:
            raise ValueError(
                f"Unknown operation: {operation}. "
                "Valid operations: filter, search, sort"
            )

    @staticmethod
    def sanitize_filters(
        model_name: str,
        filters: dict[str, Any],
        strict: bool = False
    ) -> dict[str, Any]:
        """
        清理过滤器字典，移除不允许的字段

        Args:
            model_name: 模型名称
            filters: 原始过滤器字典
            strict: 严格模式 - 发现无效字段时抛出异常

        Returns:
            清理后的过滤器字典

        Raises:
            HTTPException: 如果 strict=True 且发现无效字段
        """
        if not filters:
            return {}

        valid_fields, invalid_fields = FieldValidator.validate_filter_fields(
            model_name,
            list(filters.keys()),
            raise_on_invalid=strict
        )

        # Return only valid fields
        sanitized = {k: v for k, v in filters.items() if k in valid_fields}

        if invalid_fields and not strict:
            logger.info(
                f"Removed unauthorized filter fields: {invalid_fields} "
                f"from {model_name} query"
            )

        return sanitized


# ============================================================================
# Convenience Functions
# ============================================================================

def validate_asset_filters(fields: list[str]) -> None:
    """快捷方法: 验证 Asset 过滤字段"""
    FieldValidator.validate_filter_fields("Asset", fields)


def validate_contract_filters(fields: list[str]) -> None:
    """快捷方法: 验证 RentContract 过滤字段"""
    FieldValidator.validate_filter_fields("RentContract", fields)


def get_allowed_asset_fields(operation: str = "filter") -> set[str]:
    """快捷方法: 获取 Asset 允许的字段"""
    return FieldValidator.get_allowed_fields("Asset", operation)
