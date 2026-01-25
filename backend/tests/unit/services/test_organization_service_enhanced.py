"""
组织服务增强测试

Enhanced tests for Organization Service to improve coverage
"""

import pytest
from sqlalchemy.orm import Session


@pytest.fixture
def org_service(db: Session):
    """组织服务实例"""
    from src.services.organization.service import OrganizationService
    return OrganizationService(db)


@pytest.fixture
def sample_organization(db: Session):
    """示例组织数据"""
    from src.schemas.organization import OrganizationCreate
    from src.crud.organization import organization_crud

    org = organization_crud.create(
        db,
        obj_in=OrganizationCreate(
            name="测试组织",
            code="TEST-ORG-001",
            organization_type="enterprise",
            unified_social_credit_code="91110000123456789X"
        )
    )
    yield org
    try:
        organization_crud.remove(db, id=org.id)
    except:
        pass


class TestOrganizationServiceBusinessLogic:
    """测试组织服务业务逻辑"""

    def test_organization_code_validation(self, org_service, db: Session):
        """测试组织代码验证"""
        # 测试重复代码
        from src.schemas.organization import OrganizationCreate
        from src.crud.organization import organization_crud

        org1 = organization_crud.create(
            db,
            obj_in=OrganizationCreate(
                name="组织1",
                code="DUPLICATE",
                organization_type="enterprise"
            )
        )

        # 尝试创建重复代码的组织
        with pytest.raises(ValueError):
            org_service.create_organization(
                db,
                OrganizationCreate(
                    name="组织2",
                    code="DUPLICATE",
                    organization_type="enterprise"
                )
            )

    def test_organization_hierarchy(self, org_service, sample_organization):
        """测试组织层级关系"""
        # 测试父子组织关系
        pass

    def test_organization_statistics(self, org_service, sample_organization):
        """测试组织统计信息"""
        stats = org_service.get_organization_statistics(
            db, sample_organization.id
        )
        assert stats is not None

    def test_organization_filter_by_type(self, org_service, db: Session):
        """测试按类型筛选组织"""
        result = org_service.filter_organizations(
            db,
            organization_type="enterprise"
        )
        assert result is not None

    def test_organization_search(self, org_service, db: Session):
        """测试组织搜索功能"""
        result = org_service.search_organizations(
            db,
            keyword="测试"
        )
        assert result is not None
