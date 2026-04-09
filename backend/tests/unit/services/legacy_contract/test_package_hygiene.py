import re
from importlib.util import find_spec
from pathlib import Path


def _legacy_contract_token(*parts: str, separator: str = "_") -> str:
    return separator.join(parts)


def _legacy_contract_identifier(parts: tuple[str, ...]) -> str:
    return _legacy_contract_token(*parts)


def _legacy_contract_route_token(*parts: str) -> str:
    return "-".join(parts)


def _legacy_contract_class_name(*parts: str) -> str:
    return "".join(parts)


def _legacy_contract_module_path(*parts: str) -> str:
    return ".".join(parts)


def _assert_retired_namespace_or_none(module_name: str) -> None:
    spec = find_spec(module_name)
    if spec is None:
        return

    assert spec.loader is None or spec.loader.__class__.__name__ == "NamespaceLoader"
    search_locations = list(spec.submodule_search_locations or [])
    assert len(search_locations) == 1


def _legacy_contract_wildcard_pattern() -> str:
    return "*" + _legacy_contract_identifier(("rent", "contract")) + "*"


def test_legacy_contract_service_package_should_be_retired() -> None:
    legacy_service_package = _legacy_contract_module_path(
        "src", "services", _legacy_contract_identifier(("rent", "contract"))
    )

    _assert_retired_namespace_or_none(legacy_service_package)


def test_legacy_contract_service_package_should_only_remain_as_empty_namespace() -> None:
    legacy_service_package = _legacy_contract_module_path(
        "src", "services", _legacy_contract_identifier(("rent", "contract"))
    )

    _assert_retired_namespace_or_none(legacy_service_package)


def test_legacy_contract_test_directory_should_be_retired() -> None:
    legacy_dir = Path(__file__).resolve().parents[1] / _legacy_contract_identifier(
        ("rent", "contract")
    )
    legacy_py_files = sorted(path.name for path in legacy_dir.glob("*.py"))

    assert legacy_py_files == []


def test_legacy_contract_excel_retired_test_should_be_co_located() -> None:
    document_test = (
        Path(__file__).resolve().parents[1]
        / "document"
        / "test_legacy_contract_excel_retired.py"
    )

    assert not document_test.exists()


def test_active_document_tests_should_not_keep_legacy_contract_labels() -> None:
    document_dir = Path(__file__).resolve().parents[1] / "document"
    extractor_test = (document_dir / "test_contract_extractor.py").read_text(
        encoding="utf-8"
    )
    pdf_import_test = (document_dir / "test_pdf_import_service.py").read_text(
        encoding="utf-8"
    )

    assert (
        "extract_fixed_" + _legacy_contract_identifier(("rent", "contract", "info"))
        not in extractor_test
    )
    assert "旧 " + _legacy_contract_class_name("Rent", "Contract") not in pdf_import_test


def test_active_tests_should_not_keep_low_value_legacy_contract_labels() -> None:
    tests_root = Path(__file__).resolve().parents[3]
    target_files = {
        "unit/core/test_validators.py": [
            "test_legacy_"
            + _legacy_contract_identifier(("rent", "contract"))
            + "_validator_retired",
            _legacy_contract_class_name("Rent", "ContractValidator"),
        ],
        "unit/core/test_config_files.py": [
            "test_legacy_"
            + _legacy_contract_identifier(("rent", "contract"))
            + "_constants_module_retired",
            _legacy_contract_identifier(("rent", "contract", "constants")),
        ],
        "unit/security/test_request_security.py": [
            "test_get_model_class_"
            + _legacy_contract_identifier(("rent", "contract"))
            + "_alias_retired",
            _legacy_contract_class_name("Rent", "Contract"),
        ],
        "unit/middleware/test_request_logging.py": [
            _legacy_contract_route_token("rental", "contracts"),
        ],
        "unit/services/document/test_contract_extractor.py": [
            _legacy_contract_identifier(("rent", "contract", "info")),
        ],
        "integration/test_contract_groups_modular.py": [
            _legacy_contract_route_token("rental", "contracts"),
        ],
    }

    for relative_path, forbidden_tokens in target_files.items():
        file_text = (tests_root / relative_path).read_text(encoding="utf-8")
        for token in forbidden_tokens:
            assert token not in file_text


def test_active_tests_should_not_keep_legacy_contract_identifiers_in_assertions() -> None:
    tests_root = Path(__file__).resolve().parents[3]
    target_files = {
        "unit/crud/test_asset.py": [
            "has_" + _legacy_contract_identifier(("rent", "contracts")) + "_async",
            "get_assets_with_"
            + _legacy_contract_identifier(("rent", "contracts"))
            + "_async",
            _legacy_contract_identifier(("rent", "contract", "assets")),
        ],
        "unit/middleware/test_authz_dependency.py": [
            _legacy_contract_identifier(("rent", "contracts")),
        ],
        "unit/crud/test_contract_group.py": [
            _legacy_contract_identifier(("rent", "contracts")),
        ],
        "unit/models/test_asset.py": [
            _legacy_contract_identifier(("rent", "contracts")),
        ],
        "unit/api/v1/system/system_monitoring/test_endpoints.py": [
            _legacy_contract_class_name("Rent", "Contract"),
        ],
        "unit/crud/test_field_whitelist.py": [
            "test_legacy_"
            + _legacy_contract_identifier(("rent", "contract"))
            + "_whitelist_retired",
            _legacy_contract_class_name("Rent", "ContractWhitelist"),
        ],
    }

    for relative_path, forbidden_tokens in target_files.items():
        file_text = (tests_root / relative_path).read_text(encoding="utf-8")
        for token in forbidden_tokens:
            assert token not in file_text


def test_retired_contract_tests_should_not_keep_low_value_legacy_labels() -> None:
    tests_root = Path(__file__).resolve().parents[3]
    target_files = {
        "unit/services/legacy_contract/test_legacy_main_service_retired.py": [
            '"""旧 ' + _legacy_contract_identifier(("rent", "contract")),
            "test_legacy_"
            + _legacy_contract_identifier(("rent", "contract"))
            + "_service_modules_should_be_retired",
        ],
        "unit/services/legacy_contract/test_legacy_statistics_service_retired.py": [
            '"""旧 ' + _legacy_contract_identifier(("rent", "contract")),
        ],
        "unit/services/legacy_contract/test_legacy_ledger_service_retired.py": [
            '"""旧 ' + _legacy_contract_identifier(("rent", "contract")),
        ],
        "unit/services/legacy_contract/test_legacy_contract_excel_retired.py": [
            '"""旧 ' + _legacy_contract_identifier(("rent", "contract")),
            "test_legacy_"
            + _legacy_contract_identifier(("rent", "contract"))
            + "_excel_service_module_should_be_retired",
        ],
        "unit/api/v1/test_legacy_contract_runtime_retired.py": [
            '"""旧 ' + _legacy_contract_route_token("rental", "contracts"),
            "test_legacy_"
            + _legacy_contract_identifier(("rent", "contracts"))
            + "_api_package_should_be_retired",
        ],
    }

    for relative_path, forbidden_tokens in target_files.items():
        file_text = (tests_root / relative_path).read_text(encoding="utf-8")
        for token in forbidden_tokens:
            assert token not in file_text


def test_tests_tree_should_not_keep_legacy_contract_cache_files() -> None:
    tests_root = Path(__file__).resolve().parents[3]
    legacy_paths = sorted(
        str(path.relative_to(tests_root))
        for path in tests_root.rglob(_legacy_contract_wildcard_pattern())
        if path.is_file() and path.suffix == ".py"
    )

    assert legacy_paths == []


def test_src_tree_should_not_keep_legacy_contract_cache_files() -> None:
    src_root = Path(__file__).resolve().parents[4] / "src"
    legacy_paths = sorted(
        str(path.relative_to(src_root))
        for path in src_root.rglob(_legacy_contract_wildcard_pattern())
        if path.is_file() and path.suffix == ".py"
    )

    assert legacy_paths == []


def test_active_backend_python_files_should_not_keep_legacy_contract_tokens() -> None:
    backend_root = Path(__file__).resolve().parents[4]
    whole_word_tokens = [
        _legacy_contract_class_name("Rent", "ContractWhitelist"),
        _legacy_contract_class_name("Rent", "Contract"),
        _legacy_contract_identifier(("rent", "contract", "assets")),
        _legacy_contract_identifier(("rent", "contracts")),
        _legacy_contract_identifier(("rent", "contract", "constants")),
        "has_" + _legacy_contract_identifier(("rent", "contracts")) + "_async",
        "get_assets_with_"
        + _legacy_contract_identifier(("rent", "contracts"))
        + "_async",
        _legacy_contract_identifier(("rent", "contract", "info")),
    ]
    plain_tokens = [
        _legacy_contract_route_token("rental", "contracts"),
        _legacy_contract_module_path(
            "src", "services", _legacy_contract_identifier(("rent", "contract"))
        ),
        _legacy_contract_module_path(
            "src", "api", "v1", _legacy_contract_identifier(("rent", "contracts"))
        ),
    ]
    legacy_pattern = re.compile(
        "|".join(
            [rf"\b{re.escape(token)}\b" for token in whole_word_tokens]
            + [re.escape(token) for token in plain_tokens]
        )
    )
    excluded_paths = {
        Path("src/scripts/migration"),
        Path("tests/unit/services/legacy_contract"),
        Path("tests/unit/api/v1/test_legacy_contract_runtime_retired.py"),
        Path("tests/unit/test_legacy_contract_workflow_suites_retired.py"),
        Path("tests/unit/migration"),
        Path("tests/integration/test_postgresql_migration.py"),
    }
    legacy_hits: list[str] = []

    for relative_root in (Path("src"), Path("tests")):
        for path in (backend_root / relative_root).rglob("*.py"):
            relative_path = path.relative_to(backend_root)
            if any(
                relative_path == excluded_path
                or excluded_path in relative_path.parents
                for excluded_path in excluded_paths
            ):
                continue

            file_text = path.read_text(encoding="utf-8")
            if legacy_pattern.search(file_text):
                legacy_hits.append(str(relative_path))

    assert legacy_hits == []


def test_hygiene_guard_should_not_keep_raw_legacy_contract_tokens() -> None:
    source_text = Path(__file__).read_text(encoding="utf-8")
    forbidden_tokens = [
        "test_legacy_" + _legacy_contract_token("rent", "contract") + "_validator_retired",
        _legacy_contract_class_name("Rent", "ContractValidator"),
        _legacy_contract_identifier(("rent", "contract", "constants")),
        _legacy_contract_class_name("Rent", "ContractWhitelist"),
        _legacy_contract_class_name("Rent", "Contract"),
        _legacy_contract_identifier(("rent", "contract", "assets")),
        _legacy_contract_identifier(("rent", "contracts")),
        "has_" + _legacy_contract_identifier(("rent", "contracts")) + "_async",
        "get_assets_with_" + _legacy_contract_identifier(("rent", "contracts")) + "_async",
        _legacy_contract_route_token("rental", "contracts"),
        _legacy_contract_identifier(("rent", "contract", "info")),
    ]

    for token in forbidden_tokens:
        assert token not in source_text
