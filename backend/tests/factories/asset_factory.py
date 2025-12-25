"""
资产测试数据工厂
使用factory模式生成高质量的测试数据
支持各种测试场景的数据需求
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import factory

from src.models.asset import Asset
from src.models.auth import User
from src.models.rbac import Permission, Role


class AssetFactory(factory.Factory):
    """资产数据工厂"""

    class Meta:
        model = Asset
        sqlalchemy_session = None  # 将在测试中设置

    # 基本信息 (8字段)
    ownership_entity = factory.Faker('company')
    ownership_category = factory.Faker('random_element', elements=['国有企业', '民营企业', '外资企业', '合资企业'])
    project_name = factory.Faker('sentence', nb_words=3)
    property_name = factory.Faker('sentence', nb_words=2)
    address = factory.Faker('address')
    ownership_status = factory.Faker('random_element', elements=['已确权', '待确权', '确权中'])
    property_nature = factory.Faker('random_element', elements=['商业用途', '办公用途', '工业用途', '住宅用途'])
    usage_status = factory.Faker('random_element', elements=['使用中', '空置', '装修中', '待租'])
    business_category = factory.Faker('random_element', elements=['零售商业', '办公服务', '餐饮服务', '教育培训'])
    is_litigated = factory.Faker('boolean')
    notes = factory.Faker('paragraph', nb_sentences=2)

    # 面积相关字段 (6字段)
    land_area = factory.Faker('random_int', min=1000, max=50000)
    actual_property_area = factory.Faker('random_int', min=500, max=20000)
    rentable_area = factory.Faker('random_int', min=300, max=15000)
    rented_area = factory.Faker('random_int', min=0, max=12000)
    non_commercial_area = factory.Faker('random_int', min=0, max=5000)
    include_in_occupancy_rate = True

    # 用途相关字段 (2字段)
    certificated_usage = factory.Faker('random_element', elements=['商业用地', '办公用地', '工业用地', '住宅用地'])
    actual_usage = factory.Faker('random_element', elements=['零售商场', '办公楼', '工厂', '住宅'])

    # 租户相关字段 (2字段)
    tenant_name = factory.Faker('company')
    tenant_type = factory.Faker('random_element', elements=['企业', '个人', '事业单位', '社会组织'])

    # 合同相关字段 (8字段)
    lease_contract_number = factory.Sequence(lambda n: f"LC{datetime.now().year}{n:04d}")
    contract_start_date = factory.LazyAttribute(lambda obj: date.today() - timedelta(days=factory.random_random.Random().randint(30, 365)))
    contract_end_date = factory.LazyAttribute(lambda obj: obj.contract_start_date + timedelta(days=factory.random_random.Random().randint(180, 1095)))
    monthly_rent = factory.Faker('random_int', min=10000, max=1000000)
    deposit = factory.LazyAttribute(lambda obj: obj.monthly_rent * 3)
    is_sublease = factory.Faker('boolean')
    sublease_notes = factory.Faker('sentence', nb_sentences=1)

    # 管理相关字段 (3字段)
    business_model = factory.Faker('random_element', elements=['自营', '委托经营', '租赁经营', '合作经营'])
    operation_status = factory.Faker('random_element', elements=['正常营业', '装修中', '暂停营业', '已关闭'])
    manager_name = factory.Faker('name')

    # 接收相关字段 (3字段)
    operation_agreement_start_date = factory.LazyAttribute(lambda obj: obj.contract_start_date - timedelta(days=30))
    operation_agreement_end_date = factory.LazyAttribute(lambda obj: obj.contract_end_date + timedelta(days=365))
    operation_agreement_attachments = factory.Faker('file_name', extension='pdf')

    # 终端合同字段 (1字段)
    terminal_contract_files = factory.Faker('file_name', extension='pdf')

    # 项目相关字段
    project_phase = factory.Faker('random_element', elements=['一期', '二期', '三期', '整体'])

    # 系统字段 (6字段)
    data_status = '正常'
    version = 1
    tags = factory.Faker('words', nb=3)
    created_by = 'test_user'
    updated_by = 'test_user'
    audit_notes = factory.Faker('sentence', nb_sentences=1)

    # 多租户支持
    tenant_id = 'test_tenant_001'

    # 确保计算字段的正确性
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """创建前调整数据确保计算字段正确"""
        # 确保已出租面积不大于可出租面积
        if 'rented_area' in kwargs and 'rentable_area' in kwargs:
            if kwargs['rented_area'] > kwargs['rentable_area']:
                kwargs['rented_area'] = kwargs['rentable_area']

        # 确保合同日期正确
        if 'contract_start_date' in kwargs and 'contract_end_date' in kwargs:
            if kwargs['contract_end_date'] <= kwargs['contract_start_date']:
                kwargs['contract_end_date'] = kwargs['contract_start_date'] + timedelta(days=365)

        return super()._create(model_class, *args, **kwargs)


class AssetWithCompleteDataFactory(AssetFactory):
    """包含完整数据的资产工厂"""

    land_area = 5000
    actual_property_area = 4000
    rentable_area = 3500
    rented_area = 2800
    non_commercial_area = 500
    monthly_rent = 500000
    project_name = '城市商业综合体'
    property_name = '中心商业大厦'
    business_category = '零售商业'
    certificated_usage = '商业用地'
    actual_usage = '零售商场'


class AssetWithHighOccupancyFactory(AssetFactory):
    """高出租率资产工厂"""

    rentable_area = 2000
    rented_area = 1900  # 95%出租率
    monthly_rent = 300000
    usage_status = '使用中'
    tenant_name = '知名品牌连锁店'


class AssetWithLowOccupancyFactory(AssetFactory):
    """低出租率资产工厂"""

    rentable_area = 5000
    rented_area = 500  # 10%出租率
    monthly_rent = 200000
    usage_status = '空置'
    tenant_name = ''


class AssetUnderMaintenanceFactory(AssetFactory):
    """维护中资产工厂"""

    usage_status = '装修中'
    tenant_name = ''
    rented_area = 0
    monthly_rent = 0


# 用户和权限工厂
class UserFactory(factory.Factory):
    """用户数据工厂"""

    class Meta:
        model = User
        sqlalchemy_session_persistence = True

    username = factory.Faker('user_name')
    email = factory.Faker('email')
    full_name = factory.Faker('name')
    is_active = True
    is_superuser = False
    organization_id = 'test_org_001'


class AdminUserFactory(UserFactory):
    """管理员用户工厂"""

    username = 'admin'
    email = 'admin@example.com'
    full_name = '系统管理员'
    is_active = True
    is_superuser = True


class InactiveUserFactory(UserFactory):
    """非活跃用户工厂"""

    is_active = False


class RoleFactory(factory.Factory):
    """角色数据工厂"""

    class Meta:
        model = Role
        sqlalchemy_session_persistence = True

    name = factory.Sequence(lambda n: f"role_{n}")
    display_name = factory.Faker('job')
    description = factory.Faker('sentence', nb_sentences=2)
    level = factory.Faker('random_int', min=1, max=10)
    category = factory.Faker('random_element', elements=['业务', '管理', '系统'])
    is_system_role = False
    organization_id = 'test_org_001'
    scope = factory.Faker('random_element', elements=['organization', 'department', 'team'])
    scope_id = 'test_scope_001'


class PermissionFactory(factory.Factory):
    """权限数据工厂"""

    class Meta:
        model = Permission
        sqlalchemy_session_persistence = True

    name = factory.Sequence(lambda n: f"permission_{n}")
    display_name = factory.Faker('catch_phrase')
    description = factory.Faker('sentence', nb_sentences=1)
    resource = factory.Faker('random_element', elements=['assets', 'users', 'roles', 'reports'])
    action = factory.Faker('random_element', elements=['create', 'read', 'update', 'delete', 'admin'])
    max_level = factory.Faker('random_int', min=1, max=10)
    is_system_permission = False
    requires_approval = False


# 工厂函数
def create_asset_with_contract(contract_length_months: int = 12, **kwargs) -> Asset:
    """创建带指定合同长度的资产"""
    start_date = kwargs.get('contract_start_date', date.today())
    end_date = start_date + timedelta(days=contract_length_months * 30)

    return AssetFactory.create(
        contract_start_date=start_date,
        contract_end_date=end_date,
        **kwargs
    )


def create_asset_with_financial_data(
    annual_income: Decimal | None = None,
    annual_expense: Decimal | None = None,
    **kwargs
) -> Asset:
    """创建带财务数据的资产"""
    if annual_income is None:
        monthly_rent = kwargs.get('monthly_rent', Decimal('100000'))
        annual_income = monthly_rent * 12

    return AssetFactory.create(
        annual_income=annual_income,
        annual_expense=annual_expense or Decimal(annual_income * 0.2),
        **kwargs
    )


def create_asset_portfolio(total_assets: int, **common_kwargs) -> list[Asset]:
    """创建资产组合"""
    assets = []

    for i in range(total_assets):
        # 为每个资产添加一些变化
        kwargs = common_kwargs.copy()
        kwargs.update({
            'ownership_entity': f"公司_{i}",
            'property_name': f"物业_{i}",
            'rentable_area': 1000 + (i * 500),
            'rented_area': int((1000 + (i * 500)) * 0.8),
        })

        assets.append(AssetFactory.create(**kwargs))

    return assets


def create_test_scenarios() -> dict[str, list[Asset]]:
    """创建标准测试场景数据"""
    return {
        'high_occupancy': AssetWithHighOccupancyFactory.create_batch(5),
        'low_occupancy': AssetWithLowOccupancyFactory.create_batch(5),
        'under_maintenance': AssetUnderMaintenanceFactory.create_batch(3),
        'complete_data': AssetWithCompleteDataFactory.create_batch(10),
        'normal_assets': AssetFactory.create_batch(20),
    }


def create_permission_hierarchy() -> tuple[list[Permission], list[Role]]:
    """创建权限层级"""
    # 创建基础权限
    permissions = [
        PermissionFactory.create(resource='assets', action='read'),
        PermissionFactory.create(resource='assets', action='create'),
        PermissionFactory.create(resource='assets', action='update'),
        PermissionFactory.create(resource='assets', action='delete'),
        PermissionFactory.create(resource='users', action='read'),
        PermissionFactory.create(resource='users', action='create'),
        PermissionFactory.create(resource='users', action='update'),
        PermissionFactory.create(resource='users', action='delete'),
        PermissionFactory.create(resource='roles', action='read'),
        PermissionFactory.create(resource='roles', action='create'),
        PermissionFactory.create(resource='roles', action='update'),
        PermissionFactory.create(resource='roles', action='delete'),
    ]

    # 创建角色层级
    basic_role = RoleFactory.create(name='basic_user', level=1)
    manager_role = RoleFactory.create(name='asset_manager', level=5)
    admin_role = RoleFactory.create(name='system_admin', level=10)

    roles = [basic_role, manager_role, admin_role]

    return permissions, roles


# 测试数据清理工具
class TestDataCleanup:
    """测试数据清理工具"""

    @staticmethod
    def cleanup_test_data(session):
        """清理测试数据"""
        # 按依赖关系倒序删除
        session.query(AssetHistory).delete()
        session.query(Asset).delete()
        session.query(UserRoleAssignment).delete()
        session.query(User).delete()
        session.query(Role).delete()
        session.query(Permission).delete()
        session.commit()

    @staticmethod
    def create_test_data(session):
        """创建基础测试数据"""
        # 创建权限和角色
        permissions, roles = create_permission_hierarchy()

        # 创建测试用户
        admin = AdminUserFactory.create()
        normal_user = UserFactory.create()
        inactive_user = InactiveUserFactory.create()

        session.add_all(permissions + roles + [admin, normal_user, inactive_user])
        session.commit()

        return {
            'permissions': permissions,
            'roles': roles,
            'users': [admin, normal_user, inactive_user]
        }
