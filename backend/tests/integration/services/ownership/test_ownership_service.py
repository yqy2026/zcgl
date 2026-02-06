"""
OwnershipService 集成测试
测试权属方的创建、更新、删除、统计等功能
"""

import pytest
from sqlalchemy.orm import Session

from src.models.ownership import Ownership
from src.schemas.ownership import OwnershipCreate, OwnershipUpdate
from src.services.ownership.service import OwnershipService

# ============================================================================
# Test Data Factory
# ============================================================================


class OwnershipTestDataFactory:
    """权属方测试数据工厂"""

    @staticmethod
    def create_ownership_dict(**kwargs):
        """生成权属方创建数据"""
        default_data = {
            "name": "测试权属方A",
            "short_name": "测试公司A",
            "type": "企业",
        }
        default_data.update(kwargs)
        return default_data


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def ownership_service():
    """OwnershipService实例"""
    return OwnershipService()


# ============================================================================
# Test Class 1: Ownership Creation
# ============================================================================


class TestOwnershipCreation:
    """权属方创建测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session, ownership_service: OwnershipService):
        self.db = db_session
        self.service = ownership_service
        self.factory = OwnershipTestDataFactory()

    def test_create_ownership_success(self):
        """测试成功创建权属方"""
        ownership_data = OwnershipCreate(**self.factory.create_ownership_dict())

        ownership = self.service.create_ownership(self.db, obj_in=ownership_data)

        assert ownership.id is not None
        assert ownership.name == "测试权属方A"
        assert ownership.code is not None  # 自动生成的编码
        assert ownership.code.startswith("OW")

    def test_create_ownership_generates_code(self):
        """测试创建权属方时自动生成编码"""
        ownership_data = OwnershipCreate(
            **self.factory.create_ownership_dict(name="权属方B")
        )

        ownership = self.service.create_ownership(self.db, obj_in=ownership_data)

        assert ownership.code is not None
        assert len(ownership.code) == 9  # OW + YYMM + NNN
        assert ownership.code.startswith("OW")

    def test_duplicate_name_raises_error(self):
        """测试创建重复名称抛出异常"""
        ownership_data = OwnershipCreate(**self.factory.create_ownership_dict())

        # 创建第一个权属方
        self.service.create_ownership(self.db, obj_in=ownership_data)

        # 尝试创建相同名称的权属方
        with pytest.raises(ValueError, match="权属方名称.*已存在"):
            self.service.create_ownership(self.db, obj_in=ownership_data)


# ============================================================================
# Test Class 2: Ownership Update
# ============================================================================


class TestOwnershipUpdate:
    """权属方更新测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session, ownership_service: OwnershipService):
        self.db = db_session
        self.service = ownership_service
        self.factory = OwnershipTestDataFactory()

        # 创建测试权属方
        self.ownership = self.service.create_ownership(
            self.db, obj_in=OwnershipCreate(**self.factory.create_ownership_dict())
        )

    def test_update_ownership_basic_fields(self):
        """测试更新权属方基本信息"""
        update_data = OwnershipUpdate(name="更新后的权属方", short_name="更新公司")

        updated = self.service.update_ownership(
            self.db, db_obj=self.ownership, obj_in=update_data
        )

        assert updated.name == "更新后的权属方"
        assert updated.short_name == "更新公司"

    def test_update_duplicate_name_raises_error(self):
        """测试更新为重复名称抛出异常"""
        # 创建第二个权属方
        self.service.create_ownership(
            self.db,
            obj_in=OwnershipCreate(
                **self.factory.create_ownership_dict(name="权属方B")
            ),
        )

        # 尝试将第一个权属方更新为与第二个权属方相同的名称
        update_data = OwnershipUpdate(name="权属方B")

        with pytest.raises(ValueError, match="权属方名称.*已存在"):
            self.service.update_ownership(
                self.db, db_obj=self.ownership, obj_in=update_data
            )


# ============================================================================
# Test Class 3: Ownership Statistics
# ============================================================================


class TestOwnershipStatistics:
    """权属方统计测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session, ownership_service: OwnershipService):
        self.db = db_session
        self.service = ownership_service
        self.factory = OwnershipTestDataFactory()

    def test_get_statistics_empty_database(self):
        """测试空数据库的统计信息"""
        stats = self.service.get_statistics(self.db)

        assert stats["total_count"] == 0
        assert stats["active_count"] == 0
        assert stats["inactive_count"] == 0
        assert len(stats["recent_created"]) == 0

    def test_get_statistics_with_ownerships(self):
        """测试有权属方时的统计信息"""
        # 创建2个权属方
        self.service.create_ownership(
            self.db,
            obj_in=OwnershipCreate(
                **self.factory.create_ownership_dict(name="权属方A")
            ),
        )
        self.service.create_ownership(
            self.db,
            obj_in=OwnershipCreate(
                **self.factory.create_ownership_dict(name="权属方B")
            ),
        )

        stats = self.service.get_statistics(self.db)

        assert stats["total_count"] == 2
        assert stats["active_count"] == 2
        assert len(stats["recent_created"]) == 2


# ============================================================================
# Test Class 4: Ownership Status Toggle
# ============================================================================


class TestOwnershipStatusToggle:
    """权属方状态切换测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session, ownership_service: OwnershipService):
        self.db = db_session
        self.service = ownership_service
        self.factory = OwnershipTestDataFactory()

    def test_toggle_status_success(self):
        """测试切换权属方状态"""
        ownership = self.service.create_ownership(
            self.db, obj_in=OwnershipCreate(**self.factory.create_ownership_dict())
        )
        initial_status = ownership.is_active

        # 切换状态
        toggled = self.service.toggle_status(self.db, id=ownership.id)

        assert toggled.is_active == (not initial_status)

    def test_toggle_nonexistent_raises_error(self):
        """测试切换不存在的权属方状态抛出异常"""
        with pytest.raises(ValueError, match="权属方ID.*不存在"):
            self.service.toggle_status(self.db, id="nonexistent-id")


# ============================================================================
# Test Class 5: Ownership Deletion
# ============================================================================


class TestOwnershipDeletion:
    """权属方删除测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session, ownership_service: OwnershipService):
        self.db = db_session
        self.service = ownership_service
        self.factory = OwnershipTestDataFactory()

    def test_delete_ownership_success(self):
        """测试成功删除权属方"""
        ownership = self.service.create_ownership(
            self.db, obj_in=OwnershipCreate(**self.factory.create_ownership_dict())
        )
        ownership_id = ownership.id

        deleted = self.service.delete_ownership(self.db, id=ownership_id)

        assert deleted.id == ownership_id

        # 验证权属方已删除
        result = self.db.query(Ownership).filter(Ownership.id == ownership_id).first()
        assert result is None

    def test_delete_with_assets_raises_error(self):
        """测试删除有资产的权属方抛出异常"""
        # 创建权属方
        ownership = self.service.create_ownership(
            self.db,
            obj_in=OwnershipCreate(
                **self.factory.create_ownership_dict(name="有权资产的权属方")
            ),
        )

        # 为权属方创建一个资产
        from src.crud.asset import asset_crud

        asset_crud.create(
            self.db,
            obj_in={
                "ownership_id": ownership.id,
                "property_name": "测试物业",
                "address": "测试地址",
                "ownership_status": "已确权",
                "property_nature": "商业",
                "usage_status": "出租中",
            },
            commit=False,
        )
        self.db.commit()

        # 尝试删除权属方
        with pytest.raises(ValueError, match="该权属方还有.*个关联资产"):
            self.service.delete_ownership(self.db, id=ownership.id)

    def test_delete_nonexistent_raises_error(self):
        """测试删除不存在的权属方抛出异常"""
        with pytest.raises(ValueError, match="权属方ID.*不存在"):
            self.service.delete_ownership(self.db, id="nonexistent-id")
