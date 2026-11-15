"""Historical as_of recomputes the archive matrix from dated facts."""

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from src.api.v1 import archive_matrix as api
from src.models.asset_contract import UpstreamContract, UpstreamContractAssetUnit
from src.models.attachment import Attachment
from src.models.contract_supplement import ContractSupplement
from src.services.party_scope_resolver import EffectivePartyScope
from tests.e2e.test_asset_unit_certificates import (
    certificate_facts as _certificate_facts,
)

certificate_facts = _certificate_facts

pytestmark = pytest.mark.e2e


def _category(body, document_type):
    return next(
        c for c in body["categories"] if c["document_type"] == document_type
    )


def test_archive_completion_recomputes_at_historical_as_of(
    authenticated_client,
    csrf_headers,
    certificate_facts,
    db_session,
    monkeypatch,
):
    f = certificate_facts
    client = authenticated_client

    cid = str(uuid4())
    staged = str(uuid4())
    db_session.add(
        Attachment(
            id=staged,
            owner_type="contract",
            owner_id="intake-session-" + cid,
            file_name="staged.pdf",
            file_type="pdf",
            file_size=1,
            storage_key="intake/" + staged,
            created_by=str(uuid4()),
        )
    )
    db_session.flush()
    db_session.add(
        UpstreamContract(
            id=cid,
            contract_number="HIST-" + cid,
            contract_type="lease",
            name="历史口径测试",
            owner_party_id=f["owner"],
            operator_party_id=f["manager"],
            start_date=date(2020, 1, 1),
            end_date=date(2030, 1, 1),
            payment_cycle="monthly",
            scan_document_id=staged,
        )
    )
    db_session.flush()
    db_session.add(
        UpstreamContractAssetUnit(
            upstream_contract_id=cid,
            asset_unit_id=f["visible_unit"],
            effective_from=date(2020, 1, 1),
        )
    )
    # Registered in January, withdrawn in October.
    db_session.add(
        ContractSupplement(
            id=str(uuid4()),
            contract_kind="upstream",
            contract_id=cid,
            agreement_number="HIST-补-1",
            title="历史窗口",
            signed_on=date(2026, 1, 5),
            created_by=client._user_id,
            created_at=datetime(2026, 1, 10, tzinfo=UTC),
            version=1,
        )
    )
    db_session.commit()

    async def owner_scope(db, *, user_id):
        return EffectivePartyScope(
            user_id=user_id,
            source="explicit",
            scope_mode="owner",
            owner_party_ids=[f["owner"]],
        )

    monkeypatch.setattr(api.party_scope_resolver, "resolve", owner_scope)

    def completion(as_of=None):
        params = {"as_of": as_of} if as_of is not None else {}
        body = client.get("/api/v1/archive/completion", params=params).json()
        return body.get("data", body)

    at_september = completion("2026-09-15")
    assert at_september["as_of"] == "2026-09-15"
    assert _category(at_september, "supplement")["required"] >= 1
    assert at_september["categories"][0]["required"] >= 0  # shape sanity

    withdrawn = (
        db_session.query(ContractSupplement)
        .filter(ContractSupplement.agreement_number == "HIST-补-1")
        .one()
    )
    withdrawn.withdrawn_at = datetime(2026, 10, 1, tzinfo=UTC)
    withdrawn.withdrawn_by = client._user_id
    withdrawn.withdrawal_reason = "登记错误"
    db_session.commit()

    still_september = completion("2026-09-15")
    before_required = _category(still_september, "supplement")["required"]
    at_november = completion("2026-11-01")
    after_required = _category(at_november, "supplement")["required"]
    assert before_required == _category(at_september, "supplement")["required"]
    assert after_required == before_required - 1

    future = client.get(
        "/api/v1/archive/completion",
        params={"as_of": (date.today() + timedelta(days=1)).isoformat()},
    )
    assert future.status_code == 422
    assert future.json()["error"]["code"] == "ARCHIVE_AS_OF_INVALID"

    matrix = client.get(
        "/api/v1/archive/matrix", params={"as_of": "2026-09-15"}
    ).json()
    matrix = matrix.get("data", matrix)
    assert matrix["as_of"] == "2026-09-15"
    assert matrix["total"] >= 1
