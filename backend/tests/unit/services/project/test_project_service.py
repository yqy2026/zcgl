"""
濞村鐦い鍦窗閺堝秴濮熼敍鍫濈磽濮濄儻绱?
"""

import inspect
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from src.constants.business_constants import DataStatusValues
from src.core.exception_handler import (
    DuplicateResourceError,
    OperationNotAllowedError,
    ResourceNotFoundError,
)
from src.crud.query_builder import PartyFilter
from src.models import Project
from src.models.contract_group import (
    ContractLifecycleStatus,
    GroupRelationType,
    RevenueMode,
)
from src.schemas.project import (
    ProjectCreate,
    ProjectLedgerMetricGroup,
    ProjectLedgerSummaryResponse,
    ProjectOperatingResultSummary,
    ProjectSearchRequest,
    ProjectUpdate,
)
from src.services.project.service import ProjectService

pytestmark = pytest.mark.asyncio


def _project_ledger_summary(
    *,
    receivable_amount: Decimal,
    payable_amount: Decimal,
    received_amount: Decimal,
    paid_amount: Decimal,
    overdue_amount: Decimal,
    service_fee_receivable: Decimal,
    service_fee_received: Decimal,
) -> ProjectLedgerSummaryResponse:
    return ProjectLedgerSummaryResponse(
        receivable_amount=receivable_amount,
        payable_amount=payable_amount,
        received_amount=received_amount,
        paid_amount=paid_amount,
        overdue_amount=overdue_amount,
        service_fee_receivable=service_fee_receivable,
        service_fee_received=service_fee_received,
        terminal_collection=ProjectLedgerMetricGroup(
            amount_due=receivable_amount,
            paid_amount=received_amount,
            outstanding_amount=max(receivable_amount - received_amount, Decimal(0)),
            overdue_amount=overdue_amount,
        ),
        operator_income=ProjectLedgerMetricGroup(
            amount_due=receivable_amount,
            paid_amount=received_amount,
            outstanding_amount=max(receivable_amount - received_amount, Decimal(0)),
        ),
        operator_cost=ProjectLedgerMetricGroup(
            amount_due=payable_amount,
            paid_amount=paid_amount,
            outstanding_amount=max(payable_amount - paid_amount, Decimal(0)),
        ),
        service_fee_settlement=ProjectLedgerMetricGroup(
            amount_due=service_fee_receivable,
            paid_amount=service_fee_received,
            outstanding_amount=max(
                service_fee_receivable - service_fee_received,
                Decimal(0),
            ),
        ),
        operating_result=ProjectOperatingResultSummary(
            accrual_net_amount=receivable_amount - payable_amount,
            cash_net_amount=received_amount - paid_amount,
        ),
    )


async def test_project_service_module_should_not_use_datetime_utcnow() -> None:
    """Project service should use the centralized clock helper."""
    from src.services.project import service as project_service_module

    module_source = inspect.getsource(project_service_module)
    assert "datetime.utcnow(" not in module_source


@pytest.fixture
def project_service() -> ProjectService:
    return ProjectService()


def _ledger_entry(
    *,
    contract_id: str,
    revenue_mode: RevenueMode,
    relation_type: GroupRelationType,
    amount_due: str,
    paid_amount: str,
    payment_status: str,
    year_month: str | None = None,
    due_date: date | None = None,
    current_project_id: str = "project-moved-away",
    ledger_views: list[str] | None = None,
) -> SimpleNamespace:
    group = SimpleNamespace(
        contract_group_id=f"group-{contract_id}",
        project_id=current_project_id,
        revenue_mode=revenue_mode,
    )
    contract = SimpleNamespace(
        contract_id=contract_id,
        contract_group=group,
        group_relation_type=relation_type,
    )
    return SimpleNamespace(
        contract_id=contract_id,
        contract=contract,
        amount_due=Decimal(amount_due),
        paid_amount=Decimal(paid_amount),
        payment_status=payment_status,
        year_month=year_month,
        due_date=due_date,
        attributed_project_id="project-1",
        ledger_views=ledger_views
        or {
            GroupRelationType.UPSTREAM: ["operator_cost"],
            GroupRelationType.DOWNSTREAM: [
                "terminal_collection",
                "operator_income",
            ],
            GroupRelationType.DIRECT_LEASE: ["terminal_collection"],
        }.get(relation_type, []),
    )


def _service_fee_entry(
    *,
    amount_due: str,
    paid_amount: str,
    payment_status: str,
    year_month: str | None = None,
    due_date: date | None = None,
) -> SimpleNamespace:
    agency_group = SimpleNamespace(
        contract_group_id="group-agency",
        project_id="project-moved-away",
        revenue_mode=RevenueMode.AGENCY,
    )
    agency_contract = SimpleNamespace(
        contract_id="contract-direct",
        contract_group=agency_group,
        group_relation_type=GroupRelationType.DIRECT_LEASE,
    )
    return SimpleNamespace(
        agency_contract=agency_contract,
        amount_due=Decimal(amount_due),
        paid_amount=Decimal(paid_amount),
        payment_status=payment_status,
        year_month=year_month,
        due_date=due_date,
        attributed_project_id="project-1",
    )


@pytest.fixture
def mock_project() -> MagicMock:
    project = MagicMock(spec=Project)
    project.id = "project_123"
    project.project_name = "濞村鐦い鍦窗"
    project.project_code = "PRJ-TEST01-202606-0001"
    project.status = "active"
    project.created_by = "user_123"
    project.created_at = datetime.now()
    return project


class TestCreateProject:
    async def test_create_project_success(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
        mock_project: MagicMock,
    ) -> None:
        obj_in = ProjectCreate(
            project_name="new-project",
            project_code="PRJ-TEST01-202606-0002",
            status="planning",
        )

        with patch(
            "src.crud.project.project_crud.get_by_code",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch(
                "src.crud.project.project_crud.create",
                new_callable=AsyncMock,
                return_value=mock_project,
            ):
                result = await project_service.create_project(mock_db, obj_in=obj_in)

        assert result is not None

    async def test_create_project_auto_generates_code(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
        mock_project: MagicMock,
    ) -> None:
        obj_in = ProjectCreate(
            project_name="new-project",
            project_code=None,
            status="planning",
            manager_party_id="operator-party-1",
        )

        with patch.object(
            project_service,
            "_resolve_operator_party_for_code",
            new_callable=AsyncMock,
            return_value=("operator-party-1", "TEST01"),
        ):
            with patch(
                "src.services.project.service.project_crud.get_by_code",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with patch.object(
                    project_service,
                    "generate_project_code",
                    new_callable=AsyncMock,
                    return_value="PRJ-TEST01-202606-0003",
                ):
                    with patch(
                        "src.crud.project.project_crud.create",
                        new_callable=AsyncMock,
                        return_value=mock_project,
                    ):
                        result = await project_service.create_project(
                            mock_db, obj_in=obj_in
                        )

        assert result is not None

    async def test_create_project_duplicate_code(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
        mock_project: MagicMock,
    ) -> None:
        obj_in = ProjectCreate(
            project_name="new-project",
            project_code="PRJ-TEST01-202606-0001",
            status="planning",
        )

        with patch(
            "src.crud.project.project_crud.get_by_code",
            new_callable=AsyncMock,
            return_value=mock_project,
        ):
            with pytest.raises(DuplicateResourceError):
                await project_service.create_project(mock_db, obj_in=obj_in)

    async def test_create_project_with_user(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
        mock_project: MagicMock,
    ) -> None:
        obj_in = ProjectCreate(
            project_name="new-project",
            project_code="PRJ-TEST01-202606-0002",
            status="planning",
        )

        with patch(
            "src.crud.project.project_crud.get_by_code",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch(
                "src.crud.project.project_crud.create",
                new_callable=AsyncMock,
                return_value=mock_project,
            ):
                result = await project_service.create_project(
                    mock_db,
                    obj_in=obj_in,
                    created_by="user_123",
                )

        assert result is not None

    async def test_create_project_should_reject_party_relations_write(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
        mock_project: MagicMock,
    ) -> None:
        obj_in = ProjectCreate(
            project_name="new-project",
            project_code="PRJ-TEST01-202606-0010",
            status="planning",
            party_relations=[
                {
                    "party_id": "ownership-001",
                    "relation_type": "owner",
                    "is_primary": True,
                    "is_active": True,
                }
            ],
        )

        mock_db.add.reset_mock()
        mock_db.execute.reset_mock()

        with patch(
            "src.crud.project.project_crud.get_by_code",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch(
                "src.crud.project.project_crud.create",
                new_callable=AsyncMock,
                return_value=mock_project,
            ):
                with pytest.raises(
                    OperationNotAllowedError,
                    match="party_relations",
                ):
                    await project_service.create_project(
                        mock_db,
                        obj_in=obj_in,
                        created_by="user_123",
                    )

            mock_db.execute.assert_not_awaited()
            mock_db.add.assert_not_called()

    async def test_create_project_should_not_touch_relation_table_when_party_relations_missing(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
        mock_project: MagicMock,
    ) -> None:
        obj_in = ProjectCreate(
            project_name="new-project",
            project_code="PRJ-TEST01-202606-0011",
            status="planning",
        )

        mock_db.add.reset_mock()
        mock_db.execute.reset_mock()

        with patch(
            "src.crud.project.project_crud.get_by_code",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch(
                "src.crud.project.project_crud.create",
                new_callable=AsyncMock,
                return_value=mock_project,
            ):
                await project_service.create_project(
                    mock_db,
                    obj_in=obj_in,
                    created_by="user_123",
                )

        mock_db.execute.assert_not_awaited()
        mock_db.add.assert_not_called()


class TestUpdateProject:
    async def test_update_project_basic(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
        mock_project: MagicMock,
    ) -> None:
        obj_in = ProjectUpdate(project_name="updated-project")

        with patch(
            "src.crud.project.project_crud.get",
            new_callable=AsyncMock,
            return_value=mock_project,
        ):
            with patch(
                "src.crud.project.project_crud.update",
                new_callable=AsyncMock,
                return_value=mock_project,
            ):
                result = await project_service.update_project(
                    mock_db, project_id="project_123", obj_in=obj_in
                )

        assert result is not None

    async def test_update_project_not_found(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        obj_in = ProjectUpdate(project_name="updated-project")

        with patch(
            "src.crud.project.project_crud.get",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(ResourceNotFoundError):
                await project_service.update_project(
                    mock_db, project_id="nonexistent", obj_in=obj_in
                )

    async def test_update_project_with_user(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
        mock_project: MagicMock,
    ) -> None:
        obj_in = ProjectUpdate(status="active")

        with patch(
            "src.crud.project.project_crud.get",
            new_callable=AsyncMock,
            return_value=mock_project,
        ):
            with patch(
                "src.crud.project.project_crud.update",
                new_callable=AsyncMock,
                return_value=mock_project,
            ):
                result = await project_service.update_project(
                    mock_db,
                    project_id="project_123",
                    obj_in=obj_in,
                    updated_by="user_123",
                )

        assert result is not None

    async def test_update_project_should_reject_party_relations_write(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
        mock_project: MagicMock,
    ) -> None:
        obj_in = ProjectUpdate(
            status="active",
            party_relations=[
                {
                    "party_id": "ownership-001",
                    "relation_type": "owner",
                    "is_active": True,
                },
                {
                    "party_id": "ownership-002",
                    "relation_type": "owner",
                    "is_active": True,
                },
                {
                    "party_id": "ownership-003",
                    "relation_type": "owner",
                    "is_active": False,
                },
                {
                    "party_id": "ownership-001",
                    "relation_type": "owner",
                    "is_active": False,
                },
            ],
        )

        mock_db.add.reset_mock()
        mock_db.execute.reset_mock()

        with patch(
            "src.crud.project.project_crud.get",
            new_callable=AsyncMock,
            return_value=mock_project,
        ):
            with patch(
                "src.crud.project.project_crud.update",
                new_callable=AsyncMock,
                return_value=mock_project,
            ) as mock_update:
                with pytest.raises(
                    OperationNotAllowedError,
                    match="party_relations",
                ):
                    await project_service.update_project(
                        mock_db,
                        project_id="project_123",
                        obj_in=obj_in,
                        updated_by="user_123",
                    )

        mock_update.assert_not_awaited()
        mock_db.execute.assert_not_awaited()
        mock_db.add.assert_not_called()

    async def test_update_project_should_not_replace_party_relations_when_not_provided(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
        mock_project: MagicMock,
    ) -> None:
        obj_in = ProjectUpdate(status="active")

        mock_db.add.reset_mock()
        mock_db.execute.reset_mock()

        with patch(
            "src.crud.project.project_crud.get",
            new_callable=AsyncMock,
            return_value=mock_project,
        ):
            with patch(
                "src.crud.project.project_crud.update",
                new_callable=AsyncMock,
                return_value=mock_project,
            ):
                await project_service.update_project(
                    mock_db,
                    project_id="project_123",
                    obj_in=obj_in,
                    updated_by="user_123",
                )

        mock_db.execute.assert_not_awaited()
        mock_db.add.assert_not_called()

    async def test_update_project_should_reject_empty_party_relations_write(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
        mock_project: MagicMock,
    ) -> None:
        obj_in = ProjectUpdate(status="active", party_relations=[])

        mock_db.add.reset_mock()
        mock_db.execute.reset_mock()

        with patch(
            "src.crud.project.project_crud.get",
            new_callable=AsyncMock,
            return_value=mock_project,
        ):
            with patch(
                "src.crud.project.project_crud.update",
                new_callable=AsyncMock,
                return_value=mock_project,
            ) as mock_update:
                with pytest.raises(
                    OperationNotAllowedError,
                    match="party_relations",
                ):
                    await project_service.update_project(
                        mock_db,
                        project_id="project_123",
                        obj_in=obj_in,
                        updated_by="user_123",
                    )

        mock_update.assert_not_awaited()
        mock_db.execute.assert_not_awaited()
        mock_db.add.assert_not_called()


class TestToggleStatus:
    async def test_toggle_status_from_active_to_paused(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
        mock_project: MagicMock,
    ) -> None:
        mock_project.status = "active"

        with patch(
            "src.crud.project.project_crud.get",
            new_callable=AsyncMock,
            return_value=mock_project,
        ):
            result = await project_service.toggle_status(
                mock_db, project_id="project_123"
            )

        assert result is not None
        assert result.status == "paused"
        mock_db.commit.assert_awaited_once()

    async def test_toggle_status_from_paused_to_active(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
        mock_project: MagicMock,
    ) -> None:
        mock_project.status = "paused"

        with patch(
            "src.crud.project.project_crud.get",
            new_callable=AsyncMock,
            return_value=mock_project,
        ):
            result = await project_service.toggle_status(
                mock_db, project_id="project_123"
            )

        assert result is not None
        assert result.status == "active"
        mock_db.commit.assert_awaited_once()

    async def test_toggle_status_from_planning_to_paused(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
        mock_project: MagicMock,
    ) -> None:
        mock_project.status = "planning"

        with patch(
            "src.crud.project.project_crud.get",
            new_callable=AsyncMock,
            return_value=mock_project,
        ):
            result = await project_service.toggle_status(
                mock_db, project_id="project_123"
            )

        assert result is not None
        assert result.status == "paused"

    async def test_toggle_status_unknown_status(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
        mock_project: MagicMock,
    ) -> None:
        mock_project.status = "unknown"

        with patch(
            "src.crud.project.project_crud.get",
            new_callable=AsyncMock,
            return_value=mock_project,
        ):
            result = await project_service.toggle_status(
                mock_db, project_id="project_123"
            )

        assert result is not None
        assert result.status == "active"

    async def test_toggle_status_not_found(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        with patch(
            "src.crud.project.project_crud.get",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(ResourceNotFoundError):
                await project_service.toggle_status(mock_db, project_id="nonexistent")

    async def test_toggle_status_with_user(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
        mock_project: MagicMock,
    ) -> None:
        mock_project.status = "active"

        with patch(
            "src.crud.project.project_crud.get",
            new_callable=AsyncMock,
            return_value=mock_project,
        ):
            result = await project_service.toggle_status(
                mock_db,
                project_id="project_123",
                updated_by="user_123",
            )

        assert result is not None
        assert result.updated_by == "user_123"


class TestDeleteProject:
    async def test_delete_project_success(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
        mock_project: MagicMock,
    ) -> None:
        with patch(
            "src.crud.project.project_crud.get_asset_count",
            new_callable=AsyncMock,
            return_value=0,
        ):
            with patch(
                "src.crud.project.project_crud.get",
                new_callable=AsyncMock,
                return_value=mock_project,
            ):
                with patch(
                    "src.crud.project.project_crud.remove", new_callable=AsyncMock
                ) as mock_remove:
                    await project_service.delete_project(
                        mock_db, project_id="project_123"
                    )

        mock_remove.assert_awaited_once_with(mock_db, id="project_123")

    async def test_delete_project_with_assets_fails(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        with patch(
            "src.crud.project.project_crud.get_asset_count",
            new_callable=AsyncMock,
            return_value=5,
        ):
            with pytest.raises(OperationNotAllowedError):
                await project_service.delete_project(mock_db, project_id="project_123")

    async def test_delete_project_not_found(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        with patch(
            "src.crud.project.project_crud.get_asset_count",
            new_callable=AsyncMock,
            return_value=0,
        ):
            with patch(
                "src.crud.project.project_crud.get",
                new_callable=AsyncMock,
                return_value=None,
            ):
                await project_service.delete_project(mock_db, project_id="nonexistent")


class TestGenerateProjectCode:
    async def test_generate_code_first_of_month(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = None
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await project_service.generate_project_code(
            mock_db, operator_party_code="test01"
        )

        assert result.startswith("PRJ-")
        assert len(result) > 9

    async def test_generate_code_sequence_increment(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        mock_last_project = MagicMock()
        mock_last_project.project_code = "PRJ-TEST01-202606-0001"

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.first.return_value = mock_last_project
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await project_service.generate_project_code(
            mock_db, operator_party_code="test01"
        )

        assert result.endswith("-0002")

    async def test_generate_code_with_name(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        with patch(
            "src.crud.project.project_crud.get_by_code",
            new_callable=AsyncMock,
            return_value=None,
        ):
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            mock_scalars.first.return_value = None
            mock_result.scalars.return_value = mock_scalars
            mock_db.execute = AsyncMock(return_value=mock_result)

            result = await project_service.generate_project_code(
                mock_db,
                name="test-project",
                operator_party_code="test01",
            )

        assert result is not None

    async def test_generate_code_uses_operator_segment_month_and_seq4(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        mock_last_project = MagicMock()
        mock_last_project.project_code = "PRJ-OPER0001-202606-0007"

        with patch.object(
            project_service,
            "_utcnow_naive",
            return_value=datetime(2026, 6, 15),
        ):
            with patch(
                "src.services.project.service.project_crud.get_latest_by_code_prefix",
                new_callable=AsyncMock,
                return_value=mock_last_project,
            ) as mock_get_latest:
                result = await project_service.generate_project_code(
                    mock_db,
                    operator_party_id="operator-party-1",
                    operator_party_code="oper-0001",
                )

        assert result == "PRJ-OPER0001-202606-0008"
        prefix = mock_get_latest.await_args.kwargs["prefix"]
        assert prefix == "PRJ-OPER0001-202606-"

    async def test_generate_code_acquires_prefix_lock_before_latest_lookup(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        with patch.object(
            project_service,
            "_utcnow_naive",
            return_value=datetime(2026, 6, 15),
        ):
            with patch(
                "src.services.project.service.project_crud.acquire_code_generation_lock",
                new_callable=AsyncMock,
            ) as mock_lock:
                with patch(
                    "src.services.project.service.project_crud.get_latest_by_code_prefix",
                    new_callable=AsyncMock,
                    return_value=None,
                ) as mock_get_latest:
                    result = await project_service.generate_project_code(
                        mock_db,
                        operator_party_id="operator-party-1",
                        operator_party_code="oper-0001",
                    )

        assert result == "PRJ-OPER0001-202606-0001"
        assert mock_lock.await_args.kwargs["prefix"] == "PRJ-OPER0001-202606-"
        assert mock_get_latest.await_args.kwargs["prefix"] == "PRJ-OPER0001-202606-"


class TestSearchProjects:
    async def test_search_projects_basic(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        search_params = ProjectSearchRequest(keyword="project", page=1, page_size=10)
        mock_items = [MagicMock(), MagicMock()]

        with patch(
            "src.crud.project.project_crud.search",
            new_callable=AsyncMock,
            return_value=(mock_items, 2),
        ):
            result = await project_service.search_projects(mock_db, search_params)

        assert result["total"] == 2
        assert result["page"] == 1
        assert result["page_size"] == 10
        assert result["pages"] == 1

    async def test_search_projects_pagination(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        search_params = ProjectSearchRequest(keyword="", page=2, page_size=20)
        mock_items = [MagicMock()]

        with patch(
            "src.crud.project.project_crud.search",
            new_callable=AsyncMock,
            return_value=(mock_items, 25),
        ):
            result = await project_service.search_projects(mock_db, search_params)

        assert result["page"] == 2
        assert result["pages"] == 2

    async def test_search_projects_empty(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        search_params = ProjectSearchRequest(keyword="missing", page=1, page_size=10)

        with patch(
            "src.crud.project.project_crud.search",
            new_callable=AsyncMock,
            return_value=([], 0),
        ):
            result = await project_service.search_projects(mock_db, search_params)

        assert result["total"] == 0
        assert result["items"] == []


class TestProjectDropdownOptions:
    async def test_get_project_dropdown_options_filters_by_status(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
    ) -> None:
        active_project = MagicMock(spec=Project)
        active_project.id = "p1"
        active_project.project_name = "妞ゅ湱娲癆"
        active_project.project_code = "PRJ-TEST01-000001"
        active_project.status = "active"

        planning_project = MagicMock(spec=Project)
        planning_project.id = "p2"
        planning_project.project_name = "妞ゅ湱娲癇"
        planning_project.project_code = "PRJ-TEST01-000002"
        planning_project.status = "planning"

        with patch.object(
            project_service,
            "_resolve_party_filter",
            new=AsyncMock(return_value=None),
        ):
            with patch(
                "src.crud.project.project_crud.get_multi",
                new_callable=AsyncMock,
                return_value=[active_project, planning_project],
            ) as mock_get_multi:
                result = await project_service.get_project_dropdown_options(
                    mock_db,
                    status="active",
                )

        mock_get_multi.assert_awaited_once_with(
            mock_db,
            skip=0,
            limit=1000,
            status="active",
            party_filter=None,
        )
        assert [item["id"] for item in result] == ["p1", "p2"]
        assert all(
            set(item.keys()) == {"id", "project_name", "project_code"}
            for item in result
        )

    async def test_get_project_dropdown_options_uses_all_status_when_filter_is_empty(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
    ) -> None:
        with patch.object(
            project_service,
            "_resolve_party_filter",
            new=AsyncMock(return_value=None),
        ):
            with patch(
                "src.crud.project.project_crud.get_multi",
                new_callable=AsyncMock,
                return_value=[],
            ) as mock_get_multi:
                await project_service.get_project_dropdown_options(
                    mock_db,
                    status="",
                )

        mock_get_multi.assert_awaited_once_with(
            mock_db,
            skip=0,
            limit=1000,
            status=None,
            party_filter=None,
        )


class TestGetProjectById:
    async def test_get_project_by_id_resolves_tenant_filter(
        self,
        project_service: ProjectService,
        mock_db: MagicMock,
        mock_project: MagicMock,
    ) -> None:
        party_filter = PartyFilter(party_ids=["org-1"])

        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=party_filter),
            ) as mock_resolve,
            patch(
                "src.crud.project.project_crud.get",
                new_callable=AsyncMock,
                return_value=mock_project,
            ) as mock_get,
        ):
            result = await project_service.get_project_by_id(
                mock_db,
                project_id="project_123",
                current_user_id="user_1",
            )

        assert result == mock_project
        mock_resolve.assert_awaited_once_with(
            mock_db,
            current_user_id="user_1",
            party_filter=None,
        )
        mock_get.assert_awaited_once_with(
            db=mock_db,
            id="project_123",
            party_filter=party_filter,
        )

    async def test_get_project_by_id_fail_closed_when_no_accessible_org(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        with patch.object(
            project_service,
            "_resolve_party_filter",
            new=AsyncMock(return_value=PartyFilter(party_ids=[])),
        ):
            with patch(
                "src.crud.project.project_crud.get",
                new_callable=AsyncMock,
            ) as mock_get:
                result = await project_service.get_project_by_id(
                    mock_db,
                    project_id="project_123",
                    current_user_id="user_1",
                )

        assert result is None
        mock_get.assert_not_awaited()


class TestTenantFilterResolution:
    async def test_resolve_party_filter_disables_legacy_default_org_fallback(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        resolved_filter = PartyFilter(party_ids=["party-1"])

        with patch(
            "src.services.project.service.resolve_user_party_filter",
            new=AsyncMock(return_value=resolved_filter),
        ) as mock_resolve:
            party_filter = await project_service._resolve_party_filter(
                mock_db,
                current_user_id="user-1",
            )

        assert party_filter == resolved_filter
        mock_resolve.assert_awaited_once_with(
            mock_db,
            current_user_id="user-1",
            party_filter=None,
            logger=ANY,
            allow_legacy_default_organization_fallback=False,
        )

    async def test_resolve_party_filter_uses_user_party_bindings(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        """Resolve filter scope from user party bindings."""
        binding = MagicMock()
        binding.party_id = "party-1"

        with patch(
            "src.services.party_scope.party_crud.get_user_bindings",
            new=AsyncMock(return_value=[binding]),
        ):
            party_filter = await project_service._resolve_party_filter(
                mock_db,
                current_user_id="user-1",
            )

        assert party_filter is not None
        assert party_filter.party_ids == ["party-1"]

    async def test_resolve_party_filter_keeps_bindings_when_org_lookup_fails(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        """Return party binding scope when organization lookup fails."""
        binding = MagicMock()
        binding.party_id = "party-1"

        with patch(
            "src.services.party_scope.party_crud.get_user_bindings",
            new=AsyncMock(return_value=[binding]),
        ):
            party_filter = await project_service._resolve_party_filter(
                mock_db,
                current_user_id="user-1",
            )

        assert party_filter is not None
        assert party_filter.party_ids == ["party-1"]


class TestGetProjectActiveAssets:
    async def test_get_project_active_assets_filters_inactive(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        active_binding = SimpleNamespace(asset_id="asset-active", valid_to=None)
        inactive_binding = SimpleNamespace(
            asset_id="asset-inactive",
            valid_to=datetime.now(),
        )
        active_asset = SimpleNamespace(
            id="asset-active",
            data_status=DataStatusValues.ASSET_NORMAL,
            rentable_area=Decimal("100.00"),
            rented_area=Decimal("80.00"),
        )
        inactive_asset = SimpleNamespace(
            id="asset-inactive",
            data_status=DataStatusValues.ASSET_NORMAL,
            rentable_area=Decimal("30.00"),
            rented_area=Decimal("10.00"),
        )

        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                project_service,
                "get_project_by_id",
                new=AsyncMock(return_value=SimpleNamespace(id="project-1")),
            ),
            patch(
                "src.services.project.service.project_asset_crud.get_project_assets",
                new=AsyncMock(return_value=[active_binding, inactive_binding]),
            ) as mock_get_project_assets,
            patch(
                "src.services.project.service.asset_crud.get_multi_by_ids_async",
                new=AsyncMock(return_value=[active_asset, inactive_asset]),
            ),
        ):
            assets, summary = await project_service.get_project_active_assets(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        mock_get_project_assets.assert_awaited_once_with(
            mock_db,
            project_id="project-1",
            active_only=True,
        )
        assert [asset.id for asset in assets] == ["asset-active"]
        assert summary.total_assets == 1
        assert summary.total_rentable_area == 100.0
        assert summary.total_rented_area == 80.0
        assert summary.occupancy_rate == 80.0

    async def test_get_project_active_assets_excludes_deleted_assets(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        project_assets = [SimpleNamespace(asset_id="asset-1", valid_to=None)]
        normal_asset = SimpleNamespace(
            id="asset-1",
            data_status=DataStatusValues.ASSET_NORMAL,
            rentable_area=Decimal("50.00"),
            rented_area=Decimal("30.00"),
        )
        deleted_asset = SimpleNamespace(
            id="asset-2",
            data_status=DataStatusValues.ASSET_DELETED,
            rentable_area=Decimal("60.00"),
            rented_area=Decimal("50.00"),
        )
        abnormal_asset = SimpleNamespace(
            id="asset-3",
            data_status=DataStatusValues.ASSET_ABNORMAL,
            rentable_area=Decimal("70.00"),
            rented_area=Decimal("20.00"),
        )

        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                project_service,
                "get_project_by_id",
                new=AsyncMock(return_value=SimpleNamespace(id="project-1")),
            ),
            patch(
                "src.services.project.service.project_asset_crud.get_project_assets",
                new=AsyncMock(return_value=project_assets),
            ),
            patch(
                "src.services.project.service.asset_crud.get_multi_by_ids_async",
                new=AsyncMock(
                    return_value=[normal_asset, deleted_asset, abnormal_asset]
                ),
            ),
        ):
            assets, summary = await project_service.get_project_active_assets(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        assert [asset.id for asset in assets] == ["asset-1"]
        assert summary.total_assets == 1
        assert summary.total_rentable_area == 50.0
        assert summary.total_rented_area == 30.0
        assert summary.occupancy_rate == 60.0

    async def test_get_project_active_assets_summary_zero_rentable_area(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        project_assets = [SimpleNamespace(asset_id="asset-1", valid_to=None)]
        zero_rentable_asset = SimpleNamespace(
            id="asset-1",
            data_status=DataStatusValues.ASSET_NORMAL,
            rentable_area=Decimal("0.00"),
            rented_area=Decimal("12.00"),
        )

        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                project_service,
                "get_project_by_id",
                new=AsyncMock(return_value=SimpleNamespace(id="project-1")),
            ),
            patch(
                "src.services.project.service.project_asset_crud.get_project_assets",
                new=AsyncMock(return_value=project_assets),
            ),
            patch(
                "src.services.project.service.asset_crud.get_multi_by_ids_async",
                new=AsyncMock(return_value=[zero_rentable_asset]),
            ),
        ):
            assets, summary = await project_service.get_project_active_assets(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        assert len(assets) == 1
        assert summary.total_rentable_area == 0.0
        assert summary.total_rented_area == 12.0
        assert summary.occupancy_rate == 0.0

    async def test_get_project_active_assets_empty_project(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                project_service,
                "get_project_by_id",
                new=AsyncMock(return_value=SimpleNamespace(id="project-1")),
            ),
            patch(
                "src.services.project.service.project_asset_crud.get_project_assets",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.services.project.service.asset_crud.get_multi_by_ids_async",
                new=AsyncMock(return_value=[]),
            ) as mock_get_assets,
        ):
            assets, summary = await project_service.get_project_active_assets(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        mock_get_assets.assert_not_awaited()
        assert assets == []
        assert summary.total_assets == 0
        assert summary.total_rentable_area == 0.0
        assert summary.total_rented_area == 0.0
        assert summary.occupancy_rate == 0.0

    async def test_get_project_active_assets_project_not_found(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                project_service,
                "get_project_by_id",
                new=AsyncMock(return_value=None),
            ),
        ):
            with pytest.raises(ResourceNotFoundError):
                await project_service.get_project_active_assets(
                    mock_db,
                    project_id="missing-project",
                    current_user_id="user-1",
                )


class TestGetProjectContractRelations:
    async def test_get_project_contract_relations_returns_display_projection(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        lease_group = SimpleNamespace(
            contract_group_id="group-lease",
            project_id="project-1",
            group_code="GRP-LEASE",
            revenue_mode=RevenueMode.LEASE,
            owner_party_id="owner-1",
            operator_party_id="manager-1",
            assets=[SimpleNamespace(id="asset-1")],
            risk_tags=["閸掔増婀℃搴ㄦ珦"],
        )
        agency_group = SimpleNamespace(
            contract_group_id="group-agency",
            project_id="project-1",
            group_code="GRP-AGENCY",
            revenue_mode=RevenueMode.AGENCY,
            owner_party_id="owner-2",
            operator_party_id="manager-1",
            assets=[SimpleNamespace(id="asset-2")],
            risk_tags=None,
        )

        async def mock_list_by_group(_db, *, group_id: str):
            if group_id == "group-lease":
                return [
                    SimpleNamespace(
                        contract_id="contract-upstream",
                        group_relation_type=GroupRelationType.UPSTREAM,
                        status=ContractLifecycleStatus.ACTIVE,
                        data_status=DataStatusValues.ASSET_NORMAL,
                    ),
                    SimpleNamespace(
                        contract_id="contract-downstream",
                        group_relation_type=GroupRelationType.DOWNSTREAM,
                        status=ContractLifecycleStatus.DRAFT,
                        data_status=DataStatusValues.ASSET_NORMAL,
                    ),
                ]
            return [
                SimpleNamespace(
                    contract_id="contract-entrusted",
                    group_relation_type=GroupRelationType.ENTRUSTED,
                    status=ContractLifecycleStatus.ACTIVE,
                    data_status=DataStatusValues.ASSET_NORMAL,
                ),
                SimpleNamespace(
                    contract_id="contract-direct",
                    group_relation_type=GroupRelationType.DIRECT_LEASE,
                    status=ContractLifecycleStatus.DRAFT,
                    data_status=DataStatusValues.ASSET_NORMAL,
                ),
            ]

        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                project_service,
                "get_project_by_id",
                new=AsyncMock(return_value=SimpleNamespace(id="project-1")),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_by_project",
                new=AsyncMock(return_value=[lease_group, agency_group]),
            ),
            patch(
                "src.services.project.service.contract_crud.list_by_group",
                new=AsyncMock(side_effect=mock_list_by_group),
            ),
        ):
            response = await project_service.get_project_contract_relations(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        assert response.total == 2
        lease_relation = response.items[0]
        assert lease_relation.contract_relation_id == "group-lease"
        assert lease_relation.display_name == "GRP-LEASE"
        assert lease_relation.revenue_mode == "lease"
        assert lease_relation.relation_kind == "lease_sublease"
        assert lease_relation.asset_ids == ["asset-1"]
        assert lease_relation.primary_contract_ids == ["contract-upstream"]
        assert lease_relation.terminal_contract_ids == ["contract-downstream"]
        assert lease_relation.derived_status
        assert lease_relation.risk_tags

        agency_relation = response.items[1]
        assert agency_relation.relation_kind == "agency_operation"
        assert agency_relation.primary_contract_ids == ["contract-entrusted"]
        assert agency_relation.terminal_contract_ids == ["contract-direct"]


class TestGetProjectRisks:
    @pytest.fixture(autouse=True)
    def _resolved_party_filter(self, project_service: ProjectService):
        async def _resolve(
            _db: MagicMock,
            *,
            current_user_id: str | None = None,
            party_filter: PartyFilter | None = None,
        ) -> PartyFilter | None:
            _ = current_user_id
            return party_filter

        with patch.object(
            project_service,
            "_resolve_party_filter",
            new=AsyncMock(side_effect=_resolve),
        ):
            yield

    async def test_get_project_risks_returns_manual_relation_tags(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        from src.schemas.project import (
            ProjectContractRelationItem,
            ProjectContractRelationsResponse,
        )

        relations = ProjectContractRelationsResponse(
            items=[
                ProjectContractRelationItem(
                    contract_relation_id="group-lease",
                    project_id="project-1",
                    display_name="GRP-LEASE",
                    revenue_mode="lease",
                    relation_kind="lease_sublease",
                    owner_party_id="owner-1",
                    operator_party_id="manager-1",
                    asset_ids=["asset-1"],
                    primary_contract_ids=[],
                    terminal_contract_ids=["contract-downstream"],
                    derived_status="pending",
                    risk_tags=["閸掔増婀℃搴ㄦ珦"],
                )
            ],
            total=1,
        )

        with (
            patch.object(
                project_service,
                "get_project_contract_relations",
                new=AsyncMock(return_value=relations),
            ),
            patch.object(
                project_service,
                "_load_project_active_assets",
                new=AsyncMock(return_value=([], None)),
            ),
            patch(
                "src.services.project.service.contract_crud.list_by_group",
                new=AsyncMock(return_value=[]),
            ),
        ):
            response = await project_service.get_project_risks(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        assert response.total == 1
        assert response.items[0].message == relations.items[0].risk_tags[0]
        assert response.items[0].risk_type == "manual_tag"

    async def test_get_project_risks_returns_contract_expiring_reminders(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        from src.schemas.project import (
            ProjectContractRelationItem,
            ProjectContractRelationsResponse,
        )

        relations = ProjectContractRelationsResponse(
            items=[
                ProjectContractRelationItem(
                    contract_relation_id="group-lease",
                    project_id="project-1",
                    display_name="GRP-LEASE",
                    revenue_mode="lease",
                    relation_kind="lease_sublease",
                    owner_party_id="owner-1",
                    operator_party_id="manager-1",
                    asset_ids=["asset-1"],
                    primary_contract_ids=["contract-upstream"],
                    terminal_contract_ids=["contract-downstream"],
                    derived_status="active",
                    risk_tags=[],
                )
            ],
            total=1,
        )
        expiring_contract = SimpleNamespace(
            contract_id="contract-downstream",
            contract_number="CN-DOWNSTREAM-001",
            group_relation_type=GroupRelationType.DOWNSTREAM,
            status=ContractLifecycleStatus.ACTIVE,
            effective_to=date(2026, 6, 10),
        )
        far_future_contract = SimpleNamespace(
            contract_id="contract-upstream",
            contract_number="CN-UPSTREAM-001",
            group_relation_type=GroupRelationType.UPSTREAM,
            status=ContractLifecycleStatus.ACTIVE,
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
            assets=[SimpleNamespace(id="asset-1")],
        )
        expiring_contract.effective_from = date(2026, 2, 1)
        expiring_contract.assets = [SimpleNamespace(id="asset-1")]

        with (
            patch.object(
                project_service,
                "get_project_contract_relations",
                new=AsyncMock(return_value=relations),
            ),
            patch.object(
                project_service,
                "_load_project_active_assets",
                new=AsyncMock(return_value=([], None)),
            ),
            patch(
                "src.services.project.service.contract_crud.list_by_group",
                new=AsyncMock(return_value=[expiring_contract, far_future_contract]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_ledger_entries_by_contract",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_service_fee_entries_by_group",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.services.project.service.ProjectService._today",
                return_value=date(2026, 5, 14),
            ),
        ):
            response = await project_service.get_project_risks(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        assert response.total == 1
        assert response.items[0].risk_type == "contract_expiring"
        assert response.items[0].severity == "warning"
        assert "CN-DOWNSTREAM-001" in response.items[0].message
        assert "2026-06-10" in response.items[0].message

    async def test_get_project_risks_returns_overdue_payment_risk(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        from src.schemas.project import (
            ProjectContractRelationItem,
            ProjectContractRelationsResponse,
        )

        relations = ProjectContractRelationsResponse(
            items=[
                ProjectContractRelationItem(
                    contract_relation_id="group-lease",
                    project_id="project-1",
                    display_name="GRP-LEASE",
                    revenue_mode="lease",
                    relation_kind="lease_sublease",
                    owner_party_id="owner-1",
                    operator_party_id="manager-1",
                    asset_ids=["asset-1"],
                    primary_contract_ids=["contract-upstream"],
                    terminal_contract_ids=["contract-downstream"],
                    derived_status="active",
                    risk_tags=[],
                )
            ],
            total=1,
        )
        downstream_contract = SimpleNamespace(
            contract_id="contract-downstream",
            contract_number="CN-DOWNSTREAM-001",
            group_relation_type=GroupRelationType.DOWNSTREAM,
            status=ContractLifecycleStatus.ACTIVE,
            effective_to=date(2026, 12, 31),
        )
        upstream_contract = SimpleNamespace(
            contract_id="contract-upstream",
            contract_number="CN-UPSTREAM-001",
            group_relation_type=GroupRelationType.UPSTREAM,
            status=ContractLifecycleStatus.ACTIVE,
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
            assets=[SimpleNamespace(id="asset-1")],
        )
        downstream_contract.effective_from = date(2026, 2, 1)
        downstream_contract.assets = [SimpleNamespace(id="asset-1")]
        overdue_entry = SimpleNamespace(
            amount_due=Decimal("1000.00"),
            paid_amount=Decimal("400.00"),
            payment_status="unpaid",
            due_date=date(2026, 5, 1),
            attributed_owner_party_id="owner-1",
            attributed_operator_party_id="manager-1",
        )
        hidden_overdue_entry = SimpleNamespace(
            amount_due=Decimal("900.00"),
            paid_amount=Decimal("0.00"),
            payment_status="unpaid",
            due_date=date(2026, 5, 1),
            attributed_owner_party_id="owner-hidden",
            attributed_operator_party_id="manager-hidden",
        )

        async def mock_list_ledger_entries_by_contract(
            _db: MagicMock, *, contract_id: str
        ) -> list[SimpleNamespace]:
            return (
                [overdue_entry, hidden_overdue_entry]
                if contract_id == "contract-downstream"
                else []
            )

        with (
            patch.object(
                project_service,
                "get_project_contract_relations",
                new=AsyncMock(return_value=relations),
            ),
            patch.object(
                project_service,
                "_load_project_active_assets",
                new=AsyncMock(return_value=([], None)),
            ),
            patch(
                "src.services.project.service.contract_crud.list_by_group",
                new=AsyncMock(return_value=[downstream_contract, upstream_contract]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_ledger_entries_by_contract",
                new=AsyncMock(side_effect=mock_list_ledger_entries_by_contract),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_rent_terms_by_contract",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_service_fee_entries_by_group",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.services.project.service.ProjectService._today",
                return_value=date(2026, 5, 14),
            ),
        ):
            response = await project_service.get_project_risks(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
                party_filter=PartyFilter(
                    party_ids=["owner-1"],
                    filter_mode="owner",
                    owner_party_ids=["owner-1"],
                ),
            )

        assert response.total == 1
        assert response.items[0].risk_type == "payment_overdue"
        assert "CN-DOWNSTREAM-001" in response.items[0].message
        assert "¥600.00" in response.items[0].message
        assert "600.00" in response.items[0].message

    async def test_get_project_risks_returns_stale_paid_ledger_risk_after_correction(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        from src.schemas.project import (
            ProjectContractRelationItem,
            ProjectContractRelationsResponse,
        )

        relations = ProjectContractRelationsResponse(
            items=[
                ProjectContractRelationItem(
                    contract_relation_id="group-lease",
                    project_id="project-1",
                    display_name="GRP-LEASE",
                    revenue_mode="lease",
                    relation_kind="lease_sublease",
                    owner_party_id="owner-1",
                    operator_party_id="manager-1",
                    asset_ids=["asset-1"],
                    primary_contract_ids=["contract-upstream"],
                    terminal_contract_ids=["contract-downstream"],
                    derived_status="active",
                    risk_tags=[],
                )
            ],
            total=1,
        )
        downstream_contract = SimpleNamespace(
            contract_id="contract-downstream",
            contract_number="CN-DOWNSTREAM-001",
            group_relation_type=GroupRelationType.DOWNSTREAM,
            status=ContractLifecycleStatus.ACTIVE,
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
            lease_detail=SimpleNamespace(payment_cycle="鏈堜粯"),
        )
        stale_paid_entry = SimpleNamespace(
            entry_id="entry-jan",
            year_month="2026-01",
            amount_due=Decimal("1000.00"),
            due_date=date(2026, 1, 1),
            payment_status="paid",
            paid_amount=Decimal("1000.00"),
        )
        current_rent_term = SimpleNamespace(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            monthly_rent=Decimal("1200.00"),
            total_monthly_amount=Decimal("1200.00"),
            sort_order=1,
        )

        with (
            patch.object(
                project_service,
                "get_project_contract_relations",
                new=AsyncMock(return_value=relations),
            ),
            patch.object(
                project_service,
                "_load_project_active_assets",
                new=AsyncMock(return_value=([], None)),
            ),
            patch(
                "src.services.project.service.contract_crud.list_by_group",
                new=AsyncMock(return_value=[downstream_contract]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_ledger_entries_by_contract",
                new=AsyncMock(return_value=[stale_paid_entry]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_rent_terms_by_contract",
                new=AsyncMock(return_value=[current_rent_term]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_service_fee_entries_by_group",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.services.project.service.ProjectService._today",
                return_value=date(2026, 5, 14),
            ),
        ):
            response = await project_service.get_project_risks(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        assert response.total == 1
        assert response.items[0].risk_type == "ledger_stale_after_correction"
        assert response.items[0].contract_relation_id == "group-lease"
        assert "CN-DOWNSTREAM-001" in response.items[0].message

    async def test_get_project_risks_returns_stale_allocated_ledger_risk_after_correction(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        from src.schemas.project import (
            ProjectContractRelationItem,
            ProjectContractRelationsResponse,
        )

        relations = ProjectContractRelationsResponse(
            items=[
                ProjectContractRelationItem(
                    contract_relation_id="group-lease",
                    project_id="project-1",
                    display_name="GRP-LEASE",
                    revenue_mode="lease",
                    relation_kind="lease_sublease",
                    owner_party_id="owner-1",
                    operator_party_id="manager-1",
                    asset_ids=["asset-1"],
                    primary_contract_ids=[],
                    terminal_contract_ids=["contract-downstream"],
                    derived_status="active",
                    risk_tags=[],
                )
            ],
            total=1,
        )
        downstream_contract = SimpleNamespace(
            contract_id="contract-downstream",
            contract_number="CN-DOWNSTREAM-001",
            group_relation_type=GroupRelationType.DOWNSTREAM,
            status=ContractLifecycleStatus.ACTIVE,
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
            lease_detail=SimpleNamespace(payment_cycle="monthly"),
        )
        allocated_entry = SimpleNamespace(
            entry_id="entry-jan",
            year_month="2026-01",
            amount_due=Decimal("1000.00"),
            due_date=date(2026, 1, 1),
            payment_status="unpaid",
            paid_amount=Decimal("0.00"),
            active_allocation_count=1,
        )
        current_rent_term = SimpleNamespace(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            monthly_rent=Decimal("1200.00"),
            total_monthly_amount=Decimal("1200.00"),
            sort_order=1,
        )

        with (
            patch.object(
                project_service,
                "get_project_contract_relations",
                new=AsyncMock(return_value=relations),
            ),
            patch.object(
                project_service,
                "_load_project_active_assets",
                new=AsyncMock(return_value=([], None)),
            ),
            patch(
                "src.services.project.service.contract_crud.list_by_group",
                new=AsyncMock(return_value=[downstream_contract]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_ledger_entries_by_contract",
                new=AsyncMock(return_value=[allocated_entry]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_rent_terms_by_contract",
                new=AsyncMock(return_value=[current_rent_term]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_service_fee_entries_by_group",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.services.project.service.ProjectService._today",
                return_value=date(2026, 1, 1),
            ),
        ):
            response = await project_service.get_project_risks(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        assert response.total == 1
        assert response.items[0].risk_type == "ledger_stale_after_correction"
        assert response.items[0].contract_relation_id == "group-lease"
        assert "CN-DOWNSTREAM-001" in response.items[0].message

    async def test_get_project_risks_omits_stale_paid_ledger_risk_after_manual_alignment(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        from src.schemas.project import (
            ProjectContractRelationItem,
            ProjectContractRelationsResponse,
        )

        relations = ProjectContractRelationsResponse(
            items=[
                ProjectContractRelationItem(
                    contract_relation_id="group-lease",
                    project_id="project-1",
                    display_name="GRP-LEASE",
                    revenue_mode="lease",
                    relation_kind="lease_sublease",
                    owner_party_id="owner-1",
                    operator_party_id="manager-1",
                    asset_ids=["asset-1"],
                    primary_contract_ids=[],
                    terminal_contract_ids=["contract-downstream"],
                    derived_status="active",
                    risk_tags=[],
                )
            ],
            total=1,
        )
        downstream_contract = SimpleNamespace(
            contract_id="contract-downstream",
            contract_number="CN-DOWNSTREAM-001",
            group_relation_type=GroupRelationType.DOWNSTREAM,
            status=ContractLifecycleStatus.ACTIVE,
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
            lease_detail=SimpleNamespace(payment_cycle="鏈堜粯"),
        )
        aligned_paid_entry = SimpleNamespace(
            entry_id="entry-jan",
            year_month="2026-01",
            amount_due=Decimal("1200.00"),
            due_date=date(2026, 1, 1),
            payment_status="paid",
            paid_amount=Decimal("1200.00"),
        )
        current_rent_term = SimpleNamespace(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            monthly_rent=Decimal("1200.00"),
            total_monthly_amount=Decimal("1200.00"),
            sort_order=1,
        )

        with (
            patch.object(
                project_service,
                "get_project_contract_relations",
                new=AsyncMock(return_value=relations),
            ),
            patch.object(
                project_service,
                "_load_project_active_assets",
                new=AsyncMock(return_value=([], None)),
            ),
            patch(
                "src.services.project.service.contract_crud.list_by_group",
                new=AsyncMock(return_value=[downstream_contract]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_ledger_entries_by_contract",
                new=AsyncMock(return_value=[aligned_paid_entry]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_rent_terms_by_contract",
                new=AsyncMock(return_value=[current_rent_term]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_service_fee_entries_by_group",
                new=AsyncMock(return_value=[]),
            ),
        ):
            response = await project_service.get_project_risks(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        assert [
            item.risk_type
            for item in response.items
            if item.risk_type == "ledger_stale_after_correction"
        ] == []

    async def test_get_project_risks_derives_stale_paid_ledger_risk_for_primary_contracts(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        from src.schemas.project import (
            ProjectContractRelationItem,
            ProjectContractRelationsResponse,
        )

        relations = ProjectContractRelationsResponse(
            items=[
                ProjectContractRelationItem(
                    contract_relation_id="group-lease",
                    project_id="project-1",
                    display_name="GRP-LEASE",
                    revenue_mode="lease",
                    relation_kind="lease_sublease",
                    owner_party_id="owner-1",
                    operator_party_id="manager-1",
                    asset_ids=["asset-1"],
                    primary_contract_ids=["contract-upstream"],
                    terminal_contract_ids=[],
                    derived_status="active",
                    risk_tags=[],
                )
            ],
            total=1,
        )
        upstream_contract = SimpleNamespace(
            contract_id="contract-upstream",
            contract_number="CN-UPSTREAM-001",
            group_relation_type=GroupRelationType.UPSTREAM,
            status=ContractLifecycleStatus.ACTIVE,
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 12, 31),
            lease_detail=SimpleNamespace(payment_cycle="鏈堜粯"),
        )
        stale_paid_entry = SimpleNamespace(
            entry_id="entry-jan",
            year_month="2026-01",
            amount_due=Decimal("1000.00"),
            due_date=date(2026, 1, 1),
            payment_status="paid",
            paid_amount=Decimal("1000.00"),
        )
        current_rent_term = SimpleNamespace(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            monthly_rent=Decimal("1300.00"),
            total_monthly_amount=Decimal("1300.00"),
            sort_order=1,
        )

        with (
            patch.object(
                project_service,
                "get_project_contract_relations",
                new=AsyncMock(return_value=relations),
            ),
            patch.object(
                project_service,
                "_load_project_active_assets",
                new=AsyncMock(return_value=([], None)),
            ),
            patch(
                "src.services.project.service.contract_crud.list_by_group",
                new=AsyncMock(return_value=[upstream_contract]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_ledger_entries_by_contract",
                new=AsyncMock(return_value=[stale_paid_entry]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_rent_terms_by_contract",
                new=AsyncMock(return_value=[current_rent_term]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_service_fee_entries_by_group",
                new=AsyncMock(return_value=[]),
            ),
        ):
            response = await project_service.get_project_risks(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        assert response.total == 1
        assert response.items[0].risk_type == "ledger_stale_after_correction"
        assert "CN-UPSTREAM-001" in response.items[0].message

    async def test_get_project_risks_ignores_primary_terminal_coverage(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        from src.schemas.project import (
            ProjectContractRelationItem,
            ProjectContractRelationsResponse,
        )

        relations = ProjectContractRelationsResponse(
            items=[
                ProjectContractRelationItem(
                    contract_relation_id="group-lease",
                    project_id="project-1",
                    display_name="GRP-LEASE",
                    revenue_mode="lease",
                    relation_kind="lease_sublease",
                    owner_party_id="owner-1",
                    operator_party_id="manager-1",
                    asset_ids=["asset-1"],
                    primary_contract_ids=["contract-upstream"],
                    terminal_contract_ids=["contract-downstream"],
                    derived_status="active",
                    risk_tags=[],
                )
            ],
            total=1,
        )
        upstream_contract = SimpleNamespace(
            contract_id="contract-upstream",
            contract_number="CN-UPSTREAM-001",
            group_relation_type=GroupRelationType.UPSTREAM,
            status=ContractLifecycleStatus.ACTIVE,
            effective_from=date(2026, 1, 1),
            effective_to=date(2026, 6, 30),
            assets=[SimpleNamespace(id="asset-1")],
        )
        downstream_contract = SimpleNamespace(
            contract_id="contract-downstream",
            group_relation_type=GroupRelationType.DOWNSTREAM,
            status=ContractLifecycleStatus.ACTIVE,
            effective_from=date(2026, 2, 1),
            effective_to=date(2026, 12, 31),
            assets=[SimpleNamespace(id="asset-1")],
        )

        with (
            patch.object(
                project_service,
                "get_project_contract_relations",
                new=AsyncMock(return_value=relations),
            ),
            patch.object(
                project_service,
                "_load_project_active_assets",
                new=AsyncMock(return_value=([], None)),
            ),
            patch(
                "src.services.project.service.contract_crud.list_by_group",
                new=AsyncMock(return_value=[upstream_contract, downstream_contract]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_ledger_entries_by_contract",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_service_fee_entries_by_group",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.services.project.service.ProjectService._today",
                return_value=date(2026, 5, 14),
            ),
        ):
            response = await project_service.get_project_risks(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        assert response.total == 0
        assert [item.risk_type for item in response.items] == []

    async def test_get_project_risks_returns_vacancy_risk_for_uncovered_rentable_area(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        from src.schemas.project import (
            ProjectAssetSummary,
            ProjectContractRelationItem,
            ProjectContractRelationsResponse,
        )

        relations = ProjectContractRelationsResponse(
            items=[
                ProjectContractRelationItem(
                    contract_relation_id="group-lease",
                    project_id="project-1",
                    display_name="GRP-LEASE",
                    revenue_mode="lease",
                    relation_kind="lease_sublease",
                    owner_party_id="owner-1",
                    operator_party_id="manager-1",
                    asset_ids=["asset-1"],
                    primary_contract_ids=["contract-upstream"],
                    terminal_contract_ids=[],
                    derived_status="active",
                    risk_tags=[],
                )
            ],
            total=1,
        )
        vacant_asset = SimpleNamespace(
            id="asset-1",
            asset_name="vacant-asset",
            rentable_area=Decimal("100.00"),
            rented_area=Decimal("40.00"),
        )

        with (
            patch.object(
                project_service,
                "get_project_contract_relations",
                new=AsyncMock(return_value=relations),
            ),
            patch.object(
                project_service,
                "_load_project_active_assets",
                new=AsyncMock(
                    return_value=(
                        [vacant_asset],
                        ProjectAssetSummary(
                            total_assets=1,
                            total_rentable_area=100.0,
                            total_rented_area=40.0,
                            occupancy_rate=40.0,
                        ),
                    )
                ),
            ),
            patch(
                "src.services.project.service.contract_crud.list_by_group",
                new=AsyncMock(return_value=[]),
            ),
        ):
            response = await project_service.get_project_risks(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        assert response.total == 1
        assert response.items[0].risk_type == "vacancy"
        assert response.items[0].severity == "warning"
        assert "60.00" in response.items[0].message


class TestGetProjectLedgerSummary:
    async def test_get_project_ledger_summary_aggregates_receivable_payable_and_service_fee(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        ledger_entries = [
            _ledger_entry(
                contract_id="contract-upstream",
                revenue_mode=RevenueMode.LEASE,
                relation_type=GroupRelationType.UPSTREAM,
                amount_due="1000.00",
                paid_amount="700.00",
                payment_status="partial",
            ),
            _ledger_entry(
                contract_id="contract-downstream",
                revenue_mode=RevenueMode.LEASE,
                relation_type=GroupRelationType.DOWNSTREAM,
                amount_due="1800.00",
                paid_amount="1200.00",
                payment_status="paid",
            ),
            _ledger_entry(
                contract_id="contract-downstream",
                revenue_mode=RevenueMode.LEASE,
                relation_type=GroupRelationType.DOWNSTREAM,
                amount_due="600.00",
                paid_amount="0.00",
                payment_status="unpaid",
                due_date=date(2026, 5, 1),
            ),
            _ledger_entry(
                contract_id="contract-direct",
                revenue_mode=RevenueMode.AGENCY,
                relation_type=GroupRelationType.DIRECT_LEASE,
                amount_due="5000.00",
                paid_amount="5000.00",
                payment_status="paid",
            ),
        ]
        service_fee_ledgers = [
            _service_fee_entry(
                amount_due="250.00",
                paid_amount="200.00",
                payment_status="partial",
            )
        ]

        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                project_service,
                "get_project_by_id",
                new=AsyncMock(return_value=SimpleNamespace(id="project-1")),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_ledger_entries_by_attributed_project",
                new=AsyncMock(return_value=ledger_entries),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_service_fee_entries_by_attributed_project",
                new=AsyncMock(return_value=service_fee_ledgers),
            ),
        ):
            response = await project_service.get_project_ledger_summary(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        assert response.receivable_amount == Decimal("2650.00")
        assert response.received_amount == Decimal("1400.00")
        assert response.payable_amount == Decimal("1000.00")
        assert response.paid_amount == Decimal("700.00")
        assert response.overdue_amount == Decimal("600.00")
        assert response.service_fee_receivable == Decimal("250.00")
        assert response.service_fee_received == Decimal("200.00")
        assert response.terminal_collection.amount_due == Decimal("7400.00")
        assert response.terminal_collection.paid_amount == Decimal("6200.00")
        assert response.terminal_collection.outstanding_amount == Decimal("1200.00")
        assert response.terminal_collection.overdue_amount == Decimal("600.00")
        assert response.operator_income.amount_due == Decimal("2650.00")
        assert response.operator_income.paid_amount == Decimal("1400.00")
        assert response.operator_cost.amount_due == Decimal("1000.00")
        assert response.operator_cost.paid_amount == Decimal("700.00")
        assert response.service_fee_settlement.amount_due == Decimal("250.00")
        assert response.service_fee_settlement.paid_amount == Decimal("200.00")
        assert response.operating_result.accrual_net_amount == Decimal("1650.00")
        assert response.operating_result.cash_net_amount == Decimal("700.00")

    async def test_get_project_ledger_summary_rejects_invisible_project(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=PartyFilter(party_ids=[])),
            ),
            patch.object(
                project_service,
                "get_project_by_id",
                new=AsyncMock(),
            ) as mock_get_project,
        ):
            with pytest.raises(ResourceNotFoundError):
                await project_service.get_project_ledger_summary(
                    mock_db,
                    project_id="project-1",
                    current_user_id="user-1",
                )

        mock_get_project.assert_not_awaited()

    async def test_get_project_ledger_summary_filters_frozen_party_attribution(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        visible_entry = _ledger_entry(
            contract_id="contract-visible",
            revenue_mode=RevenueMode.LEASE,
            relation_type=GroupRelationType.DOWNSTREAM,
            amount_due="100.00",
            paid_amount="50.00",
            payment_status="partial",
        )
        visible_entry.attributed_owner_party_id = "owner-1"
        visible_entry.attributed_operator_party_id = "operator-1"
        hidden_entry = _ledger_entry(
            contract_id="contract-hidden",
            revenue_mode=RevenueMode.LEASE,
            relation_type=GroupRelationType.DOWNSTREAM,
            amount_due="900.00",
            paid_amount="900.00",
            payment_status="paid",
        )
        hidden_entry.attributed_owner_party_id = "other-owner"
        hidden_entry.attributed_operator_party_id = "other-operator"
        visible_fee = _service_fee_entry(
            amount_due="10.00",
            paid_amount="5.00",
            payment_status="partial",
        )
        visible_fee.attributed_owner_party_id = "owner-1"
        visible_fee.attributed_operator_party_id = "operator-1"
        hidden_fee = _service_fee_entry(
            amount_due="90.00",
            paid_amount="90.00",
            payment_status="paid",
        )
        hidden_fee.attributed_owner_party_id = "other-owner"
        hidden_fee.attributed_operator_party_id = "other-operator"
        party_filter = PartyFilter(
            party_ids=["owner-1"],
            filter_mode="owner",
            owner_party_ids=["owner-1"],
        )

        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=party_filter),
            ),
            patch.object(
                project_service,
                "get_project_by_id",
                new=AsyncMock(return_value=SimpleNamespace(id="project-1")),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_ledger_entries_by_attributed_project",
                new=AsyncMock(return_value=[visible_entry, hidden_entry]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_service_fee_entries_by_attributed_project",
                new=AsyncMock(return_value=[visible_fee, hidden_fee]),
            ),
        ):
            response = await project_service.get_project_ledger_summary(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
                party_filter=party_filter,
            )

        assert response.terminal_collection.amount_due == Decimal("100.00")
        assert response.operator_income.amount_due == Decimal("110.00")
        assert response.service_fee_settlement.amount_due == Decimal("10.00")


class TestGetProjectTenants:
    async def test_get_project_tenants_aggregates_terminal_contract_customers(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        lease_group = SimpleNamespace(
            contract_group_id="group-lease",
            project_id="project-1",
            revenue_mode=RevenueMode.LEASE,
        )
        agency_group = SimpleNamespace(
            contract_group_id="group-agency",
            project_id="project-1",
            revenue_mode=RevenueMode.AGENCY,
        )
        upstream_contract = SimpleNamespace(
            contract_id="contract-upstream",
            group_relation_type=GroupRelationType.UPSTREAM,
            lessee_party_id="operator-1",
            lessee_party=SimpleNamespace(name="operator"),
        )
        downstream_contract_a = SimpleNamespace(
            contract_id="contract-downstream-a",
            group_relation_type=GroupRelationType.DOWNSTREAM,
            lessee_party_id="tenant-1",
            lessee_party=SimpleNamespace(name="tenant-a"),
        )
        downstream_contract_b = SimpleNamespace(
            contract_id="contract-downstream-b",
            group_relation_type=GroupRelationType.DOWNSTREAM,
            lessee_party_id="tenant-1",
            lessee_party=SimpleNamespace(name="tenant-b"),
        )
        direct_contract = SimpleNamespace(
            contract_id="contract-direct",
            group_relation_type=GroupRelationType.DIRECT_LEASE,
            lessee_party_id="tenant-2",
            lessee_party=SimpleNamespace(name="tenant-a"),
        )

        async def mock_list_by_group(
            _db: MagicMock, *, group_id: str
        ) -> list[SimpleNamespace]:
            if group_id == "group-lease":
                return [upstream_contract, downstream_contract_a, downstream_contract_b]
            return [direct_contract]

        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=PartyFilter(party_ids=["manager-1"])),
            ),
            patch.object(
                project_service,
                "get_project_by_id",
                new=AsyncMock(return_value=SimpleNamespace(id="project-1")),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_by_project",
                new=AsyncMock(return_value=[lease_group, agency_group]),
            ),
            patch(
                "src.services.project.service.contract_crud.list_by_group",
                new=AsyncMock(side_effect=mock_list_by_group),
            ),
        ):
            response = await project_service.get_project_tenants(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        assert response.total == 2
        assert [(item.party_id, item.contract_count) for item in response.items] == [
            ("tenant-1", 2),
            ("tenant-2", 1),
        ]

    async def test_get_project_tenants_deduplicates_same_party_across_terminal_types(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        lease_group = SimpleNamespace(
            contract_group_id="group-lease",
            project_id="project-1",
            revenue_mode=RevenueMode.LEASE,
        )
        agency_group = SimpleNamespace(
            contract_group_id="group-agency",
            project_id="project-1",
            revenue_mode=RevenueMode.AGENCY,
        )
        downstream_contract = SimpleNamespace(
            contract_id="contract-downstream",
            group_relation_type=GroupRelationType.DOWNSTREAM,
            lessee_party_id="tenant-shared",
            lessee_party=SimpleNamespace(name="shared-terminal-customer"),
        )
        direct_contract = SimpleNamespace(
            contract_id="contract-direct",
            group_relation_type=GroupRelationType.DIRECT_LEASE,
            lessee_party_id="tenant-shared",
            lessee_party=SimpleNamespace(name="shared-terminal-customer"),
        )

        async def mock_list_by_group(
            _db: MagicMock, *, group_id: str
        ) -> list[SimpleNamespace]:
            if group_id == "group-lease":
                return [downstream_contract]
            return [direct_contract]

        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=PartyFilter(party_ids=["manager-1"])),
            ),
            patch.object(
                project_service,
                "get_project_by_id",
                new=AsyncMock(return_value=SimpleNamespace(id="project-1")),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_by_project",
                new=AsyncMock(return_value=[lease_group, agency_group]),
            ),
            patch(
                "src.services.project.service.contract_crud.list_by_group",
                new=AsyncMock(side_effect=mock_list_by_group),
            ),
        ):
            response = await project_service.get_project_tenants(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        assert response.total == 1
        assert [
            (item.party_id, item.party_name, item.contract_count)
            for item in response.items
        ] == [("tenant-shared", "shared-terminal-customer", 2)]


class TestGetProjectAnalytics:
    async def test_get_project_analytics_filters_frozen_party_attribution(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        from src.schemas.project import (
            ProjectAssetSummary,
            ProjectContractRelationsResponse,
            ProjectRisksResponse,
            ProjectTenantSummaryResponse,
        )

        visible_entry = _ledger_entry(
            contract_id="contract-visible",
            revenue_mode=RevenueMode.LEASE,
            relation_type=GroupRelationType.DOWNSTREAM,
            amount_due="100.00",
            paid_amount="50.00",
            payment_status="partial",
        )
        visible_entry.attributed_owner_party_id = "owner-1"
        hidden_entry = _ledger_entry(
            contract_id="contract-hidden",
            revenue_mode=RevenueMode.LEASE,
            relation_type=GroupRelationType.DOWNSTREAM,
            amount_due="900.00",
            paid_amount="900.00",
            payment_status="paid",
        )
        hidden_entry.attributed_owner_party_id = "owner-hidden"
        party_filter = PartyFilter(
            party_ids=["owner-1"],
            filter_mode="owner",
            owner_party_ids=["owner-1"],
        )

        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=party_filter),
            ),
            patch.object(
                project_service,
                "get_project_active_assets",
                new=AsyncMock(
                    return_value=(
                        [],
                        ProjectAssetSummary(
                            total_assets=0,
                            total_rentable_area=0,
                            total_rented_area=0,
                            occupancy_rate=0,
                        ),
                    )
                ),
            ),
            patch.object(
                project_service,
                "get_project_contract_relations",
                new=AsyncMock(
                    return_value=ProjectContractRelationsResponse(items=[], total=0)
                ),
            ),
            patch.object(
                project_service,
                "get_project_ledger_summary",
                new=AsyncMock(
                    return_value=_project_ledger_summary(
                        receivable_amount=Decimal("100.00"),
                        payable_amount=Decimal("0"),
                        received_amount=Decimal("50.00"),
                        paid_amount=Decimal("0"),
                        overdue_amount=Decimal("0"),
                        service_fee_receivable=Decimal("0"),
                        service_fee_received=Decimal("0"),
                    )
                ),
            ),
            patch.object(
                project_service,
                "get_project_tenants",
                new=AsyncMock(
                    return_value=ProjectTenantSummaryResponse(items=[], total=0)
                ),
            ),
            patch.object(
                project_service,
                "get_project_risks",
                new=AsyncMock(return_value=ProjectRisksResponse(items=[], total=0)),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_ledger_entries_by_attributed_project",
                new=AsyncMock(return_value=[visible_entry, hidden_entry]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_service_fee_entries_by_attributed_project",
                new=AsyncMock(return_value=[]),
            ),
        ):
            response = await project_service.get_project_analytics(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
                party_filter=party_filter,
            )

        by_kind = {item.relation_kind: item for item in response.mode_summaries}
        assert by_kind["lease_sublease"].receivable_amount == Decimal("100.00")

    async def test_get_project_analytics_separates_lease_and_agency_metrics(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        from src.schemas.project import (
            ProjectAssetSummary,
            ProjectContractRelationItem,
            ProjectContractRelationsResponse,
            ProjectRiskItem,
            ProjectRisksResponse,
            ProjectTenantSummaryItem,
            ProjectTenantSummaryResponse,
        )

        asset_summary = ProjectAssetSummary(
            total_assets=3,
            total_rentable_area=300.0,
            total_rented_area=210.0,
            occupancy_rate=70.0,
        )
        relations = ProjectContractRelationsResponse(
            items=[
                ProjectContractRelationItem(
                    contract_relation_id="group-lease",
                    project_id="project-1",
                    display_name="GRP-LEASE",
                    revenue_mode="lease",
                    relation_kind="lease_sublease",
                    owner_party_id="owner-1",
                    operator_party_id="manager-1",
                    asset_ids=["asset-1", "asset-2"],
                    primary_contract_ids=["contract-upstream"],
                    terminal_contract_ids=["contract-downstream"],
                    derived_status="active",
                    risk_tags=[],
                ),
                ProjectContractRelationItem(
                    contract_relation_id="group-agency",
                    project_id="project-1",
                    display_name="GRP-AGENCY",
                    revenue_mode="agency",
                    relation_kind="agency_operation",
                    owner_party_id="owner-2",
                    operator_party_id="manager-1",
                    asset_ids=["asset-2", "asset-3"],
                    primary_contract_ids=["contract-entrusted"],
                    terminal_contract_ids=["contract-direct"],
                    derived_status="active",
                    risk_tags=[],
                ),
            ],
            total=2,
        )
        ledger_summary = _project_ledger_summary(
            receivable_amount=Decimal("2650.00"),
            payable_amount=Decimal("1000.00"),
            received_amount=Decimal("1400.00"),
            paid_amount=Decimal("700.00"),
            overdue_amount=Decimal("600.00"),
            service_fee_receivable=Decimal("250.00"),
            service_fee_received=Decimal("200.00"),
        )
        tenants = ProjectTenantSummaryResponse(
            items=[
                ProjectTenantSummaryItem(
                    party_id="tenant-1",
                    party_name="tenant-a",
                    group_relation_type="downstream",
                    contract_count=2,
                ),
                ProjectTenantSummaryItem(
                    party_id="tenant-2",
                    party_name="tenant-b",
                    group_relation_type="direct_lease",
                    contract_count=1,
                ),
            ],
            total=2,
        )
        risks = ProjectRisksResponse(
            items=[
                ProjectRiskItem(
                    risk_id="group-lease:payment_overdue",
                    risk_type="payment_overdue",
                    severity="high",
                    message="闁偓婀￠張顏呮暪",
                    contract_relation_id="group-lease",
                    display_name="GRP-LEASE",
                ),
                ProjectRiskItem(
                    risk_id="group-agency:manual_tag",
                    risk_type="manual_tag",
                    severity="warning",
                    message="閸掔増婀℃搴ㄦ珦",
                    contract_relation_id="group-agency",
                    display_name="GRP-AGENCY",
                ),
            ],
            total=2,
        )
        ledger_entries = [
            _ledger_entry(
                contract_id="contract-upstream",
                revenue_mode=RevenueMode.LEASE,
                relation_type=GroupRelationType.UPSTREAM,
                amount_due="1000.00",
                paid_amount="700.00",
                payment_status="partial",
            ),
            _ledger_entry(
                contract_id="contract-downstream",
                revenue_mode=RevenueMode.LEASE,
                relation_type=GroupRelationType.DOWNSTREAM,
                amount_due="1800.00",
                paid_amount="1200.00",
                payment_status="paid",
            ),
            _ledger_entry(
                contract_id="contract-downstream",
                revenue_mode=RevenueMode.LEASE,
                relation_type=GroupRelationType.DOWNSTREAM,
                amount_due="600.00",
                paid_amount="0.00",
                payment_status="unpaid",
                due_date=date(2026, 5, 1),
            ),
            _ledger_entry(
                contract_id="contract-direct",
                revenue_mode=RevenueMode.AGENCY,
                relation_type=GroupRelationType.DIRECT_LEASE,
                amount_due="5000.00",
                paid_amount="5000.00",
                payment_status="paid",
            ),
        ]

        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                project_service,
                "get_project_active_assets",
                new=AsyncMock(return_value=([], asset_summary)),
            ),
            patch.object(
                project_service,
                "get_project_contract_relations",
                new=AsyncMock(return_value=relations),
            ),
            patch.object(
                project_service,
                "get_project_ledger_summary",
                new=AsyncMock(return_value=ledger_summary),
            ),
            patch.object(
                project_service,
                "get_project_tenants",
                new=AsyncMock(return_value=tenants),
            ),
            patch.object(
                project_service,
                "get_project_risks",
                new=AsyncMock(return_value=risks),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_ledger_entries_by_attributed_project",
                new=AsyncMock(return_value=ledger_entries),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_service_fee_entries_by_attributed_project",
                new=AsyncMock(
                    return_value=[
                        _service_fee_entry(
                            amount_due="250.00",
                            paid_amount="200.00",
                            payment_status="partial",
                        )
                    ]
                ),
            ),
        ):
            response = await project_service.get_project_analytics(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        assert response.contract_relation_count == 2
        assert response.tenant_count == 2
        assert response.high_risk_count == 1
        by_kind = {item.relation_kind: item for item in response.mode_summaries}
        assert by_kind["lease_sublease"].receivable_amount == Decimal("2400.00")
        assert by_kind["lease_sublease"].payable_amount == Decimal("1000.00")
        assert by_kind["lease_sublease"].overdue_amount == Decimal("600.00")
        assert by_kind["lease_sublease"].customer_count == 1
        assert by_kind["lease_sublease"].risk_count == 1
        assert by_kind["agency_operation"].receivable_amount == Decimal("250.00")
        assert by_kind["agency_operation"].payable_amount == Decimal("0.00")
        assert by_kind["agency_operation"].customer_count == 1
        assert by_kind["agency_operation"].risk_count == 1

    async def test_get_project_analytics_should_suppress_customer_metrics_for_all_scope(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        from src.schemas.project import (
            ProjectAssetSummary,
            ProjectContractRelationsResponse,
            ProjectRisksResponse,
            ProjectTenantSummaryItem,
            ProjectTenantSummaryResponse,
        )

        asset_summary = ProjectAssetSummary(
            total_assets=1,
            total_rentable_area=100.0,
            total_rented_area=70.0,
            occupancy_rate=70.0,
        )
        ledger_summary = _project_ledger_summary(
            receivable_amount=Decimal("100.00"),
            payable_amount=Decimal("0.00"),
            received_amount=Decimal("20.00"),
            paid_amount=Decimal("0.00"),
            overdue_amount=Decimal("0.00"),
            service_fee_receivable=Decimal("0.00"),
            service_fee_received=Decimal("0.00"),
        )
        tenants = ProjectTenantSummaryResponse(
            items=[
                ProjectTenantSummaryItem(
                    party_id="tenant-1",
                    party_name="tenant-a",
                    group_relation_type="downstream",
                    contract_count=2,
                )
            ],
            total=1,
        )

        with (
            patch.object(
                project_service,
                "get_project_active_assets",
                new=AsyncMock(return_value=([], asset_summary)),
            ),
            patch.object(
                project_service,
                "get_project_contract_relations",
                new=AsyncMock(
                    return_value=ProjectContractRelationsResponse(items=[], total=0)
                ),
            ),
            patch.object(
                project_service,
                "get_project_ledger_summary",
                new=AsyncMock(return_value=ledger_summary),
            ),
            patch.object(
                project_service,
                "get_project_tenants",
                new=AsyncMock(return_value=tenants),
            ),
            patch.object(
                project_service,
                "get_project_risks",
                new=AsyncMock(return_value=ProjectRisksResponse(items=[], total=0)),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_ledger_entries_by_attributed_project",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_service_fee_entries_by_attributed_project",
                new=AsyncMock(return_value=[]),
            ),
        ):
            response = await project_service.get_project_analytics(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
                party_filter=PartyFilter(
                    party_ids=["owner-1", "manager-1"],
                    filter_mode="any",
                    owner_party_ids=["owner-1"],
                    manager_party_ids=["manager-1"],
                ),
            )

        assert response.tenant_count is None
        assert response.customer_contract_count is None
        assert (
            response.customer_metrics_suppression_reason
            == "customer_metrics_requires_single_perspective"
        )
        assert response.receivable_amount == Decimal("100.00")

    async def test_get_project_analytics_returns_monthly_amount_trends(
        self, project_service: ProjectService, mock_db: MagicMock
    ) -> None:
        from src.schemas.project import (
            ProjectAssetSummary,
            ProjectContractRelationItem,
            ProjectContractRelationsResponse,
            ProjectRisksResponse,
            ProjectTenantSummaryResponse,
        )

        asset_summary = ProjectAssetSummary(
            total_assets=1,
            total_rentable_area=100.0,
            total_rented_area=70.0,
            occupancy_rate=70.0,
        )
        relations = ProjectContractRelationsResponse(
            items=[
                ProjectContractRelationItem(
                    contract_relation_id="group-lease",
                    project_id="project-1",
                    display_name="GRP-LEASE",
                    revenue_mode="lease",
                    relation_kind="lease_sublease",
                    owner_party_id="owner-1",
                    operator_party_id="manager-1",
                    asset_ids=["asset-1"],
                    primary_contract_ids=["contract-upstream"],
                    terminal_contract_ids=["contract-downstream"],
                    derived_status="active",
                    risk_tags=[],
                ),
                ProjectContractRelationItem(
                    contract_relation_id="group-agency",
                    project_id="project-1",
                    display_name="GRP-AGENCY",
                    revenue_mode="agency",
                    relation_kind="agency_operation",
                    owner_party_id="owner-2",
                    operator_party_id="manager-1",
                    asset_ids=["asset-2"],
                    primary_contract_ids=["contract-entrusted"],
                    terminal_contract_ids=["contract-direct"],
                    derived_status="active",
                    risk_tags=[],
                ),
            ],
            total=2,
        )
        ledger_summary = _project_ledger_summary(
            receivable_amount=Decimal("4000.00"),
            payable_amount=Decimal("1000.00"),
            received_amount=Decimal("2100.00"),
            paid_amount=Decimal("1000.00"),
            overdue_amount=Decimal("500.00"),
            service_fee_receivable=Decimal("600.00"),
            service_fee_received=Decimal("600.00"),
        )
        ledger_entries = [
            _ledger_entry(
                contract_id="contract-upstream",
                revenue_mode=RevenueMode.LEASE,
                relation_type=GroupRelationType.UPSTREAM,
                year_month="2026-01",
                amount_due="1000.00",
                paid_amount="1000.00",
                payment_status="paid",
            ),
            _ledger_entry(
                contract_id="contract-downstream",
                revenue_mode=RevenueMode.LEASE,
                relation_type=GroupRelationType.DOWNSTREAM,
                year_month="2026-01",
                amount_due="2000.00",
                paid_amount="1600.00",
                payment_status="partial",
            ),
            _ledger_entry(
                contract_id="contract-downstream",
                revenue_mode=RevenueMode.LEASE,
                relation_type=GroupRelationType.DOWNSTREAM,
                year_month="2026-02",
                amount_due="1400.00",
                paid_amount="500.00",
                payment_status="partial",
                due_date=date(2026, 5, 1),
            ),
        ]

        with (
            patch.object(
                project_service,
                "_resolve_party_filter",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                project_service,
                "get_project_active_assets",
                new=AsyncMock(return_value=([], asset_summary)),
            ),
            patch.object(
                project_service,
                "get_project_contract_relations",
                new=AsyncMock(return_value=relations),
            ),
            patch.object(
                project_service,
                "get_project_ledger_summary",
                new=AsyncMock(return_value=ledger_summary),
            ),
            patch.object(
                project_service,
                "get_project_tenants",
                new=AsyncMock(
                    return_value=ProjectTenantSummaryResponse(items=[], total=0)
                ),
            ),
            patch.object(
                project_service,
                "get_project_risks",
                new=AsyncMock(return_value=ProjectRisksResponse(items=[], total=0)),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_ledger_entries_by_attributed_project",
                new=AsyncMock(return_value=ledger_entries),
            ),
            patch(
                "src.services.project.service.contract_group_crud.list_service_fee_entries_by_attributed_project",
                new=AsyncMock(
                    return_value=[
                        _service_fee_entry(
                            year_month="2026-02",
                            amount_due="600.00",
                            paid_amount="600.00",
                            payment_status="paid",
                        )
                    ]
                ),
            ),
        ):
            response = await project_service.get_project_analytics(
                mock_db,
                project_id="project-1",
                current_user_id="user-1",
            )

        assert [
            (
                item.period,
                item.receivable_amount,
                item.payable_amount,
                item.received_amount,
                item.paid_amount,
                item.overdue_amount,
            )
            for item in response.monthly_trends
        ] == [
            (
                "2026-01",
                Decimal("2000.00"),
                Decimal("1000.00"),
                Decimal("1600.00"),
                Decimal("1000.00"),
                Decimal("0.00"),
            ),
            (
                "2026-02",
                Decimal("2000.00"),
                Decimal("0.00"),
                Decimal("1100.00"),
                Decimal("0.00"),
                Decimal("900.00"),
            ),
        ]


async def _get_agency_project_risks(
    project_service: ProjectService,
    mock_db: MagicMock,
    *,
    source_mismatches: list[SimpleNamespace],
    service_fee_entries: list[SimpleNamespace] | None = None,
):
    from src.schemas.project import (
        ProjectContractRelationItem,
        ProjectContractRelationsResponse,
    )

    relations = ProjectContractRelationsResponse(
        items=[
            ProjectContractRelationItem(
                contract_relation_id="group-agency",
                project_id="project-1",
                display_name="GRP-AGENCY",
                revenue_mode="agency",
                relation_kind="agency_operation",
                owner_party_id="owner-1",
                operator_party_id="manager-1",
                asset_ids=["asset-1"],
                primary_contract_ids=["contract-entrusted"],
                terminal_contract_ids=["contract-direct"],
                derived_status="active",
                risk_tags=[],
            )
        ],
        total=1,
    )

    with (
        patch.object(
            project_service,
            "_resolve_party_filter",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            project_service,
            "get_project_contract_relations",
            new=AsyncMock(return_value=relations),
        ),
        patch.object(
            project_service,
            "_load_project_active_assets",
            new=AsyncMock(return_value=([], None)),
        ),
        patch(
            "src.services.project.service.contract_crud.list_by_group",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "src.services.project.service.contract_group_crud.list_service_fee_entries_by_group",
            new=AsyncMock(return_value=service_fee_entries or []),
        ),
        patch(
            "src.services.project.service.service_fee_ledger_service.find_source_mismatches",
            new=AsyncMock(return_value=source_mismatches),
        ),
        patch(
            "src.services.project.service.ProjectService._today",
            return_value=date(2026, 5, 14),
        ),
    ):
        return await project_service.get_project_risks(
            mock_db,
            project_id="project-1",
            current_user_id="user-1",
        )


async def test_get_project_risks_returns_service_fee_source_mismatch_risk(
    project_service: ProjectService, mock_db: MagicMock
) -> None:
    mismatch = SimpleNamespace(
        service_fee_entry_id="fee-001",
        year_month="2026-05",
        reason="service_fee_source_changed",
    )

    response = await _get_agency_project_risks(
        project_service,
        mock_db,
        source_mismatches=[mismatch],
    )

    assert response.total == 1
    assert response.items[0].risk_type == "service_fee_source_mismatch"
    assert response.items[0].contract_relation_id == "group-agency"
    assert "GRP-AGENCY" in response.items[0].message


async def test_get_project_risks_does_not_treat_service_fee_unpaid_as_overdue(
    project_service: ProjectService, mock_db: MagicMock
) -> None:
    unpaid_service_fee = SimpleNamespace(
        service_fee_entry_id="fee-unpaid",
        amount_due=Decimal("1000.00"),
        paid_amount=Decimal("0.00"),
        payment_status="unpaid",
        due_date=date(2026, 1, 1),
    )

    response = await _get_agency_project_risks(
        project_service,
        mock_db,
        source_mismatches=[],
        service_fee_entries=[unpaid_service_fee],
    )

    assert response.items == []
