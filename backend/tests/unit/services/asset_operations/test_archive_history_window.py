"""Historical as_of windows for the archive projection."""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace as Row
from unittest.mock import AsyncMock

import pytest

from src.crud.archive_matrix import ArchiveMatrixFacts
from src.models.asset_contract import UpstreamContract
from src.services.asset_operations.archive_matrix_service import (
    ArchiveMatrixService,
    categories,
    project_requirements,
)
from src.services.party_scope_resolver import EffectivePartyScope

TODAY = date(2026, 11, 3)


def facts(**changes):
    fields = dict(
        units=(),
        upstream=(),
        terminal=(),
        upstream_links=(),
        terminal_links=(),
        certificates=(),
        certificate_links=(),
        events=(),
        statements=(),
        attachments=(),
        documents=(),
        successors={},
    )
    fields.update(changes)
    return ArchiveMatrixFacts(**fields)


def agreement(link_to=date(2030, 1, 1)):
    contract = UpstreamContract(
        id="c",
        contract_type="management_agreement",
        start_date=date(2020, 1, 1),
        end_date=link_to,
        contract_number="协议",
        scan_document_id=None,
    )
    link = Row(
        upstream_contract_id="c",
        asset_unit_id="u",
        effective_from=date(2020, 1, 1),
        effective_to=None,
    )
    return contract, link


@pytest.mark.unit
def test_statement_superseded_after_as_of_still_counts():
    contract, link = agreement()
    fee = Row(
        id="fee",
        status="superseded",
        confirmed_at=datetime(2026, 9, 1, tzinfo=UTC),
        upstream_contract_ids=["c"],
        statement_number="对账",
        stamped_document_id=None,
    )
    base = dict(
        upstream=(contract,),
        upstream_links=(link,),
        statements=(fee,),
        superseded_at={"fee": datetime(2026, 10, 1, tzinfo=UTC)},
    )
    at_september = project_requirements(facts(**base), date(2026, 9, 15))
    assert [
        r.document_type
        for r in at_september
        if r.document_type == "management_fee_statement"
    ] == ["management_fee_statement"]
    at_november = project_requirements(facts(**base), date(2026, 11, 1))
    assert [
        r.document_type
        for r in at_november
        if r.document_type == "management_fee_statement"
    ] == []


@pytest.mark.unit
def test_statement_confirmed_after_as_of_does_not_count():
    contract, link = agreement()
    fee = Row(
        id="fee",
        status="confirmed",
        confirmed_at=datetime(2026, 10, 1, tzinfo=UTC),
        upstream_contract_ids=["c"],
        statement_number="对账",
        stamped_document_id=None,
    )
    rows = project_requirements(
        facts(upstream=(contract,), upstream_links=(link,), statements=(fee,)),
        date(2026, 9, 15),
    )
    assert [r.document_type for r in rows if r.document_type == "management_fee_statement"] == []


@pytest.mark.unit
def test_stamp_bound_after_as_of_is_not_existing():
    contract, link = agreement()
    fee = Row(
        id="fee",
        status="confirmed",
        confirmed_at=datetime(2026, 9, 1, tzinfo=UTC),
        upstream_contract_ids=["c"],
        statement_number="对账",
        stamped_document_id="stamp",
    )
    base = dict(
        upstream=(contract,),
        upstream_links=(link,),
        statements=(fee,),
        attachments=(
            Row(
                id="stamp",
                owner_type="management_fee_statement",
                owner_id="fee",
                created_at=datetime(2026, 10, 5, tzinfo=UTC),
            ),
        ),
    )
    rows = project_requirements(facts(**base), date(2026, 9, 15))
    assert [
        r.existing
        for r in rows
        if r.document_type == "management_fee_statement"
    ] == [False]
    # An archive version bound before as_of keeps the statement existing even
    # though the current fact pointer has moved to a later file.
    more_attachments = (
        Row(
            id="old-stamp",
            owner_type="management_fee_statement",
            owner_id="fee",
            created_at=datetime(2026, 9, 2, tzinfo=UTC),
        ),
    )
    chained = facts(
        **{**base, "attachments": base["attachments"] + more_attachments},
        documents=(
            Row(
                id="sd1",
                uploaded_at=datetime(2026, 9, 2, tzinfo=UTC),
                replaces_document_id=None,
                target_type="management_fee_statement",
                target_id="fee",
                document_type="management_fee_statement",
                attachment_id="old-stamp",
            ),
        ),
    )
    rows = project_requirements(chained, date(2026, 9, 15))
    assert [
        r.existing
        for r in rows
        if r.document_type == "management_fee_statement"
    ] == [True]


@pytest.mark.unit
def test_document_replaced_after_as_of_remains_current():
    rows = project_requirements(
        facts(
            certificates=(Row(id="c", certificate_number="证"),),
            certificate_links=(Row(certificate_id="c", asset_unit_id="a"),),
            documents=(
                Row(
                    id="d1",
                    uploaded_at=datetime(2026, 1, 1, tzinfo=UTC),
                    replaces_document_id=None,
                    target_type="property_certificate",
                    target_id="c",
                    document_type="property_certificate",
                    attachment_id="f1",
                ),
                Row(
                    id="d2",
                    uploaded_at=datetime(2026, 10, 1, tzinfo=UTC),
                    replaces_document_id="d1",
                    target_type="property_certificate",
                    target_id="c",
                    document_type="property_certificate",
                    attachment_id="f2",
                ),
            ),
            attachments=(
                Row(
                    id="f1",
                    owner_type="property_certificate",
                    owner_id="c",
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                ),
                Row(
                    id="f2",
                    owner_type="property_certificate",
                    owner_id="c",
                    created_at=datetime(2026, 10, 1, tzinfo=UTC),
                ),
            ),
        ),
        date(2026, 9, 15),
    )
    assert categories(rows)[0].existing == 1


@pytest.mark.unit
def test_supplement_registration_window_at_as_of():
    contract, link = agreement()
    registered = Row(
        id="s1",
        contract_kind="upstream",
        contract_id="c",
        agreement_number="补-1",
        title="免租期",
        created_at=datetime(2026, 1, 10, tzinfo=UTC),
        withdrawn_at=None,
    )
    withdrawn_late = Row(
        id="s2",
        contract_kind="upstream",
        contract_id="c",
        agreement_number="补-2",
        title="调租",
        created_at=datetime(2026, 1, 10, tzinfo=UTC),
        withdrawn_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    registered_late = Row(
        id="s3",
        contract_kind="upstream",
        contract_id="c",
        agreement_number="补-3",
        title="新签",
        created_at=datetime(2026, 10, 1, tzinfo=UTC),
        withdrawn_at=None,
    )
    base = dict(
        upstream=(contract,),
        upstream_links=(link,),
        supplements=(registered, withdrawn_late, registered_late),
    )
    at_september = project_requirements(facts(**base), date(2026, 9, 15))
    assert sorted(
        r.target_id for r in at_september if r.document_type == "supplement"
    ) == ["s1", "s2"]
    at_november = project_requirements(facts(**base), date(2026, 11, 1))
    assert sorted(
        r.target_id for r in at_november if r.document_type == "supplement"
    ) == ["s1", "s3"]


@pytest.mark.unit
async def test_future_as_of_is_rejected_before_loading():
    repo = AsyncMock()
    service = ArchiveMatrixService(repository=repo, clock=lambda: TODAY)
    scope = EffectivePartyScope(
        user_id="u",
        source="explicit",
        scope_mode="owner",
        owner_party_ids=["o"],
    )
    with pytest.raises(Exception) as error:
        await service.completion(AsyncMock(), scope=scope, as_of=TODAY + timedelta(days=1))
    assert getattr(error.value, "code", None) == "ARCHIVE_AS_OF_INVALID"
    repo.load.assert_not_awaited()
