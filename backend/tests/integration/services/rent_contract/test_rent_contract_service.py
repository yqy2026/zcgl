"""
RentContractService 集成测试
覆盖合同创建、更新与台账生成等核心能力。
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants.rent_contract_constants import PaymentStatus
from src.core.enums import ContractStatus
from src.core.exception_handler import BusinessValidationError, ResourceConflictError
from src.models.asset import Asset
from src.models.associations import rent_contract_assets
from src.models.ownership import Ownership
from src.models.rent_contract import RentContractHistory, RentTerm
from src.schemas.rent_contract import (
    ContractType,
    GenerateLedgerRequest,
    RentContractCreate,
    RentContractUpdate,
    RentTermCreate,
    RentTermUpdate,
)
from src.services.rent_contract.service import RentContractService

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


class AssetTestDataFactory:
    """资产测试数据工厂"""

    @staticmethod
    def create_asset(**kwargs):
        default_data = {
            "property_name": f"测试资产-{uuid4().hex[:8]}",
            "address": "北京市朝阳区测试路",
            "ownership_status": "已确权",
            "property_nature": "经营类",
            "usage_status": "出租",
        }
        default_data.update(kwargs)
        return Asset(**default_data)


class RentContractTestDataFactory:
    """租金合同测试数据工厂"""

    @staticmethod
    def create_contract_dict(**kwargs):
        default_data = {
            "contract_number": f"CT{uuid4().hex[:10].upper()}",
            "owner_name": "张三",
            "owner_phone": "13800138000",
            "tenant_name": "李四",
            "tenant_phone": "13900139000",
            "contract_type": ContractType.LEASE_DOWNSTREAM,
            "sign_date": date(2023, 12, 31),
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 12, 31),
            "monthly_rent_base": Decimal("5000.00"),
            "total_deposit": Decimal("10000.00"),
            "contract_status": ContractStatus.ACTIVE,
            "asset_ids": [],
            "rent_terms": [],
        }
        default_data.update(kwargs)
        return default_data

    @staticmethod
    def create_rent_term_dict(**kwargs):
        default_data = {
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 12, 31),
            "monthly_rent": Decimal("5000.00"),
            "management_fee": Decimal("500.00"),
            "other_fees": Decimal("0"),
            "total_monthly_amount": Decimal("5500.00"),
        }
        default_data.update(kwargs)
        return default_data


@pytest.fixture
def contract_service():
    return RentContractService()


@pytest.fixture
def test_ownership(db_session: Session):
    ownership = Ownership(
        name="测试权属方",
        code=f"OW{uuid4().hex[:7].upper()}",
        short_name="测试权属",
    )
    db_session.add(ownership)
    db_session.commit()
    db_session.refresh(ownership)
    return ownership


class TestContractCreation:
    """合同创建测试"""

    @pytest.fixture(autouse=True)
    def setup(
        self, db_session: Session, contract_service: RentContractService, test_ownership
    ):
        self.db = db_session
        self.async_db = AsyncSessionAdapter(db_session)
        self.service = contract_service
        self.ownership = test_ownership
        self.factory = RentContractTestDataFactory()

    async def test_create_contract_success(self):
        term = RentTermCreate(**self.factory.create_rent_term_dict())
        contract_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                rent_terms=[term],
            )
        )

        contract = await self.service.create_contract_async(self.async_db, obj_in=contract_data)
        assert contract.id is not None
        assert contract.ownership_id == self.ownership.id
        assert contract.contract_status == ContractStatus.ACTIVE.value

        terms = self.db.query(RentTerm).filter(RentTerm.contract_id == contract.id).all()
        assert len(terms) == 1
        assert terms[0].total_monthly_amount == Decimal("5500.00")

    async def test_create_contract_with_assets(self):
        asset1 = AssetTestDataFactory.create_asset(ownership_id=self.ownership.id)
        asset2 = AssetTestDataFactory.create_asset(ownership_id=self.ownership.id)
        self.db.add_all([asset1, asset2])
        self.db.commit()

        term = RentTermCreate(**self.factory.create_rent_term_dict())
        contract_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                asset_ids=[asset1.id, asset2.id],
                rent_terms=[term],
            )
        )
        contract = await self.service.create_contract_async(self.async_db, obj_in=contract_data)

        rows = self.db.execute(
            select(rent_contract_assets.c.asset_id).where(
                rent_contract_assets.c.contract_id == contract.id
            )
        ).all()
        assert {row[0] for row in rows} == {asset1.id, asset2.id}

    async def test_create_contract_calculates_total_monthly_amount(self):
        term = RentTermCreate(
            **self.factory.create_rent_term_dict(
                monthly_rent=Decimal("5000.00"),
                management_fee=Decimal("500.00"),
                other_fees=Decimal("100.00"),
                total_monthly_amount=None,
            )
        )
        contract_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                rent_terms=[term],
            )
        )

        contract = await self.service.create_contract_async(self.async_db, obj_in=contract_data)
        created_term = (
            self.db.query(RentTerm).filter(RentTerm.contract_id == contract.id).first()
        )
        assert created_term is not None
        assert created_term.total_monthly_amount == Decimal("5600.00")

    async def test_create_contract_requires_number(self):
        term = RentTermCreate(**self.factory.create_rent_term_dict())
        contract_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                contract_number=None,
                rent_terms=[term],
            )
        )

        with pytest.raises(BusinessValidationError):
            await self.service.create_contract_async(self.async_db, obj_in=contract_data)

    async def test_create_contract_detects_asset_conflict(self):
        asset = AssetTestDataFactory.create_asset(ownership_id=self.ownership.id)
        self.db.add(asset)
        self.db.commit()

        term1 = RentTermCreate(
            **self.factory.create_rent_term_dict(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
            )
        )
        contract1_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                asset_ids=[asset.id],
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                rent_terms=[term1],
            )
        )
        await self.service.create_contract_async(self.async_db, obj_in=contract1_data)

        term2 = RentTermCreate(
            **self.factory.create_rent_term_dict(
                start_date=date(2024, 6, 1),
                end_date=date(2025, 5, 31),
                total_monthly_amount=Decimal("5000.00"),
            )
        )
        contract2_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                asset_ids=[asset.id],
                start_date=date(2024, 6, 1),
                end_date=date(2025, 5, 31),
                rent_terms=[term2],
            )
        )

        with pytest.raises(ResourceConflictError):
            await self.service.create_contract_async(self.async_db, obj_in=contract2_data)

    async def test_create_contract_creates_history(self):
        term = RentTermCreate(**self.factory.create_rent_term_dict())
        contract_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                rent_terms=[term],
            )
        )
        contract = await self.service.create_contract_async(self.async_db, obj_in=contract_data)

        history = (
            self.db.query(RentContractHistory)
            .filter(RentContractHistory.contract_id == contract.id)
            .first()
        )
        assert history is not None
        assert history.change_type == "创建"
        assert history.change_description == "创建新合同"


class TestContractUpdate:
    """合同更新测试"""

    @pytest.fixture(autouse=True)
    async def setup(
        self, db_session: Session, contract_service: RentContractService, test_ownership
    ):
        self.db = db_session
        self.async_db = AsyncSessionAdapter(db_session)
        self.service = contract_service
        self.ownership = test_ownership
        self.factory = RentContractTestDataFactory()

        term = RentTermCreate(**self.factory.create_rent_term_dict())
        self.contract_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                rent_terms=[term],
            )
        )
        self.contract = await self.service.create_contract_async(
            self.async_db, obj_in=self.contract_data
        )

    async def test_update_contract_basic_fields(self):
        update_data = RentContractUpdate(
            tenant_name="新承租人",
            monthly_rent_base=Decimal("6000.00"),
        )
        updated = await self.service.update_contract_async(
            self.async_db,
            db_obj=self.contract,
            obj_in=update_data,
        )
        assert updated.tenant_name == "新承租人"
        assert updated.monthly_rent_base == Decimal("6000.00")

    async def test_update_contract_replaces_rent_terms(self):
        new_terms = [
            RentTermUpdate(
                **self.factory.create_rent_term_dict(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 6, 30),
                    monthly_rent=Decimal("6000.00"),
                    total_monthly_amount=Decimal("6500.00"),
                )
            ),
            RentTermUpdate(
                **self.factory.create_rent_term_dict(
                    start_date=date(2024, 7, 1),
                    end_date=date(2024, 12, 31),
                    monthly_rent=Decimal("6500.00"),
                    total_monthly_amount=Decimal("7000.00"),
                )
            ),
        ]

        await self.service.update_contract_async(
            self.async_db,
            db_obj=self.contract,
            obj_in=RentContractUpdate(rent_terms=new_terms),
        )

        terms = self.db.query(RentTerm).filter(RentTerm.contract_id == self.contract.id).all()
        assert len(terms) == 2
        assert {term.monthly_rent for term in terms} == {
            Decimal("6000.00"),
            Decimal("6500.00"),
        }

    async def test_update_contract_updates_assets(self):
        asset1 = AssetTestDataFactory.create_asset(ownership_id=self.ownership.id)
        asset2 = AssetTestDataFactory.create_asset(ownership_id=self.ownership.id)
        self.db.add_all([asset1, asset2])
        self.db.commit()

        await self.service.update_contract_async(
            self.async_db,
            db_obj=self.contract,
            obj_in=RentContractUpdate(asset_ids=[asset1.id, asset2.id]),
        )

        rows = self.db.execute(
            select(rent_contract_assets.c.asset_id).where(
                rent_contract_assets.c.contract_id == self.contract.id
            )
        ).all()
        assert {row[0] for row in rows} == {asset1.id, asset2.id}

    async def test_update_contract_creates_history(self):
        await self.service.update_contract_async(
            self.async_db,
            db_obj=self.contract,
            obj_in=RentContractUpdate(owner_name="更新后业主"),
        )

        history_count = (
            self.db.query(RentContractHistory)
            .filter(
                RentContractHistory.contract_id == self.contract.id,
                RentContractHistory.change_type == "更新",
            )
            .count()
        )
        assert history_count >= 1


class TestMonthlyLedger:
    """月度台账生成测试"""

    @pytest.fixture(autouse=True)
    async def setup(
        self, db_session: Session, contract_service: RentContractService, test_ownership
    ):
        self.db = db_session
        self.async_db = AsyncSessionAdapter(db_session)
        self.service = contract_service
        self.ownership = test_ownership
        self.factory = RentContractTestDataFactory()

        term = RentTermCreate(
            **self.factory.create_rent_term_dict(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                monthly_rent=Decimal("5000.00"),
                total_monthly_amount=Decimal("5500.00"),
            )
        )
        contract_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                rent_terms=[term],
            )
        )
        self.contract = await self.service.create_contract_async(
            self.async_db, obj_in=contract_data
        )

    async def test_generate_monthly_ledger(self):
        request = GenerateLedgerRequest(
            contract_id=self.contract.id,
            start_year_month="2024-01",
            end_year_month="2024-03",
        )
        ledgers = await self.service.generate_monthly_ledger_async(
            self.async_db, request=request
        )

        assert len(ledgers) == 3
        assert ledgers[0].year_month == "2024-01"
        assert ledgers[0].due_amount == Decimal("5500.00")
        assert ledgers[0].payment_status == PaymentStatus.UNPAID

    async def test_generate_ledger_skips_existing(self):
        request = GenerateLedgerRequest(
            contract_id=self.contract.id,
            start_year_month="2024-01",
            end_year_month="2024-01",
        )
        first = await self.service.generate_monthly_ledger_async(
            self.async_db, request=request
        )
        second = await self.service.generate_monthly_ledger_async(
            self.async_db, request=request
        )

        assert len(first) == 1
        assert len(second) == 0

    async def test_generate_ledger_uses_default_date_range(self):
        request = GenerateLedgerRequest(contract_id=self.contract.id)
        ledgers = await self.service.generate_monthly_ledger_async(
            self.async_db, request=request
        )

        assert len(ledgers) == 12
        assert ledgers[0].year_month == "2024-01"
        assert ledgers[-1].year_month == "2024-12"

    async def test_generate_ledger_calculates_due_date(self):
        request = GenerateLedgerRequest(
            contract_id=self.contract.id,
            start_year_month="2024-01",
            end_year_month="2024-01",
        )
        ledgers = await self.service.generate_monthly_ledger_async(
            self.async_db, request=request
        )

        assert len(ledgers) == 1
        assert ledgers[0].due_date.day == 1
