"""Unit tests for project schema compatibility fields."""

from datetime import UTC, datetime

from src.schemas.project import ProjectResponse


def _build_project_payload() -> dict[str, object]:
    return {
        "id": "project-1",
        "name": "测试项目",
        "is_active": True,
        "data_status": "正常",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "created_by": None,
        "updated_by": None,
    }


def test_project_response_party_relations_keep_is_active_from_ownership_relations() -> None:
    payload = _build_project_payload()
    payload["ownership_relations"] = [
        {
            "id": "rel-inactive",
            "project_id": "project-1",
            "ownership_id": "ownership-inactive",
            "ownership_name": "停用主体",
            "is_active": False,
        },
        {
            "id": "rel-active",
            "project_id": "project-1",
            "ownership_id": "ownership-active",
            "ownership_name": "有效主体",
            "is_active": True,
        },
    ]

    project = ProjectResponse.model_validate(payload)

    assert [relation["is_active"] for relation in project.party_relations] == [False, True]
