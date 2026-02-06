"""
Property Certificate Validator
产权证数据验证器
"""

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, NoReturn

from src.models.property_certificate import CertificateType

from ...core.exception_handler import BusinessValidationError


@dataclass
class ValidationResult:
    """验证结果"""

    errors: list[str]
    warnings: list[str]

    def is_valid(self) -> bool:
        return len(self.errors) == 0


class PropertyCertificateValidator:
    """产权证验证器"""

    # Required fields by certificate type
    REQUIRED_FIELDS = {
        CertificateType.REAL_ESTATE: ["certificate_number", "property_address"],
        CertificateType.HOUSE_OWNERSHIP: ["certificate_number", "property_address"],
        CertificateType.LAND_USE: ["certificate_number", "property_address"],
        CertificateType.OTHER: ["certificate_number"],
    }

    @classmethod
    def validate_extracted_fields(
        cls, data: dict[str, Any], cert_type: CertificateType
    ) -> ValidationResult:
        """验证提取的字段"""
        errors = []
        warnings = []

        # Check required fields
        required = cls.REQUIRED_FIELDS.get(cert_type, [])
        for field in required:
            if field not in data or not data[field]:
                errors.append(f"必填字段缺失: {field}")

        # Validate certificate number format
        if "certificate_number" in data:
            if not cls._validate_certificate_number(data["certificate_number"]):
                errors.append("证书编号格式不正确")

        # Validate dates
        if "registration_date" in data and data["registration_date"]:
            if not cls._validate_date(data["registration_date"]):
                errors.append("登记日期格式不正确")

        # Validate area fields
        for field in ["building_area", "land_area"]:
            if field in data and data[field]:
                if not cls._validate_area(data[field]):
                    warnings.append(f"{field} 格式可能不正确")

        # Validate date logic
        if "land_use_term_start" in data and "land_use_term_end" in data:
            if data["land_use_term_start"] and data["land_use_term_end"]:
                if data["land_use_term_start"] >= data["land_use_term_end"]:
                    errors.append("土地使用终止日期必须晚于起始日期")

        return ValidationResult(errors=errors, warnings=warnings)

    def validate_certificate_number(self, number: str | None) -> bool:
        if not number:
            self._raise_validation_error("证书编号不能为空", field="certificate_number")
        if len(number) != 18:
            self._raise_validation_error(
                "证书编号长度必须为 18 位", field="certificate_number"
            )
        return True

    def validate_area(self, area: float | int | str | None) -> bool:
        if area is None:
            self._raise_validation_error("面积不能为空", field="area")
        try:
            value = float(area)
        except (TypeError, ValueError):
            self._raise_validation_error("面积格式不正确", field="area")
        if value <= 0:
            self._raise_validation_error("面积必须为正数", field="area")
        if value > 100000000:
            self._raise_validation_error("面积过大", field="area")
        return True

    def validate_issue_date(self, issue_date: datetime | date | None) -> bool:
        if issue_date is None:
            self._raise_validation_error("发证日期不能为空", field="issue_date")
        if isinstance(issue_date, date) and not isinstance(issue_date, datetime):
            issue_date = datetime.combine(issue_date, datetime.min.time(), tzinfo=UTC)
        if isinstance(issue_date, datetime):
            if issue_date.tzinfo is None:
                issue_date = issue_date.replace(tzinfo=UTC)
            if issue_date > datetime.utcnow():
                self._raise_validation_error(
                    "发证日期不能晚于当前日期", field="issue_date"
                )
            return True
        self._raise_validation_error("发证日期格式不正确", field="issue_date")

    def validate_expiry_date(
        self, expiry_date: datetime | date | None, issue_date: datetime | date | None
    ) -> bool:
        if expiry_date is None:
            self._raise_validation_error("到期日期不能为空", field="expiry_date")
        if issue_date is None:
            self._raise_validation_error("发证日期不能为空", field="issue_date")
        if isinstance(expiry_date, date) and not isinstance(expiry_date, datetime):
            expiry_date = datetime.combine(expiry_date, datetime.min.time(), tzinfo=UTC)
        if isinstance(issue_date, date) and not isinstance(issue_date, datetime):
            issue_date = datetime.combine(issue_date, datetime.min.time(), tzinfo=UTC)
        if not isinstance(expiry_date, datetime):
            self._raise_validation_error("日期格式不正确", field="expiry_date")
        if not isinstance(issue_date, datetime):
            self._raise_validation_error("日期格式不正确", field="issue_date")
        if expiry_date.tzinfo is None:
            expiry_date = expiry_date.replace(tzinfo=UTC)
        if issue_date.tzinfo is None:
            issue_date = issue_date.replace(tzinfo=UTC)
        if expiry_date <= issue_date:
            self._raise_validation_error(
                "到期日期必须晚于发证日期", field="expiry_date"
            )
        return True

    def validate_property_name(self, name: str | None) -> bool:
        if not name:
            self._raise_validation_error("房产名称不能为空", field="property_name")
        if len(name.strip()) < 3:
            self._raise_validation_error("房产名称过短", field="property_name")
        return True

    def validate_address(self, address: str | None) -> bool:
        if not address or not address.strip():
            self._raise_validation_error("地址不能为空", field="address")
        return True

    def validate_certificate_data(self, data: dict[str, Any]) -> bool:
        required_fields = [
            "certificate_number",
            "property_name",
            "area",
            "issue_date",
            "expiry_date",
            "address",
        ]
        for field in required_fields:
            if field not in data:
                self._raise_validation_error(
                    "缺少必填字段", field=field, details={"missing_field": field}
                )
        self.validate_certificate_number(data.get("certificate_number"))
        self.validate_property_name(data.get("property_name"))
        self.validate_area(data.get("area"))
        self.validate_issue_date(data.get("issue_date"))
        self.validate_expiry_date(data.get("expiry_date"), data.get("issue_date"))
        self.validate_address(data.get("address"))
        return True

    def validate_registration_number(self, number: str | None) -> bool:
        if not number:
            self._raise_validation_error("注册号不能为空", field="registration_number")
        pattern = r"^REG-\d{4}-\d{6}$"
        if not re.match(pattern, number):
            self._raise_validation_error(
                "注册号格式不正确", field="registration_number"
            )
        return True

    def validate_owner_name(self, name: str | None) -> bool:
        if not name or not name.strip():
            self._raise_validation_error("业主姓名不能为空", field="owner_name")
        return True

    def validate_certificate_type(self, cert_type: str | None) -> bool:
        allowed = {"house", "land", "real_estate", "other"}
        if not cert_type or cert_type not in allowed:
            self._raise_validation_error("无效的产权证类型", field="certificate_type")
        return True

    def validate_land_use_right(self, right: str | None) -> bool:
        allowed = {"residential", "commercial", "industrial", "mixed", "other"}
        if not right or right not in allowed:
            self._raise_validation_error("无效的土地使用权", field="land_use_right")
        return True

    def validate_land_term(self, term: int | None) -> bool:
        if term is None:
            self._raise_validation_error("土地年限不能为空", field="land_term")
        if term <= 0:
            self._raise_validation_error("土地年限必须为正数", field="land_term")
        if term > 70:
            self._raise_validation_error("土地年限过长", field="land_term")
        return True

    def validate_certificate_copy_number(self, count: int | None) -> bool:
        if count is None:
            self._raise_validation_error(
                "份数不能为空", field="certificate_copy_number"
            )
        if count <= 0:
            self._raise_validation_error(
                "份数必须为正数", field="certificate_copy_number"
            )
        return True

    @staticmethod
    def _raise_validation_error(
        message: str,
        *,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> NoReturn:
        field_errors = {field: [message]} if field else None
        raise BusinessValidationError(
            message=message,
            field_errors=field_errors,
            details=details,
        )

    @staticmethod
    def _validate_certificate_number(number: str) -> bool:
        """验证证书编号格式"""
        if not number or len(number) < 5:
            return False
        return True

    @staticmethod
    def _validate_date(date_value: Any) -> bool:
        """验证日期格式"""
        if isinstance(date_value, date):
            return True
        if isinstance(date_value, str):
            try:
                date.fromisoformat(date_value)
                return True
            except ValueError:
                return False
        return False

    @staticmethod
    def _validate_area(area: Any) -> bool:
        """验证面积格式"""
        try:
            float(area)
            return True
        except (ValueError, TypeError):
            return False
