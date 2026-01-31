"""
Rent contract constants.

Centralized values for rent contract attachments and payment statuses.
"""

from enum import Enum
from typing import Final

CONTRACT_ATTACHMENT_SUBDIR: Final[str] = "contracts"


class PaymentStatus(str, Enum):
    """支付状态枚举"""

    UNPAID = "未支付"
    PAID = "已支付"
    PARTIAL = "部分支付"
    OVERDUE = "逾期"


class SettlementStatus(str, Enum):
    """结算状态枚举"""

    UNSETTLED = "待结算"
    SETTLED = "已结算"


__all__ = ["CONTRACT_ATTACHMENT_SUBDIR", "PaymentStatus", "SettlementStatus"]
