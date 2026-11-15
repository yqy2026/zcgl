from datetime import date
from types import SimpleNamespace as R

import pytest

from src.services.asset_operations.handover_archive_service import unavailable_reason

pytestmark=pytest.mark.unit
@pytest.mark.parametrize("change,expected", [({},None),({"handover_status":"not_applicable"},"HANDOVER_NOT_REQUIRED"),({"effective_date":date(2030,1,1)},"HANDOVER_NOT_EFFECTIVE")])
def test_handover_write_boundaries(change,expected):
    fields=dict(id="e",effective_date=date(2020,1,1),handover_status="pending")
    fields.update(change)
    assert unavailable_reason(R(**fields),(),date(2026,11,3))==expected
def test_effective_reversal_rejects_write():
    e=R(id="e",effective_date=date(2020,1,1),handover_status="completed")
    reverse=R(event_type="reversed",reversed_event_id="e",effective_date=date(2026,11,3))
    assert unavailable_reason(e,(reverse,),date(2026,11,3))=="HANDOVER_EVENT_REVERSED"
