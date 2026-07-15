"""Unit tests for payment-flow voucher storage and download auditing."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.core.exception_handler import BusinessValidationError, ResourceNotFoundError

pytestmark = pytest.mark.asyncio


async def test_download_voucher_records_success_before_returning_file(
    mock_db,
    tmp_path: Path,
) -> None:
    from src.services.contract.payment_voucher_service import payment_voucher_service

    flow = SimpleNamespace(
        flow_id="flow-1",
        voucher_attachment_ids=["attachment-1"],
    )
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
    assert mock_audit.await_args.kwargs["resource_id"] == "flow-1"
    assert '"attachment_id": "attachment-1"' in (
        mock_audit.await_args.kwargs["details"]
    )
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
                mock_db,
                flow_id="flow-1",
                current_user_id="user-1",
            )

    mock_list.assert_not_awaited()


async def test_upload_voucher_links_generic_attachment_to_active_flow(
    mock_db,
    tmp_path: Path,
) -> None:
    from src.services.contract.payment_voucher_service import payment_voucher_service

    flow = SimpleNamespace(
        flow_id="flow-1",
        status="active",
        voucher_attachment_ids=None,
        updated_at=None,
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
            file_name="receipt.pdf",
            content_type="application/pdf",
            content=b"%PDF-1.7\npdf-content",
            user_id="user-1",
        )

    assert attachment.id in flow.voucher_attachment_ids
    assert attachment.owner_type == "payment_flow"
    assert attachment.owner_id == "flow-1"
    assert attachment.file_hash is not None
    assert (tmp_path / attachment.storage_key).read_bytes() == b"%PDF-1.7\npdf-content"
    assert mock_scope.await_args.kwargs["for_update"] is True
    mock_create.assert_awaited_once()
    mock_db.commit.assert_awaited_once()


async def test_upload_voucher_rejects_spoofed_extension_without_magic_dependency(
    mock_db,
    tmp_path: Path,
) -> None:
    """A .pdf name must not make arbitrary bytes a payment voucher."""
    from src.services.contract.payment_voucher_service import payment_voucher_service

    flow = SimpleNamespace(
        flow_id="flow-1",
        status="active",
        voucher_attachment_ids=None,
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
        with pytest.raises(
            BusinessValidationError,
            match="voucher content does not match its PDF file type",
        ):
            await payment_voucher_service.upload_voucher(
                mock_db,
                flow_id="flow-1",
                file_name="spoofed.pdf",
                content_type="application/pdf",
                content=b"not-a-pdf",
                user_id="user-1",
            )

    mock_create.assert_not_awaited()
    mock_db.commit.assert_not_awaited()
