"""Simplified async tests for PropertyCertificateService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.crud.query_builder import TenantFilter
from src.models.property_certificate import PropertyCertificate
from src.schemas.property_certificate import (
    PropertyCertificateCreate,
    PropertyCertificateUpdate,
)
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

    async def test_list_certificates_with_current_user_resolves_tenant_filter(self, mock_db):
        service = PropertyCertificateService(mock_db)
        tenant_filter = TenantFilter(organization_ids=["org-1"])
        certs = [PropertyCertificate(certificate_number="PC-1", certificate_type="property")]

        with patch.object(
            service,
            "_resolve_tenant_filter",
            new=AsyncMock(return_value=tenant_filter),
        ) as mock_resolve:
            with patch(
                "src.services.property_certificate.service.property_certificate_crud.get_multi",
                new=AsyncMock(return_value=certs),
            ) as mock_get_multi:
                result = await service.list_certificates(current_user_id="user-1")

        assert result == certs
        mock_resolve.assert_awaited_once_with(
            current_user_id="user-1",
            tenant_filter=None,
        )
        mock_get_multi.assert_awaited_once_with(
            mock_db,
            skip=0,
            limit=100,
            tenant_filter=tenant_filter,
        )

    async def test_get_certificate_fail_closed_when_no_accessible_org(self, mock_db):
        service = PropertyCertificateService(mock_db)

        with patch.object(
            service,
            "_resolve_tenant_filter",
            new=AsyncMock(return_value=TenantFilter(organization_ids=[])),
        ):
            with patch(
                "src.services.property_certificate.service.property_certificate_crud.get",
                new=AsyncMock(),
            ) as mock_get:
                result = await service.get_certificate(
                    "id-1",
                    current_user_id="user-1",
                )

        assert result is None
        mock_get.assert_not_awaited()

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
                {
                    "extracted_data": {"certificate_number": "PC-EXIST"},
                    "asset_ids": [],
                    "should_create_new_asset": True,
                }
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
                "src.services.property_certificate.service.property_owner_crud.create_multi_async",
                new=AsyncMock(return_value=[owner]),
            ):
                with patch(
                    "src.services.property_certificate.service.property_certificate_crud.create_with_owners_async",
                    new=AsyncMock(return_value=created),
                ) as mock_create_with_owners:
                    data = {
                        "extracted_data": {
                            "certificate_number": "PC-NEW",
                            "certificate_type": "property",
                        },
                        "asset_ids": ["asset-1"],
                        "asset_link_id": "asset-1",
                        "should_create_new_asset": False,
                        "owners": [
                            {"name": "Owner", "id_number": "123"}
                        ],
                    }
                    result = await service.confirm_import(data)

                    assert result == created
                    mock_create_with_owners.assert_called_once()
                    kwargs = mock_create_with_owners.call_args.kwargs
                    assert kwargs["asset_ids"] == ["asset-1"]
