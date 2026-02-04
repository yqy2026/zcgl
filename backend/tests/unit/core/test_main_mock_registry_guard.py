"""
Tests for production guardrails in src.main.
"""

from __future__ import annotations

import importlib
import sys
import types

import pytest

from src.core.exception_handler import ConfigurationError


def _clear_modules(module_names: list[str]) -> None:
    for module_name in module_names:
        sys.modules.pop(module_name, None)


def test_production_rejects_allow_mock_registry(monkeypatch):
    _clear_modules(["src.main", "src.core.config"])
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOW_MOCK_REGISTRY", "true")

    with pytest.raises(ConfigurationError, match="ALLOW_MOCK_REGISTRY"):
        importlib.import_module("src.main")

    _clear_modules(["src.main", "src.core.config"])


def test_production_missing_registry_attributes_raises(monkeypatch):
    _clear_modules(["src.main", "src.core.config"])
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("ALLOW_MOCK_REGISTRY", raising=False)

    dummy_registry = types.ModuleType("src.core.router_registry")
    original_registry = sys.modules.get("src.core.router_registry")
    sys.modules["src.core.router_registry"] = dummy_registry

    try:
        with pytest.raises(ConfigurationError, match="route_registry"):
            importlib.import_module("src.main")
    finally:
        if original_registry is None:
            sys.modules.pop("src.core.router_registry", None)
        else:
            sys.modules["src.core.router_registry"] = original_registry
        _clear_modules(["src.main", "src.core.config"])
