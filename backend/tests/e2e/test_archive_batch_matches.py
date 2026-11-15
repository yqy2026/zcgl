"""Batch pairing previews suggest by filename and commit atomically."""

import io
from datetime import date
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy import select

from src.api.v1 import archive_documents as api
from src.models.asset_contract import UpstreamContract, UpstreamContractAssetUnit
from src.models.attachment import Attachment
from src.services.party_scope_resolver import EffectivePartyScope
from tests.e2e.test_asset_unit_certificates import (
    certificate_facts as _certificate_facts,
)

certificate_facts = _certificate_facts

pytestmark = pytest.mark.e2e


def _image(color):
    out = io.BytesIO()
    Image.new("RGB", (4, 4), color).save(out, format="PNG")
    return out.getvalue()


def test_batch_match_preview_and_commit_http(
    authenticated_client,
    csrf_headers,
    certificate_facts,
    db_session,
    tmp_path,
    monkeypatch,
):
    from src.services.asset_operations.archive_batch_match_service import (
        archive_batch_match_service,
    )
    from src.services.property_certificate.attachment_service import (
        property_certificate_attachment_service,
    )

    f = certificate_facts
    monkeypatch.setattr(archive_batch_match_service, "uploads_root", tmp_path)
    monkeypatch.setattr(
        property_certificate_attachment_service, "uploads_root", tmp_path
    )
    client = authenticated_client

    upstream_id = str(uuid4())
    terminal_id = str(uuid4())

    def placeholder_scan(contract_id):
        staged = str(uuid4())
        db_session.add(
            Attachment(
                id=staged,
                owner_type="contract",
                owner_id="intake-session-" + contract_id,
                file_name="staged.pdf",
                file_type="pdf",
                file_size=1,
                storage_key="intake/" + staged,
                created_by=str(uuid4()),
            )
        )
        db_session.flush()
        return staged

    db_session.add(
        UpstreamContract(
            id=upstream_id,
            contract_number="五羊司合字[2024]214号",
            contract_type="lease",
            name="批量配对上游",
            owner_party_id=f["owner"],
            operator_party_id=f["manager"],
            start_date=date(2020, 1, 1),
            end_date=date(2030, 1, 1),
            payment_cycle="monthly",
            scan_document_id=(upstream_scan := placeholder_scan(upstream_id)),
        )
    )
    db_session.add(
        UpstreamContract(
            id=terminal_id,
            contract_number="元件合字[2025]第018号",
            contract_type="lease",
            name="批量配对终端占位",
            owner_party_id=f["owner"],
            operator_party_id=f["manager"],
            start_date=date(2020, 1, 1),
            end_date=date(2030, 1, 1),
            payment_cycle="monthly",
            scan_document_id=placeholder_scan(terminal_id),
        )
    )
    db_session.flush()
    db_session.add(
        UpstreamContractAssetUnit(
            upstream_contract_id=upstream_id,
            asset_unit_id=f["visible_unit"],
            effective_from=date(2020, 1, 1),
        )
    )
    db_session.add(
        UpstreamContractAssetUnit(
            upstream_contract_id=terminal_id,
            asset_unit_id=f["visible_unit"],
            effective_from=date(2020, 1, 1),
        )
    )
    db_session.commit()

    async def owner_scope(db, *, user_id):
        return EffectivePartyScope(
            user_id=user_id,
            source="explicit",
            scope_mode="owner",
            owner_party_ids=[f["owner"]],
        )

    monkeypatch.setattr(api.party_scope_resolver, "resolve", owner_scope)

    def completion_missing(document_type):
        body = client.get("/api/v1/archive/completion").json()
        body = body.get("data", body)
        return next(
            c for c in body["categories"] if c["document_type"] == document_type
        )["missing"]

    missing_before = completion_missing("upstream_contract")

    preview = client.post(
        "/api/v1/archive/batch-matches/preview",
        files=[
            (
                "files",
                (
                    "【五羊司合字[2024]214号】广州市直管房租赁合同.png",
                    _image("red"),
                    "image/png",
                ),
            ),
            ("files", ("无编号扫描件.png", _image("blue"), "image/png")),
        ],
        headers=csrf_headers,
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    body = body.get("data", body)
    assert body["expires_at"] is not None
    items = {item["file_name"]: item for item in body["items"]}
    detected = items["【五羊司合字[2024]214号】广州市直管房租赁合同.png"]
    assert detected["detected"]["target_type"] == "upstream_contract"
    assert detected["detected"]["target_id"] == upstream_id
    assert detected["already_archived"] is False
    assert items["无编号扫描件.png"]["detected"] is None

    token = body["preview_token"]
    unknown_target = client.post(
        "/api/v1/archive/batch-matches",
        json={
            "preview_token": token,
            "matches": [
                {
                    "staging_id": detected["staging_id"],
                    "target_type": "upstream_contract",
                    "target_id": str(uuid4()),
                }
            ],
        },
        headers=csrf_headers,
    )
    assert unknown_target.status_code == 404, unknown_target.text

    committed = client.post(
        "/api/v1/archive/batch-matches",
        json={
            "preview_token": token,
            "matches": [
                {
                    "staging_id": detected["staging_id"],
                    "target_type": "upstream_contract",
                    "target_id": upstream_id,
                }
            ],
        },
        headers=csrf_headers,
    )
    assert committed.status_code == 201, committed.text
    committed_body = committed.json()
    committed_body = committed_body.get("data", committed_body)
    assert len(committed_body["items"]) == 1
    assert committed_body["items"][0]["document_version"] == 1

    listed = client.get(
        "/api/v1/archive/documents",
        params={
            "target_type": "upstream_contract",
            "target_id": upstream_id,
            "document_type": "upstream_contract",
        },
    )
    listed = listed.json().get("data", listed.json())
    assert [item["id"] for item in listed["items"]] == [
        committed_body["items"][0]["id"]
    ]

    replay = client.post(
        "/api/v1/archive/batch-matches",
        json={
            "preview_token": token,
            "matches": [
                {
                    "staging_id": detected["staging_id"],
                    "target_type": "upstream_contract",
                    "target_id": upstream_id,
                }
            ],
        },
        headers=csrf_headers,
    )
    assert replay.status_code == 404, replay.text

    # The contract fact pointer stays untouched; the matrix is repaired by the
    # archive chain alone.
    assert (
        db_session.scalar(
            select(UpstreamContract.scan_document_id).where(
                UpstreamContract.id == upstream_id
            )
        )
        == upstream_scan
    )
    assert completion_missing("upstream_contract") == missing_before - 1

    async def hidden(db, *, user_id):
        return EffectivePartyScope(
            user_id=user_id,
            source="explicit",
            scope_mode="owner",
            owner_party_ids=[str(uuid4())],
        )

    monkeypatch.setattr(api.party_scope_resolver, "resolve", hidden)
    outside = client.post(
        "/api/v1/archive/batch-matches/preview",
        files=[
            (
                "files",
                (
                    "【五羊司合字[2024]214号】广州市直管房租赁合同.png",
                    _image("green"),
                    "image/png",
                ),
            )
        ],
        headers=csrf_headers,
    )
    assert outside.status_code == 200, outside.text
    outside_body = outside.json()
    outside_body = outside_body.get("data", outside_body)
    # An out-of-scope preview never suggests contracts it cannot see.
    assert outside_body["items"][0]["detected"] is None
    assert outside_body["items"][0]["ambiguous"] == []
