"""
测试 NotificationSchedulerService（异步）
"""

from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.auth import User
from src.models.contract_group import Contract, ContractLedgerEntry
from src.models.notification import Notification, NotificationPriority, NotificationType
from src.services.notification.scheduler import (
    NotificationSchedulerService,
    run_notification_tasks,
)

pytestmark = pytest.mark.asyncio


def _result_with_scalars(values: list[object] | None = None) -> MagicMock:
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values or []
    result.scalars.return_value = scalars
    return result


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def scheduler_service(mock_db):
    return NotificationSchedulerService(mock_db)


@pytest.fixture
def mock_contract():
    contract = MagicMock(spec=Contract)
    contract.contract_id = "contract_123"
    contract.contract_number = "HT2024001"
    contract.lease_detail = MagicMock(tenant_name="测试租户")
    contract.lessee_party = MagicMock(name="测试租户")
    contract.status = "ACTIVE"
    contract.effective_to = date.today() + timedelta(days=15)
    return contract


@pytest.fixture
def mock_ledger():
    ledger = MagicMock(spec=ContractLedgerEntry)
    ledger.entry_id = "ledger_123"
    ledger.year_month = "2024-01"
    ledger.amount_due = 10000.0
    ledger.payment_status = "unpaid"
    ledger.due_date = date.today() - timedelta(days=5)
    ledger.contract = MagicMock(spec=Contract)
    ledger.contract.contract_number = "HT2024001"
    ledger.contract.lease_detail = MagicMock(tenant_name="测试租户")
    ledger.contract.lessee_party = MagicMock(name="测试租户")
    return ledger


# ============================================================================
# Init
# ============================================================================


class TestNotificationSchedulerServiceInit:
    async def test_initialization(self, mock_db):
        service = NotificationSchedulerService(mock_db)
        assert service.db == mock_db
        assert isinstance(service.wecom_enabled, bool)


# ============================================================================
# _send_wecom_notification
# ============================================================================


class TestSendWecomNotification:
    async def test_send_wecom_success(self, scheduler_service, mock_db):
        notification = MagicMock(spec=Notification)
        notification.id = "notif_123"
        notification.title = "测试通知"
        notification.content = "测试内容"

        with patch("src.services.notification.scheduler.wecom_service") as mock_wecom:
            mock_wecom.enabled = True
            scheduler_service.wecom_enabled = True
            mock_wecom.send_notification = AsyncMock(return_value=True)

            result = await scheduler_service._send_wecom_notification(notification)

            assert result is True
            assert notification.is_sent_wecom is True
            assert notification.wecom_sent_at is not None
            mock_db.commit.assert_awaited_once()

    async def test_send_wecom_disabled(self, scheduler_service):
        scheduler_service.wecom_enabled = False
        notification = MagicMock(spec=Notification)

        result = await scheduler_service._send_wecom_notification(notification)
        assert result is False

    async def test_send_wecom_api_failure(self, scheduler_service, mock_db):
        notification = MagicMock(spec=Notification)
        notification.id = "notif_123"
        notification.title = "测试通知"
        notification.content = "测试内容"

        with patch("src.services.notification.scheduler.wecom_service") as mock_wecom:
            mock_wecom.enabled = True
            scheduler_service.wecom_enabled = True
            mock_wecom.send_notification = AsyncMock(return_value=False)

            result = await scheduler_service._send_wecom_notification(notification)

            assert result is False
            assert notification.is_sent_wecom is False
            assert notification.wecom_send_error == "企业微信返回失败"
            mock_db.commit.assert_awaited_once()

    async def test_send_wecom_exception(self, scheduler_service, mock_db):
        notification = MagicMock(spec=Notification)
        notification.id = "notif_123"
        notification.title = "测试通知"
        notification.content = "测试内容"

        with patch("src.services.notification.scheduler.wecom_service") as mock_wecom:
            mock_wecom.enabled = True
            scheduler_service.wecom_enabled = True
            mock_wecom.send_notification = AsyncMock(
                side_effect=Exception("Network error")
            )

            result = await scheduler_service._send_wecom_notification(notification)

            assert result is False
            assert "企业微信发送异常" in notification.wecom_send_error
            mock_db.commit.assert_awaited_once()


# ============================================================================
# _create_and_send_notification
# ============================================================================


class TestCreateAndSendNotification:
    async def test_create_notification_without_wecom(self, scheduler_service, mock_db):
        scheduler_service.wecom_enabled = False

        notification = await scheduler_service._create_and_send_notification(
            recipient_id="user_123",
            notification_type=NotificationType.CONTRACT_EXPIRING,
            priority=NotificationPriority.NORMAL,
            title="测试标题",
            content="测试内容",
            related_entity_type="contract",
            related_entity_id="contract_123",
        )

        assert notification.recipient_id == "user_123"
        assert notification.type == NotificationType.CONTRACT_EXPIRING
        assert notification.title == "测试标题"
        assert notification.is_read is False
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    async def test_create_notification_wecom_exception(self, scheduler_service):
        scheduler_service.wecom_enabled = True

        with patch.object(
            scheduler_service,
            "_send_wecom_notification",
            new_callable=AsyncMock,
        ) as mock_send:
            mock_send.side_effect = Exception("Loop error")

            notification = await scheduler_service._create_and_send_notification(
                recipient_id="user_123",
                notification_type=NotificationType.CONTRACT_EXPIRING,
                priority=NotificationPriority.NORMAL,
                title="测试标题",
                content="测试内容",
                related_entity_type="contract",
                related_entity_id="contract_123",
            )

            assert "企业微信推送失败" in notification.wecom_send_error


# ============================================================================
# check_contract_expiry
# ============================================================================


class TestCheckContractExpiry:
    async def test_expiry_uses_new_contract_crud(self, scheduler_service, mock_contract):
        with (
            patch(
                "src.services.notification.scheduler.contract_crud.get_expiring_contracts_async",
                new_callable=AsyncMock,
                return_value=[mock_contract],
            ) as mock_get_expiring,
            patch(
                "src.services.notification.scheduler.notification_service"
            ) as mock_service,
            patch.object(
                scheduler_service, "_create_and_send_notification", new_callable=AsyncMock
            ),
        ):
            mock_service.list_active_users_async = AsyncMock(return_value=[])
            mock_service.find_existing_notification_pairs_async = AsyncMock(
                return_value=set()
            )

            result = await scheduler_service.check_contract_expiry(days_ahead=30)

        assert result == 1
        mock_get_expiring.assert_awaited_once()

    async def test_no_expiring_contracts(self, scheduler_service, mock_db):
        mock_db.execute = AsyncMock(return_value=_result_with_scalars([]))

        result = await scheduler_service.check_contract_expiry(days_ahead=30)

        assert result == 0
        mock_db.commit.assert_awaited_once()

    async def test_contract_expiring_today(self, scheduler_service, mock_db):
        contract = MagicMock(spec=Contract)
        contract.contract_id = "contract_123"
        contract.contract_number = "HT001"
        contract.lease_detail = MagicMock(tenant_name="租户A")
        contract.lessee_party = MagicMock(name="租户A")
        contract.effective_to = date.today()

        mock_db.execute = AsyncMock(return_value=_result_with_scalars([contract]))

        with patch(
            "src.services.notification.scheduler.notification_service"
        ) as mock_service:
            mock_service.list_active_users_async = AsyncMock(return_value=[])
            mock_service.find_existing_notification_pairs_async = AsyncMock(
                return_value=set()
            )
            with patch.object(
                scheduler_service, "_create_and_send_notification", new_callable=AsyncMock
            ) as mock_create:
                result = await scheduler_service.check_contract_expiry(days_ahead=30)

                assert result == 1
                mock_create.assert_not_awaited()

    async def test_duplicate_contract_notification_skipped(
        self, scheduler_service, mock_db, mock_contract
    ):
        mock_db.execute = AsyncMock(return_value=_result_with_scalars([mock_contract]))

        user = MagicMock(spec=User)
        user.id = "user_123"

        with patch(
            "src.services.notification.scheduler.notification_service"
        ) as mock_service:
            mock_service.list_active_users_async = AsyncMock(return_value=[user])
            mock_service.find_existing_notification_pairs_async = AsyncMock(
                return_value={(str(user.id), str(mock_contract.contract_id))}
            )

            with patch.object(
                scheduler_service, "_create_and_send_notification", new_callable=AsyncMock
            ) as mock_create:
                result = await scheduler_service.check_contract_expiry(days_ahead=30)

                assert result == 1
                mock_create.assert_not_awaited()


# ============================================================================
# check_payment_overdue
# ============================================================================


class TestCheckPaymentOverdue:
    async def test_overdue_uses_new_contract_ledger_crud(
        self, scheduler_service, mock_ledger
    ):
        with (
            patch(
                "src.services.notification.scheduler.contract_group_crud.get_overdue_with_contract_async",
                new_callable=AsyncMock,
                return_value=[mock_ledger],
            ) as mock_get_overdue,
            patch(
                "src.services.notification.scheduler.notification_service"
            ) as mock_service,
            patch.object(
                scheduler_service, "_create_and_send_notification", new_callable=AsyncMock
            ),
        ):
            mock_service.list_active_users_async = AsyncMock(return_value=[])
            mock_service.find_existing_notification_pairs_async = AsyncMock(
                return_value=set()
            )

            result = await scheduler_service.check_payment_overdue()

        assert result == 0
        mock_get_overdue.assert_awaited_once()
        assert (
            mock_service.find_existing_notification_pairs_async.await_args.kwargs[
                "related_entity_type"
            ]
            == "contract_ledger_entry"
        )

    async def test_no_overdue_payments(self, scheduler_service, mock_db):
        mock_db.execute = AsyncMock(return_value=_result_with_scalars([]))

        result = await scheduler_service.check_payment_overdue()
        assert result == 0

    async def test_payment_overdue_creates_notifications(
        self, scheduler_service, mock_db, mock_ledger
    ):
        mock_db.execute = AsyncMock(return_value=_result_with_scalars([mock_ledger]))

        with patch(
            "src.services.notification.scheduler.notification_service"
        ) as mock_service:
            mock_service.list_active_users_async = AsyncMock(return_value=[])
            mock_service.find_existing_notification_pairs_async = AsyncMock(
                return_value=set()
            )
            with patch.object(
                scheduler_service, "_create_and_send_notification", new_callable=AsyncMock
            ):
                result = await scheduler_service.check_payment_overdue()

                assert isinstance(result, int)

    async def test_duplicate_overdue_notification_skipped(
        self, scheduler_service, mock_db, mock_ledger
    ):
        mock_db.execute = AsyncMock(return_value=_result_with_scalars([mock_ledger]))

        user = MagicMock(spec=User)
        user.id = "user_123"

        with patch(
            "src.services.notification.scheduler.notification_service"
        ) as mock_service:
            mock_service.list_active_users_async = AsyncMock(return_value=[user])
            mock_service.find_existing_notification_pairs_async = AsyncMock(
                return_value={(str(user.id), str(mock_ledger.entry_id))}
            )

            with patch.object(
                scheduler_service, "_create_and_send_notification", new_callable=AsyncMock
            ) as mock_create:
                result = await scheduler_service.check_payment_overdue()

                assert result == 0
                mock_create.assert_not_awaited()


# ============================================================================
# check_payment_due_soon
# ============================================================================


class TestCheckPaymentDueSoon:
    async def test_due_soon_uses_new_contract_ledger_crud(
        self, scheduler_service, mock_ledger
    ):
        with (
            patch(
                "src.services.notification.scheduler.contract_group_crud.get_due_soon_with_contract_async",
                new_callable=AsyncMock,
                return_value=[mock_ledger],
            ) as mock_get_due_soon,
            patch(
                "src.services.notification.scheduler.notification_service"
            ) as mock_service,
            patch.object(
                scheduler_service, "_create_and_send_notification", new_callable=AsyncMock
            ),
        ):
            mock_service.list_active_users_async = AsyncMock(return_value=[])
            mock_service.find_existing_notification_pairs_async = AsyncMock(
                return_value=set()
            )

            result = await scheduler_service.check_payment_due_soon(days_ahead=7)

        assert result == 0
        mock_get_due_soon.assert_awaited_once()
        assert (
            mock_service.find_existing_notification_pairs_async.await_args.kwargs[
                "related_entity_type"
            ]
            == "contract_ledger_entry"
        )

    async def test_no_payments_due(self, scheduler_service, mock_db):
        mock_db.execute = AsyncMock(return_value=_result_with_scalars([]))

        result = await scheduler_service.check_payment_due_soon(days_ahead=7)
        assert result == 0

    async def test_payment_due_today(self, scheduler_service, mock_db, mock_ledger):
        mock_ledger.due_date = date.today()
        mock_db.execute = AsyncMock(return_value=_result_with_scalars([mock_ledger]))

        with patch(
            "src.services.notification.scheduler.notification_service"
        ) as mock_service:
            mock_service.list_active_users_async = AsyncMock(return_value=[])
            mock_service.find_existing_notification_pairs_async = AsyncMock(
                return_value=set()
            )
            with patch.object(
                scheduler_service, "_create_and_send_notification", new_callable=AsyncMock
            ):
                result = await scheduler_service.check_payment_due_soon(days_ahead=7)

                assert isinstance(result, int)


# ============================================================================
# run_notification_tasks
# ============================================================================


class TestRunNotificationTasks:
    async def test_run_all_tasks(self):
        mock_db = AsyncMock()

        @asynccontextmanager
        async def fake_scope():
            yield mock_db

        with patch(
            "src.services.notification.scheduler.async_session_scope",
            side_effect=fake_scope,
        ):
            with patch(
                "src.services.notification.scheduler.NotificationSchedulerService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service.check_contract_expiry = AsyncMock(return_value=5)
                mock_service.check_payment_overdue = AsyncMock(return_value=3)
                mock_service.check_payment_due_soon = AsyncMock(return_value=2)
                mock_service_class.return_value = mock_service

                result = await run_notification_tasks()

                assert result["expiring_contracts"] == 5
                assert result["overdue_payments"] == 3
                assert result["due_payments"] == 2
                assert "timestamp" in result

    async def test_run_tasks_exception_handling(self):
        mock_db = AsyncMock()

        @asynccontextmanager
        async def fake_scope():
            yield mock_db

        with patch(
            "src.services.notification.scheduler.async_session_scope",
            side_effect=fake_scope,
        ):
            with patch(
                "src.services.notification.scheduler.NotificationSchedulerService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_service.check_contract_expiry = AsyncMock(
                    side_effect=Exception("DB error")
                )
                mock_service_class.return_value = mock_service

                with pytest.raises(Exception, match="DB error"):
                    await run_notification_tasks()


# ============================================================================
# Edge Cases
# ============================================================================


class TestSchedulerEdgeCases:
    async def test_contract_with_datetime_end_date(self, scheduler_service, mock_db):
        contract = MagicMock(spec=Contract)
        end_datetime = datetime.combine(date.today(), datetime.min.time())
        contract.effective_to = end_datetime
        contract.contract_number = "HT001"
        contract.lease_detail = MagicMock(tenant_name="租户A")
        contract.lessee_party = MagicMock(name="租户A")
        contract.contract_id = "contract_123"

        mock_db.execute = AsyncMock(return_value=_result_with_scalars([contract]))

        with patch(
            "src.services.notification.scheduler.notification_service"
        ) as mock_service:
            mock_service.list_active_users_async = AsyncMock(return_value=[])
            mock_service.find_existing_notification_pairs_async = AsyncMock(
                return_value=set()
            )
            with patch.object(
                scheduler_service, "_create_and_send_notification", new_callable=AsyncMock
            ):
                result = await scheduler_service.check_contract_expiry(days_ahead=30)

                assert result == 1

    async def test_ledger_with_datetime_due_date(self, scheduler_service, mock_db):
        ledger = MagicMock(spec=ContractLedgerEntry)
        due_datetime = datetime.combine(
            date.today() - timedelta(days=5), datetime.min.time()
        )
        ledger.due_date = due_datetime
        ledger.payment_status = "unpaid"
        ledger.year_month = "2024-01"
        ledger.amount_due = 5000.0
        ledger.contract = MagicMock(spec=Contract)
        ledger.contract.contract_number = "HT001"
        ledger.contract.lease_detail = MagicMock(tenant_name="租户A")
        ledger.contract.lessee_party = MagicMock(name="租户A")

        mock_db.execute = AsyncMock(return_value=_result_with_scalars([ledger]))

        with patch(
            "src.services.notification.scheduler.notification_service"
        ) as mock_service:
            mock_service.list_active_users_async = AsyncMock(return_value=[])
            mock_service.find_existing_notification_pairs_async = AsyncMock(
                return_value=set()
            )
            with patch.object(
                scheduler_service, "_create_and_send_notification", new_callable=AsyncMock
            ):
                result = await scheduler_service.check_payment_overdue()

                assert isinstance(result, int)
