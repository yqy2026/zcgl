"""
SecurityService removal tests.

Ensure deprecated SecurityService is not importable or exported.
"""

import importlib

import pytest


def test_security_service_module_removed() -> None:
    """security_service module should not be importable."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("src.services.core.security_service")


def test_security_service_not_exported_from_services() -> None:
    """SecurityService should not be exported from src.services."""
    services = importlib.import_module("src.services")
    assert "SecurityService" not in getattr(services, "__all__", [])
    with pytest.raises(AttributeError):
        getattr(services, "SecurityService")


def test_security_service_not_exported_from_core_services() -> None:
    """SecurityService should not be exported from src.services.core."""
    core_services = importlib.import_module("src.services.core")
    assert "SecurityService" not in getattr(core_services, "__all__", [])
    with pytest.raises(AttributeError):
        getattr(core_services, "SecurityService")
