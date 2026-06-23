"""
Contract CRUD query predicate tests.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.crud.contract import CRUDContract

pytestmark = pytest.mark.asyncio


@pytest.fixture
def crud() -> CRUDContract:
    return CRUDContract()


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result)
    return db


class TestContractNumberQueries:
    async def test_shared_scan_scope_excludes_deleted_contract_groups(
        self,
        crud: CRUDContract,
        mock_db: MagicMock,
    ) -> None:
        await crud.list_by_contract_number(
            mock_db,
            contract_number="HT-SHARED-001",
            lessor_party_id="owner-party",
            lessee_party_id="operator-party",
            shared_scan_scope_only=True,
        )

        stmt = mock_db.execute.await_args.args[0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))

        assert "contracts.contract_number = 'HT-SHARED-001'" in compiled
        assert "contracts.group_relation_type = 'ENTRUSTED'" in compiled
        assert "contract_groups.revenue_mode = 'AGENCY'" in compiled
        assert "contract_groups.data_status = '正常'" in compiled
