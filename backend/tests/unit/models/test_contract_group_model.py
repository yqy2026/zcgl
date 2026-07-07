"""Static metadata tests for contract-group models.

Service-layer tests mock CRUD heavily, so these tests guard SQLAlchemy enum
column metadata directly.
"""

import pytest

from src.models.associations import contract_scan_document_links
from src.models.contract_group import (
    Contract,
    ContractAuditLog,
    ContractDirection,
    ContractGroup,
    ContractLedgerEntry,
    ContractLifecycleStatus,
    ContractScanDocument,
    GroupRelationType,
    OperationalPaymentFlow,
    PaymentAllocation,
    RevenueMode,
    ServiceFeeLedger,
    derive_ledger_payment_status,
)

pytestmark = pytest.mark.unit


class TestEnumColumnStorageStrategy:
    """ORM enum labels must match migration DDL labels."""

    def _get_enum_labels(self, model_cls: type, col_name: str) -> list[str]:
        table = model_cls.__table__
        col = table.c[col_name]
        return list(col.type.enums)

    def _assert_enum_uses_names(
        self, model_cls: type, col_name: str, enum_cls: type
    ) -> None:
        labels = self._get_enum_labels(model_cls, col_name)
        expected = [m.name for m in enum_cls]
        assert labels == expected, (
            f"{model_cls.__name__}.{col_name} labels {labels} != {expected}"
        )

    def test_contract_group_revenue_mode_uses_names(self) -> None:
        self._assert_enum_uses_names(ContractGroup, "revenue_mode", RevenueMode)

    def test_contract_direction_uses_names(self) -> None:
        self._assert_enum_uses_names(Contract, "contract_direction", ContractDirection)

    def test_contract_group_relation_type_uses_names(self) -> None:
        self._assert_enum_uses_names(Contract, "group_relation_type", GroupRelationType)

    def test_contract_lifecycle_status_uses_names(self) -> None:
        self._assert_enum_uses_names(Contract, "status", ContractLifecycleStatus)
        assert [status.name for status in ContractLifecycleStatus] == [
            "DRAFT",
            "ACTIVE",
            "TERMINATED",
        ]

    def test_contract_review_workflow_columns_are_removed(self) -> None:
        retired_columns = {
            "review_status",
            "review_by",
            "reviewed_at",
            "review_reason",
        }
        assert retired_columns.isdisjoint(set(Contract.__table__.c.keys()))

    def test_contract_relation_model_is_removed(self) -> None:
        import src.models.contract_group as contract_group_models

        assert not hasattr(contract_group_models, "ContractRelation")
        assert not hasattr(contract_group_models, "ContractRelationType")

    def test_contract_keeps_explicit_correction_source_column(self) -> None:
        assert "correction_source_contract_id" in Contract.__table__.c

    def test_contract_audit_log_action_comment_excludes_expire(self) -> None:
        comment = ContractAuditLog.__table__.c["action"].comment or ""
        assert "expire" not in comment
        assert "finalize_correction" in comment

    def test_contract_number_is_unique_per_project_not_global(self) -> None:
        contract_number = Contract.__table__.c["contract_number"]
        assert contract_number.unique is not True

        constraints = {
            constraint.name: {column.name for column in constraint.columns}
            for constraint in Contract.__table__.constraints
            if constraint.name is not None
        }
        assert constraints["uq_contract_number_project"] == {
            "contract_number",
            "project_id",
        }

    def test_contract_has_frozen_project_id(self) -> None:
        assert "project_id" in Contract.__table__.c

    def test_contract_has_party_name_snapshot_columns(self) -> None:
        assert Contract.__table__.c["lessor_name_snapshot"].nullable is True
        assert Contract.__table__.c["lessee_name_snapshot"].nullable is True

    def test_contract_ledger_has_operations_view_and_follow_up_columns(self) -> None:
        columns = ContractLedgerEntry.__table__.c

        assert "ledger_views" in columns
        assert columns["ledger_views"].nullable is False
        assert "follow_up_status" in columns
        assert "next_follow_up_date" in columns
        assert "follow_up_note" in columns

    def test_payment_flow_and_allocation_models_exist(self) -> None:
        assert OperationalPaymentFlow.__tablename__ == "operational_payment_flows"
        assert PaymentAllocation.__tablename__ == "payment_allocations"
        assert OperationalPaymentFlow.__table__.c["amount"].nullable is False
        assert PaymentAllocation.__table__.c["flow_id"].nullable is False

    def test_payment_flow_amount_has_positive_constraint(self) -> None:
        constraint_sql = " ".join(
            str(constraint.sqltext)
            for constraint in OperationalPaymentFlow.__table__.constraints
            if hasattr(constraint, "sqltext")
        )

        assert "amount > 0" in constraint_sql

    def test_service_fee_ledger_uses_monthly_aggregate_source_columns(self) -> None:
        columns = ServiceFeeLedger.__table__.c

        assert "agency_agreement_contract_id" in columns
        assert "source_ledger_ids" in columns
        assert "calculation_base_amount" in columns
        assert "source_ledger_id" not in columns

    def test_contract_scan_document_model_and_link_table_exist(self) -> None:
        assert ContractScanDocument.__tablename__ == "contract_scan_documents"
        assert ContractScanDocument.__table__.c["storage_key"].unique is True
        assert contract_scan_document_links.name == "contract_scan_document_links"
        assert {column.name for column in contract_scan_document_links.c} == {
            "contract_id",
            "document_id",
            "created_at",
        }

    def test_all_enum_columns_in_one_pass(self) -> None:
        cases: list[tuple[type, str, type]] = [
            (ContractGroup, "revenue_mode", RevenueMode),
            (Contract, "contract_direction", ContractDirection),
            (Contract, "group_relation_type", GroupRelationType),
            (Contract, "status", ContractLifecycleStatus),
        ]

        failures: list[str] = []
        for model_cls, col_name, enum_cls in cases:
            actual = self._get_enum_labels(model_cls, col_name)
            expected = [m.name for m in enum_cls]
            if actual != expected:
                failures.append(
                    f"  {model_cls.__name__}.{col_name}: "
                    f"actual={actual}, expected={expected}"
                )

        assert not failures, "\n".join(failures)


class TestLedgerPaymentStatusDerivation:
    def test_derive_ledger_payment_status_preserves_voided(self) -> None:
        assert (
            derive_ledger_payment_status(
                amount_due="1000.00",
                paid_amount="1000.00",
                stored_status="voided",
            )
            == "voided"
        )

    @pytest.mark.parametrize(
        ("paid_amount", "expected_status"),
        [
            ("0.00", "unpaid"),
            ("100.00", "partial"),
            ("1000.00", "paid"),
            ("1200.00", "paid"),
        ],
    )
    def test_contract_ledger_payment_status_is_derived_from_amounts(
        self,
        paid_amount: str,
        expected_status: str,
    ) -> None:
        entry = ContractLedgerEntry(amount_due="1000.00", paid_amount=paid_amount)

        assert entry.payment_status == expected_status

    def test_service_fee_payment_status_is_derived_from_amounts(self) -> None:
        entry = ServiceFeeLedger(
            amount_due="100.00",
            paid_amount="50.00",
            payment_status="paid",
        )

        assert entry.payment_status == "partial"


class TestEnumLabelsMatchMigrationDDL:
    """Cross-check ORM labels against the current contract-group DDL."""

    def test_revenue_mode_ddl_labels(self) -> None:
        ddl_labels = ["LEASE", "AGENCY"]
        orm_labels = list(ContractGroup.__table__.c["revenue_mode"].type.enums)
        assert orm_labels == ddl_labels

    def test_lifecycle_status_ddl_labels(self) -> None:
        ddl_labels = ["DRAFT", "ACTIVE", "TERMINATED"]
        orm_labels = list(Contract.__table__.c["status"].type.enums)
        assert orm_labels == ddl_labels

    def test_group_relation_type_ddl_labels(self) -> None:
        ddl_labels = ["UPSTREAM", "DOWNSTREAM", "ENTRUSTED", "DIRECT_LEASE"]
        orm_labels = list(Contract.__table__.c["group_relation_type"].type.enums)
        assert orm_labels == ddl_labels

    def test_contract_direction_ddl_labels(self) -> None:
        ddl_labels = ["LESSOR", "LESSEE"]
        orm_labels = list(Contract.__table__.c["contract_direction"].type.enums)
        assert orm_labels == ddl_labels
