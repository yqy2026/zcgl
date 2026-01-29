"""
权属服务完整测试

Complete tests for Ownership Service to maximize coverage
"""


import pytest
from sqlalchemy.orm import Session


@pytest.fixture
def ownership_service(db: Session):
    """权属服务实例"""
    from src.services.ownership.service import OwnershipService

    return OwnershipService(db)


@pytest.fixture
def sample_ownership(db: Session, admin_user):
    """示例权属数据"""
    from src.crud.ownership import ownership_crud
    from src.schemas.ownership import OwnershipCreate

    ownership = ownership_crud.create(
        db,
        obj_in=OwnershipCreate(
            owner_name="测试业主",
            owner_type="individual",
            id_card="110101199001011234",
            phone="13800138000",
            address="北京市朝阳区测试地址",
            ownership_ratio=100.0,
            asset_id="asset-001",
        ),
    )
    yield ownership
    try:
        ownership_crud.remove(db, id=ownership.id)
    except Exception:
        pass


@pytest.fixture
def sample_ownership_with_org(db: Session, admin_user):
    """组织权属数据"""
    from src.crud.ownership import ownership_crud
    from src.schemas.ownership import OwnershipCreate

    ownership = ownership_crud.create(
        db,
        obj_in=OwnershipCreate(
            owner_name="测试公司",
            owner_type="enterprise",
            credit_code="91110000123456789X",
            phone="010-12345678",
            address="北京市海淀区测试地址",
            ownership_ratio=50.0,
            asset_id="asset-002",
        ),
    )
    yield ownership
    try:
        ownership_crud.remove(db, id=ownership.id)
    except Exception:
        pass


class TestOwnershipServiceBusinessLogic:
    """测试权属服务业务逻辑"""

    def test_calculate_total_ownership_ratio(self, ownership_service, db: Session):
        """测试计算总权属比例"""
        total_ratio = ownership_service.calculate_total_ownership_ratio(
            db, asset_id="asset-001"
        )
        assert total_ratio is not None
        assert total_ratio >= 0
        assert total_ratio <= 100

    def test_validate_ownership_ratio_exceeds_100(self, ownership_service, db: Session):
        """测试验证权属比例超过100%"""
        with pytest.raises(ValueError):
            ownership_service.validate_ownership_ratio(
                db, asset_id="asset-001", new_ratio=150.0
            )

    def test_transfer_ownership_success(
        self, ownership_service, sample_ownership, db: Session
    ):
        """测试成功转移权属"""
        new_owner_data = {
            "owner_name": "新业主",
            "owner_type": "individual",
            "id_card": "110101199001019999",
            "phone": "13900139000",
        }

        result = ownership_service.transfer_ownership(
            db, ownership_id=sample_ownership.id, new_owner_data=new_owner_data
        )
        assert result is not None
        assert result.owner_name == "新业主"

    def test_split_ownership(self, ownership_service, sample_ownership, db: Session):
        """测试分割权属"""
        split_data = [
            {
                "owner_name": "共有人1",
                "owner_type": "individual",
                "ownership_ratio": 60.0,
                "id_card": "110101199001011111",
            },
            {
                "owner_name": "共有人2",
                "owner_type": "individual",
                "ownership_ratio": 40.0,
                "id_card": "110101199001012222",
            },
        ]

        result = ownership_service.split_ownership(
            db, ownership_id=sample_ownership.id, split_data=split_data
        )
        assert result is not None
        assert len(result) == 2

    def test_merge_ownerships(self, ownership_service, db: Session):
        """测试合并权属"""
        ownership_ids = ["ownership-1", "ownership-2"]

        result = ownership_service.merge_ownerships(
            db,
            ownership_ids=ownership_ids,
            merged_owner_data={
                "owner_name": "合并后业主",
                "owner_type": "individual",
                "id_card": "110101199001013333",
            },
        )
        assert result is not None

    def test_get_ownership_history(self, ownership_service, sample_ownership):
        """测试获取权属历史"""
        history = ownership_service.get_ownership_history(
            ownership_id=sample_ownership.id
        )
        assert history is not None

    def test_verify_ownership_documents(self, ownership_service, sample_ownership):
        """测试验证权属文档"""
        documents = ["doc1.pdf", "doc2.pdf"]

        result = ownership_service.verify_ownership_documents(
            ownership_id=sample_ownership.id, document_ids=documents
        )
        assert result is not None

    def test_get_owners_by_asset(self, ownership_service, db: Session):
        """测试按资产获取所有业主"""
        owners = ownership_service.get_owners_by_asset(db, asset_id="asset-001")
        assert owners is not None
        assert isinstance(owners, list)

    def test_get_assets_by_owner(self, ownership_service, db: Session):
        """测试按业主获取所有资产"""
        assets = ownership_service.get_assets_by_owner(db, owner_id="owner-001")
        assert assets is not None
        assert isinstance(assets, list)

    def test_update_ownership_ratio(
        self, ownership_service, sample_ownership, db: Session
    ):
        """测试更新权属比例"""
        new_ratio = 75.0

        result = ownership_service.update_ownership_ratio(
            db, ownership_id=sample_ownership.id, new_ratio=new_ratio
        )
        assert result is not None
        assert result.ownership_ratio == new_ratio

    def test_validate_id_card_format(self, ownership_service):
        """测试验证身份证号格式"""
        # 有效身份证号
        assert ownership_service.validate_id_card("110101199001011234") is not None

        # 无效身份证号
        with pytest.raises(ValueError):
            ownership_service.validate_id_card("invalid_id")

    def test_validate_credit_code_format(self, ownership_service):
        """测试验证统一社会信用代码格式"""
        # 有效信用代码
        assert ownership_service.validate_credit_code("91110000123456789X") is not None

        # 无效信用代码
        with pytest.raises(ValueError):
            ownership_service.validate_credit_code("invalid_code")

    def test_get_ownership_statistics(self, ownership_service, db: Session):
        """测试获取权属统计信息"""
        stats = ownership_service.get_ownership_statistics(db)
        assert stats is not None
        assert "total_ownerships" in stats
        assert "individual_owners" in stats
        assert "enterprise_owners" in stats

    def test_search_ownerships_advanced(self, ownership_service, db: Session):
        """测试高级搜索权属"""
        result = ownership_service.search_ownerships(
            db, keyword="测试", owner_type="individual", asset_id="asset-001"
        )
        assert result is not None

    def test_calculate_ownership_value(self, ownership_service, sample_ownership):
        """测试计算权属价值"""
        asset_value = 1000000.0

        ownership_value = ownership_service.calculate_ownership_value(
            ownership_id=sample_ownership.id, asset_value=asset_value
        )
        assert ownership_value is not None
        assert ownership_value >= 0

    def test_check_ownership_completeness(self, ownership_service, db: Session):
        """测试检查权属完整性"""
        completeness = ownership_service.check_ownership_completeness(
            db, asset_id="asset-001"
        )
        assert completeness is not None
        assert "is_complete" in completeness
        assert "total_ratio" in completeness

    def test_get_joint_owners(self, ownership_service, db: Session):
        """测试获取共有权人"""
        joint_owners = ownership_service.get_joint_owners(db, asset_id="asset-001")
        assert joint_owners is not None
        assert isinstance(joint_owners, list)

    def test_create_ownership_with_encryption(self, ownership_service, db: Session):
        """测试创建权属时加密敏感信息"""
        ownership_data = {
            "owner_name": "加密测试业主",
            "owner_type": "individual",
            "id_card": "110101199001014444",
            "phone": "13800138888",
            "asset_id": "asset-003",
            "ownership_ratio": 100.0,
        }

        result = ownership_service.create_ownership(db, ownership_data)
        assert result is not None
        # 验证敏感信息已加密（存储时）
        # 实际验证需要查询数据库

    def test_update_encrypted_fields(
        self, ownership_service, sample_ownership, db: Session
    ):
        """测试更新加密字段"""
        update_data = {"phone": "13900139999"}

        result = ownership_service.update_ownership(
            db, ownership_id=sample_ownership.id, update_data=update_data
        )
        assert result is not None
