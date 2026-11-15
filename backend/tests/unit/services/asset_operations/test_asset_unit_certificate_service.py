"""Certificate reads authorize the unit before examining its links."""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exception_handler import (
    BaseBusinessError,
    PartyScopeForbiddenError,
    ResourceNotFoundError,
)
from src.services.asset_operations.asset_unit_certificate_service import (
    AssetUnitCertificateService,
)
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.fixture(autouse=True)
def certificate_lock(monkeypatch):
    from src.crud.archive_document import archive_document_repository

    lock = AsyncMock(return_value=True)
    monkeypatch.setattr(archive_document_repository, "lock_certificate", lock)
    return lock


async def test_reopening_preserves_the_old_range(certificate_lock):
    from types import SimpleNamespace

    old = SimpleNamespace(
        effective_from=date(2026, 1, 1), effective_to=date(2026, 10, 31)
    )
    repository = MagicMock(find_link=AsyncMock(return_value=old))
    repository.is_known_certificate = AsyncMock(return_value=True)
    service = AssetUnitCertificateService(
        units=MagicMock(get=AsyncMock(return_value=MagicMock())),
        certificates=MagicMock(get=AsyncMock(return_value=MagicMock())),
        repository=repository,
    )
    with pytest.raises(BaseBusinessError) as raised:
        await service.link_certificate(
            MagicMock(),
            unit_id="unit",
            certificate_id="cert",
            effective_from=date(2027, 1, 1),
            effective_to=None,
            scope=scope(),
            actor_id="actor",
        )
    assert raised.value.code == "CERTIFICATE_LINK_HISTORY_PROTECTED"
    assert old.effective_from == date(2026, 1, 1)
    assert old.effective_to == date(2026, 10, 31)
    repository.update_interval.assert_not_called()


@pytest.mark.parametrize(
    "start,unlink",
    [
        (date(2026, 1, 1), date(2026, 1, 1)),
        (date(2026, 11, 2), date(2026, 11, 2)),
        (date(2026, 1, 1), date(2026, 10, 1)),
    ],
)
async def test_unlink_cannot_erase_past_or_today_start(start, unlink):
    repository = MagicMock(
        find_active=AsyncMock(
            return_value=MagicMock(effective_from=start, effective_to=None)
        )
    )
    repository.is_known_certificate = AsyncMock(return_value=True)
    service = AssetUnitCertificateService(
        units=MagicMock(get=AsyncMock(return_value=MagicMock())),
        repository=repository,
        clock=lambda: datetime(2026, 11, 2, tzinfo=UTC),
    )
    with pytest.raises(BaseBusinessError) as raised:
        await service.unlink_certificate(
            MagicMock(),
            unit_id="unit",
            certificate_id="cert",
            effective_from=unlink,
            scope=scope(),
            actor_id="actor",
        )
    assert raised.value.code == "CERTIFICATE_LINK_HISTORY_PROTECTED"
    repository.remove.assert_not_called()
    repository.close_interval.assert_not_called()


async def test_write_locks_certificate_before_unit(certificate_lock):
    calls = []

    async def lock(*args, **kwargs):
        calls.append("certificate")
        return True

    async def unit(*args, **kwargs):
        calls.append("unit")
        return None

    certificate_lock.side_effect = lock
    service = AssetUnitCertificateService(
        units=MagicMock(get=AsyncMock(side_effect=unit))
    )
    with pytest.raises(ResourceNotFoundError):
        await service.unlink_certificate(
            MagicMock(),
            unit_id="unit",
            certificate_id="cert",
            effective_from=date(2027, 1, 1),
            scope=scope(),
            actor_id="actor",
        )
    assert calls == ["certificate", "unit"]


def scope(mode="owner", error=None):
    return EffectivePartyScope(
        user_id="reader",
        source="explicit",
        scope_mode=mode,
        owner_party_ids=["owner"] if mode == "owner" else [],
        error_code=error,
    )


@pytest.mark.parametrize(
    "effective_scope", [scope("none"), scope(error="PARTY_SCOPE_MISSING")]
)
async def test_missing_scope_never_queries_certificates(effective_scope):
    units, certificates = MagicMock(), MagicMock()
    service = AssetUnitCertificateService(units=units, repository=certificates)
    with pytest.raises(PartyScopeForbiddenError):
        await service.list_for_unit(MagicMock(), unit_id="unit", scope=effective_scope)
    units.get.assert_not_called()
    certificates.list.assert_not_called()


async def test_invisible_unit_is_not_found_before_certificate_query():
    units, certificates = MagicMock(), MagicMock()
    units.get = AsyncMock(return_value=None)
    service = AssetUnitCertificateService(units=units, repository=certificates)
    with pytest.raises(ResourceNotFoundError):
        await service.list_for_unit(MagicMock(), unit_id="unit", scope=scope())
    certificates.list.assert_not_called()


@pytest.mark.parametrize(
    "as_of, expected", [(None, date(2026, 11, 2)), (date(2020, 1, 1), date(2020, 1, 1))]
)
async def test_visible_unit_uses_requested_date_or_shanghai_today(as_of, expected):
    units, certificates = MagicMock(), MagicMock()
    units.get = AsyncMock(return_value=MagicMock())
    certificates.list = AsyncMock(return_value=["certificate"])
    service = AssetUnitCertificateService(
        units=units,
        repository=certificates,
        clock=lambda: datetime(2026, 11, 1, 17, tzinfo=UTC),
    )
    db, effective_scope = MagicMock(), scope()
    assert await service.list_for_unit(
        db, unit_id="unit", scope=effective_scope, as_of=as_of
    ) == ["certificate"]
    units.get.assert_awaited_once_with(db, unit_id="unit", scope=effective_scope)
    certificates.list.assert_awaited_once_with(db, unit_id="unit", as_of=expected)


@pytest.mark.parametrize(
    "effective_scope",
    [
        EffectivePartyScope(
            user_id="reader",
            source="explicit",
            scope_mode="manager",
            owner_party_ids=["owner"],
        ),
        EffectivePartyScope(
            user_id="reader",
            source="explicit",
            scope_mode="owner",
            manager_party_ids=["manager"],
        ),
        EffectivePartyScope(user_id="reader", source="explicit", scope_mode="all"),
    ],
)
async def test_wrong_or_empty_scope_axis_fails_before_reads(effective_scope):
    units, certificates = MagicMock(), MagicMock()
    with pytest.raises(PartyScopeForbiddenError):
        await AssetUnitCertificateService(
            units=units, repository=certificates
        ).list_for_unit(MagicMock(), unit_id="unit", scope=effective_scope)
    units.get.assert_not_called()
    certificates.list.assert_not_called()


@pytest.mark.parametrize(
    "effective_scope",
    [
        EffectivePartyScope(
            user_id="reader",
            source="explicit",
            scope_mode="manager",
            manager_party_ids=["manager"],
        ),
        EffectivePartyScope(
            user_id="reader",
            source="explicit",
            scope_mode="all",
            owner_party_ids=["owner"],
        ),
        EffectivePartyScope(
            user_id="reader", source="unrestricted", scope_mode="unrestricted"
        ),
    ],
)
async def test_supported_scope_axes_still_require_visible_unit(effective_scope):
    units, certificates = MagicMock(), MagicMock()
    units.get = AsyncMock(return_value=None)
    with pytest.raises(ResourceNotFoundError):
        await AssetUnitCertificateService(
            units=units, repository=certificates
        ).list_for_unit(MagicMock(), unit_id="hidden", scope=effective_scope)
    units.get.assert_awaited_once()
    certificates.list.assert_not_called()


@pytest.mark.parametrize(
    "effective_scope", [scope("none"), scope(error="PARTY_SCOPE_MISSING")]
)
async def test_link_missing_scope_never_touches_units(effective_scope):
    units, certificates, repository = (
        MagicMock(is_known_certificate=AsyncMock(return_value=True)),
        MagicMock(),
        MagicMock(),
    )
    repository.is_known_certificate = AsyncMock(return_value=True)
    service = AssetUnitCertificateService(
        units=units, certificates=certificates, repository=repository
    )
    with pytest.raises(PartyScopeForbiddenError):
        await service.link_certificate(
            MagicMock(),
            unit_id="unit",
            certificate_id="cert-1",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            scope=effective_scope,
            actor_id="actor",
        )
    units.get.assert_not_called()


async def test_link_invisible_unit_is_not_found_before_certificate_lookup():
    units, certificates, repository = (
        MagicMock(is_known_certificate=AsyncMock(return_value=True)),
        MagicMock(),
        MagicMock(),
    )
    units.get = AsyncMock(return_value=None)
    repository.is_known_certificate = AsyncMock(return_value=True)
    service = AssetUnitCertificateService(
        units=units, certificates=certificates, repository=repository
    )
    with pytest.raises(ResourceNotFoundError):
        await service.link_certificate(
            MagicMock(),
            unit_id="hidden",
            certificate_id="cert-1",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            scope=scope(),
            actor_id="actor",
        )
    certificates.get.assert_not_called()


async def test_link_unknown_certificate_is_rejected():
    units, certificates, repository = (
        MagicMock(is_known_certificate=AsyncMock(return_value=True)),
        MagicMock(),
        MagicMock(),
    )
    units.get = AsyncMock(return_value=MagicMock(id="unit"))
    certificates.get = AsyncMock(return_value=None)
    repository.is_known_certificate = AsyncMock(return_value=True)
    service = AssetUnitCertificateService(
        units=units, certificates=certificates, repository=repository
    )
    with pytest.raises(ResourceNotFoundError):
        await service.link_certificate(
            MagicMock(),
            unit_id="unit",
            certificate_id="missing",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            scope=scope(),
            actor_id="actor",
        )
    repository.add.assert_not_called()


async def test_link_inverted_range_is_rejected():
    units, certificates, repository = (
        MagicMock(is_known_certificate=AsyncMock(return_value=True)),
        MagicMock(),
        MagicMock(),
    )
    units.get = AsyncMock(return_value=MagicMock(id="unit"))
    certificates.get = AsyncMock(return_value=MagicMock(id="cert-1"))
    repository.is_known_certificate = AsyncMock(return_value=True)
    service = AssetUnitCertificateService(
        units=units, certificates=certificates, repository=repository
    )

    with pytest.raises(BaseBusinessError) as raised:
        await service.link_certificate(
            MagicMock(),
            unit_id="unit",
            certificate_id="cert-1",
            effective_from=date(2026, 6, 1),
            effective_to=date(2026, 5, 1),
            scope=scope(),
            actor_id="actor",
        )
    assert raised.value.code == "CERTIFICATE_LINK_RANGE_INVALID"
    repository.find_link.assert_not_called()


async def test_link_overlapping_interval_conflicts():
    units, certificates, repository = (
        MagicMock(is_known_certificate=AsyncMock(return_value=True)),
        MagicMock(),
        MagicMock(),
    )
    units.get = AsyncMock(return_value=MagicMock(id="unit"))
    certificates.get = AsyncMock(return_value=MagicMock(id="cert-1"))
    repository.find_link = AsyncMock(
        return_value=MagicMock(effective_from=date(2026, 1, 1), effective_to=None)
    )
    repository.is_known_certificate = AsyncMock(return_value=True)
    service = AssetUnitCertificateService(
        units=units, certificates=certificates, repository=repository
    )

    with pytest.raises(BaseBusinessError) as raised:
        await service.link_certificate(
            MagicMock(),
            unit_id="unit",
            certificate_id="cert-1",
            effective_from=date(2027, 1, 1),
            effective_to=None,
            scope=scope(),
            actor_id="actor",
        )
    assert raised.value.code == "CERTIFICATE_LINK_OVERLAP"
    assert raised.value.status_code == 409
    repository.add.assert_not_called()
    repository.update_interval.assert_not_called()


async def test_link_success_adds_row_audits_and_commits():
    db = MagicMock(commit=AsyncMock())
    unit = MagicMock(id="unit")
    units = MagicMock()
    units.get = AsyncMock(return_value=unit)
    certificates = MagicMock()
    certificates.get = AsyncMock(return_value=MagicMock(id="cert-1"))
    repository = MagicMock(is_known_certificate=AsyncMock(return_value=True))
    repository.find_link = AsyncMock(return_value=None)
    repository.add = AsyncMock()
    repository.list = AsyncMock(return_value=["certificate"])
    audit = AsyncMock()
    repository.is_known_certificate = AsyncMock(return_value=True)
    service = AssetUnitCertificateService(
        units=units, certificates=certificates, repository=repository, audit=audit
    )
    result = await service.link_certificate(
        db,
        unit_id="unit",
        certificate_id="cert-1",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        scope=scope(),
        actor_id="actor",
    )
    assert result == ["certificate"]
    repository.add.assert_awaited_once_with(
        db,
        unit_id="unit",
        certificate_id="cert-1",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
    )
    audit.assert_awaited_once()
    assert audit.await_args.kwargs["action"] == "certificate_link_added"
    assert audit.await_args.kwargs["actor_id"] == "actor"
    db.commit.assert_awaited_once()
    repository.list.assert_awaited_once_with(db, unit_id="unit", as_of=date(2026, 1, 1))


async def test_unlink_without_active_interval_is_not_found():
    units, certificates, repository = (
        MagicMock(is_known_certificate=AsyncMock(return_value=True)),
        MagicMock(),
        MagicMock(),
    )
    units.get = AsyncMock(return_value=MagicMock(id="unit"))
    repository.find_active = AsyncMock(return_value=None)
    repository.is_known_certificate = AsyncMock(return_value=True)
    service = AssetUnitCertificateService(
        units=units, certificates=certificates, repository=repository
    )
    with pytest.raises(ResourceNotFoundError):
        await service.unlink_certificate(
            MagicMock(),
            unit_id="unit",
            certificate_id="cert-1",
            effective_from=date(2026, 6, 1),
            scope=scope(),
            actor_id="actor",
        )


async def test_unlink_not_yet_started_interval_removes_the_row():
    db = MagicMock(commit=AsyncMock())
    units = MagicMock()
    units.get = AsyncMock(return_value=MagicMock(id="unit"))
    repository = MagicMock(is_known_certificate=AsyncMock(return_value=True))
    repository.find_active = AsyncMock(
        return_value=MagicMock(
            asset_unit_id="unit",
            certificate_id="cert-1",
            effective_from=date(2026, 6, 1),
            effective_to=None,
        )
    )
    repository.remove = AsyncMock()
    repository.list = AsyncMock(return_value=[])
    audit = AsyncMock()
    repository.is_known_certificate = AsyncMock(return_value=True)
    service = AssetUnitCertificateService(
        units=units,
        repository=repository,
        audit=audit,
        clock=lambda: datetime(2026, 5, 1, tzinfo=UTC),
    )
    await service.unlink_certificate(
        db,
        unit_id="unit",
        certificate_id="cert-1",
        effective_from=date(2026, 6, 1),
        scope=scope(),
        actor_id="actor",
    )
    repository.remove.assert_awaited_once()
    repository.close_interval.assert_not_called()
    assert audit.await_args.kwargs["action"] == "certificate_link_removed"
    db.commit.assert_awaited_once()


async def test_unlink_closes_interval_through_the_day_before():
    db = MagicMock(commit=AsyncMock())
    units = MagicMock()
    units.get = AsyncMock(return_value=MagicMock(id="unit"))
    link = MagicMock(
        asset_unit_id="unit",
        certificate_id="cert-1",
        effective_from=date(2026, 1, 1),
        effective_to=None,
    )
    repository = MagicMock(is_known_certificate=AsyncMock(return_value=True))
    repository.find_active = AsyncMock(return_value=link)
    repository.close_interval = AsyncMock()
    repository.list = AsyncMock(return_value=["certificate"])
    audit = AsyncMock()
    repository.is_known_certificate = AsyncMock(return_value=True)
    service = AssetUnitCertificateService(
        units=units,
        repository=repository,
        audit=audit,
        clock=lambda: datetime(2026, 5, 1, tzinfo=UTC),
    )
    result = await service.unlink_certificate(
        db,
        unit_id="unit",
        certificate_id="cert-1",
        effective_from=date(2026, 6, 1),
        scope=scope(),
        actor_id="actor",
    )
    assert result == ["certificate"]
    repository.close_interval.assert_awaited_once_with(
        db, link=link, effective_to=date(2026, 5, 31)
    )
    repository.remove.assert_not_called()
    assert audit.await_args.kwargs["before"]["effective_to"] is None
    assert audit.await_args.kwargs["after"]["effective_to"] == "2026-05-31"
    db.commit.assert_awaited_once()


@pytest.mark.parametrize(
    ("existing_to", "new_from", "conflicts"),
    [
        (date(2026, 5, 10), date(2026, 5, 10), True),
        (date(2026, 5, 10), date(2026, 5, 9), True),
        (date(2026, 5, 10), date(2026, 5, 11), False),
    ],
)
async def test_link_closed_range_boundary_is_inclusive(
    existing_to: date, new_from: date, conflicts: bool
):
    """A stored end is inclusive; even nonoverlapping rebinds preserve the old row."""
    units, certificates, repository = (
        MagicMock(is_known_certificate=AsyncMock(return_value=True)),
        MagicMock(),
        MagicMock(),
    )
    units.get = AsyncMock(return_value=MagicMock(id="unit"))
    certificates.get = AsyncMock(return_value=MagicMock(id="cert-1"))
    repository.find_link = AsyncMock(
        return_value=MagicMock(
            effective_from=date(2026, 1, 1), effective_to=existing_to
        )
    )
    repository.update_interval = AsyncMock()
    repository.list = AsyncMock(return_value=[])
    repository.is_known_certificate = AsyncMock(return_value=True)
    service = AssetUnitCertificateService(
        units=units, certificates=certificates, repository=repository
    )
    if conflicts:
        with pytest.raises(BaseBusinessError) as raised:
            await service.link_certificate(
                MagicMock(),
                unit_id="unit",
                certificate_id="cert-1",
                effective_from=new_from,
                effective_to=None,
                scope=scope(),
                actor_id="actor",
            )
        assert raised.value.code == "CERTIFICATE_LINK_OVERLAP"
        repository.update_interval.assert_not_called()
    else:
        with pytest.raises(BaseBusinessError) as raised:
            await service.link_certificate(
                MagicMock(),
                unit_id="unit",
                certificate_id="cert-1",
                effective_from=new_from,
                effective_to=None,
                scope=scope(),
                actor_id="actor",
            )
        assert raised.value.code == "CERTIFICATE_LINK_HISTORY_PROTECTED"
        repository.update_interval.assert_not_called()


async def test_unlink_single_day_range_keeps_from_equal_to_end():
    db = MagicMock(commit=AsyncMock())
    units = MagicMock()
    units.get = AsyncMock(return_value=MagicMock(id="unit"))
    link = MagicMock(
        asset_unit_id="unit",
        certificate_id="cert-1",
        effective_from=date(2026, 5, 10),
        effective_to=None,
    )
    repository = MagicMock(is_known_certificate=AsyncMock(return_value=True))
    repository.find_active = AsyncMock(return_value=link)
    repository.close_interval = AsyncMock()
    repository.list = AsyncMock(return_value=[])
    repository.is_known_certificate = AsyncMock(return_value=True)
    service = AssetUnitCertificateService(
        units=units,
        repository=repository,
        audit=AsyncMock(),
        clock=lambda: datetime(2026, 5, 1, tzinfo=UTC),
    )
    await service.unlink_certificate(
        db,
        unit_id="unit",
        certificate_id="cert-1",
        effective_from=date(2026, 5, 11),
        scope=scope(),
        actor_id="actor",
    )
    repository.close_interval.assert_awaited_once_with(
        db, link=link, effective_to=date(2026, 5, 10)
    )


async def test_invisible_target_is_not_read_or_written():
    units = MagicMock(get=AsyncMock(return_value=MagicMock()))
    certificates = MagicMock(get=AsyncMock())
    repository = MagicMock(
        is_known_certificate=AsyncMock(return_value=False),
        has_current_holder=AsyncMock(return_value=False),
    )
    service = AssetUnitCertificateService(
        units=units, certificates=certificates, repository=repository
    )
    with pytest.raises(ResourceNotFoundError):
        await service.link_certificate(
            MagicMock(),
            unit_id="unit",
            certificate_id="hidden",
            effective_from=date(2027, 1, 1),
            effective_to=None,
            scope=scope(),
            actor_id="actor",
        )
    certificates.get.assert_not_called()
    repository.add.assert_not_called()


@pytest.mark.parametrize(
    "known,holder,allowed",
    [(True, False, True), (False, True, True), (False, False, False)],
)
async def test_target_qualification_uses_known_or_locked_unit_holder(
    known, holder, allowed
):
    unit = MagicMock(owner_party_id="locked-owner")
    certificates = MagicMock(get=AsyncMock(return_value=MagicMock()))
    repository = MagicMock(
        is_known_certificate=AsyncMock(return_value=known),
        has_current_holder=AsyncMock(return_value=holder),
        find_link=AsyncMock(return_value=None),
        add=AsyncMock(),
        list=AsyncMock(return_value=[]),
    )
    service = AssetUnitCertificateService(
        units=MagicMock(get=AsyncMock(return_value=unit)),
        certificates=certificates,
        repository=repository,
        audit=AsyncMock(),
        clock=lambda: datetime(2026, 11, 2, 12, tzinfo=UTC),
    )
    db = MagicMock(commit=AsyncMock())
    operation = service.link_certificate(
        db,
        unit_id="unit",
        certificate_id="cert",
        effective_from=date(2027, 1, 1),
        effective_to=None,
        scope=scope(),
        actor_id="actor",
    )
    if allowed:
        await operation
        repository.add.assert_awaited_once()
    else:
        with pytest.raises(ResourceNotFoundError):
            await operation
        certificates.get.assert_not_called()
        repository.add.assert_not_called()
        db.commit.assert_not_called()
    if not known:
        repository.has_current_holder.assert_awaited_once_with(
            db,
            certificate_id="cert",
            party_id="locked-owner",
            at=datetime(2026, 11, 2, 12),
        )
