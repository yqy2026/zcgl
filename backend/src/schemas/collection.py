"""
催缴管理相关的 Pydantic schemas
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class CollectionMethodEnum(str, Enum):
    """催缴方式枚举"""

    PHONE = "phone"
    SMS = "sms"
    EMAIL = "email"
    WECOM = "wecom"
    VISIT = "visit"
    LETTER = "letter"
    OTHER = "other"


class CollectionStatusEnum(str, Enum):
    """催缴状态枚举"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class CollectionRecordBase(BaseModel):
    """催缴记录基础Schema"""

    ledger_id: str = Field(..., description="关联的租金台账ID")
    contract_id: str = Field(..., description="关联合同ID")
    collection_method: CollectionMethodEnum = Field(..., description="催缴方式")
    collection_date: date = Field(..., description="催缴日期")
    collection_status: CollectionStatusEnum = Field(
        CollectionStatusEnum.PENDING, description="催缴状态"
    )
    contacted_person: str | None = Field(None, description="被联系人")
    contact_phone: str | None = Field(None, description="联系电话")
    promised_amount: Decimal | None = Field(None, ge=0, description="承诺付款金额")
    promised_date: date | None = Field(None, description="承诺付款日期")
    actual_payment_amount: Decimal | None = Field(
        None, ge=0, description="实际付款金额"
    )
    collection_notes: str | None = Field(None, description="催缴备注")
    next_follow_up_date: date | None = Field(None, description="下次跟进日期")


class CollectionRecordCreate(CollectionRecordBase):
    """创建催缴记录Schema"""

    operator: str | None = Field(None, description="操作人")
    operator_id: str | None = Field(None, description="操作人ID")


class CollectionRecordUpdate(BaseModel):
    """更新催缴记录Schema"""

    collection_status: CollectionStatusEnum | None = Field(None, description="催缴状态")
    contacted_person: str | None = Field(None, description="被联系人")
    contact_phone: str | None = Field(None, description="联系电话")
    promised_amount: Decimal | None = Field(None, ge=0, description="承诺付款金额")
    promised_date: date | None = Field(None, description="承诺付款日期")
    actual_payment_amount: Decimal | None = Field(
        None, ge=0, description="实际付款金额"
    )
    collection_notes: str | None = Field(None, description="催缴备注")
    next_follow_up_date: date | None = Field(None, description="下次跟进日期")


class CollectionRecordResponse(CollectionRecordBase):
    """催缴记录响应Schema"""

    id: str
    operator: str | None = Field(None, description="操作人")
    operator_id: str | None = Field(None, description="操作人ID")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CollectionTaskSummary(BaseModel):
    """催缴任务汇总"""

    total_overdue_count: int = Field(..., description="逾期台账总数")
    total_overdue_amount: Decimal = Field(..., description="逾期总金额")
    pending_collection_count: int = Field(..., description="待催缴数量")
    this_month_collection_count: int = Field(..., description="本月催缴次数")
    collection_success_rate: Decimal | None = Field(None, description="催缴成功率")


# 分页Schema
class CollectionRecordListResponse(BaseModel):
    """催缴记录列表响应"""

    items: list[CollectionRecordResponse]
    total: int
    page: int
    limit: int
    pages: int
