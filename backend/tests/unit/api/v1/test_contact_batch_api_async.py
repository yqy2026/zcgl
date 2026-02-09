from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.contact import Contact, ContactType
from src.schemas.contact import ContactCreate

pytestmark = pytest.mark.asyncio


class TestContactBatchApi:
    async def test_create_contacts_batch_uses_bulk_create(self):
        from src.api.v1.system.contact import create_contacts_batch

        db = AsyncMock()
        user = SimpleNamespace(username="tester")
        contacts_in = [
            ContactCreate(
                name="联系人A",
                phone="13800000001",
                entity_type="ignored",
                entity_id="ignored",
            ),
            ContactCreate(
                name="联系人B",
                phone="13800000002",
                entity_type="ignored",
                entity_id="ignored",
                is_primary=True,
            ),
        ]

        now = datetime.utcnow()
        created_contacts = [
            Contact(
                id="contact-a",
                entity_type="ownership",
                entity_id="org-1",
                name="联系人A",
                phone="13800000001",
                contact_type=ContactType.GENERAL,
                is_primary=False,
                is_active=True,
                created_at=now,
                updated_at=now,
                created_by="tester",
                updated_by="tester",
            ),
            Contact(
                id="contact-b",
                entity_type="ownership",
                entity_id="org-1",
                name="联系人B",
                phone="13800000002",
                contact_type=ContactType.PRIMARY,
                is_primary=True,
                is_active=True,
                created_at=now,
                updated_at=now,
                created_by="tester",
                updated_by="tester",
            ),
        ]

        mock_service = MagicMock()
        mock_service.create_contacts_batch = AsyncMock(return_value=created_contacts)

        result = await create_contacts_batch(
            entity_type="ownership",
            entity_id="org-1",
            db=db,
            contacts_in=contacts_in,
            current_user=user,
            service=mock_service,
        )

        assert len(result) == 2
        mock_service.create_contacts_batch.assert_awaited_once()
        kwargs = mock_service.create_contacts_batch.await_args.kwargs
        assert kwargs["db"] is db
        assert len(kwargs["contacts_data"]) == 2
        assert kwargs["contacts_data"][0]["entity_type"] == "ownership"
        assert kwargs["contacts_data"][0]["entity_id"] == "org-1"
        assert kwargs["contacts_data"][1]["is_primary"] is True

    async def test_create_contacts_batch_empty(self):
        from src.api.v1.system.contact import create_contacts_batch

        db = AsyncMock()
        user = SimpleNamespace(username="tester")
        mock_service = MagicMock()
        mock_service.create_contacts_batch = AsyncMock(return_value=[])

        result = await create_contacts_batch(
            entity_type="ownership",
            entity_id="org-1",
            db=db,
            contacts_in=[],
            current_user=user,
            service=mock_service,
        )

        assert result == []
        mock_service.create_contacts_batch.assert_awaited_once()
