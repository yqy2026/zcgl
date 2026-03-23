"""AssetReviewStatus 静态约束测试。"""

from src.models.asset import AssetReviewStatus


def test_asset_review_status_members_should_match_review_workflow() -> None:
    assert {member.name for member in AssetReviewStatus} == {
        "DRAFT",
        "PENDING",
        "APPROVED",
        "REVERSED",
    }


def test_asset_review_status_values_should_match_frozen_codes() -> None:
    assert {member.value for member in AssetReviewStatus} == {
        "draft",
        "pending",
        "approved",
        "reversed",
    }

