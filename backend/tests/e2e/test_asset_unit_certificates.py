"""Read v5 certificate links through real PostgreSQL and authenticated HTTP."""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.v1 import asset_units as api
from src.models.asset_unit import AssetUnit, PropertyCertificateAssetUnit
from src.models.project import Project
from src.models.property_certificate import PropertyCertificate
from src.services.party_scope_resolver import EffectivePartyScope
from tests.e2e.factories import create_approved_legal_party

pytestmark = pytest.mark.e2e


@pytest.fixture(autouse=True)
def business_clock(monkeypatch):
    monkeypatch.setattr(
        api.asset_unit_certificate_service,
        "clock",
        lambda: datetime(2026, 11, 2, 12, tzinfo=UTC),
    )


@pytest.fixture
def certificate_facts(db_session: Session) -> dict[str, str]:
    suffix = uuid4().hex[:12]
    owner = create_approved_legal_party(db_session, suffix=suffix, name="证照产权方")
    manager = create_approved_legal_party(
        db_session, suffix=f"m{suffix}", name="证照运营方"
    )
    other = create_approved_legal_party(
        db_session, suffix=f"o{suffix}", name="范围外产权方"
    )
    project = Project(
        id=str(uuid4()),
        project_code=f"PRJ-CERT-{suffix}",
        project_name="证照读取项目",
        manager_party_id=manager.id,
        status="active",
    )
    db_session.add(project)
    db_session.flush()
    units = []
    for index, party in enumerate((owner, other, owner)):
        unit = AssetUnit(
            id=str(uuid4()),
            unit_code=f"CERT-{suffix}-{index}",
            name=f"证照单元{index}",
            project_id=project.id,
            owner_party_id=party.id,
            address="证照测试地址",
            usage_type="commercial",
            acquisition_mode="owned",
            land_area=Decimal("10"),
            building_area=Decimal("20"),
            rentable_area=Decimal("15"),
            managed_from=date(2020, 1, 1),
        )
        db_session.add(unit)
        units.append(unit)
    certificates = []
    for index in range(3):
        certificate = PropertyCertificate(
            id=str(uuid4()),
            certificate_number=f"CERT-NO-{suffix}-{index}",
            certificate_type="real_estate",
            property_address="证载地址",
            building_area="共用面积详见附图",
            land_area="00120.00",
        )
        db_session.add(certificate)
        certificates.append(certificate)
    db_session.flush()
    # Deliberately no old Asset associations or CertificatePartyRelation rows.
    for certificate, start, end in (
        (certificates[0], date(2026, 11, 1), date(2026, 11, 30)),
        (certificates[1], date(2026, 12, 1), None),
        (certificates[2], date(2026, 1, 1), date(2026, 10, 31)),
    ):
        db_session.add(
            PropertyCertificateAssetUnit(
                certificate_id=certificate.id,
                asset_unit_id=units[0].id,
                effective_from=start,
                effective_to=end,
            )
        )
    db_session.add(
        PropertyCertificateAssetUnit(
            certificate_id=certificates[0].id,
            asset_unit_id=units[1].id,
            effective_from=date(2026, 1, 1),
        )
    )
    db_session.add(
        PropertyCertificateAssetUnit(
            certificate_id=certificates[2].id,
            asset_unit_id=units[2].id,
            effective_from=date(2026, 1, 1),
        )
    )
    db_session.commit()
    return {
        "owner": owner.id,
        "manager": manager.id,
        "other": other.id,
        "unit": units[0].id,
        "hidden_unit": units[1].id,
        "visible_unit": units[2].id,
        "current": certificates[0].id,
        "future": certificates[1].id,
        "past": certificates[2].id,
    }


def _scope(monkeypatch, facts, mode):
    scope = EffectivePartyScope(
        user_id="certificate-reader",
        source="unrestricted" if mode == "unrestricted" else "explicit",
        scope_mode=mode,
        owner_party_ids=[facts["owner"]] if mode == "owner" else [],
        manager_party_ids=[facts["manager"]] if mode == "manager" else [],
    )
    monkeypatch.setattr(
        api.party_scope_resolver, "resolve", AsyncMock(return_value=scope)
    )


@pytest.mark.parametrize(
    ("as_of", "keys"),
    [
        ("2026-10-31", ["past"]),
        ("2026-11-01", ["current"]),
        ("2026-11-30", ["current"]),
        ("2026-12-01", ["future"]),
    ],
)
def test_relation_dates_are_inclusive_and_do_not_use_old_asset_links(
    authenticated_client: TestClient,
    certificate_facts: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    as_of: str,
    keys: list[str],
) -> None:
    facts = certificate_facts
    _scope(monkeypatch, facts, "owner")
    response = authenticated_client.get(
        f"/api/v1/asset-units/{facts['unit']}/property-certificates?as_of={as_of}"
    )
    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["items"]] == [facts[k] for k in keys]
    assert facts["hidden_unit"] not in response.text
    assert facts["other"] not in response.text
    assert "party_relations" not in response.text
    assert "assets" not in response.text


@pytest.mark.parametrize("mode", ["owner", "manager", "unrestricted"])
def test_shared_certificate_is_returned_once_under_each_current_scope(
    authenticated_client: TestClient,
    certificate_facts: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    facts = certificate_facts
    _scope(monkeypatch, facts, mode)
    response = authenticated_client.get(
        f"/api/v1/asset-units/{facts['unit']}/property-certificates?as_of=2026-11-15"
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == facts["current"]
    assert items[0]["building_area"] == "共用面积详见附图"
    assert items[0]["land_area"] == "00120.00"


def test_historical_date_cannot_bypass_current_scope(
    authenticated_client: TestClient,
    certificate_facts: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facts = certificate_facts
    _scope(monkeypatch, facts, "owner")
    for unit_id in (facts["hidden_unit"], str(uuid4())):
        response = authenticated_client.get(
            f"/api/v1/asset-units/{unit_id}/property-certificates?as_of=2026-01-01"
        )
        assert response.status_code == 404, response.text
        assert facts["current"] not in response.text


def test_missing_scope_is_forbidden_before_reading_certificate_facts(
    authenticated_client: TestClient,
    certificate_facts: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _scope(monkeypatch, certificate_facts, "owner")
    monkeypatch.setattr(
        api.party_scope_resolver,
        "resolve",
        AsyncMock(
            return_value=EffectivePartyScope(
                user_id="certificate-reader", source="none", scope_mode="none"
            )
        ),
    )
    response = authenticated_client.get(
        f"/api/v1/asset-units/{certificate_facts['unit']}/property-certificates"
    )
    assert response.status_code == 403, response.text


def test_reopening_ended_pair_preserves_historical_query(
    authenticated_client,
    csrf_headers,
    certificate_facts,
    monkeypatch,
):
    facts = certificate_facts
    _scope(monkeypatch, facts, "owner")
    response = authenticated_client.post(
        f"/api/v1/asset-units/{facts['unit']}/property-certificates",
        json={"certificate_id": facts["past"], "effective_from": "2027-01-01"},
        headers=csrf_headers,
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "CERTIFICATE_LINK_HISTORY_PROTECTED"
    historical = authenticated_client.get(
        f"/api/v1/asset-units/{facts['unit']}/property-certificates?as_of=2026-06-01"
    )
    assert [item["id"] for item in historical.json()["items"]] == [facts["past"]]


def test_unlink_closes_range_through_the_day_before(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    certificate_facts: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    facts = certificate_facts
    _scope(monkeypatch, facts, "owner")
    response = authenticated_client.post(
        f"/api/v1/asset-units/{facts['unit']}/property-certificates/"
        f"{facts['current']}/unlink",
        json={"effective_from": "2026-11-16"},
        headers=csrf_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"] == []
    visible = authenticated_client.get(
        f"/api/v1/asset-units/{facts['unit']}/property-certificates?as_of=2026-11-15"
    )
    assert [item["id"] for item in visible.json()["items"]] == [facts["current"]]
    closed = authenticated_client.get(
        f"/api/v1/asset-units/{facts['unit']}/property-certificates?as_of=2026-11-16"
    )
    assert closed.json()["items"] == []
    link = (
        db_session.query(PropertyCertificateAssetUnit)
        .filter_by(asset_unit_id=facts["unit"], certificate_id=facts["current"])
        .one()
    )
    assert link.effective_to == date(2026, 11, 15)


def test_unlink_not_yet_started_interval_removes_the_row(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    certificate_facts: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
) -> None:
    facts = certificate_facts
    _scope(monkeypatch, facts, "owner")
    response = authenticated_client.post(
        f"/api/v1/asset-units/{facts['unit']}/property-certificates/"
        f"{facts['future']}/unlink",
        json={"effective_from": "2026-12-01"},
        headers=csrf_headers,
    )
    assert response.status_code == 200, response.text
    remaining = (
        db_session.query(PropertyCertificateAssetUnit)
        .filter_by(asset_unit_id=facts["unit"], certificate_id=facts["future"])
        .count()
    )
    assert remaining == 0


def test_link_rejects_invisible_unit_and_unknown_certificate(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    certificate_facts: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facts = certificate_facts
    _scope(monkeypatch, facts, "owner")
    hidden = authenticated_client.post(
        f"/api/v1/asset-units/{facts['hidden_unit']}/property-certificates",
        json={
            "certificate_id": facts["past"],
            "effective_from": "2027-01-01",
        },
        headers=csrf_headers,
    )
    assert hidden.status_code == 404, hidden.text
    unknown = authenticated_client.post(
        f"/api/v1/asset-units/{facts['unit']}/property-certificates",
        json={
            "certificate_id": str(uuid4()),
            "effective_from": "2027-01-01",
        },
        headers=csrf_headers,
    )
    assert unknown.status_code == 404, unknown.text


def test_link_without_scope_is_forbidden(
    authenticated_client: TestClient,
    csrf_headers: dict[str, str],
    certificate_facts: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        api.party_scope_resolver,
        "resolve",
        AsyncMock(
            return_value=EffectivePartyScope(
                user_id="certificate-reader", source="none", scope_mode="none"
            )
        ),
    )
    response = authenticated_client.post(
        f"/api/v1/asset-units/{certificate_facts['unit']}/property-certificates",
        json={
            "certificate_id": certificate_facts["past"],
            "effective_from": "2027-01-01",
        },
        headers=csrf_headers,
    )
    assert response.status_code == 403, response.text


def test_bind_only_currently_visible_certificate_target(
    authenticated_client, csrf_headers, certificate_facts, monkeypatch
):
    facts = certificate_facts
    _scope(monkeypatch, facts, "owner")
    response = authenticated_client.post(
        f"/api/v1/asset-units/{facts['visible_unit']}/property-certificates",
        json={"certificate_id": facts["current"], "effective_from": "2027-01-01"},
        headers=csrf_headers,
    )
    assert response.status_code == 201, response.text
    assert facts["current"] in [item["id"] for item in response.json()["items"]]
    denied = authenticated_client.post(
        f"/api/v1/asset-units/{facts['visible_unit']}/property-certificates",
        json={"certificate_id": facts["future"], "effective_from": "2027-01-01"},
        headers=csrf_headers,
    )
    assert denied.status_code == 404, denied.text


@pytest.mark.parametrize(
    "role,window,party,mode,allowed",
    [
        ("owner", "current", "owner", "owner", True),
        ("co_owner", "current", "owner", "owner", True),
        ("owner", "current", "owner", "manager", True),
        ("owner", "today", "owner", "owner", True),
        ("owner", "boundary", "owner", "owner", True),
        ("issuer", "current", "owner", "owner", False),
        ("custodian", "current", "owner", "owner", False),
        ("owner", "expired", "owner", "owner", False),
        ("owner", "future", "owner", "owner", False),
        ("owner", "current", "other", "owner", False),
    ],
)
def test_unseen_certificate_qualifies_only_by_current_holder(
    authenticated_client,
    csrf_headers,
    certificate_facts,
    monkeypatch,
    db_session,
    role,
    window,
    party,
    mode,
    allowed,
):
    from src.models.certificate_party_relation import (
        CertificatePartyRelation,
        CertificateRelationRole,
    )

    facts = certificate_facts
    _scope(monkeypatch, facts, mode)
    certificate_id = str(uuid4())
    db_session.add(
        PropertyCertificate(
            id=certificate_id,
            certificate_number=f"HOLDER-{uuid4().hex}",
            certificate_type="real_estate",
        )
    )
    db_session.flush()
    start = datetime(2020, 1, 1)
    end = None
    if window == "today":
        start = datetime(2026, 11, 2, 10)
    if window == "boundary":
        start, end = datetime(2026, 11, 2, 12), datetime(2026, 11, 2, 12)
    if window == "expired":
        end = datetime(2026, 11, 2, 11, 59, 59)
    if window == "future":
        start = datetime(2026, 11, 2, 12, 0, 1)
    db_session.add(
        CertificatePartyRelation(
            certificate_id=certificate_id,
            party_id=facts[party],
            relation_role=CertificateRelationRole(role),
            valid_from=start,
            valid_to=end,
        )
    )
    db_session.commit()
    options = authenticated_client.get(
        f"/api/v1/asset-units/{facts['unit']}/property-certificate-options"
    )
    assert options.status_code == 200, options.text
    assert (
        certificate_id in [item["id"] for item in options.json()["items"]]
    ) is allowed
    response = authenticated_client.post(
        f"/api/v1/asset-units/{facts['unit']}/property-certificates",
        json={"certificate_id": certificate_id, "effective_from": "2027-01-01"},
        headers=csrf_headers,
    )
    assert response.status_code == (201 if allowed else 404), response.text
    assert db_session.query(PropertyCertificateAssetUnit).filter_by(
        certificate_id=certificate_id
    ).count() == int(allowed)


def test_ended_visible_link_makes_certificate_known(
    authenticated_client, csrf_headers, certificate_facts, monkeypatch, db_session
):
    facts = certificate_facts
    _scope(monkeypatch, facts, "owner")
    certificate_id = str(uuid4())
    db_session.add(
        PropertyCertificate(
            id=certificate_id,
            certificate_number=f"KNOWN-{uuid4().hex}",
            certificate_type="real_estate",
        )
    )
    db_session.flush()
    db_session.add(
        PropertyCertificateAssetUnit(
            certificate_id=certificate_id,
            asset_unit_id=facts["visible_unit"],
            effective_from=date(2020, 1, 1),
            effective_to=date(2021, 1, 1),
        )
    )
    db_session.commit()
    response = authenticated_client.post(
        f"/api/v1/asset-units/{facts['unit']}/property-certificates",
        json={"certificate_id": certificate_id, "effective_from": "2027-01-01"},
        headers=csrf_headers,
    )
    assert response.status_code == 201, response.text


def test_options_filter_before_pagination_and_recheck_holder_on_commit(
    authenticated_client, csrf_headers, certificate_facts, monkeypatch, db_session
):
    from src.models.certificate_party_relation import (
        CertificatePartyRelation,
        CertificateRelationRole,
    )

    facts = certificate_facts
    _scope(monkeypatch, facts, "owner")
    prefix = f"OPTIONS-{uuid4().hex}"
    certificates = []
    for label, party in [("A", "owner"), ("B", "owner"), ("C", "other")]:
        certificate = PropertyCertificate(
            id=str(uuid4()),
            certificate_number=f"{prefix}-{label}",
            certificate_type="real_estate",
            property_address="可搜索地址",
        )
        db_session.add(certificate)
        db_session.flush()
        db_session.add(
            CertificatePartyRelation(
                certificate_id=certificate.id,
                party_id=facts[party],
                relation_role=CertificateRelationRole.OWNER,
                valid_from=datetime(2020, 1, 1),
            )
        )
        certificates.append(certificate.id)
    db_session.commit()
    path = f"/api/v1/asset-units/{facts['unit']}/property-certificate-options"
    response = authenticated_client.get(
        path, params={"q": prefix, "offset": 1, "limit": 1}
    )
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 2
    assert [item["id"] for item in response.json()["items"]] == [certificates[1]]
    assert authenticated_client.get(path, params={"q": prefix, "offset": 2}).json() == {
        "items": [],
        "total": 2,
    }
    db_session.query(CertificatePartyRelation).filter_by(
        certificate_id=certificates[1]
    ).update({"valid_to": datetime(2026, 11, 2, 11)})
    db_session.commit()
    submitted = authenticated_client.post(
        f"/api/v1/asset-units/{facts['unit']}/property-certificates",
        json={"certificate_id": certificates[1], "effective_from": "2027-01-01"},
        headers=csrf_headers,
    )
    assert submitted.status_code == 404, submitted.text
    assert (
        db_session.query(PropertyCertificateAssetUnit)
        .filter_by(certificate_id=certificates[1])
        .count()
        == 0
    )
