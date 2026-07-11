"""Tests for policy-package seed action coverage."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import pytest
import sqlalchemy as sa


def _load_seed_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260219_phase2_seed_data_policy_packages.py"
    )
    spec = spec_from_file_location("seed_data_policy_packages", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_backfill_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260221_backfill_expanded_policy_package_rules.py"
    )
    spec = spec_from_file_location("backfill_policy_package_rules", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_party_columns_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260219_phase2_add_party_columns_step1.py"
    )
    spec = spec_from_file_location("phase2_add_party_columns_step1", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_missing_resource_backfill_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260224_backfill_ownership_occupancy_policy_rules.py"
    )
    spec = spec_from_file_location(
        "backfill_ownership_occupancy_policy_rules", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_cleanup_legacy_contract_rules_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260307_m2_cleanup_legacy_contract_policy_rules.py"
    )
    spec = spec_from_file_location("cleanup_legacy_contract_policy_rules", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_drop_collection_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260615_drop_collection_module.py"
    )
    spec = spec_from_file_location("drop_collection_module", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_drop_manual_overdue_status_module() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[3]
        / "alembic"
        / "versions"
        / "20260616_drop_manual_overdue_status.py"
    )
    spec = spec_from_file_location("drop_manual_overdue_status", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _merged_policy_seeds() -> list[dict[str, object]]:
    seed_module = _load_seed_module()
    backfill_module = _load_backfill_module()

    merged: dict[str, dict[str, object]] = {}
    for seed in seed_module.POLICY_SEEDS:
        payload = dict(seed)
        payload.setdefault(
            "condition_expr",
            seed_module._condition_expr_for_policy(str(payload["name"])),
        )
        merged[str(payload["rule_id"])] = payload
    for seed in backfill_module.BACKFILL_POLICY_SEEDS:
        payload = dict(seed)
        payload.setdefault(
            "condition_expr",
            backfill_module._condition_expr_for_policy(str(payload["name"])),
        )
        merged[str(payload["rule_id"])] = payload
    return list(merged.values())


def _actions_for_policy(
    policy_seeds: list[dict[str, object]],
    policy_name: str,
) -> set[str]:
    return {
        str(seed["action"]) for seed in policy_seeds if str(seed["name"]) == policy_name
    }


def _resource_actions_for_policy(
    policy_seeds: list[dict[str, object]],
    policy_name: str,
) -> dict[str, set[str]]:
    coverage: dict[str, set[str]] = {}
    for seed in policy_seeds:
        if str(seed["name"]) != policy_name:
            continue
        resource = str(seed["resource_type"])
        action = str(seed["action"])
        coverage.setdefault(resource, set()).add(action)
    return coverage


def _collect_var_paths(node: object) -> set[str]:
    if isinstance(node, dict):
        if set(node.keys()) == {"var"} and isinstance(node.get("var"), str):
            return {str(node["var"])}
        paths: set[str] = set()
        for value in node.values():
            paths.update(_collect_var_paths(value))
        return paths

    if isinstance(node, list):
        paths: set[str] = set()
        for value in node:
            paths.update(_collect_var_paths(value))
        return paths

    return set()


def _discover_api_authz_resource_types() -> set[str]:
    api_root = Path(__file__).resolve().parents[3] / "src" / "api" / "v1"
    keyword_pattern = re.compile(
        r"require_authz\([\s\S]*?action\s*=\s*['\"]([^'\"]+)['\"][\s\S]*?resource_type\s*=\s*['\"]([^'\"]+)['\"]"
    )
    positional_pattern = re.compile(
        r"require_authz\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]"
    )

    resources: set[str] = set()
    for py_file in api_root.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        for match in keyword_pattern.finditer(source):
            resources.add(str(match.group(2)))
        for match in positional_pattern.finditer(source):
            resources.add(str(match.group(2)))
    return resources


def test_seed_packages_cover_route_guard_actions() -> None:
    policy_seeds = _merged_policy_seeds()

    read_only_packages = {"dual_party_viewer", "audit_viewer"}
    read_write_packages = {
        "platform_admin",
        "asset_owner_operator",
        "asset_manager_operator",
        "project_manager_operator",
    }
    deny_packages = {"no_data_access"}

    for package in read_only_packages:
        assert "read" in _actions_for_policy(policy_seeds, package)

    required_rw_actions = {"create", "read", "update", "delete"}
    for package in read_write_packages:
        assert required_rw_actions.issubset(_actions_for_policy(policy_seeds, package))

    for package in deny_packages:
        assert required_rw_actions.issubset(_actions_for_policy(policy_seeds, package))


def test_seed_packages_cover_new_guarded_resource_types() -> None:
    policy_seeds = _merged_policy_seeds()
    backfill_module = _load_backfill_module()

    guarded_resources = set(backfill_module._EXPANDED_RESOURCE_TYPES)
    rw_actions = {"create", "read", "update", "delete"}

    full_rw_packages = {
        "platform_admin",
        "asset_owner_operator",
        "asset_manager_operator",
    }
    read_only_packages = {
        "project_manager_operator",
        "dual_party_viewer",
        "audit_viewer",
    }
    deny_packages = {"no_data_access"}

    for package in full_rw_packages:
        coverage = _resource_actions_for_policy(policy_seeds, package)
        for resource in guarded_resources:
            assert rw_actions.issubset(coverage.get(resource, set()))

    for package in read_only_packages:
        coverage = _resource_actions_for_policy(policy_seeds, package)
        for resource in guarded_resources:
            assert "read" in coverage.get(resource, set())

    for package in deny_packages:
        coverage = _resource_actions_for_policy(policy_seeds, package)
        for resource in guarded_resources:
            assert rw_actions.issubset(coverage.get(resource, set()))


def test_backfill_expanded_resource_types_should_include_system_domain_resources() -> (
    None
):
    module = _load_backfill_module()

    expected_resources = {
        "backup",
        "analytics",
        "dictionary",
        "enum_field",
        "history",
        "notification",
    }

    assert expected_resources.issubset(set(module._EXPANDED_RESOURCE_TYPES))
    assert "contact" not in set(module._EXPANDED_RESOURCE_TYPES)


def test_backfill_expanded_resource_types_should_match_non_base_api_authz_resources() -> (
    None
):
    module = _load_backfill_module()

    api_resources = _discover_api_authz_resource_types()
    non_base_api_resources = api_resources - {"asset", "project"}

    retired_resources = {"collection"}

    later_backfill_resources = {"ledger"}
    assert (
        (set(module._EXPANDED_RESOURCE_TYPES) - retired_resources)
        | later_backfill_resources
    ) == non_base_api_resources
    assert retired_resources.isdisjoint(api_resources)


def test_backfill_expanded_resource_types_should_not_keep_legacy_contract_resource() -> (
    None
):
    module = _load_backfill_module()

    assert "rent_contract" not in set(module._EXPANDED_RESOURCE_TYPES)


def test_backfill_expanded_resource_types_should_include_task() -> None:
    module = _load_backfill_module()

    assert "task" in set(module._EXPANDED_RESOURCE_TYPES)


def test_backfill_expanded_resource_types_should_include_operation_log() -> None:
    module = _load_backfill_module()

    assert "operation_log" in set(module._EXPANDED_RESOURCE_TYPES)


def test_backfill_migration_targets_already_migrated_databases() -> None:
    module = _load_backfill_module()

    assert module.down_revision == "20260219_phase2_seed_data_policy_packages"
    assert len(module.BACKFILL_POLICY_SEEDS) > 0


def test_cleanup_legacy_contract_rule_migration_should_follow_current_head() -> None:
    module = _load_cleanup_legacy_contract_rules_module()

    assert module.down_revision == "20260307_m2_contract_number_on_contracts"


def test_drop_collection_module_migration_should_follow_current_head() -> None:
    module = _load_drop_collection_module()

    assert module.down_revision == "20260612_drop_contract_relations"


def test_drop_collection_module_upgrade_should_delete_runtime_rules_and_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_drop_collection_module()
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    dropped_tables: list[str] = []

    metadata = sa.MetaData()
    rule_table = sa.Table(
        "abac_policy_rules",
        metadata,
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("resource_type", sa.String, nullable=False),
    )
    resource_permission_table = sa.Table(
        "resource_permissions",
        metadata,
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("resource_type", sa.String, nullable=False),
        sa.Column("permission_id", sa.String, nullable=True),
    )
    permission_table = sa.Table(
        "permissions",
        metadata,
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("resource", sa.String, nullable=False),
    )
    role_permission_table = sa.Table(
        "role_permissions",
        metadata,
        sa.Column("role_id", sa.String, nullable=False),
        sa.Column("permission_id", sa.String, nullable=False),
    )
    permission_grant_table = sa.Table(
        "permission_grants",
        metadata,
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("permission_id", sa.String, nullable=False),
    )
    sa.Table(
        "collection_records",
        metadata,
        sa.Column("id", sa.String, primary_key=True),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            rule_table.insert(),
            [
                {"id": "collection_rule", "resource_type": "collection"},
                {"id": "asset_rule", "resource_type": "asset"},
            ],
        )
        connection.execute(
            resource_permission_table.insert(),
            [
                {
                    "id": "collection_resource_permission",
                    "resource_type": "collection",
                    "permission_id": None,
                },
                {
                    "id": "legacy_mismatched_collection_permission",
                    "resource_type": "asset",
                    "permission_id": "collection_permission",
                },
                {
                    "id": "asset_resource_permission",
                    "resource_type": "asset",
                    "permission_id": "asset_permission",
                },
            ],
        )
        connection.execute(
            permission_table.insert(),
            [
                {"id": "collection_permission", "resource": "collection"},
                {"id": "asset_permission", "resource": "asset"},
            ],
        )
        connection.execute(
            role_permission_table.insert(),
            [
                {"role_id": "role_1", "permission_id": "collection_permission"},
                {"role_id": "role_1", "permission_id": "asset_permission"},
            ],
        )
        connection.execute(
            permission_grant_table.insert(),
            [
                {"id": "collection_grant", "permission_id": "collection_permission"},
                {"id": "asset_grant", "permission_id": "asset_permission"},
            ],
        )

        monkeypatch.setattr(module.op, "get_bind", lambda: connection)
        monkeypatch.setattr(module.op, "drop_table", dropped_tables.append)

        module.upgrade()

        remaining_rules = set(connection.execute(sa.select(rule_table.c.id)).scalars())
        remaining_permissions = set(
            connection.execute(sa.select(permission_table.c.id)).scalars()
        )
        remaining_role_permissions = set(
            connection.execute(
                sa.select(role_permission_table.c.permission_id)
            ).scalars()
        )
        remaining_resource_permissions = set(
            connection.execute(sa.select(resource_permission_table.c.id)).scalars()
        )
        remaining_grants = set(
            connection.execute(sa.select(permission_grant_table.c.id)).scalars()
        )

    assert dropped_tables == ["collection_records"]
    assert remaining_rules == {"asset_rule"}
    assert remaining_permissions == {"asset_permission"}
    assert remaining_role_permissions == {"asset_permission"}
    assert remaining_resource_permissions == {"asset_resource_permission"}
    assert remaining_grants == {"asset_grant"}


def test_drop_manual_overdue_status_migration_should_follow_current_head() -> None:
    module = _load_drop_manual_overdue_status_module()

    assert module.down_revision == "20260615_drop_collection_module"


def test_drop_manual_overdue_status_upgrade_should_normalize_ledger_statuses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_drop_manual_overdue_status_module()
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    metadata = sa.MetaData()

    contract_ledger_table = sa.Table(
        "contract_ledger_entries",
        metadata,
        sa.Column("entry_id", sa.String, primary_key=True),
        sa.Column("payment_status", sa.String, nullable=False),
        sa.Column("paid_amount", sa.Numeric(15, 2), nullable=False),
    )
    service_fee_ledger_table = sa.Table(
        "service_fee_ledgers",
        metadata,
        sa.Column("service_fee_entry_id", sa.String, primary_key=True),
        sa.Column("payment_status", sa.String, nullable=False),
        sa.Column("paid_amount", sa.Numeric(15, 2), nullable=False),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            contract_ledger_table.insert(),
            [
                {
                    "entry_id": "contract_unpaid_overdue",
                    "payment_status": "overdue",
                    "paid_amount": 0,
                },
                {
                    "entry_id": "contract_partial_overdue",
                    "payment_status": "overdue",
                    "paid_amount": 10,
                },
                {
                    "entry_id": "contract_paid",
                    "payment_status": "paid",
                    "paid_amount": 100,
                },
            ],
        )
        connection.execute(
            service_fee_ledger_table.insert(),
            [
                {
                    "service_fee_entry_id": "fee_unpaid_overdue",
                    "payment_status": "overdue",
                    "paid_amount": 0,
                },
                {
                    "service_fee_entry_id": "fee_partial_overdue",
                    "payment_status": "overdue",
                    "paid_amount": 5,
                },
            ],
        )

        monkeypatch.setattr(module.op, "get_bind", lambda: connection)

        module.upgrade()

        contract_statuses = dict(
            connection.execute(
                sa.select(
                    contract_ledger_table.c.entry_id,
                    contract_ledger_table.c.payment_status,
                )
            ).all()
        )
        service_fee_statuses = dict(
            connection.execute(
                sa.select(
                    service_fee_ledger_table.c.service_fee_entry_id,
                    service_fee_ledger_table.c.payment_status,
                )
            ).all()
        )

    assert contract_statuses == {
        "contract_unpaid_overdue": "unpaid",
        "contract_partial_overdue": "partial",
        "contract_paid": "paid",
    }
    assert service_fee_statuses == {
        "fee_unpaid_overdue": "unpaid",
        "fee_partial_overdue": "partial",
    }


def test_seed_migration_should_keep_original_predecessor_for_upgrade_continuity() -> (
    None
):
    module = _load_seed_module()

    assert module.down_revision == "20260219_create_abac_and_relation_tables"


def test_party_columns_migration_should_follow_backfill_head() -> None:
    module = _load_party_columns_module()

    assert module.down_revision == "20260221_backfill_expanded_policy_package_rules"


def test_missing_resource_backfill_migration_should_follow_party_columns_head() -> None:
    module = _load_missing_resource_backfill_module()

    assert module.down_revision == "20260219_phase2_add_party_columns_step1"


def test_missing_resource_backfill_should_cover_all_current_missing_resources() -> None:
    module = _load_missing_resource_backfill_module()

    assert set(module._MISSING_RESOURCE_TYPES) == {
        "ownership",
        "occupancy",
        "custom_field",
    }


def test_backfill_migration_should_not_delete_or_reseed_legacy_rule_ids() -> None:
    module = _load_backfill_module()

    legacy_rule_ids = {
        "seed_rule_platform_admin_asset_list",
        "seed_rule_asset_owner_operator_asset_read",
        "seed_rule_asset_manager_operator_asset_update",
        "seed_rule_dual_party_viewer_asset_list",
        "seed_rule_project_manager_operator_project_update",
        "seed_rule_audit_viewer_asset_read",
        "seed_rule_no_data_access_asset_list",
    }

    backfill_rule_ids = {str(seed["rule_id"]) for seed in module.BACKFILL_POLICY_SEEDS}
    assert legacy_rule_ids.isdisjoint(backfill_rule_ids)


def test_backfill_migration_should_define_legacy_rule_condition_updates() -> None:
    module = _load_backfill_module()

    legacy_rule_name_map: dict[str, str] = module.LEGACY_POLICY_RULE_NAME_BY_ID
    assert set(legacy_rule_name_map.keys()) == set(module.LEGACY_POLICY_RULE_IDS)

    scoped_policy_names = {
        "asset_owner_operator",
        "asset_manager_operator",
        "dual_party_viewer",
        "project_manager_operator",
        "audit_viewer",
    }
    tautology_expr = {"==": [1, 1]}

    for policy_name in legacy_rule_name_map.values():
        expr = module._condition_expr_for_policy(policy_name)
        if policy_name in scoped_policy_names:
            assert expr != tautology_expr


def test_backfill_upgrade_should_update_existing_legacy_rule_condition_expr() -> None:
    module = _load_backfill_module()
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)

    metadata = sa.MetaData()
    policy_table = sa.Table(
        "abac_policies",
        metadata,
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("effect", sa.String, nullable=False),
        sa.Column("priority", sa.Integer, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    rule_table = sa.Table(
        "abac_policy_rules",
        metadata,
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("policy_id", sa.String, nullable=False),
        sa.Column("resource_type", sa.String, nullable=False),
        sa.Column("action", sa.String, nullable=False),
        sa.Column("condition_expr", sa.JSON, nullable=False),
        sa.Column("field_mask", sa.JSON, nullable=True),
    )

    metadata.create_all(engine)

    now = datetime.now(UTC).replace(tzinfo=None)
    legacy_rule_id = "seed_rule_asset_owner_operator_asset_read"
    tautology_expr = {"==": [1, 1]}
    expected_expr = module._condition_expr_for_policy("asset_owner_operator")

    with engine.begin() as connection:
        connection.execute(
            policy_table.insert().values(
                id="seed_policy_asset_owner_operator",
                name="asset_owner_operator",
                effect="allow",
                priority=20,
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        )
        connection.execute(
            rule_table.insert().values(
                id=legacy_rule_id,
                policy_id="seed_policy_asset_owner_operator",
                resource_type="asset",
                action="read",
                condition_expr=tautology_expr,
                field_mask=None,
            )
        )

        original_get_bind = module.op.get_bind
        module.op.get_bind = lambda: connection
        try:
            module.upgrade()
        finally:
            module.op.get_bind = original_get_bind

        stored_expr = connection.execute(
            sa.select(rule_table.c.condition_expr).where(
                rule_table.c.id == legacy_rule_id
            )
        ).scalar_one()

    if isinstance(stored_expr, str):
        stored_expr = json.loads(stored_expr)

    assert stored_expr == expected_expr
    assert stored_expr != tautology_expr


def test_missing_resource_backfill_upgrade_should_insert_expected_rules() -> None:
    module = _load_missing_resource_backfill_module()
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)

    metadata = sa.MetaData()
    sa.Table(
        "abac_policies",
        metadata,
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("effect", sa.String, nullable=False),
        sa.Column("priority", sa.Integer, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    rule_table = sa.Table(
        "abac_policy_rules",
        metadata,
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("policy_id", sa.String, nullable=False),
        sa.Column("resource_type", sa.String, nullable=False),
        sa.Column("action", sa.String, nullable=False),
        sa.Column("condition_expr", sa.JSON, nullable=False),
        sa.Column("field_mask", sa.JSON, nullable=True),
    )

    metadata.create_all(engine)

    expected_rule_ids = {
        str(seed["rule_id"]) for seed in module.MISSING_RESOURCE_POLICY_SEEDS
    }
    sample_rule_id = "seed_rule_asset_owner_operator_ownership_read"
    expected_expr = module._condition_expr_for_policy("asset_owner_operator")

    with engine.begin() as connection:
        original_get_bind = module.op.get_bind
        module.op.get_bind = lambda: connection
        try:
            module.upgrade()
            module.upgrade()
        finally:
            module.op.get_bind = original_get_bind

        stored_rule_ids = set(
            connection.execute(
                sa.select(rule_table.c.id).where(rule_table.c.id.in_(expected_rule_ids))
            ).scalars()
        )
        assert stored_rule_ids == expected_rule_ids

        stored_expr = connection.execute(
            sa.select(rule_table.c.condition_expr).where(
                rule_table.c.id == sample_rule_id
            )
        ).scalar_one()

        total_inserted = connection.execute(
            sa.select(sa.func.count())
            .select_from(rule_table)
            .where(rule_table.c.id.in_(expected_rule_ids))
        ).scalar_one()

    if isinstance(stored_expr, str):
        stored_expr = json.loads(stored_expr)

    assert stored_expr == expected_expr
    assert total_inserted == len(expected_rule_ids)


def test_cleanup_legacy_contract_rule_migration_should_delete_retired_rules() -> None:
    module = _load_cleanup_legacy_contract_rules_module()
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)

    metadata = sa.MetaData()
    rule_table = sa.Table(
        "abac_policy_rules",
        metadata,
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("policy_id", sa.String, nullable=False),
        sa.Column("resource_type", sa.String, nullable=False),
        sa.Column("action", sa.String, nullable=False),
        sa.Column("condition_expr", sa.JSON, nullable=False),
        sa.Column("field_mask", sa.JSON, nullable=True),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            rule_table.insert(),
            [
                {
                    "id": "legacy_contract_rule",
                    "policy_id": "policy_1",
                    "resource_type": "rent_contract",
                    "action": "read",
                    "condition_expr": {"==": [1, 1]},
                    "field_mask": None,
                },
                {
                    "id": "active_contract_rule",
                    "policy_id": "policy_1",
                    "resource_type": "contract",
                    "action": "read",
                    "condition_expr": {"==": [1, 1]},
                    "field_mask": None,
                },
            ],
        )

        original_get_bind = module.op.get_bind
        module.op.get_bind = lambda: connection
        try:
            module.upgrade()
        finally:
            module.op.get_bind = original_get_bind

        remaining_resources = set(
            connection.execute(sa.select(rule_table.c.resource_type)).scalars().all()
        )

    assert "rent_contract" not in remaining_resources
    assert "contract" in remaining_resources


def test_scoped_policy_packages_should_not_use_tautology_conditions() -> None:
    policy_seeds = _merged_policy_seeds()
    scoped_packages = {
        "asset_owner_operator",
        "asset_manager_operator",
        "dual_party_viewer",
        "project_manager_operator",
        "audit_viewer",
    }
    tautology_expr = {"==": [1, 1]}

    for seed in policy_seeds:
        policy_name = str(seed["name"])
        if policy_name not in scoped_packages:
            continue
        assert seed["condition_expr"] != tautology_expr


def test_scoped_policy_packages_should_reference_party_scope_variables() -> None:
    policy_seeds = _merged_policy_seeds()

    expected_vars_by_policy = {
        "asset_owner_operator": {"subject.owner_party_ids"},
        "asset_manager_operator": {"subject.manager_party_ids"},
        "dual_party_viewer": {"subject.owner_party_ids", "subject.manager_party_ids"},
        "project_manager_operator": {"subject.manager_party_ids"},
        "audit_viewer": {"subject.owner_party_ids", "subject.manager_party_ids"},
    }

    for policy_name, expected_vars in expected_vars_by_policy.items():
        sample_seed = next(
            seed for seed in policy_seeds if str(seed["name"]) == policy_name
        )
        actual_vars = _collect_var_paths(sample_seed["condition_expr"])
        assert expected_vars.issubset(actual_vars)


def test_scoped_policy_conditions_should_fail_closed_when_resource_scope_missing() -> (
    None
):
    deny_all_expr = {"==": [1, 0]}
    scoped_policy_names = {
        "asset_owner_operator",
        "asset_manager_operator",
        "dual_party_viewer",
        "project_manager_operator",
        "audit_viewer",
    }

    modules = (_load_seed_module(), _load_backfill_module())
    for module in modules:
        for policy_name in scoped_policy_names:
            condition_expr = module._condition_expr_for_policy(policy_name)
            assert isinstance(condition_expr, dict)
            if_branch = condition_expr.get("if")
            assert isinstance(if_branch, list)
            assert len(if_branch) == 3
            assert if_branch[2] == deny_all_expr
