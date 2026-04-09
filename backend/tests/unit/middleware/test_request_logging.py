from fastapi import FastAPI

from src.middleware.request_logging import RequestLoggingMiddleware


def test_map_module_name_uses_contract_modules_for_rental_management() -> None:
    middleware = RequestLoggingMiddleware(FastAPI())

    assert middleware._map_module_name("contract-groups") == "租赁管理"
    assert middleware._map_module_name("contracts") == "租赁管理"
    assert middleware._map_module_name("legacy-contracts") == "legacy-contracts"


def test_map_action_uses_read_for_get_requests() -> None:
    middleware = RequestLoggingMiddleware(FastAPI())

    assert middleware._map_action("GET", ["assets"]) == "read"
    assert middleware._map_action_name("read") == "查看"
