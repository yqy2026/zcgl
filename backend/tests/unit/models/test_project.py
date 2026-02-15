"""Project model unit tests."""

from src.models.project import Project


def test_project_creation_and_repr() -> None:
    project = Project(name="Urban Renewal", code="PRJ-001", project_status="在建")

    assert project.name == "Urban Renewal"
    assert project.code == "PRJ-001"
    assert project.project_status == "在建"
    assert "Urban Renewal" in repr(project)
    assert "PRJ-001" in repr(project)


def test_project_table_name() -> None:
    assert Project.__tablename__ == "projects"

