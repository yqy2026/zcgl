"""Regression tests for purpose-specific Excel and restore uploads."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import SpooledTemporaryFile
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import UploadFile
from openpyxl import Workbook
from starlette.datastructures import Headers

from src.schemas.excel_advanced import ExcelImportRequest
from src.services.file_upload import UploadValidationError

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
JSON_MIME = "application/json"


def _xlsx_upload(filename: str = "assets.xlsx") -> UploadFile:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["asset_name"])
    worksheet.append(["Example asset"])
    content = BytesIO()
    workbook.save(content)
    stream = SpooledTemporaryFile()
    stream.write(content.getvalue())
    stream.seek(0)
    return UploadFile(
        filename=filename,
        file=stream,
        headers=Headers({"content-type": XLSX_MIME}),
    )


def _json_upload(content: bytes) -> UploadFile:
    stream = SpooledTemporaryFile()
    stream.write(content)
    stream.seek(0)
    return UploadFile(
        filename="system-backup.json",
        file=stream,
        headers=Headers({"content-type": JSON_MIME}),
    )


@pytest.mark.asyncio
async def test_preview_rejects_legacy_xls_before_business_parser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.api.v1.documents.excel import preview

    monkeypatch.setattr(preview, "TEMP_UPLOAD_ROOT", tmp_path)
    with pytest.raises(UploadValidationError) as exc_info:
        await preview.preview_excel(file=_xlsx_upload("legacy.xls"), max_rows=10)

    assert exc_info.value.details["upload_error_code"] == "extension_not_allowed"
    assert not (tmp_path / ".staging").exists()


@pytest.mark.asyncio
async def test_sync_import_uses_and_discards_validated_staging_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.api.v1.documents.excel import import_ops

    monkeypatch.setattr(import_ops, "TEMP_UPLOAD_ROOT", tmp_path)
    importer = MagicMock()
    importer.import_assets_from_excel = AsyncMock(
        return_value={"total": 1, "success": 1, "failed": 0, "errors": []}
    )
    monkeypatch.setattr(import_ops, "ExcelImportService", MagicMock(return_value=importer))

    result = await import_ops.import_excel(
        file=_xlsx_upload(),
        should_skip_errors=False,
        sheet_name="Sheet",
        db=MagicMock(),
        current_user=MagicMock(organization_id=None),
    )

    staged_path = Path(importer.import_assets_from_excel.await_args.kwargs["file_path"])
    assert result["success"] == 1
    assert staged_path.suffix == ".xlsx"
    assert not staged_path.exists()
    assert not (tmp_path / ".staging").exists()


@pytest.mark.asyncio
async def test_async_import_defers_staged_file_cleanup_to_background_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.api.v1.documents.excel import import_ops

    monkeypatch.setattr(import_ops, "TEMP_UPLOAD_ROOT", tmp_path)
    task = MagicMock(id="task-1", status="pending")
    task_service = MagicMock(create_task=AsyncMock(return_value=task))
    background_tasks = MagicMock()
    result = await import_ops.import_excel_async(
        background_tasks=background_tasks,
        file=_xlsx_upload(),
        request=ExcelImportRequest(),
        db=MagicMock(),
        current_user=MagicMock(id="user-1", organization_id=None),
        task_service=task_service,
    )

    assert result["task_id"] == "task-1"
    _, kwargs = background_tasks.add_task.call_args
    staged_path = Path(kwargs["file_path"])
    assert staged_path.exists()
    assert kwargs["staging_root"] == tmp_path

    background_task_service = MagicMock(
        get_task=AsyncMock(return_value=task),
        update_task=AsyncMock(),
    )
    importer = MagicMock()
    importer.import_assets_from_excel = AsyncMock(return_value={})
    monkeypatch.setattr(import_ops, "ExcelImportService", MagicMock(return_value=importer))
    await import_ops._process_excel_import_async(
        task_id="task-1",
        file_path=str(staged_path),
        staging_root=tmp_path,
        request=ExcelImportRequest(),
        db_session=MagicMock(),
        task_service=background_task_service,
    )

    assert not staged_path.exists()


@pytest.mark.asyncio
async def test_system_restore_rejects_json_without_dedicated_backup_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.api.v1.system import system_settings

    monkeypatch.setattr(system_settings, "SYSTEM_SETTINGS_UPLOAD_ROOT", tmp_path)
    with pytest.raises(UploadValidationError) as exc_info:
        await system_settings.restore_system(
            backup_file=_json_upload(b'{"system_settings": {}}'),
            db=MagicMock(),
            current_user=MagicMock(),
            request=MagicMock(),
        )

    assert exc_info.value.details["upload_error_code"] == "json_schema_invalid"
    assert not (tmp_path / ".staging").exists()
