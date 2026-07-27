"""Unit tests for payment-flow voucher storage and download auditing."""

import asyncio
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import fitz
import pytest
from starlette.datastructures import UploadFile

from src.core.exception_handler import ResourceNotFoundError
from src.services.file_upload import UploadValidationError

pytestmark = pytest.mark.asyncio


def _pdf_bytes() -> bytes:
    document = fitz.open()
    document.new_page()
    content = document.tobytes()
    document.close()
    return content


def _upload(content: bytes, filename: str = "receipt.pdf") -> UploadFile:
    return UploadFile(
        BytesIO(content),
        filename=filename,
        headers={"content-type": "application/pdf"},
    )


async def test_download_voucher_records_success_before_returning_file(
    mock_db, tmp_path: Path
) -> None:
    from src.services.contract.payment_voucher_service import payment_voucher_service

    flow = SimpleNamespace(flow_id="flow-1", voucher_attachment_ids=["attachment-1"])
    attachment = SimpleNamespace(
        id="attachment-1",
        owner_type="payment_flow",
        owner_id="flow-1",
        file_name="receipt.pdf",
        file_type="pdf",
        storage_key="payment_flows/flow-1/attachment-1/receipt.pdf",
    )
    file_path = tmp_path / attachment.storage_key
    file_path.parent.mkdir(parents=True)
    file_path.write_bytes(b"pdf")

    with (
        patch(
            "src.services.contract.payment_voucher_service.payment_flow_service.get_flow_in_scope",
            new=AsyncMock(return_value=flow),
        ),
        patch(
            "src.services.contract.payment_voucher_service.attachment_crud.get_for_owner",
            new=AsyncMock(return_value=attachment),
        ),
        patch(
            "src.services.contract.payment_voucher_service.operation_log_crud.create_async",
            new=AsyncMock(return_value=SimpleNamespace(id="log-1")),
        ) as mock_audit,
        patch.object(payment_voucher_service, "uploads_root", tmp_path),
    ):
        result = await payment_voucher_service.prepare_download(
            mock_db,
            flow_id="flow-1",
            attachment_id="attachment-1",
            user_id="user-1",
        )

    assert result.path == file_path.resolve()
    assert result.attachment is attachment
    assert mock_audit.await_args.kwargs["user_id"] == "user-1"
    assert '"result": "success"' in mock_audit.await_args.kwargs["details"]


async def test_list_download_audits_hides_out_of_scope_flow(mock_db) -> None:
    from src.services.contract.payment_voucher_service import payment_voucher_service

    with (
        patch(
            "src.services.contract.payment_voucher_service.payment_flow_service.get_flow_in_scope",
            new=AsyncMock(side_effect=ResourceNotFoundError("PaymentFlow", "flow-1")),
        ),
        patch(
            "src.services.contract.payment_voucher_service.operation_log_crud.list_resource_actions_async",
            new=AsyncMock(),
        ) as mock_list,
    ):
        with pytest.raises(ResourceNotFoundError):
            await payment_voucher_service.list_download_audits(
                mock_db, flow_id="flow-1", current_user_id="user-1"
            )

    mock_list.assert_not_awaited()


async def test_upload_voucher_authorizes_before_reading_upload(
    mock_db, tmp_path: Path
) -> None:
    from src.services.contract.payment_voucher_service import payment_voucher_service

    upload = _upload(_pdf_bytes())
    upload.seek = AsyncMock(wraps=upload.seek)
    upload.read = AsyncMock(wraps=upload.read)
    with (
        patch(
            "src.services.contract.payment_voucher_service.payment_flow_service.get_flow_in_scope",
            new=AsyncMock(side_effect=ResourceNotFoundError("PaymentFlow", "flow-1")),
        ),
        patch.object(payment_voucher_service, "uploads_root", tmp_path),
    ):
        with pytest.raises(ResourceNotFoundError):
            await payment_voucher_service.upload_voucher(
                mock_db,
                flow_id="flow-1",
                file=upload,
                user_id="user-1",
            )

    upload.seek.assert_not_awaited()
    upload.read.assert_not_awaited()
    assert list(tmp_path.rglob("*")) == []


async def test_upload_voucher_links_generic_attachment_to_active_flow(
    mock_db, tmp_path: Path
) -> None:
    from src.services.contract.payment_voucher_service import payment_voucher_service

    flow = SimpleNamespace(
        flow_id="flow-1", status="active", voucher_attachment_ids=None, updated_at=None
    )

    async def _create(_db, *, data, commit):  # noqa: ANN001
        assert commit is False
        return SimpleNamespace(**data)

    with (
        patch(
            "src.services.contract.payment_voucher_service.payment_flow_service.get_flow_in_scope",
            new=AsyncMock(return_value=flow),
        ) as mock_scope,
        patch(
            "src.services.contract.payment_voucher_service.attachment_crud.create",
            new=AsyncMock(side_effect=_create),
        ) as mock_create,
        patch.object(payment_voucher_service, "uploads_root", tmp_path),
    ):
        attachment = await payment_voucher_service.upload_voucher(
            mock_db,
            flow_id="flow-1",
            file=_upload(_pdf_bytes()),
            user_id="user-1",
        )

    assert attachment.id in flow.voucher_attachment_ids
    assert attachment.owner_type == "payment_flow"
    assert attachment.owner_id == "flow-1"
    assert attachment.file_hash is not None
    assert (tmp_path / attachment.storage_key).is_file()
    assert mock_scope.await_args.kwargs["for_update"] is True
    mock_create.assert_awaited_once()
    mock_db.commit.assert_awaited_once()


async def test_upload_voucher_rejects_correct_header_with_damaged_pdf(
    mock_db, tmp_path: Path
) -> None:
    from src.services.contract.payment_voucher_service import payment_voucher_service

    flow = SimpleNamespace(
        flow_id="flow-1", status="active", voucher_attachment_ids=None
    )
    with (
        patch(
            "src.services.contract.payment_voucher_service.payment_flow_service.get_flow_in_scope",
            new=AsyncMock(return_value=flow),
        ),
        patch(
            "src.services.contract.payment_voucher_service.attachment_crud.create",
            new=AsyncMock(),
        ) as mock_create,
        patch.object(payment_voucher_service, "uploads_root", tmp_path),
    ):
        with pytest.raises(UploadValidationError) as exc_info:
            await payment_voucher_service.upload_voucher(
                mock_db,
                flow_id="flow-1",
                file=_upload(b"%PDF-1.7\nbroken"),
                user_id="user-1",
            )

    assert exc_info.value.details["upload_error_code"] in {
        "pdf_invalid",
        "pdf_repaired",
    }
    mock_create.assert_not_awaited()
    assert list(tmp_path.rglob("*.pdf")) == []


async def test_upload_voucher_database_failure_removes_promoted_file(
    mock_db, tmp_path: Path
) -> None:
    from src.services.contract.payment_voucher_service import payment_voucher_service

    flow = SimpleNamespace(
        flow_id="flow-1", status="active", voucher_attachment_ids=None, updated_at=None
    )
    with (
        patch(
            "src.services.contract.payment_voucher_service.payment_flow_service.get_flow_in_scope",
            new=AsyncMock(return_value=flow),
        ),
        patch(
            "src.services.contract.payment_voucher_service.attachment_crud.create",
            new=AsyncMock(side_effect=RuntimeError("database unavailable")),
        ),
        patch.object(payment_voucher_service, "uploads_root", tmp_path),
    ):
        with pytest.raises(RuntimeError, match="database unavailable"):
            await payment_voucher_service.upload_voucher(
                mock_db,
                flow_id="flow-1",
                file=_upload(_pdf_bytes()),
                user_id="user-1",
            )

    mock_db.rollback.assert_awaited_once()
    assert list(tmp_path.rglob("*.pdf")) == []

async def test_upload_voucher_rollback_failure_still_removes_promoted_file(
    mock_db, tmp_path: Path
) -> None:
    from src.services.contract.payment_voucher_service import payment_voucher_service

    flow = SimpleNamespace(
        flow_id="flow-1", status="active", voucher_attachment_ids=None, updated_at=None
    )
    mock_db.rollback.side_effect = RuntimeError("rollback unavailable")
    with (
        patch(
            "src.services.contract.payment_voucher_service.payment_flow_service.get_flow_in_scope",
            new=AsyncMock(return_value=flow),
        ),
        patch(
            "src.services.contract.payment_voucher_service.attachment_crud.create",
            new=AsyncMock(side_effect=RuntimeError("database unavailable")),
        ),
        patch.object(payment_voucher_service, "uploads_root", tmp_path),
    ):
        with pytest.raises(RuntimeError, match="rollback unavailable"):
            await payment_voucher_service.upload_voucher(
                mock_db,
                flow_id="flow-1",
                file=_upload(_pdf_bytes()),
                user_id="user-1",
            )

    assert list(tmp_path.rglob("*.pdf")) == []


async def test_upload_voucher_cancellation_removes_promoted_file(
    mock_db, tmp_path: Path
) -> None:
    from src.services.contract.payment_voucher_service import payment_voucher_service

    flow = SimpleNamespace(
        flow_id="flow-1", status="active", voucher_attachment_ids=None, updated_at=None
    )
    with (
        patch(
            "src.services.contract.payment_voucher_service.payment_flow_service.get_flow_in_scope",
            new=AsyncMock(return_value=flow),
        ),
        patch(
            "src.services.contract.payment_voucher_service.attachment_crud.create",
            new=AsyncMock(side_effect=asyncio.CancelledError()),
        ),
        patch.object(payment_voucher_service, "uploads_root", tmp_path),
    ):
        with pytest.raises(asyncio.CancelledError):
            await payment_voucher_service.upload_voucher(
                mock_db,
                flow_id="flow-1",
                file=_upload(_pdf_bytes()),
                user_id="user-1",
            )

    assert list(tmp_path.rglob("*.pdf")) == []
