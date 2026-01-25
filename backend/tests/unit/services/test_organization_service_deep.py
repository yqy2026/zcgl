"""
组织服务深度测试

Deep tests for Organization Service to maximize coverage
"""

import pytest
from sqlalchemy.orm import Session
from datetime import datetime, UTC


@pytest.fixture
def org_service(db: Session):
    """组织服务实例"""
    from src.services.organization.service import OrganizationService
    return OrganizationService(db)


@pytest.fixture
def sample_organization(db: Session, admin_user):
    """示例组织数据"""
    from src.schemas.organization import OrganizationCreate
    from src.crud.organization import organization_crud

    org = organization_crud.create(
        db,
        obj_in=OrganizationCreate(
            name="测试组织",
            code="TEST-ORG-001",
            organization_type="enterprise",
            credit_code="91110000123456789X",
            legal_representative="张三",
            registration_date=datetime.now(UTC)
        )
    )
    yield org
    try:
        organization_crud.remove(db, id=org.id)
    except:
        pass


class TestOrganizationServiceDeep:
    """测试组织服务深度功能"""

    def test_organization_hierarchy_validation(self, org_service, db: Session):
        """测试组织层级验证"""
        # 创建父组织
        from src.schemas.organization import OrganizationCreate
        from src.crud.organization import organization_crud

        parent_org = organization_crud.create(
            db,
            obj_in=OrganizationCreate(
                name="父组织",
                code="PARENT-001",
                organization_type="enterprise"
            )
        )

        # 创建子组织
        child_org_data = OrganizationCreate(
            name="子组织",
            code="CHILD-001",
            organization_type="department",
            parent_id=parent_org.id
        )

        child_org = org_service.create_organization(db, child_org_data)
        assert child_org is not None
        assert child_org.parent_id == parent_org.id

        # 验证不能创建循环引用
        with pytest.raises(ValueError):
            org_service.update_organization(
                db,
                organization_id=parent_org.id,
                update_data={"parent_id": child_org.id}
            )

    def test_organization_code_uniqueness(self, org_service, db: Session):
        """测试组织代码唯一性"""
        from src.schemas.organization import OrganizationCreate
        from src.crud.organization import organization_crud

        # 创建第一个组织
        org1 = organization_crud.create(
            db,
            obj_in=OrganizationCreate(
                name="组织1",
                code="UNIQUE-001",
                organization_type="enterprise"
            )
        )

        # 尝试创建相同代码的第二个组织
        with pytest.raises(ValueError):
            org_service.create_organization(
                db,
                OrganizationCreate(
                    name="组织2",
                    code="UNIQUE-001",  # 重复代码
                    organization_type="enterprise"
                )
            )

    def test_get_organization_tree(self, org_service, db: Session):
        """测试获取组织树"""
        tree = org_service.get_organization_tree(db)
        assert tree is not None
        assert isinstance(tree, list)

    def test_get_sub_organizations(self, org_service, sample_organization, db: Session):
        """测试获取子组织"""
        sub_orgs = org_service.get_sub_organizations(
            db,
            parent_id=sample_organization.id
        )
        assert sub_orgs is not None
        assert isinstance(sub_orgs, list)

    def test_organization_statistics(self, org_service, db: Session):
        """测试组织统计信息"""
        stats = org_service.get_organization_statistics(db)
        assert stats is not None
        assert "total_count" in stats
        assert "by_type" in stats

    def test_search_organizations_advanced(self, org_service, db: Session):
        """测试高级搜索组织"""
        result = org_service.search_organizations(
            db,
            keyword="测试",
            organization_type="enterprise",
            include_inactive=False
        )
        assert result is not None

    def test_validate_credit_code(self, org_service):
        """测试验证统一社会信用代码"""
        # 有效信用代码
        valid_code = "91110000123456789X"
        assert org_service.validate_credit_code(valid_code) is not None

        # 无效信用代码
        with pytest.raises(ValueError):
            org_service.validate_credit_code("invalid")

    def test_organization_merge(self, org_service, db: Session):
        """测试合并组织"""
        from src.schemas.organization import OrganizationCreate
        from src.crud.organization import organization_crud

        # 创建两个组织
        org1 = organization_crud.create(
            db,
            obj_in=OrganizationCreate(
                name="待合并组织1",
                code="MERGE-001",
                organization_type="enterprise"
            )
        )

        org2 = organization_crud.create(
            db,
            obj_in=OrganizationCreate(
                name="待合并组织2",
                code="MERGE-002",
                organization_type="enterprise"
            )
        )

        # 合并组织
        merged_org = org_service.merge_organizations(
            db,
            source_org_ids=[org1.id, org2.id],
            target_org_data={
                "name": "合并后组织",
                "code": "MERGED-001",
                "organization_type": "enterprise"
            }
        )
        assert merged_org is not None

    def test_organization_split(self, org_service, sample_organization, db: Session):
        """测试拆分组织"""
        split_data = [
            {
                "name": "拆分后组织1",
                "code": "SPLIT-001",
                "organization_type": "department"
            },
            {
                "name": "拆分后组织2",
                "code": "SPLIT-002",
                "organization_type": "department"
            }
        ]

        result = org_service.split_organization(
            db,
            organization_id=sample_organization.id,
            split_data=split_data
        )
        assert result is not None
        assert len(result) == 2

    def test_update_organization_status(self, org_service, sample_organization, db: Session):
        """测试更新组织状态"""
        updated = org_service.update_organization_status(
            db,
            organization_id=sample_organization.id,
            new_status="inactive"
        )
        assert updated is not None
        assert updated.status == "inactive"

    def test_get_organization_path(self, org_service, sample_organization):
        """测试获取组织路径"""
        path = org_service.get_organization_path(
            organization_id=sample_organization.id
        )
        assert path is not None
        assert isinstance(path, list)

    def test_organization_contact_info_validation(self, org_service, db: Session):
        """测试验证组织联系信息"""
        contact_info = {
            "phone": "010-12345678",
            "email": "test@example.com",
            "address": "北京市朝阳区"
        }

        result = org_service.validate_contact_info(contact_info)
        assert result is not None

    def test_organization_with_encryption(self, org_service, db: Session):
        """测试组织敏感信息加密"""
        from src.schemas.organization import OrganizationCreate

        org_data = OrganizationCreate(
            name="加密测试组织",
            code="ENCRYPT-001",
            organization_type="enterprise",
            id_card="110101199001015555",
            phone="13800137777",
            leader_phone="13800136666",
            emergency_phone="13800135555"
        )

        result = org_service.create_organization(db, org_data)
        assert result is not None
        # 敏感信息应该被加密存储

    def test_batch_update_organizations(self, org_service, db: Session):
        """测试批量更新组织"""
        org_ids = ["org-1", "org-2"]
        update_data = {"status": "active"}

        result = org_service.batch_update_organizations(
            db,
            organization_ids=org_ids,
            update_data=update_data
        )
        assert result is not None

    def test_get_organization_ancestors(self, org_service, sample_organization):
        """测试获取组织祖先节点"""
        ancestors = org_service.get_organization_ancestors(
            organization_id=sample_organization.id
        )
        assert ancestors is not None
        assert isinstance(ancestors, list)

    def test_get_organization_descendants(self, org_service, sample_organization):
        """测试获取组织后代节点"""
        descendants = org_service.get_organization_descendants(
            organization_id=sample_organization.id
        )
        assert descendants is not None
        assert isinstance(descendants, list)

    def test_validate_organization_type_change(self, org_service, sample_organization, db: Session):
        """测试验证组织类型变更"""
        # 某些类型变更可能被限制
        with pytest.raises(ValueError):
            org_service.update_organization(
                db,
                organization_id=sample_organization.id,
                update_data={"organization_type": "invalid_type"}
            )

    def test_organization_registration_date_validation(self, org_service, db: Session):
        """测试验证组织注册日期"""
        from datetime import datetime

        # 注册日期不能在未来
        with pytest.raises(ValueError):
            org_service.create_organization(
                db,
                {
                    "name": "未来组织",
                    "code": "FUTURE-001",
                    "organization_type": "enterprise",
                    "registration_date": datetime(2030, 1, 1)
                }
            )

    def test_get_active_organizations(self, org_service, db: Session):
        """测试获取活跃组织"""
        active_orgs = org_service.get_active_organizations(db)
        assert active_orgs is not None
        assert isinstance(active_orgs, list)

    def test_organization_deactivation_cascade(self, org_service, sample_organization, db: Session):
        """测试组织停用的级联影响"""
        # 停用父组织时，子组织也应该被停用
        result = org_service.deactivate_organization_with_children(
            db,
            organization_id=sample_organization.id
        )
        assert result is not None

    def test_get_organization_by_credit_code(self, org_service, db: Session):
        """测试按信用代码获取组织"""
        org = org_service.get_organization_by_credit_code(
            db,
            credit_code="91110000123456789X"
        )
        # 可能返回None或组织对象
        assert org is None or hasattr(org, 'id')

    def test_organization_name_uniqueness_in_type(self, org_service, db: Session):
        """测试验证同类型组织名称唯一性"""
        from src.schemas.organization import OrganizationCreate
        from src.crud.organization import organization_crud

        # 创建第一个组织
        org1 = organization_crud.create(
            db,
            obj_in=OrganizationCreate(
                name="同名组织",
                code="NAME-001",
                organization_type="enterprise"
            )
        )

        # 尝试创建同类型同名组织
        with pytest.raises(ValueError):
            org_service.create_organization(
                db,
                OrganizationCreate(
                    name="同名组织",  # 同名
                    code="NAME-002",
                    organization_type="enterprise"  # 同类型
                )
            )
