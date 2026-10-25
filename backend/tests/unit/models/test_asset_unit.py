"""Contract tests for the asset-operations v5 asset-unit models."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, UniqueConstraint

from src.models.asset_unit import (
    AssetUnit,
    AssetUnitBoundaryChange,
    AssetUnitBoundarySource,
    PropertyCertificateAssetUnit,
)


def _constraint_names(model: type[object]) -> set[str]:
    return {
        constraint.name
        for constraint in model.__table__.constraints  # type: ignore[attr-defined]
        if constraint.name is not None
    }


def test_asset_unit_contains_only_source_fields_for_rental_projection() -> None:
    columns = set(AssetUnit.__table__.c.keys())

    assert {
        "id",
        "unit_code",
        "name",
        "project_id",
        "owner_party_id",
        "address",
        "usage_type",
        "acquisition_mode",
        "is_operating",
        "land_area",
        "building_area",
        "rentable_area",
        "managed_from",
        "managed_to",
        "vacancy_reason",
        "expected_lease_start",
        "predecessor_unit_ids",
        "version",
        "created_at",
        "updated_at",
    } <= columns
    assert columns.isdisjoint(
        {"rental_status", "rented_area", "occupancy_rate", "upstream_risk"}
    )


def test_asset_unit_database_constraints_encode_stable_invariants() -> None:
    names = _constraint_names(AssetUnit)

    assert {
        "ck_asset_units_acquisition_mode",
        "ck_asset_units_land_area_nonnegative",
        "ck_asset_units_building_area_nonnegative",
        "ck_asset_units_rentable_area_valid",
        "ck_asset_units_managed_range",
        "ck_asset_units_vacancy_reason",
        "uq_asset_units_unit_code",
    } <= names
    assert any(
        isinstance(constraint, UniqueConstraint)
        and tuple(constraint.columns.keys()) == ("unit_code",)
        for constraint in AssetUnit.__table__.constraints
    )
    assert AssetUnit.__mapper__.version_id_col is AssetUnit.__table__.c.version


def test_asset_unit_boundary_change_is_append_only_and_idempotent() -> None:
    columns = set(AssetUnitBoundaryChange.__table__.c.keys())
    names = _constraint_names(AssetUnitBoundaryChange)

    assert {
        "id",
        "change_type",
        "effective_date",
        "source_unit_ids",
        "result_unit_ids",
        "area_check",
        "reason",
        "created_by",
        "created_at",
        "idempotency_key",
        "request_fingerprint",
        "result_data",
    } <= columns
    assert "ck_asset_unit_boundary_changes_type" in names
    assert "uq_asset_unit_boundary_changes_actor_request" in names
    assert any(
        isinstance(constraint, UniqueConstraint)
        and tuple(constraint.columns.keys()) == ("created_by", "idempotency_key")
        for constraint in AssetUnitBoundaryChange.__table__.constraints
    )


def test_boundary_source_relation_allows_one_consuming_change_per_unit() -> None:
    table = AssetUnitBoundarySource.__table__

    assert {"id", "asset_unit_id", "boundary_change_id"} <= set(table.c.keys())
    assert "uq_asset_unit_boundary_sources_unit" in _constraint_names(
        AssetUnitBoundarySource
    )
    assert all(
        isinstance(constraint, CheckConstraint)
        for constraint in [
            next(
                constraint
                for constraint in AssetUnitBoundaryChange.__table__.constraints
                if constraint.name == "ck_asset_unit_boundary_changes_type"
            )
        ]
    )


def test_property_certificate_asset_unit_link_is_temporal_and_unique() -> None:
    table = PropertyCertificateAssetUnit.__table__

    assert tuple(table.primary_key.columns.keys()) == (
        "certificate_id",
        "asset_unit_id",
    )
    assert {"effective_from", "effective_to"} <= set(table.c.keys())
    assert "ck_property_certificate_asset_units_effective_range" in _constraint_names(
        PropertyCertificateAssetUnit
    )
