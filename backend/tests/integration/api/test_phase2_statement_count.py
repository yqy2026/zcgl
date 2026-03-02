"""Phase 2.2 statement-count baseline tests (list/detail/export/statistics)."""

from dataclasses import dataclass
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.engine import Engine

from src.crud.asset import asset_crud
from src.models.asset import Asset
from src.models.party import Party, PartyType

pytestmark = pytest.mark.integration


@pytest.fixture
def authenticated_client(client: TestClient, test_data) -> TestClient:
    """Authenticate integration client with real cookie login."""
    admin_user = test_data["admin"]
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": admin_user.username, "password": "Admin123!@#"},
    )
    assert response.status_code == 200
    auth_token = response.cookies.get("auth_token")
    csrf_token = response.cookies.get("csrf_token")
    assert auth_token is not None
    client.cookies.set("auth_token", auth_token)
    if csrf_token is not None:
        client.cookies.set("csrf_token", csrf_token)
    return client


@dataclass
class SQLStatementCounter:
    """Count executed SQL statements for a code block."""

    engine: Engine
    count: int = 0

    def __post_init__(self) -> None:
        self._handler = None

    def __enter__(self) -> "SQLStatementCounter":
        def _before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ) -> None:
            normalized = statement.strip().upper()
            if normalized.startswith(
                ("BEGIN", "COMMIT", "ROLLBACK", "SAVEPOINT", "RELEASE SAVEPOINT")
            ):
                return
            self.count += 1

        self._handler = _before_cursor_execute
        event.listen(self.engine, "before_cursor_execute", self._handler)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self._handler is not None:
            event.remove(self.engine, "before_cursor_execute", self._handler)


def _seed_assets(
    db_session,
    *,
    organization_id: str,
    count: int,
    name_prefix: str,
) -> list[str]:
    party_stmt = select(Party).where(
        Party.party_type == PartyType.ORGANIZATION.value,
        Party.external_ref == organization_id,
    )
    party = db_session.execute(party_stmt).scalar_one_or_none()
    if party is None:
        party = Party(
            party_type=PartyType.ORGANIZATION.value,
            name=f"StatementCountOrg-{organization_id[:8]}",
            code=f"STMT-ORG-{organization_id[:8]}",
            external_ref=organization_id,
            status="active",
        )
        db_session.add(party)
        db_session.flush()

    created_ids: list[str] = []
    for idx in range(count):
        asset = Asset(
            property_name=f"{name_prefix}-{idx}",
            address=f"statement-count-address-{idx}",
            ownership_status="已确权",
            property_nature="商业",
            usage_status="在用",
            business_category="商服",
            owner_party_id=party.id,
            manager_party_id=party.id,
            data_status="正常",
        )
        db_session.add(asset)
        db_session.flush()
        created_ids.append(str(asset.id))
    db_session.commit()
    return created_ids


class TestPhase2StatementCount:
    """Phase 2.2 baseline: query count must remain stable as data grows."""

    def test_assets_list_statement_count_no_n_plus_one(
        self, authenticated_client: TestClient, db_session, test_data, engine: Engine
    ) -> None:
        org_id = str(test_data["organization"].id)
        suffix = uuid4().hex[:8]
        _seed_assets(
            db_session,
            organization_id=org_id,
            count=1,
            name_prefix=f"phase2-list-small-{suffix}",
        )
        asset_crud.clear_cache()

        with SQLStatementCounter(engine) as small_counter:
            small_resp = authenticated_client.get(
                f"/api/v1/assets?page=1&page_size=100&include_relations=true&search=phase2-list-small-{suffix}"
            )
        assert small_resp.status_code == 200

        _seed_assets(
            db_session,
            organization_id=org_id,
            count=40,
            name_prefix=f"phase2-list-large-{suffix}",
        )
        asset_crud.clear_cache()
        with SQLStatementCounter(engine) as large_counter:
            large_resp = authenticated_client.get(
                "/api/v1/assets?page=1&page_size=100&include_relations=true"
            )
        assert large_resp.status_code == 200
        assert large_counter.count <= small_counter.count + 2

    def test_asset_detail_statement_count_budget(
        self, authenticated_client: TestClient, db_session, test_data, engine: Engine
    ) -> None:
        org_id = str(test_data["organization"].id)
        suffix = uuid4().hex[:8]
        created_ids = _seed_assets(
            db_session,
            organization_id=org_id,
            count=1,
            name_prefix=f"phase2-detail-{suffix}",
        )
        asset_crud.clear_cache()

        with SQLStatementCounter(engine) as counter:
            response = authenticated_client.get(f"/api/v1/assets/{created_ids[0]}")
        assert response.status_code == 200
        assert counter.count <= 12

    def test_assets_export_statement_count_no_n_plus_one(
        self, authenticated_client: TestClient, db_session, test_data, engine: Engine
    ) -> None:
        org_id = str(test_data["organization"].id)
        suffix = uuid4().hex[:8]
        _seed_assets(
            db_session,
            organization_id=org_id,
            count=1,
            name_prefix=f"phase2-export-small-{suffix}",
        )
        asset_crud.clear_cache()

        with SQLStatementCounter(engine) as small_counter:
            small_resp = authenticated_client.get(
                f"/api/v1/assets/all?max_export=500&include_relations=false&search=phase2-export-small-{suffix}"
            )
        assert small_resp.status_code == 200

        _seed_assets(
            db_session,
            organization_id=org_id,
            count=60,
            name_prefix=f"phase2-export-large-{suffix}",
        )
        asset_crud.clear_cache()
        with SQLStatementCounter(engine) as large_counter:
            large_resp = authenticated_client.get(
                "/api/v1/assets/all?max_export=500&include_relations=false"
            )
        assert large_resp.status_code == 200
        assert large_counter.count <= small_counter.count + 2

    def test_analytics_statistics_statement_count_no_n_plus_one(
        self, authenticated_client: TestClient, db_session, test_data, engine: Engine
    ) -> None:
        org_id = str(test_data["organization"].id)
        suffix = uuid4().hex[:8]
        _seed_assets(
            db_session,
            organization_id=org_id,
            count=2,
            name_prefix=f"phase2-stats-small-{suffix}",
        )
        asset_crud.clear_cache()

        with SQLStatementCounter(engine) as small_counter:
            small_resp = authenticated_client.get(
                "/api/v1/analytics/comprehensive?should_include_deleted=false&should_use_cache=false"
            )
        assert small_resp.status_code == 200

        _seed_assets(
            db_session,
            organization_id=org_id,
            count=50,
            name_prefix=f"phase2-stats-large-{suffix}",
        )
        asset_crud.clear_cache()
        with SQLStatementCounter(engine) as large_counter:
            large_resp = authenticated_client.get(
                "/api/v1/analytics/comprehensive?should_include_deleted=false&should_use_cache=false"
            )
        assert large_resp.status_code == 200
        assert large_counter.count <= small_counter.count + 4
