"""
资产批量操作验证器

模块化的资产数据验证逻辑，提供可重用的验证方法
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class AssetBatchValidator:
    """
    资产批量操作验证器

    提供静态方法验证资产数据的完整性、正确性和一致性
    """

    # 必填字段定义
    REQUIRED_FIELDS = [
        "property_name",
        "address",
        "ownership_status",
        "property_nature",
        "usage_status",
    ]

    # 数值字段定义
    NUMERIC_FIELDS = [
        "land_area",
        "actual_property_area",
        "rentable_area",
        "rented_area",
        "non_commercial_area",
    ]

    # 日期字段定义
    DATE_FIELDS = [
        "operation_agreement_start_date",
        "operation_agreement_end_date",
    ]

    # 建议字段定义
    SUGGESTION_FIELDS = [
        ("land_area", "建议填写土地面积"),
        ("rentable_area", "建议填写可出租面积"),
        ("rented_area", "建议填写已出租面积"),
    ]

    @staticmethod
    def validate_required_fields(data: dict[str, Any]) -> list[dict[str, str]]:
        """
        验证必填字段

        Args:
            data: 待验证的资产数据字典

        Returns:
            错误列表，格式: [{"field": "field_name", "error": "error_message"}]
        """
        errors = []

        for field in AssetBatchValidator.REQUIRED_FIELDS:
            if field not in data or not data[field]:
                errors.append({"field": field, "error": f"{field}为必填字段"})

        return errors

    @staticmethod
    def validate_numeric_fields(data: dict[str, Any]) -> list[dict[str, str]]:
        """
        验证数值字段

        Args:
            data: 待验证的资产数据字典

        Returns:
            错误列表
        """
        errors = []

        for field in AssetBatchValidator.NUMERIC_FIELDS:
            if field in data and data[field] is not None:
                try:
                    float(data[field])
                except (ValueError, TypeError):
                    errors.append({"field": field, "error": f"{field}必须是有效的数字"})

        return errors

    @staticmethod
    def validate_date_fields(data: dict[str, Any]) -> list[dict[str, str]]:
        """
        验证日期字段

        Args:
            data: 待验证的资产数据字典

        Returns:
            错误列表
        """
        errors = []

        for field in AssetBatchValidator.DATE_FIELDS:
            if field in data and data[field] is not None:
                if isinstance(data[field], str):
                    # 验证 YYYY-MM-DD 格式
                    if not re.match(r"^\d{4}-\d{2}-\d{2}$", data[field]):
                        errors.append(
                            {
                                "field": field,
                                "error": f"{field}日期格式应为 YYYY-MM-DD",
                            }
                        )

        return errors

    @staticmethod
    def validate_area_consistency(data: dict[str, Any]) -> list[dict[str, str]]:
        """
        验证面积一致性

        确保已出租面积不超过可出租面积

        Args:
            data: 待验证的资产数据字典

        Returns:
            错误列表
        """
        errors = []

        rentable_area = data.get("rentable_area")
        rented_area = data.get("rented_area")

        if rentable_area is not None and rented_area is not None:
            try:
                if float(rented_area) > float(rentable_area):
                    errors.append(
                        {
                            "field": "rented_area",
                            "error": "已出租面积不能大于可出租面积",
                        }
                    )
            except (ValueError, TypeError):
                # 如果类型转换失败，数值验证会捕获这个错误
                pass

        return errors

    @staticmethod
    def get_suggestion_warnings(data: dict[str, Any]) -> list[dict[str, str]]:
        """
        获取建议性警告

        对于缺失但非必填的字段，提供建议性警告

        Args:
            data: 待验证的资产数据字典

        Returns:
            警告列表
        """
        warnings = []

        for field, suggestion in AssetBatchValidator.SUGGESTION_FIELDS:
            if field not in data or data[field] is None:
                warnings.append({"field": field, "message": suggestion})

        return warnings

    @classmethod
    def validate_all(
        cls, data: dict[str, Any], validate_rules: list[str] | None = None
    ) -> tuple[bool, list[dict[str, str]], list[dict[str, str]], list[str]]:
        """
        执行所有验证

        Args:
            data: 待验证的资产数据字典
            validate_rules: 验证规则列表，默认为 ["required_fields", "data_format"]

        Returns:
            (is_valid, errors, warnings, validated_fields) 元组:
            - is_valid: 是否通过验证
            - errors: 错误列表
            - warnings: 警告列表
            - validated_fields: 已验证的字段列表
        """
        validate_rules = validate_rules or ["required_fields", "data_format"]
        errors = []
        warnings = []
        validated_fields = []

        # 验证必填字段
        if "required_fields" in validate_rules:
            field_errors = cls.validate_required_fields(data)
            errors.extend(field_errors)
            # 记录通过验证的必填字段
            for field in cls.REQUIRED_FIELDS:
                if field in data and data[field]:
                    validated_fields.append(field)

        # 验证数据格式
        if "data_format" in validate_rules:
            # 数值字段
            numeric_errors = cls.validate_numeric_fields(data)
            errors.extend(numeric_errors)
            # 记录通过验证的数值字段
            for field in cls.NUMERIC_FIELDS:
                if field in data and data[field] is not None:
                    try:
                        float(data[field])
                        validated_fields.append(field)
                    except (ValueError, TypeError):
                        pass

            # 日期字段
            date_errors = cls.validate_date_fields(data)
            errors.extend(date_errors)
            # 记录通过验证的日期字段
            for field in cls.DATE_FIELDS:
                if field in data and data[field] is not None:
                    if isinstance(data[field], str) and re.match(
                        r"^\d{4}-\d{2}-\d{2}$", data[field]
                    ):
                        validated_fields.append(field)

            # 面积一致性
            consistency_errors = cls.validate_area_consistency(data)
            errors.extend(consistency_errors)

        # 获取建议性警告
        warnings = cls.get_suggestion_warnings(data)

        is_valid = len(errors) == 0
        return is_valid, errors, warnings, validated_fields
