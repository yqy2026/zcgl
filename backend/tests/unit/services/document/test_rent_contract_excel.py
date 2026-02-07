from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.services.document.rent_contract_excel import CONTRACT_COLUMNS, RentContractExcelService

pytestmark = pytest.mark.asyncio


def _result_with_scalars_all(values):
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


class TestRentContractExcelImport:
    async def test_prefetches_existing_contract_numbers_once(self):
        service = RentContractExcelService()
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=_result_with_scalars_all([]))

        contracts_df = pd.DataFrame(
            [
                {
                    CONTRACT_COLUMNS["contract_number"]: "HT-001",
                    CONTRACT_COLUMNS["ownership_id"]: "OWN-001",
                    CONTRACT_COLUMNS["tenant_name"]: "租户A",
                    CONTRACT_COLUMNS["sign_date"]: "2025-01-01",
                    CONTRACT_COLUMNS["start_date"]: "2025-01-01",
                    CONTRACT_COLUMNS["end_date"]: "2025-12-31",
                },
                {
                    CONTRACT_COLUMNS["contract_number"]: "HT-001",
                    CONTRACT_COLUMNS["ownership_id"]: "OWN-001",
                    CONTRACT_COLUMNS["tenant_name"]: "租户B",
                    CONTRACT_COLUMNS["sign_date"]: "2025-01-01",
                    CONTRACT_COLUMNS["start_date"]: "2025-01-01",
                    CONTRACT_COLUMNS["end_date"]: "2025-12-31",
                },
            ]
        )

        with patch("pandas.read_excel", return_value=contracts_df), patch(
            "src.services.document.rent_contract_excel.rent_contract_service"
        ) as mock_contract_service:
            mock_contract_service.create_contract_async = AsyncMock(
                return_value=MagicMock(contract_number="HT-001")
            )
            mock_contract_service.update_contract_async = AsyncMock()

            result = await service.import_contracts_from_excel(
                db=mock_db,
                file_path="dummy.xlsx",
                import_terms=False,
                overwrite_existing=False,
            )

        mock_db.execute.assert_awaited_once()
        mock_contract_service.create_contract_async.assert_awaited_once()
        assert result["imported_contracts"] == 1
        assert any("合同编号已存在: HT-001" in error for error in result["errors"])

