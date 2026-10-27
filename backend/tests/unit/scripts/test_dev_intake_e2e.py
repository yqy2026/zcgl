from __future__ import annotations

import pytest

from scripts import dev_intake_e2e


def test_walkthrough_password_comes_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("V5_WALKTHROUGH_PASSWORD", "configured-at-runtime")

    assert dev_intake_e2e.get_walkthrough_password() == "configured-at-runtime"


def test_walkthrough_password_fails_loud_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("V5_WALKTHROUGH_PASSWORD", raising=False)

    with pytest.raises(RuntimeError, match="V5_WALKTHROUGH_PASSWORD"):
        dev_intake_e2e.get_walkthrough_password()
