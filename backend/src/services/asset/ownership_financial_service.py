"""
权属方财务统计服务

将财务统计逻辑从 API 层抽离到 Service 层
"""

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.rent_contract import rent_contract, rent_ledger

logger = logging.getLogger(__name__)


@dataclass
class FinancialSummary:
    """财务汇总数据"""

    total_due_amount: float
    total_paid_amount: float
    total_arrears_amount: float
    payment_rate: float


@dataclass
class ContractSummary:
    """合同汇总数据"""

    total_contracts: int
    active_contracts: int


@dataclass
class OwnershipFinancialResult:
    """权属方财务统计结果"""

    ownership_id: str
    ownership_name: str
    financial_summary: FinancialSummary
    contract_summary: ContractSummary

    def to_dict(self) -> dict[str, object]:
        """转换为字典格式"""
        return {
            "ownership_id": self.ownership_id,
            "ownership_name": self.ownership_name,
            "financial_summary": {
                "total_due_amount": self.financial_summary.total_due_amount,
                "total_paid_amount": self.financial_summary.total_paid_amount,
                "total_arrears_amount": self.financial_summary.total_arrears_amount,
                "payment_rate": self.financial_summary.payment_rate,
            },
            "contract_summary": {
                "total_contracts": self.contract_summary.total_contracts,
                "active_contracts": self.contract_summary.active_contracts,
            },
        }


class OwnershipFinancialService:
    """权属方财务统计服务"""

    async def get_financial_summary(
        self,
        db: AsyncSession,
        ownership_id: str,
        ownership_name: str,
    ) -> OwnershipFinancialResult:
        """
        计算权属方财务汇总

        Args:
            db: 数据库会话
            ownership_id: 权属方ID
            ownership_name: 权属方名称

        Returns:
            OwnershipFinancialResult
        """
        # 统计应收总额
        due_amount = await rent_ledger.sum_due_amount_by_ownership_async(
            db, ownership_id
        )

        # 统计实收总额
        paid_amount = await rent_ledger.sum_paid_amount_by_ownership_async(
            db, ownership_id
        )

        # 统计欠款总额
        arrears_amount = await rent_ledger.sum_overdue_amount_by_ownership_async(
            db, ownership_id
        )

        # 统计合同数量
        total_contracts = await rent_contract.count_by_ownership_async(
            db, ownership_id
        )

        # 统计活跃合同数
        active_contracts = await rent_contract.count_active_by_ownership_async(
            db, ownership_id
        )

        # 计算收款率
        payment_rate = float(paid_amount / due_amount * 100) if due_amount > 0 else 0.0

        logger.info(
            f"计算权属方财务汇总: ownership={ownership_id}, "
            f"due={due_amount}, paid={paid_amount}, contracts={total_contracts}"
        )

        return OwnershipFinancialResult(
            ownership_id=ownership_id,
            ownership_name=ownership_name,
            financial_summary=FinancialSummary(
                total_due_amount=float(due_amount),
                total_paid_amount=float(paid_amount),
                total_arrears_amount=float(arrears_amount),
                payment_rate=payment_rate,
            ),
            contract_summary=ContractSummary(
                total_contracts=total_contracts,
                active_contracts=active_contracts,
            ),
        )
