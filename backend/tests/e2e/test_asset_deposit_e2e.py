"""REQ-DEP-001 HTTP deposit facts and paired rent corrections."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from src.models.asset_contract import ContractLifecycleEvent, UpstreamContract
from src.models.asset_ledger import RentLedgerEntry, RentPaymentRecord
from src.models.deposit_ledger import DepositLedgerEntry, DepositRecord
from tests.e2e.test_asset_contract_lifecycle_e2e import _seed_signed_contracts

pytestmark = pytest.mark.e2e


def test_deposit_collection_offset_and_rent_side_reversal_are_atomic(
    authenticated_client, csrf_headers, db_session
):
    client = authenticated_client
    facts = _seed_signed_contracts(db_session, client._user_id)
    entry_id = (
        db_session.query(DepositLedgerEntry)
        .filter_by(contract_kind="terminal", contract_id=facts["terminal_id"])
        .one()
        .id
    )
    rent_id = str(uuid4())
    today = date.fromisoformat(facts["effective_date"])
    db_session.add(
        RentLedgerEntry(
            id=rent_id,
            contract_kind="terminal",
            contract_id=facts["terminal_id"],
            entry_type="terminal_receivable",
            period=today.strftime("%Y-%m"),
            period_start=today,
            period_end=today,
            due_date=today,
            due_amount=Decimal("300"),
            origin="manual",
            basis_note="押金抵扣测试",
            version=1,
        )
    )
    db_session.commit()
    path = f"/api/v1/deposits/{entry_id}"
    view = client.get(path)
    assert view.status_code == 200, view.text
    assert Decimal(str(view.json()["outstanding_amount"])) == 500
    payload = {
        "record_type": "collect",
        "amount": "500",
        "occurred_on": facts["effective_date"],
        "expected_version": 1,
    }
    headers = csrf_headers | {"Idempotency-Key": str(uuid4())}
    collected = client.post(f"{path}/records", json=payload, headers=headers)
    assert collected.status_code == 200, collected.text
    replay = client.post(f"{path}/records", json=payload, headers=headers)
    assert replay.status_code == 200 and replay.json()["idempotent"], replay.text
    conflict = client.post(
        f"{path}/records", json=payload | {"amount": "499"}, headers=headers
    )
    assert conflict.status_code == 409, conflict.text
    excess = client.post(
        f"{path}/records",
        json=payload | {"amount": "1", "expected_version": collected.json()["version"]},
        headers=csrf_headers | {"Idempotency-Key": str(uuid4())},
    )
    assert excess.status_code == 409, excess.text
    assert excess.json()["error"]["code"] == "DEPOSIT_AMOUNT_EXCEEDS_REMAINING"
    assert (
        client.get(
            "/api/v1/deposits", params={"contract_id": facts["terminal_id"]}
        ).json()["total"]
        == 0
    )
    assert (
        client.get(
            "/api/v1/deposits",
            params={"contract_id": facts["terminal_id"], "status": "settled"},
        ).json()["total"]
        == 1
    )
    blocked = client.post(
        f"{path}/records",
        json={
            "record_type": "deduct",
            "amount": "300",
            "occurred_on": facts["effective_date"],
            "offset_ledger_entry_id": rent_id,
            "expected_version": collected.json()["version"],
        },
        headers=csrf_headers | {"Idempotency-Key": str(uuid4())},
    )
    assert blocked.status_code == 409, blocked.text
    db_session.add(
        ContractLifecycleEvent(
            id=str(uuid4()),
            contract_kind="terminal",
            contract_id=facts["terminal_id"],
            event_type="terminated",
            effective_date=today,
            created_by=client._user_id,
            reason="终止结算测试",
            idempotency_key=str(uuid4()),
        )
    )
    db_session.commit()
    deducted = client.post(
        f"{path}/records",
        json={
            "record_type": "deduct",
            "amount": "300",
            "occurred_on": facts["effective_date"],
            "offset_ledger_entry_id": rent_id,
            "expected_version": collected.json()["version"],
        },
        headers=csrf_headers | {"Idempotency-Key": str(uuid4())},
    )
    assert deducted.status_code == 200, deducted.text
    view = client.get(path).json()
    assert Decimal(str(view["held_amount"])) == 200
    invalid_reversal = client.post(
        f"/api/v1/deposit-records/{collected.json()['id']}/reversal",
        json={"expected_version": view["version"], "reason": "收取错误"},
        headers=csrf_headers | {"Idempotency-Key": str(uuid4())},
    )
    assert invalid_reversal.status_code == 409, invalid_reversal.text
    db_session.expire_all()
    pair = (
        db_session.query(RentPaymentRecord)
        .filter_by(paired_deposit_record_id=deducted.json()["id"])
        .one()
    )
    rent = db_session.get(RentLedgerEntry, rent_id)
    reversal_headers = csrf_headers | {"Idempotency-Key": str(uuid4())}
    reversal_payload = {"expected_version": rent.version, "reason": "更正抵扣"}
    reversed_response = client.post(
        f"/api/v1/rent-payment-records/{pair.id}/reversal",
        json=reversal_payload,
        headers=reversal_headers,
    )
    assert reversed_response.status_code == 200, reversed_response.text
    replay_reversal = client.post(
        f"/api/v1/rent-payment-records/{pair.id}/reversal",
        json=reversal_payload,
        headers=reversal_headers,
    )
    assert (
        replay_reversal.status_code == 200 and replay_reversal.json()["idempotent"]
    ), replay_reversal.text
    assert Decimal(str(client.get(path).json()["held_amount"])) == 500
    db_session.expire_all()
    assert (
        db_session.query(DepositRecord)
        .filter_by(reverses_record_id=deducted.json()["id"])
        .count()
        == 1
    )


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


def test_termination_offsets_and_clawback_reverse_in_one_transaction(
    authenticated_client, csrf_headers, db_session
):
    client = authenticated_client
    facts = _seed_signed_contracts(db_session, client._user_id)
    contract_id = facts["terminal_id"]
    entry = (
        db_session.query(DepositLedgerEntry)
        .filter_by(contract_kind="terminal", contract_id=contract_id)
        .one()
    )
    deposit_id = entry.id
    today = date.fromisoformat(facts["effective_date"])
    rent_id = str(uuid4())
    past = today - timedelta(days=20)
    db_session.add(
        RentLedgerEntry(
            id=rent_id,
            contract_kind="terminal",
            contract_id=contract_id,
            entry_type="terminal_receivable",
            period=past.strftime("%Y-%m"),
            period_start=past,
            period_end=past,
            due_date=past,
            due_amount=Decimal("300"),
            origin="manual",
            basis_note="终止前欠租",
            version=1,
        )
    )
    db_session.commit()
    collected = client.post(
        f"/api/v1/deposits/{deposit_id}/records",
        json={
            "record_type": "collect",
            "amount": "500",
            "occurred_on": facts["effective_date"],
            "expected_version": 1,
        },
        headers=csrf_headers | {"Idempotency-Key": str(uuid4())},
    )
    assert collected.status_code == 200, collected.text
    path = f"/api/v1/terminal-contracts/{contract_id}"
    proposal = {
        "effective_date": facts["effective_date"],
        "termination_type": "early",
        "handover_status": "completed",
        "deposit_settlement_status": "pending",
        "reason": "提前终止结算",
        "clawback_amount": "100",
        "clawback_basis": "合同免租优惠提前终止须补收",
    }
    preview = client.post(
        f"{path}/termination/preview", json=proposal, headers=csrf_headers
    )
    assert preview.status_code == 200, preview.text
    settlement = preview.json()["deposit_settlement"]
    assert sum(Decimal(row["amount"]) for row in settlement["offsets"]) == 400
    assert Decimal(settlement["refundable_amount"]) == 100
    headers = csrf_headers | {"Idempotency-Key": str(uuid4())}
    payload = {
        "preview_token": preview.json()["preview_token"],
        "expected_version": preview.json()["contract_version"],
    }
    committed = client.post(f"{path}/termination", json=payload, headers=headers)
    assert committed.status_code == 200, committed.text
    assert (
        Decimal(str(client.get(f"/api/v1/deposits/{deposit_id}").json()["held_amount"]))
        == 100
    )
    repeated = client.post(f"{path}/termination", json=payload, headers=headers)
    assert repeated.status_code == 200 and repeated.json()["idempotent"], repeated.text
    reversed_response = client.post(
        f"{path}/termination-reversal",
        json={
            "target_event_id": committed.json()["id"],
            "effective_date": facts["effective_date"],
            "reason": "撤销错误终止",
        },
        headers=csrf_headers | {"Idempotency-Key": str(uuid4())},
    )
    assert reversed_response.status_code == 200, reversed_response.text
    assert (
        Decimal(str(client.get(f"/api/v1/deposits/{deposit_id}").json()["held_amount"]))
        == 500
    )
    db_session.expire_all()
    clawback = (
        db_session.query(RentLedgerEntry)
        .filter_by(contract_id=contract_id, origin="clawback")
        .one()
    )
    assert clawback.voided_at is not None
    deductions = (
        db_session.query(DepositRecord)
        .filter_by(lifecycle_event_id=committed.json()["id"])
        .all()
    )
    assert len(deductions) == 2
    for deduction in deductions:
        assert (
            db_session.query(DepositRecord)
            .filter_by(reverses_record_id=deduction.id)
            .count()
            == 1
        )
