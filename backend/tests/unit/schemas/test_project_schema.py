"""Unit tests for project schema fields."""

from datetime import UTC, datetime

from src.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectRiskItem,
    ProjectUpdate,
)


def _build_project_payload() -> dict[str, object]:
    return {
        "id": "project-1",
        "project_name": "测试项目",
        "project_code": "PRJ-TEST01-202606-0001",
        "status": "planning",
        "data_status": "正常",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "created_by": None,
        "updated_by": None,
    }


def test_project_response_party_relations_keep_is_active() -> None:
    payload = _build_project_payload()
    payload["party_relations"] = [
        {
            "id": "rel-inactive",
            "project_id": "project-1",
            "party_id": "ownership-inactive",
            "party_name": "停用主体",
            "relation_type": "owner",
            "is_active": False,
        },
        {
            "id": "rel-active",
            "project_id": "project-1",
            "party_id": "ownership-active",
            "party_name": "有效主体",
            "relation_type": "owner",
            "is_active": True,
        },
    ]

    project = ProjectResponse.model_validate(payload)

    assert [relation["is_active"] for relation in project.party_relations] == [
        False,
        True,
    ]


def test_project_response_allows_legacy_project_code_for_read_path() -> None:
    payload = _build_project_payload()
    payload["project_code"] = "legacy-001"

    project = ProjectResponse.model_validate(payload)

    assert project.project_code == "legacy-001"


def test_project_create_accepts_operator_month_seq4_code() -> None:
    project = ProjectCreate(
        project_name="new-project",
        project_code="PRJ-OPER0001-202606-0001",
    )

    assert project.project_code == "PRJ-OPER0001-202606-0001"


def test_project_update_accepts_operator_month_seq4_code() -> None:
    project = ProjectUpdate(project_code="PRJ-OPER0001-202606-0002")

    assert project.project_code == "PRJ-OPER0001-202606-0002"


def test_project_response_should_not_expose_review_fields() -> None:
    payload = _build_project_payload()
    payload.update(
        {
            "review_status": "draft",
            "review_by": "reviewer",
            "reviewed_at": datetime.now(UTC),
            "review_reason": "legacy",
        }
    )

    project = ProjectResponse.model_validate(payload)

    assert "review_status" not in project.model_fields_set
    assert "review_by" not in project.model_fields_set
    assert "reviewed_at" not in project.model_fields_set
    assert "review_reason" not in project.model_fields_set


def test_project_risk_item_serializes_property_certificate_linkage() -> None:
    """Data-quality risks expose stable source fields instead of message parsing."""
    item = ProjectRiskItem(
        risk_id=("property-certificate:cert-1:asset:asset-1:holder_owner_mismatch"),
        risk_type="property_certificate_data_quality",
        message="holder and owner differ",
        asset_id="asset-1",
        property_certificate_id="cert-1",
        warning_code="holder_owner_mismatch",
    )

    assert item.model_dump() == {
        "risk_id": ("property-certificate:cert-1:asset:asset-1:holder_owner_mismatch"),
        "risk_type": "property_certificate_data_quality",
        "severity": "warning",
        "message": "holder and owner differ",
        "contract_relation_id": None,
        "display_name": None,
        "asset_id": "asset-1",
        "property_certificate_id": "cert-1",
        "warning_code": "holder_owner_mismatch",
    }
