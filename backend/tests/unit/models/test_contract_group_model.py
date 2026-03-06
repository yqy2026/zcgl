"""
合同组模型元数据测试（REQ-RNT-001）

# 为什么需要这类测试？—— Mock 测试的盲区
# ============================================================
# 这个项目的单元测试对 CRUD 层做了全量 Mock。这带来一个系统性盲区：
#
#   SQLAlchemy 的 Enum 列有一个关键配置：values_callable。
#   它决定"Python enum 成员 → DB 存储字符串"的映射策略。
#
#   - 若不配置：SQLAlchemy 2.0 对 StrEnum 默认使用 str(member) = .value
#               例如 RevenueMode.LEASE → 存入 "lease"（小写）
#   - 若配置 values_callable=lambda e: [m.name for m in e]：
#               例如 RevenueMode.LEASE → 存入 "LEASE"（大写，与 DDL 一致）
#
#   迁移文件（20260305_contract_group_m1.py）手写了大写成员名作为 DDL 枚举值，
#   例如 sa.Enum("LEASE", "AGENCY", name="revenuemode")。
#   如果 ORM 未配置正确，会产生以下两个"被 mock 完全掩盖"的运行时错误：
#
#   1. INSERT/UPDATE 时：ORM 发送 "lease"，PostgreSQL 校验失败（invalid enum value）
#      ← mock 掉 CRUD 后，SQLAlchemy 的 bind_processor 从不被调用，永远测不到
#
#   2. SELECT 时：PostgreSQL 返回 "LEASE"，ORM 尝试 RevenueMode("LEASE") →
#      ValueError（因 value 是 "lease"），需依赖 SQLAlchemy 版本相关的 fallback
#      ← mock 掉 DB 后永远测不到
#
# 本测试通过静态检查 ORM Column 元数据来填补这一空白，无需真实数据库即可运行。
# 原则：凡是 Service 层的 mock 测试"穿不透"的 ORM 配置，都应有对应的模型级静态测试。
"""

import pytest

from src.models.contract_group import (
    Contract,
    ContractDirection,
    ContractGroup,
    ContractLifecycleStatus,
    ContractRelation,
    ContractRelationType,
    ContractReviewStatus,
    GroupRelationType,
    RevenueMode,
)

pytestmark = pytest.mark.unit


# ─── Enum 列存储策略：ORM 标签必须与迁移 DDL 对齐 ────────────────────────────


class TestEnumColumnStorageStrategy:
    """
    验证 ORM Enum 列配置了 values_callable=name，与迁移 DDL 对齐。

    为什么能静态验证？
    SQLAlchemy 的 Enum 类型把允许的标签存在 column.type.enums 上。
    配置了 values_callable=name 后，enums = [m.name for m in enum_class]。
    没有配置时（默认），enums = [str(m) for m in enum_class]，对 StrEnum 是 .value。
    """

    def _get_enum_labels(self, model_cls, col_name: str) -> list[str]:
        table = model_cls.__table__
        col = table.c[col_name]
        return list(col.type.enums)

    def test_contract_group_revenue_mode_uses_names(self) -> None:
        """ContractGroup.revenue_mode：DDL 有 LEASE/AGENCY（成员 name），ORM 必须一致。"""
        labels = self._get_enum_labels(ContractGroup, "revenue_mode")
        expected = [m.name for m in RevenueMode]
        assert labels == expected, (
            f"ORM Enum 标签 {labels} ≠ DDL 期望 {expected}（成员 name）。\n"
            "请在 Enum(...) 中添加 values_callable=lambda e: [m.name for m in e]"
        )

    def test_contract_direction_uses_names(self) -> None:
        """Contract.contract_direction：DDL 有 LESSOR/LESSEE（成员 name）。"""
        labels = self._get_enum_labels(Contract, "contract_direction")
        expected = [m.name for m in ContractDirection]
        assert labels == expected, (
            f"ORM labels {labels} ≠ expected {expected}"
        )

    def test_contract_group_relation_type_uses_names(self) -> None:
        """Contract.group_relation_type：DDL 有 UPSTREAM/DOWNSTREAM/ENTRUSTED/DIRECT_LEASE。"""
        labels = self._get_enum_labels(Contract, "group_relation_type")
        expected = [m.name for m in GroupRelationType]
        assert labels == expected, (
            f"ORM labels {labels} ≠ expected {expected}"
        )

    def test_contract_lifecycle_status_uses_names(self) -> None:
        """Contract.status：DDL 有 DRAFT/PENDING_REVIEW/ACTIVE/EXPIRED/TERMINATED。"""
        labels = self._get_enum_labels(Contract, "status")
        expected = [m.name for m in ContractLifecycleStatus]
        assert labels == expected, (
            f"ORM labels {labels} ≠ expected {expected}"
        )

    def test_contract_review_status_uses_names(self) -> None:
        """Contract.review_status：DDL 有 DRAFT/PENDING/APPROVED/REVERSED。"""
        labels = self._get_enum_labels(Contract, "review_status")
        expected = [m.name for m in ContractReviewStatus]
        assert labels == expected, (
            f"ORM labels {labels} ≠ expected {expected}"
        )

    def test_contract_relation_type_uses_names(self) -> None:
        """ContractRelation.relation_type：DDL 有 UPSTREAM_DOWNSTREAM/AGENCY_DIRECT/RENEWAL。"""
        labels = self._get_enum_labels(ContractRelation, "relation_type")
        expected = [m.name for m in ContractRelationType]
        assert labels == expected, (
            f"ORM labels {labels} ≠ expected {expected}"
        )

    def test_all_six_enum_columns_in_one_pass(self) -> None:
        """
        一次性断言全部 6 个枚举列，防止遗漏。

        新增枚举列时需同步在此注册，否则测试报错提醒。
        """
        cases: list[tuple[type, str, type]] = [
            (ContractGroup, "revenue_mode", RevenueMode),
            (Contract, "contract_direction", ContractDirection),
            (Contract, "group_relation_type", GroupRelationType),
            (Contract, "status", ContractLifecycleStatus),
            (Contract, "review_status", ContractReviewStatus),
            (ContractRelation, "relation_type", ContractRelationType),
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
        assert not failures, (
            "以下枚举列 ORM 标签与 DDL 不一致（未使用 values_callable=name）：\n"
            + "\n".join(failures)
        )


# ─── DDL 与 ORM 标签的完整性验证 ────────────────────────────────────────────────


class TestEnumLabelsMatchMigrationDDL:
    """
    将 ORM Enum 标签与迁移文件 DDL 中的字面量进行交叉核对。

    迁移文件（20260305_contract_group_m1.py）是真相来源（DDL SSOT）。
    本测试确保 ORM 与迁移文件保持一致，避免手写迁移时因笔误导致偏差。
    """

    def test_revenue_mode_ddl_labels(self) -> None:
        """RevenueMode：迁移 DDL 字面量为 LEASE / AGENCY。"""
        # 以下是从 20260305_contract_group_m1.py 中 hand-copied 的 DDL 字面量
        ddl_labels = ["LEASE", "AGENCY"]
        orm_labels = list(ContractGroup.__table__.c["revenue_mode"].type.enums)
        assert orm_labels == ddl_labels

    def test_lifecycle_status_ddl_labels(self) -> None:
        """ContractLifecycleStatus：迁移 DDL 字面量为 5 个成员 name。"""
        ddl_labels = ["DRAFT", "PENDING_REVIEW", "ACTIVE", "EXPIRED", "TERMINATED"]
        orm_labels = list(Contract.__table__.c["status"].type.enums)
        assert orm_labels == ddl_labels

    def test_review_status_ddl_labels(self) -> None:
        """ContractReviewStatus：迁移 DDL 字面量为 4 个成员 name。"""
        ddl_labels = ["DRAFT", "PENDING", "APPROVED", "REVERSED"]
        orm_labels = list(Contract.__table__.c["review_status"].type.enums)
        assert orm_labels == ddl_labels

    def test_group_relation_type_ddl_labels(self) -> None:
        """GroupRelationType：迁移 DDL 字面量为 4 个成员 name。"""
        ddl_labels = ["UPSTREAM", "DOWNSTREAM", "ENTRUSTED", "DIRECT_LEASE"]
        orm_labels = list(Contract.__table__.c["group_relation_type"].type.enums)
        assert orm_labels == ddl_labels

    def test_contract_direction_ddl_labels(self) -> None:
        """ContractDirection：迁移 DDL 字面量为 LESSOR / LESSEE。"""
        ddl_labels = ["LESSOR", "LESSEE"]
        orm_labels = list(Contract.__table__.c["contract_direction"].type.enums)
        assert orm_labels == ddl_labels

    def test_contract_relation_type_ddl_labels(self) -> None:
        """ContractRelationType：迁移 DDL 字面量为 3 个成员 name。"""
        ddl_labels = ["UPSTREAM_DOWNSTREAM", "AGENCY_DIRECT", "RENEWAL"]
        orm_labels = list(ContractRelation.__table__.c["relation_type"].type.enums)
        assert orm_labels == ddl_labels
