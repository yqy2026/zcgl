from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from ...constants.rent_contract_constants import PaymentStatus
from ...core.exception_handler import BusinessValidationError, ResourceNotFoundError
from ...crud.rent_contract import rent_contract, rent_ledger, rent_term
from ...models.rent_contract import (
    RentContract,
    RentDepositLedger,
    RentLedger,
    ServiceFeeLedger,
)
from ...schemas.rent_contract import GenerateLedgerRequest, RentLedgerBatchUpdate

from .helpers import RentContractHelperMixin


class RentContractLedgerService(RentContractHelperMixin):
    """合同台账相关服务"""

    def generate_monthly_ledger(
        self, db: Session, *, request: GenerateLedgerRequest
    ) -> list[RentLedger]:
        """生成月度台账"""
        # 获取合同信息
        contract = rent_contract.get(db, id=request.contract_id)
        if not contract:
            raise ResourceNotFoundError("合同", request.contract_id)

        # 获取租金条款
        rent_terms = rent_term.get_by_contract(db, contract_id=request.contract_id)
        if not rent_terms:
            raise BusinessValidationError(
                f"合同没有租金条款: {request.contract_id}",
                field_errors={"rent_terms": ["合同没有租金条款"]},
            )

        # 确定生成月份范围
        if not request.start_year_month:
            start_year_month = contract.start_date.strftime("%Y-%m")
        else:
            start_year_month = request.start_year_month

        if not request.end_year_month:
            end_year_month = contract.end_date.strftime("%Y-%m")
        else:
            end_year_month = request.end_year_month

        # 生成月份列表
        months = self._generate_month_range(start_year_month, end_year_month)

        # 为每个月份生成台账记录
        created_ledgers = []
        for year_month in months:
            # 检查是否已存在
            existing = rent_ledger.get_by_contract_and_month(
                db, contract_id=request.contract_id, year_month=year_month
            )

            if existing:
                continue

            # 计算该月的租金
            month_date = datetime.strptime(year_month + "-01", "%Y-%m-%d").date()
            term = self._get_rent_term_for_date(rent_terms, month_date)

            if term:
                due_amount = term.total_monthly_amount or term.monthly_rent
                due_date = self._calculate_due_date(month_date, contract)

                db_ledger = RentLedger()
                db_ledger.contract_id = request.contract_id
                db_ledger.asset_id = None
                db_ledger.ownership_id = contract.ownership_id
                db_ledger.year_month = year_month
                db_ledger.due_date = due_date
                db_ledger.due_amount = due_amount
                db_ledger.paid_amount = Decimal("0")
                db_ledger.overdue_amount = Decimal("0")
                db_ledger.payment_status = PaymentStatus.UNPAID
                db.add(db_ledger)
                created_ledgers.append(db_ledger)

        db.commit()
        return created_ledgers

    def batch_update_payment(
        self, db: Session, *, request: RentLedgerBatchUpdate
    ) -> list[RentLedger]:
        """批量更新支付状态"""
        ledgers = (
            db.query(RentLedger).filter(RentLedger.id.in_(request.ledger_ids)).all()
        )

        for ledger in ledgers:
            # 更新支付信息
            if request.payment_status is not None:
                ledger.payment_status = request.payment_status
            if request.payment_date is not None:
                setattr(ledger, "payment_date", request.payment_date)
            if request.payment_method is not None:
                ledger.payment_method = request.payment_method
            if request.payment_reference is not None:
                ledger.payment_reference = request.payment_reference
            if request.notes is not None:
                ledger.notes = request.notes

            # 计算逾期金额
            if ledger.payment_status in [PaymentStatus.PAID, PaymentStatus.PARTIAL]:
                if ledger.paid_amount < ledger.due_amount:
                    ledger.overdue_amount = ledger.due_amount - ledger.paid_amount
                else:
                    ledger.overdue_amount = Decimal("0")

                # V2: 委托运营合同自动计算服务费
                self._calculate_service_fee_for_ledger(db, ledger)

        db.commit()
        return ledgers

    def get_contract_by_id(
        self, db: Session, *, contract_id: str
    ) -> RentContract | None:
        """获取合同详情"""
        return db.query(RentContract).filter(RentContract.id == contract_id).first()

    def get_deposit_ledger(
        self, db: Session, *, contract_id: str
    ) -> list[RentDepositLedger]:
        """
        获取合同押金变动记录

        Args:
            db: 数据库会话
            contract_id: 合同ID

        Returns:
            押金变动记录列表（按创建时间倒序）
        """
        return (
            db.query(RentDepositLedger)
            .filter(RentDepositLedger.contract_id == contract_id)
            .order_by(RentDepositLedger.created_at.desc())
            .all()
        )

    def get_service_fee_ledger(
        self, db: Session, *, contract_id: str
    ) -> list[ServiceFeeLedger]:
        """
        获取合同服务费台账记录

        Args:
            db: 数据库会话
            contract_id: 合同ID

        Returns:
            服务费台账记录列表（按年月倒序）
        """
        return (
            db.query(ServiceFeeLedger)
            .filter(ServiceFeeLedger.contract_id == contract_id)
            .order_by(ServiceFeeLedger.year_month.desc())
            .all()
        )
