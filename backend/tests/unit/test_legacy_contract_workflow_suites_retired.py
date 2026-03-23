from importlib.util import find_spec


def test_legacy_contract_workflow_test_suites_retired() -> None:
    assert find_spec("tests.integration.test_contract_workflow") is None
    assert find_spec("tests.integration.services.test_contract_renewal_service") is None
    assert find_spec("tests.e2e.test_contract_workflow_e2e") is None
