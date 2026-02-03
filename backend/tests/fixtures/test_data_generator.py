"""
测试数据生成器
使用 Faker 生成真实的测试数据
"""

import random
from datetime import date
from decimal import Decimal
from typing import Any

from faker import Faker

# 初始化 Faker（使用中文）
fake = Faker("zh_CN")


class TestDataGenerator:
    """测试数据生成器"""

    @staticmethod
    def generate_contract_data(**kwargs) -> dict[str, Any]:
        """
        生成合同数据

        Args:
            **kwargs: 自定义字段值

        Returns:
            合同数据字典
        """
        start_date = kwargs.get(
            "start_date", fake.date_between(start_date="-1y", end_date="today")
        )
        end_date = kwargs.get(
            "end_date", fake.date_between(start_date="today", end_date="+2y")
        )

        return {
            "contract_no": kwargs.get(
                "contract_no", f"HT-{fake.year()}-{fake.random_int(100, 999)}"
            ),
            "contract_name": kwargs.get("contract_name", fake.sentence(nb_words=5)),
            "contract_type": kwargs.get(
                "contract_type", random.choice(["lease", "service", "management"])
            ),
            "status": kwargs.get(
                "status", random.choice(["draft", "active", "expired", "terminated"])
            ),
            "start_date": start_date,
            "end_date": end_date,
            "total_rent": kwargs.get(
                "total_rent", Decimal(str(random.uniform(10000, 1000000)))
            ),
            "tenant_name": kwargs.get("tenant_name", fake.company()),
            "tenant_phone": kwargs.get("tenant_phone", fake.phone_number()),
            "tenant_contact": kwargs.get("tenant_contact", fake.name()),
            "payment_cycle": kwargs.get(
                "payment_cycle", random.choice(["monthly", "quarterly", "yearly"])
            ),
            "payment_method": kwargs.get(
                "payment_method", random.choice(["bank_transfer", "cash", "check"])
            ),
        }

    @staticmethod
    def generate_asset_data(**kwargs) -> dict[str, Any]:
        """
        生成资产数据

        Args:
            **kwargs: 自定义字段值

        Returns:
            资产数据字典
        """
        return {
            "name": kwargs.get("name", fake.sentence(nb_words=3)),
            "code": kwargs.get("code", f"ASSET-{fake.random_int(1000, 9999)}"),
            "area": kwargs.get("area", Decimal(str(random.uniform(100, 10000)))),
            "location": kwargs.get("location", fake.address()),
            "status": kwargs.get(
                "status", random.choice(["active", "inactive", "maintenance"])
            ),
            "asset_type": kwargs.get(
                "asset_type",
                random.choice(["building", "land", "facility", "equipment"]),
            ),
            "building_area": kwargs.get(
                "building_area", Decimal(str(random.uniform(50, 5000)))
            ),
            "floor_area": kwargs.get(
                "floor_area", Decimal(str(random.uniform(50, 5000)))
            ),
            "description": kwargs.get("description", fake.text(max_nb_chars=200)),
        }

    @staticmethod
    def generate_user_data(**kwargs) -> dict[str, Any]:
        """
        生成用户数据

        Args:
            **kwargs: 自定义字段值

        Returns:
            用户数据字典
        """
        return {
            "username": kwargs.get("username", fake.user_name()),
            "email": kwargs.get("email", fake.email()),
            "full_name": kwargs.get("full_name", fake.name()),
            "phone": kwargs.get("phone", fake.phone_number()),
            "role": kwargs.get("role", random.choice(["admin", "user", "manager"])),
            "department": kwargs.get("department", fake.company_suffix()),
            "is_active": kwargs.get("is_active", True),
        }

    @staticmethod
    def generate_organization_data(**kwargs) -> dict[str, Any]:
        """
        生成组织机构数据

        Args:
            **kwargs: 自定义字段值

        Returns:
            组织机构数据字典
        """
        return {
            "name": kwargs.get("name", fake.company()),
            "code": kwargs.get("code", f"ORG-{fake.random_int(1000, 9999)}"),
            "type": kwargs.get(
                "type", random.choice(["company", "government", "institution", "other"])
            ),
            "unified_social_credit_code": kwargs.get(
                "unified_social_credit_code", fake.credit_card_number()
            ),
            "legal_representative": kwargs.get("legal_representative", fake.name()),
            "contact_person": kwargs.get("contact_person", fake.name()),
            "contact_phone": kwargs.get("contact_phone", fake.phone_number()),
            "address": kwargs.get("address", fake.address()),
            "is_active": kwargs.get("is_active", True),
        }

    @staticmethod
    def generate_ownership_data(**kwargs) -> dict[str, Any]:
        """
        生成权属数据

        Args:
            **kwargs: 自定义字段值

        Returns:
            权属数据字典
        """
        start_date = kwargs.get(
            "start_date", fake.date_between(start_date="-5y", end_date="today")
        )

        return {
            "asset_id": kwargs.get("asset_id", fake.random_int(1, 1000)),
            "organization_id": kwargs.get("organization_id", fake.random_int(1, 100)),
            "ownership_ratio": kwargs.get(
                "ownership_ratio", Decimal(str(random.uniform(10, 100)))
            ),
            "start_date": start_date,
            "end_date": kwargs.get("end_date", None),
            "ownership_type": kwargs.get(
                "ownership_type", random.choice(["full", "partial", "shared"])
            ),
            "is_active": kwargs.get("is_active", True),
            "certificate_no": kwargs.get(
                "certificate_no", f"CERT-{fake.random_int(100000, 999999)}"
            ),
        }

    @staticmethod
    def generate_property_certificate_data(**kwargs) -> dict[str, Any]:
        """
        生成产权证数据

        Args:
            **kwargs: 自定义字段值

        Returns:
            产权证数据字典
        """
        issue_date = kwargs.get(
            "issue_date", fake.date_between(start_date="-10y", end_date="today")
        )

        return {
            "certificate_no": kwargs.get(
                "certificate_no", f"PROP-{fake.random_int(100000, 999999)}"
            ),
            "asset_id": kwargs.get("asset_id", fake.random_int(1, 1000)),
            "ownership_type": kwargs.get(
                "ownership_type",
                random.choice(["state", "collective", "private", "mixed"]),
            ),
            "land_use_type": kwargs.get(
                "land_use_type",
                random.choice(["commercial", "residential", "industrial", "mixed"]),
            ),
            "land_area": kwargs.get(
                "land_area", Decimal(str(random.uniform(100, 10000)))
            ),
            "building_area": kwargs.get(
                "building_area", Decimal(str(random.uniform(50, 5000)))
            ),
            "issue_date": issue_date,
            "issue_authority": kwargs.get(
                "issue_authority", fake.company_suffix() + "自然资源局"
            ),
            "register_date": kwargs.get(
                "register_date",
                fake.date_between(start_date=issue_date, end_date="today"),
            ),
            "status": kwargs.get(
                "status", random.choice(["valid", "expired", "revoked", "transferred"])
            ),
        }

    @staticmethod
    def generate_rent_term_data(**kwargs) -> dict[str, Any]:
        """
        生成租金条款数据

        Args:
            **kwargs: 自定义字段值

        Returns:
            租金条款数据字典
        """
        due_date = kwargs.get(
            "due_date", fake.date_between(start_date="today", end_date="+1y")
        )

        return {
            "contract_id": kwargs.get("contract_id", fake.random_int(1, 500)),
            "term_order": kwargs.get("term_order", fake.random_int(1, 12)),
            "due_date": due_date,
            "rent_amount": kwargs.get(
                "rent_amount", Decimal(str(random.uniform(5000, 50000)))
            ),
            "payment_status": kwargs.get(
                "payment_status",
                random.choice(["unpaid", "partial", "paid", "overdue"]),
            ),
            "paid_amount": kwargs.get("paid_amount", Decimal("0")),
            "payment_date": kwargs.get("payment_date", None),
            "notes": kwargs.get(
                "notes", fake.text(max_nb_chars=100) if random.random() > 0.5 else None
            ),
        }

    @staticmethod
    def generate_contracts(count: int = 10, **kwargs) -> list[dict[str, Any]]:
        """
        批量生成合同数据

        Args:
            count: 生成数量
            **kwargs: 自定义字段值

        Returns:
            合同数据列表
        """
        return [
            TestDataGenerator.generate_contract_data(**kwargs) for _ in range(count)
        ]

    @staticmethod
    def generate_assets(count: int = 10, **kwargs) -> list[dict[str, Any]]:
        """
        批量生成资产数据

        Args:
            count: 生成数量
            **kwargs: 自定义字段值

        Returns:
            资产数据列表
        """
        return [TestDataGenerator.generate_asset_data(**kwargs) for _ in range(count)]

    @staticmethod
    def generate_ownerships(count: int = 10, **kwargs) -> list[dict[str, Any]]:
        """
        批量生成权属数据

        Args:
            count: 生成数量
            **kwargs: 自定义字段值

        Returns:
            权属数据列表
        """
        return [
            TestDataGenerator.generate_ownership_data(**kwargs) for _ in range(count)
        ]

    @staticmethod
    def generate_date_range(
        start_date: date | None = None,
        end_date: date | None = None,
        months: int = 12,
    ) -> list[date]:
        """
        生成日期范围（按月）

        Args:
            start_date: 开始日期
            end_date: 结束日期
            months: 月数

        Returns:
            日期列表
        """
        if start_date is None:
            start_date = date.today().replace(day=1)

        dates = []
        current_date = start_date

        for _ in range(months):
            dates.append(current_date)
            # 计算下个月的第一天
            year = current_date.year + (current_date.month // 12)
            month = (current_date.month % 12) + 1
            current_date = date(year, month, 1)

            if end_date and current_date > end_date:
                break

        return dates

    @staticmethod
    def random_phone() -> str:
        """生成随机手机号"""
        return fake.phone_number()

    @staticmethod
    def random_id_card() -> str:
        """生成随机身份证号"""
        return fake.ssn()

    @staticmethod
    def random_address() -> str:
        """生成随机地址"""
        return fake.address()

    @staticmethod
    def random_company_name() -> str:
        """生成随机公司名称"""
        return fake.company()
