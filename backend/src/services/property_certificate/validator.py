"""Property certificate extraction-field validator."""

from dataclasses import dataclass
from datetime import date
from typing import Any

from src.models.property_certificate import CertificateType


@dataclass
class ValidationResult:
    """Validation result used by extraction preview pages."""

    errors: list[str]
    warnings: list[str]

    def is_valid(self) -> bool:
        return len(self.errors) == 0


class PropertyCertificateValidator:
    """Validator for extraction preview hints only."""

    REQUIRED_FIELDS = {
        CertificateType.REAL_ESTATE: ["certificate_number", "property_address"],
        CertificateType.HOUSE_OWNERSHIP: ["certificate_number", "property_address"],
        CertificateType.LAND_USE: ["certificate_number", "property_address"],
        CertificateType.OTHER: ["certificate_number"],
    }

    @classmethod
    def validate_extracted_fields(
        cls,
        data: dict[str, Any],
        cert_type: CertificateType,
    ) -> ValidationResult:
        """Validate extracted fields for preview hints, not persistence gates."""
        errors: list[str] = []
        warnings: list[str] = []

        required = cls.REQUIRED_FIELDS.get(cert_type, [])
        for field in required:
            if field not in data or not data[field]:
                errors.append(f"必填字段缺失: {field}")

        if "certificate_number" in data:
            if not cls._validate_certificate_number(data["certificate_number"]):
                errors.append("证书编号格式不正确")

        if "registration_date" in data and data["registration_date"]:
            if not cls._validate_date(data["registration_date"]):
                errors.append("登记日期格式不正确")

        for field in ["building_area", "land_area"]:
            if field in data and data[field]:
                if not cls._validate_area(data[field]):
                    warnings.append(f"{field} 格式可能不正确")

        if "land_use_term_start" in data and "land_use_term_end" in data:
            if data["land_use_term_start"] and data["land_use_term_end"]:
                if data["land_use_term_start"] >= data["land_use_term_end"]:
                    errors.append("土地使用终止日期必须晚于起始日期")

        return ValidationResult(errors=errors, warnings=warnings)

    @staticmethod
    def _validate_certificate_number(number: str) -> bool:
        if not number or len(number) < 5:
            return False
        return True

    @staticmethod
    def _validate_date(date_value: Any) -> bool:
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
        try:
            float(area)
            return True
        except (ValueError, TypeError):
            return False
