from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from ...crud.rent_contract import rent_contract, rent_ledger, rent_term
from ...models.asset import Asset, Ownership
from ...models.rent_contract import (
    ContractType,
    DepositTransactionType,
    RentContract,
    RentContractHistory,
    RentDepositLedger,
    RentLedger,
    RentTerm,
    ServiceFeeLedger,
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

    def create_contract(
        self, db: Session, *, obj_in: RentContractCreate
    ) -> RentContract:
        """创建合同（包含租金条款）- V2 支持多资产"""
        # 生成合同编号
        if not obj_in.contract_number:
            obj_in.contract_number = self._generate_contract_number(db)

        # V2: 检查资产租金冲突
        if obj_in.asset_ids:
            conflicts = self._check_asset_rent_conflicts(
                db,
                asset_ids=obj_in.asset_ids,
                start_date=obj_in.start_date,
                end_date=obj_in.end_date,
                exclude_contract_id=None,
            )
            if conflicts:
                # 构造友好的错误消息
                conflict_details = [
                    f"资产 {c['asset_name']} 已被合同 {c['contract_number']} 覆盖 "
                    f"({c['contract_start_date']} 至 {c['contract_end_date']})"
                    for c in conflicts
                ]
                raise ValueError(
                    "资产租金冲突检测:\n"
                    + "\n".join(conflict_details)
                    + "\n\n是否仍要创建? 如果确认创建,请联系管理员或使用强制覆盖功能。"
                )

        # V2: 提取 asset_ids 单独处理
        asset_ids = obj_in.asset_ids or []
        contract_data = obj_in.model_dump(exclude={"rent_terms", "asset_ids"})
        db_contract = RentContract(**contract_data)

        # V2: 关联资产
        if asset_ids:
            assets = db.query(Asset).filter(Asset.id.in_(asset_ids)).all()
            db_contract.assets = assets

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
                term_data_dict["total_monthly_amount"] = (
                    monthly_rent + management_fee + other_fees
                )

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
        """更新合同（包含租金条款）- V2 支持多资产"""
        old_data = model_to_dict(db_obj)

        # V2: 提取 asset_ids 单独处理
        update_data = obj_in.model_dump(
            exclude_unset=True, exclude={"rent_terms", "asset_ids"}
        )
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        # V2: 更新资产关联
        if obj_in.asset_ids is not None:
            assets = db.query(Asset).filter(Asset.id.in_(obj_in.asset_ids)).all()
            db_obj.assets = assets

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

    def renew_contract(
        self,
        db: Session,
        *,
        original_contract_id: str,
        new_contract_data: RentContractCreate,
        transfer_deposit: bool = True,
        operator: str | None = None,
        operator_id: str | None = None,
    ) -> RentContract:
        """
        合同续签
        1. 创建新合同（预填数据）
        2. 结束原合同
        3. 转移押金（通过 DepositLedger 记录）
        """
        # 获取原合同
        original = (
            db.query(RentContract)
            .filter(RentContract.id == original_contract_id)
            .first()
        )
        if not original:
            raise ValueError(f"原合同不存在: {original_contract_id}")
        if original.contract_status != "有效":
            raise ValueError(f"原合同状态不可续签: {original.contract_status}")

        # 创建新合同
        new_contract = self.create_contract(db, obj_in=new_contract_data)

        # 转移押金
        if transfer_deposit and original.total_deposit > 0:
            deposit_amount = original.total_deposit

            # 原合同押金转出
            transfer_out = RentDepositLedger(
                contract_id=original.id,
                transaction_type=DepositTransactionType.TRANSFER_OUT,
                amount=-deposit_amount,
                transaction_date=date.today(),
                related_contract_id=new_contract.id,
                notes=f"续签转出至新合同 {new_contract.contract_number}",
                operator=operator,
                operator_id=operator_id,
            )
            db.add(transfer_out)

            # 新合同押金转入
            transfer_in = RentDepositLedger(
                contract_id=new_contract.id,
                transaction_type=DepositTransactionType.TRANSFER_IN,
                amount=deposit_amount,
                transaction_date=date.today(),
                related_contract_id=original.id,
                notes=f"从原合同 {original.contract_number} 续签转入",
                operator=operator,
                operator_id=operator_id,
            )
            db.add(transfer_in)

        # 结束原合同
        setattr(original, "contract_status", "已续签")
        db.add(original)

        # 记录历史
        self._create_history(
            db,
            contract_id=original.id,
            change_type="续签",
            change_description=f"续签至新合同 {new_contract.contract_number}",
            operator=operator,
            operator_id=operator_id,
        )

        db.commit()
        db.refresh(new_contract)
        return new_contract

    def terminate_contract(
        self,
        db: Session,
        *,
        contract_id: str,
        termination_date: date,
        refund_deposit: bool = True,
        deduction_amount: Decimal = Decimal("0"),
        termination_reason: str | None = None,
        operator: str | None = None,
        operator_id: str | None = None,
    ) -> RentContract:
        """
        合同提前终止
        1. 更新合同状态
        2. 处理押金（退还/抵扣）
        """
        contract = db.query(RentContract).filter(RentContract.id == contract_id).first()
        if not contract:
            raise ValueError(f"合同不存在: {contract_id}")
        if contract.contract_status not in ["有效"]:
            raise ValueError(f"合同状态不可终止: {contract.contract_status}")

        deposit_balance = contract.total_deposit

        # 处理抵扣
        if deduction_amount > 0:
            if deduction_amount > deposit_balance:
                raise ValueError(
                    f"抵扣金额 {deduction_amount} 超过押金余额 {deposit_balance}"
                )

            deduction = RentDepositLedger(
                contract_id=contract.id,
                transaction_type=DepositTransactionType.DEDUCTION,
                amount=-deduction_amount,
                transaction_date=termination_date,
                notes=f"终止抵扣: {termination_reason or '欠租等'}",
                operator=operator,
                operator_id=operator_id,
            )
            db.add(deduction)
            deposit_balance -= deduction_amount

        # 退还剩余押金
        if refund_deposit and deposit_balance > 0:
            refund = RentDepositLedger(
                contract_id=contract.id,
                transaction_type=DepositTransactionType.REFUND,
                amount=-deposit_balance,
                transaction_date=termination_date,
                notes="终止退还押金",
                operator=operator,
                operator_id=operator_id,
            )
            db.add(refund)

        # 更新合同状态
        setattr(contract, "contract_status", "已终止")
        setattr(
            contract,
            "end_date",
            datetime.combine(termination_date, datetime.min.time()),
        )
        db.add(contract)

        # 记录历史
        self._create_history(
            db,
            contract_id=contract.id,
            change_type="终止",
            change_description=f"提前终止: {termination_reason or '未说明'}",
            operator=operator,
            operator_id=operator_id,
        )

        db.commit()
        db.refresh(contract)
        return contract

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
                    # V2: asset_id is nullable in RentLedger, contract has M2M assets
                    "asset_id": None,
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
        ledgers = (
            db.query(RentLedger).filter(RentLedger.id.in_(request.ledger_ids)).all()
        )

        for ledger in ledgers:
            # 更新支付信息
            if request.payment_status is not None:
                ledger.payment_status = request.payment_status
            if request.payment_date is not None:
                setattr(
                    ledger,
                    "payment_date",
                    datetime.combine(request.payment_date, datetime.min.time()),
                )
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

                # V2: 委托运营合同自动计算服务费
                self._calculate_service_fee_for_ledger(db, ledger)

        db.commit()
        return ledgers

    # 统计相关方法
    def get_statistics(
        self, db: Session, *, query_params: RentStatisticsQuery
    ) -> dict[str, Any]:
        """获取统计信息"""
        # 构建基础查询
        base_query = db.query(RentLedger)

        # 应用筛选条件
        if query_params.start_date:
            base_query = base_query.filter(
                RentLedger.due_date >= query_params.start_date
            )
        if query_params.end_date:
            base_query = base_query.filter(RentLedger.due_date <= query_params.end_date)
        if query_params.ownership_ids:
            base_query = base_query.filter(
                RentLedger.ownership_id.in_(query_params.ownership_ids)
            )
        if query_params.asset_ids:
            base_query = base_query.filter(
                RentLedger.asset_id.in_(query_params.asset_ids)
            )

        # 基础统计
        stats = base_query.with_entities(
            func.sum(RentLedger.due_amount).label("total_due"),
            func.sum(RentLedger.paid_amount).label("total_paid"),
            func.sum(RentLedger.overdue_amount).label("total_overdue"),
            func.count(RentLedger.id).label("total_records"),
        ).first()

        # Handle None case for stats
        if stats is None:
            total_due = Decimal("0")
            total_paid = Decimal("0")
            total_overdue = Decimal("0")
            total_records = 0
        else:
            total_due = stats.total_due or Decimal("0")
            total_paid = stats.total_paid or Decimal("0")
            total_overdue = stats.total_overdue or Decimal("0")
            total_records = stats.total_records or 0

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

        payment_rate = (total_paid / total_due * 100) if total_due else Decimal("0")

        return {
            "total_due": total_due,
            "total_paid": total_paid,
            "total_overdue": total_overdue,
            "total_records": total_records,
            "payment_rate": payment_rate,
            # V2: New Operational Metrics
            "average_unit_price": self._calculate_average_unit_price(db, query_params),
            "renewal_rate": self._calculate_renewal_rate(db, query_params),
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
            payment_rate = (
                (total_paid / total_due * 100) if total_due > 0 else Decimal("0")
            )

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
            payment_rate = (
                (total_paid / total_due * 100) if total_due > 0 else Decimal("0")
            )

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
                func.count(func.distinct(RentLedger.contract_id)).label(
                    "total_contracts"
                ),
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
            payment_rate = (
                (total_paid / total_due * 100) if total_due > 0 else Decimal("0")
            )

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
    def _check_asset_rent_conflicts(
        self,
        db: Session,
        *,
        asset_ids: list[str],
        start_date: date,
        end_date: date,
        exclude_contract_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        检查资产租金冲突

        检测指定资产在指定时间段内是否已被其他合同覆盖

        Args:
            db: 数据库会话
            asset_ids: 要检查的资产ID列表
            start_date: 新合同的开始日期
            end_date: 新合同的结束日期
            exclude_contract_id: 要排除的合同ID(更新合同时使用)

        Returns:
            冲突列表,每个冲突包含资产信息和合同信息
        """
        conflicts = []

        # Build conditions for and_()
        conditions = [RentContract.contract_status == "有效"]
        if exclude_contract_id:
            conditions.append(RentContract.id != exclude_contract_id)

        # 查询与指定资产相关的所有有效合同
        existing_contracts = db.query(RentContract).filter(and_(*conditions)).all()

        # 检查每个现有合同是否与新合同时间段重叠
        for contract in existing_contracts:
            # 获取该合同的资产
            contract_assets = [a.id for a in contract.assets]

            # 检查是否有资产重叠
            overlapping_assets = set(asset_ids) & set(contract_assets)

            if overlapping_assets:
                # 检查时间段是否重叠
                # 重叠条件: (新合同开始 <= 旧合同结束) AND (新合同结束 >= 旧合同开始)
                if start_date <= contract.end_date and end_date >= contract.start_date:
                    # 获取重叠资产的名称
                    overlapping_asset_names = [
                        a.name for a in contract.assets if a.id in overlapping_assets
                    ]

                    conflicts.append(
                        {
                            "contract_id": contract.id,
                            "contract_number": contract.contract_number,
                            "contract_start_date": contract.start_date.isoformat(),
                            "contract_end_date": contract.end_date.isoformat(),
                            "asset_ids": list(overlapping_assets),
                            "asset_name": overlapping_asset_names[0]
                            if overlapping_asset_names
                            else "未知",
                        }
                    )

        return conflicts

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
        old_data: dict[str, Any] | None = None,
        new_data: dict[str, Any] | None = None,
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

    def _calculate_service_fee_for_ledger(
        self, db: Session, ledger: RentLedger
    ) -> ServiceFeeLedger | None:
        """
        V2: 为委托运营合同自动计算服务费
        当租金台账收到实收款项时，如果关联合同为委托运营类型，自动生成服务费记录
        """
        # 获取合同信息
        contract = (
            db.query(RentContract).filter(RentContract.id == ledger.contract_id).first()
        )
        if not contract:
            return None

        # 仅处理委托运营类型的合同
        if contract.contract_type != ContractType.ENTRUSTED:
            return None

        # 合同必须设置服务费率
        if not contract.service_fee_rate or contract.service_fee_rate <= 0:
            return None

        # 检查此台账是否已生成过服务费
        existing = (
            db.query(ServiceFeeLedger)
            .filter(ServiceFeeLedger.source_ledger_id == ledger.id)
            .first()
        )
        if existing:
            # 更新现有记录
            existing.paid_rent_amount = ledger.paid_amount
            existing.fee_amount = ledger.paid_amount * contract.service_fee_rate
            return existing

        # 计算服务费：实收金额 × 服务费率
        fee_amount = ledger.paid_amount * contract.service_fee_rate

        # 创建服务费记录
        service_fee = ServiceFeeLedger(
            contract_id=contract.id,
            source_ledger_id=ledger.id,
            year_month=ledger.year_month,
            paid_rent_amount=ledger.paid_amount,
            fee_rate=contract.service_fee_rate,
            fee_amount=fee_amount,
            settlement_status="待结算",
            notes=f"自动生成：基于租金台账 {ledger.year_month} 实收 {ledger.paid_amount}",
        )
        db.add(service_fee)
        return service_fee

    def _calculate_average_unit_price(
        self, db: Session, query_params: RentStatisticsQuery
    ) -> Decimal:
        """
        Calculates the average unit price (Monthly Rent / Rentable Area).
        Note: Only considers 'lease_downstream' contracts which typically generate revenue.
        Formula: Sum(Monthly Rent) / Sum(Rentable Area)
        """
        # Join RentContract with Asset to get area
        # V2: Contracts have many-to-many relationship with Assets, but here we can approximate
        # by checking contracts that have associated assets.
        # Since calculating exact area share for multi-asset contracts is complex,
        # we will aggregate total rent of downstream contracts and divide by total area of assets linked to them.

        # 1. Filter valid downstream contracts
        query = db.query(RentContract).filter(
            RentContract.contract_type == ContractType.LEASE_DOWNSTREAM,
            RentContract.contract_status == "有效",
        )

        if query_params.start_date:
            # Check if contract is active during the period
            query = query.filter(RentContract.start_date <= query_params.end_date)
        if query_params.end_date:
            query = query.filter(RentContract.end_date >= query_params.start_date)

        if query_params.ownership_ids:
            query = query.filter(
                RentContract.ownership_id.in_(query_params.ownership_ids)
            )

        contracts = query.all()
        if not contracts:
            return Decimal("0")

        total_rent = Decimal("0")
        total_area = Decimal("0")

        for contract in contracts:
            # Monthly Rent
            # If monthly_rent_base is set, use it. Otherwise try to get from current term
            rent = contract.monthly_rent_base or Decimal("0")
            if rent == 0 and contract.rent_terms:
                # Use first active term or just first term as fallback
                rent = contract.rent_terms[0].monthly_rent

            # Asset Area
            # Sum area of all associated assets
            area = sum((asset.area or Decimal("0")) for asset in contract.assets)

            if area > 0:
                total_rent += rent
                total_area += area

        if total_area == 0:
            return Decimal("0")

        return (total_rent / total_area).quantize(Decimal("0.00"))

    def _calculate_renewal_rate(
        self, db: Session, query_params: RentStatisticsQuery
    ) -> Decimal:
        """
        Calculates renewal rate.
        Formula: Renewed Contracts / (Renewed + Expired + Terminated)
        Renewal Rate = '已续签' / ('已续签' + '已到期' + '已终止')
        """
        query = db.query(
            RentContract.contract_status, func.count(RentContract.id)
        ).group_by(RentContract.contract_status)

        if query_params.ownership_ids:
            query = query.filter(
                RentContract.ownership_id.in_(query_params.ownership_ids)
            )

        # Date filtering for renewal rate
        if query_params.start_date and query_params.end_date:
            query = query.filter(
                RentContract.end_date.between(
                    query_params.start_date, query_params.end_date
                )
            )

        stats = {row[0]: row[1] for row in query.all()}

        renewed = stats.get("已续签", 0)
        expired = stats.get("已到期", 0)
        terminated = stats.get("已终止", 0)

        total_ended = renewed + expired + terminated
        if total_ended == 0:
            return Decimal("0")

        rate = (Decimal(str(renewed)) / Decimal(str(total_ended))) * 100
        return rate.quantize(Decimal("0.00"))


rent_contract_service = RentContractService()
