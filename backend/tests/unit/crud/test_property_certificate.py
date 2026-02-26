"""Simplified async tests for property certificate CRUD."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crud.property_certificate import (
    CRUDPropertyCertificate,
    CRUDPropertyOwner,
    property_certificate_crud,
    property_owner_crud,
)
from src.crud.query_builder import PartyFilter
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

    async def test_get_with_tenant_filter_applies_tenant_filter(self, mock_db):
        crud = CRUDPropertyCertificate(PropertyCertificate)
        cert = PropertyCertificate(certificate_number="PC-001", certificate_type="property")
        execute_result = MagicMock()
        execute_result.scalars.return_value.first.return_value = cert
        mock_db.execute = AsyncMock(return_value=execute_result)

        party_filter = PartyFilter(party_ids=["org-1"])
        with patch.object(
            crud.query_builder,
            "apply_party_filter",
            side_effect=lambda stmt, _tf: stmt,
        ) as mock_apply_party_filter:
            result = await crud.get(
                mock_db,
                id="cert-1",
                party_filter=party_filter,
            )

        assert result == cert
        assert mock_apply_party_filter.call_args.args[1] == party_filter

    async def test_get_multi_with_empty_tenant_filter_is_fail_closed(self, mock_db):
        crud = CRUDPropertyCertificate(PropertyCertificate)
        execute_result = MagicMock()
        execute_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=execute_result)

        result = await crud.get_multi(
            mock_db,
            party_filter=PartyFilter(party_ids=[]),
        )

        assert result == []
        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "false" in compiled.lower()


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
    async def test_instances(self):
        assert property_certificate_crud is not None
        assert property_owner_crud is not None
