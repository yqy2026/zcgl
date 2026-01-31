"""
RentContractService 集成测试
覆盖合同创建、更新、续签、终止、台账生成、统计等功能

测试策略：
- 使用 PostgreSQL 测试数据库
- 测试真实service依赖
- 覆盖所有主要业务路径
- 包含边界条件和异常处理
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from src.constants.rent_contract_constants import PaymentStatus
from src.core.exception_handler import OperationNotAllowedError
from src.models.asset import Asset, Ownership
from src.models.rent_contract import (
    ContractType,
    DepositTransactionType,
    RentContract,
    RentContractHistory,
    RentDepositLedger,
)
from src.schemas.rent_contract import (
    GenerateLedgerRequest,
    RentContractCreate,
    RentContractUpdate,
    RentTermCreate,
    RentTermUpdate,
)
from src.services.rent_contract.service import RentContractService

# ============================================================================
# Test Data Factory
# ============================================================================


class AssetTestDataFactory:
    """资产测试数据工厂"""

    @staticmethod
    def create_asset(**kwargs):
        """创建Asset实例"""
        default_data = {
            "ownership_entity": "测试权属方",
            "property_name": "测试资产",
            "address": "测试地址",
            "ownership_status": "已确权",
            "property_nature": "商业",
            "usage_status": "空置",
        }
        default_data.update(kwargs)
        return Asset(**default_data)


class RentContractTestDataFactory:
    """租金合同测试数据工厂"""

    @staticmethod
    def create_contract_dict(**kwargs):
        """生成合同创建数据"""
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
            "contract_status": "有效",
            "asset_ids": [],
            "rent_terms": [],  # 默认为空，测试时覆盖
        }
        default_data.update(kwargs)
        return default_data

    @staticmethod
    def create_rent_term_dict(**kwargs):
        """生成租金条款数据"""
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


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def contract_service(db_session: Session):
    """RentContractService实例"""
    return RentContractService()


@pytest.fixture
def test_ownership(db_session: Session):
    """测试用权属方"""
    ownership = Ownership(
        name="测试权属方",
        code="TEST_OW_001",
        short_name="测试权属",
    )
    db_session.add(ownership)
    db_session.commit()
    db_session.refresh(ownership)
    yield ownership
    # 清理会在数据库fixture中自动处理


@pytest.fixture
def test_asset(db_session: Session, test_ownership: Ownership):
    """测试用资产"""
    asset = Asset(
        ownership_entity="权属方A",
        property_name="测试资产1",
        address="北京市朝阳区",
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    yield asset


# ============================================================================
# Test Class 1: Contract Creation
# ============================================================================


class TestContractCreation:
    """合同创建测试"""

    @pytest.fixture(autouse=True)
    def setup(
        self, db_session: Session, contract_service: RentContractService, test_ownership
    ):
        self.db = db_session
        self.service = contract_service
        self.ownership = test_ownership
        self.factory = RentContractTestDataFactory()

    def test_create_contract_success(self):
        """测试成功创建基本合同"""
        term = RentTermCreate(**self.factory.create_rent_term_dict())

        contract_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                rent_terms=[term],
            )
        )

        contract = self.service.create_contract(self.db, obj_in=contract_data)

        assert contract.id is not None
        assert contract.contract_number == contract_data.contract_number
        assert contract.owner_name == "张三"
        assert contract.contract_status == "有效"
        assert contract.ownership_id == self.ownership.id

    def test_create_contract_with_assets(self):
        """测试创建带资产的合同"""
        # 使用Asset工厂创建资产
        asset1 = AssetTestDataFactory.create_asset(
            property_name="资产1", address="地址1"
        )
        asset2 = AssetTestDataFactory.create_asset(
            property_name="资产2", address="地址2"
        )
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

        contract = self.service.create_contract(self.db, obj_in=contract_data)

        assert len(contract.assets) == 2
        asset_ids = {a.id for a in contract.assets}
        assert asset_ids == {asset1.id, asset2.id}

    def test_create_contract_with_rent_terms(self):
        """测试创建带租金条款的合同"""
        term = RentTermCreate(**self.factory.create_rent_term_dict())

        contract_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                rent_terms=[term],
            )
        )

        contract = self.service.create_contract(self.db, obj_in=contract_data)

        assert len(contract.rent_terms) == 1
        assert contract.rent_terms[0].monthly_rent == Decimal("5000.00")
        assert contract.rent_terms[0].total_monthly_amount == Decimal("5500.00")

    def test_create_contract_requires_number(self):
        """测试合同编号必填"""
        term = RentTermCreate(**self.factory.create_rent_term_dict())

        with pytest.raises(ValidationError, match="contract_number"):
            RentContractCreate(
                **self.factory.create_contract_dict(
                    ownership_id=self.ownership.id,
                    contract_number=None,
                    rent_terms=[term],
                )
            )

    def test_create_contract_calculates_total_monthly_amount(self):
        """测试自动计算月度总额"""
        term = RentTermCreate(
            **self.factory.create_rent_term_dict(
                monthly_rent=Decimal("5000.00"),
                management_fee=Decimal("500.00"),
                other_fees=Decimal("100.00"),
                total_monthly_amount=None,  # 让系统自动计算
            )
        )

        contract_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                rent_terms=[term],
            )
        )

        contract = self.service.create_contract(self.db, obj_in=contract_data)

        assert contract.rent_terms[0].total_monthly_amount == Decimal("5600.00")

    def test_create_contract_detects_asset_conflict(self):
        """测试检测资产租金冲突"""
        asset = AssetTestDataFactory.create_asset(
            property_name="冲突资产", address="地址1"
        )
        self.db.add(asset)
        self.db.commit()

        # 创建第一个合同及其租金条款
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
        self.service.create_contract(self.db, obj_in=contract1_data)

        # 尝试创建冲突的第二个合同及其租金条款
        term2 = RentTermCreate(
            **self.factory.create_rent_term_dict(
                start_date=date(2024, 6, 1),
                end_date=date(2025, 5, 31),
            )
        )

        contract2_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                asset_ids=[asset.id],
                start_date=date(2024, 6, 1),  # 时间重叠
                end_date=date(2025, 5, 31),
                rent_terms=[term2],
            )
        )

        with pytest.raises(ValueError, match="资产租金冲突"):
            self.service.create_contract(self.db, obj_in=contract2_data)

    def test_create_contract_creates_history(self):
        """测试创建合同历史记录"""
        term = RentTermCreate(**self.factory.create_rent_term_dict())

        contract_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                rent_terms=[term],
            )
        )

        contract = self.service.create_contract(self.db, obj_in=contract_data)

        history = (
            self.db.query(RentContractHistory)
            .filter(RentContractHistory.contract_id == contract.id)
            .first()
        )

        assert history is not None
        assert history.change_type == "创建"
        assert history.change_description == "创建新合同"
        assert history.new_data is not None


# ============================================================================
# Test Class 2: Contract Update
# ============================================================================


class TestContractUpdate:
    """合同更新测试"""

    @pytest.fixture(autouse=True)
    def setup(
        self, db_session: Session, contract_service: RentContractService, test_ownership
    ):
        self.db = db_session
        self.service = contract_service
        self.ownership = test_ownership
        self.factory = RentContractTestDataFactory()

        # 创建测试合同（包含rent_terms）
        term = RentTermCreate(**self.factory.create_rent_term_dict())
        self.contract_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                rent_terms=[term],
            )
        )
        self.contract = self.service.create_contract(self.db, obj_in=self.contract_data)

    def test_update_contract_basic_fields(self):
        """测试更新合同基本信息"""
        update_data = RentContractUpdate(
            tenant_name="新承租人",  # 使用tenant_name而不是owner_name
            monthly_rent_base=Decimal("6000.00"),
        )

        updated = self.service.update_contract(
            self.db, db_obj=self.contract, obj_in=update_data
        )

        # 从数据库重新查询以获取最新状态
        from src.crud.base import CRUDBase

        crud = CRUDBase(RentContract)
        updated_fresh = crud.get(self.db, id=updated.id)

        assert updated_fresh.tenant_name == "新承租人"
        assert updated_fresh.monthly_rent_base == Decimal("6000.00")

    def test_update_contract_replaces_rent_terms(self):
        """测试更新租金条款（替换模式）"""
        new_terms = [
            RentTermUpdate(
                **self.factory.create_rent_term_dict(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 6, 30),
                    monthly_rent=Decimal("6000.00"),
                )
            ),
            RentTermUpdate(
                **self.factory.create_rent_term_dict(
                    start_date=date(2024, 7, 1),
                    end_date=date(2024, 12, 31),
                    monthly_rent=Decimal("6500.00"),
                )
            ),
        ]

        update_data = RentContractUpdate(rent_terms=new_terms)
        updated = self.service.update_contract(
            self.db, db_obj=self.contract, obj_in=update_data
        )

        # 使用返回的updated对象，而不是self.contract
        assert len(updated.rent_terms) == 2
        assert updated.rent_terms[0].monthly_rent == Decimal("6000.00")

    def test_update_contract_updates_assets(self):
        """测试更新关联资产"""
        asset1 = AssetTestDataFactory.create_asset(
            property_name="新资产1", address="地址1"
        )
        asset2 = AssetTestDataFactory.create_asset(
            property_name="新资产2", address="地址2"
        )
        self.db.add_all([asset1, asset2])
        self.db.commit()

        update_data = RentContractUpdate(asset_ids=[asset1.id, asset2.id])
        updated = self.service.update_contract(
            self.db, db_obj=self.contract, obj_in=update_data
        )

        assert len(updated.assets) == 2
        asset_ids = {a.id for a in updated.assets}
        assert asset_ids == {asset1.id, asset2.id}

    def test_update_contract_creates_history(self):
        """测试更新创建历史记录"""
        update_data = RentContractUpdate(owner_name="更新后业主")
        self.service.update_contract(self.db, db_obj=self.contract, obj_in=update_data)

        history_count = (
            self.db.query(RentContractHistory)
            .filter(
                RentContractHistory.contract_id == self.contract.id,
                RentContractHistory.change_type == "更新",
            )
            .count()
        )

        assert history_count >= 1


# ============================================================================
# Test Class 3: Contract Renewal
# ============================================================================


class TestContractRenewal:
    """合同续签测试"""

    @pytest.fixture(autouse=True)
    def setup(
        self, db_session: Session, contract_service: RentContractService, test_ownership
    ):
        self.db = db_session
        self.service = contract_service
        self.ownership = test_ownership
        self.factory = RentContractTestDataFactory()

        # 创建原合同（包含rent_terms）
        term = RentTermCreate(
            **self.factory.create_rent_term_dict(
                start_date=date(2023, 1, 1),
                end_date=date(2023, 12, 31),
            )
        )
        self.original_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                total_deposit=Decimal("10000.00"),
                start_date=date(2023, 1, 1),
                end_date=date(2023, 12, 31),
                rent_terms=[term],
            )
        )
        self.original_contract = self.service.create_contract(
            self.db, obj_in=self.original_data
        )

    def test_renew_contract_success(self):
        """测试成功续签合同"""
        term = RentTermCreate(**self.factory.create_rent_term_dict())
        new_contract_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                rent_terms=[term],
            )
        )

        new_contract = self.service.renew_contract(
            self.db,
            original_contract_id=self.original_contract.id,
            new_contract_data=new_contract_data,
            operator="测试员",
        )

        assert new_contract.id != self.original_contract.id
        assert new_contract.start_date == date(2024, 1, 1)
        assert self.original_contract.contract_status == "已续签"

    def test_renew_contract_transfers_deposit(self):
        """测试续签转移押金"""
        term = RentTermCreate(**self.factory.create_rent_term_dict())
        new_contract_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                total_deposit=Decimal("0"),  # 新合同不设押金
                rent_terms=[term],
            )
        )

        new_contract = self.service.renew_contract(
            self.db,
            original_contract_id=self.original_contract.id,
            new_contract_data=new_contract_data,
            should_transfer_deposit=True,
        )

        # 检查原合同转出记录
        transfer_out = (
            self.db.query(RentDepositLedger)
            .filter(
                RentDepositLedger.contract_id == self.original_contract.id,
                RentDepositLedger.transaction_type
                == DepositTransactionType.TRANSFER_OUT,
            )
            .first()
        )

        assert transfer_out is not None
        assert transfer_out.amount == -Decimal("10000.00")
        assert transfer_out.related_contract_id == new_contract.id

        # 检查新合同转入记录
        transfer_in = (
            self.db.query(RentDepositLedger)
            .filter(
                RentDepositLedger.contract_id == new_contract.id,
                RentDepositLedger.transaction_type
                == DepositTransactionType.TRANSFER_IN,
            )
            .first()
        )

        assert transfer_in is not None
        assert transfer_in.amount == Decimal("10000.00")

    def test_renew_invalid_contract_status_raises_error(self):
        """测试续签无效状态合同抛出异常"""
        self.original_contract.contract_status = "已到期"
        self.db.add(self.original_contract)
        self.db.commit()

        term = RentTermCreate(**self.factory.create_rent_term_dict())
        new_contract_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                rent_terms=[term],
            )
        )

        with pytest.raises(OperationNotAllowedError, match="原合同状态不可续签"):
            self.service.renew_contract(
                self.db,
                original_contract_id=self.original_contract.id,
                new_contract_data=new_contract_data,
            )


# ============================================================================
# Test Class 4: Contract Termination
# ============================================================================


class TestContractTermination:
    """合同终止测试"""

    @pytest.fixture(autouse=True)
    def setup(
        self, db_session: Session, contract_service: RentContractService, test_ownership
    ):
        self.db = db_session
        self.service = contract_service
        self.ownership = test_ownership
        self.factory = RentContractTestDataFactory()

        # 创建测试合同（包含rent_terms）
        term = RentTermCreate(**self.factory.create_rent_term_dict())
        self.contract_data = RentContractCreate(
            **self.factory.create_contract_dict(
                ownership_id=self.ownership.id,
                total_deposit=Decimal("10000.00"),
                rent_terms=[term],
            )
        )
        self.contract = self.service.create_contract(self.db, obj_in=self.contract_data)

    def test_terminate_contract_success(self):
        """测试成功终止合同"""
        termination_date = date(2024, 6, 30)

        terminated = self.service.terminate_contract(
            self.db,
            contract_id=self.contract.id,
            termination_date=termination_date,
            termination_reason="租户提前退租",
            operator="管理员",
        )

        assert terminated.contract_status == "已终止"
        # end_date会被设置为termination_date（可能是date或datetime）
        if isinstance(terminated.end_date, datetime):
            assert terminated.end_date.date() == termination_date
        else:
            assert terminated.end_date == termination_date

    def test_terminate_contract_refunds_deposit(self):
        """测试终止退还押金"""
        termination_date = date(2024, 6, 30)

        self.service.terminate_contract(
            self.db,
            contract_id=self.contract.id,
            termination_date=termination_date,
            should_refund_deposit=True,
        )

        refund = (
            self.db.query(RentDepositLedger)
            .filter(
                RentDepositLedger.contract_id == self.contract.id,
                RentDepositLedger.transaction_type == DepositTransactionType.REFUND,
            )
            .first()
        )

        assert refund is not None
        assert refund.amount == -Decimal("10000.00")

    def test_terminate_with_deduction(self):
        """测试终止时抵扣押金"""
        termination_date = date(2024, 6, 30)

        self.service.terminate_contract(
            self.db,
            contract_id=self.contract.id,
            termination_date=termination_date,
            deduction_amount=Decimal("2000.00"),
            termination_reason="欠租抵扣",
        )

        # 检查抵扣记录
        deduction = (
            self.db.query(RentDepositLedger)
            .filter(
                RentDepositLedger.contract_id == self.contract.id,
                RentDepositLedger.transaction_type == DepositTransactionType.DEDUCTION,
            )
            .first()
        )

        assert deduction is not None
        assert deduction.amount == -Decimal("2000.00")

        # 检查退还记录（剩余8000）
        refund = (
            self.db.query(RentDepositLedger)
            .filter(
                RentDepositLedger.contract_id == self.contract.id,
                RentDepositLedger.transaction_type == DepositTransactionType.REFUND,
            )
            .first()
        )

        assert refund is not None
        assert refund.amount == -Decimal("8000.00")

    def test_terminate_deduction_exceeds_deposit_raises_error(self):
        """测试抵扣金额超过押金抛出异常"""
        with pytest.raises(ValueError, match="抵扣金额.*超过押金余额"):
            self.service.terminate_contract(
                self.db,
                contract_id=self.contract.id,
                termination_date=date(2024, 6, 30),
                deduction_amount=Decimal("15000.00"),  # 超过押金10000
            )


# ============================================================================
# Test Class 5: Monthly Ledger Generation
# ============================================================================


class TestMonthlyLedger:
    """月度台账生成测试"""

    @pytest.fixture(autouse=True)
    def setup(
        self, db_session: Session, contract_service: RentContractService, test_ownership
    ):
        self.db = db_session
        self.service = contract_service
        self.ownership = test_ownership

        # 创建带租金条款的合同
        term = RentTermCreate(
            **RentContractTestDataFactory.create_rent_term_dict(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                monthly_rent=Decimal("5000.00"),
                total_monthly_amount=Decimal("5500.00"),
            )
        )

        self.contract_data = RentContractCreate(
            **RentContractTestDataFactory.create_contract_dict(
                ownership_id=self.ownership.id,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                rent_terms=[term],
            )
        )
        self.contract = self.service.create_contract(self.db, obj_in=self.contract_data)

    def test_generate_monthly_ledger(self):
        """测试生成月度台账"""
        request = GenerateLedgerRequest(
            contract_id=self.contract.id,
            start_year_month="2024-01",
            end_year_month="2024-03",
        )

        ledgers = self.service.generate_monthly_ledger(self.db, request=request)

        assert len(ledgers) == 3
        assert ledgers[0].year_month == "2024-01"
        assert ledgers[0].due_amount == Decimal("5500.00")
        assert ledgers[0].payment_status == PaymentStatus.UNPAID

    def test_generate_ledger_skips_existing(self):
        """测试跳过已存在的台账"""
        request = GenerateLedgerRequest(
            contract_id=self.contract.id,
            start_year_month="2024-01",
            end_year_month="2024-01",
        )

        # 第一次生成
        ledgers1 = self.service.generate_monthly_ledger(self.db, request=request)
        assert len(ledgers1) == 1

        # 第二次生成（应该跳过）
        ledgers2 = self.service.generate_monthly_ledger(self.db, request=request)
        assert len(ledgers2) == 0

    def test_generate_ledger_uses_default_date_range(self):
        """测试使用默认日期范围"""
        request = GenerateLedgerRequest(
            contract_id=self.contract.id,
            # 不指定start_year_month和end_year_month
        )

        ledgers = self.service.generate_monthly_ledger(self.db, request=request)

        # 应该生成12个月的台账
        assert len(ledgers) == 12
        assert ledgers[0].year_month == "2024-01"
        assert ledgers[-1].year_month == "2024-12"

    def test_generate_ledger_calculates_due_date(self):
        """测试计算应缴日期"""
        request = GenerateLedgerRequest(
            contract_id=self.contract.id,
            start_year_month="2024-01",
            end_year_month="2024-01",
        )

        ledgers = self.service.generate_monthly_ledger(self.db, request=request)

        assert len(ledgers) == 1
        # 应缴日期应该是每月1号
        assert ledgers[0].due_date.day == 1
