"""
Property Certificate Validator
产权证数据验证器
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

from src.models.property_certificate import CertificateType


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
