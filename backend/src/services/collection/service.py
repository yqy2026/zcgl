"""
催缴管理业务服务

将催缴相关的数据库操作从 API 层迁移至此服务层，
遵循项目架构规范：业务逻辑必须在 services/ 层。
"""

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from ...constants.rent_contract_constants import PaymentStatus
from ...core.exception_handler import ResourceNotFoundError
from ...models.collection import CollectionRecord, CollectionStatus
from ...models.rent_contract import RentLedger
from ...schemas.collection import (
    CollectionRecordCreate,
    CollectionRecordUpdate,
    CollectionTaskSummary,
)


class CollectionService:
    """催缴管理业务服务"""

    def get_summary(self, db: Session) -> CollectionTaskSummary:
        """
        获取催缴任务汇总统计

        包括：
        - 逾期台账总数和总金额
        - 待催缴数量
        - 本月催缴次数
        - 催缴成功率
        """
        today = date.today()
        current_month_start = date(today.year, today.month, 1)

        # 1. 统计逾期台账
        overdue_stats = (
            db.query(
                func.count(RentLedger.id).label("total_count"),
                func.sum(RentLedger.overdue_amount).label("total_amount"),
            )
            .filter(
                and_(
                    RentLedger.payment_status.in_([PaymentStatus.UNPAID, PaymentStatus.PARTIAL]),
                    RentLedger.due_date < today,
                    RentLedger.data_status == "正常",
                )
            )
            .first()
        )

        total_overdue_count = overdue_stats.total_count if overdue_stats else 0
        total_overdue_amount = (
            overdue_stats.total_amount if overdue_stats else Decimal("0")
        )

        # 2. 统计待催缴数量（状态为 pending 或 in_progress 的记录）
        pending_count = (
            db.query(func.count(CollectionRecord.id))
            .filter(
                CollectionRecord.collection_status.in_(
                    [CollectionStatus.PENDING, CollectionStatus.IN_PROGRESS]
                )
            )
            .scalar()
        )
        pending_collection_count = pending_count or 0

        # 3. 统计本月催缴次数
        this_month_count = (
            db.query(func.count(CollectionRecord.id))
            .filter(CollectionRecord.collection_date >= current_month_start)
            .scalar()
        )
        this_month_collection_count = this_month_count or 0

        # 4. 计算催缴成功率（状态为 success 的记录占比）
        success_count = (
            db.query(func.count(CollectionRecord.id))
            .filter(CollectionRecord.collection_status == CollectionStatus.SUCCESS)
            .scalar()
        )
        total_collection_count = db.query(func.count(CollectionRecord.id)).scalar()

        collection_success_rate = None
        if total_collection_count and total_collection_count > 0:
            collection_success_rate = (
                Decimal(success_count or 0)
                / Decimal(total_collection_count)
                * Decimal("100")
            )

        return CollectionTaskSummary(
            total_overdue_count=total_overdue_count,
            total_overdue_amount=total_overdue_amount,
            pending_collection_count=pending_collection_count,
            this_month_collection_count=this_month_collection_count,
            collection_success_rate=collection_success_rate,
        )

    def list_records(
        self,
        db: Session,
        *,
        ledger_id: str | None = None,
        contract_id: str | None = None,
        collection_status: CollectionStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """
        查询催缴记录列表，支持按台账、合同、状态筛选

        Returns:
            包含 items, total, page, page_size 的字典
        """
        query = db.query(CollectionRecord)

        # 应用筛选条件
        if ledger_id:
            query = query.filter(CollectionRecord.ledger_id == ledger_id)
        if contract_id:
            query = query.filter(CollectionRecord.contract_id == contract_id)
        if collection_status:
            query = query.filter(CollectionRecord.collection_status == collection_status)

        # 计算总数
        total = query.count()

        # 分页
        offset = (page - 1) * page_size
        records = (
            query.order_by(CollectionRecord.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return {
            "items": records,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get_by_id(self, db: Session, *, record_id: str) -> CollectionRecord | None:
        """获取单条催缴记录"""
        return (
            db.query(CollectionRecord)
            .filter(CollectionRecord.id == record_id)
            .first()
        )

    def get_ledger_by_id(self, db: Session, *, ledger_id: str) -> RentLedger | None:
        """获取关联的租金台账"""
        return db.query(RentLedger).filter(RentLedger.id == ledger_id).first()

    def create(
        self,
        db: Session,
        *,
        obj_in: CollectionRecordCreate,
        operator: str | None = None,
        operator_id: str | None = None,
    ) -> CollectionRecord:
        """
        创建新的催缴记录

        Args:
            db: 数据库会话
            obj_in: 创建数据
            operator: 操作人名称（可选，用于填充默认值）
            operator_id: 操作人ID（可选，用于填充默认值）

        Returns:
            创建的催缴记录

        Raises:
            ValueError: 如果关联的租金台账不存在
        """
        # 验证台账存在
        ledger = self.get_ledger_by_id(db, ledger_id=obj_in.ledger_id)
        if not ledger:
            raise ResourceNotFoundError("租金台账", obj_in.ledger_id)

        # 设置操作人
        record_data = obj_in.model_dump()
        if not record_data.get("operator") and operator:
            record_data["operator"] = operator
        if not record_data.get("operator_id") and operator_id:
            record_data["operator_id"] = operator_id

        # 创建记录
        record = CollectionRecord(**record_data)
        db.add(record)
        db.commit()
        db.refresh(record)

        return record

    def update(
        self,
        db: Session,
        *,
        db_obj: CollectionRecord,
        obj_in: CollectionRecordUpdate,
    ) -> CollectionRecord:
        """
        更新催缴记录（状态、承诺信息等）

        Args:
            db: 数据库会话
            db_obj: 现有记录对象
            obj_in: 更新数据

        Returns:
            更新后的催缴记录
        """
        update_dict = obj_in.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(db_obj, field, value)

        db.commit()
        db.refresh(db_obj)

        return db_obj

    def delete(self, db: Session, *, db_obj: CollectionRecord) -> None:
        """
        删除催缴记录

        Args:
            db: 数据库会话
            db_obj: 要删除的记录对象
        """
        db.delete(db_obj)
        db.commit()


# 单例实例
collection_service = CollectionService()
