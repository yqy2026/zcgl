from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exception_handler import BusinessValidationError
from src.models.notification import NotificationPriority, NotificationType
from src.services.notification.notification_service import NotificationService


def _active_user(user_id: str) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    return user


class TestCreateSystemNotice:
    async def test_broadcasts_neutral_notice_to_all_active_users(self, mock_db):
        service = NotificationService()
        active_users = [_active_user("user-1"), _active_user("user-2")]

        with patch(
            "src.services.notification.notification_service.notification_crud"
        ) as mock_crud:
            mock_crud.get_active_users_async = AsyncMock(return_value=active_users)

            created = await service.create_system_notice_async(
                mock_db,
                title="Maintenance window",
                content="System maintenance starts at 22:00.",
                priority=NotificationPriority.NORMAL,
            )

        assert len(created) == 2
        assert [item.recipient_id for item in created] == ["user-1", "user-2"]
        assert {item.type for item in created} == {NotificationType.SYSTEM_NOTICE}
        assert {item.priority for item in created} == {NotificationPriority.NORMAL}
        assert {item.related_entity_type for item in created} == {None}
        assert {item.related_entity_id for item in created} == {None}
        assert all(item.is_read is False for item in created)
        assert mock_db.add.call_count == 2
        mock_db.flush.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

    async def test_rejects_business_entity_binding(self, mock_db):
        service = NotificationService()

        with pytest.raises(BusinessValidationError):
            await service.create_system_notice_async(
                mock_db,
                title="Contract update",
                content="A contract changed.",
                priority=NotificationPriority.NORMAL,
                related_entity_type="contract",
                related_entity_id="contract-1",
            )

        mock_db.add.assert_not_called()

    async def test_rejects_pii_in_content(self, mock_db):
        service = NotificationService()

        with pytest.raises(BusinessValidationError):
            await service.create_system_notice_async(
                mock_db,
                title="Personal data",
                content="Call 13800000000 for details.",
                priority=NotificationPriority.NORMAL,
            )

        mock_db.add.assert_not_called()
