from datetime import date
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session, selectinload

from ...constants.rent_contract_constants import SettlementStatus
from ...core.enums import ContractStatus
from ...models.rent_contract import (
    ContractType,
    RentContract,
    RentContractHistory,
    RentLedger,
    RentTerm,
    ServiceFeeLedger,
)


class RentContractHelperMixin:
    """租金合同服务公共辅助方法"""

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
        conditions = [RentContract.contract_status == ContractStatus.ACTIVE]
        if exclude_contract_id:
            conditions.append(RentContract.id != exclude_contract_id)

        # 查询与指定资产相关的所有有效合同
        query = db.query(RentContract).options(selectinload(RentContract.assets))
        existing_contracts = query.filter(and_(*conditions)).all()

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
                        a.property_name
                        if getattr(a, "property_name", None)
                        else getattr(a, "name", None)
                        for a in contract.assets
                        if a.id in overlapping_assets
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
        history = RentContractHistory()
        history.contract_id = contract_id
        history.change_type = change_type
        history.change_description = change_description
        history.old_data = old_data
        history.new_data = new_data
        history.operator = operator
        history.operator_id = operator_id
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
        service_fee = ServiceFeeLedger()
        service_fee.contract_id = contract.id
        service_fee.source_ledger_id = ledger.id
        service_fee.year_month = ledger.year_month
        service_fee.paid_rent_amount = ledger.paid_amount
        service_fee.fee_rate = contract.service_fee_rate
        service_fee.fee_amount = fee_amount
        service_fee.settlement_status = SettlementStatus.UNSETTLED
        service_fee.notes = (
            f"自动生成：基于租金台账 {ledger.year_month} 实收 {ledger.paid_amount}"
        )
        db.add(service_fee)
        return service_fee
