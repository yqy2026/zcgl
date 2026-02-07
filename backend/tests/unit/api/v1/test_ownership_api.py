"""
Ownership API 路由单元测试（异步）
"""

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.core.exception_handler import (
    BaseBusinessError,
    DuplicateResourceError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from src.schemas.ownership import (
    OwnershipCreate,
    OwnershipSearchRequest,
    OwnershipUpdate,
)
from src.services.asset.ownership_financial_service import (
    ContractSummary,
    FinancialSummary,
    OwnershipFinancialResult,
)

pytestmark = [pytest.mark.api, pytest.mark.asyncio]


def _make_ownership(
    ownership_id: str = "ownership-id-123",
    name: str = "Test Ownership Company",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=ownership_id,
        name=name,
        code="OW2501001",
        short_name="Test Owner",
        is_active=True,
        data_status="正常",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        project_relations_data=[],
    )


@pytest.fixture
def mock_db() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_current_user() -> SimpleNamespace:
    return SimpleNamespace(id="user-id", username="testuser", is_active=True)


class TestGetOwnershipDropdownOptions:
    async def test_get_dropdown_options_success(
        self, mock_db: AsyncMock, mock_current_user: SimpleNamespace
    ):
        from src.api.v1.assets.ownership import get_ownership_dropdown_options

        service_data = [
            {
                "id": "ownership-id-1",
                "name": "Ownership 1",
                "code": "OW2501001",
                "short_name": "O1",
                "is_active": True,
                "data_status": "正常",
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
                "asset_count": 5,
                "project_count": 2,
            }
        ]

        with patch(
            "src.api.v1.assets.ownership.ownership_service"
        ) as mock_service:
            mock_service.get_ownership_dropdown_options = AsyncMock(
                return_value=service_data
            )

            result = await get_ownership_dropdown_options(
                current_user=mock_current_user,
                db=mock_db,
                is_active=True,
            )

        assert len(result) == 1
        assert result[0].name == "Ownership 1"
        assert result[0].asset_count == 5
        assert result[0].project_count == 2

    async def test_get_dropdown_options_exception(
        self, mock_db: AsyncMock, mock_current_user: SimpleNamespace
    ):
        from src.api.v1.assets.ownership import get_ownership_dropdown_options

        with patch(
            "src.api.v1.assets.ownership.ownership_service"
        ) as mock_service:
            mock_service.get_ownership_dropdown_options = AsyncMock(
                side_effect=Exception("db error")
            )

            with pytest.raises(BaseBusinessError) as exc_info:
                await get_ownership_dropdown_options(
                    current_user=mock_current_user,
                    db=mock_db,
                    is_active=True,
                )

        assert exc_info.value.status_code == 500
        assert "获取权属方选项失败" in exc_info.value.message


class TestCreateOwnership:
    async def test_create_ownership_success(
        self, mock_db: AsyncMock, mock_current_user: SimpleNamespace
    ):
        from src.api.v1.assets.ownership import create_ownership

        obj = _make_ownership()
        payload = OwnershipCreate(name="New Ownership", short_name="New")

        with patch(
            "src.api.v1.assets.ownership.ownership_service"
        ) as mock_service:
            mock_service.create_ownership = AsyncMock(return_value=obj)

            result = await create_ownership(
                db=mock_db,
                ownership_in=payload,
                current_user=mock_current_user,
            )

        assert result.id == obj.id
        assert result.name == obj.name

    async def test_create_ownership_duplicate(
        self, mock_db: AsyncMock, mock_current_user: SimpleNamespace
    ):
        from src.api.v1.assets.ownership import create_ownership

        payload = OwnershipCreate(name="Existing", short_name="Ex")

        with patch(
            "src.api.v1.assets.ownership.ownership_service"
        ) as mock_service:
            mock_service.create_ownership = AsyncMock(
                side_effect=DuplicateResourceError("权属方", "name", "Existing")
            )

            with pytest.raises(BaseBusinessError) as exc_info:
                await create_ownership(
                    db=mock_db,
                    ownership_in=payload,
                    current_user=mock_current_user,
                )

        assert exc_info.value.status_code == 409
        assert "权属方已存在" in exc_info.value.message


class TestUpdateOwnership:
    async def test_update_ownership_success(
        self, mock_db: AsyncMock, mock_current_user: SimpleNamespace
    ):
        from src.api.v1.assets.ownership import update_ownership

        obj = _make_ownership(name="Updated Name")
        payload = OwnershipUpdate(name="Updated Name")

        with patch(
            "src.api.v1.assets.ownership.ownership_service"
        ) as mock_service:
            mock_service.update_ownership_by_id = AsyncMock(return_value=obj)

            result = await update_ownership(
                db=mock_db,
                ownership_id=obj.id,
                ownership_in=payload,
                current_user=mock_current_user,
            )

        assert result.name == "Updated Name"

    async def test_update_ownership_not_found(
        self, mock_db: AsyncMock, mock_current_user: SimpleNamespace
    ):
        from src.api.v1.assets.ownership import update_ownership

        payload = OwnershipUpdate(name="Missing")

        with patch(
            "src.api.v1.assets.ownership.ownership_service"
        ) as mock_service:
            mock_service.update_ownership_by_id = AsyncMock(
                side_effect=ResourceNotFoundError("权属方", "missing")
            )

            with pytest.raises(BaseBusinessError) as exc_info:
                await update_ownership(
                    db=mock_db,
                    ownership_id="missing",
                    ownership_in=payload,
                    current_user=mock_current_user,
                )

        assert exc_info.value.status_code == 404


class TestUpdateOwnershipProjects:
    async def test_update_projects_success(
        self, mock_db: AsyncMock, mock_current_user: SimpleNamespace
    ):
        from src.api.v1.assets.ownership import update_ownership_projects

        obj = _make_ownership()

        with patch(
            "src.api.v1.assets.ownership.ownership_service"
        ) as mock_service:
            mock_service.get_ownership = AsyncMock(side_effect=[obj, obj])
            mock_service.update_related_projects = AsyncMock(return_value=None)
            mock_service.get_project_count = AsyncMock(return_value=3)

            result = await update_ownership_projects(
                db=mock_db,
                ownership_id=obj.id,
                project_ids=["project-1", "project-2", "project-3"],
                current_user=mock_current_user,
            )

        assert result.project_count == 3

    async def test_update_projects_not_found(
        self, mock_db: AsyncMock, mock_current_user: SimpleNamespace
    ):
        from src.api.v1.assets.ownership import update_ownership_projects

        with patch(
            "src.api.v1.assets.ownership.ownership_service"
        ) as mock_service:
            mock_service.get_ownership = AsyncMock(return_value=None)

            with pytest.raises(BaseBusinessError) as exc_info:
                await update_ownership_projects(
                    db=mock_db,
                    ownership_id="missing",
                    project_ids=["project-1"],
                    current_user=mock_current_user,
                )

        assert exc_info.value.status_code == 404


class TestDeleteOwnership:
    async def test_delete_ownership_success(
        self, mock_db: AsyncMock, mock_current_user: SimpleNamespace
    ):
        from src.api.v1.assets.ownership import delete_ownership

        obj = _make_ownership()

        with patch(
            "src.api.v1.assets.ownership.ownership_service"
        ) as mock_service:
            mock_service.get_asset_count = AsyncMock(return_value=2)
            mock_service.delete_ownership = AsyncMock(return_value=obj)

            result = await delete_ownership(
                db=mock_db,
                ownership_id=obj.id,
                current_user=mock_current_user,
            )

        assert result.id == obj.id
        assert result.affected_assets == 2

    async def test_delete_ownership_with_assets_forbidden(
        self, mock_db: AsyncMock, mock_current_user: SimpleNamespace
    ):
        from src.api.v1.assets.ownership import delete_ownership

        with patch(
            "src.api.v1.assets.ownership.ownership_service"
        ) as mock_service:
            mock_service.get_asset_count = AsyncMock(return_value=3)
            mock_service.delete_ownership = AsyncMock(
                side_effect=OperationNotAllowedError(
                    "该权属方还有 3 个关联资产，无法删除",
                    reason="ownership_has_assets",
                )
            )

            with pytest.raises(BaseBusinessError) as exc_info:
                await delete_ownership(
                    db=mock_db,
                    ownership_id="ownership-id-123",
                    current_user=mock_current_user,
                )

        assert exc_info.value.status_code == 400


class TestGetOwnershipsAndSearch:
    async def test_get_ownerships_success(
        self, mock_db: AsyncMock, mock_current_user: SimpleNamespace
    ):
        from src.api.v1.assets.ownership import get_ownerships

        items = [_make_ownership("ownership-id-1"), _make_ownership("ownership-id-2")]

        with patch(
            "src.api.v1.assets.ownership.ownership_service"
        ) as mock_service:
            mock_service.search_ownerships = AsyncMock(
                return_value={
                    "items": items,
                    "total": 2,
                    "page": 1,
                    "page_size": 10,
                }
            )
            mock_service.get_asset_count = AsyncMock(return_value=5)
            mock_service.get_project_count = AsyncMock(return_value=2)

            result = await get_ownerships(
                current_user=mock_current_user,
                db=mock_db,
                page=1,
                page_size=10,
                keyword=None,
                is_active=None,
            )

        payload = json.loads(result.body)
        assert payload["data"]["pagination"]["total"] == 2
        assert len(payload["data"]["items"]) == 2
        assert payload["data"]["items"][0]["asset_count"] == 5

    async def test_search_ownerships_success(
        self, mock_db: AsyncMock, mock_current_user: SimpleNamespace
    ):
        from src.api.v1.assets.ownership import search_ownerships

        items = [_make_ownership("ownership-id-1")]
        search_params = OwnershipSearchRequest(keyword="Test", page=1, page_size=10)

        with patch(
            "src.api.v1.assets.ownership.ownership_service"
        ) as mock_service:
            mock_service.search_ownerships = AsyncMock(
                return_value={
                    "items": items,
                    "total": 1,
                    "page": 1,
                    "page_size": 10,
                }
            )
            mock_service.get_asset_count = AsyncMock(return_value=3)
            mock_service.get_project_count = AsyncMock(return_value=1)

            result = await search_ownerships(
                db=mock_db,
                search_params=search_params,
                current_user=mock_current_user,
            )

        payload = json.loads(result.body)
        assert payload["data"]["pagination"]["total"] == 1
        assert payload["data"]["items"][0]["project_count"] == 1


class TestStatisticsAndToggle:
    async def test_get_ownership_statistics_success(
        self, mock_db: AsyncMock, mock_current_user: SimpleNamespace
    ):
        from src.api.v1.assets.ownership import get_ownership_statistics

        recent = [_make_ownership("ownership-id-1")]

        with patch(
            "src.api.v1.assets.ownership.ownership_service"
        ) as mock_service:
            mock_service.get_statistics = AsyncMock(
                return_value={
                    "total_count": 10,
                    "active_count": 8,
                    "inactive_count": 2,
                    "recent_created": recent,
                }
            )

            result = await get_ownership_statistics(
                db=mock_db,
                current_user=mock_current_user,
            )

        assert result.total_count == 10
        assert len(result.recent_created) == 1

    async def test_toggle_status_success(
        self, mock_db: AsyncMock, mock_current_user: SimpleNamespace
    ):
        from src.api.v1.assets.ownership import toggle_ownership_status

        obj = _make_ownership()
        obj.is_active = False

        with patch(
            "src.api.v1.assets.ownership.ownership_service"
        ) as mock_service:
            mock_service.toggle_status = AsyncMock(return_value=obj)

            result = await toggle_ownership_status(
                db=mock_db,
                ownership_id=obj.id,
                current_user=mock_current_user,
            )

        assert result.is_active is False


class TestFinancialSummary:
    async def test_get_financial_summary_success(
        self, mock_db: AsyncMock, mock_current_user: SimpleNamespace
    ):
        from src.api.v1.assets.ownership import get_ownership_financial_summary

        obj = _make_ownership()
        financial_result = OwnershipFinancialResult(
            ownership_id=obj.id,
            ownership_name=obj.name,
            financial_summary=FinancialSummary(
                total_due_amount=100000.0,
                total_paid_amount=80000.0,
                total_arrears_amount=20000.0,
                payment_rate=80.0,
            ),
            contract_summary=ContractSummary(total_contracts=5, active_contracts=3),
        )

        with patch(
            "src.api.v1.assets.ownership.ownership_service"
        ) as mock_service, patch(
            "src.services.asset.ownership_financial_service.OwnershipFinancialService.get_financial_summary",
            new_callable=AsyncMock,
        ) as mock_get_financial:
            mock_service.get_ownership = AsyncMock(return_value=obj)
            mock_get_financial.return_value = financial_result

            result = await get_ownership_financial_summary(
                ownership_id=obj.id,
                db=mock_db,
                current_user=mock_current_user,
            )

        assert result["ownership_id"] == obj.id
        assert result["financial_summary"]["payment_rate"] == 80.0
        assert result["contract_summary"]["total_contracts"] == 5

    async def test_get_financial_summary_not_found(
        self, mock_db: AsyncMock, mock_current_user: SimpleNamespace
    ):
        from src.api.v1.assets.ownership import get_ownership_financial_summary

        with patch(
            "src.api.v1.assets.ownership.ownership_service"
        ) as mock_service:
            mock_service.get_ownership = AsyncMock(return_value=None)

            with pytest.raises(BaseBusinessError) as exc_info:
                await get_ownership_financial_summary(
                    ownership_id="missing",
                    db=mock_db,
                    current_user=mock_current_user,
                )

        assert exc_info.value.status_code == 404
