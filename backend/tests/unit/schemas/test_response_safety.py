"""
Unit tests for response schemas that should not trigger lazy-loads.
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy.orm.attributes import NO_VALUE

from src.schemas.asset import AssetResponse
from src.schemas.organization import OrganizationResponse
from src.schemas.project import ProjectResponse


class DummyProject:
    def __init__(self) -> None:
        self.id = "proj-001"
        self.project_name = "测试项目"
        self.project_code = "PRJ-TEST01-000001"
        self.status = "planning"
        self.review_status = "draft"
        self.review_by = None
        self.reviewed_at = None
        self.review_reason = None
        self.data_status = "正常"
        self.manager_party_id = None
        now = datetime.now(UTC).replace(tzinfo=None)
        self.created_at = now
        self.updated_at = now
        self.created_by = None
        self.updated_by = None

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


class DummyAsset:
    def __init__(self) -> None:
        self.id = "asset-001"
        self.organization_id = None
        self.project_id = None
        self.ownership_id = None
        self.manager_party_id = None
        self.owner_party_id = "owner-1"
        self.project = None
        self.ownership = None
        self.ownership_entity = None
        self.ownership_category = None
        self.project_name = None
        self.asset_code = None
        self.asset_name = "测试资产"
        self.asset_form = None
        self.spatial_level = None
        self.business_usage = None
        self.province_code = None
        self.city_code = None
        self.district_code = None
        self.address_detail = None
        self.address = "测试地址"
        self.ownership_status = "已确权"
        self.property_nature = "经营性"
        self.usage_status = "出租"
        self.management_entity = None
        self.business_category = None
        self.is_litigated = False
        self.notes = None
        self.land_area = None
        self.actual_property_area = None
        self.rentable_area = None
        self.rented_area = None
        self.non_commercial_area = None
        self.include_in_occupancy_rate = True
        self.certificated_usage = None
        self.actual_usage = None
        self.tenant_name = None
        self.tenant_type = None
        self.lease_contract_number = None
        self.contract_start_date = None
        self.contract_end_date = None
        self.monthly_rent = None
        self.deposit = None
        self.is_sublease = False
        self.sublease_notes = None
        self.manager_name = None
        self.revenue_mode = None
        self.operation_status = None
        self.operation_agreement_start_date = None
        self.operation_agreement_end_date = None
        self.operation_agreement_attachments = None
        self.terminal_contract_files = None
        self.data_status = "正常"
        self.created_by = None
        self.updated_by = None
        self.version = 1
        self.tags = None
        self.review_status = None
        self.review_by = None
        self.reviewed_at = None
        self.review_reason = None
        self.audit_notes = None
        now = datetime.now(UTC).replace(tzinfo=None)
        self.created_at = now
        self.updated_at = now


def _fake_state(keys: list[str], rel_name: str, loaded_value=NO_VALUE):
    class FakeAttr:
        def __init__(self, key: str) -> None:
            self.key = key

    return SimpleNamespace(
        mapper=SimpleNamespace(column_attrs=[FakeAttr(key) for key in keys]),
        attrs=SimpleNamespace(**{rel_name: SimpleNamespace(loaded_value=loaded_value)}),
    )


def test_project_response_skips_unloaded_relation_objects() -> None:
    dummy = DummyProject()
    fake_state = _fake_state(
        ["id", "project_name", "project_code", "status", "review_status",
         "review_by", "reviewed_at", "review_reason", "manager_party_id",
         "data_status", "created_at", "updated_at", "created_by", "updated_by"],
        "ownership_relations",
    )

    with patch(
        "src.schemas.project.sa_inspect", return_value=fake_state, create=True
    ):
        result = ProjectResponse.model_validate(dummy)

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
        ["id", "project_name", "project_code", "status", "review_status",
         "review_by", "reviewed_at", "review_reason", "manager_party_id",
         "data_status", "created_at", "updated_at", "created_by", "updated_by"],
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


def test_asset_response_should_normalize_null_review_status_to_draft() -> None:
    result = AssetResponse.model_validate(DummyAsset())

    assert result.review_status == "draft"
