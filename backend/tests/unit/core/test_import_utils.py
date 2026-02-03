"""
Unit tests for import_utils
"""

import importlib

import pytest

from src.core import import_utils
from src.core.environment import DependencyPolicy


class TestSafeImport:
    def test_safe_import_returns_module(self):
        module = import_utils.safe_import("math")
        assert module.sqrt(9) == 3

    def test_safe_import_missing_returns_fallback(self):
        fallback = object()
        result = import_utils.safe_import(
            "missing_module_123", fallback=fallback, silent=True
        )
        assert result is fallback

    def test_safe_import_missing_uses_mock_factory(self):
        sentinel = object()
        called = {"value": False}

        def factory():
            called["value"] = True
            return sentinel

        result = import_utils.safe_import(
            "missing_module_456", mock_factory=factory, silent=True
        )
        assert result is sentinel
        assert called["value"] is True

    def test_safe_import_critical_production_raises(self, monkeypatch):
        monkeypatch.setattr(import_utils, "is_production", lambda: True)
        with pytest.raises(ImportError):
            import_utils.safe_import("missing_module_789", critical=True)

    def test_safe_import_critical_strict_returns_fallback(self, monkeypatch):
        monkeypatch.setattr(import_utils, "is_production", lambda: False)
        monkeypatch.setattr(
            import_utils, "get_dependency_policy", lambda: DependencyPolicy.STRICT
        )
        fallback = object()

        result = import_utils.safe_import(
            "missing_module_000", critical=True, fallback=fallback
        )
        assert result is fallback

    def test_safe_import_non_import_error_is_raised(self, monkeypatch):
        def raise_error(_):
            raise RuntimeError("boom")

        monkeypatch.setattr(importlib, "import_module", raise_error)

        with pytest.raises(RuntimeError):
            import_utils.safe_import("math")


class TestSafeImportFrom:
    def test_safe_import_from_returns_attribute(self):
        attr = import_utils.safe_import_from("math", "sqrt")
        assert attr(16) == 4

    def test_safe_import_from_missing_attribute_returns_fallback(self):
        fallback = object()
        result = import_utils.safe_import_from(
            "math", "missing_attr", fallback=fallback, silent=True
        )
        assert result is fallback

    def test_safe_import_from_critical_production_raises(self, monkeypatch):
        monkeypatch.setattr(import_utils, "is_production", lambda: True)
        with pytest.raises(ImportError):
            import_utils.safe_import_from("math", "missing_attr", critical=True)


class TestHelpers:
    def test_create_mock_registry_methods(self):
        registry = import_utils.create_mock_registry()
        assert registry.register_global_dependency("x") is None
        assert registry.include_all("app") is None

    def test_create_lambda_none(self):
        factory = import_utils.create_lambda_none()
        assert callable(factory)
        assert factory("anything") is None

    def test_optional_import_missing_returns_noop(self):
        @import_utils.optional_import("missing_module_zzz")
        def do_work():
            return "worked"

        assert do_work() is None

    def test_optional_import_existing_returns_function(self):
        @import_utils.optional_import("math")
        def do_work():
            return "worked"

        assert do_work() == "worked"
