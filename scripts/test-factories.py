#!/usr/bin/env python3
"""
测试数据工厂
用于生成各种类型的测试数据
支持多种策略和边界条件
"""

import random
import string
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional

from faker import Faker

# 导入项目模型
from src.models.asset import Asset
from src.models.rent_contract import RentContract
from src.models.rbac import User, Role, Permission, Organization
from src.models.ownership import Ownership


class BaseFactory:
    """基础工厂类"""

    def __init__(self, locale: str = 'zh_CN'):
        self.fake = Faker(locale)
        self.random = random.Random()

    def random_string(self, length: int = 10) -> str:
        """生成随机字符串"""
        return ''.join(self.random.choices(string.ascii_letters + string.digits, k=length))

    def random_email(self) -> str:
        """生成随机邮箱"""
        return self.fake.email()

    def random_phone(self) -> str:
        """生成随机电话"""
        return self.fake.phone_number()

    def random_decimal(self, min_val: float = 0.0, max_val: float = 999999.99) -> Decimal:
        """生成随机小数"""
        return Decimal(str(self.random.uniform(min_val, max_val)))

    def random_choice(self, choices: List[Any]) -> Any:
        """从列表中随机选择"""
        return self.random.choice(choices)

    def random_choices(self, choices: List[Any], count: int) -> List[Any]:
        """从列表中随机选择多个"""
        return self.random.choices(choices, k=count)

    def random_boolean(self) -> bool:
        """生成随机布尔值"""
        return self.random.choice([True, False])

    def random_date(self, start_date: datetime = None, end_date: datetime = None) -> datetime:
        """生成随机日期"""
        if start_date and end_date:
            delta = end_date - start_date
            random_days = self.random.randint(0, delta.days)
            return start_date + timedelta(days=random_days)
        elif start_date:
            delta = timedelta(days=self.random.randint(0, 365))
            return start_date + delta
        elif end_date:
            delta = timedelta(days=self.random.randint(-365, 0))
            return end_date + delta
        else:
            days_ago = self.random.randint(0, 365)
            return datetime.now() - timedelta(days=days_ago)


class AssetFactory(BaseFactory):
    """资产数据工厂"""

    def create_asset(self, **overrides) -> Dict[str, Any]:
        """创建资产数据"""
        data = {
            # 基本信息
            "id": str(uuid.uuid4()),
            "ownership_entity": overrides.get("ownership_entity", self.fake.company()),
            "ownership_category": self.random_choice(["国有", "集体", "私有"]),
            "project_name": overrides.get("project_name", f"{self.fake.company()}{self.random.randint(1, 10)}号项目"),
            "property_name": overrides.get("property_name", f"{self.fake.company()}物业{self.random.randint(1, 100)}号"),
            "address": overrides.get("address", f"{self.fake.province()}{self.fake.city()}{self.fake.street_address()}"),
            "ownership_status": self.random_choice(["已确权", "待确权", "确权中"]),
            "property_nature": self.random_choice(["商业", "住宅", "工业", "综合"]),
            "usage_status": self.random_choice(["运营中", "已出租", "闲置", "装修中"]),

            # 面积字段
            "land_area": overrides.get("land_area", float(self.random_decimal(100, 10000))),
            "actual_property_area": overrides.get("actual_property_area", float(self.random_decimal(50, 5000))),
            "rentable_area": overrides.get("rentable_area", float(self.random_decimal(80, 4000))),
            "rented_area": overrides.get("rented_area", float(self.random_decimal(20, 3000))),
            "unrented_area": overrides.get("unrented_area", float(self.random_decimal(5, 1000))),
            "non_commercial_area": overrides.get("non_commercial_area", float(self.random_decimal(10, 500))),
            "occupancy_rate": overrides.get("occupancy_rate", float(self.random_decimal(0, 100))),
            "include_in_occupancy_rate": self.random_boolean(),

            # 财务字段
            "annual_income": overrides.get("annual_income", float(self.random_decimal(10000, 500000))),
            "annual_expense": overrides.get("annual_expense", float(self.random_decimal(2000, 100000))),
            "net_income": overrides.get("net_income", float(self.random_decimal(10000, 200000))),

            # 合同字段
            "lease_contract_number": overrides.get("lease_contract_number", f"HT{datetime.now().year}{self.random.randint(1000, 9999)}"),
            "contract_start_date": overrides.get("contract_start_date", self.random_date()),
            "contract_end_date": overrides.get("contract_end_date", self.random_date(
                start_date=overrides.get("contract_start_date", self.random_date()) if overrides.get("contract_start_date") else None
            )),
            "contract_term": overrides.get("contract_term", self.random.randint(1, 60)),  # 月
            "rent_payment_method": self.random_choice(["月付", "季付", "年付"]),
            "deposit_amount": overrides.get("deposit_amount", float(self.random_decimal(1000, 10000))),
            "tenant_name": overrides.get("tenant_name", self.fake.company()),
            "tenant_type": self.random_choice(["企业", "个人", "个体户"]),

            # 状态字段
            "is_litigated": overrides.get("is_litigated", self.random_boolean()),
            "business_model": overrides.get("business_model", self.random_choice(["自营", "委托管理", "合作经营"]),

            # 系统字段
            "created_at": overrides.get("created_at", datetime.now().isoformat()),
            "updated_at": overrides.get("updated_at", datetime.now().isoformat()),
            "created_by": overrides.get("created_by", "admin_user"),
            "updated_by": overrides.get("updated_by", "admin_user")
        }

        return data

    def create_asset_list(self, count: int, **common_overrides) -> List[Dict[str, Any]]:
        """创建资产列表"""
        return [self.create_asset(**{**common_overrides,
                                      f"ownership_entity_{i}": f"测试权属方{i}"})
                for i in range(count)]

    def create_high_value_asset(self) -> Dict[str, Any]:
        """创建高价值资产"""
        return self.create_asset(
            ownership_entity="大型地产投资集团",
            actual_property_area=float(self.random_decimal(5000, 20000)),
            annual_income=float(self.random_decimal(500000, 2000000)),
            rentable_area=float(self.random_decimal(4000, 15000))
        )

    def create_low_occupancy_asset(self) -> Dict[str, Any]:
        """创建低出租率资产"""
        return self.create_asset(
            rentable_area=float(self.random_decimal(1000, 5000)),
            rented_area=float(self.random_decimal(50, 200))
        )

    def create_boundary_test_assets(self) -> Dict[str, Any]:
        """创建边界测试资产"""
        return [
            self.create_asset(annual_income=0),  # 零收入
            self.create_asset(actual_property_area=0),  # 零面积
            self.create_asset(rentable_area=0),  # 零可租面积
            self.create_asset(occupancy_rate=0),  # 零出租率
            self.create_asset(occupancy_rate=100),  # 100%出租率
            self.create_asset(occupancy_rate=120),  # 异常高出租率
        ]

    def create_financial_calculation_assets(self) -> List[Dict[str, Any]]:
        """创建财务计算测试资产"""
        assets = []

        # 测试净收入计算
        assets.append(self.create_asset(
            annual_income=100000,
            annual_expense=30000
        ))

        # 测试出租率计算
        assets.append(self.create_asset(
            rentable_area=1000,
            rented_area=750
        ))

        return assets


class UserFactory(BaseFactory):
    """用户数据工厂"""

    def create_user(self, **overrides) -> Dict[str, Any]:
        """创建用户数据"""
        data = {
            "id": str(uuid.uuid4()),
            "username": overrides.get("username", self.fake.user_name()),
            "email": overrides.get("email", self.random_email()),
            "full_name": overrides.get("full_name", self.fake.name()),
            "phone": overrides.get("phone", self.random_phone()),
            "avatar_url": overrides.get("avatar_url", f"https://avatar.example.com/{self.random_string(10)}.jpg"),
            "organization_id": overrides.get("organization_id", str(uuid.uuid4())),
            "is_active": overrides.get("is_active", True),
            "is_superuser": overrides.get("is_superuser", False),
            "last_login_at": overrides.get("last_login_at", self.random_date()),
            "login_count": overrides.get("login_count", self.random.randint(0, 1000)),
            "created_at": overrides.get("created_at", datetime.now().isoformat()),
            "updated_at": overrides.get("updated_at", datetime.now().isoformat())
        }

        return data

    def create_admin_user(self) -> Dict[str, Any]:
        """创建管理员用户"""
        return self.create_user(
            username="admin",
            is_superuser=True,
            permissions=["all"]
        )

    def create_inactive_user(self) -> Dict[str, Any]:
        """创建非活跃用户"""
        return self.create_user(is_active=False)


class PermissionFactory(BaseFactory):
    """权限数据工厂"""

    def create_permission(self, **overrides) -> Dict[str, Any]:
        """创建权限数据"""
        data = {
            "id": str(uuid.uuid4()),
            "permission_name": overrides.get("permission_name", self.random.choice(["查看资产", "创建资产", "编辑资产", "删除资产"])),
            "permission_code": overrides.get("permission_code", f"{'PERMISSION_'.upper()}"),
            "resource": overrides.get("resource", self.random.choice(["ASSET", "CONTRACT", "USER", "ROLE", "SYSTEM"])),
            "action": overrides.get("action", self.random_choice(["VIEW", "CREATE", "EDIT", "DELETE", "MANAGE"])),
            "description": overrides.get("description", f"{data['permission_name']}权限"),
            "parent_permission_id": overrides.get("parent_permission_id"),
            "permission_level": overrides.get("permission_level", 1),
            "is_system_permission": overrides.get("is_system_permission", False),
            "permission_status": overrides.get("permission_status", "ACTIVE")
        }

        return data

    def create_permission_hierarchy(self) -> List[Dict[str, Any]]:
        """创建权限层级"""
        permissions = []

        # 创建根权限
        root_permissions = [
            self.create_permission(resource="SYSTEM", action="MANAGE", permission_level=1),
            self.create_permission(resource="ASSET", action="VIEW", permission_level=2),
            self.create_permission(resource="CONTRACT", action="VIEW", permission_level=2)
        ]
        permissions.extend(root_permissions)

        # 创建子权限
        asset_permissions = [
            self.create_permission(resource="ASSET", action="EDIT", permission_level=3, parent_id=root_permissions[1]["id"]),
            self.create_permission(resource="ASSET", action="DELETE", permission_level=3, parent_id=root_permissions[0]["id"]),
            self.create_permission(resource="ASSET", action="CREATE", permission_level=3, parent_id=root_permissions[0]["id"])
        ]
        permissions.extend(asset_permissions)

        return permissions


class OrganizationFactory(BaseFactory):
    """组织架构数据工厂"""

    def create_organization(self, **overrides) -> Dict[str, Any]:
        """创建组织数据"""
        data = {
            "id": str(uuid.uuid4()),
            "org_name": overrides.get("org_name", self.fake.company()),
            "org_code": overrides.get("org_code", f"ORG_{self.random_string(6).upper()}"),
            "parent_org_id": overrides.get("parent_org_id"),
            "org_level": overrides.get("org_level", 1),
            "org_type": overrides.get("org_type", self.random_choice(["公司", "部门", "项目部"])),
            "manager_id": overrides.get("manager_id", str(uuid.uuid4())),
            "contact_phone": overrides.get("contact_phone", self.random_phone()),
            "contact_email": overrides.get("contact_email", self.fake.company_email()),
            "address": overrides.get("address", self.fake.address()),
            "org_status": overrides.get("org_status", "ACTIVE")
        }

        return data

    def create_organization_hierarchy(self, levels: int = 3) -> List[Dict[str, Any]]:
        """创建组织层级"""
        organizations = []
        parent_id = None

        for level in range(1, levels + 1):
            org = self.create_organization(
                org_level=level,
                parent_org_id=parent_id
            )
            organizations.append(org)
            parent_id = org["id"]

        return organizations


class RentContractFactory(BaseFactory):
    """租赁合同数据工厂"""

    def create_contract(self, **overrides) -> Dict[str, Any]:
        """创建合同数据"""
        data = {
            "id": str(uuid.uuid4()),
            "contract_number": overrides.get("contract_number", f"RC{datetime.now().year}{self.random.randint(10000, 99999)}"),
            "asset_id": overrides.get("asset_id", str(uuid.uuid4())),
            "tenant_name": overrides.get("tenant_name", self.fake.company()),
            "tenant_type": overrides.get("tenant_type", self.random_choice(["企业", "个人", "个体户"])),
            "start_date": overrides.get("start_date", self.random_date()),
            "end_date": overrides.get("end_date", self.random_date(
                start_date=overrides.get("start_date", self.random_date())
            )),
            "monthly_rent": overrides.get("monthly_rent", float(self.random_decimal(1000, 50000))),
            "deposit_amount": overrides.get("deposit_amount", float(self.random_decimal(1000, 50000))),
            "payment_method": overrides.get("payment_method", self.random_choice(["月付", "季付", "年付"])),
            "contract_status": overrides.get("contract_status", "ACTIVE"),
            "contract_file": overrides.get("contract_file", f"contracts/{overrides.get('contract_number', '')}.pdf")
        }

        return data

    def create_expired_contract(self) -> Dict[str, Any]:
        """创建过期合同"""
        return self.create_contract(
            end_date=datetime.now() - timedelta(days=30),
            contract_status="EXPIRED"
        )

    def create_contract_with_multiple_tenants(self) -> Dict[str, Any]:
        """创建多个租户的合同"""
        return self.create_contract(
            tenant_name=f"{self.fake.company()} & {self.fake.company()}"
        )


# 边界测试数据
class BoundaryTestData:
    """边界测试数据集合"""

    @staticmethod
    def get_extreme_values():
        """获取极端值用于边界测试"""
        return {
            "max_area": float(999999.99),
            "min_area": 0.01,
            "max_income": float(999999999.99),
            "min_income": 0.0,
            "max_rent": float(10000.0),
            "min_rent": 100.0,
            "long_term": 120,  # 月
            "short_term": 1,   # 月
            "high_occupancy": 100.0,
            "zero_occupancy": 0.0
        }

    @staticmethod
    def get_invalid_data():
        """获取无效数据"""
        return {
            "negative_area": -100.0,
            "invalid_email": "invalid-email",
            "invalid_date": "invalid-date",
            "empty_string": "",
            "null_value": None
        }


class TestDataManager:
    """测试数据管理器"""

    def __init__(self):
        self.assets = []
        self.users = []
        self.contracts = []
        self.organizations = []
        self.permissions = []

    def create_test_dataset(self,
                       assets_count: int = 10,
                       users_count: int = 5,
                       contracts_count: int = 5,
                       organizations_count: int = 3) -> Dict[str, Any]:
        """创建完整测试数据集"""
        print(f"🔄 创建测试数据集: {assets_count}资产, {users_count}用户, {contracts_count}合同, {organizations_count}组织")

        # 创建组织
        for i in range(organizations_count):
            org = OrganizationFactory().create_organization()
            self.organizations.append(org)

        # 创建权限
        self.permissions = PermissionFactory().create_permission_hierarchy()

        # 创建用户
        for i in range(users_count):
            user = UserFactory().create_user(
                organization_id=self.organizations[0]["id"]
            )
            self.users.append(user)

        # 创建合同
        for i in range(contracts_count):
            contract = RentContractFactory().create_contract()
            self.contracts.append(contract)

        # 创建资产
        for i in range(assets_count):
            asset = AssetFactory().create_asset()
            self.assets.append(asset)

        dataset = {
            "created_at": datetime.now().isoformat(),
            "description": f"标准测试数据集 - {len(self.assets)}资产, {len(self.contracts)}合同, {len(self.users)}用户",
            "assets": self.assets,
            "users": self.users,
            "contracts": self.contracts,
            "organizations": self.organizations,
            "permissions": self.permissions
        }

        print(f"✅ 测试数据集创建完成")
        return dataset

    def clear_data(self):
        """清空测试数据"""
        self.assets.clear()
        self.users.clear()
        self.contracts.clear()
        self.organizations.clear()
        self.permissions.clear()
        print("🧹 测试数据已清空")

    def get_asset_by_id(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取资产"""
        for asset in self.assets:
            if asset["id"] == asset_id:
                return asset
        return None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户"""
        for user in self.users:
            if user["username"] == username:
                return user
        return None