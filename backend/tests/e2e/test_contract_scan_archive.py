"""Contract scan archives are scoped, versioned, and repair the matrix."""

from datetime import date
from decimal import Decimal
from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy import select

from src.api.v1 import archive_documents as api
from src.models.asset_contract import UpstreamContract, UpstreamContractAssetUnit
from src.models.attachment import Attachment
from src.services.party_scope_resolver import EffectivePartyScope
from src.services.property_certificate.attachment_service import (
    property_certificate_attachment_service,
)
from tests.e2e.test_asset_unit_certificates import (
    certificate_facts as _certificate_facts,
)

certificate_facts = _certificate_facts

pytestmark = pytest.mark.e2e


def _image(color):
    out = BytesIO()
    Image.new("RGB", (2, 2), color).save(out, format="PNG")
    return out.getvalue()


def _completion(client, document_type):
    body = client.get("/api/v1/archive/completion").json()
    body = body.get("data", body)
    return next(c for c in body["categories"] if c["document_type"] == document_type)


def test_contract_scan_upload_replace_and_matrix_repair(
    authenticated_client,
    csrf_headers,
    certificate_facts,
    db_session,
    monkeypatch,
    tmp_path,
):
    f = certificate_facts
    cid = str(uuid4())
    # The real gap: every contract has a scan reference, but the referenced file
    # may not be owned by the contract itself (e.g. an intake-staged upload that
    # was never rebound), which the matrix counts as missing.
    staged_file = str(uuid4())
    db_session.add(
        Attachment(
            id=staged_file,
            owner_type="contract",
            owner_id="intake-session-" + cid,
            file_name="staged.pdf",
            file_type="pdf",
            file_size=1,
            storage_key="intake/" + staged_file,
            created_by=str(uuid4()),
        )
    )
    db_session.flush()
    db_session.add(
        UpstreamContract(
            id=cid,
            contract_number="SCAN-" + cid,
            contract_type="lease",
            name="扫描件维护测试",
            owner_party_id=f["owner"],
            operator_party_id=f["manager"],
            start_date=date(2020, 1, 1),
            end_date=date(2030, 1, 1),
            payment_cycle="monthly",
            scan_document_id=staged_file,
        )
    )
    db_session.flush()
    db_session.add(
        UpstreamContractAssetUnit(
            upstream_contract_id=cid,
            asset_unit_id=f["visible_unit"],
            effective_from=date(2020, 1, 1),
        )
    )
    db_session.commit()

    async def visible(db, *, user_id):
        return EffectivePartyScope(
            user_id=user_id,
            source="explicit",
            scope_mode="owner",
            owner_party_ids=[f["owner"]],
        )

    monkeypatch.setattr(api.party_scope_resolver, "resolve", visible)
    monkeypatch.setattr(
        property_certificate_attachment_service, "uploads_root", tmp_path
    )
    before = _completion(authenticated_client, "upstream_contract")
    assert before["required"] >= 1
    assert before["missing"] >= 1

    data = {
        "target_type": "upstream_contract",
        "target_id": cid,
        "document_type": "upstream_contract",
    }
    first = authenticated_client.post(
        "/api/v1/archive/documents",
        data=data,
        files={"file": ("scan.png", _image("red"), "image/png")},
        headers=csrf_headers,
    )
    assert first.status_code == 201, first.text
    first = first.json()
    first = first.get("data", first)
    assert first["target_type"] == "upstream_contract"
    assert first["document_version"] == 1

    after = _completion(authenticated_client, "upstream_contract")
    assert after["missing"] == before["missing"] - 1
    assert after["existing"] == before["existing"] + 1

    duplicate = authenticated_client.post(
        "/api/v1/archive/documents",
        data=data,
        files={"file": ("scan.png", _image("red"), "image/png")},
        headers=csrf_headers,
    )
    assert duplicate.status_code == 409, duplicate.text

    listed = authenticated_client.get("/api/v1/archive/documents", params=data)
    assert listed.status_code == 200, listed.text
    listed = listed.json()
    listed = listed.get("data", listed)
    assert [item["id"] for item in listed["items"]] == [first["id"]]

    replacement = authenticated_client.post(
        f"/api/v1/archive/documents/{first['id']}/replacement",
        files={"file": ("new.png", _image("blue"), "image/png")},
        headers=csrf_headers,
    )
    assert replacement.status_code == 201, replacement.text
    replacement = replacement.json()
    replacement = replacement.get("data", replacement)
    assert replacement["document_version"] == 2
    assert replacement["replaces_document_id"] == first["id"]

    stale = authenticated_client.post(
        f"/api/v1/archive/documents/{first['id']}/replacement",
        files={"file": ("new.png", _image("green"), "image/png")},
        headers=csrf_headers,
    )
    assert stale.status_code == 409, stale.text

    history = authenticated_client.get(
        f"/api/v1/archive/documents/{first['id']}/content"
    )
    assert history.status_code == 200, history.text
    assert history.content == _image("red")
    current = authenticated_client.get(
        f"/api/v1/archive/documents/{replacement['id']}/content"
    )
    assert current.content == _image("blue")

    # The archive chain repairs the matrix without rewriting the contract fact.
    assert (
        db_session.scalar(
            select(UpstreamContract.scan_document_id).where(UpstreamContract.id == cid)
        )
        == staged_file
    )
    final = _completion(authenticated_client, "upstream_contract")
    assert final["missing"] == before["missing"] - 1

    terminal_file = str(uuid4())
    terminal_id = str(uuid4())
    db_session.add(
        Attachment(
            id=terminal_file,
            owner_type="contract",
            owner_id="intake-session-" + terminal_id,
            file_name="terminal.pdf",
            file_type="pdf",
            file_size=1,
            storage_key="intake/" + terminal_file,
            created_by=str(uuid4()),
        )
    )
    db_session.flush()
    db_session.add(
        UpstreamContract(
            id=terminal_id,
            contract_number="SCAN-T-" + terminal_id,
            contract_type="management_agreement",
            name="终端目标占位",
            owner_party_id=f["owner"],
            operator_party_id=f["manager"],
            start_date=date(2020, 1, 1),
            end_date=date(2030, 1, 1),
            payment_cycle=None,
            management_fee_rate=Decimal("0.05"),
            scan_document_id=terminal_file,
        )
    )
    db_session.commit()
    wrong_pair = authenticated_client.post(
        "/api/v1/archive/documents",
        data={
            "target_type": "terminal_contract",
            "target_id": terminal_id,
            "document_type": "upstream_contract",
        },
        files={"file": ("x.png", _image("yellow"), "image/png")},
        headers=csrf_headers,
    )
    assert wrong_pair.status_code == 422, wrong_pair.text

    count = len(list(tmp_path.rglob("*")))

    async def hidden(db, *, user_id):
        return EffectivePartyScope(
            user_id=user_id,
            source="explicit",
            scope_mode="owner",
            owner_party_ids=[str(uuid4())],
        )

    monkeypatch.setattr(api.party_scope_resolver, "resolve", hidden)
    assert (
        authenticated_client.post(
            "/api/v1/archive/documents",
            data=data,
            files={"file": ("x.png", _image("green"), "image/png")},
            headers=csrf_headers,
        ).status_code
        == 404
    )
    assert (
        authenticated_client.get("/api/v1/archive/documents", params=data).status_code
        == 404
    )
    assert (
        authenticated_client.get(
            f"/api/v1/archive/documents/{replacement['id']}/content"
        ).status_code
        == 404
    )
    assert (
        authenticated_client.post(
            f"/api/v1/archive/documents/{replacement['id']}/replacement",
            files={"file": ("x.png", _image("green"), "image/png")},
            headers=csrf_headers,
        ).status_code
        == 404
    )
    assert len(list(tmp_path.rglob("*"))) == count
