"""Architecture guardrails for API route registration."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
API_V1_INIT = REPO_ROOT / "src" / "api" / "v1" / "__init__.py"
API_V1_DIR = REPO_ROOT / "src" / "api" / "v1"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_registry_owned_routes_should_not_be_included_by_api_router() -> None:
    """route_registry-owned routers must not gain a second aggregate alias."""
    api_v1_source = _read(API_V1_INIT)

    registry_owned_modules = {
        "party": API_V1_DIR / "party.py",
        "authz": API_V1_DIR / "authz.py",
        "collection": API_V1_DIR / "system" / "collection.py",
    }

    for module_name, module_path in registry_owned_modules.items():
        module_source = _read(module_path)
        assert "route_registry.register_router(" in module_source
        assert f"include_router({module_name}_router" not in api_v1_source

    assert "from .system.collection import router as collection_router" not in api_v1_source
