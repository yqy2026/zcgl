"""Simplified async tests for PropertyCertificateService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.property_certificate import PropertyCertificate
from src.schemas.property_certificate import PropertyCertificateCreate, PropertyCertificateUpdate
from src.services.property_certificate.service import PropertyCertificateService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db():
    return MagicMock()


class TestPropertyCertificateServiceBasics:
    async def test_list_certificates(self, mock_db):
        service = PropertyCertificateService(mock_db)
        certs = [PropertyCertificate(certificate_number="PC-1", certificate_type="property")]

        with patch(
            "src.services.property_certificate.service.property_certificate_crud.get_multi",
            new=AsyncMock(return_value=certs),
        ):
            result = await service.list_certificates()
            assert result == certs

    async def test_get_certificate(self, mock_db):
        service = PropertyCertificateService(mock_db)
        cert = PropertyCertificate(certificate_number="PC-1", certificate_type="property")

        with patch(
            "src.services.property_certificate.service.property_certificate_crud.get",
            new=AsyncMock(return_value=cert),
        ):
            result = await service.get_certificate("id-1")
            assert result == cert

    async def test_create_update_delete_certificate(self, mock_db):
        service = PropertyCertificateService(mock_db)
        cert = PropertyCertificate(certificate_number="PC-1", certificate_type="property")

        with patch(
            "src.services.property_certificate.service.property_certificate_crud.create",
            new=AsyncMock(return_value=cert),
        ):
            created = await service.create_certificate(
                PropertyCertificateCreate(
                    certificate_number="PC-1",
                    certificate_type="property",
                )
            )
            assert created == cert

        with patch(
            "src.services.property_certificate.service.property_certificate_crud.update",
            new=AsyncMock(return_value=cert),
        ):
            updated = await service.update_certificate(
                cert, PropertyCertificateUpdate(remarks="note")
            )
            assert updated == cert

        with patch(
            "src.services.property_certificate.service.property_certificate_crud.remove",
            new=AsyncMock(return_value=None),
        ):
            await service.delete_certificate("id-1")


class TestPropertyCertificateConfirmImport:
    async def test_confirm_import_existing(self, mock_db):
        service = PropertyCertificateService(mock_db)
        existing = PropertyCertificate(certificate_number="PC-EXIST", certificate_type="property")

        with patch(
            "src.services.property_certificate.service.property_certificate_crud.get_by_certificate_number_async",
            new=AsyncMock(return_value=existing),
        ):
            result = await service.confirm_import(
                {"certificate_number": "PC-EXIST", "extraction_data": {}}
            )
            assert result == existing

    async def test_confirm_import_creates_new(self, mock_db):
        service = PropertyCertificateService(mock_db)
        created = PropertyCertificate(certificate_number="PC-NEW", certificate_type="property")
        owner = MagicMock(id="owner-1")

        with patch(
            "src.services.property_certificate.service.property_certificate_crud.get_by_certificate_number_async",
            new=AsyncMock(return_value=None),
        ):
            with patch(
                "src.services.property_certificate.service.property_owner_crud.create_async",
                new=AsyncMock(return_value=owner),
            ):
                with patch(
                    "src.services.property_certificate.service.property_certificate_crud.create_with_owners_async",
                    new=AsyncMock(return_value=created),
                ) as mock_create_with_owners:
                    data = {
                        "certificate_number": "PC-NEW",
                        "extraction_data": {"certificate_type": "property"},
                        "owners": [
                            {"name": "Owner", "id_number": "123"}
                        ],
                    }
                    result = await service.confirm_import(data)

                    assert result == created
                    mock_create_with_owners.assert_called_once()
