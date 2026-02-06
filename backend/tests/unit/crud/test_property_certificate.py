"""Simplified async tests for property certificate CRUD."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.property_certificate import (
    CRUDPropertyCertificate,
    CRUDPropertyOwner,
    property_certificate_crud,
    property_owner_crud,
)
from src.models.property_certificate import PropertyCertificate, PropertyOwner
from src.schemas.property_certificate import PropertyCertificateCreate

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


class TestPropertyCertificateCRUD:
    async def test_get_by_certificate_number_async(self, mock_db):
        crud = CRUDPropertyCertificate(PropertyCertificate)
        cert = PropertyCertificate(certificate_number="PC-001", certificate_type="property")

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = cert
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await crud.get_by_certificate_number_async(mock_db, "PC-001")
        assert result == cert

    async def test_create_with_owners_async(self, mock_db):
        crud = CRUDPropertyCertificate(PropertyCertificate)
        owner = PropertyOwner(id="owner-1")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [owner]
        mock_db.execute = AsyncMock(return_value=mock_result)

        obj_in = PropertyCertificateCreate(
            certificate_number="PC-002",
            certificate_type="property",
        )

        cert = await crud.create_with_owners_async(
            mock_db, obj_in=obj_in, owner_ids=["owner-1"]
        )

        assert cert.certificate_number == "PC-002"
        mock_db.add.assert_called_once()


class TestPropertyOwnerCRUD:
    async def test_search_by_id_number_async(self, mock_db):
        crud = CRUDPropertyOwner(PropertyOwner)
        owner = PropertyOwner(id="owner-1")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [owner]
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Stub encryption to deterministic value
        crud.sensitive_data_handler.encrypt_field = MagicMock(return_value="enc")

        results = await crud.search_by_id_number_async(mock_db, "123")
        assert results == [owner]


class TestCRUDInstances:
    def test_instances(self):
        assert property_certificate_crud is not None
        assert property_owner_crud is not None
