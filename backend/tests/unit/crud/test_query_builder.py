from src.crud.query_builder import QueryBuilder
from src.models.asset import Asset  # Using Asset as a test model


class TestQueryBuilder:
    def test_build_query_basic(self):
        qb = QueryBuilder(Asset)
        query = qb.build_query()
        compiled = str(query.compile())
        assert "SELECT assets.id" in compiled or "SELECT assets." in compiled

    def test_build_query_with_filters(self):
        qb = QueryBuilder(Asset)
        filters = {
            "property_name": "Test Asset",
            "min_actual_property_area": 100,
            "max_actual_property_area": 200,
            "id__in": ["1", "2"],
        }
        query = qb.build_query(filters=filters)
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "assets.property_name = 'Test Asset'" in compiled
        assert "assets.actual_property_area >= 100" in compiled
        assert "assets.actual_property_area <= 200" in compiled
        assert "assets.id IN ('1', '2')" in compiled

    def test_build_query_search(self):
        qb = QueryBuilder(Asset)
        search = "Building"
        search_fields = ["property_name", "address"]
        query = qb.build_query(search_query=search, search_fields=search_fields)
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert (
            "lower(assets.property_name) LIKE lower('%Building%')" in compiled
            or "assets.property_name ILIKE" in compiled
        )
        assert (
            "lower(assets.address) LIKE lower('%Building%')" in compiled
            or "assets.address ILIKE" in compiled
        )
        assert "OR" in compiled

    def test_build_count_query(self):
        qb = QueryBuilder(Asset)
        filters = {"property_name": "Test"}
        query = qb.build_count_query(filters=filters)
        compiled = str(query.compile(compile_kwargs={"literal_binds": True}))

        assert "count" in compiled.lower()
        assert "assets.property_name = 'Test'" in compiled
