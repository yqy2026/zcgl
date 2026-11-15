"""Archive completion/matrix HTTP surface: as_of passes through and validates."""

from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest

from src.api.v1 import archive_matrix as api
from src.core.exception_handler import BaseBusinessError
from src.schemas.archive_matrix import ArchiveCompletion
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = pytest.mark.unit


def _invalid_as_of():
    return BaseBusinessError(
        "统计日期不可晚于今天", code="ARCHIVE_AS_OF_INVALID", status_code=422
    )


def test_completion_passes_as_of_and_rejects_future(client, monkeypatch):
    scope = EffectivePartyScope(
        user_id="actor", source="unrestricted", scope_mode="unrestricted"
    )
    monkeypatch.setattr(
        api.party_scope_resolver, "resolve", AsyncMock(return_value=scope)
    )
    reader = AsyncMock(
        return_value=ArchiveCompletion(
            as_of=date(2026, 9, 15), categories=[], unlinked_unit_count=0
        )
    )
    monkeypatch.setattr(api.archive_matrix_service, "completion", reader)

    ok = client.get("/api/v1/archive/completion", params={"as_of": "2026-09-15"})
    assert ok.status_code == 200, ok.text
    assert reader.await_args.kwargs["as_of"] == date(2026, 9, 15)

    monkeypatch.setattr(
        api.archive_matrix_service, "completion", AsyncMock(side_effect=_invalid_as_of())
    )
    future = client.get(
        "/api/v1/archive/completion",
        params={"as_of": (date.today() + timedelta(days=1)).isoformat()},
    )
    assert future.status_code == 422
    assert future.json()["error"]["code"] == "ARCHIVE_AS_OF_INVALID"

    malformed = client.get("/api/v1/archive/completion", params={"as_of": "2026/09/15"})
    assert malformed.status_code == 422
