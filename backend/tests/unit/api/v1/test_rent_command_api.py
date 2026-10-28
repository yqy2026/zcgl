"""Rent commands use write capability and durable request identifiers."""

from pydantic_core import PydanticUndefined

from src.api.v1 import rent_ledgers, terminal_contracts, upstream_contracts


def test_rent_write_routes_require_asset_operations_write():
    routes = [
        route
        for module in (rent_ledgers, upstream_contracts, terminal_contracts)
        for route in module.router.routes
        if route.path.startswith("/rent-") or "/rent-schedule-correction" in route.path
    ]
    assert len(routes) == 8
    for route in routes:
        assert route.methods == {"POST"}
        guards = [
            dependency.call
            for dependency in route.dependant.dependencies
            if type(dependency.call).__name__ == "AuthzPermissionChecker"
        ]
        assert len(guards) == 1
        assert guards[0].action == "write"
        assert guards[0].resource_type == "asset_ops"
        if not route.path.endswith("/preview"):
            headers = {param.alias: param for param in route.dependant.header_params}
            assert headers["Idempotency-Key"].default is PydanticUndefined
