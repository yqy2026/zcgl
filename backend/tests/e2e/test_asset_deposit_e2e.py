"""REQ-DEP-001 admission: management agreements never acquire deposits.

The remaining deposit record and settlement HTTP flows belong to PR-B and
are not covered by this initial boundary test.
"""

from decimal import Decimal

import pytest

from src.models.asset_contract import UpstreamContract
from tests.e2e.test_asset_contract_lifecycle_e2e import _seed_signed_contracts

pytestmark = pytest.mark.e2e


def test_management_agreement_cannot_be_updated_to_hold_a_deposit(
    authenticated_client, csrf_headers, db_session
):
    client = authenticated_client
    facts = _seed_signed_contracts(db_session, client._user_id)
    agreement = db_session.get(UpstreamContract, facts["upstream_id"])
    agreement.contract_type = "management_agreement"
    agreement.deposit_amount = Decimal("0")
    agreement.payment_cycle = None
    agreement.payment_day = None
    agreement.management_fee_rate = Decimal("0.10")
    db_session.commit()
    path = f"/api/v1/upstream-contracts/{agreement.id}"
    before = client.get(path)
    assert before.status_code == 200, before.text
    rejected = client.patch(
        path,
        json={
            "expected_version": before.json()["version"],
            "deposit_amount": "100",
        },
        headers=csrf_headers,
    )
    assert rejected.status_code == 422, rejected.text
    assert rejected.json()["error"]["code"] == "CONTRACT_FIELD_NOT_APPLICABLE"
    after = client.get(path)
    assert after.status_code == 200, after.text
    assert Decimal(str(after.json()["deposit_amount"])) == 0
    assert after.json()["version"] == before.json()["version"]
