"""
Unit tests for response schemas that should not trigger lazy-loads.
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy.orm.attributes import NO_VALUE

from src.schemas.organization import OrganizationResponse
from src.schemas.project import ProjectResponse


class DummyProject:
    def __init__(self) -> None:
        self.id = "proj-001"
        self.name = "测试项目"
        self.is_active = True
        self.data_status = "正常"
        now = datetime.now(UTC).replace(tzinfo=None)
        self.created_at = now
        self.updated_at = now

    @property
    def ownership_relations(self):  # type: ignore[override]
        raise RuntimeError("lazy ownership_relations access")


class DummyOrganization:
    def __init__(self) -> None:
        self.id = "org-001"
        self.name = "测试组织"
        self.code = "ORG001"
        self.level = 1
        self.sort_order = 0
        self.type = "company"
        self.status = "active"
        now = datetime.now(UTC).replace(tzinfo=None)
        self.created_at = now
        self.updated_at = now

    @property
    def children(self):  # type: ignore[override]
        raise RuntimeError("lazy children access")


def _fake_state(keys: list[str], rel_name: str, loaded_value=NO_VALUE):
    class FakeAttr:
        def __init__(self, key: str) -> None:
            self.key = key

    return SimpleNamespace(
        mapper=SimpleNamespace(column_attrs=[FakeAttr(key) for key in keys]),
        attrs=SimpleNamespace(**{rel_name: SimpleNamespace(loaded_value=loaded_value)}),
    )


def test_project_response_skips_unloaded_ownership_relations() -> None:
    dummy = DummyProject()
    fake_state = _fake_state(
        ["id", "name", "is_active", "data_status", "created_at", "updated_at"],
        "ownership_relations",
    )

    with patch(
        "src.schemas.project.sa_inspect", return_value=fake_state, create=True
    ):
        result = ProjectResponse.model_validate(dummy)

    assert result.ownership_relations is None
    assert result.party_relations == []


def test_project_response_builds_party_relations_from_ownership_relations() -> None:
    dummy = DummyProject()
    relation = SimpleNamespace(
        id="rel-1",
        project_id="proj-001",
        ownership_id="own-001",
        is_active=True,
        ownership=SimpleNamespace(name="测试权属方", code="OWN001", short_name="权属方"),
    )
    fake_state = _fake_state(
        ["id", "name", "is_active", "data_status", "created_at", "updated_at"],
        "ownership_relations",
        loaded_value=[relation],
    )

    with patch(
        "src.schemas.project.sa_inspect", return_value=fake_state, create=True
    ):
        result = ProjectResponse.model_validate(dummy)

    assert result.party_relations == [
        {
            "id": "rel-1",
            "project_id": "proj-001",
            "party_id": "own-001",
            "party_name": "测试权属方",
            "relation_type": "owner",
            "is_primary": True,
            "is_active": True,
        }
    ]


def test_organization_response_skips_unloaded_children() -> None:
    dummy = DummyOrganization()
    fake_state = _fake_state(
        [
            "id",
            "name",
            "code",
            "level",
            "sort_order",
            "type",
            "status",
            "created_at",
            "updated_at",
        ],
        "children",
    )

    with patch(
        "src.schemas.organization.sa_inspect", return_value=fake_state, create=True
    ):
        result = OrganizationResponse.model_validate(dummy)

    assert result.children == []
