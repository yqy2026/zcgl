"""Tests for phase2 party-migration scripts."""

from __future__ import annotations

import sqlalchemy as sa

from src.scripts.migration.party_migration.backfill_business_tables import (
    LEGACY_CONTRACTS_TABLE,
    _apply_mapping_updates,
    _backfill_role_scope,
    _build_operations,
)
from src.scripts.migration.party_migration.backfill_role_policies import (
    _choose_policy_package,
)
from src.scripts.migration.party_migration.generate_mapping import (
    build_mapping_artifact,
)
from src.scripts.migration.party_migration.reconciliation import (
    _check_role_party_scope_integrity,
)


def _create_connection() -> sa.engine.Connection:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    connection = engine.connect()
    connection.info["_test_engine"] = engine
    return connection


def _close_connection(connection: sa.engine.Connection) -> None:
    engine = connection.info.pop("_test_engine")
    connection.close()
    engine.dispose()


def test_generate_mapping_artifact_prefers_external_ref_and_code() -> None:
    artifact = build_mapping_artifact(
        organization_rows=[
            {"id": "org-ext", "name": "外部组织", "code": "ORG_EXT"},
            {"id": "org-code", "name": "编码组织", "code": "ORG_CODE"},
            {"id": "org-missing", "name": "未知组织", "code": "ORG_MISS"},
        ],
        ownership_rows=[
            {"id": "own-name", "name": "A权属", "code": "OWN_A"},
            {"id": "own-missing", "name": "B权属", "code": "OWN_B"},
        ],
        party_rows=[
            {
                "id": "party-org-ext",
                "party_type": "organization",
                "name": "外部组织",
                "code": "ORG_IGNORE",
                "external_ref": "org-ext",
            },
            {
                "id": "party-org-code",
                "party_type": "organization",
                "name": "编码组织",
                "code": "ORG_CODE",
                "external_ref": None,
            },
            {
                "id": "party-own-name",
                "party_type": "legal_entity",
                "name": "A权属",
                "code": "OWN_X",
                "external_ref": None,
            },
        ],
    )

    assert artifact.org_to_party_map == {
        "org-ext": "party-org-ext",
        "org-code": "party-org-code",
    }
    assert artifact.ownership_to_party_map == {"own-name": "party-own-name"}
    assert artifact.unmatched_org_ids == ["org-missing"]
    assert artifact.unmatched_ownership_ids == ["own-missing"]


def test_apply_mapping_updates_dry_run_and_exec() -> None:
    connection = _create_connection()
    try:
        connection.execute(
            sa.text(
                """
                CREATE TABLE assets (
                    id TEXT PRIMARY KEY,
                    ownership_id TEXT,
                    owner_party_id TEXT
                )
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO assets (id, ownership_id, owner_party_id)
                VALUES ('a1', 'own-1', NULL), ('a2', 'own-2', 'party-2')
                """
            )
        )

        dry_run_rows = _apply_mapping_updates(
            connection,
            table_name="assets",
            source_column="ownership_id",
            target_column="owner_party_id",
            mapping={"own-1": "party-1"},
            dry_run=True,
        )
        assert dry_run_rows == 1
        owner_after_dry_run = connection.execute(
            sa.text("SELECT owner_party_id FROM assets WHERE id = 'a1'")
        ).scalar_one()
        assert owner_after_dry_run is None

        updated_rows = _apply_mapping_updates(
            connection,
            table_name="assets",
            source_column="ownership_id",
            target_column="owner_party_id",
            mapping={"own-1": "party-1"},
            dry_run=False,
        )
        assert updated_rows == 1
        owner_after_exec = connection.execute(
            sa.text("SELECT owner_party_id FROM assets WHERE id = 'a1'")
        ).scalar_one()
        assert owner_after_exec == "party-1"
    finally:
        _close_connection(connection)


def test_backfill_role_scope_updates_organization_scope() -> None:
    connection = _create_connection()
    try:
        connection.execute(
            sa.text(
                """
                CREATE TABLE roles (
                    id TEXT PRIMARY KEY,
                    scope TEXT,
                    scope_id TEXT
                )
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO roles (id, scope, scope_id)
                VALUES ('r1', 'organization', 'org-1'),
                       ('r2', 'party', 'org-2')
                """
            )
        )

        affected = _backfill_role_scope(
            connection,
            org_to_party_map={"org-1": "party-1", "org-2": "party-2"},
            dry_run=False,
        )
        assert affected >= 2
        row_r1 = connection.execute(
            sa.text("SELECT scope, scope_id FROM roles WHERE id = 'r1'")
        ).one()
        row_r2 = connection.execute(
            sa.text("SELECT scope, scope_id FROM roles WHERE id = 'r2'")
        ).one()
        assert row_r1[0] == "party"
        assert row_r1[1] == "party-1"
        assert row_r2[0] == "party"
        assert row_r2[1] == "party-2"
    finally:
        _close_connection(connection)


def test_build_operations_uses_legacy_contract_summary_key() -> None:
    legacy_summary_key = ".".join(("legacy_contracts", "owner_party_id"))
    retired_summary_key = ".".join((LEGACY_CONTRACTS_TABLE, "owner_party_id"))

    operations = _build_operations(
        org_to_party_map={"org-1": "party-1"},
        ownership_to_party_map={"own-1": "party-1"},
    )

    assert any(
        operation[0] == legacy_summary_key
        and operation[1] == LEGACY_CONTRACTS_TABLE
        and operation[2] == "ownership_id"
        and operation[3] == "owner_party_id"
        for operation in operations
    )
    assert not any(operation[0] == retired_summary_key for operation in operations)


def test_reconciliation_role_scope_integrity_fails_for_invalid_scope() -> None:
    connection = _create_connection()
    try:
        connection.execute(
            sa.text(
                """
                CREATE TABLE roles (
                    id TEXT PRIMARY KEY,
                    scope TEXT,
                    scope_id TEXT
                )
                """
            )
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO roles (id, scope, scope_id)
                VALUES ('r-invalid', 'organization', 'org-1')
                """
            )
        )
        status, failed_count = _check_role_party_scope_integrity(connection)
        assert status == "FAIL"
        assert failed_count == 1
    finally:
        _close_connection(connection)


def test_choose_policy_package_uses_role_signals() -> None:
    assert _choose_policy_package({"name": "platform_admin"}) == "platform_admin"
    assert (
        _choose_policy_package({"name": "viewer", "is_system_role": True})
        == "dual_party_viewer"
    )
    assert _choose_policy_package({"name": "user"}) == "dual_party_viewer"
    assert _choose_policy_package({"category": "business"}) == "dual_party_viewer"
    assert _choose_policy_package({"display_name": "普通用户"}) == "dual_party_viewer"
    assert _choose_policy_package({"display_name": "审计角色"}) == "audit_viewer"
    assert _choose_policy_package({"category": "project"}) == "project_manager_operator"
    assert _choose_policy_package({"name": "owner_view"}) == "asset_owner_operator"
    assert _choose_policy_package({"name": "manager_ops"}) == "asset_manager_operator"
    assert _choose_policy_package({"name": "custom_role_x"}) == "no_data_access"
