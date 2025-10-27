"""
租金台账相关的Pydantic schemas
"""

from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, ConfigDict


# 基础Schema
class RentTermBase(BaseModel):
    """租金条款基础Schema"""
    start_date: date = Field(..., description="条款开始日期")
    end_date: date = Field(..., description="条款结束日期")
    monthly_rent: Decimal = Field(..., ge=0, description="月租金金额")
    rent_description: Optional[str] = Field(None, description="租金描述")
    management_fee: Decimal = Field(0, ge=0, description="管理费")
    other_fees: Decimal = Field(0, ge=0, description="其他费用")
    total_monthly_amount: Optional[Decimal] = Field(None, ge=0, description="月总金额")

    @field_validator('total_monthly_amount')
    @classmethod
    def calculate_total_amount(cls, v, values):
        """计算月总金额"""
        if v is None:
            monthly_rent = values.get('monthly_rent', Decimal('0'))
            management_fee = values.get('management_fee', Decimal('0'))
            other_fees = values.get('other_fees', Decimal('0'))
            return monthly_rent + management_fee + other_fees
        return v

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v, values):
        """验证日期范围"""
        start_date = values.get('start_date')
        if start_date and v <= start_date:
            raise ValueError("结束日期必须大于开始日期")
        return v


class RentTermCreate(RentTermBase):
    """创建租金条款Schema"""
    pass


class RentTermUpdate(RentTermBase):
    """更新租金条款Schema"""
    pass


class RentTermResponse(RentTermBase):
    """租金条款响应Schema"""
    id: str
    contract_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes = True
    )
class RentContractBase(BaseModel):
    """租金合同基础Schema"""
    contract_number: str = Field(..., description="合同编号")
    asset_id: str = Field(..., description="关联资产ID")
    ownership_id: str = Field(..., description="权属方ID")
    tenant_name: str = Field(..., description="承租方名称")
    tenant_contact: Optional[str] = Field(None, description="承租方联系人")
    tenant_phone: Optional[str] = Field(None, description="承租方联系电话")
    tenant_address: Optional[str] = Field(None, description="承租方地址")
    sign_date: date = Field(..., description="签订日期")
    start_date: date = Field(..., description="租期开始日期")
    end_date: date = Field(..., description="租期结束日期")
    total_deposit: Decimal = Field(0, ge=0, description="总押金金额")
    monthly_rent_base: Optional[Decimal] = Field(None, ge=0, description="基础月租金")
    contract_status: str = Field("有效", description="合同状态")
    payment_terms: Optional[str] = Field(None, description="支付条款")
    contract_notes: Optional[str] = Field(None, description="合同备注")

    @field_validator('end_date')
    @classmethod
    def validate_date_range(cls, v, values):
        """验证日期范围"""
        start_date = values.get('start_date')
        if start_date and v <= start_date:
            raise ValueError("结束日期必须大于开始日期")
        return v


class RentContractCreate(RentContractBase):
    """创建租金合同Schema"""
    rent_terms: List[RentTermCreate] = Field(..., description="租金条款列表")

    @field_validator('rent_terms')
    @classmethod
    def validate_rent_terms(cls, v, values):
        """验证租金条款"""
        if not v:
            raise ValueError("租金条款不能为空")

        start_date = values.get('start_date')
        end_date = values.get('end_date')

        if start_date and end_date:
            # 验证条款覆盖完整租期
            terms_sorted = sorted(v, key=lambda x: x.start_date)

            # 检查第一个条款开始日期
            if terms_sorted[0].start_date != start_date:
                raise ValueError(f"第一个条款的开始日期必须是合同开始日期: {start_date}")

            # 检查连续性
            for i in range(len(terms_sorted) - 1):
                if terms_sorted[i].end_date != terms_sorted[i + 1].start_date:
                    raise ValueError("租金条款时间范围必须连续")

            # 检查最后一个条款结束日期
            if terms_sorted[-1].end_date != end_date:
                raise ValueError(f"最后一个条款的结束日期必须是合同结束日期: {end_date}")

        return v


class RentContractUpdate(RentContractBase):
    """更新租金合同Schema"""
    contract_number: Optional[str] = Field(None, description="合同编号")
    asset_id: Optional[str] = Field(None, description="关联资产ID")
    ownership_id: Optional[str] = Field(None, description="权属方ID")
    tenant_name: Optional[str] = Field(None, description="承租方名称")
    sign_date: Optional[date] = Field(None, description="签订日期")
    start_date: Optional[date] = Field(None, description="租期开始日期")
    end_date: Optional[date] = Field(None, description="租期结束日期")
    rent_terms: Optional[List[RentTermUpdate]] = Field(None, description="租金条款列表")


class RentContractResponse(RentContractBase):
    """租金合同响应Schema"""
    id: str
    data_status: str = Field("正常", description="数据状态")
    version: int = Field(1, description="版本号")
    created_at: datetime
    updated_at: datetime
    tenant_id: Optional[str] = Field(None, description="租户ID")
    rent_terms: List[RentTermResponse] = Field([], description="租金条款列表")

    model_config = ConfigDict(
        from_attributes = True
    )
class RentLedgerBase(BaseModel):
    """租金台账基础Schema"""
    contract_id: str = Field(..., description="关联合同ID")
    asset_id: str = Field(..., description="关联资产ID")
    ownership_id: str = Field(..., description="权属方ID")
    year_month: str = Field(..., description="年月，格式：YYYY-MM")
    due_date: date = Field(..., description="应缴日期")
    due_amount: Decimal = Field(..., ge=0, description="应收金额")
    paid_amount: Decimal = Field(0, ge=0, description="实收金额")
    overdue_amount: Decimal = Field(0, ge=0, description="逾期金额")
    payment_status: str = Field("未支付", description="支付状态")
    payment_date: Optional[date] = Field(None, description="支付日期")
    payment_method: Optional[str] = Field(None, description="支付方式")
    payment_reference: Optional[str] = Field(None, description="支付参考号")
    late_fee: Decimal = Field(0, ge=0, description="滞纳金")
    late_fee_days: int = Field(0, ge=0, description="滞纳天数")
    notes: Optional[str] = Field(None, description="备注")

    @field_validator('year_month')
    @classmethod
    def validate_year_month(cls, v):
        """验证年月格式"""
        if len(v) != 7 or v[4] != '-':
            raise ValueError("年月格式必须是YYYY-MM")
        try:
            year = int(v[:4])
            month = int(v[5:7])
            if not (1 <= month <= 12):
                raise ValueError("月份必须在1-12之间")
        except ValueError:
            raise ValueError("年月格式无效")
        return v

    @field_validator('payment_status')
    @classmethod
    def validate_payment_status(cls, v):
        """验证支付状态"""
        valid_statuses = ["未支付", "部分支付", "已支付", "逾期"]
        if v not in valid_statuses:
            raise ValueError(f"支付状态必须是: {', '.join(valid_statuses)}")
        return v


class RentLedgerCreate(RentLedgerBase):
    """创建租金台账Schema"""
    pass


class RentLedgerUpdate(BaseModel):
    """更新租金台账Schema"""
    paid_amount: Optional[Decimal] = Field(None, ge=0, description="实收金额")
    payment_status: Optional[str] = Field(None, description="支付状态")
    payment_date: Optional[date] = Field(None, description="支付日期")
    payment_method: Optional[str] = Field(None, description="支付方式")
    payment_reference: Optional[str] = Field(None, description="支付参考号")
    late_fee: Optional[Decimal] = Field(None, ge=0, description="滞纳金")
    late_fee_days: Optional[int] = Field(None, ge=0, description="滞纳天数")
    notes: Optional[str] = Field(None, description="备注")


class RentLedgerResponse(RentLedgerBase):
    """租金台账响应Schema"""
    id: str
    data_status: str = Field("正常", description="数据状态")
    version: int = Field(1, description="版本号")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes = True
    )
class RentLedgerBatchUpdate(BaseModel):
    """批量更新租金台账Schema"""
    ledger_ids: List[str] = Field(..., description="台账ID列表")
    payment_status: str = Field(..., description="支付状态")
    payment_date: Optional[date] = Field(None, description="支付日期")
    payment_method: Optional[str] = Field(None, description="支付方式")
    payment_reference: Optional[str] = Field(None, description="支付参考号")
    notes: Optional[str] = Field(None, description="备注")


# 统计相关Schema
class RentStatisticsQuery(BaseModel):
    """租金统计查询参数"""
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    ownership_ids: Optional[List[str]] = Field(None, description="权属方ID列表")
    asset_ids: Optional[List[str]] = Field(None, description="资产ID列表")
    contract_status: Optional[str] = Field(None, description="合同状态")


class OwnershipRentStatistics(BaseModel):
    """权属方租金统计"""
    ownership_id: str
    ownership_name: str
    total_contracts: int
    active_contracts: int
    total_due_amount: Decimal
    total_paid_amount: Decimal
    total_overdue_amount: Decimal
    occupancy_rate: Optional[Decimal] = Field(None, description="收缴率")


class AssetRentStatistics(BaseModel):
    """资产租金统计"""
    asset_id: str
    asset_name: str
    asset_address: str
    contract_count: int
    total_due_amount: Decimal
    total_paid_amount: Decimal
    total_overdue_amount: Decimal
    occupancy_rate: Optional[Decimal] = Field(None, description="收缴率")


class MonthlyRentStatistics(BaseModel):
    """月度租金统计"""
    year_month: str
    total_contracts: int
    total_due_amount: Decimal
    total_paid_amount: Decimal
    total_overdue_amount: Decimal
    payment_rate: Decimal


# 生成台账Schema
class GenerateLedgerRequest(BaseModel):
    """生成台账请求"""
    contract_id: str = Field(..., description="合同ID")
    start_year_month: Optional[str] = Field(None, description="开始年月")
    end_year_month: Optional[str] = Field(None, description="结束年月")

    @field_validator('start_year_month', 'end_year_month')
    @classmethod
    def validate_year_month(cls, v):
        """验证年月格式"""
        if v is None:
            return v
        if len(v) != 7 or v[4] != '-':
            raise ValueError("年月格式必须是YYYY-MM")
        try:
            year = int(v[:4])
            month = int(v[5:7])
            if not (1 <= month <= 12):
                raise ValueError("月份必须在1-12之间")
        except ValueError:
            raise ValueError("年月格式无效")
        return v


# 分页Schema
class RentContractListResponse(BaseModel):
    """租金合同列表响应"""
    items: List[RentContractResponse]
    total: int
    page: int
    limit: int
    pages: int


class RentLedgerListResponse(BaseModel):
    """租金台账列表响应"""
    items: List[RentLedgerResponse]
    total: int
    page: int
    limit: int
    pages: int