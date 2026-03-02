"""Simplified async tests for property certificate CRUD."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.property_certificate import (
    CRUDPropertyCertificate,
    property_certificate_crud,
)
from src.crud.query_builder import PartyFilter
from src.models.property_certificate import PropertyCertificate
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
        cert = PropertyCertificate(certificate_number="PC-001", certificate_type="other")

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = cert
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await crud.get_by_certificate_number_async(mock_db, "PC-001")
        assert result == cert

    async def test_create_with_owners_async(self, mock_db):
        crud = CRUDPropertyCertificate(PropertyCertificate)
        obj_in = PropertyCertificateCreate(
            certificate_number="PC-002",
            certificate_type="other",
        )

        cert = await crud.create_with_owners_async(
            mock_db,
            obj_in=obj_in,
            owner_ids=["party-1", "party-2"],
        )

        assert cert.certificate_number == "PC-002"
        assert mock_db.add.call_count == 3

    async def test_get_with_party_filter(self, mock_db):
        crud = CRUDPropertyCertificate(PropertyCertificate)
        cert = PropertyCertificate(certificate_number="PC-001", certificate_type="other")
        execute_result = MagicMock()
        execute_result.scalars.return_value.first.return_value = cert
        mock_db.execute = AsyncMock(return_value=execute_result)

        result = await crud.get(
            mock_db,
            id="cert-1",
            party_filter=PartyFilter(party_ids=["party-1"]),
        )

        assert result == cert

    async def test_get_multi_with_empty_party_filter_is_fail_closed(self, mock_db):
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


class TestCRUDInstances:
    async def test_instances(self):
        assert property_certificate_crud is not None
