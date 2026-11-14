"""Certificate deletion cannot cascade away temporal unit evidence."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import BaseBusinessError
from src.crud.archive_document import archive_document_repository
from src.crud.asset_unit_certificate import asset_unit_certificate_repository
from src.crud.property_certificate import property_certificate_crud
from src.services.property_certificate.service import PropertyCertificateService

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.mark.parametrize(("archives", "links"), [(True, False), (False, True)])
async def test_delete_protects_archive_or_unit_link_history(
    monkeypatch, archives, links
):
    lock = AsyncMock(return_value=True)
    remove = AsyncMock()
    monkeypatch.setattr(archive_document_repository, "lock_certificate", lock)
    monkeypatch.setattr(
        archive_document_repository,
        "has_for_certificate",
        AsyncMock(return_value=archives),
    )
    monkeypatch.setattr(
        asset_unit_certificate_repository,
        "has_links_for_certificate",
        AsyncMock(return_value=links),
        raising=False,
    )
    monkeypatch.setattr(property_certificate_crud, "remove", remove)
    db = MagicMock()
    with pytest.raises(BaseBusinessError) as error:
        await PropertyCertificateService(db).delete_certificate("certificate")
    assert error.value.code == "ARCHIVE_HISTORY_PROTECTED"
    lock.assert_awaited_once_with(db, certificate_id="certificate")
    remove.assert_not_awaited()


async def test_unreferenced_certificate_remains_deletable(monkeypatch):
    monkeypatch.setattr(
        archive_document_repository, "lock_certificate", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        archive_document_repository,
        "has_for_certificate",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        asset_unit_certificate_repository,
        "has_links_for_certificate",
        AsyncMock(return_value=False),
        raising=False,
    )
    remove = AsyncMock()
    monkeypatch.setattr(property_certificate_crud, "remove", remove)
    db = MagicMock()
    await PropertyCertificateService(db).delete_certificate("certificate")
    remove.assert_awaited_once_with(db, id="certificate")
