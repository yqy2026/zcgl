"""
Unit tests for dependency_checker
"""

import pytest

from src.core import dependency_checker as dependency_checker_module
from src.core.dependency_checker import DependencyChecker
from src.core.exception_handler import ConfigurationError


class TestDependencyChecker:
    def test_check_all_success_non_production(self, monkeypatch):
        checker = DependencyChecker()
        checker.register_critical("db", lambda: True)
        checker.register_optional("redis", lambda: False)
        monkeypatch.setattr(dependency_checker_module, "is_production", lambda: False)

        assert checker.check_all() is True

    def test_check_all_failure_non_production(self, monkeypatch):
        checker = DependencyChecker()
        checker.register_critical("db", lambda: False)
        checker.register_optional("redis", lambda: True)
        monkeypatch.setattr(dependency_checker_module, "is_production", lambda: False)

        assert checker.check_all() is False

    def test_check_all_failure_production_raises(self, monkeypatch):
        checker = DependencyChecker()
        checker.register_critical("db", lambda: False)
        monkeypatch.setattr(dependency_checker_module, "is_production", lambda: True)

        with pytest.raises(ConfigurationError):
            checker.check_all()

    def test_check_all_exception_in_check_fn(self, monkeypatch):
        def raise_error():
            raise ValueError("boom")

        checker = DependencyChecker()
        checker.register_critical("db", raise_error)
        monkeypatch.setattr(dependency_checker_module, "is_production", lambda: False)

        assert checker.check_all() is False
