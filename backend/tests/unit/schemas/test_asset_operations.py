"""Schema contracts for the asset-operations v5 vertical slice."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.schemas.asset_operations import (
    AssetUnitCreate,
    AssetUnitMergeCommitRequest,
    AssetUnitMergePreviewRequest,
    AssetUnitMergeProposal,
    AssetUnitMergeResultInput,
    AssetUnitResponse,
    AssetUnitSplitCommitRequest,
    AssetUnitSplitPreviewRequest,
    AssetUnitSplitProposal,
    AssetUnitUpdate,
    ContractLifecycleEventCreate,
    ContractRentScheduleInput,
    ContractWarning,
    TerminalContractConfirmRequest,
    TerminalContractCreate,
    UpstreamContractConfirmRequest,
    UpstreamContractCreate,
)


def _asset_unit_payload() -> dict[str, object]:
    return {
        "unit_code": "UNIT-001",
        "name": "一层 101",
        "project_id": "project-1",
        "owner_party_id": "owner-1",
        "address": "测试路 1 号",
        "usage_type": "商铺",
        "acquisition_mode": "leased",
        "is_operating": True,
        "land_area": "0",
        "building_area": "100.00",
        "rentable_area": "80.00",
        "managed_from": "2026-01-01",
    }


def test_asset_unit_write_schema_rejects_derived_fields_and_invalid_area() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        AssetUnitUpdate.model_validate(
            {"expected_version": 1, "rental_status": "vacant"}
        )

    with pytest.raises(ValidationError, match="rentable_area"):
        AssetUnitCreate.model_validate(
            {**_asset_unit_payload(), "rentable_area": "120.00"}
        )


def test_asset_unit_update_requires_positive_expected_version() -> None:
    with pytest.raises(ValidationError):
        AssetUnitUpdate.model_validate({"name": "新名称"})

    update = AssetUnitUpdate.model_validate({"expected_version": 2, "name": " 新名称 "})

    assert update.expected_version == 2
    assert update.name == "新名称"


def test_asset_unit_response_accepts_derived_projection_fields() -> None:
    response = AssetUnitResponse.model_validate(
        {
            **_asset_unit_payload(),
            "id": "unit-1",
            "version": 1,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "rental_status": "vacant",
            "rented_area": "0",
            "occupancy_rate": "0",
            "warnings": [{"code": "upstream_missing", "severity": "warning"}],
        }
    )

    assert response.rental_status == "vacant"
    assert response.warnings == [
        ContractWarning(code="upstream_missing", severity="warning", message=None)
    ]


def test_split_schema_requires_two_unique_result_codes_and_minimal_commit() -> None:
    proposal = AssetUnitSplitProposal.model_validate(
        {
            "source_unit_id": "unit-1",
            "effective_date": "2026-11-01",
            "parts": [
                {
                    "unit_code": "U-001-A",
                    "name": "一号商铺 A",
                    "land_area": "8.00",
                    "building_area": "40.00",
                    "rentable_area": "30.00",
                },
                {
                    "unit_code": "U-001-B",
                    "name": "一号商铺 B",
                    "land_area": "12.00",
                    "building_area": "60.00",
                    "rentable_area": "50.00",
                },
            ],
        }
    )
    commit = AssetUnitSplitCommitRequest.model_validate(
        {
            "preview_token": "opaque-token",
            "reason": " 按楼层重新划分 ",
            "expected_version": 3,
        }
    )

    assert [part.unit_code for part in proposal.parts] == ["U-001-A", "U-001-B"]
    assert commit.reason == "按楼层重新划分"

    with pytest.raises(ValidationError, match="不得重复"):
        AssetUnitSplitProposal.model_validate(
            {
                **proposal.model_dump(mode="json"),
                "parts": [
                    proposal.parts[0].model_dump(mode="json"),
                    proposal.parts[0].model_dump(mode="json"),
                ],
            }
        )
    with pytest.raises(ValidationError, match="extra_forbidden"):
        AssetUnitSplitCommitRequest.model_validate(
            {
                **commit.model_dump(mode="json"),
                "effective_date": "2026-11-01",
            }
        )


def test_split_preview_request_takes_source_only_from_the_path() -> None:
    payload = {
        "effective_date": "2026-11-01",
        "parts": [
            {
                "unit_code": "U-001-A",
                "name": "一号商铺 A",
                "land_area": "8.00",
                "building_area": "40.00",
                "rentable_area": "30.00",
            },
            {
                "unit_code": "U-001-B",
                "name": "一号商铺 B",
                "land_area": "12.00",
                "building_area": "60.00",
                "rentable_area": "50.00",
            },
        ],
    }

    request = AssetUnitSplitPreviewRequest.model_validate(payload)

    assert request.effective_date == date(2026, 11, 1)
    with pytest.raises(ValidationError, match="extra_forbidden"):
        AssetUnitSplitPreviewRequest.model_validate(
            {**payload, "source_unit_id": "different-unit"}
        )


def test_merge_schema_requires_unique_sources_and_complete_version_set() -> None:
    preview = AssetUnitMergePreviewRequest.model_validate(
        {
            "source_unit_ids": ["unit-2", "unit-1"],
            "effective_date": "2026-11-01",
            "result": {"unit_code": "U-001+002", "name": "一二号合并商铺"},
        }
    )
    proposal = AssetUnitMergeProposal.model_validate(
        {**preview.model_dump(mode="json"), "change_type": "merge"}
    )
    commit = AssetUnitMergeCommitRequest.model_validate(
        {
            "preview_token": "opaque-merge-token",
            "reason": "恢复完整经营边界",
            "expected_versions": {"unit-1": 2, "unit-2": 3},
        }
    )

    assert proposal.source_unit_ids == ["unit-1", "unit-2"]
    assert proposal.result == AssetUnitMergeResultInput(
        unit_code="U-001+002",
        name="一二号合并商铺",
    )
    assert commit.expected_versions == {"unit-1": 2, "unit-2": 3}

    with pytest.raises(ValidationError, match="不得包含重复 ID"):
        AssetUnitMergePreviewRequest.model_validate(
            {
                **preview.model_dump(mode="json"),
                "source_unit_ids": ["unit-1", "unit-1"],
            }
        )
    with pytest.raises(ValidationError, match="greater_than_equal"):
        AssetUnitMergeCommitRequest.model_validate(
            {
                **commit.model_dump(mode="json"),
                "expected_versions": {"unit-1": 0, "unit-2": 3},
            }
        )
    with pytest.raises(ValidationError, match="extra_forbidden"):
        AssetUnitMergePreviewRequest.model_validate(
            {
                **preview.model_dump(mode="json"),
                "result": {
                    **preview.result.model_dump(mode="json"),
                    "building_area": "100.00",
                },
            }
        )


def test_upstream_contract_terms_follow_contract_type() -> None:
    lease = UpstreamContractCreate.model_validate(
        {
            "contract_number": "UP-001",
            "contract_type": "lease",
            "name": "承租合同",
            "owner_party_id": "owner-1",
            "operator_party_id": "operator-1",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "payment_cycle": "monthly",
            "payment_day": 25,
            "deposit_amount": "10000",
            "scan_document_id": "attachment-1",
            "asset_unit_ids": ["unit-1"],
        }
    )
    assert lease.management_fee_rate is None

    management = UpstreamContractCreate.model_validate(
        {
            "contract_number": "UP-002",
            "contract_type": "management_agreement",
            "name": "委托管理协议",
            "owner_party_id": "owner-1",
            "operator_party_id": "operator-1",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "management_fee_rate": "0.08",
            "deposit_amount": "0",
            "scan_document_id": "attachment-2",
            "asset_unit_ids": ["unit-1"],
        }
    )
    assert management.management_fee_rate == Decimal("0.08")

    with pytest.raises(ValidationError, match="management_agreement"):
        UpstreamContractCreate.model_validate(
            {
                **management.model_dump(),
                "payment_cycle": "monthly",
            }
        )


def test_terminal_contract_allows_missing_upstream_and_enforces_collector_mode() -> (
    None
):
    terminal = TerminalContractCreate.model_validate(
        {
            "contract_number": "TM-001",
            "contract_mode": "sublease",
            "tenant_party_id": "tenant-1",
            "lessor_party_id": "operator-1",
            "upstream_contract_id": None,
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "deposit_amount": "20000",
            "rent_collector": "operator",
            "scan_document_id": "attachment-3",
            "asset_unit_ids": ["unit-1", "unit-2"],
        }
    )
    assert terminal.upstream_contract_id is None
    assert terminal.asset_unit_ids == ["unit-1", "unit-2"]

    with pytest.raises(ValidationError, match="rent_collector"):
        TerminalContractCreate.model_validate(
            {**terminal.model_dump(), "rent_collector": "owner"}
        )


def test_rent_schedule_validates_range_money_and_due_day() -> None:
    schedule = ContractRentScheduleInput.model_validate(
        {
            "stage_start": "2026-01-01",
            "stage_end": "2026-12-31",
            "base_monthly_rent": "10000",
            "increase_rate": "0",
            "free_rent_months": "1",
            "discount_amount": "10000",
            "actual_monthly_rent": "9166.67",
            "payment_cycle": "quarterly",
            "due_day": 15,
        }
    )
    assert schedule.stage_start == date(2026, 1, 1)

    with pytest.raises(ValidationError):
        ContractRentScheduleInput.model_validate(
            {**schedule.model_dump(), "due_day": 32}
        )


def test_lifecycle_reversal_explicitly_targets_original_event() -> None:
    with pytest.raises(ValidationError, match="reversed_event_id"):
        ContractLifecycleEventCreate.model_validate(
            {
                "contract_kind": "terminal",
                "contract_id": "terminal-1",
                "event_type": "reversed",
                "effective_date": "2026-06-01",
                "reason": "恢复原合同",
                "created_by": "user-1",
                "idempotency_key": "idem-1",
            }
        )

    event = ContractLifecycleEventCreate.model_validate(
        {
            "contract_kind": "terminal",
            "contract_id": "terminal-1",
            "event_type": "reversed",
            "effective_date": "2026-06-01",
            "reversed_event_id": "event-1",
            "reason": " 恢复原合同 ",
            "created_by": "user-1",
            "idempotency_key": "idem-1",
        }
    )

    assert event.reversed_event_id == "event-1"
    assert event.reason == "恢复原合同"


def test_intake_confirmation_cannot_replace_session_type_or_scan_document() -> None:
    upstream = UpstreamContractConfirmRequest.model_validate(
        {
            "contract_number": "UP-001",
            "name": "承租合同",
            "owner_party_id": "owner-1",
            "operator_party_id": "operator-1",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "payment_cycle": "monthly",
            "asset_unit_ids": ["unit-1"],
        }
    )
    assert upstream.contract_number == "UP-001"

    for forbidden_field, value in (
        ("contract_type", "lease"),
        ("scan_document_id", "scan-other"),
        ("renewed_from_id", "upstream-existing"),
    ):
        with pytest.raises(ValidationError, match=forbidden_field):
            UpstreamContractConfirmRequest.model_validate(
                {**upstream.model_dump(), forbidden_field: value}
            )

    terminal = TerminalContractConfirmRequest.model_validate(
        {
            "contract_number": "TM-001",
            "contract_mode": "sublease",
            "tenant_party_id": "tenant-1",
            "lessor_party_id": "operator-1",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "rent_collector": "operator",
            "asset_unit_ids": ["unit-1"],
        }
    )
    for forbidden_field, value in (
        ("scan_document_id", "scan-other"),
        ("renewed_from_id", "terminal-existing"),
    ):
        with pytest.raises(ValidationError, match=forbidden_field):
            TerminalContractConfirmRequest.model_validate(
                {**terminal.model_dump(), forbidden_field: value}
            )
