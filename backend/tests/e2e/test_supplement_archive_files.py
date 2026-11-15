from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy import select

from src.models.asset_contract import UpstreamContract
from src.services.property_certificate.attachment_service import (
    property_certificate_attachment_service,
)
from tests.e2e.test_contract_supplements import certificate_facts as _certificate_facts
from tests.e2e.test_contract_supplements import (
    test_register_duplicate_withdraw_and_matrix as setup_parent,
)

certificate_facts = _certificate_facts

pytestmark = pytest.mark.e2e


def test_supplement_files(
    authenticated_client,
    csrf_headers,
    certificate_facts,
    db_session,
    monkeypatch,
    tmp_path,
):
    setup_parent(
        authenticated_client, csrf_headers, certificate_facts, db_session, monkeypatch
    )
    from src.api.v1 import archive_documents as api
    from src.services.party_scope_resolver import EffectivePartyScope

    async def visible(db, *, user_id):
        return EffectivePartyScope(
            user_id=user_id,
            source="explicit",
            scope_mode="owner",
            owner_party_ids=[certificate_facts["owner"]],
        )

    monkeypatch.setattr(api.party_scope_resolver, "resolve", visible)
    parent = db_session.scalar(
        select(UpstreamContract).where(UpstreamContract.name == "补充协议测试")
    )
    response = authenticated_client.post(
        "/api/v1/contract-supplements",
        json={
            "contract_kind": "upstream",
            "contract_id": parent.id,
            "agreement_number": str(uuid4()),
            "title": "文件测试",
        },
        headers=csrf_headers,
    )
    assert response.status_code == 201, response.text
    item = response.json()
    item = item.get("data", item)
    monkeypatch.setattr(
        property_certificate_attachment_service, "uploads_root", tmp_path
    )

    def image(color):
        out = BytesIO()
        Image.new("RGB", (2, 2), color).save(out, format="PNG")
        return out.getvalue()

    data = {
        "target_type": "contract_supplement",
        "target_id": item["id"],
        "document_type": "supplement",
    }

    def upload(content):
        return authenticated_client.post(
            "/api/v1/archive/documents",
            data=data,
            files={"file": ("scan.png", content, "image/png")},
            headers=csrf_headers,
        )

    first = upload(image("red"))
    assert first.status_code == 201, first.text
    first = first.json()
    first = first.get("data", first)
    assert first["target_type"] == "contract_supplement"
    assert upload(image("red")).status_code == 409
    url = "/api/v1/archive/documents/" + first["id"] + "/replacement"
    new = authenticated_client.post(
        url,
        files={"file": ("new.png", image("blue"), "image/png")},
        headers=csrf_headers,
    )
    assert new.status_code == 201, new.text
    assert (
        authenticated_client.post(
            url,
            files={"file": ("new.png", image("green"), "image/png")},
            headers=csrf_headers,
        ).status_code
        == 409
    )
    old = authenticated_client.get(
        "/api/v1/archive/documents/" + first["id"] + "/content"
    )
    assert old.status_code == 200, old.text
    assert old.content == image("red")
    withdrawn = authenticated_client.post(
        "/api/v1/contract-supplements/" + item["id"] + "/withdrawal",
        json={"expected_version": item["version"], "reason": "撤回"},
        headers=csrf_headers,
    )
    assert withdrawn.status_code == 200, withdrawn.text
    assert upload(image("green")).status_code == 409
    assert (
        authenticated_client.get(
            "/api/v1/archive/documents/" + first["id"] + "/content"
        ).status_code
        == 200
    )
    second = authenticated_client.post(
        "/api/v1/contract-supplements",
        json={
            "contract_kind": "upstream",
            "contract_id": parent.id,
            "agreement_number": str(uuid4()),
            "title": "independent",
        },
        headers=csrf_headers,
    ).json()
    second = second.get("data", second)
    data["target_id"] = second["id"]
    independent = upload(image("red"))
    assert independent.status_code == 201, independent.text
    independent = independent.json()
    independent = independent.get("data", independent)
    assert independent["document_version"] == 1
    count = len(list(tmp_path.rglob("*")))

    async def hidden(db, *, user_id):
        return EffectivePartyScope(
            user_id=user_id,
            source="explicit",
            scope_mode="owner",
            owner_party_ids=[str(uuid4())],
        )

    monkeypatch.setattr(api.party_scope_resolver, "resolve", hidden)
    assert upload(image("green")).status_code == 404
    assert (
        authenticated_client.get(
            "/api/v1/archive/documents/" + first["id"] + "/content"
        ).status_code
        == 404
    )
    assert (
        authenticated_client.get("/api/v1/archive/documents", params=data).status_code
        == 404
    )
    assert (
        authenticated_client.post(
            "/api/v1/archive/documents/" + independent["id"] + "/replacement",
            files={"file": ("x.png", image("green"), "image/png")},
            headers=csrf_headers,
        ).status_code
        == 404
    )
    assert len(list(tmp_path.rglob("*"))) == count
