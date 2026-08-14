from pathlib import Path
from unittest.mock import AsyncMock, Mock

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


async def test_contract_session_requires_redis_before_staging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorize = AsyncMock()
    stage_upload = AsyncMock()
    redis_unavailable = HTTPException(
        status_code=503,
        detail="distributed extraction sessions require Redis",
    )
    monkeypatch.setattr("src.api.v1.extraction_sessions._authorize", authorize)
    monkeypatch.setattr(
        "src.api.v1.extraction_sessions._workflow",
        Mock(side_effect=redis_unavailable),
    )
    monkeypatch.setattr(StagedFileService, "stage_upload", stage_upload)

    with pytest.raises(HTTPException) as exc_info:
        await create_extraction_session(
            target_type="contract",
            file=object(),
            project_id="project-1",
            revenue_mode=RevenueMode.LEASE.value,
            contract_direction=ContractDirection.LESSOR.value,
            group_relation_type=GroupRelationType.DOWNSTREAM.value,
            db=AsyncMock(),
            current_user=object(),
        )

    assert exc_info.value.status_code == 503
    authorize.assert_awaited_once()
    stage_upload.assert_not_awaited()


async def test_property_session_authorization_uses_full_session_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """产权证解析会话的 GET/confirm 授权必须基于含 context 的完整会话。

    回归（2026-08-14 验收 ACC-009）：`ContractExtractionWorkflow.public_session` 有意
    剥离 context（不向客户端暴露 staged 元信息），而授权校验 `_require_property_context`
    依赖 context（mode / asset_id），导致产权证解析会话创建后 GET/confirm 一律 404
    「session not found」，产权证解析确认链路不可用。
    """
    from src.api.v1 import extraction_sessions as module

    public_session = {
        "session_id": "s-1",
        "target_type": "property_certificate",
        "status": "ready_for_review",
        "candidates": {"fields": {}},
        "errors": [],
    }
    full_session = {
        **public_session,
        "staged_file_key": ".staging/x/source.pdf",
        "context": {
            "mode": "new",
            "source_kind": "staged",
            "asset_id": "asset-1",
        },
    }
    workflow = Mock()
    workflow.get = Mock(return_value=public_session)
    monkeypatch.setattr(module, "_workflow", lambda: workflow)
    property_workflow = Mock()
    property_workflow.get_raw = Mock(return_value=full_session)
    monkeypatch.setattr(
        module.property_sessions, "_workflow", lambda: property_workflow
    )
    authorize = AsyncMock()
    monkeypatch.setattr(module, "_authorize", authorize)

    result = await module.get_extraction_session(
        session_id="s-1",
        db=AsyncMock(),
        current_user=Mock(),
    )

    assert result["session_id"] == "s-1"
    authorize.assert_awaited_once()


async def test_confirm_reuses_authorization_snapshot_without_refetching_raw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """confirm 必须复用授权步骤的完整会话快照，不得二次 get_raw。

    回归（2026-08-14 两轴复核 D9）：授权与确认各自 get_raw 一次，即用即弃会话若在
    两次读取之间被清理，确认会拿到伪 404；且同一仓库两次读取是冗余 IO。
    """
    from src.api.v1 import extraction_sessions as module

    public_session = {
        "session_id": "s-1",
        "target_type": "property_certificate",
        "status": "ready_for_review",
        "candidates": {"fields": {}},
        "errors": [],
    }
    full_session = {
        **public_session,
        "staged_file_key": ".staging/x/source.pdf",
        "context": {
            "mode": "new",
            "source_kind": "staged",
            "asset_id": "asset-1",
        },
    }
    workflow = Mock()
    workflow.get = Mock(return_value=public_session)
    monkeypatch.setattr(module, "_workflow", lambda: workflow)
    property_workflow = Mock()
    property_workflow.get_raw = Mock(return_value=full_session)
    monkeypatch.setattr(
        module.property_sessions, "_workflow", lambda: property_workflow
    )
    authorize = AsyncMock()
    monkeypatch.setattr(module, "_authorize", authorize)
    confirm = AsyncMock(return_value={"certificate_id": "cert-1"})
    monkeypatch.setattr(
        module.property_sessions,
        "_confirm_property_certificate_extraction_session",
        confirm,
    )

    result = await module.confirm_extraction_session(
        session_id="s-1",
        payload={
            "certificate_type": "real_estate",
            "holder_party_ids": [],
            "actions": [
                {
                    "field_key": "certificate_number",
                    "action": "accept_candidate",
                    "candidate_value": None,
                    "value": None,
                }
            ],
            "link_existing_certificate_id": None,
            "attach_staged": True,
        },
        db=AsyncMock(),
        current_user=Mock(),
    )

    assert result == {"certificate_id": "cert-1"}
    property_workflow.get_raw.assert_called_once()
    confirm.assert_awaited_once()
