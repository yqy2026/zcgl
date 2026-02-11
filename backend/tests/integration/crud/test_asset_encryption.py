"""
资产加密集成测试（异步）

覆盖当前模型中仍存在且需要加密的字段：
- address（可搜索）
- manager_name（不可搜索）
"""

import base64
import uuid

import pytest
from sqlalchemy.orm import Session

from src.crud.asset import AssetCRUD
from src.models.asset import Asset
from src.models.ownership import Ownership
from src.schemas.asset import AssetUpdate
from tests.integration.conftest import AsyncSessionAdapter

pytestmark = pytest.mark.asyncio


@pytest.fixture
def valid_encryption_key() -> str:
    key_bytes = b"f" * 32
    key_b64 = base64.b64encode(key_bytes).decode("ascii")
    return f"{key_b64}:1"


@pytest.fixture
def asset_crud_with_encryption(
    valid_encryption_key: str, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", valid_encryption_key)

    import sys

    modules_to_clear = [
        "src.core.config",
        "src.core.encryption",
        "src.crud.asset",
    ]
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]

    from src.crud.asset import AssetCRUD

    yield AssetCRUD()

    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]


@pytest.fixture
def asset_crud_no_encryption(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DATA_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", "")
    monkeypatch.setenv("REQUIRE_ENCRYPTION", "false")

    import sys

    modules_to_clear = [
        "src.core.config",
        "src.core.encryption",
        "src.crud.asset",
    ]
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]

    from src.crud.asset import AssetCRUD

    yield AssetCRUD()

    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]


@pytest.fixture
def async_db_session(db_session: Session) -> AsyncSessionAdapter:
    return AsyncSessionAdapter(db_session)


@pytest.fixture
def sample_asset_data(db_session: Session) -> dict:
    suffix = uuid.uuid4().hex[:8]
    ownership = Ownership(name=f"加密测试权属方-{suffix}", code=f"OWN-ENC-{suffix}")
    db_session.add(ownership)
    db_session.flush()

    return {
        "property_name": f"测试物业-{suffix}",
        "ownership_id": ownership.id,
        "address": "北京市朝阳区某某街道123号",
        "manager_name": "王经理",
        "business_category": "商业",
        "actual_property_area": 100.5,
        "ownership_status": "已确权",
        "property_nature": "商业",
        "usage_status": "在用",
        "is_litigated": False,
        "data_status": "正常",
    }


@pytest.mark.usefixtures("db_tables")
class TestAssetCRUDEncryption:
    async def test_create_encrypts_pii_fields(
        self,
        db_session: Session,
        async_db_session: AsyncSessionAdapter,
        asset_crud_with_encryption: AssetCRUD,
        sample_asset_data: dict,
    ):
        created = await asset_crud_with_encryption.create_async(
            db=async_db_session,
            obj_in=sample_asset_data,
        )

        db_asset = db_session.query(Asset).filter(Asset.id == created.id).first()
        assert db_asset is not None
        assert db_asset.address.startswith("enc:v1:")
        assert db_asset.manager_name.startswith("enc:v1:")
        assert db_asset.property_name == sample_asset_data["property_name"]

    async def test_get_decrypts_pii_fields(
        self,
        async_db_session: AsyncSessionAdapter,
        asset_crud_with_encryption: AssetCRUD,
        sample_asset_data: dict,
    ):
        created = await asset_crud_with_encryption.create_async(
            db=async_db_session,
            obj_in=sample_asset_data,
        )

        asset = await asset_crud_with_encryption.get_async(
            db=async_db_session,
            id=created.id,
        )

        assert asset is not None
        assert asset.address == sample_asset_data["address"]
        assert asset.manager_name == sample_asset_data["manager_name"]

    async def test_update_encrypts_new_pii_values(
        self,
        db_session: Session,
        async_db_session: AsyncSessionAdapter,
        asset_crud_with_encryption: AssetCRUD,
        sample_asset_data: dict,
    ):
        created = await asset_crud_with_encryption.create_async(
            db=async_db_session,
            obj_in=sample_asset_data,
        )

        update_data = AssetUpdate(address="新地址", manager_name="新经理")
        updated = await asset_crud_with_encryption.update_async(
            db=async_db_session,
            db_obj=created,
            obj_in=update_data,
        )

        db_asset = db_session.query(Asset).filter(Asset.id == updated.id).first()
        assert db_asset is not None
        assert db_asset.address.startswith("enc:v1:")
        assert db_asset.manager_name.startswith("enc:v1:")

        asset = await asset_crud_with_encryption.get_async(
            db=async_db_session,
            id=updated.id,
        )
        assert asset is not None
        assert asset.address == "新地址"
        assert asset.manager_name == "新经理"


@pytest.mark.usefixtures("db_tables")
class TestSearchEncryptedFields:
    async def test_search_on_encrypted_address(
        self,
        async_db_session: AsyncSessionAdapter,
        asset_crud_with_encryption: AssetCRUD,
        sample_asset_data: dict,
    ):
        data1 = sample_asset_data.copy()
        data1["property_name"] = f"SearchTarget-{uuid.uuid4().hex[:6]}"
        data1["address"] = "Test Address 123"
        await asset_crud_with_encryption.create_async(db=async_db_session, obj_in=data1)

        data2 = sample_asset_data.copy()
        data2["property_name"] = f"SearchOther-{uuid.uuid4().hex[:6]}"
        data2["address"] = "Other Address"
        await asset_crud_with_encryption.create_async(db=async_db_session, obj_in=data2)

        assets, total = await asset_crud_with_encryption.get_multi_with_search_async(
            db=async_db_session,
            search="Test Address 123",
            skip=0,
            limit=20,
        )

        assert total >= 1
        assert any(asset.property_name == data1["property_name"] for asset in assets)


@pytest.mark.usefixtures("db_tables")
class TestGracefulDegradation:
    async def test_create_without_key_stores_plaintext(
        self,
        db_session: Session,
        async_db_session: AsyncSessionAdapter,
        asset_crud_no_encryption: AssetCRUD,
        sample_asset_data: dict,
    ):
        created = await asset_crud_no_encryption.create_async(
            db=async_db_session,
            obj_in=sample_asset_data,
        )

        db_asset = db_session.query(Asset).filter(Asset.id == created.id).first()
        assert db_asset is not None
        assert db_asset.address == sample_asset_data["address"]
        assert db_asset.manager_name == sample_asset_data["manager_name"]

    async def test_mixed_encrypted_plaintext_data(
        self,
        async_db_session: AsyncSessionAdapter,
        asset_crud_with_encryption: AssetCRUD,
        asset_crud_no_encryption: AssetCRUD,
        sample_asset_data: dict,
    ):
        old_data = sample_asset_data.copy()
        old_data["property_name"] = f"MixedOld-{uuid.uuid4().hex[:6]}"
        await asset_crud_no_encryption.create_async(
            db=async_db_session, obj_in=old_data
        )

        new_data = sample_asset_data.copy()
        new_data["property_name"] = f"MixedNew-{uuid.uuid4().hex[:6]}"
        await asset_crud_with_encryption.create_async(
            db=async_db_session, obj_in=new_data
        )

        assets, total = await asset_crud_with_encryption.get_multi_with_search_async(
            db=async_db_session,
            skip=0,
            limit=50,
        )

        assert total >= 2
        by_name = {asset.property_name: asset for asset in assets}
        assert by_name[old_data["property_name"]].address == old_data["address"]
        assert by_name[new_data["property_name"]].address == new_data["address"]
