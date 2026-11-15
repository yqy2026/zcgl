"""Batch pairing suggests by normalized contract number and commits atomically."""

from types import SimpleNamespace
from types import SimpleNamespace as Row
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.archive_batch_match import (
    BatchMatchCommitRequest,
    BatchMatchSelection,
)
from src.services.asset_operations import archive_batch_match_service as module
from src.services.party_scope_resolver import EffectivePartyScope

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

SCOPE = EffectivePartyScope(
    user_id="actor", source="explicit", scope_mode="owner", owner_party_ids=["owner"]
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("20250812-【元件合字[2025]第018号】-租赁合同-东川路83号", "元件合字[2025]18号"),
        ("元件司合字【2021】09号-多宝路", "元件司合字[2021]9号"),
        ("五羊司合字[2024]112号-租赁合同（盖章版）", "五羊司合字[2024]112号"),
        ("【五羊司合字[2025]32号】江南苑A05", "五羊司合字[2025]32号"),
        ("【焊机司合字[2021]2号、补1】较场西路", "焊机司合字[2021]2号"),
        ("租赁合同（史巷）（盖章版）", None),
        ("元件合字〔2025〕第18号", "元件合字[2025]18号"),
    ],
)
def test_normalize_contract_number_handles_real_variants(raw, expected):
    assert module.normalize_contract_number(raw) == expected


def _entry(staging_id, name):
    return Row(staging_id=staging_id, staged=Row(original_filename=name), original_name=name)


def _service(monkeypatch, contracts, archived=()):
    service = module.ArchiveBatchMatchService()
    monkeypatch.setattr(
        service,
        "contracts",
        SimpleNamespace(contract_numbers_in_scope=AsyncMock(return_value=contracts)),
    )
    monkeypatch.setattr(
        service,
        "documents",
        SimpleNamespace(
            target_rows=AsyncMock(
                side_effect=lambda db, *, target_type, target_id, document_type: [
                    (Row(id="d"), Row(id="a", owner_type="contract", owner_id=target_id))
                ]
                if target_id in archived
                else []
            )
        ),
    )
    return service


def _file(name):
    return Row(filename=name, size=4, read=AsyncMock(return_value=b"data"), headers={})


def _stage(monkeypatch, service):
    staged = Row(
        original_filename="staged.pdf",
        canonical_extension=".pdf",
        size_bytes=4,
        sha256="a" * 64,
    )
    lifecycle = MagicMock()
    lifecycle.stage_upload = AsyncMock(side_effect=lambda f, purpose: staged)
    monkeypatch.setattr(module, "StagedFileService", lambda root: lifecycle)
    return lifecycle


UPSTREAM = ("upstream_contract", "u1", "五羊司合字[2024]214号", "北京路物业")
TERMINAL = ("terminal_contract", "t1", "元件合字[2025]第018号", "东川路铺位")


async def test_preview_detects_and_flags_existing(monkeypatch):
    service = _service(
        monkeypatch,
        [UPSTREAM, TERMINAL],
        archived=("u1",),
    )
    _stage(monkeypatch, service)
    preview = await service.preview(
        MagicMock(),
        files=[
            _file("20250812-【元件合字[2025]第018号】-租赁合同.pdf"),
            _file("【五羊司合字[2024]214号】合同.pdf"),
        ],
        actor_id="actor",
        scope=SCOPE,
    )
    by_name = {item.file_name: item for item in preview.items}
    detected = by_name["20250812-【元件合字[2025]第018号】-租赁合同.pdf"].detected
    assert detected.target_type == "terminal_contract"
    assert detected.target_id == "t1"
    assert by_name["20250812-【元件合字[2025]第018号】-租赁合同.pdf"].already_archived is False
    stamped = by_name["【五羊司合字[2024]214号】合同.pdf"].detected
    assert stamped.target_type == "upstream_contract"
    assert stamped.target_id == "u1"
    assert by_name["【五羊司合字[2024]214号】合同.pdf"].already_archived is True


async def test_preview_reports_ambiguous_numbers_without_autoselect(monkeypatch):
    clash = ("upstream_contract", "u2", TERMINAL[2], "同编号上游")
    service = _service(monkeypatch, [TERMINAL, clash])
    _stage(monkeypatch, service)
    preview = await service.preview(
        MagicMock(),
        files=[_file("【元件合字[2025]第018号】.pdf")],
        actor_id="actor",
        scope=SCOPE,
    )
    item = preview.items[0]
    assert item.detected is None
    assert {candidate.target_id for candidate in item.ambiguous} == {"t1", "u2"}
    assert item.already_archived is False


async def test_preview_without_number_leaves_detection_empty(monkeypatch):
    service = _service(monkeypatch, [UPSTREAM])
    _stage(monkeypatch, service)
    preview = await service.preview(
        MagicMock(), files=[_file("租赁合同（盖章版）.pdf")], actor_id="actor", scope=SCOPE
    )
    assert preview.items[0].detected is None
    assert preview.items[0].ambiguous == []
    assert preview.items[0].already_archived is False


def _request(token, matches):
    return BatchMatchCommitRequest(
        preview_token=token,
        matches=[
            BatchMatchSelection(
                staging_id=s, target_type=t, target_id=i
            )
            for s, t, i in matches
        ],
    )


async def test_commit_writes_all_files_in_one_transaction(monkeypatch):
    service = _service(monkeypatch, [UPSTREAM, TERMINAL])
    _stage(monkeypatch, service)
    preview = await service.preview(
        MagicMock(),
        files=[_file("【五羊司合字[2024]214号】.pdf"), _file("东川路.pdf")],
        actor_id="actor",
        scope=SCOPE,
    )
    staging_ids = [item.staging_id for item in preview.items]
    parents = AsyncMock()
    monkeypatch.setattr(
        module, "contract_supplement_service", SimpleNamespace(_parent=parents)
    )
    written = []
    versions = []

    async def write(db, **kwargs):
        written.append(kwargs)
        version = Row(
            attachment=Row(
                id=f"a{len(written)}",
                file_name=kwargs["staged"].original_filename,
                file_type="pdf",
                file_size=4,
            ),
            document=Row(
                id=f"d{len(written)}",
                document_type=kwargs["archive_target"][2],
                target_type=kwargs["archive_target"][0],
                target_id=kwargs["archive_target"][1],
                attachment_id=f"a{len(written)}",
                document_version=1,
                replaces_document_id=None,
                uploaded_at="2026-11-04T00:00:00",
            ),
            is_current=True,
        )
        versions.append(version)
        return version, Row(storage_key=f"k{len(written)}")

    monkeypatch.setattr(service, "files", SimpleNamespace(_write_staged=write))
    db = MagicMock(commit=AsyncMock(), rollback=AsyncMock())
    result = await service.commit(
        db,
        request=_request(
            preview.preview_token,
            [
                (staging_ids[0], "upstream_contract", "u1"),
                (staging_ids[1], "terminal_contract", "t1"),
            ],
        ),
        actor_id="actor",
        scope=SCOPE,
    )
    assert [item.id for item in result.items] == ["d1", "d2"]
    assert db.commit.await_count == 1
    db.rollback.assert_not_awaited()
    # Both parents were locked for write in a stable order.
    assert [c.args[1] for c in parents.await_args_list] == ["terminal", "upstream"]


async def test_commit_rejects_duplicate_target_and_rolls_back(monkeypatch):
    service = _service(monkeypatch, [UPSTREAM])
    _stage(monkeypatch, service)
    preview = await service.preview(
        MagicMock(),
        files=[_file("【五羊司合字[2024]214号】.pdf"), _file("第二份.pdf")],
        actor_id="actor",
        scope=SCOPE,
    )
    staging_ids = [item.staging_id for item in preview.items]
    monkeypatch.setattr(
        module, "contract_supplement_service", SimpleNamespace(_parent=AsyncMock())
    )
    db = MagicMock(commit=AsyncMock(), rollback=AsyncMock())
    with pytest.raises(module.BaseBusinessError) as caught:
        await service.commit(
            db,
            request=_request(
                preview.preview_token,
                [
                    (staging_ids[0], "upstream_contract", "u1"),
                    (staging_ids[1], "upstream_contract", "u1"),
                ],
            ),
            actor_id="actor",
            scope=SCOPE,
        )
    assert caught.value.code == "ARCHIVE_BATCH_DUPLICATE_TARGET"
    db.commit.assert_not_awaited()


async def test_commit_rejects_target_with_existing_archive(monkeypatch):
    service = _service(monkeypatch, [UPSTREAM], archived=("u1",))
    _stage(monkeypatch, service)
    preview = await service.preview(
        MagicMock(), files=[_file("【五羊司合字[2024]214号】.pdf")], actor_id="actor", scope=SCOPE
    )
    staging_id = preview.items[0].staging_id
    monkeypatch.setattr(
        module, "contract_supplement_service", SimpleNamespace(_parent=AsyncMock())
    )
    write = AsyncMock()
    monkeypatch.setattr(service, "files", SimpleNamespace(_write_staged=write))
    db = MagicMock(commit=AsyncMock(), rollback=AsyncMock())
    with pytest.raises(module.BaseBusinessError) as caught:
        await service.commit(
            db,
            request=_request(preview.preview_token, [(staging_id, "upstream_contract", "u1")]),
            actor_id="actor",
            scope=SCOPE,
        )
    assert caught.value.code == "ARCHIVE_TARGET_ALREADY_HAS_FILE"
    write.assert_not_awaited()
    db.commit.assert_not_awaited()


async def test_commit_rejects_unknown_token_and_foreign_actor(monkeypatch):
    service = _service(monkeypatch, [])
    _stage(monkeypatch, service)
    db = MagicMock()
    with pytest.raises(module.ResourceNotFoundError):
        await service.commit(
            db,
            request=_request("missing", [("s", "upstream_contract", "u1")]),
            actor_id="actor",
            scope=SCOPE,
        )
    preview = await service.preview(
        MagicMock(), files=[_file("东川路.pdf")], actor_id="actor", scope=SCOPE
    )
    with pytest.raises(module.ResourceNotFoundError):
        await service.commit(
            db,
            request=_request(
                preview.preview_token, [(preview.items[0].staging_id, "upstream_contract", "u1")]
            ),
            actor_id="someone-else",
            scope=SCOPE,
        )


async def test_expired_preview_is_rejected_and_cleaned(monkeypatch):
    service = _service(monkeypatch, [UPSTREAM])
    lifecycle = _stage(monkeypatch, service)
    monkeypatch.setattr(
        service, "clock", lambda: __import__("datetime").datetime(2026, 11, 4, 12, 0)
    )
    preview = await service.preview(
        MagicMock(), files=[_file("【五羊司合字[2024]214号】.pdf")], actor_id="actor", scope=SCOPE
    )
    staging_id = preview.items[0].staging_id
    monkeypatch.setattr(
        service, "clock", lambda: __import__("datetime").datetime(2026, 11, 4, 13, 1)
    )
    db = MagicMock()
    with pytest.raises(module.BaseBusinessError) as caught:
        await service.commit(
            db,
            request=_request(preview.preview_token, [(staging_id, "upstream_contract", "u1")]),
            actor_id="actor",
            scope=SCOPE,
        )
    assert caught.value.code == "BATCH_PREVIEW_EXPIRED"
    lifecycle.discard_staged.assert_called()


async def test_midbatch_failure_invalidates_whole_preview(monkeypatch):
    service = _service(monkeypatch, [UPSTREAM, TERMINAL])
    lifecycle = _stage(monkeypatch, service)
    preview = await service.preview(
        MagicMock(),
        files=[_file("【五羊司合字[2024]214号】.pdf"), _file("东川路.pdf")],
        actor_id="actor",
        scope=SCOPE,
    )
    staging_ids = [item.staging_id for item in preview.items]
    monkeypatch.setattr(
        module, "contract_supplement_service", SimpleNamespace(_parent=AsyncMock())
    )
    calls = []

    async def write(db, **kwargs):
        calls.append(kwargs)
        if len(calls) == 2:
            raise RuntimeError("second file failed")
        version = Row(
            attachment=Row(id="a1", file_name="f", file_type="pdf", file_size=4),
            document=Row(
                id="d1",
                document_type=kwargs["archive_target"][2],
                target_type=kwargs["archive_target"][0],
                target_id=kwargs["archive_target"][1],
                attachment_id="a1",
                document_version=1,
                replaces_document_id=None,
                uploaded_at="2026-11-04T00:00:00",
            ),
            is_current=True,
        )
        return version, Row(storage_key="k1")

    monkeypatch.setattr(service, "files", SimpleNamespace(_write_staged=write))
    db = MagicMock(commit=AsyncMock(), rollback=AsyncMock())
    with pytest.raises(RuntimeError, match="second file failed"):
        await service.commit(
            db,
            request=_request(
                preview.preview_token,
                [
                    (staging_ids[0], "upstream_contract", "u1"),
                    (staging_ids[1], "terminal_contract", "t1"),
                ],
            ),
            actor_id="actor",
            scope=SCOPE,
        )
    assert db.rollback.await_count == 1
    db.commit.assert_not_awaited()
    # Every staging file of the preview is discarded; the session is gone.
    assert lifecycle.discard_staged.call_count == 2
    with pytest.raises(module.ResourceNotFoundError):
        await service.commit(
            db,
            request=_request(preview.preview_token, [(staging_ids[0], "upstream_contract", "u1")]),
            actor_id="actor",
            scope=SCOPE,
        )


async def test_partial_commit_keeps_remaining_files_pairable(monkeypatch):
    service = _service(monkeypatch, [UPSTREAM, TERMINAL])
    _stage(monkeypatch, service)
    preview = await service.preview(
        MagicMock(),
        files=[_file("【五羊司合字[2024]214号】.pdf"), _file("东川路.pdf")],
        actor_id="actor",
        scope=SCOPE,
    )
    first, second = (item.staging_id for item in preview.items)
    monkeypatch.setattr(
        module, "contract_supplement_service", SimpleNamespace(_parent=AsyncMock())
    )

    async def write2(db, **kwargs):
        version = SimpleNamespace(
            attachment=SimpleNamespace(id="a1", file_name="f", file_type="pdf", file_size=4),
            document=SimpleNamespace(
                id="d1",
                document_type=kwargs["archive_target"][2],
                target_type=kwargs["archive_target"][0],
                target_id=kwargs["archive_target"][1],
                attachment_id="a1",
                document_version=1,
                replaces_document_id=None,
                uploaded_at="2026-11-04T00:00:00",
            ),
            is_current=True,
        )
        return version, SimpleNamespace(storage_key="k1")

    monkeypatch.setattr(service, "files", SimpleNamespace(_write_staged=write2))
    db = MagicMock(commit=AsyncMock(), rollback=AsyncMock())
    await service.commit(
        db,
        request=_request(preview.preview_token, [(first, "upstream_contract", "u1")]),
        actor_id="actor",
        scope=SCOPE,
    )
    # The consumed file is gone but the untouched one can still be committed
    # with the same token.
    await service.commit(
        db,
        request=_request(preview.preview_token, [(second, "terminal_contract", "t1")]),
        actor_id="actor",
        scope=SCOPE,
    )
    with pytest.raises(module.ResourceNotFoundError):
        await service.commit(
            db,
            request=_request(preview.preview_token, [(second, "terminal_contract", "t1")]),
            actor_id="actor",
            scope=SCOPE,
        )


async def test_misowned_archive_rows_fail_loud(monkeypatch):
    service = _service(monkeypatch, [UPSTREAM])
    _stage(monkeypatch, service)
    preview = await service.preview(
        MagicMock(), files=[_file("【五羊司合字[2024]214号】.pdf")], actor_id="actor", scope=SCOPE
    )
    staging_id = preview.items[0].staging_id
    monkeypatch.setattr(
        module, "contract_supplement_service", SimpleNamespace(_parent=AsyncMock())
    )
    monkeypatch.setattr(
        service,
        "documents",
        SimpleNamespace(
            target_rows=AsyncMock(
                return_value=[
                    (
                        Row(id="d0", document_version=1),
                        Row(id="a0", owner_type="contract", owner_id="other-contract"),
                    )
                ]
            )
        ),
    )
    db = MagicMock(commit=AsyncMock(), rollback=AsyncMock())
    with pytest.raises(module.ResourceNotFoundError):
        await service.commit(
            db,
            request=_request(preview.preview_token, [(staging_id, "upstream_contract", "u1")]),
            actor_id="actor",
            scope=SCOPE,
        )
    db.commit.assert_not_awaited()
