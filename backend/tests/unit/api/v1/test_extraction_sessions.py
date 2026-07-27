from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from src.api.v1.extraction_sessions import (
    _context,
    create_extraction_session,
    document_extraction_capabilities,
)
from src.models.contract_group import ContractDirection, GroupRelationType, RevenueMode
from src.services.file_upload import StagedFileService


async def test_capabilities_expose_only_provider_free_contract_limits() -> None:
    capabilities = await document_extraction_capabilities()

    assert capabilities["targets"] == [
        {"target_type": "contract", "input": "pdf_upload"},
        {"target_type": "property_certificate", "input": "pdf_or_image_upload"},
    ]
    assert capabilities["limits"]["max_contract_pages"] == 50
    assert capabilities["limits"]["pages_per_batch"] == 20
    assert capabilities["stages"] == ["ready_for_review", "disabled"]
    assert "provider" not in str(capabilities).lower()
    assert "model" not in str(capabilities).lower()


def test_unified_router_does_not_register_standalone_property_certificate_session_paths() -> (
    None
):
    from src.api.v1 import property_certificate_extraction_sessions as legacy_module

    assert legacy_module.router.routes
    assert "route_registry.register_router" not in Path(
        legacy_module.__file__
    ).read_text(encoding="utf-8")


def test_contract_context_rejects_incompatible_revenue_mode_and_relation_type() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _context(
            project_id="project-1",
            revenue_mode=RevenueMode.LEASE.value,
            contract_direction=ContractDirection.LESSOR.value,
            group_relation_type=GroupRelationType.DIRECT_LEASE.value,
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "invalid contract extraction context"


def test_contract_context_accepts_compatible_revenue_mode_and_relation_type() -> None:
    context = _context(
        project_id="project-1",
        revenue_mode=RevenueMode.LEASE.value,
        contract_direction=ContractDirection.LESSOR.value,
        group_relation_type=GroupRelationType.DOWNSTREAM.value,
    )

    assert context["group_relation_type"] == GroupRelationType.DOWNSTREAM.value


async def test_contract_session_rejects_incompatible_context_before_staging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorize = AsyncMock()
    stage_upload = AsyncMock()
    monkeypatch.setattr("src.api.v1.extraction_sessions._authorize", authorize)
    monkeypatch.setattr(StagedFileService, "stage_upload", stage_upload)

    with pytest.raises(HTTPException) as exc_info:
        await create_extraction_session(
            target_type="contract",
            file=object(),
            project_id="project-1",
            revenue_mode=RevenueMode.LEASE.value,
            contract_direction=ContractDirection.LESSOR.value,
            group_relation_type=GroupRelationType.DIRECT_LEASE.value,
            db=AsyncMock(),
            current_user=object(),
        )

    assert exc_info.value.status_code == 422
    authorize.assert_awaited_once()
    stage_upload.assert_not_awaited()
