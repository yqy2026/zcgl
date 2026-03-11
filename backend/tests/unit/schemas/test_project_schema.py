"""Unit tests for project schema fields."""

from datetime import UTC, datetime

from src.schemas.project import ProjectResponse


def _build_project_payload() -> dict[str, object]:
    return {
        "id": "project-1",
        "project_name": "测试项目",
        "project_code": "PRJ-TEST01-000001",
        "status": "planning",
        "review_status": "draft",
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

    assert [relation["is_active"] for relation in project.party_relations] == [False, True]


def test_project_response_allows_legacy_project_code_for_read_path() -> None:
    payload = _build_project_payload()
    payload["project_code"] = "legacy-001"

    project = ProjectResponse.model_validate(payload)

    assert project.project_code == "legacy-001"
