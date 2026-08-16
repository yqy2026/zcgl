"""
Shared E2E test data factories.
"""

from src.models.ownership import Ownership


def _create_ownership(
    db_session,
    *,
    suffix: str,
    name_prefix: str,
    code_prefix: str,
    short_prefix: str,
) -> Ownership:
    ownership = Ownership(
        name=f"{name_prefix}-{suffix}",
        code=f"{code_prefix}-{suffix}",
        short_name=f"{short_prefix}{suffix[:4]}",
        data_status="正常",
    )
    db_session.add(ownership)
    db_session.commit()
    db_session.refresh(ownership)
    return ownership


def create_asset_ownership(db_session, suffix: str) -> Ownership:
    return _create_ownership(
        db_session,
        suffix=suffix,
        name_prefix="E2E权属方",
        code_prefix="E2E-OWN",
        short_prefix="E2E",
    )


def create_asset_payload(
    *,
    suffix: str,
    ownership_id: str,
    usage_status: str = "出租",
    name_prefix: str = "E2E资产",
    address_prefix: str = "E2E地址",
    business_prefix: str = "E2E业态",
    created_by: str = "e2e_test",
) -> dict[str, object]:
    return {
        "ownership_id": ownership_id,
        "asset_name": f"{name_prefix}-{suffix}",
        "address_detail": f"{address_prefix}-{suffix}",
        "ownership_status": "已确权",
        "property_nature": "经营类",
        "usage_status": usage_status,
        "business_category": f"{business_prefix}-{suffix}",
        "data_status": "正常",
        "created_by": created_by,
    }


def create_approved_legal_party(
    db_session,
    *,
    suffix: str,
    name: str,
    review_status: str = "approved",
) -> object:
    """Create an approved (or arbitrary review status) legal-entity Party row directly."""
    from uuid import uuid4

    from src.models.party import Party, PartyType

    party = Party(
        party_type=PartyType.LEGAL_ENTITY,
        name=name,
        code=f"LE-{uuid4().int % 1_000_000:06d}",
        status="active",
        review_status=review_status,
    )
    db_session.add(party)
    db_session.flush()
    db_session.commit()
    db_session.refresh(party)
    return party


def create_scoped_asset_via_api(
    authenticated_client,
    db_session,
    *,
    suffix: str,
    holder_party_id: str,
    csrf_headers: dict[str, str],
    usage_status: str = "出租",
) -> dict[str, object]:
    """Create an asset through the real API wired to the owner/manager party scope."""
    ownership = create_asset_ownership(db_session, suffix)
    payload = create_asset_payload(
        suffix=suffix,
        ownership_id=ownership.id,
        usage_status=usage_status,
    )
    payload["owner_party_id"] = holder_party_id
    payload["manager_party_id"] = holder_party_id
    response = authenticated_client.post(
        "/api/v1/assets",
        json=payload,
        headers=csrf_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()
