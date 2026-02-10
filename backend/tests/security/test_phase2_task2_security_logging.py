"""
Security Tests for Phase 2 Task 2 - Security Event Logging Integration

Tests for:
1. Permission denied event logging in middleware
2. Security alert threshold checking
3. /security/alerts/test endpoint
4. /security/events endpoint
5. Admin-only access control

Created: 2026-01-20
Task: Integrate Security Event Logging into Permission Middleware (Issue #5)
"""

from datetime import UTC

import pytest
from sqlalchemy.orm import Session

from src.models.security_event import SecurityEvent
from src.security.audit_logger import SecurityEventLogger, SecurityEventType


class AsyncSessionAdapter:
    """Async-compatible adapter for sync SQLAlchemy Session in tests."""

    def __init__(self, session: Session):
        self._session = session

    async def execute(self, *args, **kwargs):  # noqa: ANN001
        return self._session.execute(*args, **kwargs)

    async def commit(self):
        return self._session.commit()

    async def refresh(self, *args, **kwargs):  # noqa: ANN001
        return self._session.refresh(*args, **kwargs)

    async def rollback(self):
        return self._session.rollback()

    def add(self, *args, **kwargs):  # noqa: ANN001
        return self._session.add(*args, **kwargs)


@pytest.fixture
def async_test_db(test_db: Session) -> AsyncSessionAdapter:
    return AsyncSessionAdapter(test_db)


@pytest.fixture(autouse=True)
def cleanup_security_events(test_db: Session):
    """Clean up security events before and after each test"""
    test_db.query(SecurityEvent).delete()
    test_db.commit()
    yield
    test_db.query(SecurityEvent).delete()
    test_db.commit()


class TestPermissionDeniedLogging:
    """Test permission denied event logging in middleware"""

    async def test_log_permission_denied_creates_security_event(
        self, async_test_db: AsyncSessionAdapter
    ):
        """Test that permission denied events are logged to database"""
        logger = SecurityEventLogger(async_test_db)

        event = await logger.log_permission_denied(
            user_id="test_user_123",
            resource="organizations",
            action="access",
            ip="192.168.1.100",
        )

        assert event is not None
        assert event.event_type == SecurityEventType.PERMISSION_DENIED.value
        assert event.user_id == "test_user_123"
        assert event.ip_address == "192.168.1.100"
        assert event.severity == "medium"
        assert event.event_metadata["resource"] == "organizations"
        assert event.event_metadata["action"] == "access"

    async def test_log_permission_denied_increments_counter(
        self, async_test_db: AsyncSessionAdapter
    ):
        """Test that permission denied events increment Redis counter"""
        logger = SecurityEventLogger(async_test_db)

        # Log 3 permission denied events from same IP
        for i in range(3):
            await logger.log_permission_denied(
                user_id=f"user_{i}",
                resource="organizations",
                action="access",
                ip="192.168.1.101",
            )

        # Check event count
        count = await logger.get_event_count(
            ip="192.168.1.101", event_type=SecurityEventType.PERMISSION_DENIED
        )

        assert count == 3

    async def test_should_alert_when_threshold_exceeded(
        self, test_db: Session, async_test_db: AsyncSessionAdapter
    ):
        """Test that should_alert returns True when threshold is exceeded"""
        from datetime import datetime, timedelta

        from src.models.security_event import SecurityEvent
        from src.security.audit_logger import SecurityEventType

        logger = SecurityEventLogger(async_test_db, alert_threshold=5)

        # Manually create 6 events in the database (simulating past events)
        window_start = datetime.now() - timedelta(minutes=5)
        for i in range(6):
            event = SecurityEvent(
                event_type=SecurityEventType.PERMISSION_DENIED.value,
                severity="medium",
                user_id=f"user_{i}",
                ip_address="192.168.1.102",
                event_metadata={"resource": "organizations", "action": "access"},
                created_at=window_start + timedelta(seconds=i),
            )
            test_db.add(event)
        test_db.commit()

        # Should alert with 6 events (exceeds threshold of 5)
        assert (
            await logger.should_alert(
                ip="192.168.1.102", event_type=SecurityEventType.PERMISSION_DENIED
            )
            is True
        )

    async def test_should_not_alert_when_threshold_not_exceeded(
        self, test_db: Session, async_test_db: AsyncSessionAdapter
    ):
        """Test that should_alert returns False when threshold is not exceeded"""
        from datetime import datetime, timedelta

        from src.models.security_event import SecurityEvent
        from src.security.audit_logger import SecurityEventType

        logger = SecurityEventLogger(async_test_db, alert_threshold=10)

        # Manually create 5 events in the database
        window_start = datetime.now() - timedelta(minutes=5)
        for i in range(5):
            event = SecurityEvent(
                event_type=SecurityEventType.PERMISSION_DENIED.value,
                severity="medium",
                user_id=f"user_{i}",
                ip_address="192.168.1.103",
                event_metadata={"resource": "organizations", "action": "access"},
                created_at=window_start + timedelta(seconds=i),
            )
            test_db.add(event)
        test_db.commit()

        # Should not alert with only 5 events (below threshold of 10)
        assert (
            await logger.should_alert(
                ip="192.168.1.103", event_type=SecurityEventType.PERMISSION_DENIED
            )
            is False
        )

    async def test_should_alert_with_custom_threshold(
        self, test_db: Session, async_test_db: AsyncSessionAdapter
    ):
        """Test that should_alert respects custom threshold"""
        from datetime import datetime, timedelta

        from src.models.security_event import SecurityEvent
        from src.security.audit_logger import SecurityEventType

        logger = SecurityEventLogger(async_test_db, alert_threshold=5)

        # Manually create 3 events in the database
        window_start = datetime.now() - timedelta(minutes=5)
        for i in range(3):
            event = SecurityEvent(
                event_type=SecurityEventType.PERMISSION_DENIED.value,
                severity="medium",
                user_id=f"user_{i}",
                ip_address="192.168.1.104",
                event_metadata={"resource": "organizations", "action": "access"},
                created_at=window_start + timedelta(seconds=i),
            )
            test_db.add(event)
        test_db.commit()

        # Should not alert with default threshold (5)
        assert (
            await logger.should_alert(
                ip="192.168.1.104", event_type=SecurityEventType.PERMISSION_DENIED
            )
            is False
        )

        # Should alert with custom threshold (2)
        assert (
            await logger.should_alert(
                ip="192.168.1.104",
                event_type=SecurityEventType.PERMISSION_DENIED,
                threshold=2,
            )
            is True
        )


class TestSecurityAlertsEndpoint:
    """Test /security/alerts/test endpoint"""

    async def test_security_alerts_test_requires_admin(
        self, test_client_no_auth, test_admin
    ):
        """Test that /security/alerts/test requires admin role"""
        # Create auth headers for admin
        from datetime import datetime, timedelta

        import jwt

        from src.core.config import settings
        from src.security.cookie_manager import cookie_manager

        now = datetime.now(UTC)
        token_data = {
            "sub": str(test_admin.id),
            "user_id": str(test_admin.id),
            "username": test_admin.username,
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(test_admin.id),
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

        csrf_token = cookie_manager.create_csrf_token()
        response = await test_client_no_auth.post(
            "/api/v1/system/security/alerts/test",
            cookies={
                cookie_manager.cookie_name: token,
                cookie_manager.csrf_cookie_name: csrf_token,
            },
            headers={"X-CSRF-Token": csrf_token, "Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            print(f"DEBUG: Response status: {response.status_code}")
            print(f"DEBUG: Response text: {response.text}")
            print(f"DEBUG: Token data: {token_data}")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "should_alert" in data

    async def test_security_alerts_test_generates_events(
        self, test_client_no_auth, test_admin, test_db: Session
    ):
        """Test that /security/alerts/test generates security events"""
        # Get initial count
        initial_count = test_db.query(SecurityEvent).count()

        # Create auth headers for admin
        from datetime import datetime, timedelta

        import jwt

        from src.core.config import settings
        from src.security.cookie_manager import cookie_manager

        now = datetime.now(UTC)
        token_data = {
            "sub": str(test_admin.id),
            "user_id": str(test_admin.id),
            "username": test_admin.username,
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(test_admin.id),
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

        # Call test endpoint
        csrf_token = cookie_manager.create_csrf_token()
        response = await test_client_no_auth.post(
            "/api/v1/system/security/alerts/test",
            cookies={
                cookie_manager.cookie_name: token,
                cookie_manager.csrf_cookie_name: csrf_token,
            },
            headers={"X-CSRF-Token": csrf_token, "Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            print(f"DEBUG: Response status: {response.status_code}")
            print(f"DEBUG: Response text: {response.text}")

        assert response.status_code == 200

        # Verify events were created (12 test events)
        final_count = test_db.query(SecurityEvent).count()
        assert final_count >= initial_count + 12

    async def test_security_alerts_test_non_admin_forbidden(
        self, test_client_no_auth, test_user, test_db
    ):
        """Test that non-admin users cannot access /security/alerts/test"""
        # Create auth headers for regular user
        from datetime import datetime, timedelta

        import jwt

        from src.core.config import settings
        from src.models.rbac import Role, UserRoleAssignment
        from src.security.cookie_manager import cookie_manager

        # Ensure user only has non-admin role
        role = test_db.query(Role).filter(Role.name == "asset_viewer").first()
        if role is None:
            role = Role(
                name="asset_viewer",
                display_name="资产查看",
                is_system_role=True,
                is_active=True,
            )
            test_db.add(role)
            test_db.flush()
            test_db.refresh(role)

        test_db.query(UserRoleAssignment).filter(
            UserRoleAssignment.user_id == test_user.id
        ).delete()
        test_db.add(
            UserRoleAssignment(
                user_id=test_user.id,
                role_id=role.id,
                assigned_by="test-fixture",
            )
        )
        test_db.commit()

        now = datetime.now(UTC)
        token_data = {
            "sub": str(test_user.id),
            "user_id": str(test_user.id),
            "username": test_user.username,
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(test_user.id),
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

        csrf_token = cookie_manager.create_csrf_token()
        response = await test_client_no_auth.post(
            "/api/v1/system/security/alerts/test",
            cookies={
                cookie_manager.cookie_name: token,
                cookie_manager.csrf_cookie_name: csrf_token,
            },
            headers={"X-CSRF-Token": csrf_token, "Authorization": f"Bearer {token}"},
        )

        if response.status_code != 403:
            print(f"DEBUG: Response status: {response.status_code}")
            print(f"DEBUG: Response text: {response.text}")

        assert response.status_code == 403
        data = response.json()
        # Exception handler puts the detail message in "message" field
        assert "需要管理员权限" in data.get("message", "")

    async def test_security_alerts_test_without_auth(self, test_client_no_auth):
        """Test that unauthenticated users cannot access /security/alerts/test"""
        response = await test_client_no_auth.post("/api/v1/system/security/alerts/test")

        assert response.status_code == 401


class TestSecurityEventsEndpoint:
    """Test /security/events endpoint"""

    async def test_security_events_requires_admin(
        self, test_client_no_auth, test_admin
    ):
        """Test that /security/events requires admin role"""
        from datetime import datetime, timedelta

        import jwt

        from src.core.config import settings
        from src.security.cookie_manager import cookie_manager

        now = datetime.now(UTC)
        token_data = {
            "sub": str(test_admin.id),
            "user_id": str(test_admin.id),
            "username": test_admin.username,
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(test_admin.id),
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

        csrf_token = cookie_manager.create_csrf_token()
        response = await test_client_no_auth.get(
            "/api/v1/system/security/events",
            cookies={
                cookie_manager.cookie_name: token,
                cookie_manager.csrf_cookie_name: csrf_token,
            },
            headers={"X-CSRF-Token": csrf_token, "Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            print(f"DEBUG: Response status: {response.status_code}")
            print(f"DEBUG: Response text: {response.text}")

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data

    async def test_security_events_returns_paginated_results(
        self, test_client_no_auth, test_admin, test_db: Session
    ):
        """Test that /security/events returns paginated results"""
        # Create some events
        from datetime import datetime, timedelta

        import jwt

        from src.core.config import settings
        from src.models.security_event import SecurityEvent
        from src.security.audit_logger import SecurityEventType
        from src.security.cookie_manager import cookie_manager

        for i in range(15):
            event = SecurityEvent(
                event_type=SecurityEventType.PERMISSION_DENIED.value,
                severity="medium",
                user_id=f"user_{i}",
                ip_address="192.168.1.100",
                event_metadata={"resource": "test"},
            )
            test_db.add(event)
        test_db.commit()

        # Create auth token
        now = datetime.now(UTC)
        token_data = {
            "sub": str(test_admin.id),
            "user_id": str(test_admin.id),
            "username": test_admin.username,
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(test_admin.id),
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

        csrf_token = cookie_manager.create_csrf_token()
        # Request first page with size 5
        response = await test_client_no_auth.get(
            "/api/v1/system/security/events?page=1&page_size=5",
            cookies={
                cookie_manager.cookie_name: token,
                cookie_manager.csrf_cookie_name: csrf_token,
            },
            headers={"X-CSRF-Token": csrf_token, "Authorization": f"Bearer {token}"},
        )

        if response.status_code != 200:
            print(f"DEBUG: Response status: {response.status_code}")
            print(f"DEBUG: Response text: {response.text}")

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 5
        assert data["total"] >= 15
        assert data["page_size"] == 5

    async def test_security_events_includes_event_details(
        self, test_client_no_auth, test_admin, test_db: Session
    ):
        """Test that /security/events response includes event details"""
        from datetime import datetime, timedelta

        import jwt

        from src.core.config import settings
        from src.models.security_event import SecurityEvent
        from src.security.audit_logger import SecurityEventType
        from src.security.cookie_manager import cookie_manager

        # Create a specific event
        event = SecurityEvent(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY.value,
            severity="high",
            user_id="test_attacker",
            ip_address="10.0.0.1",
            event_metadata={"target": "login"},
        )
        test_db.add(event)
        test_db.commit()

        # Create auth token
        now = datetime.now(UTC)
        token_data = {
            "sub": str(test_admin.id),
            "user_id": str(test_admin.id),
            "username": test_admin.username,
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(test_admin.id),
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

        csrf_token = cookie_manager.create_csrf_token()
        response = await test_client_no_auth.get(
            "/api/v1/system/security/events",
            cookies={
                cookie_manager.cookie_name: token,
                cookie_manager.csrf_cookie_name: csrf_token,
            },
            headers={"X-CSRF-Token": csrf_token, "Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Find our event
        found_event = next(
            (e for e in data["events"] if e["user_id"] == "test_attacker"), None
        )
        assert found_event is not None
        assert found_event["type"] == SecurityEventType.SUSPICIOUS_ACTIVITY.value
        assert found_event["severity"] == "high"
        assert found_event["ip"] == "10.0.0.1"

    async def test_security_events_non_admin_forbidden(
        self, test_client_no_auth, test_user, test_db
    ):
        """Test that non-admin users cannot access /security/events"""
        from datetime import datetime, timedelta

        import jwt

        from src.core.config import settings
        from src.models.rbac import Role, UserRoleAssignment
        from src.security.cookie_manager import cookie_manager

        # Ensure user only has non-admin role
        role = test_db.query(Role).filter(Role.name == "asset_viewer").first()
        if role is None:
            role = Role(
                name="asset_viewer",
                display_name="资产查看",
                is_system_role=True,
                is_active=True,
            )
            test_db.add(role)
            test_db.flush()
            test_db.refresh(role)

        test_db.query(UserRoleAssignment).filter(
            UserRoleAssignment.user_id == test_user.id
        ).delete()
        test_db.add(
            UserRoleAssignment(
                user_id=test_user.id,
                role_id=role.id,
                assigned_by="test-fixture",
            )
        )
        test_db.commit()

        now = datetime.now(UTC)
        token_data = {
            "sub": str(test_user.id),
            "user_id": str(test_user.id),
            "username": test_user.username,
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(test_user.id),
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

        csrf_token = cookie_manager.create_csrf_token()
        response = await test_client_no_auth.get(
            "/api/v1/system/security/events",
            cookies={
                cookie_manager.cookie_name: token,
                cookie_manager.csrf_cookie_name: csrf_token,
            },
            headers={"X-CSRF-Token": csrf_token, "Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    async def test_security_events_ordered_by_created_at_desc(
        self, test_client_no_auth, test_admin, test_db: Session
    ):
        """Test that /security/events are ordered by created_at desc"""
        from datetime import datetime, timedelta

        import jwt

        from src.core.config import settings
        from src.models.security_event import SecurityEvent
        from src.security.audit_logger import SecurityEventType
        from src.security.cookie_manager import cookie_manager

        # Create events with different timestamps
        base_time = datetime.now()
        for i in range(3):
            event = SecurityEvent(
                event_type=SecurityEventType.PERMISSION_DENIED.value,
                severity="medium",
                user_id=f"user_{i}",
                ip_address="192.168.1.100",
                event_metadata={"resource": "test"},
                created_at=base_time + timedelta(seconds=i),
            )
            test_db.add(event)
        test_db.commit()

        # Create auth token
        now = datetime.now(UTC)
        token_data = {
            "sub": str(test_admin.id),
            "user_id": str(test_admin.id),
            "username": test_admin.username,
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(test_admin.id),
            "aud": settings.JWT_AUDIENCE,
            "iss": settings.JWT_ISSUER,
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

        csrf_token = cookie_manager.create_csrf_token()
        response = await test_client_no_auth.get(
            "/api/v1/system/security/events",
            cookies={
                cookie_manager.cookie_name: token,
                cookie_manager.csrf_cookie_name: csrf_token,
            },
            headers={"X-CSRF-Token": csrf_token, "Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify order
        items = data["events"]
        assert len(items) >= 3
        # Just check the first few items
        event_ids = [
            item["user_id"] for item in items if item["user_id"].startswith("user_")
        ]
        if len(event_ids) >= 3:
            # user_2 (newest) should be first
            assert event_ids[0] == "user_2"
            assert event_ids[1] == "user_1"
            assert event_ids[2] == "user_0"
