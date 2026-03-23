from sqlalchemy import select

from src.crud.query_builder import PartyFilter, QueryBuilder
from src.models.asset import Asset  # Using Asset as a test model
from src.models.ownership import Ownership
from src.models.property_certificate import PropertyCertificate
from src.models.rbac import Role
from src.models.system_dictionary import AssetCustomField


class TestQueryBuilder:
    def test_build_query_basic(self):
        qb = QueryBuilder(Asset)
        query = qb.build_query()
        compiled = str(query.compile())
        assert "SELECT assets.id" in compiled or "SELECT assets." in compiled

    def test_build_query_with_filters(self):
        qb = QueryBuilder(Asset)
        filters = {
            "asset_name": "Test Asset",
            "min_actual_property_area": 100,
            "max_actual_property_area": 200,
            "id__in": ["1", "2"],
        }
        query = qb.build_query(filters=filters)
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "assets.asset_name = 'Test Asset'" in compiled
        assert "assets.actual_property_area >= 100" in compiled
        assert "assets.actual_property_area <= 200" in compiled
        assert "assets.id IN ('1', '2')" in compiled

    def test_build_query_search(self):
        qb = QueryBuilder(Asset)
        search = "Building"
        search_fields = ["asset_name", "address"]
        query = qb.build_query(search_query=search, search_fields=search_fields)
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert (
            "lower(assets.asset_name) LIKE lower('%Building%')" in compiled
            or "assets.asset_name ILIKE" in compiled
        )
        assert (
            "lower(assets.address) LIKE lower('%Building%')" in compiled
            or "assets.address ILIKE" in compiled
        )
        assert "OR" in compiled

    def test_build_count_query(self):
        qb = QueryBuilder(Asset)
        filters = {"asset_name": "Test"}
        query = qb.build_count_query(filters=filters)
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "count" in compiled.lower()
        assert "assets.asset_name = 'Test'" in compiled

    def test_build_count_query_with_base_query_and_distinct(self):
        qb = QueryBuilder(Asset)
        base_query = select(Asset.id).join(
            Ownership, Asset.ownership_id == Ownership.id, isouter=True
        )
        query = qb.build_count_query(
            search_conditions=[Ownership.name.ilike("%test%")],
            base_query=base_query,
            distinct_column=Asset.id,
        )
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "distinct" in compiled.lower()
        assert "ownerships" in compiled.lower()

    def test_soft_delete_filter_allows_null_data_status(self):
        qb = QueryBuilder(Asset)
        query = qb.build_query()
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "assets.data_status IS NULL" in compiled
        assert (
            "assets.data_status != '已删除'" in compiled
            or "assets.data_status <> '已删除'" in compiled
        )

    def test_soft_delete_filter_skipped_when_data_status_explicit(self):
        qb = QueryBuilder(Asset)
        query = qb.build_query(filters={"data_status": "已删除"})
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "assets.data_status = '已删除'" in compiled
        assert "assets.data_status IS NULL" not in compiled

    def test_build_query_applies_party_filter_for_party_id(self):
        qb = QueryBuilder(Role)
        query = qb.build_query(
            party_filter=PartyFilter(
                party_ids=["party-1", "party-2"],
                filter_mode="owner",
            )
        )
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "roles.party_id IN ('party-1', 'party-2')" in compiled

    def test_build_count_query_applies_party_filter_for_party_id(self):
        qb = QueryBuilder(Role)
        query = qb.build_count_query(
            party_filter=PartyFilter(
                party_ids=["party-1"],
                filter_mode="owner",
            )
        )
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "roles.party_id IN ('party-1')" in compiled

    def test_build_query_fail_closed_when_party_filter_has_no_party_ids(self):
        qb = QueryBuilder(Role)
        query = qb.build_query(party_filter=PartyFilter(party_ids=[]))
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "false" in compiled.lower() or "0 = 1" in compiled

    def test_build_query_skips_party_filter_when_model_has_no_party_column(self):
        qb = QueryBuilder(AssetCustomField)
        query = qb.build_query(
            party_filter=PartyFilter(
                party_ids=["party-1"],
                filter_mode="owner",
            )
        )
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "false" not in compiled.lower()
        assert "0 = 1" not in compiled

    def test_build_count_query_skips_party_filter_when_model_has_no_party_column(self):
        qb = QueryBuilder(AssetCustomField)
        query = qb.build_count_query(
            party_filter=PartyFilter(
                party_ids=["party-1"],
                filter_mode="owner",
            )
        )
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "false" not in compiled.lower()
        assert "0 = 1" not in compiled

    def test_build_query_any_party_filter_handles_multiple_party_columns(self):
        qb = QueryBuilder(Asset)
        query = qb.build_query(
            party_filter=PartyFilter(
                party_ids=["party-1"],
                filter_mode="any",
            )
        )
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "assets.owner_party_id IN ('party-1')" in compiled
        assert "assets.manager_party_id IN ('party-1')" in compiled
        assert "assets.organization_id IN ('party-1')" not in compiled

    def test_build_query_should_keep_owner_and_manager_scope_separate(self):
        qb = QueryBuilder(Asset)
        query = qb.build_query(
            party_filter=PartyFilter(
                party_ids=["owner-1", "manager-1"],
                owner_party_ids=["owner-1"],
                manager_party_ids=["manager-1"],
            )
        )
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "assets.owner_party_id IN ('owner-1')" in compiled
        assert "assets.manager_party_id IN ('manager-1')" in compiled
        assert "assets.owner_party_id IN ('manager-1')" not in compiled
        assert "assets.manager_party_id IN ('owner-1')" not in compiled

    def test_build_query_should_only_apply_owner_scope_when_manager_scope_empty(self):
        qb = QueryBuilder(Asset)
        query = qb.build_query(
            party_filter=PartyFilter(
                party_ids=["owner-1"],
                owner_party_ids=["owner-1"],
                manager_party_ids=[],
                filter_mode="owner",
            )
        )
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "assets.owner_party_id IN ('owner-1')" in compiled
        assert "assets.manager_party_id IN" not in compiled

    def test_build_query_should_ignore_legacy_org_fallback_when_owner_scope_has_no_legacy_column(
        self,
    ):
        qb = QueryBuilder(Asset)
        query = qb.build_query(
            party_filter=PartyFilter(
                party_ids=["owner-1"],
                owner_party_ids=["owner-1"],
                owner_legacy_org_ids=["org-owner-legacy-1"],
                manager_party_ids=[],
                filter_mode="owner",
            )
        )
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "assets.owner_party_id IN ('owner-1')" in compiled
        assert "assets.owner_party_id IS NULL" not in compiled
        assert "assets.organization_id IN ('org-owner-legacy-1')" not in compiled

    def test_build_query_should_ignore_legacy_org_fallback_when_manager_scope_has_no_legacy_column(
        self,
    ):
        qb = QueryBuilder(Asset)
        query = qb.build_query(
            party_filter=PartyFilter(
                party_ids=["manager-1"],
                owner_party_ids=[],
                manager_party_ids=["manager-1"],
                manager_legacy_org_ids=["org-manager-legacy-1"],
                filter_mode="manager",
            )
        )
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "assets.manager_party_id IN ('manager-1')" in compiled
        assert "assets.manager_party_id IS NULL" not in compiled
        assert "assets.organization_id IN ('org-manager-legacy-1')" not in compiled

    def test_build_query_should_not_use_party_ids_for_legacy_org_fallback_when_mapping_missing(
        self,
    ):
        qb = QueryBuilder(Asset)
        query = qb.build_query(
            party_filter=PartyFilter(
                party_ids=["manager-party-1"],
                owner_party_ids=[],
                manager_party_ids=["manager-party-1"],
                filter_mode="manager",
            )
        )
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "assets.manager_party_id IN ('manager-party-1')" in compiled
        assert "assets.organization_id IN ('manager-party-1')" not in compiled

    def test_build_query_should_ignore_relation_aware_legacy_org_ids_without_legacy_column(
        self,
    ):
        qb = QueryBuilder(Asset)
        query = qb.build_query(
            party_filter=PartyFilter(
                party_ids=["manager-party-1"],
                owner_party_ids=[],
                manager_party_ids=["manager-party-1"],
                manager_legacy_org_ids=["org-legacy-1"],
                filter_mode="manager",
            )
        )
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "assets.manager_party_id IN ('manager-party-1')" in compiled
        assert "assets.manager_party_id IS NULL" not in compiled
        assert "assets.organization_id IN ('org-legacy-1')" not in compiled

    def test_build_query_should_skip_party_filter_when_model_has_no_party_columns(self):
        qb = QueryBuilder(PropertyCertificate)
        query = qb.build_query(
            party_filter=PartyFilter(
                party_ids=["party-1"],
                legacy_org_ids=["org-legacy-1"],
            )
        )
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "property_certificates.organization_id" not in compiled
        assert "false" not in compiled.lower()
        assert "0 = 1" not in compiled

    def test_build_query_should_not_fail_closed_when_model_has_no_party_columns(self):
        qb = QueryBuilder(PropertyCertificate)
        query = qb.build_query(
            party_filter=PartyFilter(
                party_ids=["party-1"],
            )
        )
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "false" not in compiled.lower()
        assert "0 = 1" not in compiled
