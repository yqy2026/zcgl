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

from sqlalchemy.orm import Session

from src.core.security_event_logger import SecurityEventLogger, SecurityEventType
from src.models.security_event import SecurityEvent


class TestPermissionDeniedLogging:
    """Test permission denied event logging in middleware"""

    def test_log_permission_denied_creates_security_event(self, test_db: Session):
        """Test that permission denied events are logged to database"""
        logger = SecurityEventLogger(test_db)

        event = logger.log_permission_denied(
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

    def test_log_permission_denied_increments_counter(self, test_db: Session):
        """Test that permission denied events increment Redis counter"""
        logger = SecurityEventLogger(test_db)

        # Log 3 permission denied events from same IP
        for i in range(3):
            logger.log_permission_denied(
                user_id=f"user_{i}",
                resource="organizations",
                action="access",
                ip="192.168.1.101",
            )

        # Check event count
        count = logger.get_event_count(
            ip="192.168.1.101", event_type=SecurityEventType.PERMISSION_DENIED
        )

        assert count == 3

    def test_should_alert_when_threshold_exceeded(self, test_db: Session):
        """Test that should_alert returns True when threshold is exceeded"""
        from datetime import datetime, timedelta

        from src.core.security_event_logger import SecurityEventType
        from src.models.security_event import SecurityEvent

        logger = SecurityEventLogger(test_db, alert_threshold=5)

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
            logger.should_alert(
                ip="192.168.1.102", event_type=SecurityEventType.PERMISSION_DENIED
            )
            is True
        )

    def test_should_not_alert_when_threshold_not_exceeded(self, test_db: Session):
        """Test that should_alert returns False when threshold is not exceeded"""
        from datetime import datetime, timedelta

        from src.core.security_event_logger import SecurityEventType
        from src.models.security_event import SecurityEvent

        logger = SecurityEventLogger(test_db, alert_threshold=10)

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
            logger.should_alert(
                ip="192.168.1.103", event_type=SecurityEventType.PERMISSION_DENIED
            )
            is False
        )

    def test_should_alert_with_custom_threshold(self, test_db: Session):
        """Test that should_alert respects custom threshold"""
        from datetime import datetime, timedelta

        from src.core.security_event_logger import SecurityEventType
        from src.models.security_event import SecurityEvent

        logger = SecurityEventLogger(test_db, alert_threshold=5)

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
            logger.should_alert(
                ip="192.168.1.104", event_type=SecurityEventType.PERMISSION_DENIED
            )
            is False
        )

        # Should alert with custom threshold (2)
        assert (
            logger.should_alert(
                ip="192.168.1.104",
                event_type=SecurityEventType.PERMISSION_DENIED,
                threshold=2,
            )
            is True
        )


class TestSecurityAlertsEndpoint:
    """Test /security/alerts/test endpoint"""

    def test_security_alerts_test_requires_admin(self, test_client, test_admin):
        """Test that /security/alerts/test requires admin role"""
        # Create auth headers for admin
        from datetime import datetime, timedelta

        import jwt

        from src.core.config import settings

        now = datetime.utcnow()
        token_data = {
            "sub": str(test_admin.id),
            "user_id": str(test_admin.id),
            "username": test_admin.username,
            "role": test_admin.role or "admin",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(test_admin.id),
            "aud": "land-property-system",
            "iss": "land-property-auth",
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

        response = test_client.post(
            "/api/v1/system/security/alerts/test",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "should_alert" in data

    def test_security_alerts_test_generates_events(
        self, test_client, test_admin, test_db: Session
    ):
        """Test that /security/alerts/test generates security events"""
        # Get initial count
        initial_count = test_db.query(SecurityEvent).count()

        # Create auth headers for admin
        from datetime import datetime, timedelta

        import jwt

        from src.core.config import settings

        now = datetime.utcnow()
        token_data = {
            "sub": str(test_admin.id),
            "user_id": str(test_admin.id),
            "username": test_admin.username,
            "role": test_admin.role or "admin",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(test_admin.id),
            "aud": "land-property-system",
            "iss": "land-property-auth",
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

        # Call test endpoint
        response = test_client.post(
            "/api/v1/system/security/alerts/test",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200

        # Verify events were created (12 test events)
        final_count = test_db.query(SecurityEvent).count()
        assert final_count >= initial_count + 12

    def test_security_alerts_test_non_admin_forbidden(self, test_client, test_user):
        """Test that non-admin users cannot access /security/alerts/test"""
        # Create auth headers for regular user
        from datetime import datetime, timedelta

        import jwt

        from src.core.config import settings

        # Change user role to non-admin
        test_user.role = "user"

        now = datetime.utcnow()
        token_data = {
            "sub": str(test_user.id),
            "user_id": str(test_user.id),
            "username": test_user.username,
            "role": "user",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(test_user.id),
            "aud": "land-property-system",
            "iss": "land-property-auth",
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

        response = test_client.post(
            "/api/v1/system/security/alerts/test",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert "需要管理员权限" in response.json()["detail"]

    def test_security_alerts_test_without_auth(self, test_client):
        """Test that unauthenticated users cannot access /security/alerts/test"""
        response = test_client.post("/api/v1/system/security/alerts/test")

        assert response.status_code == 401


class TestSecurityEventsEndpoint:
    """Test /security/events endpoint"""

    def test_security_events_requires_admin(self, test_client, test_admin):
        """Test that /security/events requires admin role"""
        # Create auth headers for admin
        from datetime import datetime, timedelta

        import jwt

        from src.core.config import settings

        now = datetime.utcnow()
        token_data = {
            "sub": str(test_admin.id),
            "user_id": str(test_admin.id),
            "username": test_admin.username,
            "role": test_admin.role or "admin",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(test_admin.id),
            "aud": "land-property-system",
            "iss": "land-property-auth",
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

        response = test_client.get(
            "/api/v1/system/security/events",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "events" in data
        assert isinstance(data["events"], list)

    def test_security_events_returns_paginated_results(self, test_client, test_admin):
        """Test that /security/events supports pagination"""
        # Create auth headers for admin
        from datetime import datetime, timedelta

        import jwt

        from src.core.config import settings

        now = datetime.utcnow()
        token_data = {
            "sub": str(test_admin.id),
            "user_id": str(test_admin.id),
            "username": test_admin.username,
            "role": test_admin.role or "admin",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(test_admin.id),
            "aud": "land-property-system",
            "iss": "land-property-auth",
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

        # Test first page
        response = test_client.get(
            "/api/v1/system/security/events?skip=0&limit=5",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) <= 5
        assert data["skip"] == 0
        assert data["limit"] == 5

    def test_security_events_includes_event_details(
        self, test_client, test_admin, test_db: Session
    ):
        """Test that /security/events returns complete event information"""
        # Create a test event
        logger = SecurityEventLogger(test_db)
        test_event = logger.log_permission_denied(
            user_id="test_user",
            resource="organizations",
            action="access",
            ip="192.168.1.200",
        )

        # Create auth headers for admin
        from datetime import datetime, timedelta

        import jwt

        from src.core.config import settings

        now = datetime.utcnow()
        token_data = {
            "sub": str(test_admin.id),
            "user_id": str(test_admin.id),
            "username": test_admin.username,
            "role": test_admin.role or "admin",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(test_admin.id),
            "aud": "land-property-system",
            "iss": "land-property-auth",
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

        # Fetch events
        response = test_client.get(
            "/api/v1/system/security/events",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Find our test event
        found = False
        for event in data["events"]:
            if event["id"] == test_event.id:
                found = True
                assert event["type"] == SecurityEventType.PERMISSION_DENIED.value
                assert event["user_id"] == "test_user"
                assert event["ip"] == "192.168.1.200"
                assert event["severity"] == "medium"
                assert event["metadata"]["resource"] == "organizations"
                assert event["metadata"]["action"] == "access"
                assert "created_at" in event
                break

        assert found, "Test event not found in response"

    def test_security_events_non_admin_forbidden(self, test_client, test_user):
        """Test that non-admin users cannot access /security/events"""
        # Create auth headers for regular user
        from datetime import datetime, timedelta

        import jwt

        from src.core.config import settings

        # Change user role to non-admin
        test_user.role = "user"

        now = datetime.utcnow()
        token_data = {
            "sub": str(test_user.id),
            "user_id": str(test_user.id),
            "username": test_user.username,
            "role": "user",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(test_user.id),
            "aud": "land-property-system",
            "iss": "land-property-auth",
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

        response = test_client.get(
            "/api/v1/system/security/events",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert "需要管理员权限" in response.json()["detail"]

    def test_security_events_without_auth(self, test_client):
        """Test that unauthenticated users cannot access /security/events"""
        response = test_client.get("/api/v1/system/security/events")

        assert response.status_code == 401

    def test_security_events_ordered_by_created_at_desc(
        self, test_client, test_admin, test_db: Session
    ):
        """Test that /security/events returns events in descending order by created_at"""
        # Create multiple events with slight delay
        import time

        logger = SecurityEventLogger(test_db)
        event_ids = []

        for i in range(3):
            event = logger.log_permission_denied(
                user_id=f"user_{i}",
                resource="organizations",
                action="access",
                ip=f"192.168.1.{i}",
            )
            event_ids.append(event.id)
            time.sleep(0.01)  # Small delay to ensure different timestamps

        # Create auth headers for admin
        from datetime import datetime, timedelta

        import jwt

        from src.core.config import settings

        now = datetime.utcnow()
        token_data = {
            "sub": str(test_admin.id),
            "user_id": str(test_admin.id),
            "username": test_admin.username,
            "role": test_admin.role or "admin",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(test_admin.id),
            "aud": "land-property-system",
            "iss": "land-property-auth",
        }
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

        # Fetch events
        response = test_client.get(
            "/api/v1/system/security/events?limit=10",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Find the positions of our test events
        event_positions = {}
        for idx, event in enumerate(data["events"]):
            if event["id"] in event_ids:
                event_positions[event["id"]] = idx

        # The last created event should appear first
        assert len(event_positions) == 3
        positions = list(event_positions.values())
        assert positions[0] < positions[1] < positions[2], (
            "Events should be ordered by created_at descending"
        )
