"""
OrganizationService 集成测试
测试组织的创建、更新、删除、统计等功能
"""

import pytest
from sqlalchemy.orm import Session

from src.models.organization import OrganizationHistory
from src.schemas.organization import OrganizationCreate, OrganizationUpdate
from src.services.organization.service import OrganizationService

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
            "type": "企业",
            "status": "启用",
            "parent_id": None,
        }
        default_data.update(kwargs)
        return default_data


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def organization_service(db_session: Session):
    """OrganizationService实例"""
    return OrganizationService()


# ============================================================================
# Test Class 1: Organization Creation
# ============================================================================


class TestOrganizationCreation:
    """组织创建测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session, organization_service: OrganizationService):
        self.db = db_session
        self.service = organization_service
        self.factory = OrganizationTestDataFactory()

    def test_create_organization_success(self):
        """测试成功创建组织"""
        org_data = OrganizationCreate(**self.factory.create_org_dict())

        org = self.service.create_organization(self.db, obj_in=org_data)

        assert org.id is not None
        assert org.name == "测试组织"
        assert org.code == "TEST001"
        assert org.level == 1
        assert org.path.startswith("/")

    def test_create_organization_with_parent(self):
        """测试创建带父组织的组织"""
        # 先创建父组织
        parent_data = OrganizationCreate(
            **self.factory.create_org_dict(
                name="父组织",
                code="PARENT001",
            )
        )
        parent = self.service.create_organization(self.db, obj_in=parent_data)

        # 创建子组织
        child_data = OrganizationCreate(
            **self.factory.create_org_dict(
                name="子组织",
                code="CHILD001",
                parent_id=parent.id,
            )
        )
        child = self.service.create_organization(self.db, obj_in=child_data)

        assert child.level == 2
        assert child.parent_id == parent.id
        assert child.path.startswith(parent.path)

    def test_create_organization_with_invalid_parent_raises_error(self):
        """测试使用无效的parent_id创建组织抛出异常"""
        org_data = OrganizationCreate(
            **self.factory.create_org_dict(
                parent_id="nonexistent-id",
            )
        )

        with pytest.raises(ValueError, match="上级组织.*不存在"):
            self.service.create_organization(self.db, obj_in=org_data)

    def test_create_organization_creates_history(self):
        """测试创建组织时记录历史"""
        org_data = OrganizationCreate(
            **self.factory.create_org_dict(
                created_by="test_user",
            )
        )

        org = self.service.create_organization(self.db, obj_in=org_data)

        history = (
            self.db.query(OrganizationHistory)
            .filter(OrganizationHistory.organization_id == org.id)
            .first()
        )

        assert history is not None
        assert history.action == "create"
        assert history.created_by == "test_user"


# ============================================================================
# Test Class 2: Organization Update
# ============================================================================


class TestOrganizationUpdate:
    """组织更新测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session, organization_service: OrganizationService):
        self.db = db_session
        self.service = organization_service
        self.factory = OrganizationTestDataFactory()

        # 创建测试组织
        org_data = OrganizationCreate(**self.factory.create_org_dict())
        self.org = self.service.create_organization(self.db, obj_in=org_data)

    def test_update_organization_basic_fields(self):
        """测试更新组织基本信息"""
        update_data = OrganizationUpdate(
            name="更新后的组织",
            status="停用",
        )

        updated = self.service.update_organization(
            self.db, org_id=self.org.id, obj_in=update_data
        )

        assert updated.name == "更新后的组织"
        assert updated.status == "停用"

    def test_update_organization_with_parent_change(self):
        """测试更改组织的父组织"""
        # 创建新的父组织
        new_parent_data = OrganizationCreate(
            **self.factory.create_org_dict(
                name="新父组织",
                code="NEWPARENT",
            )
        )
        new_parent = self.service.create_organization(self.db, obj_in=new_parent_data)

        # 更新父组织
        update_data = OrganizationUpdate(parent_id=new_parent.id)
        updated = self.service.update_organization(
            self.db, org_id=self.org.id, obj_in=update_data
        )

        assert updated.parent_id == new_parent.id
        assert updated.level == 2

    def test_update_organization_parent_to_child_raises_cycle_error(self):
        """测试将组织移动到其子组织下抛出循环引用错误"""
        # 先创建子组织
        child_data = OrganizationCreate(
            **self.factory.create_org_dict(
                name="子组织",
                code="CHILD001",
                parent_id=self.org.id,
            )
        )
        child = self.service.create_organization(self.db, obj_in=child_data)

        # 尝试将父组织移动到子组织下
        update_data = OrganizationUpdate(parent_id=child.id)

        with pytest.raises(ValueError, match="不能将组织移动到其子组织下"):
            self.service.update_organization(
                self.db, org_id=self.org.id, obj_in=update_data
            )

    def test_update_nonexistent_organization_raises_error(self):
        """测试更新不存在的组织抛出异常"""
        update_data = OrganizationUpdate(name="新名称")

        with pytest.raises(ValueError, match="组织ID.*不存在"):
            self.service.update_organization(
                self.db, org_id="nonexistent-id", obj_in=update_data
            )

    def test_update_organization_creates_history(self):
        """测试更新组织时记录历史"""
        update_data = OrganizationUpdate(
            name="新名称",
            updated_by="test_user",
        )

        self.service.update_organization(
            self.db, org_id=self.org.id, obj_in=update_data
        )

        history = (
            self.db.query(OrganizationHistory)
            .filter(
                OrganizationHistory.organization_id == self.org.id,
                OrganizationHistory.action == "update",
            )
            .first()
        )

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
    def setup(self, db_session: Session, organization_service: OrganizationService):
        self.db = db_session
        self.service = organization_service
        self.factory = OrganizationTestDataFactory()

    def test_delete_organization_success(self):
        """测试成功删除组织"""
        org_data = OrganizationCreate(**self.factory.create_org_dict())
        org = self.service.create_organization(self.db, obj_in=org_data)

        result = self.service.delete_organization(
            self.db, org_id=org.id, deleted_by="test_user"
        )

        assert result is True

        # 验证软删除标记
        self.db.refresh(org)
        assert org.is_deleted is True

    def test_delete_organization_with_children_raises_error(self):
        """测试删除有子组织的组织抛出异常"""
        # 创建父组织
        parent_data = OrganizationCreate(
            **self.factory.create_org_dict(
                name="父组织",
            )
        )
        parent = self.service.create_organization(self.db, obj_in=parent_data)

        # 创建子组织
        child_data = OrganizationCreate(
            **self.factory.create_org_dict(
                name="子组织",
                parent_id=parent.id,
            )
        )
        self.service.create_organization(self.db, obj_in=child_data)

        # 尝试删除父组织
        with pytest.raises(ValueError, match="不能删除有子组织的组织"):
            self.service.delete_organization(self.db, org_id=parent.id)

    def test_delete_nonexistent_organization_returns_false(self):
        """测试删除不存在的组织返回False"""
        result = self.service.delete_organization(self.db, org_id="nonexistent-id")
        assert result is False


# ============================================================================
# Test Class 4: Organization Statistics
# ============================================================================


class TestOrganizationStatistics:
    """组织统计测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session, organization_service: OrganizationService):
        self.db = db_session
        self.service = organization_service

    def test_get_statistics_empty_database(self):
        """测试空数据库的统计信息"""
        stats = self.service.get_statistics(self.db)

        assert stats["total"] == 0
        assert stats["active"] == 0
        assert stats["inactive"] == 0
        assert isinstance(stats["by_level"], dict)

    def test_get_statistics_with_organizations(self):
        """测试有组织时的统计信息"""
        # 创建3个组织
        for i in range(3):
            org_data = OrganizationCreate(
                **OrganizationTestDataFactory.create_org_dict(
                    name=f"组织{i}",
                    code=f"ORG{i:03d}",
                )
            )
            self.service.create_organization(self.db, obj_in=org_data)

        stats = self.service.get_statistics(self.db)

        assert stats["total"] == 3
        assert stats["active"] == 3
        assert stats["by_level"]["level_1"] == 3

    def test_get_statistics_with_multiple_levels(self):
        """测试多层级组织的统计信息"""
        # 创建父组织
        parent_data = OrganizationCreate(
            **OrganizationTestDataFactory.create_org_dict(
                name="父组织",
                code="PARENT",
            )
        )
        parent = self.service.create_organization(self.db, obj_in=parent_data)

        # 创建子组织
        child_data = OrganizationCreate(
            **OrganizationTestDataFactory.create_org_dict(
                name="子组织",
                code="CHILD",
                parent_id=parent.id,
            )
        )
        self.service.create_organization(self.db, obj_in=child_data)

        stats = self.service.get_statistics(self.db)

        assert stats["total"] == 2
        assert stats["by_level"]["level_1"] == 1
        assert stats["by_level"]["level_2"] == 1
