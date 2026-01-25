"""
SystemDictionaryService 集成测试
测试系统字典的创建、更新、删除、排序等功能
"""

import pytest
from sqlalchemy.orm import Session

from src.models.asset import SystemDictionary
from src.schemas.asset import SystemDictionaryCreate, SystemDictionaryUpdate
from src.services.system_dictionary.service import system_dictionary_service

# ============================================================================
# Test Data Factory
# ============================================================================


class SystemDictionaryTestDataFactory:
    """系统字典测试数据工厂"""

    @staticmethod
    def create_dictionary_dict(**kwargs):
        """生成字典创建数据"""
        default_data = {
            "dict_type": "ownership_status",
            "dict_code": "owned",
            "dict_label": "已确权",
            "dict_value": "1",
            "sort_order": 1,
            "is_active": True,
        }
        default_data.update(kwargs)
        return default_data


# ============================================================================
# Test Class 1: Dictionary Creation
# ============================================================================


class TestDictionaryCreation:
    """字典创建测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        self.db = db_session
        self.service = system_dictionary_service
        self.factory = SystemDictionaryTestDataFactory()

    def test_create_dictionary_success(self):
        """测试成功创建字典项"""
        dictionary_data = SystemDictionaryCreate(
            **self.factory.create_dictionary_dict()
        )

        dictionary = self.service.create_dictionary(self.db, obj_in=dictionary_data)

        assert dictionary.id is not None
        assert dictionary.dict_type == "ownership_status"
        assert dictionary.dict_code == "owned"
        assert dictionary.dict_label == "已确权"

    def test_create_duplicate_code_raises_error(self):
        """测试创建重复字典代码抛出异常"""
        dictionary_data = SystemDictionaryCreate(
            **self.factory.create_dictionary_dict()
        )

        # 创建第一个字典项
        self.service.create_dictionary(self.db, obj_in=dictionary_data)

        # 尝试创建相同类型和代码的字典项
        with pytest.raises(ValueError, match="字典代码.*已存在"):
            self.service.create_dictionary(self.db, obj_in=dictionary_data)


# ============================================================================
# Test Class 2: Dictionary Update
# ============================================================================


class TestDictionaryUpdate:
    """字典更新测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        self.db = db_session
        self.service = system_dictionary_service
        self.factory = SystemDictionaryTestDataFactory()

        # 创建测试字典项
        self.dictionary = self.service.create_dictionary(
            self.db,
            obj_in=SystemDictionaryCreate(**self.factory.create_dictionary_dict()),
        )

    def test_update_dictionary_basic_fields(self):
        """测试更新字典项基本信息"""
        update_data = SystemDictionaryUpdate(
            dict_label="更新后的标签", dict_value="2", is_active=False
        )

        updated = self.service.update_dictionary(
            self.db, id=self.dictionary.id, obj_in=update_data
        )

        assert updated.dict_label == "更新后的标签"
        assert updated.dict_value == "2"
        assert updated.is_active is False

    def test_update_nonexistent_dictionary_raises_error(self):
        """测试更新不存在的字典项抛出异常"""
        with pytest.raises(ValueError, match="字典项不存在"):
            self.service.update_dictionary(
                self.db,
                id="nonexistent-id",
                obj_in=SystemDictionaryUpdate(dict_label="新标签"),
            )


# ============================================================================
# Test Class 3: Dictionary Deletion
# ============================================================================


class TestDictionaryDeletion:
    """字典删除测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        self.db = db_session
        self.service = system_dictionary_service
        self.factory = SystemDictionaryTestDataFactory()

    def test_delete_dictionary_success(self):
        """测试成功删除字典项"""
        dictionary = self.service.create_dictionary(
            self.db,
            obj_in=SystemDictionaryCreate(**self.factory.create_dictionary_dict()),
        )
        dictionary_id = dictionary.id

        deleted = self.service.delete_dictionary(self.db, id=dictionary_id)

        assert deleted.id == dictionary_id

        # 验证字典项已删除
        result = (
            self.db.query(SystemDictionary)
            .filter(SystemDictionary.id == dictionary_id)
            .first()
        )
        assert result is None

    def test_delete_nonexistent_dictionary_raises_error(self):
        """测试删除不存在的字典项抛出异常"""
        with pytest.raises(ValueError, match="字典项不存在"):
            self.service.delete_dictionary(self.db, id="nonexistent-id")


# ============================================================================
# Test Class 4: Dictionary Status Toggle
# ============================================================================


class TestDictionaryStatusToggle:
    """字典状态切换测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        self.db = db_session
        self.service = system_dictionary_service
        self.factory = SystemDictionaryTestDataFactory()

    def test_toggle_active_status_success(self):
        """测试切换字典项启用状态"""
        dictionary = self.service.create_dictionary(
            self.db,
            obj_in=SystemDictionaryCreate(
                **self.factory.create_dictionary_dict(is_active=True)
            ),
        )
        initial_status = dictionary.is_active

        # 切换状态
        toggled = self.service.toggle_active_status(self.db, id=dictionary.id)

        assert toggled.is_active == (not initial_status)

    def test_toggle_nonexistent_dictionary_raises_error(self):
        """测试切换不存在的字典项状态抛出异常"""
        with pytest.raises(ValueError, match="字典项不存在"):
            self.service.toggle_active_status(self.db, id="nonexistent-id")


# ============================================================================
# Test Class 5: Sort Order Update
# ============================================================================


class TestSortOrderUpdate:
    """排序更新测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session):
        self.db = db_session
        self.service = system_dictionary_service
        self.factory = SystemDictionaryTestDataFactory()

        # 创建多个字典项
        self.dict1 = self.service.create_dictionary(
            self.db,
            obj_in=SystemDictionaryCreate(
                **self.factory.create_dictionary_dict(
                    dict_code="owned", dict_label="已确权", sort_order=1
                )
            ),
        )
        self.dict2 = self.service.create_dictionary(
            self.db,
            obj_in=SystemDictionaryCreate(
                **self.factory.create_dictionary_dict(
                    dict_code="pending", dict_label="确权中", sort_order=2
                )
            ),
        )
        self.dict3 = self.service.create_dictionary(
            self.db,
            obj_in=SystemDictionaryCreate(
                **self.factory.create_dictionary_dict(
                    dict_code="unowned", dict_label="未确权", sort_order=3
                )
            ),
        )

    def test_update_sort_orders_success(self):
        """测试批量更新排序"""
        sort_data = [
            {"id": self.dict1.id, "sort_order": 3},
            {"id": self.dict2.id, "sort_order": 1},
            {"id": self.dict3.id, "sort_order": 2},
        ]

        updated = self.service.update_sort_orders(
            self.db, dict_type="ownership_status", sort_data=sort_data
        )

        assert len(updated) == 3
        # 验证排序已更新（需要从数据库重新查询）
        self.db.refresh(self.dict1)
        self.db.refresh(self.dict2)
        self.db.refresh(self.dict3)
        assert self.dict1.sort_order == 3
        assert self.dict2.sort_order == 1
        assert self.dict3.sort_order == 2

    def test_update_sort_orders_ignores_wrong_type(self):
        """测试更新排序时忽略不同类型的字典项"""
        # 创建不同类型的字典项
        other_type_dict = self.service.create_dictionary(
            self.db,
            obj_in=SystemDictionaryCreate(
                **self.factory.create_dictionary_dict(
                    dict_type="property_type",
                    dict_code="commercial",
                    dict_label="商业",
                    sort_order=10,
                )
            ),
        )

        sort_data = [
            {"id": self.dict1.id, "sort_order": 5},
            {"id": other_type_dict.id, "sort_order": 20},  # 不同类型，应该被忽略
        ]

        updated = self.service.update_sort_orders(
            self.db, dict_type="ownership_status", sort_data=sort_data
        )

        # 只有同类型的项被更新
        assert len(updated) == 1
        assert updated[0].id == self.dict1.id
