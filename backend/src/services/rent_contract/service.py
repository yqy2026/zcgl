from typing import Any, Optional, Set

from src.models.rent_contract import RentContract, RentLedger, RentTerm
from .ledger_service import RentContractLedgerService
from .lifecycle_service import RentContractLifecycleService
from .statistics_service import RentContractStatisticsService


def model_to_dict(model: Any, exclude: Optional[Set[str]] = None) -> dict:
    """
    将 SQLAlchemy 模型或 Pydantic 模型转换为字典

    Args:
        model: SQLAlchemy 或 Pydantic 模型实例
        exclude: 要排除的字段集合

    Returns:
        dict: 模型数据的字典表示
    """
    if model is None:
        return {}

    # Pydantic v2 模型
    if hasattr(model, 'model_dump'):
        return model.model_dump(exclude=exclude)

    # SQLAlchemy 模型
    if hasattr(model, '__table__'):
        columns = model.__table__.columns.keys()
        return {
            col: getattr(model, col)
            for col in columns
            if exclude is None or col not in exclude
        }

    # 其他对象，尝试转换为 dict
    return dict(model)


class RentContractService(
    RentContractLifecycleService,
    RentContractLedgerService,
    RentContractStatisticsService,
):
    """租金合同业务服务"""


rent_contract_service = RentContractService()

# 别名，用于测试兼容性
rent_contract = RentContract
rent_ledger = RentLedger
rent_term = RentTerm

__all__ = [
    "RentContractService",
    "rent_contract_service",
    "model_to_dict",
    "rent_contract",
    "rent_ledger",
    "rent_term",
]
