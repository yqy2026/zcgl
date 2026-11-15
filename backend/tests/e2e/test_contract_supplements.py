from datetime import date
from uuid import uuid4

import pytest

from src.api.v1 import contract_supplements as api
from src.models.asset_contract import UpstreamContract, UpstreamContractAssetUnit
from src.models.attachment import Attachment
from src.services.party_scope_resolver import EffectivePartyScope
from tests.e2e.test_asset_unit_certificates import (
    certificate_facts as _certificate_facts,
)

certificate_facts = _certificate_facts

pytestmark = pytest.mark.e2e


def test_register_duplicate_withdraw_and_matrix(
    authenticated_client, csrf_headers, certificate_facts, db_session, monkeypatch
):
    f = certificate_facts
    file_id, cid = str(uuid4()), str(uuid4())
    db_session.add(
        Attachment(
            id=file_id,
            owner_type="contract",
            owner_id=cid,
            file_name="scan.pdf",
            file_type="pdf",
            file_size=1,
            storage_key="supplement/" + file_id,
            created_by=authenticated_client._user_id,
        )
    )
    db_session.flush()
    db_session.add(
        UpstreamContract(
            id=cid,
            contract_number="SUP-" + cid,
            contract_type="lease",
            name="补充协议测试",
            owner_party_id=f["owner"],
            operator_party_id=f["manager"],
            start_date=date(2020, 1, 1),
            end_date=date(2030, 1, 1),
            payment_cycle="monthly",
            scan_document_id=file_id,
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
    db_session.commit()

    async def resolve(db, *, user_id):
        return EffectivePartyScope(
            user_id=user_id,
            source="explicit",
            scope_mode="owner",
            owner_party_ids=[f["owner"]],
        )

    monkeypatch.setattr(api.party_scope_resolver, "resolve", resolve)
    request = {
        "contract_kind": "upstream",
        "contract_id": cid,
        "agreement_number": "S1",
        "title": "租赁补充协议",
    }
    response = authenticated_client.post(
        "/api/v1/contract-supplements", json=request, headers=csrf_headers
    )
    assert response.status_code == 201, response.text
    row = response.json()
    if "data" in row:
        row = row["data"]
    assert (
        authenticated_client.post(
            "/api/v1/contract-supplements", json=request, headers=csrf_headers
        ).status_code
        == 409
    )
    stats = authenticated_client.get("/api/v1/archive/completion").json()
    if "data" in stats:
        stats = stats["data"]
    assert (
        next(r for r in stats["categories"] if r["document_type"] == "supplement")[
            "required"
        ]
        == 1
    )
    response = authenticated_client.post(
        "/api/v1/contract-supplements/" + row["id"] + "/withdrawal",
        json={"expected_version": row["version"], "reason": "误登记"},
        headers=csrf_headers,
    )
    assert response.status_code == 200, response.text
    assert (
        authenticated_client.post(
            "/api/v1/contract-supplements/" + row["id"] + "/withdrawal",
            json={"expected_version": row["version"], "reason": "误登记"},
            headers=csrf_headers,
        ).status_code
        == 409
    )

    stats = authenticated_client.get("/api/v1/archive/completion").json()
    if "data" in stats:
        stats = stats["data"]
    assert (
        next(r for r in stats["categories"] if r["document_type"] == "supplement")[
            "required"
        ]
        == 0
    )

    async def hidden(db, *, user_id):
        return EffectivePartyScope(
            user_id=user_id,
            source="explicit",
            scope_mode="owner",
            owner_party_ids=[f["other"]],
        )

    monkeypatch.setattr(api.party_scope_resolver, "resolve", hidden)
    assert (
        authenticated_client.get(
            "/api/v1/contract-supplements",
            params={"contract_kind": "upstream", "contract_id": cid},
        ).status_code
        == 404
    )
    assert (
        authenticated_client.post(
            "/api/v1/contract-supplements",
            json={**request, "agreement_number": "hidden"},
            headers=csrf_headers,
        ).status_code
        == 404
    )
    assert (
        authenticated_client.post(
            "/api/v1/contract-supplements/" + row["id"] + "/withdrawal",
            json={"expected_version": 2, "reason": "不可见"},
            headers=csrf_headers,
        ).status_code
        == 404
    )


@pytest.mark.parametrize("version,reason", [(1, None), (0, "更正")])
def test_database_rejects_partial_withdrawal_or_invalid_version(
    authenticated_client, db_session, version, reason
):
    from datetime import UTC, datetime

    from sqlalchemy.exc import IntegrityError

    from src.models.contract_supplement import ContractSupplement

    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(
            ContractSupplement.__table__.insert().values(
                contract_kind="upstream",
                contract_id=str(uuid4()),
                agreement_number=str(uuid4()),
                title="约束验证",
                created_by=authenticated_client._user_id,
                withdrawn_at=datetime.now(UTC),
                withdrawn_by=authenticated_client._user_id,
                withdrawal_reason=reason,
                version=version,
            )
        )
        db_session.flush()
