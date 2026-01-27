from enum import Enum


class ContractStatus(str, Enum):
    """合同状态枚举"""

    DRAFT = "DRAFT"  # 草稿/录入中
    PENDING = "PENDING"  # 待审核
    ACTIVE = "ACTIVE"  # 执行中 (原: 有效)
    EXPIRING = "EXPIRING"  # 即将到期
    EXPIRED = "EXPIRED"  # 已到期 (原: 到期)
    TERMINATED = "TERMINATED"  # 已终止 (原: 终止)
    RENEWED = "RENEWED"  # 已续签

    @property
    def label(self) -> str:
        labels = {
            "DRAFT": "草稿",
            "PENDING": "待审核",
            "ACTIVE": "执行中",
            "EXPIRING": "即将到期",
            "EXPIRED": "已到期",
            "TERMINATED": "已终止",
            "RENEWED": "已续签",
        }
        return labels.get(self.value, "未知")
