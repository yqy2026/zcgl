"""
OwnershipService 集成测试
测试权属方的创建、更新、删除、统计等功能
"""

import pytest
from sqlalchemy.orm import Session

from src.core.exception_handler import (
    DuplicateResourceError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from src.models.asset import Asset
from src.models.ownership import Ownership
from src.schemas.ownership import OwnershipCreate, OwnershipUpdate
from src.services.ownership.service import OwnershipService

pytestmark = pytest.mark.asyncio


class AsyncSessionAdapter:
    """为同步 Session 提供异步接口，以兼容服务层。"""

    def __init__(self, session: Session):
        self._session = session

    async def execute(self, *args, **kwargs):
        return self._session.execute(*args, **kwargs)

    async def commit(self):
        return self._session.commit()

    async def refresh(self, *args, **kwargs):
        return self._session.refresh(*args, **kwargs)

    async def flush(self):
        return self._session.flush()

    async def rollback(self):
        return self._session.rollback()

    async def get(self, *args, **kwargs):
        return self._session.get(*args, **kwargs)

    async def delete(self, *args, **kwargs):
        return self._session.delete(*args, **kwargs)

    def add(self, *args, **kwargs):
        return self._session.add(*args, **kwargs)

    def __getattr__(self, name: str):
        return getattr(self._session, name)


class OwnershipTestDataFactory:
    """权属方测试数据工厂"""

    @staticmethod
    def create_ownership_dict(**kwargs):
        default_data = {
            "name": "测试权属方A",
            "short_name": "测试公司A",
        }
        default_data.update(kwargs)
        return default_data


@pytest.fixture
def ownership_service():
    return OwnershipService()


class TestOwnershipCreation:
    """权属方创建测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session, ownership_service: OwnershipService):
        self.db = db_session
        self.async_db = AsyncSessionAdapter(db_session)
        self.service = ownership_service
        self.factory = OwnershipTestDataFactory()

    async def test_create_ownership_success(self):
        ownership_data = OwnershipCreate(**self.factory.create_ownership_dict())
        ownership = await self.service.create_ownership(self.async_db, obj_in=ownership_data)
        assert ownership.id is not None
        assert ownership.name == "测试权属方A"
        assert ownership.code is not None
        assert ownership.code.startswith("OW")

    async def test_create_ownership_generates_code(self):
        ownership_data = OwnershipCreate(
            **self.factory.create_ownership_dict(name="权属方B")
        )
        ownership = await self.service.create_ownership(self.async_db, obj_in=ownership_data)
        assert ownership.code is not None
        assert len(ownership.code) == 9
        assert ownership.code.startswith("OW")

    async def test_duplicate_name_raises_error(self):
        ownership_data = OwnershipCreate(**self.factory.create_ownership_dict())
        await self.service.create_ownership(self.async_db, obj_in=ownership_data)
        with pytest.raises(DuplicateResourceError):
            await self.service.create_ownership(self.async_db, obj_in=ownership_data)


class TestOwnershipUpdate:
    """权属方更新测试"""

    @pytest.fixture(autouse=True)
    async def setup(self, db_session: Session, ownership_service: OwnershipService):
        self.db = db_session
        self.async_db = AsyncSessionAdapter(db_session)
        self.service = ownership_service
        self.factory = OwnershipTestDataFactory()
        self.ownership = await self.service.create_ownership(
            self.async_db,
            obj_in=OwnershipCreate(**self.factory.create_ownership_dict()),
        )

    async def test_update_ownership_basic_fields(self):
        update_data = OwnershipUpdate(name="更新后的权属方", short_name="更新公司")
        updated = await self.service.update_ownership(
            self.async_db, db_obj=self.ownership, obj_in=update_data
        )
        assert updated.name == "更新后的权属方"
        assert updated.short_name == "更新公司"

    async def test_update_duplicate_name_raises_error(self):
        await self.service.create_ownership(
            self.async_db,
            obj_in=OwnershipCreate(
                **self.factory.create_ownership_dict(name="权属方B")
            ),
        )
        with pytest.raises(DuplicateResourceError):
            await self.service.update_ownership(
                self.async_db,
                db_obj=self.ownership,
                obj_in=OwnershipUpdate(name="权属方B"),
            )


class TestOwnershipStatistics:
    """权属方统计测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session, ownership_service: OwnershipService):
        self.db = db_session
        self.async_db = AsyncSessionAdapter(db_session)
        self.service = ownership_service
        self.factory = OwnershipTestDataFactory()

    async def test_get_statistics_empty_database(self):
        stats = await self.service.get_statistics(self.async_db)
        assert stats["total_count"] >= 0
        assert stats["active_count"] >= 0
        assert stats["inactive_count"] >= 0
        assert stats["total_count"] == stats["active_count"] + stats["inactive_count"]
        assert len(stats["recent_created"]) <= stats["total_count"]

    async def test_get_statistics_with_ownerships(self):
        before = await self.service.get_statistics(self.async_db)
        await self.service.create_ownership(
            self.async_db,
            obj_in=OwnershipCreate(
                **self.factory.create_ownership_dict(name="权属方A")
            ),
        )
        await self.service.create_ownership(
            self.async_db,
            obj_in=OwnershipCreate(
                **self.factory.create_ownership_dict(name="权属方B")
            ),
        )
        after = await self.service.get_statistics(self.async_db)
        assert after["total_count"] == before["total_count"] + 2
        assert after["active_count"] == before["active_count"] + 2
        assert len(after["recent_created"]) >= 2


class TestOwnershipStatusToggle:
    """权属方状态切换测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session, ownership_service: OwnershipService):
        self.db = db_session
        self.async_db = AsyncSessionAdapter(db_session)
        self.service = ownership_service
        self.factory = OwnershipTestDataFactory()

    async def test_toggle_status_success(self):
        ownership = await self.service.create_ownership(
            self.async_db, obj_in=OwnershipCreate(**self.factory.create_ownership_dict())
        )
        initial_status = ownership.is_active
        toggled = await self.service.toggle_status(self.async_db, id=ownership.id)
        assert toggled.is_active is (not initial_status)

    async def test_toggle_nonexistent_raises_error(self):
        with pytest.raises(ResourceNotFoundError):
            await self.service.toggle_status(self.async_db, id="nonexistent-id")


class TestOwnershipDeletion:
    """权属方删除测试"""

    @pytest.fixture(autouse=True)
    def setup(self, db_session: Session, ownership_service: OwnershipService):
        self.db = db_session
        self.async_db = AsyncSessionAdapter(db_session)
        self.service = ownership_service
        self.factory = OwnershipTestDataFactory()

    async def test_delete_ownership_success(self):
        ownership = await self.service.create_ownership(
            self.async_db, obj_in=OwnershipCreate(**self.factory.create_ownership_dict())
        )
        ownership_id = ownership.id
        deleted = await self.service.delete_ownership(self.async_db, id=ownership_id)
        assert deleted.id == ownership_id
        result = self.db.query(Ownership).filter(Ownership.id == ownership_id).first()
        assert result is None

    async def test_delete_with_assets_raises_error(self):
        ownership = await self.service.create_ownership(
            self.async_db,
            obj_in=OwnershipCreate(
                **self.factory.create_ownership_dict(name="有权资产的权属方")
            ),
        )
        self.db.add(
            Asset(
                ownership_id=ownership.id,
                property_name="测试物业-ownership-delete-check",
                address="测试地址",
                ownership_status="已确权",
                property_nature="经营类",
                usage_status="出租",
            )
        )
        self.db.commit()

        with pytest.raises(OperationNotAllowedError):
            await self.service.delete_ownership(self.async_db, id=ownership.id)

    async def test_delete_nonexistent_raises_error(self):
        with pytest.raises(ResourceNotFoundError):
            await self.service.delete_ownership(self.async_db, id="nonexistent-id")
