"""Monthly reporting resolves operator attribution at the statistical month end."""

from datetime import date
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

draft_module = import_module(
    "src.services.asset_operations.occupancy_report_draft_service"
)
submission_module = import_module(
    "src.services.asset_operations.occupancy_report_submission_service"
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class CandidateQueryReachedError(Exception):
    pass


@pytest.mark.parametrize("path", ["draft", "submission", "snapshot_diff"])
@pytest.mark.parametrize(
    "period,expected", [("2026-10", date(2026, 10, 31)), ("2024-02", date(2024, 2, 29))]
)
async def test_operator_query_uses_statistical_month_end(
    monkeypatch, path, period, expected
):
    version = SimpleNamespace(id="scope-1")
    repository = draft_module.assessment_scope_repository
    monkeypatch.setattr(repository, "list_items", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        repository, "get_active_version", AsyncMock(return_value=version)
    )

    async def candidates(_db, *, operator_party_id, as_of, year, operating_only=True):
        assert operator_party_id == "operator-1"
        assert year == int(period[:4])
        assert as_of == expected
        if path in {"draft", "submission"}:
            assert operating_only is False
        raise CandidateQueryReachedError

    monkeypatch.setattr(repository, "list_managed_units", candidates)
    monkeypatch.setattr(draft_module, "_business_today", lambda: date(2026, 11, 2))
    monkeypatch.setattr(submission_module, "_business_today", lambda: date(2026, 11, 2))
    with pytest.raises(CandidateQueryReachedError):
        if path == "draft":
            service = draft_module.OccupancyReportDraftService()
            monkeypatch.setattr(draft_module, "require_scope", lambda *_args: None)
            monkeypatch.setattr(
                draft_module, "require_operator_access", lambda *_args, **_kwargs: None
            )
            monkeypatch.setattr(service, "_require_party", AsyncMock())
            monkeypatch.setattr(
                service, "_require_scope_version", AsyncMock(return_value=version)
            )
            monkeypatch.setattr(
                draft_module.occupancy_report_repository,
                "get_active_chain_report",
                AsyncMock(return_value=None),
            )
            await service.get_draft(
                None,
                operator_party_id="operator-1",
                period=period,
                actor_id="actor-1",
                scope=None,
            )
        elif path == "submission":
            await submission_module.OccupancyReportSubmissionService()._derive(
                None,
                scope_version=version,
                operator_party_id="operator-1",
                period=period,
                chain=None,
            )
        else:
            await submission_module.OccupancyReportSubmissionService()._current_lines(
                None, operator_party_id="operator-1", period=period
            )
