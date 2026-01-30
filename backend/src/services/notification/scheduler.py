"""
通知定时任务服务

负责扫描合同到期、付款逾期等场景，并生成通知
支持企业微信推送
"""

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from ...constants.business_constants import DataStatusValues
from ...constants.rent_contract_constants import PaymentStatus
from ...core.enums import ContractStatus
from ...database import get_db
from ...models.auth import User

logger = logging.getLogger(__name__)
from ...models.notification import Notification, NotificationPriority, NotificationType
from ...models.rent_contract import RentContract, RentLedger
from .wecom_service import wecom_service


class NotificationSchedulerService:
    """通知定时任务服务"""

    def __init__(self, db: Session):
        self.db = db
        self.wecom_enabled = wecom_service.enabled

    async def _send_wecom_notification(self, notification: Notification) -> bool:
        """
        发送企业微信通知（异步）

        Args:
            notification: 通知对象

        Returns:
            bool: 是否发送成功
        """
        if not self.wecom_enabled:
            return False

        try:
            # 构建企业微信消息
            message = f"【{notification.title}】\n{notification.content}"

            # 发送企业微信通知
            success = await wecom_service.send_notification(message=message)

            # 更新通知状态
            notification.is_sent_wecom = success
            if success:
                notification.wecom_sent_at = datetime.now()
            else:
                notification.wecom_send_error = "企业微信返回失败"

            self.db.commit()
            return success

        except Exception as e:
            # 记录错误但不影响主流程
            notification.wecom_send_error = f"企业微信发送异常: {str(e)}"
            self.db.commit()
            return False

    def _create_and_send_notification(
        self,
        recipient_id: str,
        notification_type: str,
        priority: str,
        title: str,
        content: str,
        related_entity_type: str,
        related_entity_id: str,
    ) -> Notification:
        """
        创建通知并发送企业微信（如果启用）

        Args:
            recipient_id: 接收用户ID
            notification_type: 通知类型
            priority: 优先级
            title: 标题
            content: 内容
            related_entity_type: 关联实体类型
            related_entity_id: 关联实体ID

        Returns:
            Notification: 创建的通知对象
        """
        notification = Notification(
            recipient_id=recipient_id,
            type=notification_type,
            priority=priority,
            title=title,
            content=content,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            is_read=False,
        )
        self.db.add(notification)
        self.db.flush()  # 获取 ID

        # 如果启用了企业微信，异步推送
        if self.wecom_enabled:
            try:
                # 在新的事件循环中运行异步推送
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self._send_wecom_notification(notification))
                finally:
                    loop.close()
            except Exception as e:
                # 推送失败不影响通知创建
                notification.wecom_send_error = f"企业微信推送失败: {str(e)}"

        return notification

    def check_contract_expiry(self, days_ahead: int = 30) -> int:
        """
        检查合同到期

        Args:
            days_ahead: 提前多少天提醒，默认30天

        Returns:
            int: 即将到期的合同数量
        """
        today = date.today()
        warning_date = today + timedelta(days=days_ahead)

        # 查找即将到期的有效合同
        expiring_contracts = (
            self.db.query(RentContract)
            .filter(
                and_(
                    RentContract.contract_status == ContractStatus.ACTIVE,
                    RentContract.end_date <= warning_date,
                    RentContract.end_date >= today,
                )
            )
            .all()
        )

        for contract in expiring_contracts:
            # 计算剩余天数
            # end_date is Mapped[datetime] but stored as Date, convert to date for subtraction
            end_date_val: date | datetime = contract.end_date
            if isinstance(end_date_val, datetime):
                end_date_val = end_date_val.date()
            days_remaining = (end_date_val - today).days

            # 确定通知类型和优先级
            notification_type: str
            priority: str
            if days_remaining == 0:
                notification_type = NotificationType.CONTRACT_EXPIRED
                priority = NotificationPriority.URGENT
                title = "合同已到期"
                content = f"合同 {contract.contract_number}（{contract.tenant_name}）已于今日到期，请及时处理"
            elif days_remaining <= 7:
                notification_type = NotificationType.CONTRACT_EXPIRING
                priority = NotificationPriority.URGENT
                title = f"合同即将到期（{days_remaining}天）"
                content = f"合同 {contract.contract_number}（{contract.tenant_name}）将在{days_remaining}天后到期"
            elif days_remaining <= 15:
                notification_type = NotificationType.CONTRACT_EXPIRING
                priority = NotificationPriority.HIGH
                title = f"合同即将到期（{days_remaining}天）"
                content = f"合同 {contract.contract_number}（{contract.tenant_name}）将在{days_remaining}天后到期"
            else:
                notification_type = NotificationType.CONTRACT_EXPIRING
                priority = NotificationPriority.NORMAL
                title = f"合同即将到期（{days_remaining}天）"
                content = f"合同 {contract.contract_number}（{contract.tenant_name}）将在{days_remaining}天后到期"

            # 查找所有活跃用户
            active_users = self.db.query(User).filter(User.is_active.is_(True)).all()

            # 为每个用户创建通知
            for user in active_users:
                # 检查是否已存在相同的通知
                existing_notification = (
                    self.db.query(Notification)
                    .filter(
                        and_(
                            Notification.recipient_id == user.id,
                            Notification.related_entity_id == contract.id,
                            Notification.related_entity_type == "contract",
                            Notification.type == notification_type,
                            Notification.is_read.is_(False),
                        )
                    )
                    .first()
                )

                if not existing_notification:
                    # 使用统一方法创建通知并推送企业微信
                    self._create_and_send_notification(
                        recipient_id=user.id,
                        notification_type=notification_type,
                        priority=priority,
                        title=title,
                        content=content,
                        related_entity_type="contract",
                        related_entity_id=contract.id,
                    )

        self.db.commit()
        return len(expiring_contracts)

    def check_payment_overdue(self) -> int:
        """
        检查付款逾期

        查找所有逾期未支付的租金台账记录，生成逾期提醒通知

        Returns:
            int: 创建的通知数量
        """
        today = date.today()

        # 查找逾期未支付的台账记录
        overdue_ledgers = (
            self.db.query(RentLedger)
            .filter(
                and_(
                    RentLedger.payment_status.in_([PaymentStatus.UNPAID, PaymentStatus.PARTIAL]),
                    RentLedger.due_date < today,  # 应缴日期已过
                    RentLedger.data_status == DataStatusValues.ASSET_NORMAL,
                )
            )
            .all()
        )

        notifications_created = 0

        for ledger in overdue_ledgers:
            # 计算逾期天数
            # due_date is Mapped[datetime] but stored as Date, convert to date for subtraction
            due_date_val: date | datetime = ledger.due_date
            if isinstance(due_date_val, datetime):
                due_date_val = due_date_val.date()
            days_overdue = (today - due_date_val).days

            # 确定优先级
            priority: str
            if days_overdue >= 30:
                priority = NotificationPriority.URGENT
                title = f"租金严重逾期（{days_overdue}天）"
            elif days_overdue >= 7:
                priority = NotificationPriority.HIGH
                title = f"租金逾期（{days_overdue}天）"
            else:
                priority = NotificationPriority.NORMAL
                title = f"租金逾期（{days_overdue}天）"

            contract_number = getattr(ledger.contract, "contract_number", "")
            tenant_name = getattr(ledger.contract, "tenant_name", "")
            content = (
                f"合同 {contract_number} "
                f"（{tenant_name}）的{ledger.year_month}月租金 "
                f"应收{ledger.due_amount}元，逾期{days_overdue}天未支付"
            )

            # 为所有活跃用户创建通知
            active_users = self.db.query(User).filter(User.is_active.is_(True)).all()

            for user in active_users:
                # 检查是否已存在相同的通知
                existing = (
                    self.db.query(Notification)
                    .filter(
                        and_(
                            Notification.recipient_id == user.id,
                            Notification.related_entity_type == "rent_ledger",
                            Notification.related_entity_id == ledger.id,
                            Notification.type == NotificationType.PAYMENT_OVERDUE,
                            Notification.created_at >= today,  # 今天已创建过
                        )
                    )
                    .first()
                )

                if not existing:
                    # 使用统一方法创建通知并推送企业微信
                    self._create_and_send_notification(
                        recipient_id=user.id,
                        notification_type=NotificationType.PAYMENT_OVERDUE,
                        priority=priority,
                        title=title,
                        content=content,
                        related_entity_type="rent_ledger",
                        related_entity_id=ledger.id,
                    )
                    notifications_created += 1

        self.db.commit()
        return notifications_created

    def check_payment_due_soon(self, days_ahead: int = 7) -> int:
        """
        检查即将到期的付款

        Args:
            days_ahead: 提前多少天提醒，默认7天

        Returns:
            int: 创建的通知数量
        """
        today = date.today()
        warning_date = today + timedelta(days=days_ahead)

        # 查找即将到期且未支付的台账记录
        due_soon_ledgers = (
            self.db.query(RentLedger)
            .filter(
                and_(
                    RentLedger.payment_status == PaymentStatus.UNPAID,
                    RentLedger.due_date <= warning_date,
                    RentLedger.due_date >= today,
                    RentLedger.data_status == DataStatusValues.ASSET_NORMAL,
                )
            )
            .all()
        )

        notifications_created = 0

        for ledger in due_soon_ledgers:
            # 计算剩余天数
            # due_date is Mapped[datetime] but stored as Date, convert to date for subtraction
            due_date_val: date | datetime = ledger.due_date
            if isinstance(due_date_val, datetime):
                due_date_val = due_date_val.date()
            days_remaining = (due_date_val - today).days

            # 确定优先级
            priority: str
            if days_remaining == 0:
                priority = NotificationPriority.HIGH
                title = "租金今日到期"
            elif days_remaining <= 3:
                priority = NotificationPriority.HIGH
                title = f"租金即将到期（{days_remaining}天）"
            else:
                priority = NotificationPriority.NORMAL
                title = f"租金即将到期（{days_remaining}天）"

            contract_number = getattr(ledger.contract, "contract_number", "")
            tenant_name = getattr(ledger.contract, "tenant_name", "")
            content = (
                f"合同 {contract_number} "
                f"（{tenant_name}）的{ledger.year_month}月租金 "
                f"应收{ledger.due_amount}元，将于{days_remaining}天后到期"
            )

            # 为所有活跃用户创建通知
            active_users = self.db.query(User).filter(User.is_active.is_(True)).all()

            for user in active_users:
                # 检查是否已存在相同的通知
                existing = (
                    self.db.query(Notification)
                    .filter(
                        and_(
                            Notification.recipient_id == user.id,
                            Notification.related_entity_type == "rent_ledger",
                            Notification.related_entity_id == ledger.id,
                            Notification.type == NotificationType.PAYMENT_DUE,
                            Notification.created_at >= today,
                        )
                    )
                    .first()
                )

                if not existing:
                    # 使用统一方法创建通知并推送企业微信
                    self._create_and_send_notification(
                        recipient_id=user.id,
                        notification_type=NotificationType.PAYMENT_DUE,
                        priority=priority,
                        title=title,
                        content=content,
                        related_entity_type="rent_ledger",
                        related_entity_id=ledger.id,
                    )
                    notifications_created += 1

        self.db.commit()
        return notifications_created


def run_notification_tasks() -> dict[str, Any]:
    """运行所有通知任务"""
    db = next(get_db())
    try:
        service = NotificationSchedulerService(db)

        # 检查合同到期
        expiring_count = service.check_contract_expiry(days_ahead=30)

        # 检查付款逾期
        overdue_count = service.check_payment_overdue()

        # 检查即将到期的付款
        due_count = service.check_payment_due_soon(days_ahead=7)

        return {
            "expiring_contracts": expiring_count,
            "overdue_payments": overdue_count,
            "due_payments": due_count,
            "timestamp": datetime.now().isoformat(),
        }
    finally:
        db.close()


if __name__ == "__main__":
    # 测试运行
    result = run_notification_tasks()
    logger.info(f"通知任务执行结果: {result}")
