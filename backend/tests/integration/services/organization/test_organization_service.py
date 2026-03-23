"""
OrganizationService 集成测试
测试组织的创建、更新、删除、统计等功能
"""

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from src import database as database
from src.core.cache_manager import cache_manager
from src.core.exception_handler import OperationNotAllowedError, ResourceNotFoundError
from src.models.enum_field import EnumFieldType, EnumFieldValue
from src.models.organization import OrganizationHistory
from src.schemas.organization import OrganizationCreate, OrganizationUpdate
from src.services.organization.service import OrganizationService

pytestmark = pytest.mark.asyncio

# ============================================================================
# Test Data Factory
# ============================================================================


class OrganizationTestDataFactory:
    """组织测试数据工厂"""

    @staticmethod
    def create_org_dict(**kwargs):
        """生成组织创建数据"""
        default_data = {
            "name": "测试组织",
            "code": "TEST001",
            "type": "company",
            "status": "active",
            "parent_id": None,
        }
        default_data.update(kwargs)
        return default_data


async def _ensure_organization_enum_data(db_session: AsyncSession) -> None:
    enum_defs: dict[str, tuple[str, list[str]]] = {
        "organization_type": (
            "组织类型",
            ["company", "group", "division", "department", "team", "branch", "office"],
        ),
        "organization_status": (
            "组织状态",
            ["active", "inactive", "suspended"],
        ),
    }

    for code, (name, values) in enum_defs.items():
        result = await db_session.execute(
            select(EnumFieldType).where(EnumFieldType.code == code)
        )
        enum_type = result.scalars().first()
        if enum_type is None:
            enum_type = EnumFieldType(
                name=name,
                code=code,
                category="系统管理",
                is_system=True,
                status="active",
                is_deleted=False,
                created_by="integration_test",
                updated_by="integration_test",
            )
            db_session.add(enum_type)
            await db_session.flush()
        else:
            enum_type.status = "active"
            enum_type.is_deleted = False
            enum_type.updated_by = "integration_test"

        value_result = await db_session.execute(
            select(EnumFieldValue).where(EnumFieldValue.enum_type_id == enum_type.id)
        )
        existing_values = {value_obj.value: value_obj for value_obj in value_result.scalars().all()}

        for sort_order, value in enumerate(values, start=1):
            value_obj = existing_values.get(value)
            if value_obj is None:
                db_session.add(
                    EnumFieldValue(
                        enum_type_id=enum_type.id,
                        label=value,
                        value=value,
                        sort_order=sort_order,
                        is_active=True,
                        is_deleted=False,
                        created_by="integration_test",
                        updated_by="integration_test",
                    )
                )
                continue

            value_obj.label = value
            value_obj.sort_order = sort_order
            value_obj.is_active = True
            value_obj.is_deleted = False
            value_obj.updated_by = "integration_test"

    await db_session.flush()


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def db_session():
    """创建异步数据库会话，并在测试结束后回滚事务。"""
    async_engine = create_async_engine(
        database.get_async_database_url(),
        echo=False,
        poolclass=NullPool,
    )
    async with async_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            # Keep integration tests deterministic even when shared test DB has leftover data.
            await connection.execute(
                text(
                    "TRUNCATE TABLE organization_history, organizations "
                    "RESTART IDENTITY CASCADE"
                )
            )
            cache_manager.clear(namespace=OrganizationService.CACHE_NAMESPACE)
            yield session
        finally:
            cache_manager.clear(namespace=OrganizationService.CACHE_NAMESPACE)
            await session.close()
            await transaction.rollback()
            await async_engine.dispose()


@pytest.fixture
def organization_service(db_session: AsyncSession):
    """OrganizationService实例"""
    return OrganizationService()


# ============================================================================
# Test Class 1: Organization Creation
# ============================================================================


class TestOrganizationCreation:
    """组织创建测试"""

    @pytest.fixture(autouse=True)
    async def setup(
        self, db_session: AsyncSession, organization_service: OrganizationService
    ):
        self.db = db_session
        self.service = organization_service
        self.factory = OrganizationTestDataFactory()
        await _ensure_organization_enum_data(self.db)

    async def test_create_organization_success(self):
        """测试成功创建组织"""
        org_data = OrganizationCreate(**self.factory.create_org_dict())

        org = await self.service.create_organization(self.db, obj_in=org_data)

        assert org.id is not None
        assert org.name == "测试组织"
        assert org.code == "TEST001"
        assert org.level == 1
        assert org.path.startswith("/")

    async def test_create_organization_with_parent(self):
        """测试创建带父组织的组织"""
        # 先创建父组织
        parent_data = OrganizationCreate(
            **self.factory.create_org_dict(
                name="父组织",
                code="PARENT001",
            )
        )
        parent = await self.service.create_organization(self.db, obj_in=parent_data)

        # 创建子组织
        child_data = OrganizationCreate(
            **self.factory.create_org_dict(
                name="子组织",
                code="CHILD001",
                parent_id=parent.id,
            )
        )
        child = await self.service.create_organization(self.db, obj_in=child_data)

        assert child.level == 2
        assert child.parent_id == parent.id
        assert child.path.startswith(parent.path)

    async def test_create_organization_with_invalid_parent_raises_error(self):
        """测试使用无效的parent_id创建组织抛出异常"""
        org_data = OrganizationCreate(
            **self.factory.create_org_dict(
                parent_id="nonexistent-id",
            )
        )

        with pytest.raises(ResourceNotFoundError):
            await self.service.create_organization(self.db, obj_in=org_data)

    async def test_create_organization_creates_history(self):
        """测试创建组织时记录历史"""
        org_data = OrganizationCreate(
            **self.factory.create_org_dict(
                created_by="test_user",
            )
        )

        org = await self.service.create_organization(self.db, obj_in=org_data)

        result = await self.db.execute(
            select(OrganizationHistory).where(
                OrganizationHistory.organization_id == org.id
            )
        )
        history = result.scalars().first()

        assert history is not None
        assert history.action == "create"
        assert history.created_by == "test_user"


# ============================================================================
# Test Class 2: Organization Update
# ============================================================================


class TestOrganizationUpdate:
    """组织更新测试"""

    @pytest.fixture(autouse=True)
    async def setup(
        self, db_session: AsyncSession, organization_service: OrganizationService
    ):
        self.db = db_session
        self.service = organization_service
        self.factory = OrganizationTestDataFactory()
        await _ensure_organization_enum_data(self.db)

        # 创建测试组织
        org_data = OrganizationCreate(**self.factory.create_org_dict())
        self.org = await self.service.create_organization(self.db, obj_in=org_data)

    async def test_update_organization_basic_fields(self):
        """测试更新组织基本信息"""
        update_data = OrganizationUpdate(
            name="更新后的组织",
            status="inactive",
        )

        updated = await self.service.update_organization(
            self.db, org_id=self.org.id, obj_in=update_data
        )

        assert updated.name == "更新后的组织"
        assert updated.status == "inactive"

    async def test_update_organization_with_parent_change(self):
        """测试更改组织的父组织"""
        # 创建新的父组织
        new_parent_data = OrganizationCreate(
            **self.factory.create_org_dict(
                name="新父组织",
                code="NEWPARENT",
            )
        )
        new_parent = await self.service.create_organization(
            self.db, obj_in=new_parent_data
        )

        # 更新父组织
        update_data = OrganizationUpdate(parent_id=new_parent.id)
        updated = await self.service.update_organization(
            self.db, org_id=self.org.id, obj_in=update_data
        )

        assert updated.parent_id == new_parent.id
        assert updated.level == 2

    async def test_update_organization_parent_to_child_raises_cycle_error(self):
        """测试将组织移动到其子组织下抛出循环引用错误"""
        # 先创建子组织
        child_data = OrganizationCreate(
            **self.factory.create_org_dict(
                name="子组织",
                code="CHILD001",
                parent_id=self.org.id,
            )
        )
        child = await self.service.create_organization(self.db, obj_in=child_data)

        # 尝试将父组织移动到子组织下
        update_data = OrganizationUpdate(parent_id=child.id)

        with pytest.raises(OperationNotAllowedError, match="不能将组织移动到其子组织下"):
            await self.service.update_organization(
                self.db, org_id=self.org.id, obj_in=update_data
            )

    async def test_update_nonexistent_organization_raises_error(self):
        """测试更新不存在的组织抛出异常"""
        update_data = OrganizationUpdate(name="新名称")

        with pytest.raises(ResourceNotFoundError):
            await self.service.update_organization(
                self.db, org_id="nonexistent-id", obj_in=update_data
            )

    async def test_update_organization_creates_history(self):
        """测试更新组织时记录历史"""
        update_data = OrganizationUpdate(
            name="新名称",
            updated_by="test_user",
        )

        await self.service.update_organization(
            self.db, org_id=self.org.id, obj_in=update_data
        )

        result = await self.db.execute(
            select(OrganizationHistory).where(
                OrganizationHistory.organization_id == self.org.id,
                OrganizationHistory.action == "update",
            )
        )
        history = result.scalars().first()

        assert history is not None
        assert history.field_name == "name"
        assert history.old_value == "测试组织"
        assert history.new_value == "新名称"


# ============================================================================
# Test Class 3: Organization Deletion
# ============================================================================


class TestOrganizationDeletion:
    """组织删除测试"""

    @pytest.fixture(autouse=True)
    async def setup(
        self, db_session: AsyncSession, organization_service: OrganizationService
    ):
        self.db = db_session
        self.service = organization_service
        self.factory = OrganizationTestDataFactory()

    async def test_delete_organization_success(self):
        """测试成功删除组织"""
        org_data = OrganizationCreate(**self.factory.create_org_dict())
        org = await self.service.create_organization(self.db, obj_in=org_data)

        result = await self.service.delete_organization(
            self.db, org_id=org.id, deleted_by="test_user"
        )

        assert result is True

        # 验证软删除标记
        await self.db.refresh(org)
        assert org.is_deleted is True

    async def test_delete_organization_with_children_raises_error(self):
        """测试删除有子组织的组织抛出异常"""
        # 创建父组织
        parent_data = OrganizationCreate(
            **self.factory.create_org_dict(
                name="父组织",
            )
        )
        parent = await self.service.create_organization(self.db, obj_in=parent_data)

        # 创建子组织
        child_data = OrganizationCreate(
            **self.factory.create_org_dict(
                name="子组织",
                parent_id=parent.id,
            )
        )
        await self.service.create_organization(self.db, obj_in=child_data)

        # 尝试删除父组织
        with pytest.raises(OperationNotAllowedError, match="不能删除有子组织的组织"):
            await self.service.delete_organization(self.db, org_id=parent.id)

    async def test_delete_nonexistent_organization_returns_false(self):
        """测试删除不存在的组织返回False"""
        result = await self.service.delete_organization(
            self.db, org_id="nonexistent-id"
        )
        assert result is False


# ============================================================================
# Test Class 4: Organization Statistics
# ============================================================================


class TestOrganizationStatistics:
    """组织统计测试"""

    @pytest.fixture(autouse=True)
    async def setup(
        self, db_session: AsyncSession, organization_service: OrganizationService
    ):
        self.db = db_session
        self.service = organization_service

    async def test_get_statistics_empty_database(self):
        """测试空数据库的统计信息"""
        stats = await self.service.get_statistics(self.db)

        assert stats["total"] == 0
        assert stats["active"] == 0
        assert stats["inactive"] == 0
        assert isinstance(stats["by_level"], dict)

    async def test_get_statistics_with_organizations(self):
        """测试有组织时的统计信息"""
        # 创建3个组织
        for i in range(3):
            org_data = OrganizationCreate(
                **OrganizationTestDataFactory.create_org_dict(
                    name=f"组织{i}",
                    code=f"ORG{i:03d}",
                )
            )
            await self.service.create_organization(self.db, obj_in=org_data)

        stats = await self.service.get_statistics(self.db)

        assert stats["total"] == 3
        assert stats["active"] == 3
        assert stats["by_level"]["level_1"] == 3

    async def test_get_statistics_with_multiple_levels(self):
        """测试多层级组织的统计信息"""
        # 创建父组织
        parent_data = OrganizationCreate(
            **OrganizationTestDataFactory.create_org_dict(
                name="父组织",
                code="PARENT",
            )
        )
        parent = await self.service.create_organization(self.db, obj_in=parent_data)

        # 创建子组织
        child_data = OrganizationCreate(
            **OrganizationTestDataFactory.create_org_dict(
                name="子组织",
                code="CHILD",
                parent_id=parent.id,
            )
        )
        await self.service.create_organization(self.db, obj_in=child_data)

        stats = await self.service.get_statistics(self.db)

        assert stats["total"] == 2
        assert stats["by_level"]["level_1"] == 1
        assert stats["by_level"]["level_2"] == 1
