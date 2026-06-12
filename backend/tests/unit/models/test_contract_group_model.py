"""Static metadata tests for contract-group models.

Service-layer tests mock CRUD heavily, so these tests guard SQLAlchemy enum
column metadata directly.
"""

import pytest

from src.models.contract_group import (
    Contract,
    ContractDirection,
    ContractGroup,
    ContractLifecycleStatus,
    ContractReviewStatus,
    GroupRelationType,
    RevenueMode,
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

    def test_contract_review_status_uses_names(self) -> None:
        self._assert_enum_uses_names(Contract, "review_status", ContractReviewStatus)

    def test_contract_relation_model_is_removed(self) -> None:
        import src.models.contract_group as contract_group_models

        assert not hasattr(contract_group_models, "ContractRelation")
        assert not hasattr(contract_group_models, "ContractRelationType")

    def test_contract_keeps_explicit_correction_source_column(self) -> None:
        assert "correction_source_contract_id" in Contract.__table__.c

    def test_all_five_enum_columns_in_one_pass(self) -> None:
        cases: list[tuple[type, str, type]] = [
            (ContractGroup, "revenue_mode", RevenueMode),
            (Contract, "contract_direction", ContractDirection),
            (Contract, "group_relation_type", GroupRelationType),
            (Contract, "status", ContractLifecycleStatus),
            (Contract, "review_status", ContractReviewStatus),
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


class TestEnumLabelsMatchMigrationDDL:
    """Cross-check ORM labels against the original contract-group DDL."""

    def test_revenue_mode_ddl_labels(self) -> None:
        ddl_labels = ["LEASE", "AGENCY"]
        orm_labels = list(ContractGroup.__table__.c["revenue_mode"].type.enums)
        assert orm_labels == ddl_labels

    def test_lifecycle_status_ddl_labels(self) -> None:
        ddl_labels = ["DRAFT", "PENDING_REVIEW", "ACTIVE", "EXPIRED", "TERMINATED"]
        orm_labels = list(Contract.__table__.c["status"].type.enums)
        assert orm_labels == ddl_labels

    def test_review_status_ddl_labels(self) -> None:
        ddl_labels = ["DRAFT", "PENDING", "APPROVED", "REVERSED"]
        orm_labels = list(Contract.__table__.c["review_status"].type.enums)
        assert orm_labels == ddl_labels

    def test_group_relation_type_ddl_labels(self) -> None:
        ddl_labels = ["UPSTREAM", "DOWNSTREAM", "ENTRUSTED", "DIRECT_LEASE"]
        orm_labels = list(Contract.__table__.c["group_relation_type"].type.enums)
        assert orm_labels == ddl_labels

    def test_contract_direction_ddl_labels(self) -> None:
        ddl_labels = ["LESSOR", "LESSEE"]
        orm_labels = list(Contract.__table__.c["contract_direction"].type.enums)
        assert orm_labels == ddl_labels
