from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

import pytest


def _load_module() -> ModuleType:
    script_path = (
        Path(__file__).resolve().parents[4] / "scripts" / "check_query_param_drift.py"
    )
    spec = spec_from_file_location("check_query_param_drift", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_repository_query_param_contracts_have_no_drift() -> None:
    module = _load_module()

    assert module.check_all_contracts() == []
    assert module.run() == 0


def _fixture_mapping(module: ModuleType, tmp_path: Path):
    backend_file = tmp_path / "backend.py"
    frontend_type_file = tmp_path / "types.ts"
    service_file = tmp_path / "service.ts"
    mapping = module.ContractMapping(
        name="fixture_parties",
        backend_file=backend_file,
        backend_symbol="list_parties",
        backend_route_symbol=None,
        backend_route_path=None,
        backend_route_dependency=None,
        frontend_type_file=frontend_type_file,
        frontend_type="PartyListParams",
        service_file=service_file,
        service_method="getParties",
        request_method="get",
        request_path="/parties",
    )
    return mapping, backend_file, frontend_type_file, service_file


def _write_fixture(
    backend_file: Path,
    frontend_type_file: Path,
    service_file: Path,
    *,
    backend_fields: tuple[str, ...] = ("skip", "limit", "review_status"),
    frontend_fields: tuple[str, ...] = ("skip", "limit", "review_status"),
    request_fields: tuple[str, ...] = ("skip", "limit", "review_status"),
) -> None:
    backend_params = "\n".join(
        f"    {field}: str | None = Query(None)," for field in backend_fields
    )
    type_params = "\n".join(f"  {field}?: string;" for field in frontend_fields)
    request_params = "\n".join(
        f"      {field}: params.{field}," for field in request_fields
    )

    backend_file.write_text(
        "from fastapi import Query\n\n"
        "async def list_parties(\n"
        f"{backend_params}\n"
        "):\n"
        "    return []\n",
        encoding="utf-8",
    )
    frontend_type_file.write_text(
        f"export interface PartyListParams {{\n{type_params}\n}}\n",
        encoding="utf-8",
    )
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    const requestParams = {\n"
        f"{request_params}\n"
        "    };\n"
        "    return apiClient.get('/parties', { params: requestParams });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )


def test_backend_only_query_field_is_reported(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(
        backend_file,
        frontend_type_file,
        service_file,
        backend_fields=("skip", "limit", "review_status", "status"),
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "backend_only" and issue.field == "status" for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_keyword_only_backend_query_field_is_reported(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    backend_file.write_text(
        "from fastapi import Query\n\n"
        "async def list_parties(\n"
        "    skip: str | None = Query(None),\n"
        "    limit: str | None = Query(None),\n"
        "    review_status: str | None = Query(None),\n"
        "    *,\n"
        "    status: str | None = Query(None),\n"
        "):\n"
        "    return []\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "backend_only" and issue.field == "status" for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_dynamic_forwarder_that_drops_a_named_field_fails_loudly(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "const buildParams = (params: PartyListParams) => {\n"
        "  const normalized: Record<string, string> = {};\n"
        "  Object.entries(params).forEach(([key, value]) => {\n"
        "    if (key !== 'review_status' || value == null) {\n"
        "      return;\n"
        "    }\n"
        "    normalized[key] = value;\n"
        "  });\n"
        "  return normalized;\n"
        "};\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    return apiClient.get('/parties', { params: buildParams(params) });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error"
        and issue.path == service_file
        and "cannot verify complete dynamic forwarding" in issue.detail
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_decoy_request_params_not_used_by_outbound_request_fails_loudly(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    const requestParams = {\n"
        "      skip: params.skip,\n"
        "      limit: params.limit,\n"
        "      review_status: params.review_status,\n"
        "    };\n"
        "    const outboundParams = {\n"
        "      skip: params.skip,\n"
        "      limit: params.limit,\n"
        "    };\n"
        "    return apiClient.get('/parties', { params: outboundParams });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "request_whitelist_missing" and issue.field == "review_status"
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_shadowed_outbound_request_object_fails_loudly(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    const requestParams = {\n"
        "      skip: params.skip,\n"
        "      limit: params.limit,\n"
        "      review_status: params.review_status,\n"
        "    };\n"
        "    {\n"
        "      const requestParams = {\n"
        "        skip: params.skip,\n"
        "        limit: params.limit,\n"
        "      };\n"
        "      return apiClient.get('/parties', { params: requestParams });\n"
        "    }\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error" and "nested outbound request scope" in issue.detail
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_outbound_request_object_parameter_shadowing_fails_loudly(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    const requestParams = {\n"
        "      skip: params.skip,\n"
        "      limit: params.limit,\n"
        "      review_status: params.review_status,\n"
        "    };\n"
        "    function send(requestParams: PartyListParams) {\n"
        "      return apiClient.get('/parties', { params: requestParams });\n"
        "    }\n"
        "    return send({ skip: '0', limit: '20' });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error" and "nested outbound request scope" in issue.detail
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_outbound_request_object_complex_parameter_shadowing_fails_loudly(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for nested_parameter in (
        "requestParams = { skip: '0', limit: '20' }",
        "{ requestParams }",
    ):
        service_file.write_text(
            "import { apiClient } from '@/api/client';\n"
            "import type { PartyListParams } from './types';\n\n"
            "export class PartyService {\n"
            "  async getParties(params: PartyListParams = {}) {\n"
            "    const requestParams = {\n"
            "      skip: params.skip,\n"
            "      limit: params.limit,\n"
            "      review_status: params.review_status,\n"
            "    };\n"
            f"    function send({nested_parameter}) {{\n"
            "      return apiClient.get('/parties', { params: requestParams });\n"
            "    }\n"
            "    return send({ skip: '0', limit: '20' });\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        issues = module.check_mapping(mapping)

        assert any(
            issue.kind == "parse_error"
            and "nested outbound request scope" in issue.detail
            for issue in issues
        )
        assert module.run((mapping,)) == 1


def test_generic_outbound_request_object_parameter_shadowing_fails_loudly(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for function_declaration in (
        "function send<T>(requestParams: PartyListParams)",
        "function* send(requestParams: PartyListParams)",
    ):
        service_file.write_text(
            "import { apiClient } from '@/api/client';\n"
            "import type { PartyListParams } from './types';\n\n"
            "export class PartyService {\n"
            "  async getParties(params: PartyListParams = {}) {\n"
            "    const requestParams = {\n"
            "      skip: params.skip,\n"
            "      limit: params.limit,\n"
            "      review_status: params.review_status,\n"
            "    };\n"
            f"    {function_declaration} {{\n"
            "      return apiClient.get('/parties', { params: requestParams });\n"
            "    }\n"
            "    return send({ skip: '0', limit: '20' });\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        issues = module.check_mapping(mapping)

        assert any(
            issue.kind == "parse_error"
            and "nested outbound request scope" in issue.detail
            for issue in issues
        )
        assert module.run((mapping,)) == 1


def test_nested_outbound_request_scope_fails_loudly(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for nested_request in (
        "    function send() {\n"
        "      return apiClient.get('/parties', { params: requestParams });\n"
        "    }\n"
        "    return send();\n",
        "    try {\n"
        "      const send = () =>\n"
        "        apiClient.get('/parties', { params: requestParams });\n"
        "      return send();\n"
        "    } catch (error) {\n"
        "      throw error;\n"
        "    }\n",
    ):
        service_file.write_text(
            "import { apiClient } from '@/api/client';\n"
            "import type { PartyListParams } from './types';\n\n"
            "export class PartyService {\n"
            "  async getParties(params: PartyListParams = {}) {\n"
            "    const requestParams = {\n"
            "      skip: params.skip,\n"
            "      limit: params.limit,\n"
            "      review_status: params.review_status,\n"
            "    };\n"
            f"{nested_request}"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        issues = module.check_mapping(mapping)

        assert any(
            issue.kind == "parse_error"
            and "nested outbound request scope" in issue.detail
            for issue in issues
        )
        assert module.run((mapping,)) == 1


def test_direct_try_outbound_request_scope_is_supported(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    try {\n"
        "      const requestParams = {\n"
        "        skip: params.skip,\n"
        "        limit: params.limit,\n"
        "        review_status: params.review_status,\n"
        "      };\n"
        "      return apiClient.get('/parties', { params: requestParams });\n"
        "    } catch (error) {\n"
        "      throw error;\n"
        "    }\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    assert module.check_mapping(mapping) == []
    assert module.run((mapping,)) == 0


def test_object_method_outbound_request_object_parameter_shadowing_fails_loudly(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    const requestParams = {\n"
        "      skip: params.skip,\n"
        "      limit: params.limit,\n"
        "      review_status: params.review_status,\n"
        "    };\n"
        "    const requests = {\n"
        "      send(requestParams: PartyListParams) {\n"
        "        return apiClient.get('/parties', { params: requestParams });\n"
        "      },\n"
        "    };\n"
        "    return requests.send({ skip: '0', limit: '20' });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error" and "nested outbound request scope" in issue.detail
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_shadowed_dynamic_helper_fails_loudly(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "const buildParams = (params: PartyListParams) => {\n"
        "  const normalized: Record<string, string> = {};\n"
        "  Object.entries(params).forEach(([key, value]) => {\n"
        "    if (value == null || value === '') {\n"
        "      return;\n"
        "    }\n"
        "    normalized[key] = value;\n"
        "  });\n"
        "  return normalized;\n"
        "};\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    const buildParams = (_params: PartyListParams) => ({ skip: params.skip });\n"
        "    return apiClient.get('/parties', { params: buildParams(params) });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error"
        and "cannot verify complete dynamic forwarding" in issue.detail
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_direct_params_forwarding_is_accepted(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    return apiClient.get('/parties', { params: params });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    assert module.check_mapping(mapping) == []
    assert module.run((mapping,)) == 0


def test_direct_params_forwarding_requires_the_mapped_method_input(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(input: PartyListParams = {}) {\n"
        "    const params = { skip: input.skip, limit: input.limit };\n"
        "    return apiClient.get('/parties', { params: params });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error" and "mapped Params type" in issue.detail
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_direct_params_forwarding_requires_the_mapped_params_type(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "type OtherParams = PartyListParams;\n\n"
        "export class PartyService {\n"
        "  async getParties(params: OtherParams = {}) {\n"
        "    const requestParams = {\n"
        "      skip: params.skip,\n"
        "      limit: params.limit,\n"
        "      review_status: params.review_status,\n"
        "    };\n"
        "    return apiClient.get('/parties', { params: requestParams });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error" and "mapped Params type" in issue.detail
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_direct_params_forwarding_requires_mapped_params_type_binding(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for declaration in (
        "import type { PartyListParams } from './other';\n\n",
        "type PartyListParams = {\n"
        "  skip?: string;\n"
        "  limit?: string;\n"
        "  review_status?: string;\n"
        "};\n\n",
    ):
        service_file.write_text(
            "import { apiClient } from '@/api/client';\n"
            f"{declaration}"
            "export class PartyService {\n"
            "  async getParties(params: PartyListParams = {}) {\n"
            "    const requestParams = {\n"
            "      skip: params.skip,\n"
            "      limit: params.limit,\n"
            "      review_status: params.review_status,\n"
            "    };\n"
            "    return apiClient.get('/parties', { params: requestParams });\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        issues = module.check_mapping(mapping)

        assert any(
            issue.kind == "parse_error" and "mapped Params type binding" in issue.detail
            for issue in issues
        )
        assert module.run((mapping,)) == 1


def test_same_file_params_type_declaration_is_not_a_proven_binding(
    tmp_path: Path,
) -> None:
    """A params type declared inside the service file must still be proven bound.

    The type must live in the mapped type file and be imported by the service;
    a same-file declaration gives the gate nothing to bind and must fail loudly
    instead of silently passing.
    """
    module = _load_module()
    mapping, backend_file, _, _ = _fixture_mapping(module, tmp_path)
    shared_file = tmp_path / "shared.ts"
    mapping = module.ContractMapping(
        name=mapping.name,
        backend_file=backend_file,
        backend_symbol=mapping.backend_symbol,
        backend_route_symbol=mapping.backend_route_symbol,
        backend_route_path=mapping.backend_route_path,
        backend_route_dependency=mapping.backend_route_dependency,
        frontend_type_file=shared_file,
        frontend_type=mapping.frontend_type,
        service_file=shared_file,
        service_method=mapping.service_method,
        request_method=mapping.request_method,
        request_path=mapping.request_path,
    )
    backend_file.write_text(
        "from fastapi import APIRouter, Query\n\n"
        "router = APIRouter()\n\n"
        "@router.get('/parties')\n"
        "async def list_parties(\n"
        "    skip: str | None = Query(None),\n"
        "    limit: str | None = Query(None),\n"
        "    review_status: str | None = Query(None),\n"
        "):\n"
        "    return []\n",
        encoding="utf-8",
    )
    shared_file.write_text(
        "import { apiClient } from '@/api/client';\n\n"
        "export interface PartyListParams {\n"
        "  skip?: string;\n"
        "  limit?: string;\n"
        "  review_status?: string;\n"
        "}\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    const requestParams = {\n"
        "      skip: params.skip,\n"
        "      limit: params.limit,\n"
        "      review_status: params.review_status,\n"
        "    };\n"
        "    return apiClient.get('/parties', { params: requestParams });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error" and "mapped Params type binding" in issue.detail
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_direct_params_forwarding_rejects_prior_reassignment(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    params = { skip: params.skip, limit: params.limit };\n"
        "    return apiClient.get('/parties', { params: params });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error"
        and "cannot verify direct params forwarding" in issue.detail
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_dynamic_forwarder_requires_the_mapped_method_input(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "const params = { skip: '0', limit: '20' };\n\n"
        "const buildParams = (_params: PartyListParams) => {\n"
        "  const normalized: Record<string, string> = {};\n"
        "  Object.entries(params).forEach(([key, value]) => {\n"
        "    if (value == null || value === '') {\n"
        "      return;\n"
        "    }\n"
        "    normalized[key] = value;\n"
        "  });\n"
        "  return normalized;\n"
        "};\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    return apiClient.get('/parties', { params: buildParams(params) });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error"
        and "cannot verify complete dynamic forwarding" in issue.detail
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_dynamic_forwarder_rejects_an_imported_binding(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n"
        "import { buildParams } from './other';\n\n"
        "const unrelated = () => {\n"
        "  const buildParams = (params: PartyListParams) => {\n"
        "    const normalized: Record<string, string> = {};\n"
        "    Object.entries(params).forEach(([key, value]) => {\n"
        "      if (value == null || value === '') {\n"
        "        return;\n"
        "      }\n"
        "      normalized[key] = value;\n"
        "    });\n"
        "    return normalized;\n"
        "  };\n"
        "  return buildParams;\n"
        "};\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    return apiClient.get('/parties', { params: buildParams(params) });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error"
        and "cannot verify complete dynamic forwarding" in issue.detail
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_non_query_fastapi_parameter_is_excluded(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    backend_file.write_text(
        "from fastapi import Header, Query\n\n"
        "async def list_parties(\n"
        "    skip: str | None = Query(None),\n"
        "    limit: str | None = Query(None),\n"
        "    review_status: str | None = Query(None),\n"
        "    *,\n"
        "    request_id: str | None = Header(None),\n"
        "):\n"
        "    return []\n",
        encoding="utf-8",
    )

    assert module.check_mapping(mapping) == []
    assert module.run((mapping,)) == 0


def test_request_object_unsupported_property_shapes_fail_loudly(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for unsupported_property in (
        "...extra",
        "[dynamicKey]: params.review_status",
        "review_status",
    ):
        service_file.write_text(
            "import { apiClient } from '@/api/client';\n"
            "import type { PartyListParams } from './types';\n\n"
            "export class PartyService {\n"
            "  async getParties(params: PartyListParams = {}) {\n"
            "    const requestParams = {\n"
            "      skip: params.skip,\n"
            "      limit: params.limit,\n"
            f"      {unsupported_property},\n"
            "    };\n"
            "    return apiClient.get('/parties', { params: requestParams });\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        issues = module.check_mapping(mapping)

        assert any(issue.kind == "parse_error" for issue in issues)
        assert module.run((mapping,)) == 1


def test_outbound_config_spread_that_can_override_params_fails_loudly(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    const requestParams = {\n"
        "      skip: params.skip,\n"
        "      limit: params.limit,\n"
        "      review_status: params.review_status,\n"
        "    };\n"
        "    const laterConfig = { params: { skip: params.skip, limit: params.limit } };\n"
        "    return apiClient.get('/parties', { params: requestParams, ...laterConfig });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(issue.kind == "parse_error" for issue in issues)
    assert module.run((mapping,)) == 1


def test_whitelist_rejects_method_input_mutated_before_object_creation(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for mutation in (
        "    delete params.review_status;\n",
        "    params.review_status = undefined;\n",
        "    Object.assign(params, { review_status: undefined });\n",
        "    Reflect.set(params, 'review_status', undefined);\n",
        "    Reflect.deleteProperty(params, 'review_status');\n",
    ):
        service_file.write_text(
            "import { apiClient } from '@/api/client';\n"
            "import type { PartyListParams } from './types';\n\n"
            "export class PartyService {\n"
            "  async getParties(params: PartyListParams = {}) {\n"
            f"{mutation}"
            "    const requestParams = {\n"
            "      skip: params.skip,\n"
            "      limit: params.limit,\n"
            "      review_status: params.review_status,\n"
            "    };\n"
            "    return apiClient.get('/parties', { params: requestParams });\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        issues = module.check_mapping(mapping)

        assert any(issue.kind == "parse_error" for issue in issues)
        assert module.run((mapping,)) == 1


def test_backend_duplicate_or_nested_mapped_symbols_fail_loudly(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for backend_source in (
        "from fastapi import Query\n\n"
        "async def list_parties(\n"
        "    skip: str | None = Query(None),\n"
        "    limit: str | None = Query(None),\n"
        "    review_status: str | None = Query(None),\n"
        "):\n"
        "    return []\n\n"
        "async def list_parties(\n"
        "    skip: str | None = Query(None),\n"
        "    limit: str | None = Query(None),\n"
        "    status: str | None = Query(None),\n"
        "):\n"
        "    return []\n",
        "from fastapi import Query\n\n"
        "def wrapper():\n"
        "    async def list_parties(\n"
        "        skip: str | None = Query(None),\n"
        "        limit: str | None = Query(None),\n"
        "        review_status: str | None = Query(None),\n"
        "    ):\n"
        "        return []\n",
    ):
        backend_file.write_text(backend_source, encoding="utf-8")

        issues = module.check_mapping(mapping)

        assert any(issue.kind == "parse_error" for issue in issues)
        assert module.run((mapping,)) == 1


def test_backend_query_keyword_expansion_fails_loudly(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    backend_file.write_text(
        "from fastapi import Query\n\n"
        "async def list_parties(\n"
        "    skip: str | None = Query(None),\n"
        "    limit: str | None = Query(None),\n"
        "    review_status: str | None = Query(None, **{'alias': 'reviewStatus'}),\n"
        "):\n"
        "    return []\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(issue.kind == "parse_error" for issue in issues)
    assert module.run((mapping,)) == 1


def test_typescript_interface_locations_use_the_mapped_interface_body(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    frontend_type_file.write_text(
        "export interface OtherParams {\n"
        "  skip?: string;\n"
        "  limit?: string;\n"
        "  review_status?: string;\n"
        "}\n\n"
        "export interface PartyListParams {\n"
        "  skip?: string;\n"
        "  limit?: string;\n"
        "  review_status?: string;\n"
        "}\n",
        encoding="utf-8",
    )

    fields = module.parse_typescript_interface_fields(
        frontend_type_file, "PartyListParams"
    )

    assert fields["skip"] == 8
    assert fields["limit"] == 9
    assert fields["review_status"] == 10


def test_typescript_parse_failure_is_reported_with_source_location(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    frontend_type_file.write_text(
        "export interface PartyListParams {\n  skip?: string;\n  /* unterminated\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error"
        and issue.path == frontend_type_file
        and issue.line == 3
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_annotated_fastapi_query_parameter_is_reported(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    backend_file.write_text(
        "from typing import Annotated\n\n"
        "from fastapi import Query\n\n"
        "async def list_parties(\n"
        "    skip: str | None = Query(None),\n"
        "    limit: str | None = Query(None),\n"
        "    review_status: str | None = Query(None),\n"
        "    *,\n"
        "    status: Annotated[str, Query()],\n"
        "):\n"
        "    return []\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "backend_only" and issue.field == "status" for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_dynamic_forwarder_rejects_reassigned_method_input(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "const buildParams = (params: PartyListParams) => {\n"
        "  const normalized: Record<string, string> = {};\n"
        "  Object.entries(params).forEach(([key, value]) => {\n"
        "    if (value == null || value === '') {\n"
        "      return;\n"
        "    }\n"
        "    normalized[key] = value;\n"
        "  });\n"
        "  return normalized;\n"
        "};\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    params = { skip: params.skip, limit: params.limit };\n"
        "    return apiClient.get('/parties', { params: buildParams(params) });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error"
        and "cannot verify complete dynamic forwarding" in issue.detail
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_request_whitelist_requires_an_immutable_object(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    let requestParams = {\n"
        "      skip: params.skip,\n"
        "      limit: params.limit,\n"
        "      review_status: params.review_status,\n"
        "    };\n"
        "    requestParams = { skip: params.skip, limit: params.limit };\n"
        "    return apiClient.get('/parties', { params: requestParams });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(issue.kind == "parse_error" for issue in issues)
    assert module.run((mapping,)) == 1


def test_conditional_spread_with_multiple_fields_fails_loudly(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    const requestParams = {\n"
        "      skip: params.skip,\n"
        "      ...(params.review_status != null\n"
        "        ? { review_status: params.review_status, limit: params.limit }\n"
        "        : {}),\n"
        "    };\n"
        "    return apiClient.get('/parties', { params: requestParams });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(issue.kind == "parse_error" for issue in issues)
    assert module.run((mapping,)) == 1


def test_drift_report_lists_both_compared_sources(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(
        backend_file,
        frontend_type_file,
        service_file,
        backend_fields=("skip", "limit", "review_status", "status"),
    )

    report = module.format_issues(module.check_mapping(mapping))

    assert str(backend_file) in report
    assert str(frontend_type_file) in report
    assert f"{backend_file}:" in report
    assert f"compared with {frontend_type_file})" in report


def test_frontend_only_param_is_reported(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(
        backend_file,
        frontend_type_file,
        service_file,
        frontend_fields=("skip", "limit", "review_status", "status"),
        request_fields=("skip", "limit", "review_status", "status"),
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "frontend_only" and issue.field == "status" for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_request_whitelist_omission_is_reported_and_fails_gate(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(
        backend_file,
        frontend_type_file,
        service_file,
        request_fields=("skip", "limit"),
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "request_whitelist_missing" and issue.field == "review_status"
        for issue in issues
    )
    report = module.format_issues(issues)
    assert "fixture_parties request_whitelist_missing: review_status" in report
    assert f"{service_file}:10" in report
    assert f"compared with {frontend_type_file}:4" in report
    assert module.run((mapping,)) == 1


def test_request_whitelist_only_field_is_reported(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(
        backend_file,
        frontend_type_file,
        service_file,
        request_fields=("skip", "limit", "review_status", "status"),
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "request_whitelist_only" and issue.field == "status"
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_parse_failure_is_reported_with_source_location(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    backend_file.write_text("async def list_parties(:\n", encoding="utf-8")
    frontend_type_file.write_text(
        "export interface PartyListParams {\n  skip?: string;\n}\n",
        encoding="utf-8",
    )
    service_file.write_text(
        "async getParties(params: PartyListParams = {}) {\n"
        "  const requestParams = { skip: params.skip };\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error" and issue.path == backend_file and issue.line == 1
        for issue in issues
    )
    report = module.format_issues(issues)
    assert f"{backend_file}:1" in report
    assert module.run((mapping,)) == 1


def test_whitelist_values_must_forward_the_matching_method_input(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    const requestParams = {\n"
        "      skip: params.skip,\n"
        "      limit: params.limit,\n"
        "      review_status: undefined,\n"
        "    };\n"
        "    return apiClient.get('/parties', { params: requestParams });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(issue.kind == "parse_error" for issue in issues)
    assert module.run((mapping,)) == 1


def test_conditional_whitelist_spreads_require_a_proven_field_condition(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    const requestParams = {\n"
        "      skip: params.skip,\n"
        "      limit: params.limit,\n"
        "      ...(false ? { review_status: params.review_status } : {}),\n"
        "    };\n"
        "    return apiClient.get('/parties', { params: requestParams });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(issue.kind == "parse_error" for issue in issues)
    assert module.run((mapping,)) == 1


def test_direct_params_forwarding_rejects_property_mutation(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for mutation in (
        "    params.review_status = undefined;\n",
        "    Reflect.deleteProperty(params, 'review_status');\n",
        "    Reflect.defineProperty(params, 'review_status', { value: undefined });\n",
        "    Object.defineProperties(params, { review_status: { value: undefined } });\n",
        "    Object.assign?.(params, { review_status: undefined });\n",
        "    Reflect?.deleteProperty(params, 'review_status');\n",
        "    Object['assign'](params, { review_status: undefined });\n",
    ):
        service_file.write_text(
            "import { apiClient } from '@/api/client';\n"
            "import type { PartyListParams } from './types';\n\n"
            "export class PartyService {\n"
            "  async getParties(params: PartyListParams = {}) {\n"
            f"{mutation}"
            "    return apiClient.get('/parties', { params: params });\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        issues = module.check_mapping(mapping)

        assert any(issue.kind == "parse_error" for issue in issues)
        assert module.run((mapping,)) == 1


def test_direct_params_forwarding_rejects_delayed_input_alias_mutation(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    let alias: PartyListParams;\n"
        "    alias = params;\n"
        "    delete alias.review_status;\n"
        "    return apiClient.get('/parties', { params: params });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(issue.kind == "parse_error" for issue in issues)
    assert module.run((mapping,)) == 1


def test_direct_params_forwarding_rejects_parenthesized_or_destructured_alias(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for alias_declaration in (
        "    const alias = (params);\n",
        "    const [alias] = [params];\n",
    ):
        service_file.write_text(
            "import { apiClient } from '@/api/client';\n"
            "import type { PartyListParams } from './types';\n\n"
            "export class PartyService {\n"
            "  async getParties(params: PartyListParams = {}) {\n"
            f"{alias_declaration}"
            "    delete alias.review_status;\n"
            "    return apiClient.get('/parties', { params: params });\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        issues = module.check_mapping(mapping)

        assert any(issue.kind == "parse_error" for issue in issues)
        assert module.run((mapping,)) == 1


def test_direct_params_forwarding_rejects_indirect_object_alias(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    const holder = { value: params };\n"
        "    delete holder.value.review_status;\n"
        "    return apiClient.get('/parties', { params: params });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(issue.kind == "parse_error" for issue in issues)
    assert module.run((mapping,)) == 1


def test_direct_params_forwarding_rejects_destructured_shadowing(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    const config = { request: { skip: '0', limit: '20' } };\n"
        "    const { request: params } = config;\n"
        "    return apiClient.get('/parties', { params: params });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(issue.kind == "parse_error" for issue in issues)
    assert module.run((mapping,)) == 1


def test_direct_params_forwarding_rejects_regex_or_template_mutation(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for statement in (
        "    const slash = /\\//; delete params.review_status;\n",
        "    const audit = `${delete params.review_status}`;\n",
    ):
        service_file.write_text(
            "import { apiClient } from '@/api/client';\n"
            "import type { PartyListParams } from './types';\n\n"
            "export class PartyService {\n"
            "  async getParties(params: PartyListParams = {}) {\n"
            f"{statement}"
            "    return apiClient.get('/parties', { params: params });\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        issues = module.check_mapping(mapping)

        assert any(issue.kind == "parse_error" for issue in issues)
        assert module.run((mapping,)) == 1


def test_direct_params_forwarding_rejects_unproven_params_helper(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n"
        "import { stripReviewStatus } from './params';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    stripReviewStatus(params);\n"
        "    return apiClient.get('/parties', { params: params });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error" and "unproven params helper" in issue.detail
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_outbound_request_rejects_rebound_api_client(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    const requestParams = {\n"
        "      skip: params.skip,\n"
        "      limit: params.limit,\n"
        "      review_status: params.review_status,\n"
        "    };\n"
        "    const apiClient = makeClientThatDropsFields();\n"
        "    return apiClient.get('/parties', { params: requestParams });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(issue.kind == "parse_error" for issue in issues)
    assert module.run((mapping,)) == 1


def test_outbound_request_rejects_api_client_method_parameter_shadowing(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(\n"
        "    params: PartyListParams,\n"
        "    apiClient: { get: (...args: unknown[]) => Promise<unknown> },\n"
        "  ) {\n"
        "    const requestParams = {\n"
        "      skip: params.skip,\n"
        "      limit: params.limit,\n"
        "      review_status: params.review_status,\n"
        "    };\n"
        "    return apiClient.get('/parties', { params: requestParams });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error" and "apiClient binding" in issue.detail
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_whitelist_object_mutation_before_request_fails_loudly(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    for mutation in (
        "    delete requestParams.review_status;\n",
        "    Reflect.deleteProperty(requestParams, 'review_status');\n",
    ):
        service_file.write_text(
            "import { apiClient } from '@/api/client';\n"
            "import type { PartyListParams } from './types';\n\n"
            "export class PartyService {\n"
            "  async getParties(params: PartyListParams = {}) {\n"
            "    const requestParams = {\n"
            "      skip: params.skip,\n"
            "      limit: params.limit,\n"
            "      review_status: params.review_status,\n"
            "    };\n"
            f"{mutation}"
            "    return apiClient.get('/parties', { params: requestParams });\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        issues = module.check_mapping(mapping)

        assert any(issue.kind == "parse_error" for issue in issues)
        assert module.run((mapping,)) == 1


def test_whitelist_object_alias_mutation_before_request_fails_loudly(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    const requestParams = {\n"
        "      skip: params.skip,\n"
        "      limit: params.limit,\n"
        "      review_status: params.review_status,\n"
        "    };\n"
        "    const alias = requestParams;\n"
        "    delete alias.review_status;\n"
        "    return apiClient.get('/parties', { params: requestParams });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(issue.kind == "parse_error" for issue in issues)
    assert module.run((mapping,)) == 1


def test_whitelist_object_rejects_destructured_alias_or_shadowing_before_request(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for alias_declaration, request_params in (
        (
            "    const [alias] = [requestParams];\n    delete alias.review_status;\n",
            "requestParams",
        ),
        (
            "    const config = { request: { skip: '0', limit: '20' } };\n"
            "    const { request: requestParams } = config;\n",
            "requestParams",
        ),
    ):
        service_file.write_text(
            "import { apiClient } from '@/api/client';\n"
            "import type { PartyListParams } from './types';\n\n"
            "export class PartyService {\n"
            "  async getParties(params: PartyListParams = {}) {\n"
            "    const requestParams = {\n"
            "      skip: params.skip,\n"
            "      limit: params.limit,\n"
            "      review_status: params.review_status,\n"
            "    };\n"
            f"{alias_declaration}"
            f"    return apiClient.get('/parties', {{ params: {request_params} }});\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        issues = module.check_mapping(mapping)

        assert any(issue.kind == "parse_error" for issue in issues)
        assert module.run((mapping,)) == 1


def test_whitelist_object_rejects_unproven_helper_before_request(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import { stripReviewStatus } from './params';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    const requestParams = {\n"
        "      skip: params.skip,\n"
        "      limit: params.limit,\n"
        "      review_status: params.review_status,\n"
        "    };\n"
        "    stripReviewStatus(requestParams);\n"
        "    return apiClient.get('/parties', { params: requestParams });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(issue.kind == "parse_error" for issue in issues)
    assert module.run((mapping,)) == 1


def test_whitelist_object_rejects_unproven_member_or_optional_helper_before_request(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for helper_call in (
        "    this.stripReviewStatus(requestParams);\n",
        "    mutator.stripReviewStatus(requestParams);\n",
        "    stripReviewStatus?.(requestParams);\n",
        "    mutator?.stripReviewStatus(requestParams);\n",
        "    mutator['stripReviewStatus'](requestParams);\n",
        "    mutator?.['stripReviewStatus'](requestParams);\n",
    ):
        service_file.write_text(
            "import { apiClient } from '@/api/client';\n"
            "import type { PartyListParams } from './types';\n\n"
            "export class PartyService {\n"
            "  async getParties(params: PartyListParams = {}) {\n"
            "    const requestParams = {\n"
            "      skip: params.skip,\n"
            "      limit: params.limit,\n"
            "      review_status: params.review_status,\n"
            "    };\n"
            f"{helper_call}"
            "    return apiClient.get('/parties', { params: requestParams });\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        issues = module.check_mapping(mapping)

        assert any(issue.kind == "parse_error" for issue in issues)
        assert module.run((mapping,)) == 1


def test_whitelist_object_rejects_wrapped_or_api_client_helper_before_request(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for helper_call in (
        "    (stripReviewStatus)(requestParams);\n",
        "    (0, stripReviewStatus)(requestParams);\n",
        "    stripReviewStatus.bind(undefined)(requestParams);\n",
        "    stripReviewStatus((requestParams));\n",
        "    stripReviewStatus<PartyListParams>(requestParams);\n",
        "    apiClient.stripReviewStatus(requestParams);\n",
    ):
        service_file.write_text(
            "import { apiClient } from '@/api/client';\n"
            "import type { PartyListParams } from './types';\n\n"
            "export class PartyService {\n"
            "  async getParties(params: PartyListParams = {}) {\n"
            "    const requestParams = {\n"
            "      skip: params.skip,\n"
            "      limit: params.limit,\n"
            "      review_status: params.review_status,\n"
            "    };\n"
            f"{helper_call}"
            "    return apiClient.get('/parties', { params: requestParams });\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        issues = module.check_mapping(mapping)

        assert any(issue.kind == "parse_error" for issue in issues)
        assert module.run((mapping,)) == 1


def test_dynamic_forwarder_rejects_destructured_helper_shadowing(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "const buildParams = (params: PartyListParams) => {\n"
        "  const normalized: Record<string, string> = {};\n"
        "  Object.entries(params).forEach(([key, value]) => {\n"
        "    if (value == null || value === '') {\n"
        "      return;\n"
        "    }\n"
        "    normalized[key] = value;\n"
        "  });\n"
        "  return normalized;\n"
        "};\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    const helpers = { buildParams: (_: PartyListParams) => ({ skip: '0' }) };\n"
        "    const { buildParams } = helpers;\n"
        "    return apiClient.get('/parties', { params: buildParams(params) });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(issue.kind == "parse_error" for issue in issues)
    assert module.run((mapping,)) == 1


def test_dynamic_forwarder_rejects_method_parameter_shadowing(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "const buildParams = (params: PartyListParams) => {\n"
        "  const normalized: Record<string, string> = {};\n"
        "  Object.entries(params).forEach(([key, value]) => {\n"
        "    if (value == null || value === '') {\n"
        "      return;\n"
        "    }\n"
        "    normalized[key] = value;\n"
        "  });\n"
        "  return normalized;\n"
        "};\n\n"
        "export class PartyService {\n"
        "  async getParties(\n"
        "    params: PartyListParams = {},\n"
        "    buildParams = (_params: PartyListParams) => ({ skip: '0' })\n"
        "  ) {\n"
        "    return apiClient.get('/parties', { params: buildParams(params) });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(issue.kind == "parse_error" for issue in issues)
    assert module.run((mapping,)) == 1


def test_outbound_request_search_ignores_comments_and_nested_config(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for request in (
        "    // return apiClient.get('/parties', { params: params });\n"
        "    return apiClient.get('/parties', { cache: false });\n",
        "    return apiClient.get('/parties', { meta: { params: params } });\n",
    ):
        service_file.write_text(
            "import { apiClient } from '@/api/client';\n"
            "import type { PartyListParams } from './types';\n\n"
            "export class PartyService {\n"
            "  async getParties(params: PartyListParams = {}) {\n"
            f"{request}"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        issues = module.check_mapping(mapping)

        assert any(issue.kind == "parse_error" for issue in issues)
        assert module.run((mapping,)) == 1


def test_interface_comments_and_nested_properties_do_not_count_as_params_fields(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for review_status_field in (
        "  /* review_status?: string; */\n",
        "  filter?: { review_status?: string };\n",
    ):
        frontend_type_file.write_text(
            "export interface PartyListParams {\n"
            "  skip?: string;\n"
            "  limit?: string;\n"
            f"{review_status_field}"
            "}\n",
            encoding="utf-8",
        )

        issues = module.check_mapping(mapping)

        assert any(
            issue.kind == "backend_only" and issue.field == "review_status"
            for issue in issues
        )
        assert module.run((mapping,)) == 1


def test_backend_query_aliases_and_unmarked_required_fields_fail_loudly(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for backend_source in (
        "from fastapi import Query\n\n"
        "async def list_parties(\n"
        "    skip: str | None = Query(None),\n"
        "    limit: str | None = Query(None),\n"
        "    review_status: str | None = Query(None, alias='reviewStatus'),\n"
        "):\n"
        "    return []\n",
        "from fastapi import Query as Q\n\n"
        "async def list_parties(\n"
        "    skip: str | None = Q(None),\n"
        "    limit: str | None = Q(None),\n"
        "    review_status: str | None = Q(None, alias='reviewStatus'),\n"
        "):\n"
        "    return []\n",
        "from fastapi import Query\n\n"
        "Q = Query\n\n"
        "async def list_parties(\n"
        "    skip: str | None = Q(None),\n"
        "    limit: str | None = Q(None),\n"
        "    review_status: str | None = Q(None, alias='reviewStatus'),\n"
        "):\n"
        "    return []\n",
        "from fastapi import Query\n\n"
        "async def list_parties(\n"
        "    skip: str | None = Query(None),\n"
        "    limit: str | None = Query(None),\n"
        "    review_status: str | None = Query(None),\n"
        "    filters: FilterParams = FilterParams(),\n"
        "):\n"
        "    return []\n",
    ):
        backend_file.write_text(backend_source, encoding="utf-8")

        issues = module.check_mapping(mapping)

        assert any(issue.kind == "parse_error" for issue in issues)
        assert module.run((mapping,)) == 1


def test_backend_query_marker_rejects_with_binding_shadowing(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    backend_file.write_text(
        "from fastapi import Query\n\n"
        "with object() as Query:\n"
        "    pass\n\n"
        "async def list_parties(\n"
        "    skip: str | None = Query(None),\n"
        "    limit: str | None = Query(None),\n"
        "    review_status: str | None = Query(None),\n"
        "):\n"
        "    return []\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error" and "FastAPI parameter marker" in issue.detail
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_interface_extensions_and_declaration_merging_fail_loudly(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for frontend_source in (
        "interface BaseParams { review_status?: string; }\n"
        "export interface PartyListParams extends BaseParams {\n"
        "  skip?: string;\n"
        "  limit?: string;\n"
        "}\n",
        "export interface PartyListParams {\n"
        "  skip?: string;\n"
        "  limit?: string;\n"
        "}\n\n"
        "export interface PartyListParams {\n"
        "  review_status?: string;\n"
        "}\n",
    ):
        frontend_type_file.write_text(frontend_source, encoding="utf-8")
        issues = module.check_mapping(mapping)

        assert any(issue.kind == "parse_error" for issue in issues)
        assert module.run((mapping,)) == 1


def test_backend_router_aggregation_prefix_is_part_of_route_proof(
    tmp_path: Path,
) -> None:
    module = _load_module()
    registration_file = tmp_path / "api_v1.py"
    backend_file = tmp_path / "assets" / "project.py"
    backend_file.parent.mkdir()
    backend_file.write_text(
        "from fastapi import APIRouter\n\nrouter = APIRouter()\n",
        encoding="utf-8",
    )
    registration_file.write_text(
        "from fastapi import APIRouter\n"
        "from .assets.project import router as project_router\n\n"
        "api_router = APIRouter()\n"
        "api_router.include_router(project_router, prefix='/projectz')\n",
        encoding="utf-8",
    )

    with pytest.raises(
        module.SourceParseError,
        match="complete backend route path",
    ):
        module._parse_backend_registered_route_path(
            registration_file,
            backend_file,
            "project_router",
            "/{project_id}/tenants",
            "/projects/{project_id}/tenants",
        )


def test_backend_router_aggregation_rejects_registered_router_rebinding(
    tmp_path: Path,
) -> None:
    module = _load_module()
    registration_file = tmp_path / "api_v1.py"
    backend_file = tmp_path / "assets" / "project.py"
    backend_file.parent.mkdir()
    backend_file.write_text(
        "from fastapi import APIRouter\n\nrouter = APIRouter()\n",
        encoding="utf-8",
    )
    registration_file.write_text(
        "from fastapi import APIRouter\n"
        "from .assets.project import router as project_router\n\n"
        "project_router = APIRouter()\n"
        "api_router = APIRouter()\n"
        "api_router.include_router(project_router, prefix='/projects')\n",
        encoding="utf-8",
    )

    with pytest.raises(
        module.SourceParseError,
        match="registered backend router import",
    ):
        module._parse_backend_registered_route_path(
            registration_file,
            backend_file,
            "project_router",
            "/{project_id}/tenants",
            "/projects/{project_id}/tenants",
        )


def test_mapped_backend_route_path_and_method_are_required(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for decorator in ("@router.get('/unrelated')", "@router.post('/parties')"):
        backend_file.write_text(
            "from fastapi import APIRouter, Query\n\n"
            "router = APIRouter()\n\n"
            f"{decorator}\n"
            "async def list_parties(\n"
            "    skip: str | None = Query(None),\n"
            "    limit: str | None = Query(None),\n"
            "    review_status: str | None = Query(None),\n"
            "):\n"
            "    return []\n",
            encoding="utf-8",
        )
        mapped_route = module.ContractMapping(
            name=mapping.name,
            backend_file=backend_file,
            backend_symbol=mapping.backend_symbol,
            backend_route_symbol="list_parties",
            backend_route_path="/parties",
            backend_route_dependency=None,
            frontend_type_file=frontend_type_file,
            frontend_type=mapping.frontend_type,
            service_file=service_file,
            service_method=mapping.service_method,
            request_method="get",
            request_path="/parties",
        )

        issues = module.check_mapping(mapped_route)

        assert any(
            issue.kind == "parse_error" and "mapped backend route" in issue.detail
            for issue in issues
        )
        assert module.run((mapped_route,)) == 1


def test_mapped_backend_route_requires_fastapi_router_binding(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    backend_file.write_text(
        "from fastapi import Query\n\n"
        "router = object()\n\n"
        "@router.get('/parties')\n"
        "async def list_parties(\n"
        "    skip: str | None = Query(None),\n"
        "    limit: str | None = Query(None),\n"
        "    review_status: str | None = Query(None),\n"
        "):\n"
        "    return []\n",
        encoding="utf-8",
    )
    mapped_route = module.ContractMapping(
        name=mapping.name,
        backend_file=backend_file,
        backend_symbol=mapping.backend_symbol,
        backend_route_symbol="list_parties",
        backend_route_path="/parties",
        backend_route_dependency=None,
        frontend_type_file=frontend_type_file,
        frontend_type=mapping.frontend_type,
        service_file=service_file,
        service_method=mapping.service_method,
        request_method="get",
        request_path="/parties",
    )

    issues = module.check_mapping(mapped_route)

    assert any(
        issue.kind == "parse_error" and "FastAPI APIRouter binding" in issue.detail
        for issue in issues
    )
    assert module.run((mapped_route,)) == 1


def test_mapped_backend_route_rejects_api_router_rebinding(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    backend_file.write_text(
        "from fastapi import APIRouter, Query\n\n"
        "def APIRouter():\n"
        "    return object()\n\n"
        "router = APIRouter()\n\n"
        "@router.get('/parties')\n"
        "async def list_parties(\n"
        "    skip: str | None = Query(None),\n"
        "    limit: str | None = Query(None),\n"
        "    review_status: str | None = Query(None),\n"
        "):\n"
        "    return []\n",
        encoding="utf-8",
    )
    mapped_route = module.ContractMapping(
        name=mapping.name,
        backend_file=backend_file,
        backend_symbol=mapping.backend_symbol,
        backend_route_symbol="list_parties",
        backend_route_path="/parties",
        backend_route_dependency=None,
        frontend_type_file=frontend_type_file,
        frontend_type=mapping.frontend_type,
        service_file=service_file,
        service_method=mapping.service_method,
        request_method="get",
        request_path="/parties",
    )

    issues = module.check_mapping(mapped_route)

    assert any(
        issue.kind == "parse_error" and "FastAPI APIRouter binding" in issue.detail
        for issue in issues
    )
    assert module.run((mapped_route,)) == 1


def test_backend_query_marker_requires_fastapi_import(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for backend_source in (
        "from custom_query import Query\n\n"
        "async def list_parties(\n"
        "    skip: str | None = Query(None),\n"
        "    limit: str | None = Query(None),\n"
        "    review_status: str | None = Query(None),\n"
        "):\n"
        "    return []\n",
        "from fastapi import Query\n\n"
        "def Query(value):\n"
        "    return value\n\n"
        "async def list_parties(\n"
        "    skip: str | None = Query(None),\n"
        "    limit: str | None = Query(None),\n"
        "    review_status: str | None = Query(None),\n"
        "):\n"
        "    return []\n",
    ):
        backend_file.write_text(backend_source, encoding="utf-8")

        issues = module.check_mapping(mapping)

        assert any(issue.kind == "parse_error" for issue in issues)
        assert module.run((mapping,)) == 1


def test_mapped_route_dependency_is_required(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    frontend_type_file.write_text(
        "export interface PartyListParams {\n"
        "  skip?: string;\n"
        "  limit?: string;\n"
        "  review_status?: string;\n"
        "}\n",
        encoding="utf-8",
    )
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    const requestParams = {\n"
        "      skip: params.skip,\n"
        "      limit: params.limit,\n"
        "      review_status: params.review_status,\n"
        "    };\n"
        "    return apiClient.get('/parties', { params: requestParams });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    for dependency in ("other_query_params",):
        backend_file.write_text(
            "from fastapi import Depends, Query\n\n"
            "router = object()\n\n"
            "def resolve_query_params(\n"
            "    skip: str | None = Query(None),\n"
            "    limit: str | None = Query(None),\n"
            "    review_status: str | None = Query(None),\n"
            "):\n"
            "    return None\n\n"
            "@router.get('/parties')\n"
            "async def list_parties(\n"
            f"    query_params = Depends({dependency}),\n"
            "):\n"
            "    return []\n",
            encoding="utf-8",
        )
        mapped_route = module.ContractMapping(
            name=mapping.name,
            backend_file=backend_file,
            backend_symbol="resolve_query_params",
            backend_route_symbol="list_parties",
            backend_route_path="/parties",
            backend_route_dependency="resolve_query_params",
            frontend_type_file=frontend_type_file,
            frontend_type=mapping.frontend_type,
            service_file=service_file,
            service_method=mapping.service_method,
            request_method="get",
            request_path="/parties",
        )

        issues = module.check_mapping(mapped_route)

        assert any(
            issue.kind == "parse_error"
            and "mapped backend route dependency" in issue.detail
            for issue in issues
        )
        assert module.run((mapped_route,)) == 1


def test_mapped_request_target_and_method_are_required(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for outbound_request in (
        "    return apiClient.get('/unrelated', { params: requestParams });\n",
        "    return apiClient.post('/parties', { params: requestParams });\n",
    ):
        service_file.write_text(
            "import { apiClient } from '@/api/client';\n"
            "import type { PartyListParams } from './types';\n\n"
            "export class PartyService {\n"
            "  async getParties(params: PartyListParams = {}) {\n"
            "    const requestParams = {\n"
            "      skip: params.skip,\n"
            "      limit: params.limit,\n"
            "      review_status: params.review_status,\n"
            "    };\n"
            f"{outbound_request}"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        issues = module.check_mapping(mapping)

        assert any(
            issue.kind == "parse_error" and "mapped outbound request" in issue.detail
            for issue in issues
        )
        assert module.run((mapping,)) == 1


def test_dynamic_endpoint_constant_matches_backend_route_parameter_name(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    mapping = module.ContractMapping(
        **{
            **mapping.__dict__,
            "request_path": "/projects/{project_id}/tenants",
        }
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import { API_ENDPOINTS } from '@/constants/api';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(projectId: string, params: PartyListParams = {}) {\n"
        "    const requestParams = {\n"
        "      skip: params.skip,\n"
        "      limit: params.limit,\n"
        "      review_status: params.review_status,\n"
        "    };\n"
        "    return apiClient.get(API_ENDPOINTS.PROJECT.TENANTS(projectId), {\n"
        "      params: requestParams,\n"
        "    });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    assert module.check_mapping(mapping) == []


def test_dynamic_endpoint_constant_rejects_unproven_call_arguments(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    mapping = module.ContractMapping(
        **{
            **mapping.__dict__,
            "request_path": "/projects/{project_id}/tenants",
        }
    )
    _write_fixture(backend_file, frontend_type_file, service_file)

    for target in (
        "API_ENDPOINTS.PROJECT.TENANTS()",
        "API_ENDPOINTS.PROJECT.TENANTS(projectId, extra)",
        "API_ENDPOINTS.PROJECT.TENANTS(project.id)",
    ):
        service_file.write_text(
            "import { apiClient } from '@/api/client';\n"
            "import { API_ENDPOINTS } from '@/constants/api';\n"
            "import type { PartyListParams } from './types';\n\n"
            "export class PartyService {\n"
            "  async getParties(projectId: string, params: PartyListParams = {}) {\n"
            "    const requestParams = {\n"
            "      skip: params.skip,\n"
            "      limit: params.limit,\n"
            "      review_status: params.review_status,\n"
            "    };\n"
            f"    return apiClient.get({target}, {{ params: requestParams }});\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )

        issues = module.check_mapping(mapping)

        assert any(
            issue.kind == "parse_error" and "mapped outbound request" in issue.detail
            for issue in issues
        )


def test_dynamic_endpoint_constant_rejects_unbound_template_identifier(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_module()
    constants_file = tmp_path / "frontend/src/constants/api.ts"
    constants_file.parent.mkdir(parents=True)
    constants_file.write_text(
        "export const PROJECT_API = {\n"
        "  TENANTS: (id: string) => `/projects/${projectId}/tenants`,\n"
        "} as const;\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "ROOT", tmp_path)

    assert (
        module._resolve_request_path("", "API_ENDPOINTS.PROJECT.TENANTS(projectId)")
        is None
    )


def test_whitelist_rejects_method_input_alias_mutation(tmp_path: Path) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    const input = params;\n"
        "    delete input.review_status;\n"
        "    const requestParams = {\n"
        "      skip: params.skip,\n"
        "      limit: params.limit,\n"
        "      review_status: params.review_status,\n"
        "    };\n"
        "    return apiClient.get('/parties', { params: requestParams });\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error" and "unchanged method input" in issue.detail
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_direct_forwarding_rejects_nested_params_parameter_shadowing(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    service_file.write_text(
        "import { apiClient } from '@/api/client';\n"
        "import type { PartyListParams } from './types';\n\n"
        "export class PartyService {\n"
        "  async getParties(params: PartyListParams = {}) {\n"
        "    return (() => {\n"
        "      const send = (params: PartyListParams) =>\n"
        "        apiClient.get('/parties', { params: params });\n"
        "      return send({ skip: '0', limit: '20' });\n"
        "    })();\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error" and "nested outbound request scope" in issue.detail
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_invalid_utf8_mapped_source_reports_contract_parse_error(
    tmp_path: Path,
) -> None:
    module = _load_module()
    mapping, backend_file, frontend_type_file, service_file = _fixture_mapping(
        module, tmp_path
    )
    _write_fixture(backend_file, frontend_type_file, service_file)
    frontend_type_file.write_bytes(b"\xff")

    issues = module.check_mapping(mapping)

    assert any(
        issue.kind == "parse_error"
        and issue.path == frontend_type_file
        and "cannot decode source" in issue.detail
        for issue in issues
    )
    assert module.run((mapping,)) == 1


def test_repository_request_metadata_matches_mapped_routes() -> None:
    module = _load_module()

    assert [
        (
            mapping.name,
            mapping.backend_route_symbol,
            mapping.backend_route_path,
            mapping.backend_route_dependency,
            mapping.request_method,
            mapping.request_path,
            (
                mapping.backend_registration_file.relative_to(module.ROOT).as_posix()
                if mapping.backend_registration_file is not None
                else None
            ),
            mapping.backend_registered_router,
        )
        for mapping in module.CONTRACT_MAPPINGS
    ] == [
        ("parties", "list_parties", "/parties", None, "get", "/parties", None, None),
        (
            "contract_groups",
            "list_contract_groups",
            "/contract-groups",
            None,
            "get",
            "/contract-groups",
            None,
            None,
        ),
        (
            "ledger_entries",
            "get_ledger_entries",
            "/ledger/entries",
            "resolve_ledger_query_params",
            "get",
            "/ledger/entries",
            None,
            None,
        ),
        (
            "projects",
            "list_projects",
            "",
            None,
            "get",
            "/projects",
            "backend/src/api/v1/__init__.py",
            "project_router",
        ),
        (
            "project_tenants",
            "get_project_tenants",
            "/{project_id}/tenants",
            None,
            "get",
            "/projects/{project_id}/tenants",
            "backend/src/api/v1/__init__.py",
            "project_router",
        ),
        (
            "project_analytics",
            "get_project_analytics",
            "/{project_id}/analytics",
            None,
            "get",
            "/projects/{project_id}/analytics",
            "backend/src/api/v1/__init__.py",
            "project_router",
        ),
        (
            "property_certificates",
            "list_certificates",
            "",
            None,
            "get",
            "/property-certificates",
            None,
            None,
        ),
    ]
