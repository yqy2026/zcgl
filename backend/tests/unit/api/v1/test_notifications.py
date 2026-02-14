"""
通知API测试

Test coverage for Notifications API endpoints:
- Get notifications list (with pagination and filtering)
- Get unread count
- Mark notification as read
- Mark all as read
- Delete notification
- Authentication and authorization
- Error handling
"""

import pytest
from fastapi import status
from sqlalchemy.orm import Session

from src.models.notification import Notification

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def admin_user_in_db(db_session: Session, admin_user):
    """Ensure admin user exists in DB for FK constraints."""
    from src.models.auth import User

    # Check by ID first
    existing = db_session.query(User).filter(User.id == admin_user.id).first()
    if existing:
        return existing

    # Check by username to avoid unique constraint violations
    existing_by_name = (
        db_session.query(User).filter(User.username == admin_user.username).first()
    )
    if existing_by_name:
        return existing_by_name

    user = User(
        id=admin_user.id,
        username=admin_user.username,
        email=admin_user.email,
        phone="13800009999",
        full_name="Admin User",
        password_hash="test-hash",
        is_active=True,
        created_by="test-fixture",
        updated_by="test-fixture",
    )
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)
    from src.models.rbac import Role, UserRoleAssignment

    role = db_session.query(Role).filter(Role.name == "admin").first()
    if role is None:
        role = Role(
            name="admin",
            display_name="管理员",
            is_system_role=True,
            is_active=True,
        )
        db_session.add(role)
        db_session.flush()
        db_session.refresh(role)

    assignment = (
        db_session.query(UserRoleAssignment)
        .filter(
            UserRoleAssignment.user_id == user.id,
            UserRoleAssignment.role_id == role.id,
        )
        .first()
    )
    if assignment is None:
        assignment = UserRoleAssignment(
            user_id=user.id,
            role_id=role.id,
            assigned_by="test-fixture",
        )
        db_session.add(assignment)
        db_session.flush()
    return user


@pytest.fixture
def sample_notification(db_session: Session, admin_user_in_db):
    """创建测试通知"""
    from datetime import UTC, datetime

    from src.models.notification import Notification

    notification = Notification(
        recipient_id=admin_user_in_db.id,
        type="system",
        priority="normal",
        title="测试通知",
        content="这是一条测试通知内容",
        is_read=False,
        created_at=datetime.now(UTC),
    )
    db_session.add(notification)
    db_session.flush()
    db_session.refresh(notification)

    yield notification


@pytest.fixture
def multiple_notifications(db_session: Session, admin_user_in_db):
    """创建多条测试通知"""
    from datetime import UTC, datetime

    from src.models.notification import Notification

    notifications = []
    for i in range(5):
        notification = Notification(
            recipient_id=admin_user_in_db.id,
            type="alert" if i % 2 == 0 else "info",
            priority="high" if i % 2 == 0 else "normal",
            title=f"测试通知 {i}",
            content=f"通知内容 {i}",
            is_read=(i >= 3),  # 前3条未读，后2条已读
            created_at=datetime.now(UTC),
        )
        db_session.add(notification)
        db_session.flush()
        db_session.refresh(notification)
        notifications.append(notification)

    yield notifications


@pytest.fixture
def admin_user_headers(client, admin_user_in_db, monkeypatch):
    """管理员用户认证头 - 并更新 Mock 用户以匹配 admin_user_in_db"""
    from unittest.mock import MagicMock

    from src.main import app
    from src.middleware import auth as auth_module

    # Update the mock user in auth module to match the DB user
    mock_user = MagicMock()
    mock_user.id = admin_user_in_db.id
    mock_user.username = admin_user_in_db.username
    mock_user.email = admin_user_in_db.email
    mock_user.is_active = True

    def mock_get_user():
        return mock_user

    # Update dependency overrides to ensure FastAPI uses our mock user
    # Note: We must iterate keys because client fixture monkeypatches the module,
    # so importing get_current_active_user here might give us the mock, not the original function key.
    for key in list(app.dependency_overrides.keys()):
        if getattr(key, "__name__", "") in [
            "get_current_active_user",
            "get_current_user",
            "get_current_user_from_cookie",
            "require_admin",
        ]:
            app.dependency_overrides[key] = mock_get_user

    monkeypatch.setattr(auth_module, "get_current_user", mock_get_user)
    monkeypatch.setattr(auth_module, "get_current_active_user", mock_get_user)

    return {"Authorization": "Bearer mock_token"}


# ============================================================================
# Get Notifications List Tests
# ============================================================================


class TestGetNotifications:
    """测试获取通知列表API"""

    def test_get_notifications_default(
        self, client, admin_user_headers, multiple_notifications
    ):
        """测试获取通知列表（默认参数）"""
        response = client.get("/api/v1/notifications/", headers=admin_user_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "items" in data["data"]
        assert "unread_count" in data["data"]
        assert "pagination" in data["data"]
        assert "total" in data["data"]["pagination"]

    def test_get_notifications_with_pagination(
        self, client, admin_user_headers, multiple_notifications
    ):
        """测试分页功能"""
        response = client.get(
            "/api/v1/notifications/?page=1&page_size=2", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]["items"]) <= 2

    def test_get_notifications_filter_by_unread(
        self, client, admin_user_headers, multiple_notifications
    ):
        """测试筛选未读通知"""
        response = client.get(
            "/api/v1/notifications/?is_read=false", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 验证所有结果都是未读的
        for item in data["data"]["items"]:
            assert item["is_read"] is False

    def test_get_notifications_filter_by_read(
        self, client, admin_user_headers, multiple_notifications
    ):
        """测试筛选已读通知"""
        response = client.get(
            "/api/v1/notifications/?is_read=true", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 验证所有结果都是已读的
        for item in data["data"]["items"]:
            assert item["is_read"] is True

    def test_get_notifications_filter_by_type(
        self, client, admin_user_headers, multiple_notifications
    ):
        """测试按类型筛选"""
        response = client.get(
            "/api/v1/notifications/?type=alert", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 验证所有结果都是alert类型
        for item in data["data"]["items"]:
            assert item["type"] == "alert"

    def test_get_notifications_unauthorized(self, unauthenticated_client):
        """测试未授权获取通知"""
        response = unauthenticated_client.get("/api/v1/notifications/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data.get("error", {}).get("code") == "AUTHENTICATION_ERROR"


# ============================================================================
# Get Unread Count Tests
# ============================================================================


class TestGetUnreadCount:
    """测试获取未读数量API"""

    def test_get_unread_count_success(
        self, client, admin_user_headers, multiple_notifications
    ):
        """测试成功获取未读数量"""
        response = client.get(
            "/api/v1/notifications/unread-count", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "unread_count" in data
        assert data["unread_count"] >= 0

    def test_get_unread_count_zero(
        self, client, admin_user_headers, db_session: Session, admin_user
    ):
        """测试没有未读通知时返回0"""
        # 清除所有通知
        db_session.query(Notification).filter(
            Notification.recipient_id == admin_user.id
        ).delete()
        db_session.commit()

        response = client.get(
            "/api/v1/notifications/unread-count", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["unread_count"] == 0

    def test_get_unread_count_unauthorized(self, unauthenticated_client):
        """测试未授权获取未读数量"""
        response = unauthenticated_client.get("/api/v1/notifications/unread-count")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data.get("error", {}).get("code") == "AUTHENTICATION_ERROR"


# ============================================================================
# Mark as Read Tests
# ============================================================================


class TestMarkAsRead:
    """测试标记已读API"""

    def test_mark_notification_as_read_success(
        self, client, admin_user_headers, sample_notification
    ):
        """测试成功标记通知为已读"""
        response = client.post(
            f"/api/v1/notifications/{sample_notification.id}/read",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_read"] is True
        assert "read_at" in data
        assert data["read_at"] is not None

    def test_mark_notification_as_read_not_found(self, client, admin_user_headers):
        """测试标记不存在的通知"""
        response = client.post(
            "/api/v1/notifications/non-existent-id/read", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_mark_notification_as_read_unauthorized(
        self, unauthenticated_client, sample_notification
    ):
        """测试未授权标记通知"""
        response = unauthenticated_client.post(
            f"/api/v1/notifications/{sample_notification.id}/read"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data.get("error", {}).get("code") == "AUTHENTICATION_ERROR"


# ============================================================================
# Mark All as Read Tests
# ============================================================================


class TestMarkAllAsRead:
    """测试全部标记已读API"""

    def test_mark_all_as_read_success(
        self,
        client,
        admin_user_headers,
        multiple_notifications,
        db_session: Session,
        admin_user,
    ):
        """测试成功标记所有通知为已读"""
        response = client.post(
            "/api/v1/notifications/read-all", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data

        # 验证所有通知都已读
        unread_count = (
            db_session.query(Notification)
            .filter(
                Notification.recipient_id == admin_user.id,
                Notification.is_read.is_(False),
            )
            .count()
        )
        assert unread_count == 0

    def test_mark_all_as_read_unauthorized(self, unauthenticated_client):
        """测试未授权全部标记已读"""
        response = unauthenticated_client.post("/api/v1/notifications/read-all")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data.get("error", {}).get("code") == "AUTHENTICATION_ERROR"


# ============================================================================
# Delete Notification Tests
# ============================================================================


class TestDeleteNotification:
    """测试删除通知API"""

    def test_delete_notification_success(
        self, client, admin_user_headers, sample_notification, db_session: Session
    ):
        """测试成功删除通知"""
        notification_id = sample_notification.id

        response = client.delete(
            f"/api/v1/notifications/{notification_id}", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data

        # 验证通知已删除
        notification = (
            db_session.query(Notification)
            .filter(Notification.id == notification_id)
            .first()
        )
        assert notification is None

    def test_delete_notification_not_found(self, client, admin_user_headers):
        """测试删除不存在的通知"""
        response = client.delete(
            "/api/v1/notifications/non-existent-id", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_notification_unauthorized(
        self, unauthenticated_client, sample_notification
    ):
        """测试未授权删除通知"""
        response = unauthenticated_client.delete(
            f"/api/v1/notifications/{sample_notification.id}"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data.get("error", {}).get("code") == "AUTHENTICATION_ERROR"


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestNotificationsEdgeCases:
    """测试边界情况"""

    def test_empty_notifications_list(
        self, client, admin_user_headers, db_session: Session, admin_user
    ):
        """测试空通知列表"""
        # 清除所有通知
        db_session.query(Notification).filter(
            Notification.recipient_id == admin_user.id
        ).delete()
        db_session.commit()

        response = client.get("/api/v1/notifications/", headers=admin_user_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]["items"]) == 0
        assert data["data"]["pagination"]["total"] == 0
        assert data["data"]["unread_count"] == 0

    def test_large_page_size(self, client, admin_user_headers):
        """测试大分页大小"""
        response = client.get(
            "/api/v1/notifications/?page_size=100", headers=admin_user_headers
        )

        assert response.status_code == status.HTTP_200_OK

    def test_invalid_page_size(self, client, admin_user_headers):
        """测试无效的分页大小（超过最大值）"""
        response = client.get(
            "/api/v1/notifications/?page_size=200",  # 超过最大值100
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_mark_already_read_notification(
        self, client, admin_user_headers, sample_notification
    ):
        """测试标记已读通知（幂等性）"""
        # 先标记为已读
        client.post(
            f"/api/v1/notifications/{sample_notification.id}/read",
            headers=admin_user_headers,
        )

        # 再次标记应该成功（幂等）
        response = client.post(
            f"/api/v1/notifications/{sample_notification.id}/read",
            headers=admin_user_headers,
        )

        assert response.status_code == status.HTTP_200_OK

    def test_notifications_ordering(
        self, client, admin_user_headers, multiple_notifications
    ):
        """测试通知排序（按创建时间倒序）"""
        response = client.get("/api/v1/notifications/", headers=admin_user_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # 验证排序（最新在前）
        if len(data["data"]["items"]) > 1:
            for i in range(len(data["data"]["items"]) - 1):
                assert (
                    data["data"]["items"][i]["created_at"]
                    >= data["data"]["items"][i + 1]["created_at"]
                )
