"""Party API behavior tests."""

from fastapi import status


def test_list_parties_should_filter_by_search_query(client, db_session) -> None:
    """`/parties` 应根据 search 过滤名称/编码匹配结果。"""
    from src.models.party import Party, PartyType

    matching_party = Party(
        party_type=PartyType.ORGANIZATION,
        name="Acme Holdings",
        code="ACME-001",
        status="active",
    )
    other_party = Party(
        party_type=PartyType.ORGANIZATION,
        name="Beta Group",
        code="BETA-001",
        status="active",
    )
    db_session.add_all([matching_party, other_party])
    db_session.flush()

    response = client.get("/api/v1/parties?search=acme")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["name"] == "Acme Holdings"
    assert payload[0]["code"] == "ACME-001"


def test_list_parties_should_filter_by_search_code(client, db_session) -> None:
    """`/parties` 应支持按编码模糊搜索。"""
    from src.models.party import Party, PartyType

    matching_party = Party(
        party_type=PartyType.ORGANIZATION,
        name="Code Match Party",
        code="ACME-001",
        status="active",
    )
    other_party = Party(
        party_type=PartyType.ORGANIZATION,
        name="Other Party",
        code="BETA-001",
        status="active",
    )
    db_session.add_all([matching_party, other_party])
    db_session.flush()

    response = client.get("/api/v1/parties?search=ACME-001")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["name"] == "Code Match Party"
    assert payload[0]["code"] == "ACME-001"
