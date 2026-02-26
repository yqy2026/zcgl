"""分层约束测试：rent_contract terms 路由应委托服务层。"""

import re
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.api


def _read_module_source() -> str:
    from src.api.v1.rent_contracts import terms as terms_module

    return Path(terms_module.__file__).read_text(encoding="utf-8")


def test_terms_module_should_not_import_rent_contract_crud_directly() -> None:
    """terms 路由模块不应直接导入 crud.rent_contract。"""
    module_source = _read_module_source()
    assert "from ....crud.rent_contract" not in module_source
    assert "rent_term." not in module_source
    assert "rent_contract." not in module_source


def test_terms_module_should_import_authz_dependency() -> None:
    """terms 路由应引入统一 ABAC 依赖。"""
    module_source = _read_module_source()
    assert "AuthzContext" in module_source
    assert "require_authz" in module_source


def test_terms_endpoints_should_use_require_authz() -> None:
    """条款查询和新增端点应接入 require_authz。"""
    module_source = _read_module_source()
    expected_patterns = [
        r"async def get_contract_terms[\s\S]*?require_authz\([\s\S]*?action=\"read\"[\s\S]*?resource_type=\"rent_contract\"[\s\S]*?resource_id=\"\{contract_id\}\"[\s\S]*?deny_as_not_found=True",
        r"async def add_rent_term[\s\S]*?require_authz\([\s\S]*?action=\"update\"[\s\S]*?resource_type=\"rent_contract\"[\s\S]*?resource_id=\"\{contract_id\}\"",
    ]
    for pattern in expected_patterns:
        assert re.search(pattern, module_source), pattern


@pytest.mark.asyncio
async def test_get_contract_terms_should_delegate_service() -> None:
    """获取条款接口应委托 rent_contract_service.get_contract_terms_async。"""
    from src.api.v1.rent_contracts import terms as module
    from src.api.v1.rent_contracts.terms import get_contract_terms

    mock_service = MagicMock()
    mock_service.get_contract_terms_async = AsyncMock(return_value=[MagicMock()])

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        result = await get_contract_terms(
            contract_id="contract-1",
            db=MagicMock(),
            current_user=MagicMock(),
        )

    assert len(result) == 1
    mock_service.get_contract_terms_async.assert_awaited_once_with(
        db=ANY,
        contract_id="contract-1",
    )


@pytest.mark.asyncio
async def test_add_rent_term_should_delegate_service() -> None:
    """新增条款接口应委托 rent_contract_service.add_contract_term_async。"""
    from src.api.v1.rent_contracts import terms as module
    from src.api.v1.rent_contracts.terms import add_rent_term
    from src.schemas.rent_contract import RentTermCreate

    term_in = RentTermCreate(
        start_date="2026-01-01",
        end_date="2026-12-31",
        monthly_rent="1000.00",
    )

    mock_service = MagicMock()
    mock_service.add_contract_term_async = AsyncMock(return_value=MagicMock(id="term-1"))

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(module, "rent_contract_service", mock_service)
        result = await add_rent_term(
            contract_id="contract-1",
            db=MagicMock(),
            term_in=term_in,
            current_user=MagicMock(),
        )

    assert getattr(result, "id", None) == "term-1"
    mock_service.add_contract_term_async.assert_awaited_once_with(
        db=ANY,
        contract_id="contract-1",
        term_in=term_in,
    )
