from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

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

        with patch(
            "src.api.v1.system.contact.contact_crud.create_many_async",
            new=AsyncMock(return_value=created_contacts),
        ) as mock_create_many:
            result = await create_contacts_batch(
                entity_type="ownership",
                entity_id="org-1",
                db=db,
                contacts_in=contacts_in,
                current_user=user,
            )

        assert len(result) == 2
        mock_create_many.assert_awaited_once()
        kwargs = mock_create_many.call_args.kwargs
        assert kwargs["db"] == db
        assert len(kwargs["objects_in"]) == 2
        assert kwargs["objects_in"][0]["entity_type"] == "ownership"
        assert kwargs["objects_in"][0]["entity_id"] == "org-1"
        assert kwargs["objects_in"][1]["is_primary"] is True

    async def test_create_contacts_batch_empty(self):
        from src.api.v1.system.contact import create_contacts_batch

        db = AsyncMock()
        user = SimpleNamespace(username="tester")

        with patch(
            "src.api.v1.system.contact.contact_crud.create_many_async",
            new=AsyncMock(return_value=[]),
        ) as mock_create_many:
            result = await create_contacts_batch(
                entity_type="ownership",
                entity_id="org-1",
                db=db,
                contacts_in=[],
                current_user=user,
            )

        assert result == []
        mock_create_many.assert_awaited_once()
