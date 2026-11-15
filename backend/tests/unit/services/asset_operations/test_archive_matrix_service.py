from unittest.mock import AsyncMock

import pytest

from src.services.asset_operations.archive_matrix_service import ArchiveMatrixService
from src.services.party_scope_resolver import EffectivePartyScope


@pytest.mark.unit
async def test_invalid_scope_fails_before_repository():
    repo = AsyncMock()
    service = ArchiveMatrixService(repository=repo)
    with pytest.raises(Exception) as error:
        await service.completion(
            AsyncMock(),
            scope=EffectivePartyScope(
                user_id="u", source="explicit", scope_mode="owner"
            ),
        )
    assert getattr(error.value, "status_code", None) == 403
    repo.load.assert_not_awaited()


from datetime import UTC, date, datetime
from types import SimpleNamespace as Row

from src.crud.archive_matrix import ArchiveMatrixFacts
from src.services.asset_operations.archive_matrix_service import (
    categories,
    project_requirements,
)

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


@pytest.mark.unit
def test_zero_denominator_and_unsupported_are_distinct():
    result = categories(())
    assert result[0].required == 0
    assert result[0].completion_rate is None
    assert result[3].required == 0
    assert result[3].supported is True


@pytest.mark.unit
def test_shared_certificate_and_multiple_versions_count_once():
    rows = project_requirements(
        facts(
            certificates=(Row(id="c", certificate_number="证"),),
            certificate_links=(
                Row(certificate_id="c", asset_unit_id="a"),
                Row(certificate_id="c", asset_unit_id="b"),
            ),
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
                    uploaded_at=datetime(2026, 2, 1, tzinfo=UTC),
                    replaces_document_id="d1",
                    target_type="property_certificate",
                    target_id="c",
                    document_type="property_certificate",
                    attachment_id="f2",
                ),
            ),
            attachments=(
                Row(
                    id="f2",
                    owner_type="property_certificate",
                    owner_id="c",
                    created_at=datetime(2026, 2, 1, tzinfo=UTC),
                ),
            ),
        ),
        TODAY,
    )
    assert len(rows) == 1
    assert rows[0].unit_ids == frozenset({"a", "b"})
    assert categories(rows)[0].existing == 1


@pytest.mark.unit
def test_future_contract_and_effective_successor_do_not_count():
    contract = Row(
        id="c",
        start_date=date(2020, 1, 1),
        end_date=date(2030, 1, 1),
        contract_number="合同",
        scan_document_id="f",
    )
    link = Row(
        upstream_contract_id="c",
        asset_unit_id="u",
        effective_from=date(2020, 1, 1),
        effective_to=None,
    )
    assert (
        project_requirements(
            facts(
                upstream=(contract,),
                upstream_links=(link,),
                successors={("upstream", "c"): TODAY},
            ),
            TODAY,
        )
        == ()
    )
    contract.start_date = date(2027, 1, 1)
    assert (
        project_requirements(facts(upstream=(contract,), upstream_links=(link,)), TODAY)
        == ()
    )


@pytest.mark.unit
def test_handover_reversal_and_non_applicable_do_not_count():
    contract = Row(
        id="c",
        start_date=date(2020, 1, 1),
        end_date=date(2021, 1, 1),
        contract_number="合同",
        scan_document_id=None,
    )
    link = Row(
        upstream_contract_id="c",
        asset_unit_id="u",
        effective_from=date(2020, 1, 1),
        effective_to=date(2021, 1, 1),
    )
    event = Row(
        id="e",
        contract_kind="upstream",
        contract_id="c",
        event_type="exited",
        effective_date=date(2021, 1, 1),
        handover_status="pending",
        reversed_event_id=None,
    )
    rows = project_requirements(
        facts(upstream=(contract,), upstream_links=(link,), events=(event,)), TODAY
    )
    assert [r.document_type for r in rows] == ["handover"]
    reverse = Row(
        id="r",
        event_type="reversed",
        effective_date=TODAY,
        reversed_event_id="e",
        contract_kind="upstream",
        contract_id="c",
        handover_status=None,
    )
    assert (
        project_requirements(
            facts(
                upstream=(contract,), upstream_links=(link,), events=(event, reverse)
            ),
            TODAY,
        )
        == ()
    )


from src.models.asset_contract import UpstreamContract


@pytest.mark.unit
@pytest.mark.parametrize(
    "start,end,coverage_end,expected",
    [
        (date(2020, 1, 1), date(2030, 1, 1), None, 1),
        (date(2020, 1, 1), date(2021, 1, 1), None, 0),
        (date(2027, 1, 1), date(2030, 1, 1), None, 0),
        (date(2020, 1, 1), date(2030, 1, 1), date(2021, 1, 1), 0),
    ],
)
def test_fees_require_current_agreement_and_coverage(
    start, end, coverage_end, expected
):
    contract = UpstreamContract(
        id="c",
        contract_type="management_agreement",
        start_date=start,
        end_date=end,
        contract_number="协议",
        scan_document_id=None,
    )
    link = Row(
        upstream_contract_id="c",
        asset_unit_id="u",
        effective_from=date(2020, 1, 1),
        effective_to=coverage_end,
    )
    fee = Row(
        id="fee",
        status="confirmed",
        confirmed_at=datetime(2026, 1, 1, tzinfo=UTC),
        upstream_contract_ids=["c"],
        statement_number="对账",
        stamped_document_id=None,
    )
    rows = project_requirements(
        facts(upstream=(contract,), upstream_links=(link,), statements=(fee,)), TODAY
    )
    assert (
        len([r for r in rows if r.document_type == "management_fee_statement"])
        == expected
    )


@pytest.mark.unit
def test_contract_scan_archive_chain_satisfies_requirement_without_fact():
    from src.models.asset_contract import UpstreamContract

    contract = UpstreamContract(
        id="c",
        contract_type="management_agreement",
        start_date=date(2020, 1, 1),
        end_date=date(2030, 1, 1),
        contract_number="合同",
        scan_document_id=None,
    )
    link = Row(
        upstream_contract_id="c",
        asset_unit_id="u",
        effective_from=date(2020, 1, 1),
        effective_to=None,
    )
    missing = project_requirements(
        facts(upstream=(contract,), upstream_links=(link,)), TODAY
    )
    assert missing[0].existing is False
    archived_row = Row(
        id="d1",
        uploaded_at=datetime(2026, 2, 1, tzinfo=UTC),
        replaces_document_id=None,
        target_type="upstream_contract",
        target_id="c",
        document_type="upstream_contract",
        attachment_id="f1",
    )
    owned = project_requirements(
        facts(
            upstream=(contract,),
            upstream_links=(link,),
            documents=(archived_row,),
            attachments=(Row(
                id="f1",
                owner_type="contract",
                owner_id="c",
                created_at=datetime(2026, 2, 1, tzinfo=UTC),
            ),),
        ),
        TODAY,
    )
    assert owned[0].existing is True
    wrong_owner = project_requirements(
        facts(
            upstream=(contract,),
            upstream_links=(link,),
            documents=(archived_row,),
            attachments=(Row(
                id="f1",
                owner_type="contract",
                owner_id="other",
                created_at=datetime(2026, 2, 1, tzinfo=UTC),
            ),),
        ),
        TODAY,
    )
    assert wrong_owner[0].existing is False
