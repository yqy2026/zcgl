"""Tests for the generic attachment storage model."""

from src.models.attachment import Attachment


def test_attachment_model_supports_payment_flow_ownership() -> None:
    columns = Attachment.__table__.c

    assert Attachment.__tablename__ == "attachments"
    assert columns["owner_type"].nullable is False
    assert columns["owner_id"].nullable is False
    assert columns["storage_key"].unique is True
    assert columns["file_size"].nullable is False

    constraint_sql = " ".join(
        str(constraint.sqltext)
        for constraint in Attachment.__table__.constraints
        if hasattr(constraint, "sqltext")
    )
    assert "payment_flow" in constraint_sql
    assert "file_size <= 20971520" in constraint_sql
