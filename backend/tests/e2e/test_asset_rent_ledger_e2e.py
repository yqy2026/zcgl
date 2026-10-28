"""Real HTTP rent correction, generation, partial receipts and reversal."""

from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from tests.e2e.test_asset_contract_lifecycle_e2e import _seed_signed_contracts

pytestmark = pytest.mark.e2e


def test_rent_receipts_and_reversal_over_http(authenticated_client, csrf_headers, db_session):
    client = authenticated_client
    facts = _seed_signed_contracts(db_session, getattr(client, '_user_id'))
    path = f"/api/v1/terminal-contracts/{facts['terminal_id']}"
    headers = {**csrf_headers, 'Idempotency-Key': str(uuid4())}
    preview = client.post(f'{path}/rent-schedule-correction/preview', json={
        'reason': '补录合同已签租金阶段', 'rent_schedules': [{
            'stage_start': facts['start'], 'stage_end': facts['end'],
            'base_monthly_rent': '100', 'actual_monthly_rent': '100',
            'payment_cycle': 'monthly', 'due_day': 31,
        }],
    }, headers=csrf_headers)
    assert preview.status_code == 200, preview.text
    corrected = client.post(f'{path}/rent-schedule-correction', json={
        'preview_token': preview.json()['preview_token'],
        'expected_version': preview.json()['contract_version'],
    }, headers=headers)
    assert corrected.status_code == 200, corrected.text
    today = datetime.now(ZoneInfo('Asia/Shanghai')).date()
    matrix = client.get('/api/v1/rent-ledgers', params={'year': today.year, 'ledger_type': 'terminal_rent'})
    assert matrix.status_code == 200, matrix.text
    row = next(row for row in matrix.json()['rows'] if row['contract_id'] == facts['terminal_id'])
    entry = row['months'][today.month - 1]['entries'][0]
    endpoint = f"/api/v1/rent-ledger-entries/{entry['id']}"
    version = entry['version']
    receipts = []
    for amount in ['30', '70']:
        response = client.post(f'{endpoint}/records', json={
            'record_type': 'receipt', 'amount': amount, 'occurred_on': today.isoformat(),
            'expected_version': version,
        }, headers={**csrf_headers, 'Idempotency-Key': str(uuid4())})
        assert response.status_code == 200, response.text
        receipts.append(response.json())
        version = response.json()['version']
    detail = client.get(endpoint)
    assert detail.status_code == 200, detail.text
    assert detail.json()['status'] == 'paid'
    reversal = client.post(f"/api/v1/rent-payment-records/{receipts[1]['id']}/reversal", json={
        'reason': '撤销重复到账', 'expected_version': version,
    }, headers={**csrf_headers, 'Idempotency-Key': str(uuid4())})
    assert reversal.status_code == 200, reversal.text
    detail = client.get(endpoint)
    assert detail.status_code == 200, detail.text
    assert detail.json()['status'] == 'partial'
    assert float(detail.json()['remaining_amount']) == 70
    assert len(detail.json()['records']) == 3
