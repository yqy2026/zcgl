from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from ...crud.rent_contract import rent_contract, rent_ledger, rent_term
from ...models.asset import Asset, Ownership
from ...models.rent_contract import (
    RentContract,
    RentContractHistory,
    RentLedger,
    RentTerm,
)
from ...schemas.rent_contract import (
    GenerateLedgerRequest,
    RentContractCreate,
    RentContractUpdate,
    RentLedgerBatchUpdate,
    RentStatisticsQuery,
)
from ...utils.model_utils import model_to_dict


class RentContractService:
    """租金合同业务服务"""

    def create_contract(self, db: Session, *, obj_in: RentContractCreate) -> RentContract:
        """创建合同（包含租金条款）"""
        # 生成合同编号
        if not obj_in.contract_number:
            obj_in.contract_number = self._generate_contract_number(db)

        # 创建合同数据
        contract_data = obj_in.model_dump(exclude={"rent_terms"})
        db_contract = RentContract(**contract_data)
        db.add(db_contract)
        db.flush()  # 获取ID

        # 创建租金条款
        for term_data in obj_in.rent_terms:
            term_data_dict = term_data.model_dump()
            # 确保 total_monthly_amount 被正确计算
            if term_data_dict.get("total_monthly_amount") is None:
                monthly_rent = term_data_dict.get("monthly_rent", Decimal("0"))
                management_fee = term_data_dict.get("management_fee", Decimal("0"))
                other_fees = term_data_dict.get("other_fees", Decimal("0"))
                term_data_dict["total_monthly_amount"] = monthly_rent + management_fee + other_fees

            term_data_dict["contract_id"] = db_contract.id
            db_term = RentTerm(**term_data_dict)
            db.add(db_term)

        db.commit()
        db.refresh(db_contract)

        # 记录历史
        self._create_history(
            db,
            contract_id=db_contract.id,
            change_type="创建",
            change_description="创建新合同",
            new_data=model_to_dict(db_contract),
        )

        return db_contract

    def update_contract(
        self, db: Session, *, db_obj: RentContract, obj_in: RentContractUpdate
    ) -> RentContract:
        """更新合同（包含租金条款）"""
        old_data = model_to_dict(db_obj)

        # 更新合同基本信息
        update_data = obj_in.model_dump(exclude_unset=True, exclude={"rent_terms"})
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        # 更新租金条款
        if obj_in.rent_terms is not None:
            # 删除现有条款
            db.query(RentTerm).filter(RentTerm.contract_id == db_obj.id).delete()

            # 创建新条款
            for term_data in obj_in.rent_terms:
                term_data_dict = term_data.model_dump()
                term_data_dict["contract_id"] = db_obj.id
                db_term = RentTerm(**term_data_dict)
                db.add(db_term)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        # 记录历史
        self._create_history(
            db,
            contract_id=db_obj.id,
            change_type="更新",
            change_description="更新合同信息",
            old_data=old_data,
            new_data=model_to_dict(db_obj),
        )

        return db_obj

    def generate_monthly_ledger(
        self, db: Session, *, request: GenerateLedgerRequest
    ) -> list[RentLedger]:
        """生成月度台账"""
        # 获取合同信息
        contract = rent_contract.get(db, id=request.contract_id)
        if not contract:
            raise ValueError(f"合同不存在: {request.contract_id}")

        # 获取租金条款
        rent_terms = rent_term.get_by_contract(db, contract_id=request.contract_id)
        if not rent_terms:
            raise ValueError(f"合同没有租金条款: {request.contract_id}")

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

                ledger_data = {
                    "contract_id": request.contract_id,
                    "asset_id": contract.asset_id,
                    "ownership_id": contract.ownership_id,
                    "year_month": year_month,
                    "due_date": due_date,
                    "due_amount": due_amount,
                    "paid_amount": Decimal("0"),
                    "overdue_amount": Decimal("0"),
                    "payment_status": "未支付",
                }

                db_ledger = RentLedger(**ledger_data)
                db.add(db_ledger)
                created_ledgers.append(db_ledger)

        db.commit()
        return created_ledgers

    def batch_update_payment(
        self, db: Session, *, request: RentLedgerBatchUpdate
    ) -> list[RentLedger]:
        """批量更新支付状态"""
        ledgers = db.query(RentLedger).filter(RentLedger.id.in_(request.ledger_ids)).all()

        for ledger in ledgers:
            # 更新支付信息
            if request.payment_status is not None:
                ledger.payment_status = request.payment_status
            if request.payment_date is not None:
                ledger.payment_date = request.payment_date
            if request.payment_method is not None:
                ledger.payment_method = request.payment_method
            if request.payment_reference is not None:
                ledger.payment_reference = request.payment_reference
            if request.notes is not None:
                ledger.notes = request.notes

            # 计算逾期金额
            if ledger.payment_status in ["已支付", "部分支付"]:
                if ledger.paid_amount < ledger.due_amount:
                    ledger.overdue_amount = ledger.due_amount - ledger.paid_amount
                else:
                    ledger.overdue_amount = Decimal("0")

        db.commit()
        return ledgers

    # 统计相关方法
    def get_statistics(self, db: Session, *, query_params: RentStatisticsQuery) -> dict[str, Any]:
        """获取统计信息"""
        # 构建基础查询
        base_query = db.query(RentLedger)

        # 应用筛选条件
        if query_params.start_date:
            base_query = base_query.filter(RentLedger.due_date >= query_params.start_date)
        if query_params.end_date:
            base_query = base_query.filter(RentLedger.due_date <= query_params.end_date)
        if query_params.ownership_ids:
            base_query = base_query.filter(RentLedger.ownership_id.in_(query_params.ownership_ids))
        if query_params.asset_ids:
            base_query = base_query.filter(RentLedger.asset_id.in_(query_params.asset_ids))

        # 基础统计
        stats = base_query.with_entities(
            func.sum(RentLedger.due_amount).label("total_due"),
            func.sum(RentLedger.paid_amount).label("total_paid"),
            func.sum(RentLedger.overdue_amount).label("total_overdue"),
            func.count(RentLedger.id).label("total_records"),
        ).first()

        # 按状态统计
        status_stats = (
            base_query.with_entities(
                RentLedger.payment_status,
                func.count(RentLedger.id).label("count"),
                func.sum(RentLedger.due_amount).label("due_amount"),
                func.sum(RentLedger.paid_amount).label("paid_amount"),
            )
            .group_by(RentLedger.payment_status)
            .all()
        )

        # 按月份统计
        monthly_stats = (
            base_query.with_entities(
                RentLedger.year_month,
                func.sum(RentLedger.due_amount).label("due_amount"),
                func.sum(RentLedger.paid_amount).label("paid_amount"),
                func.sum(RentLedger.overdue_amount).label("overdue_amount"),
            )
            .group_by(RentLedger.year_month)
            .order_by(RentLedger.year_month)
            .all()
        )

        return {
            "total_due": stats.total_due or Decimal("0"),
            "total_paid": stats.total_paid or Decimal("0"),
            "total_overdue": stats.total_overdue or Decimal("0"),
            "total_records": stats.total_records or 0,
            "payment_rate": (stats.total_paid / stats.total_due * 100)
            if stats.total_due
            else Decimal("0"),
            "status_breakdown": [
                {
                    "status": stat.payment_status,
                    "count": stat.count,
                    "due_amount": stat.due_amount or Decimal("0"),
                    "paid_amount": stat.paid_amount or Decimal("0"),
                }
                for stat in status_stats
            ],
            "monthly_breakdown": [
                {
                    "year_month": stat.year_month,
                    "due_amount": stat.due_amount or Decimal("0"),
                    "paid_amount": stat.paid_amount or Decimal("0"),
                    "overdue_amount": stat.overdue_amount or Decimal("0"),
                }
                for stat in monthly_stats
            ],
        }

    def get_ownership_statistics(
        self,
        db: Session,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        ownership_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """按权属方统计租金情况"""
        # ... logic moved from CRUD ...
        query = (
            db.query(
                Ownership.id,
                Ownership.name,
                Ownership.short_name,
                func.count(RentContract.id).label("contract_count"),
                func.sum(RentLedger.due_amount).label("total_due_amount"),
                func.sum(RentLedger.paid_amount).label("total_paid_amount"),
                func.sum(RentLedger.overdue_amount).label("total_overdue_amount"),
            )
            .join(RentContract, RentContract.ownership_id == Ownership.id)
            .join(RentLedger, RentLedger.contract_id == RentContract.id)
            .group_by(Ownership.id, Ownership.name, Ownership.short_name)
        )

        if start_date:
            query = query.filter(RentLedger.due_date >= start_date)
        if end_date:
            query = query.filter(RentLedger.due_date <= end_date)
        if ownership_ids:
            query = query.filter(Ownership.id.in_(ownership_ids))

        results = query.all()

        ownership_stats = []
        for result in results:
            total_due = result.total_due_amount or Decimal("0")
            total_paid = result.total_paid_amount or Decimal("0")
            payment_rate = (total_paid / total_due * 100) if total_due > 0 else Decimal("0")

            ownership_stats.append(
                {
                    "ownership_id": result.id,
                    "ownership_name": result.name,
                    "total_contracts": result.contract_count,
                    "active_contracts": result.contract_count,
                    "total_due_amount": total_due,
                    "total_paid_amount": total_paid,
                    "total_overdue_amount": result.total_overdue_amount or Decimal("0"),
                    "occupancy_rate": payment_rate,
                }
            )

        return ownership_stats

    def get_asset_statistics(
        self,
        db: Session,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        asset_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """按资产统计租金情况"""
        query = (
            db.query(
                Asset.id,
                Asset.property_name,
                Asset.address,
                func.count(RentContract.id).label("contract_count"),
                func.sum(RentLedger.due_amount).label("total_due_amount"),
                func.sum(RentLedger.paid_amount).label("total_paid_amount"),
                func.sum(RentLedger.overdue_amount).label("total_overdue_amount"),
            )
            .join(RentContract, RentContract.asset_id == Asset.id)
            .join(RentLedger, RentLedger.contract_id == RentContract.id)
            .group_by(Asset.id, Asset.property_name, Asset.address)
        )

        if start_date:
            query = query.filter(RentLedger.due_date >= start_date)
        if end_date:
            query = query.filter(RentLedger.due_date <= end_date)
        if asset_ids:
            query = query.filter(Asset.id.in_(asset_ids))

        results = query.all()

        asset_stats = []
        for result in results:
            total_due = result.total_due_amount or Decimal("0")
            total_paid = result.total_paid_amount or Decimal("0")
            payment_rate = (total_paid / total_due * 100) if total_due > 0 else Decimal("0")

            asset_stats.append(
                {
                    "asset_id": result.id,
                    "asset_name": result.property_name,
                    "asset_address": result.address,
                    "contract_count": result.contract_count,
                    "total_due_amount": total_due,
                    "total_paid_amount": total_paid,
                    "total_overdue_amount": result.total_overdue_amount or Decimal("0"),
                    "payment_rate": payment_rate,
                }
            )

        return asset_stats

    def get_monthly_statistics(
        self,
        db: Session,
        *,
        year: int | None = None,
        start_month: str | None = None,
        end_month: str | None = None,
    ) -> list[dict[str, Any]]:
        """获取月度租金统计"""
        query = (
            db.query(
                RentLedger.year_month,
                func.count(func.distinct(RentLedger.contract_id)).label("total_contracts"),
                func.sum(RentLedger.due_amount).label("total_due_amount"),
                func.sum(RentLedger.paid_amount).label("total_paid_amount"),
                func.sum(RentLedger.overdue_amount).label("total_overdue_amount"),
            )
            .group_by(RentLedger.year_month)
            .order_by(RentLedger.year_month)
        )

        if year:
            query = query.filter(RentLedger.year_month.like(f"{year}%"))

        if start_month:
            query = query.filter(RentLedger.year_month >= start_month)
        if end_month:
            query = query.filter(RentLedger.year_month <= end_month)

        results = query.all()

        monthly_stats = []
        for result in results:
            total_due = result.total_due_amount or Decimal("0")
            total_paid = result.total_paid_amount or Decimal("0")
            payment_rate = (total_paid / total_due * 100) if total_due > 0 else Decimal("0")

            monthly_stats.append(
                {
                    "year_month": result.year_month,
                    "total_contracts": result.total_contracts,
                    "total_due_amount": total_due,
                    "total_paid_amount": total_paid,
                    "total_overdue_amount": result.total_overdue_amount or Decimal("0"),
                    "payment_rate": payment_rate,
                }
            )

        return monthly_stats

    # Private helper methods
    def _generate_contract_number(self, db: Session) -> str:
        """生成合同编号"""
        today = datetime.now()
        date_str = today.strftime("%Y%m%d")

        today_count = (
            db.query(RentContract)
            .filter(RentContract.contract_number.like(f"ZJ{date_str}%"))
            .count()
        )

        return f"ZJ{date_str}{today_count + 1:03d}"

    def _create_history(
        self,
        db: Session,
        contract_id: str,
        change_type: str,
        change_description: str,
        old_data: dict | None = None,
        new_data: dict | None = None,
        operator: str | None = None,
        operator_id: str | None = None,
    ) -> RentContractHistory:
        """创建合同历史记录"""
        history = RentContractHistory(
            contract_id=contract_id,
            change_type=change_type,
            change_description=change_description,
            old_data=old_data,
            new_data=new_data,
            operator=operator,
            operator_id=operator_id,
        )
        db.add(history)
        db.commit()
        return history

    def _generate_month_range(self, start_month: str, end_month: str) -> list[str]:
        """生成月份范围"""
        start_year, start_month_num = map(int, start_month.split("-"))
        end_year, end_month_num = map(int, end_month.split("-"))

        months = []
        current_year, current_month = start_year, start_month_num

        while (current_year < end_year) or (
            current_year == end_year and current_month <= end_month_num
        ):
            months.append(f"{current_year}-{current_month:02d}")
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

        return months

    def _get_rent_term_for_date(
        self, rent_terms: list[RentTerm], target_date: date
    ) -> RentTerm | None:
        """获取指定日期的租金条款"""
        for term in rent_terms:
            if term.start_date <= target_date <= term.end_date:
                return term
        return None

    def _calculate_due_date(self, month_date: date, contract: RentContract) -> date:
        """计算应缴日期（默认每月1号）"""
        return month_date.replace(day=1)


rent_contract_service = RentContractService()
