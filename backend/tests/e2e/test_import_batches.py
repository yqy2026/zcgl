"""E2E tests for the three-sheet import batch lifecycle (V4-3 ~ V4-5)."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from openpyxl import Workbook

from src.api.v1 import import_batches as import_api
from src.services.asset_operations.import_workbook_parser import (
    TEMPLATE_VERSION,
    TERMINAL_HEADERS,
    UNIT_HEADERS,
    UPSTREAM_HEADERS,
    parse_import_workbook,
)
from src.services.party_scope_resolver import EffectivePartyScope
from tests.e2e.factories import create_approved_legal_party

pytestmark = pytest.mark.e2e


def _one_page_pdf() -> bytes:
    import fitz

    doc = fitz.open()
    doc.new_page()
    try:
        return doc.tobytes()
    finally:
        doc.close()


PDF_BYTES = _one_page_pdf()


def _workbook_bytes() -> Workbook:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for sheet_name, headers in (
        ("物业单元", UNIT_HEADERS),
        ("承租合同", UPSTREAM_HEADERS),
        ("终端合同", TERMINAL_HEADERS),
    ):
        sheet = workbook.create_sheet(title=sheet_name)
        sheet.append(list(headers))
        sheet.append(
            [f"template_version={TEMPLATE_VERSION}"] + [""] * (len(headers) - 1)
        )
        sheet.row_dimensions[2].hidden = True
    return workbook


def _as_bytes(workbook: Workbook) -> bytes:
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _unit_row(sheet, code, party="导入产权方"):
    sheet.append(
        [
            code,
            "导入单元",
            party,
            "IMP-PRJ",
            "导入地址 1 号",
            "commercial",
            "owned",
            "2026-01-01",
            "",
            "100",
            "200",
            "180",
        ]
    )


def _stage(start, end):
    return [start, end, "3000", "0", "0", "0", "3000", "monthly", "15"]


def _upstream(number, scan, unit):
    return [
        number,
        "lease",
        f"{number}名称",
        "导入产权方",
        "导入运营方",
        unit,
        "2026-01-01",
        "2026-12-31",
        "monthly",
        "15",
        "5000",
        "",
        scan,
    ]


def _terminal(number, scan, unit, upstream=""):
    return [
        number,
        "sublease",
        "导入租户",
        "导入运营方",
        unit,
        upstream,
        "2026-01-01",
        "2026-12-31",
        "2000",
        "",
        scan,
    ]


async def _unrestricted(db, *, user_id):
    return EffectivePartyScope(
        user_id=user_id, source="role", scope_mode="unrestricted"
    )


def _post(client, csrf_headers, path, **kwargs):
    headers = {**csrf_headers, **kwargs.pop("headers", {})}
    return client.post(path, headers=headers, **kwargs)


def _body(response):
    payload = response.json()
    return payload.get("data", payload)


@pytest.fixture
def import_facts(db_session):
    suffix = uuid4().hex[:10]
    create_approved_legal_party(db_session, suffix=suffix, name="导入产权方")
    manager = create_approved_legal_party(
        db_session, suffix=f"m{suffix}", name="导入运营方"
    )
    create_approved_legal_party(db_session, suffix=f"t{suffix}", name="导入租户")
    from src.models.project import Project

    db_session.add(
        Project(
            id=str(uuid4()),
            project_code="IMP-PRJ",
            project_name="导入测试项目",
            manager_party_id=manager.id,
            status="active",
        )
    )
    db_session.commit()


def _stage_one_scan(client, csrf_headers, name):
    response = _post(
        client,
        csrf_headers,
        "/api/v1/import-batches/scan-staging",
        files=[("files", (name, io.BytesIO(PDF_BYTES), "application/pdf"))],
    )
    assert response.status_code == 201, response.text
    return name


def _upload_batch(client, csrf_headers, workbook, mode):
    response = _post(
        client,
        csrf_headers,
        "/api/v1/import-batches",
        data={"mode": mode},
        files={
            "file": (
                f"import-{uuid4().hex[:6]}.xlsx",
                io.BytesIO(_as_bytes(workbook)),
                "application/octet-stream",
            )
        },
        headers={"Idempotency-Key": f"up-{uuid4()}"},
    )
    assert response.status_code == 201, response.text
    return _body(response)


def _replay_commit(client, csrf_headers, batch, proposal, idempotency_key):
    return _post(
        client,
        csrf_headers,
        f"/api/v1/import-batches/{batch['id']}/commit",
        json={
            "commit_token": proposal["commit_token"],
            "expected_version": batch["version"],
            "proposal_hash": proposal["proposal_hash"],
            "idempotency_key": idempotency_key,
        },
        headers={"Idempotency-Key": idempotency_key},
    )


def _commit_batch(client, csrf_headers, batch, idempotency_key):
    preview = _post(
        client, csrf_headers, f"/api/v1/import-batches/{batch['id']}/commit-preview"
    )
    assert preview.status_code == 200, preview.text
    proposal = _body(preview)
    response = _post(
        client,
        csrf_headers,
        f"/api/v1/import-batches/{batch['id']}/commit",
        json={
            "commit_token": proposal["commit_token"],
            "expected_version": batch["version"],
            "proposal_hash": proposal["proposal_hash"],
            "idempotency_key": idempotency_key,
        },
        headers={"Idempotency-Key": idempotency_key},
    )
    return response, proposal


def test_template_download_parses_clean(authenticated_client):
    response = authenticated_client.get("/api/v1/imports/templates/create")
    assert response.status_code == 200
    parsed = parse_import_workbook(response.content, mode="create")
    assert parsed.error_count == 0


def test_create_mode_end_to_end_and_idempotent_replay(
    authenticated_client, csrf_headers, import_facts, monkeypatch
):
    monkeypatch.setattr(import_api.party_scope_resolver, "resolve", _unrestricted)
    client = authenticated_client
    run = uuid4().hex[:6]
    unit_code = f"IMP-U-{run}"
    upstream_scan = _stage_one_scan(client, csrf_headers, f"HT-{run}.pdf")
    terminal_scan = _stage_one_scan(client, csrf_headers, f"ZD-{run}.pdf")

    workbook = _workbook_bytes()
    _unit_row(workbook["物业单元"], unit_code)
    workbook["承租合同"].append(
        _upstream(f"HT-{run}", upstream_scan, unit_code)
        + _stage("2026-01-01", "2026-12-31")
    )
    workbook["终端合同"].append(
        _terminal(f"ZD-{run}", terminal_scan, unit_code)
        + _stage("2026-01-01", "2026-12-31")
    )

    batch = _upload_batch(client, csrf_headers, workbook, "create")
    assert batch["status"] == "ready", batch
    assert batch["error_count"] == 0

    changes = client.get(f"/api/v1/import-batches/{batch['id']}/changes")
    assert changes.status_code == 200
    items = _body(changes)["items"]
    assert {item["target_type"] for item in items} == {
        "asset_unit",
        "upstream_contract",
        "terminal_contract",
    }

    commit, proposal = _commit_batch(client, csrf_headers, batch, f"idem-{run}")
    assert commit.status_code == 200, commit.text
    assert _body(commit)["status"] == "committed"

    units = client.get("/api/v1/asset-units", params={"q": unit_code})
    assert units.status_code == 200
    assert any(unit_code in str(item) for item in _body(units).get("items", []))

    replay = _replay_commit(client, csrf_headers, batch, proposal, f"idem-{run}")
    assert replay.status_code == 200
    assert _body(replay)["idempotent"] is True


def test_unknown_party_blocks_batch(
    authenticated_client, csrf_headers, import_facts, monkeypatch
):
    monkeypatch.setattr(import_api.party_scope_resolver, "resolve", _unrestricted)
    client = authenticated_client
    run = uuid4().hex[:6]
    unit_code = f"IMP-U-4-{run}"
    scan = _stage_one_scan(client, csrf_headers, f"ht404-{run}.pdf")

    workbook = _workbook_bytes()
    _unit_row(workbook["物业单元"], unit_code, party="不存在的主体")
    workbook["承租合同"].append(
        _upstream(f"HT-404-{run}", scan, unit_code) + _stage("2026-01-01", "2026-12-31")
    )

    batch = _upload_batch(client, csrf_headers, workbook, "create")
    assert batch["status"] == "invalid"
    assert batch["error_count"] >= 1

    commit = _post(
        client,
        csrf_headers,
        f"/api/v1/import-batches/{batch['id']}/commit",
        json={
            "commit_token": "x",
            "expected_version": batch["version"],
            "proposal_hash": "x",
            "idempotency_key": f"idem-404-{run}",
        },
        headers={"Idempotency-Key": f"idem-404-{run}"},
    )
    assert commit.status_code == 409
    assert commit.json()["error"]["code"] == "IMPORT_HAS_ERRORS"


def test_shared_scan_rolls_back_whole_batch(
    authenticated_client, csrf_headers, import_facts, monkeypatch
):
    monkeypatch.setattr(import_api.party_scope_resolver, "resolve", _unrestricted)
    client = authenticated_client
    run = uuid4().hex[:6]
    unit_code = f"IMP-U-S-{run}"
    scan = _stage_one_scan(client, csrf_headers, f"shared-{run}.pdf")

    workbook = _workbook_bytes()
    _unit_row(workbook["物业单元"], unit_code)
    workbook["承租合同"].append(
        _upstream(f"HT-A-{run}", scan, unit_code) + _stage("2026-01-01", "2026-12-31")
    )
    workbook["承租合同"].append(
        _upstream(f"HT-B-{run}", scan, unit_code) + _stage("2026-01-01", "2026-12-31")
    )

    batch = _upload_batch(client, csrf_headers, workbook, "create")
    assert batch["status"] == "ready"

    commit, _ = _commit_batch(client, csrf_headers, batch, f"idem-shared-{run}")
    assert commit.status_code in (409, 500), commit.text

    units = client.get("/api/v1/asset-units", params={"q": unit_code})
    assert _body(units).get("items", []) == [], "整批回滚不得留下已建单元"


def test_update_mode_diff_and_selection(
    authenticated_client, csrf_headers, import_facts, monkeypatch
):
    monkeypatch.setattr(import_api.party_scope_resolver, "resolve", _unrestricted)
    client = authenticated_client
    run = uuid4().hex[:6]
    unit_code = f"IMP-U-U-{run}"
    scan = _stage_one_scan(client, csrf_headers, f"upd-{run}.pdf")

    workbook = _workbook_bytes()
    _unit_row(workbook["物业单元"], unit_code)
    workbook["承租合同"].append(
        _upstream(f"HT-UPD-{run}", scan, unit_code) + _stage("2026-01-01", "2026-12-31")
    )
    batch = _upload_batch(client, csrf_headers, workbook, "create")
    commit, _ = _commit_batch(client, csrf_headers, batch, f"idem-upd-{run}")
    assert commit.status_code == 200, commit.text

    update_wb = _workbook_bytes()
    update_wb["物业单元"].append(
        [unit_code, "改名后的单元", "", "", "", "", "", "", "", "", "", ""]
    )
    update_batch = _upload_batch(client, csrf_headers, update_wb, "update")
    assert update_batch["status"] == "ready", update_batch

    changes = client.get(
        f"/api/v1/import-batches/{update_batch['id']}/changes",
        params={"severity": "change"},
    )
    items = _body(changes)["items"]
    assert len(items) == 1
    assert items[0]["field_name"] == "name"
    assert items[0]["old_value"]["value"] == "导入单元"
    assert items[0]["new_value"]["value"] == "改名后的单元"

    selection = client.put(
        f"/api/v1/import-batches/{update_batch['id']}/selection",
        json={"selections": {items[0]["id"]: False}},
        headers=csrf_headers,
    )
    assert selection.status_code == 200, selection.text
    refreshed = _body(selection)
    assert refreshed["proposal_hash"] != update_batch["proposal_hash"]

    preview = _post(
        client,
        csrf_headers,
        f"/api/v1/import-batches/{update_batch['id']}/commit-preview",
    )
    assert preview.status_code == 200, preview.text
    proposal = _body(preview)
    assert proposal["change_count"] == 0

    commit = _post(
        client,
        csrf_headers,
        f"/api/v1/import-batches/{update_batch['id']}/commit",
        json={
            "commit_token": proposal["commit_token"],
            "expected_version": refreshed["version"],
            "proposal_hash": proposal["proposal_hash"],
            "idempotency_key": f"idem-sel-{run}",
        },
        headers={"Idempotency-Key": f"idem-sel-{run}"},
    )
    assert commit.status_code == 200, commit.text
    units = client.get("/api/v1/asset-units", params={"q": unit_code})
    kept = _body(units)["items"]
    assert any(item.get("name") == "导入单元" for item in kept), (
        "取消选择后提交不得应用改名"
    )


def test_revert_removes_created_facts(
    authenticated_client, csrf_headers, import_facts, monkeypatch
):
    monkeypatch.setattr(import_api.party_scope_resolver, "resolve", _unrestricted)
    client = authenticated_client
    run = uuid4().hex[:6]
    unit_code = f"IMP-U-R-{run}"
    scan = _stage_one_scan(client, csrf_headers, f"rev-{run}.pdf")

    workbook = _workbook_bytes()
    _unit_row(workbook["物业单元"], unit_code)
    workbook["承租合同"].append(
        _upstream(f"HT-REV-{run}", scan, unit_code) + _stage("2026-01-01", "2026-12-31")
    )
    batch = _upload_batch(client, csrf_headers, workbook, "create")
    commit, _ = _commit_batch(client, csrf_headers, batch, f"idem-rev-{run}")
    assert commit.status_code == 200, commit.text

    revert_preview = _post(
        client, csrf_headers, f"/api/v1/import-batches/{batch['id']}/revert-preview"
    )
    assert revert_preview.status_code == 200, revert_preview.text
    revert_proposal = _body(revert_preview)
    assert revert_proposal["blockers"] == []

    revert = _post(
        client,
        csrf_headers,
        f"/api/v1/import-batches/{batch['id']}/revert",
        json={
            "revert_token": revert_proposal["revert_token"],
            "reason": "导入错误",
            "idempotency_key": f"idem-revert-{run}",
        },
        headers={"Idempotency-Key": f"idem-revert-{run}"},
    )
    assert revert.status_code == 200, revert.text
    assert _body(revert)["status"] == "reverted"

    units = client.get("/api/v1/asset-units", params={"q": unit_code})
    assert _body(units).get("items", []) == []

    again = _post(
        client,
        csrf_headers,
        f"/api/v1/import-batches/{batch['id']}/revert",
        json={
            "revert_token": revert_proposal["revert_token"],
            "reason": "重复撤销",
            "idempotency_key": f"idem-revert-{run}",
        },
        headers={"Idempotency-Key": f"idem-revert-{run}"},
    )
    assert again.status_code == 200
    assert _body(again)["idempotent"] is True


def test_revert_deadline_is_seven_shanghai_days() -> None:
    from zoneinfo import ZoneInfo

    from src.services.asset_operations.import_batch_service import _revert_deadline

    committed = datetime(2026, 11, 15, 16, 0, tzinfo=UTC)
    result = _revert_deadline(committed)
    shanghai = ZoneInfo("Asia/Shanghai")
    assert result == datetime(2026, 11, 23, 0, 0, tzinfo=shanghai)
