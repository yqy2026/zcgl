"""
通知定时任务服务

负责扫描合同到期、付款逾期等场景，并生成通知
支持企业微信推送
"""

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.contract import contract_crud
from ...crud.contract_group import contract_group_crud
from ...database import async_session_scope

logger = logging.getLogger(__name__)
from ...models.notification import Notification, NotificationPriority, NotificationType
from .notification_service import notification_service
from .wecom_service import wecom_service


def _resolve_tenant_name(contract: Any) -> str:
    lease_detail = getattr(contract, "lease_detail", None)
    tenant_name = getattr(lease_detail, "tenant_name", None)
    if tenant_name:
        return str(tenant_name)

    lessee_party = getattr(contract, "lessee_party", None)
    party_name = getattr(lessee_party, "name", None)
    return str(party_name or "")


class NotificationSchedulerService:
    """通知定时任务服务"""

    def __init__(self, db: AsyncSession):
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

            await self.db.commit()
            return success

        except Exception as e:
            # 记录错误但不影响主流程
            notification.wecom_send_error = f"企业微信发送异常: {str(e)}"
            await self.db.commit()
            return False

    async def _create_and_send_notification(
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
        await self.db.flush()  # 获取 ID

        # 如果启用了企业微信，异步推送
        if self.wecom_enabled:
            try:
                await self._send_wecom_notification(notification)
            except Exception as e:
                # 推送失败不影响通知创建
                notification.wecom_send_error = f"企业微信推送失败: {str(e)}"

        return notification

    async def check_contract_expiry(self, days_ahead: int = 30) -> int:
        """
        检查合同到期

        Args:
            days_ahead: 提前多少天提醒，默认30天

        Returns:
            int: 即将到期的合同数量
        """
        today = date.today()
        warning_date = today + timedelta(days=days_ahead)

        expiring_contracts = await contract_crud.get_expiring_contracts_async(
            self.db,
            today=today,
            warning_date=warning_date,
        )

        active_users = await notification_service.list_active_users_async(self.db)
        active_user_ids = [str(user.id) for user in active_users]
        contract_alerts: list[dict[str, str]] = []
        contract_ids_by_type: dict[str, list[str]] = {}

        for contract in expiring_contracts:
            # 计算剩余天数
            # end_date is Mapped[datetime] but stored as Date, convert to date for subtraction
            raw_end_date = contract.effective_to
            if raw_end_date is None:
                continue
            if isinstance(raw_end_date, datetime):
                end_date_val = raw_end_date.date()
            else:
                end_date_val = raw_end_date
            days_remaining = (end_date_val - today).days
            tenant_name = _resolve_tenant_name(contract)

            # 确定通知类型和优先级
            notification_type: str
            priority: str
            if days_remaining == 0:
                notification_type = NotificationType.CONTRACT_EXPIRED
                priority = NotificationPriority.URGENT
                title = "合同已到期"
                content = f"合同 {contract.contract_number}（{tenant_name}）已于今日到期，请及时处理"
            elif days_remaining <= 7:
                notification_type = NotificationType.CONTRACT_EXPIRING
                priority = NotificationPriority.URGENT
                title = f"合同即将到期（{days_remaining}天）"
                content = f"合同 {contract.contract_number}（{tenant_name}）将在{days_remaining}天后到期"
            elif days_remaining <= 15:
                notification_type = NotificationType.CONTRACT_EXPIRING
                priority = NotificationPriority.HIGH
                title = f"合同即将到期（{days_remaining}天）"
                content = f"合同 {contract.contract_number}（{tenant_name}）将在{days_remaining}天后到期"
            else:
                notification_type = NotificationType.CONTRACT_EXPIRING
                priority = NotificationPriority.NORMAL
                title = f"合同即将到期（{days_remaining}天）"
                content = f"合同 {contract.contract_number}（{tenant_name}）将在{days_remaining}天后到期"

            contract_id = str(contract.contract_id)
            contract_alerts.append(
                {
                    "contract_id": contract_id,
                    "notification_type": notification_type,
                    "priority": priority,
                    "title": title,
                    "content": content,
                }
            )
            contract_ids_by_type.setdefault(notification_type, []).append(contract_id)

        existing_pairs_by_type: dict[str, set[tuple[str, str]]] = {}
        for notification_type, contract_ids in contract_ids_by_type.items():
            existing_pairs_by_type[
                notification_type
            ] = await notification_service.find_existing_notification_pairs_async(
                self.db,
                recipient_ids=active_user_ids,
                related_entity_type="contract",
                related_entity_ids=contract_ids,
                notification_type=notification_type,
                require_unread=True,
            )

        # 为每个用户创建通知
        for contract_alert in contract_alerts:
            notification_type = contract_alert["notification_type"]
            contract_id = contract_alert["contract_id"]
            existing_pairs = existing_pairs_by_type.get(notification_type, set())
            for user in active_users:
                user_id = str(user.id)
                if (user_id, contract_id) not in existing_pairs:
                    # 使用统一方法创建通知并推送企业微信
                    await self._create_and_send_notification(
                        recipient_id=user_id,
                        notification_type=notification_type,
                        priority=contract_alert["priority"],
                        title=contract_alert["title"],
                        content=contract_alert["content"],
                        related_entity_type="contract",
                        related_entity_id=contract_id,
                    )
                    existing_pairs.add((user_id, contract_id))

        await self.db.commit()
        return len(expiring_contracts)

    async def check_payment_overdue(self) -> int:
        """
        检查付款逾期

        查找所有逾期未支付的租金台账记录，生成逾期提醒通知

        Returns:
            int: 创建的通知数量
        """
        today = date.today()

        overdue_ledgers = await contract_group_crud.get_overdue_with_contract_async(
            self.db,
            today=today,
        )

        notifications_created = 0
        active_users = await notification_service.list_active_users_async(self.db)
        active_user_ids = [str(user.id) for user in active_users]
        ledger_alerts: list[dict[str, str]] = []

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
            tenant_name = _resolve_tenant_name(ledger.contract)
            content = (
                f"合同 {contract_number} "
                f"（{tenant_name}）的{ledger.year_month}月租金 "
                f"应收{ledger.amount_due}元，逾期{days_overdue}天未支付"
            )

            ledger_alerts.append(
                {
                    "ledger_id": str(ledger.entry_id),
                    "priority": priority,
                    "title": title,
                    "content": content,
                }
            )

        existing_pairs = (
            await notification_service.find_existing_notification_pairs_async(
                self.db,
                recipient_ids=active_user_ids,
                related_entity_type="contract_ledger_entry",
                related_entity_ids=[alert["ledger_id"] for alert in ledger_alerts],
                notification_type=NotificationType.PAYMENT_OVERDUE,
                created_since=today,
            )
        )

        for ledger_alert in ledger_alerts:
            ledger_id = ledger_alert["ledger_id"]
            for user in active_users:
                user_id = str(user.id)
                if (user_id, ledger_id) not in existing_pairs:
                    # 使用统一方法创建通知并推送企业微信
                    await self._create_and_send_notification(
                        recipient_id=user_id,
                        notification_type=NotificationType.PAYMENT_OVERDUE,
                        priority=ledger_alert["priority"],
                        title=ledger_alert["title"],
                        content=ledger_alert["content"],
                        related_entity_type="contract_ledger_entry",
                        related_entity_id=ledger_id,
                    )
                    notifications_created += 1
                    existing_pairs.add((user_id, ledger_id))

        await self.db.commit()
        return notifications_created

    async def check_payment_due_soon(self, days_ahead: int = 7) -> int:
        """
        检查即将到期的付款

        Args:
            days_ahead: 提前多少天提醒，默认7天

        Returns:
            int: 创建的通知数量
        """
        today = date.today()
        warning_date = today + timedelta(days=days_ahead)

        due_soon_ledgers = await contract_group_crud.get_due_soon_with_contract_async(
            self.db,
            today=today,
            warning_date=warning_date,
        )

        notifications_created = 0
        active_users = await notification_service.list_active_users_async(self.db)
        active_user_ids = [str(user.id) for user in active_users]
        ledger_alerts: list[dict[str, str]] = []

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
            tenant_name = _resolve_tenant_name(ledger.contract)
            content = (
                f"合同 {contract_number} "
                f"（{tenant_name}）的{ledger.year_month}月租金 "
                f"应收{ledger.amount_due}元，将于{days_remaining}天后到期"
            )

            ledger_alerts.append(
                {
                    "ledger_id": str(ledger.entry_id),
                    "priority": priority,
                    "title": title,
                    "content": content,
                }
            )

        existing_pairs = (
            await notification_service.find_existing_notification_pairs_async(
                self.db,
                recipient_ids=active_user_ids,
                related_entity_type="contract_ledger_entry",
                related_entity_ids=[alert["ledger_id"] for alert in ledger_alerts],
                notification_type=NotificationType.PAYMENT_DUE,
                created_since=today,
            )
        )

        for ledger_alert in ledger_alerts:
            ledger_id = ledger_alert["ledger_id"]
            for user in active_users:
                user_id = str(user.id)
                if (user_id, ledger_id) not in existing_pairs:
                    # 使用统一方法创建通知并推送企业微信
                    await self._create_and_send_notification(
                        recipient_id=user_id,
                        notification_type=NotificationType.PAYMENT_DUE,
                        priority=ledger_alert["priority"],
                        title=ledger_alert["title"],
                        content=ledger_alert["content"],
                        related_entity_type="contract_ledger_entry",
                        related_entity_id=ledger_id,
                    )
                    notifications_created += 1
                    existing_pairs.add((user_id, ledger_id))

        await self.db.commit()
        return notifications_created


async def run_notification_tasks() -> dict[str, Any]:
    """运行所有通知任务"""
    async with async_session_scope() as db:
        service = NotificationSchedulerService(db)

        # 检查合同到期
        expiring_count = await service.check_contract_expiry(days_ahead=30)

        # 检查付款逾期
        overdue_count = await service.check_payment_overdue()

        # 检查即将到期的付款
        due_count = await service.check_payment_due_soon(days_ahead=7)

        return {
            "expiring_contracts": expiring_count,
            "overdue_payments": overdue_count,
            "due_payments": due_count,
            "timestamp": datetime.now().isoformat(),
        }


if __name__ == "__main__":
    # 测试运行
    result = asyncio.run(run_notification_tasks())
    logger.info(f"通知任务执行结果: {result}")
