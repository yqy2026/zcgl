"""
Integration Tests for Notification Scheduler Service (Async)

Tests for the notification scheduler that scans for:
- Contract expiry warnings
- Payment overdue reminders (future)
- Payment due reminders (future)
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from src import database as database
from src.core.enums import ContractStatus
from src.models.auth import User
from src.models.notification import Notification, NotificationPriority, NotificationType
from src.models.ownership import Ownership
from src.models.rent_contract import ContractType, PaymentCycle, RentContract
from src.services.notification.scheduler import NotificationSchedulerService

pytestmark = pytest.mark.asyncio


# ==================== Fixtures ====================


@pytest.fixture
async def async_db():
    async_engine = create_async_engine(
        database.get_async_database_url(),
        echo=False,
        poolclass=NullPool,
    )
    async with async_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
            await async_engine.dispose()


@pytest.fixture(autouse=True)
async def ensure_ownership(async_db):
    ownership = await async_db.get(Ownership, "ownership_001")
    if ownership is None:
        async_db.add(
            Ownership(
                id="ownership_001",
                name="通知测试权属方",
                code="OWN-NOTIFY-001",
            )
        )
        await async_db.flush()
    yield


@pytest.fixture
async def active_user(async_db):
    """Create an active test user with unique ID"""
    from src.services.core.password_service import PasswordService

    pwd_service = PasswordService()
    unique_id = str(uuid.uuid4())[:8]
    user = User(
        id=f"user_{unique_id}",
        username=f"testuser_{unique_id}",
        email=f"test_{unique_id}@example.com",
        phone=f"138{unique_id[:8]}",
        full_name="测试用户",
        password_hash=pwd_service.get_password_hash("testpass123"),
        is_active=True,
    )
    async_db.add(user)
    await async_db.flush()
    yield user


@pytest.fixture
async def expiring_contract_today(async_db):
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
        contract_status=ContractStatus.ACTIVE.value,
        payment_cycle=PaymentCycle.MONTHLY,
        total_deposit=Decimal("10000"),
    )
    async_db.add(contract)
    await async_db.flush()
    yield contract


@pytest.fixture
async def expiring_contract_7days(async_db):
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
        contract_status=ContractStatus.ACTIVE.value,
        payment_cycle=PaymentCycle.MONTHLY,
        total_deposit=Decimal("15000"),
    )
    async_db.add(contract)
    await async_db.flush()
    yield contract


@pytest.fixture
async def expiring_contract_30days(async_db):
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
        contract_status=ContractStatus.ACTIVE.value,
        payment_cycle=PaymentCycle.QUARTERLY,
        total_deposit=Decimal("20000"),
    )
    async_db.add(contract)
    await async_db.flush()
    yield contract


# ==================== Contract Expiry Tests ====================


class TestContractExpiryNotifications:
    async def test_contract_expiring_today_creates_urgent_notification(
        self, async_db, active_user, expiring_contract_today
    ):
        scheduler = NotificationSchedulerService(async_db)
        await scheduler.check_contract_expiry(days_ahead=30)

        result = await async_db.execute(
            select(Notification).where(
                Notification.recipient_id == active_user.id,
                Notification.related_entity_id == expiring_contract_today.id,
            )
        )
        notifications = list(result.scalars().all())

        assert len(notifications) == 1
        notification = notifications[0]
        assert notification.type == NotificationType.CONTRACT_EXPIRED
        assert notification.priority == NotificationPriority.URGENT
        assert "已到期" in notification.title
        assert expiring_contract_today.contract_number in notification.content
        assert not notification.is_read

    async def test_contract_expiring_in_7days_creates_urgent_notification(
        self, async_db, active_user, expiring_contract_7days
    ):
        scheduler = NotificationSchedulerService(async_db)
        await scheduler.check_contract_expiry(days_ahead=30)

        result = await async_db.execute(
            select(Notification).where(
                Notification.recipient_id == active_user.id,
                Notification.related_entity_id == expiring_contract_7days.id,
            )
        )
        notifications = list(result.scalars().all())

        assert len(notifications) == 1
        notification = notifications[0]
        assert notification.type == NotificationType.CONTRACT_EXPIRING
        assert notification.priority == NotificationPriority.URGENT
        assert "7天" in notification.title

    async def test_contract_expiring_in_30days_creates_normal_notification(
        self, async_db, active_user, expiring_contract_30days
    ):
        scheduler = NotificationSchedulerService(async_db)
        await scheduler.check_contract_expiry(days_ahead=30)

        result = await async_db.execute(
            select(Notification).where(
                Notification.recipient_id == active_user.id,
                Notification.related_entity_id == expiring_contract_30days.id,
            )
        )
        notifications = list(result.scalars().all())

        assert len(notifications) == 1
        notification = notifications[0]
        assert notification.type == NotificationType.CONTRACT_EXPIRING
        assert notification.priority == NotificationPriority.NORMAL
        assert "30天" in notification.title

    async def test_expired_contract_not_checked(self, async_db, active_user):
        expired_contract = RentContract(
            id="contract_expired",
            contract_number="EXP_OLD",
            contract_type=ContractType.LEASE_DOWNSTREAM,
            tenant_name="已过期租户",
            ownership_id="ownership_001",
            sign_date=date.today() - timedelta(days=400),
            start_date=date.today() - timedelta(days=400),
            end_date=date.today() - timedelta(days=10),
            contract_status=ContractStatus.ACTIVE.value,
            payment_cycle=PaymentCycle.MONTHLY,
        )
        async_db.add(expired_contract)
        await async_db.commit()

        scheduler = NotificationSchedulerService(async_db)
        await scheduler.check_contract_expiry(days_ahead=30)

        result = await async_db.execute(
            select(Notification).where(
                Notification.related_entity_id == expired_contract.id
            )
        )
        notifications = list(result.scalars().all())

        assert len(notifications) == 0

    async def test_future_contract_beyond_warning_period(
        self, async_db, active_user
    ):
        future_contract = RentContract(
            id="contract_future",
            contract_number="FUTURE",
            contract_type=ContractType.LEASE_DOWNSTREAM,
            tenant_name="未来租户",
            ownership_id="ownership_001",
            sign_date=date.today(),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=60),
            contract_status=ContractStatus.ACTIVE.value,
            payment_cycle=PaymentCycle.MONTHLY,
        )
        async_db.add(future_contract)
        await async_db.commit()

        scheduler = NotificationSchedulerService(async_db)
        await scheduler.check_contract_expiry(days_ahead=30)

        result = await async_db.execute(
            select(Notification).where(
                Notification.related_entity_id == future_contract.id
            )
        )
        notifications = list(result.scalars().all())

        assert len(notifications) == 0


# ==================== Duplicate Prevention Tests ====================


class TestDuplicatePrevention:
    async def test_no_duplicate_notification_for_same_contract(
        self, async_db, active_user, expiring_contract_7days
    ):
        scheduler = NotificationSchedulerService(async_db)

        await scheduler.check_contract_expiry(days_ahead=30)
        await scheduler.check_contract_expiry(days_ahead=30)

        result = await async_db.execute(
            select(Notification).where(
                Notification.recipient_id == active_user.id,
                Notification.related_entity_id == expiring_contract_7days.id,
            )
        )
        notifications = list(result.scalars().all())

        assert len(notifications) == 1

    async def test_different_users_receive_separate_notifications(
        self, async_db, expiring_contract_7days
    ):
        from src.services.core.password_service import PasswordService

        pwd_service = PasswordService()
        user1 = User(
            id="user_1",
            username="user1",
            email="user1@example.com",
            phone=f"user1_{uuid.uuid4().hex[:8]}",
            full_name="User One",
            password_hash=pwd_service.get_password_hash("pass123"),
            is_active=True,
        )
        user2 = User(
            id="user_2",
            username="user2",
            email="user2@example.com",
            phone=f"user2_{uuid.uuid4().hex[:8]}",
            full_name="User Two",
            password_hash=pwd_service.get_password_hash("pass123"),
            is_active=True,
        )
        async_db.add_all([user1, user2])
        await async_db.commit()

        scheduler = NotificationSchedulerService(async_db)
        await scheduler.check_contract_expiry(days_ahead=30)

        result1 = await async_db.execute(
            select(Notification).where(Notification.recipient_id == user1.id)
        )
        result2 = await async_db.execute(
            select(Notification).where(Notification.recipient_id == user2.id)
        )
        user1_notifications = list(result1.scalars().all())
        user2_notifications = list(result2.scalars().all())

        assert len(user1_notifications) == 1
        assert len(user2_notifications) == 1
        assert user1_notifications[0].id != user2_notifications[0].id


# ==================== Inactive User Tests ====================


class TestInactiveUserFiltering:
    async def test_inactive_users_do_not_receive_notifications(
        self, async_db, expiring_contract_7days
    ):
        from src.services.core.password_service import PasswordService

        pwd_service = PasswordService()
        inactive_user = User(
            id="inactive_user",
            username="inactive",
            email="inactive@example.com",
            phone=f"inactive_{uuid.uuid4().hex[:8]}",
            full_name="Inactive User",
            password_hash=pwd_service.get_password_hash("pass123"),
            is_active=False,
        )
        async_db.add(inactive_user)
        await async_db.commit()

        scheduler = NotificationSchedulerService(async_db)
        await scheduler.check_contract_expiry(days_ahead=30)

        result = await async_db.execute(
            select(Notification).where(Notification.recipient_id == inactive_user.id)
        )
        notifications = list(result.scalars().all())

        assert len(notifications) == 0


# ==================== Edge Cases Tests ====================


class TestEdgeCases:
    async def test_contract_with_invalid_status_skipped(self, async_db, active_user):
        contract = RentContract(
            id="contract_terminated",
            contract_number="TERM001",
            contract_type=ContractType.LEASE_DOWNSTREAM,
            tenant_name="已终止租户",
            ownership_id="ownership_001",
            sign_date=date.today() - timedelta(days=100),
            start_date=date.today() - timedelta(days=100),
            end_date=date.today() + timedelta(days=7),
            contract_status=ContractStatus.TERMINATED.value,
            payment_cycle=PaymentCycle.MONTHLY,
        )
        async_db.add(contract)
        await async_db.commit()

        scheduler = NotificationSchedulerService(async_db)
        await scheduler.check_contract_expiry(days_ahead=30)

        result = await async_db.execute(
            select(Notification).where(Notification.related_entity_id == contract.id)
        )
        notifications = list(result.scalars().all())

        assert len(notifications) == 0

    async def test_no_active_users_no_notifications_created(
        self, async_db, expiring_contract_7days
    ):
        await async_db.execute(update(User).values(is_active=False))
        await async_db.commit()

        scheduler = NotificationSchedulerService(async_db)
        await scheduler.check_contract_expiry(days_ahead=30)

        result = await async_db.execute(select(Notification))
        notifications = list(result.scalars().all())
        assert len(notifications) == 0
