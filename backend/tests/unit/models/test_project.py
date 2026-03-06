"""Project model unit tests."""

from src.models.project import Project


def test_project_creation_and_repr() -> None:
    project = Project(project_name="Urban Renewal", project_code="PRJ-URB001-000001", status="planning")

    assert project.project_name == "Urban Renewal"
    assert project.project_code == "PRJ-URB001-000001"
    assert project.status == "planning"
    assert "Urban Renewal" in repr(project)
    assert "PRJ-URB001-000001" in repr(project)


def test_project_table_name() -> None:
    assert Project.__tablename__ == "projects"

