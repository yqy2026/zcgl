from importlib.util import find_spec


def test_legacy_contract_workflow_test_suites_retired() -> None:
    """The legacy M1 contract suites must stay retired.

    Note: ``tests/e2e/test_contract_workflow_e2e.py`` no longer belongs to the
    retired legacy suite — since 2026-08-15 that filename carries the new
    M2/M3 contract workflow e2e (REQ-RNT-001/005/006), so only the legacy
    integration suites remain name-guarded here.
    """
    assert find_spec("tests.integration.test_contract_workflow") is None
    assert find_spec("tests.integration.services.test_contract_renewal_service") is None
