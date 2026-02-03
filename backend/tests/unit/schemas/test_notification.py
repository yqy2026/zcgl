"""
Unit tests for notification schemas
"""

from dataclasses import dataclass
from datetime import datetime

import pytest
from pydantic import ValidationError

from src.schemas.notification import (
    NotificationCreate,
    NotificationListResponse,
    NotificationMarkReadRequest,
    NotificationPriority,
    NotificationResponse,
    NotificationSummary,
    NotificationType,
)


class TestNotificationSchemas:
    def test_notification_create_defaults(self):
        payload = NotificationCreate(
            type=NotificationType.CONTRACT_EXPIRING,
            title="Title",
            content="Content",
            recipient_id="user-1",
        )
        assert payload.priority == NotificationPriority.NORMAL
        assert payload.related_entity_id is None

    def test_notification_response_from_attributes(self):
        @dataclass
        class Obj:
            id: str
            recipient_id: str
            type: NotificationType
            priority: NotificationPriority
            title: str
            content: str
            is_read: bool
            read_at: datetime | None
            is_sent_wecom: bool
            wecom_sent_at: datetime | None
            wecom_send_error: str | None
            created_at: datetime
            updated_at: datetime
            related_entity_type: str | None = None
            related_entity_id: str | None = None
            extra_data: dict | None = None

        now = datetime(2024, 1, 1, 12, 0, 0)
        obj = Obj(
            id="n1",
            recipient_id="u1",
            type=NotificationType.SYSTEM_NOTICE,
            priority=NotificationPriority.HIGH,
            title="System",
            content="Hello",
            is_read=False,
            read_at=None,
            is_sent_wecom=False,
            wecom_sent_at=None,
            wecom_send_error=None,
            created_at=now,
            updated_at=now,
        )

        model = NotificationResponse.model_validate(obj)
        assert model.id == "n1"
        assert model.priority == NotificationPriority.HIGH
        assert model.created_at == now

    def test_notification_title_max_length(self):
        long_title = "x" * 201
        with pytest.raises(ValidationError):
            NotificationCreate(
                type=NotificationType.PAYMENT_DUE,
                title=long_title,
                content="Content",
                recipient_id="user-1",
            )

    def test_notification_list_response(self):
        item = NotificationResponse(
            id="n1",
            recipient_id="u1",
            type=NotificationType.SYSTEM_NOTICE,
            priority=NotificationPriority.NORMAL,
            title="T",
            content="C",
            related_entity_type=None,
            related_entity_id=None,
            extra_data=None,
            is_read=False,
            read_at=None,
            is_sent_wecom=False,
            wecom_sent_at=None,
            wecom_send_error=None,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0),
        )
        response = NotificationListResponse(
            items=[item], total=1, page=1, page_size=10, pages=1
        )
        assert response.total == 1
        assert response.items[0].id == "n1"

    def test_notification_mark_read_request(self):
        req = NotificationMarkReadRequest(notification_ids=["n1", "n2"])
        assert req.notification_ids == ["n1", "n2"]

    def test_notification_summary(self):
        summary = NotificationSummary(
            total_count=10, unread_count=2, urgent_count=1, today_count=3
        )
        assert summary.unread_count == 2
