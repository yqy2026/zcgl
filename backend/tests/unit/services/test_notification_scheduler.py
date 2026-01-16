"""
Unit Tests for Notification Scheduler Service

Tests for the notification scheduler that scans for:
- Contract expiry warnings
- Payment overdue reminders (future)
- Payment due reminders (future)

Author: V2.0 Test Suite
Date: 2026-01-08
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from src.models.auth import User
from src.models.notification import Notification, NotificationPriority, NotificationType
from src.models.rent_contract import ContractType, PaymentCycle, RentContract
from src.services.notification.scheduler import NotificationSchedulerService

# ==================== Fixtures ====================


@pytest.fixture(autouse=True)
def clean_database(test_db: Session):
    """Clean database before and after each test to ensure isolation"""
    # Clean before test
    test_db.query(Notification).delete()
    test_db.query(RentContract).delete()
    test_db.query(User).delete()
    test_db.commit()
    yield
    # Clean after test
    test_db.query(Notification).delete()
    test_db.query(RentContract).delete()
    test_db.query(User).delete()
    test_db.commit()


@pytest.fixture
def active_user(test_db: Session):
    """Create an active test user with unique ID"""
    from src.services.core.password_service import PasswordService

    pwd_service = PasswordService()
    unique_id = str(uuid.uuid4())[:8]
    user = User(
        id=f"user_{unique_id}",
        username=f"testuser_{unique_id}",
        email=f"test_{unique_id}@example.com",
        full_name="测试用户",
        password_hash=pwd_service.get_password_hash("testpass123"),
        is_active=True,
    )
    test_db.add(user)
    test_db.flush()
    yield user
    # 清理
    test_db.rollback()


@pytest.fixture
def expiring_contract_today(test_db: Session):
    """Contract expiring today with unique ID"""
    unique_id = str(uuid.uuid4())[:8]
    contract = RentContract(
        id=f"contract_today_{unique_id}",
        contract_number=f"EXP{unique_id}",
        contract_type=ContractType.LEASE_DOWNSTREAM,
        tenant_name=f"测试租户A_{unique_id}",
        ownership_id="ownership_001",
        sign_date=date.today() - timedelta(days=365),
        start_date=date.today() - timedelta(days=365),
        end_date=date.today(),
        contract_status="有效",
        payment_cycle=PaymentCycle.MONTHLY,
        total_deposit=Decimal("10000"),
    )
    test_db.add(contract)
    test_db.flush()
    yield contract
    # 清理
    test_db.rollback()


@pytest.fixture
def expiring_contract_7days(test_db: Session):
    """Contract expiring in 7 days with unique ID"""
    unique_id = str(uuid.uuid4())[:8]
    contract = RentContract(
        id=f"contract_7days_{unique_id}",
        contract_number=f"EXP007_{unique_id}",
        contract_type=ContractType.LEASE_DOWNSTREAM,
        tenant_name=f"测试租户B_{unique_id}",
        ownership_id="ownership_001",
        sign_date=date.today() - timedelta(days=358),
        start_date=date.today() - timedelta(days=358),
        end_date=date.today() + timedelta(days=7),
        contract_status="有效",
        payment_cycle=PaymentCycle.MONTHLY,
        total_deposit=Decimal("15000"),
    )
    test_db.add(contract)
    test_db.flush()
    yield contract
    # 清理
    test_db.rollback()


@pytest.fixture
def expiring_contract_30days(test_db: Session):
    """Contract expiring in 30 days with unique ID"""
    unique_id = str(uuid.uuid4())[:8]
    contract = RentContract(
        id=f"contract_30days_{unique_id}",
        contract_number=f"EXP030_{unique_id}",
        contract_type=ContractType.LEASE_UPSTREAM,
        tenant_name=f"测试权属方_{unique_id}",
        ownership_id="ownership_001",
        sign_date=date.today() - timedelta(days=335),
        start_date=date.today() - timedelta(days=335),
        end_date=date.today() + timedelta(days=30),
        contract_status="有效",
        payment_cycle=PaymentCycle.QUARTERLY,
        total_deposit=Decimal("20000"),
    )
    test_db.add(contract)
    test_db.flush()
    yield contract
    # 清理
    test_db.rollback()


# ==================== Contract Expiry Tests ====================


class TestContractExpiryNotifications:
    """Test contract expiry notification generation"""

    def test_contract_expiring_today_creates_urgent_notification(
        self, test_db: Session, active_user: User, expiring_contract_today: RentContract
    ):
        """TC-NOT-001: Contract expiring today generates URGENT notification"""
        scheduler = NotificationSchedulerService(test_db)

        # Run expiry check
        scheduler.check_contract_expiry(days_ahead=30)

        # Verify notification created
        notifications = (
            test_db.query(Notification)
            .filter(
                Notification.recipient_id == active_user.id,
                Notification.related_entity_id == expiring_contract_today.id,
            )
            .all()
        )

        assert len(notifications) == 1
        notification = notifications[0]
        assert notification.type == NotificationType.CONTRACT_EXPIRED
        assert notification.priority == NotificationPriority.URGENT
        assert "已到期" in notification.title
        assert expiring_contract_today.contract_number in notification.content
        assert not notification.is_read

    def test_contract_expiring_in_7days_creates_urgent_notification(
        self, test_db: Session, active_user: User, expiring_contract_7days: RentContract
    ):
        """TC-NOT-002: Contract expiring in 7 days generates URGENT notification"""
        scheduler = NotificationSchedulerService(test_db)

        scheduler.check_contract_expiry(days_ahead=30)

        notifications = (
            test_db.query(Notification)
            .filter(
                Notification.recipient_id == active_user.id,
                Notification.related_entity_id == expiring_contract_7days.id,
            )
            .all()
        )

        assert len(notifications) == 1
        notification = notifications[0]
        assert notification.type == NotificationType.CONTRACT_EXPIRING
        assert notification.priority == NotificationPriority.URGENT
        assert "7天" in notification.title

    def test_contract_expiring_in_30days_creates_normal_notification(
        self,
        test_db: Session,
        active_user: User,
        expiring_contract_30days: RentContract,
    ):
        """TC-NOT-003: Contract expiring in 30 days generates NORMAL notification"""
        scheduler = NotificationSchedulerService(test_db)

        scheduler.check_contract_expiry(days_ahead=30)

        notifications = (
            test_db.query(Notification)
            .filter(
                Notification.recipient_id == active_user.id,
                Notification.related_entity_id == expiring_contract_30days.id,
            )
            .all()
        )

        assert len(notifications) == 1
        notification = notifications[0]
        assert notification.type == NotificationType.CONTRACT_EXPIRING
        assert notification.priority == NotificationPriority.NORMAL
        assert "30天" in notification.title

    def test_expired_contract_not_checked(self, test_db: Session, active_user: User):
        """TC-NOT-004: Already expired contracts are not checked"""
        # Create expired contract
        expired_contract = RentContract(
            id="contract_expired",
            contract_number="EXP_OLD",
            contract_type=ContractType.LEASE_DOWNSTREAM,
            tenant_name="已过期租户",
            ownership_id="ownership_001",
            sign_date=date.today() - timedelta(days=400),
            start_date=date.today() - timedelta(days=400),
            end_date=date.today() - timedelta(days=10),  # 10天前已过期
            contract_status="有效",
            payment_cycle=PaymentCycle.MONTHLY,
        )
        test_db.add(expired_contract)
        test_db.commit()

        scheduler = NotificationSchedulerService(test_db)
        scheduler.check_contract_expiry(days_ahead=30)

        # Should not create notification for expired contract
        notifications = (
            test_db.query(Notification)
            .filter(Notification.related_entity_id == expired_contract.id)
            .all()
        )

        assert len(notifications) == 0

    def test_future_contract_beyond_warning_period(
        self, test_db: Session, active_user: User
    ):
        """TC-NOT-005: Contracts beyond warning period don't generate notifications"""
        # Create contract expiring in 60 days
        future_contract = RentContract(
            id="contract_future",
            contract_number="FUTURE",
            contract_type=ContractType.LEASE_DOWNSTREAM,
            tenant_name="未来租户",
            ownership_id="ownership_001",
            sign_date=date.today(),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=60),  # 60天后
            contract_status="有效",
            payment_cycle=PaymentCycle.MONTHLY,
        )
        test_db.add(future_contract)
        test_db.commit()

        scheduler = NotificationSchedulerService(test_db)
        scheduler.check_contract_expiry(days_ahead=30)

        # Should not create notification
        notifications = (
            test_db.query(Notification)
            .filter(Notification.related_entity_id == future_contract.id)
            .all()
        )

        assert len(notifications) == 0


# ==================== Duplicate Prevention Tests ====================


class TestDuplicatePrevention:
    """Test that duplicate notifications are prevented"""

    def test_no_duplicate_notification_for_same_contract(
        self, test_db: Session, active_user: User, expiring_contract_7days: RentContract
    ):
        """TC-NOT-006: Running scheduler twice doesn't create duplicate notifications"""
        scheduler = NotificationSchedulerService(test_db)

        # Run first time
        scheduler.check_contract_expiry(days_ahead=30)

        # Run second time
        scheduler.check_contract_expiry(days_ahead=30)

        # Should still have only one notification
        notifications = (
            test_db.query(Notification)
            .filter(
                Notification.recipient_id == active_user.id,
                Notification.related_entity_id == expiring_contract_7days.id,
            )
            .all()
        )

        assert len(notifications) == 1

    def test_different_users_receive_separate_notifications(
        self, test_db: Session, expiring_contract_7days: RentContract
    ):
        """TC-NOT-007: Each active user receives their own notification"""
        from src.services.core.password_service import PasswordService

        pwd_service = PasswordService()
        # Create two active users
        user1 = User(
            id="user_1",
            username="user1",
            email="user1@example.com",
            full_name="User One",
            password_hash=pwd_service.get_password_hash("pass123"),
            is_active=True,
        )
        user2 = User(
            id="user_2",
            username="user2",
            email="user2@example.com",
            full_name="User Two",
            password_hash=pwd_service.get_password_hash("pass123"),
            is_active=True,
        )
        test_db.add_all([user1, user2])
        test_db.commit()

        scheduler = NotificationSchedulerService(test_db)
        scheduler.check_contract_expiry(days_ahead=30)

        # Each user should have their own notification
        user1_notifications = (
            test_db.query(Notification)
            .filter(
                Notification.recipient_id == user1.id,
            )
            .all()
        )

        user2_notifications = (
            test_db.query(Notification)
            .filter(
                Notification.recipient_id == user2.id,
            )
            .all()
        )

        assert len(user1_notifications) == 1
        assert len(user2_notifications) == 1
        assert user1_notifications[0].id != user2_notifications[0].id


# ==================== Inactive User Tests ====================


class TestInactiveUserFiltering:
    """Test that inactive users don't receive notifications"""

    def test_inactive_users_do_not_receive_notifications(
        self, test_db: Session, expiring_contract_7days: RentContract
    ):
        """TC-NOT-008: Inactive users are excluded from notifications"""
        from src.services.core.password_service import PasswordService

        pwd_service = PasswordService()
        # Create inactive user
        inactive_user = User(
            id="inactive_user",
            username="inactive",
            email="inactive@example.com",
            full_name="Inactive User",
            password_hash=pwd_service.get_password_hash("pass123"),
            is_active=False,  # Inactive
        )
        test_db.add(inactive_user)
        test_db.commit()

        scheduler = NotificationSchedulerService(test_db)
        scheduler.check_contract_expiry(days_ahead=30)

        # Inactive user should not receive notification
        notifications = (
            test_db.query(Notification)
            .filter(
                Notification.recipient_id == inactive_user.id,
            )
            .all()
        )

        assert len(notifications) == 0


# ==================== Edge Cases Tests ====================


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_contract_with_invalid_status_skipped(
        self, test_db: Session, active_user: User
    ):
        """TC-NOT-009: Contracts with non-'有效' status are skipped"""
        contract = RentContract(
            id="contract_terminated",
            contract_number="TERM001",
            contract_type=ContractType.LEASE_DOWNSTREAM,
            tenant_name="已终止租户",
            ownership_id="ownership_001",
            sign_date=date.today() - timedelta(days=100),
            start_date=date.today() - timedelta(days=100),
            end_date=date.today() + timedelta(days=7),
            contract_status="已终止",  # Not '有效'
            payment_cycle=PaymentCycle.MONTHLY,
        )
        test_db.add(contract)
        test_db.commit()

        scheduler = NotificationSchedulerService(test_db)
        scheduler.check_contract_expiry(days_ahead=30)

        # Should not create notification for terminated contract
        notifications = (
            test_db.query(Notification)
            .filter(Notification.related_entity_id == contract.id)
            .all()
        )

        assert len(notifications) == 0

    def test_no_active_users_no_notifications_created(
        self, test_db: Session, expiring_contract_7days: RentContract
    ):
        """TC-NOT-010: No notifications created when there are no active users"""
        # Ensure no active users (fixture creates one, so we need to handle this)
        test_db.query(User).delete()
        test_db.commit()

        scheduler = NotificationSchedulerService(test_db)
        scheduler.check_contract_expiry(days_ahead=30)

        # Should not create any notifications
        notifications = test_db.query(Notification).all()
        assert len(notifications) == 0
