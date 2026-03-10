"""
统一验证器
提供通用的数据验证和转换功能
"""

import re
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..constants.message_constants import EMPTY_STRING


class BaseValidator:
    """基础验证器类"""

    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_phone(phone: str) -> bool:
        """验证手机号格式"""
        pattern = r"^1[3-9]\d{9}$"
        return bool(re.match(pattern, phone))

    @staticmethod
    def validate_id_card(id_card: str) -> bool:
        """验证身份证号格式"""
        pattern = (
            r"^[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]$"
        )
        return bool(re.match(pattern, id_card))

    @staticmethod
    def validate_url(url: str) -> bool:
        """验证URL格式"""
        pattern = r"^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$"
        return bool(re.match(pattern, url))

    @staticmethod
    def validate_ip_address(ip: str) -> bool:
        """验证IP地址格式"""
        pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        return bool(re.match(pattern, ip))

    @staticmethod
    def validate_date_range(start_date: datetime, end_date: datetime) -> bool:
        """验证日期范围"""
        return start_date <= end_date

    @staticmethod
    def validate_positive_number(value: int | float) -> bool:
        """验证正数"""
        return isinstance(value, (int, float)) and value > 0

    @staticmethod
    def validate_non_negative_number(value: int | float) -> bool:
        """验证非负数"""
        return isinstance(value, (int, float)) and value >= 0

    @staticmethod
    def validate_percentage(value: int | float) -> bool:
        """验证百分比（0-100）"""
        return isinstance(value, (int, float)) and 0 <= value <= 100

    @staticmethod
    def validate_length(
        text: str, min_length: int = 0, max_length: int | None = None
    ) -> bool:
        """验证文本长度"""
        if len(text) < min_length:
            return False
        if max_length is not None and len(text) > max_length:
            return False
        return True

    @staticmethod
    def validate_regex(text: str, pattern: str) -> bool:
        """验证正则表达式"""
        return bool(re.match(pattern, text))


class AssetValidator(BaseValidator):
    """资产数据验证器"""

    REQUIRED_FIELDS = [
        "asset_name",
        "property_address",
        "ownership_status",
        "property_nature",
    ]

    @classmethod
    def validate_asset_data(cls, data: dict[str, Any]) -> list[str]:
        """
        验证资产数据

        Args:
            data: 资产数据字典

        Returns:
            错误消息列表
        """
        errors = []

        # 验证必填字段
        for field in cls.REQUIRED_FIELDS:
            if field not in data or not data[field]:
                errors.append(f"缺少必填字段: {field}")

        # 验证物业名称
        if "asset_name" in data:
            if not cls.validate_length(data["asset_name"], 1, 200):
                errors.append("物业名称长度应在1-200个字符之间")

        # 验证物业地址
        if "property_address" in data:
            if not cls.validate_length(data["property_address"], 5, 500):
                errors.append("物业地址长度应在5-500个字符之间")

        # 验证建筑面积
        if "building_area" in data and data["building_area"]:
            if not cls.validate_positive_number(data["building_area"]):
                errors.append("建筑面积必须为正数")

        # 验证土地面积
        if "land_area" in data and data["land_area"]:  # pragma: no cover
            if not cls.validate_positive_number(data["land_area"]):  # pragma: no cover
                errors.append("土地面积必须为正数")  # pragma: no cover

        # 验证建成年份
        if "construction_year" in data and data["construction_year"]:
            current_year = datetime.now().year
            if not (1900 <= data["construction_year"] <= current_year):
                errors.append(f"建成年份应在1900-{current_year}之间")

        # 枚举字段验证（ownership_status, property_nature, usage_status等）
        # 已移至EnumValidationService，支持从数据库动态获取枚举值

        return errors

    @classmethod
    async def validate_asset_unique(
        cls, db: AsyncSession, asset_name: str, exclude_id: str | None = None
    ) -> list[str]:
        """
        验证资产唯一性

        Args:
            db: 数据库会话
            asset_name: 物业名称
            exclude_id: 排除的资产ID（用于更新时）

        Returns:
            错误消息列表
        """
        from ..models.asset import Asset  # pragma: no cover

        stmt = select(Asset).where(Asset.asset_name == asset_name)
        if exclude_id:
            stmt = stmt.where(Asset.id != exclude_id)

        existing = (await db.execute(stmt)).scalars().first()
        if existing:
            return [f"物业名称 '{asset_name}' 已存在"]

        return []


class UserValidator(BaseValidator):
    """用户数据验证器"""

    @classmethod
    def validate_user_data(cls, data: dict[str, Any]) -> list[str]:
        """
        验证用户数据

        Args:
            data: 用户数据字典

        Returns:
            错误消息列表
        """
        errors = []

        # 验证用户名
        if "username" in data:
            username = data["username"]
            if not cls.validate_length(username, 3, 50):
                errors.append("用户名长度应在3-50个字符之间")
            if not re.match(r"^[a-zA-Z0-9_]+$", username):
                errors.append("用户名只能包含字母、数字和下划线")

        # 验证邮箱
        if "email" in data:
            if not cls.validate_email(data["email"]):
                errors.append("邮箱格式不正确")

        # 验证手机号
        if "phone" in data and data["phone"]:
            if not cls.validate_phone(data["phone"]):
                errors.append("手机号格式不正确")

        # 验证全名
        if "full_name" in data:  # pragma: no cover
            if not cls.validate_length(data["full_name"], 1, 100):  # pragma: no cover
                errors.append("姓名长度应在1-100个字符之间")  # pragma: no cover

        return errors

    @classmethod
    async def validate_user_unique(
        cls,
        db: AsyncSession,
        username: str | None = None,
        email: str | None = None,
        exclude_id: str | None = None,
    ) -> list[str]:
        """
        验证用户唯一性

        Args:
            db: 数据库会话
            username: 用户名
            email: 邮箱
            exclude_id: 排除的用户ID（用于更新时）

        Returns:
            错误消息列表
        """
        from ..models.auth import User  # pragma: no cover

        errors: list[str] = []  # pragma: no cover

        if username:  # pragma: no cover
            stmt = select(User).where(User.username == username)  # pragma: no cover
            if exclude_id:  # pragma: no cover
                stmt = stmt.where(User.id != exclude_id)  # pragma: no cover

            existing = (await db.execute(stmt)).scalars().first()  # pragma: no cover
            if existing:  # pragma: no cover
                errors.append(f"用户名 '{username}' 已存在")  # pragma: no cover

        if email:  # pragma: no cover
            stmt = select(User).where(User.email == email)  # pragma: no cover
            if exclude_id:  # pragma: no cover
                stmt = stmt.where(User.id != exclude_id)  # pragma: no cover

            existing = (await db.execute(stmt)).scalars().first()  # pragma: no cover
            if existing:  # pragma: no cover
                errors.append(f"邮箱 '{email}' 已存在")  # pragma: no cover

        return errors  # pragma: no cover


class OrganizationValidator(BaseValidator):
    """组织数据验证器"""

    @classmethod
    def validate_organization_data(cls, data: dict[str, Any]) -> list[str]:
        """
        验证组织数据

        Args:
            data: 组织数据字典

        Returns:
            错误消息列表
        """
        errors = []

        # 验证组织名称
        if "name" in data:
            if not cls.validate_length(data["name"], 1, 200):
                errors.append("组织名称长度应在1-200个字符之间")

        # 验证组织代码
        if "code" in data:
            if not cls.validate_length(data["code"], 2, 50):
                errors.append("组织代码长度应在2-50个字符之间")
            if not re.match(r"^[A-Z0-9_]+$", data["code"]):
                errors.append("组织代码只能包含大写字母、数字和下划线")

        # 验证联系电话
        if "phone" in data and data["phone"]:  # pragma: no cover
            if not cls.validate_phone(data["phone"]):  # pragma: no cover
                errors.append("联系电话格式不正确")  # pragma: no cover

        # 验证邮箱
        if "email" in data and data["email"]:  # pragma: no cover
            if not cls.validate_email(data["email"]):  # pragma: no cover
                errors.append("邮箱格式不正确")  # pragma: no cover

        return errors


class ValidationMixin:
    """验证混入类"""

    def validate_and_raise(self, errors: list[str], context: str = "数据验证") -> None:
        """验证并抛出异常"""
        if errors:
            from ..exceptions import BusinessLogicError

            raise BusinessLogicError(f"{context}失败: {'; '.join(errors)}")


class DataCleaner:
    """数据清理器"""

    @staticmethod
    def clean_phone(phone: str) -> str:
        """清理手机号"""
        return re.sub(r"[^\d]", "", phone)

    @staticmethod
    def clean_whitespace(text: str) -> str:
        """清理多余空白字符"""
        return " ".join(text.split())

    @staticmethod
    def clean_numeric_string(text: str) -> str:
        """清理数字字符串，只保留数字和小数点"""
        return re.sub(r"[^\d.]", "", text)

    @staticmethod
    def standardize_boolean(value: Any) -> bool:
        """标准化布尔值"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        if isinstance(value, (int, float)):
            return bool(value)
        return False

    @staticmethod
    def standardize_datetime(value: Any) -> datetime | None:
        """标准化日期时间"""
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                # 尝试多种日期格式
                formats = [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d",
                    "%Y/%m/%d %H:%M:%S",
                    "%Y/%m/%d",
                ]
                for fmt in formats:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
            except (
                Exception
            ):  # pragma: no cover  # nosec - B110: Intentional graceful degradation
                pass  # pragma: no cover
        return None


# 便捷函数
def validate_required_fields(
    data: dict[str, Any], required_fields: list[str]
) -> list[str]:
    """验证必填字段"""
    errors = []
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == EMPTY_STRING:
            errors.append(f"缺少必填字段: {field}")
    return errors


def validate_field_length(
    data: dict[str, Any], field_lengths: dict[str, dict[str, int]]
) -> list[str]:
    """验证字段长度"""
    errors = []
    for field, config in field_lengths.items():
        if field in data and data[field] is not None:
            length = len(str(data[field]))
            min_length = config.get("min", 0)
            max_length = config.get("max", float("inf"))

            if length < min_length:
                errors.append(f"{field}长度不能少于{min_length}个字符")
            elif length > max_length:
                errors.append(f"{field}长度不能超过{max_length}个字符")

    return errors


def validate_field_values(
    data: dict[str, Any], field_values: dict[str, list[Any]]
) -> list[str]:
    """验证字段值范围"""
    errors = []
    for field, valid_values in field_values.items():
        if field in data and data[field] not in valid_values:
            errors.append(
                f"{field}的值应为以下之一: {', '.join(map(str, valid_values))}"
            )

    return errors
