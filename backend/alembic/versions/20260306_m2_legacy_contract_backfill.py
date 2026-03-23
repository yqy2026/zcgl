"""m2 legacy contract backfill into contract-group runtime

Revision ID: 20260306_m2_legacy_contract_backfill
Revises: 20260306_m2_contract_ledger_entries
Create Date: 2026-03-06 19:05:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260306_m2_legacy_contract_backfill"
down_revision: str | None = "20260306_m2_contract_ledger_entries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_REQUIRED_TABLES: tuple[str, ...] = (
    "rent_contracts",
    "rent_contract_assets",
    "rent_terms",
    "rent_ledger",
    "contract_groups",
    "contracts",
    "contract_assets",
    "contract_group_assets",
    "lease_contract_details",
    "agency_agreement_details",
    "contract_relations",
    "contract_rent_terms",
    "contract_ledger_entries",
)


def _has_required_tables(inspector: sa.engine.reflection.Inspector) -> bool:
    return all(inspector.has_table(table_name) for table_name in _REQUIRED_TABLES)


def _execute_sql(bind: sa.engine.Connection, sql_text: str) -> None:
    bind.execute(sa.text(sql_text))


def _count_rows(bind: sa.engine.Connection, sql_text: str) -> int:
    return int(bind.execute(sa.text(sql_text)).scalar() or 0)


def _assert_backfilled_relation_semantics(bind: sa.engine.Connection) -> None:
    invalid_contract_relation_types = _count_rows(
        bind,
        """
        SELECT COUNT(*)
        FROM contracts AS c
        JOIN contract_groups AS cg
            ON cg.contract_group_id = c.contract_group_id
        WHERE c.contract_group_id LIKE 'legacy-group-%'
          AND (
                (
                    cg.revenue_mode = 'AGENCY'
                    AND c.group_relation_type NOT IN ('ENTRUSTED', 'DIRECT_LEASE')
                )
                OR (
                    cg.revenue_mode = 'LEASE'
                    AND c.group_relation_type NOT IN ('UPSTREAM', 'DOWNSTREAM')
                )
          )
        """,
    )
    if invalid_contract_relation_types > 0:
        raise RuntimeError(
            "legacy agency groups or lease groups still contain invalid contract relation types after backfill"
        )

    invalid_relation_types = _count_rows(
        bind,
        """
        SELECT COUNT(*)
        FROM contract_relations AS relation
        JOIN contracts AS child_contract
            ON child_contract.contract_id = relation.child_contract_id
        JOIN contract_groups AS cg
            ON cg.contract_group_id = child_contract.contract_group_id
        WHERE child_contract.contract_group_id LIKE 'legacy-group-%'
          AND (
                (
                    cg.revenue_mode = 'AGENCY'
                    AND relation.relation_type <> 'AGENCY_DIRECT'
                )
                OR (
                    cg.revenue_mode = 'LEASE'
                    AND relation.relation_type <> 'UPSTREAM_DOWNSTREAM'
                )
          )
        """,
    )
    if invalid_relation_types > 0:
        raise RuntimeError(
            "legacy contract relations still violate migrated group semantics after backfill"
        )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not _has_required_tables(inspector):
        return

    _execute_sql(
        bind,
        """
        WITH contract_roots AS (
            SELECT
                rc.id AS contract_id,
                COALESCE(parent.id, rc.id) AS root_contract_id
            FROM rent_contracts AS rc
            LEFT JOIN rent_contracts AS parent
                ON parent.id = rc.upstream_contract_id
        )
        INSERT INTO contract_groups (
            contract_group_id,
            group_code,
            revenue_mode,
            operator_party_id,
            owner_party_id,
            effective_from,
            effective_to,
            settlement_rule,
            revenue_attribution_rule,
            revenue_share_rule,
            risk_tags,
            predecessor_group_id,
            data_status,
            version,
            created_at,
            updated_at,
            created_by,
            updated_by
        )
        SELECT
            'legacy-group-' || cr.root_contract_id AS contract_group_id,
            'MIG-' || cr.root_contract_id AS group_code,
            CASE
                WHEN BOOL_OR(UPPER(COALESCE(rc.contract_type, '')) = 'ENTRUSTED') THEN 'AGENCY'
                ELSE 'LEASE'
            END::revenuemode AS revenue_mode,
            MIN(rc.manager_party_id) AS operator_party_id,
            MIN(rc.owner_party_id) AS owner_party_id,
            MIN(rc.start_date) AS effective_from,
            MAX(rc.end_date) AS effective_to,
            jsonb_build_object(
                'version', 'legacy-v1',
                'cycle',
                CASE MAX(COALESCE(rc.payment_cycle, 'monthly'))
                    WHEN 'monthly' THEN '月付'
                    WHEN 'quarterly' THEN '季付'
                    WHEN 'semi_annual' THEN '半年付'
                    WHEN 'annual' THEN '年付'
                    ELSE '月付'
                END,
                'settlement_mode', 'manual',
                'amount_rule', jsonb_build_object('basis', 'legacy_contract'),
                'payment_rule', jsonb_build_object('source', 'legacy_contract_backfill')
            ) AS settlement_rule,
            NULL AS revenue_attribution_rule,
            NULL AS revenue_share_rule,
            jsonb_build_array('legacy-backfill') AS risk_tags,
            NULL AS predecessor_group_id,
            COALESCE(MIN(NULLIF(rc.data_status, '')), '正常') AS data_status,
            1 AS version,
            COALESCE(MIN(rc.created_at), CURRENT_TIMESTAMP) AS created_at,
            COALESCE(
                MAX(rc.updated_at),
                COALESCE(MIN(rc.created_at), CURRENT_TIMESTAMP)
            ) AS updated_at,
            'legacy-backfill' AS created_by,
            'legacy-backfill' AS updated_by
        FROM rent_contracts AS rc
        JOIN contract_roots AS cr
            ON cr.contract_id = rc.id
        WHERE rc.owner_party_id IS NOT NULL
          AND rc.manager_party_id IS NOT NULL
        GROUP BY cr.root_contract_id
        ON CONFLICT (contract_group_id) DO NOTHING
        """,
    )

    _execute_sql(
        bind,
        """
        WITH contract_roots AS (
            SELECT
                rc.id AS contract_id,
                COALESCE(parent.id, rc.id) AS root_contract_id
            FROM rent_contracts AS rc
            LEFT JOIN rent_contracts AS parent
                ON parent.id = rc.upstream_contract_id
        ),
        group_modes AS (
            SELECT
                cr.root_contract_id,
                CASE
                    WHEN BOOL_OR(UPPER(COALESCE(rc.contract_type, '')) = 'ENTRUSTED') THEN 'AGENCY'
                    ELSE 'LEASE'
                END::revenuemode AS revenue_mode
            FROM rent_contracts AS rc
            JOIN contract_roots AS cr
                ON cr.contract_id = rc.id
            GROUP BY cr.root_contract_id
        )
        INSERT INTO contracts (
            contract_id,
            contract_group_id,
            contract_direction,
            group_relation_type,
            lessor_party_id,
            lessee_party_id,
            sign_date,
            effective_from,
            effective_to,
            currency_code,
            tax_rate,
            is_tax_included,
            status,
            review_status,
            review_by,
            reviewed_at,
            review_reason,
            data_status,
            contract_notes,
            version,
            created_at,
            updated_at,
            created_by,
            updated_by,
            source_session_id
        )
        SELECT
            rc.id AS contract_id,
            'legacy-group-' || cr.root_contract_id AS contract_group_id,
            CASE
                WHEN UPPER(COALESCE(rc.contract_type, '')) = 'LEASE_DOWNSTREAM' THEN 'LESSOR'
                ELSE 'LESSEE'
            END::contractdirection AS contract_direction,
            CASE
                WHEN group_modes.revenue_mode = 'AGENCY'
                    AND UPPER(COALESCE(rc.contract_type, '')) = 'ENTRUSTED'
                    THEN 'ENTRUSTED'
                WHEN group_modes.revenue_mode = 'AGENCY'
                    AND UPPER(COALESCE(rc.contract_type, '')) = 'LEASE_DOWNSTREAM'
                    THEN 'DIRECT_LEASE'
                WHEN UPPER(COALESCE(rc.contract_type, '')) = 'LEASE_UPSTREAM'
                    THEN 'UPSTREAM'
                WHEN UPPER(COALESCE(rc.contract_type, '')) = 'LEASE_DOWNSTREAM'
                    THEN 'DOWNSTREAM'
                ELSE 'DOWNSTREAM'
            END::grouprelationtype AS group_relation_type,
            CASE
                WHEN UPPER(COALESCE(rc.contract_type, '')) = 'LEASE_DOWNSTREAM'
                    THEN rc.manager_party_id
                ELSE rc.owner_party_id
            END AS lessor_party_id,
            CASE
                WHEN UPPER(COALESCE(rc.contract_type, '')) = 'LEASE_DOWNSTREAM'
                    THEN COALESCE(NULLIF(rc.tenant_party_id, ''), rc.manager_party_id)
                ELSE rc.manager_party_id
            END AS lessee_party_id,
            rc.sign_date,
            rc.start_date AS effective_from,
            rc.end_date AS effective_to,
            'CNY' AS currency_code,
            NULL AS tax_rate,
            TRUE AS is_tax_included,
            CASE UPPER(COALESCE(rc.contract_status, 'ACTIVE'))
                WHEN 'DRAFT' THEN 'DRAFT'
                WHEN 'PENDING_REVIEW' THEN 'PENDING_REVIEW'
                WHEN 'PENDING' THEN 'PENDING_REVIEW'
                WHEN 'ACTIVE' THEN 'ACTIVE'
                WHEN 'EXPIRED' THEN 'EXPIRED'
                WHEN 'TERMINATED' THEN 'TERMINATED'
                ELSE 'ACTIVE'
            END::contractlifecyclestatus AS status,
            CASE UPPER(COALESCE(rc.contract_status, 'ACTIVE'))
                WHEN 'DRAFT' THEN 'DRAFT'
                WHEN 'PENDING_REVIEW' THEN 'PENDING'
                WHEN 'PENDING' THEN 'PENDING'
                ELSE 'APPROVED'
            END::contractreviewstatus AS review_status,
            NULL AS review_by,
            NULL AS reviewed_at,
            NULL AS review_reason,
            COALESCE(NULLIF(rc.data_status, ''), '正常') AS data_status,
            rc.contract_notes,
            COALESCE(rc.version, 1) AS version,
            COALESCE(rc.created_at, CURRENT_TIMESTAMP) AS created_at,
            COALESCE(rc.updated_at, COALESCE(rc.created_at, CURRENT_TIMESTAMP)) AS updated_at,
            'legacy-backfill' AS created_by,
            'legacy-backfill' AS updated_by,
            rc.source_session_id
        FROM rent_contracts AS rc
        JOIN contract_roots AS cr
            ON cr.contract_id = rc.id
        JOIN group_modes
            ON group_modes.root_contract_id = cr.root_contract_id
        WHERE rc.owner_party_id IS NOT NULL
          AND rc.manager_party_id IS NOT NULL
        ON CONFLICT (contract_id) DO NOTHING
        """,
    )

    _execute_sql(
        bind,
        """
        INSERT INTO lease_contract_details (
            lease_detail_id,
            contract_id,
            total_deposit,
            rent_amount,
            monthly_rent_base,
            payment_cycle,
            payment_terms,
            tenant_name,
            tenant_contact,
            tenant_phone,
            tenant_address,
            tenant_usage,
            owner_name,
            owner_contact,
            owner_phone
        )
        SELECT
            'legacy-lease-' || rc.id AS lease_detail_id,
            rc.id AS contract_id,
            COALESCE(rc.total_deposit, 0) AS total_deposit,
            COALESCE(rc.monthly_rent_base, 0) AS rent_amount,
            rc.monthly_rent_base,
            CASE COALESCE(rc.payment_cycle, 'monthly')
                WHEN 'monthly' THEN '月付'
                WHEN 'quarterly' THEN '季付'
                WHEN 'semi_annual' THEN '半年付'
                WHEN 'annual' THEN '年付'
                ELSE '月付'
            END AS payment_cycle,
            rc.payment_terms,
            rc.tenant_name,
            rc.tenant_contact,
            rc.tenant_phone,
            rc.tenant_address,
            rc.tenant_usage,
            rc.owner_name,
            rc.owner_contact,
            rc.owner_phone
        FROM rent_contracts AS rc
        JOIN contracts AS c
            ON c.contract_id = rc.id
        WHERE UPPER(COALESCE(rc.contract_type, '')) <> 'ENTRUSTED'
        ON CONFLICT (contract_id) DO NOTHING
        """,
    )

    _execute_sql(
        bind,
        """
        INSERT INTO agency_agreement_details (
            agency_detail_id,
            contract_id,
            service_fee_ratio,
            fee_calculation_base,
            agency_scope
        )
        SELECT
            'legacy-agency-' || rc.id AS agency_detail_id,
            rc.id AS contract_id,
            COALESCE(rc.service_fee_rate, 0) AS service_fee_ratio,
            'actual_received' AS fee_calculation_base,
            NULLIF(COALESCE(rc.contract_notes, rc.owner_name), '') AS agency_scope
        FROM rent_contracts AS rc
        JOIN contracts AS c
            ON c.contract_id = rc.id
        WHERE UPPER(COALESCE(rc.contract_type, '')) = 'ENTRUSTED'
        ON CONFLICT (contract_id) DO NOTHING
        """,
    )

    _execute_sql(
        bind,
        """
        INSERT INTO contract_assets (
            contract_id,
            asset_id,
            created_at
        )
        SELECT
            rca.contract_id,
            rca.asset_id,
            COALESCE(rca.created_at, CURRENT_TIMESTAMP) AS created_at
        FROM rent_contract_assets AS rca
        JOIN contracts AS c
            ON c.contract_id = rca.contract_id
        ON CONFLICT (contract_id, asset_id) DO NOTHING
        """,
    )

    _execute_sql(
        bind,
        """
        WITH contract_roots AS (
            SELECT
                rc.id AS contract_id,
                COALESCE(parent.id, rc.id) AS root_contract_id
            FROM rent_contracts AS rc
            LEFT JOIN rent_contracts AS parent
                ON parent.id = rc.upstream_contract_id
        )
        INSERT INTO contract_group_assets (
            contract_group_id,
            asset_id,
            created_at
        )
        SELECT DISTINCT
            'legacy-group-' || cr.root_contract_id AS contract_group_id,
            rca.asset_id,
            COALESCE(rca.created_at, CURRENT_TIMESTAMP) AS created_at
        FROM rent_contract_assets AS rca
        JOIN contract_roots AS cr
            ON cr.contract_id = rca.contract_id
        ON CONFLICT (contract_group_id, asset_id) DO NOTHING
        """,
    )

    _execute_sql(
        bind,
        """
        WITH ranked_terms AS (
            SELECT
                rt.id,
                rt.contract_id,
                rt.start_date,
                rt.end_date,
                rt.monthly_rent,
                COALESCE(rt.management_fee, 0) AS management_fee,
                COALESCE(rt.other_fees, 0) AS other_fees,
                COALESCE(
                    rt.total_monthly_amount,
                    rt.monthly_rent + COALESCE(rt.management_fee, 0) + COALESCE(rt.other_fees, 0)
                ) AS total_monthly_amount,
                rt.rent_description,
                COALESCE(rt.created_at, CURRENT_TIMESTAMP) AS created_at,
                COALESCE(rt.updated_at, COALESCE(rt.created_at, CURRENT_TIMESTAMP)) AS updated_at,
                ROW_NUMBER() OVER (
                    PARTITION BY rt.contract_id
                    ORDER BY
                        rt.start_date,
                        rt.end_date,
                        COALESCE(rt.created_at, CURRENT_TIMESTAMP),
                        rt.id
                ) AS sort_order
            FROM rent_terms AS rt
        )
        INSERT INTO contract_rent_terms (
            rent_term_id,
            contract_id,
            sort_order,
            start_date,
            end_date,
            monthly_rent,
            management_fee,
            other_fees,
            total_monthly_amount,
            notes,
            created_at,
            updated_at
        )
        SELECT
            rt.id AS rent_term_id,
            rt.contract_id,
            rt.sort_order,
            rt.start_date,
            rt.end_date,
            rt.monthly_rent,
            rt.management_fee,
            rt.other_fees,
            rt.total_monthly_amount,
            rt.rent_description AS notes,
            rt.created_at,
            rt.updated_at
        FROM ranked_terms AS rt
        JOIN contracts AS c
            ON c.contract_id = rt.contract_id
        ON CONFLICT (rent_term_id) DO NOTHING
        """,
    )

    _execute_sql(
        bind,
        """
        WITH ranked_ledger AS (
            SELECT
                rl.id,
                rl.contract_id,
                rl.year_month,
                rl.due_date,
                rl.due_amount,
                rl.paid_amount,
                rl.payment_status,
                rl.notes,
                COALESCE(rl.created_at, CURRENT_TIMESTAMP) AS created_at,
                COALESCE(rl.updated_at, COALESCE(rl.created_at, CURRENT_TIMESTAMP)) AS updated_at,
                ROW_NUMBER() OVER (
                    PARTITION BY rl.contract_id, rl.year_month
                    ORDER BY
                        COALESCE(rl.created_at, CURRENT_TIMESTAMP),
                        rl.id
                ) AS canonical_rank
            FROM rent_ledger AS rl
        )
        INSERT INTO contract_ledger_entries (
            entry_id,
            contract_id,
            year_month,
            due_date,
            amount_due,
            currency_code,
            is_tax_included,
            tax_rate,
            payment_status,
            paid_amount,
            notes,
            created_at,
            updated_at
        )
        SELECT
            rl.id AS entry_id,
            rl.contract_id,
            rl.year_month,
            rl.due_date,
            rl.due_amount AS amount_due,
            'CNY' AS currency_code,
            TRUE AS is_tax_included,
            NULL AS tax_rate,
            CASE
                WHEN rl.payment_status IN ('已支付', 'paid', 'PAID') THEN 'paid'
                WHEN rl.payment_status IN ('部分支付', 'partial', 'PARTIAL') THEN 'partial'
                WHEN rl.payment_status IN ('逾期', 'overdue', 'OVERDUE') THEN 'overdue'
                ELSE 'unpaid'
            END AS payment_status,
            COALESCE(rl.paid_amount, 0) AS paid_amount,
            rl.notes,
            rl.created_at,
            rl.updated_at
        FROM ranked_ledger AS rl
        JOIN contracts AS c
            ON c.contract_id = rl.contract_id
        WHERE rl.canonical_rank = 1
        ON CONFLICT (contract_id, year_month) DO NOTHING
        """,
    )

    _execute_sql(
        bind,
        """
        WITH contract_roots AS (
            SELECT
                rc.id AS contract_id,
                COALESCE(parent.id, rc.id) AS root_contract_id
            FROM rent_contracts AS rc
            LEFT JOIN rent_contracts AS parent
                ON parent.id = rc.upstream_contract_id
        ),
        group_modes AS (
            SELECT
                cr.root_contract_id,
                CASE
                    WHEN BOOL_OR(UPPER(COALESCE(rc.contract_type, '')) = 'ENTRUSTED') THEN 'AGENCY'
                    ELSE 'LEASE'
                END::revenuemode AS revenue_mode
            FROM rent_contracts AS rc
            JOIN contract_roots AS cr
                ON cr.contract_id = rc.id
            GROUP BY cr.root_contract_id
        )
        INSERT INTO contract_relations (
            relation_id,
            parent_contract_id,
            child_contract_id,
            relation_type,
            created_at
        )
        SELECT
            'legacy-rel-' || rc.id AS relation_id,
            rc.upstream_contract_id AS parent_contract_id,
            rc.id AS child_contract_id,
            CASE
                WHEN group_modes.revenue_mode = 'AGENCY' THEN 'AGENCY_DIRECT'
                ELSE 'UPSTREAM_DOWNSTREAM'
            END::contractrelationtype AS relation_type,
            COALESCE(rc.created_at, CURRENT_TIMESTAMP) AS created_at
        FROM rent_contracts AS rc
        JOIN contract_roots AS cr
            ON cr.contract_id = rc.id
        JOIN group_modes
            ON group_modes.root_contract_id = cr.root_contract_id
        JOIN contracts AS child_contract
            ON child_contract.contract_id = rc.id
        JOIN contracts AS parent_contract
            ON parent_contract.contract_id = rc.upstream_contract_id
        WHERE UPPER(COALESCE(rc.contract_type, '')) = 'LEASE_DOWNSTREAM'
          AND rc.upstream_contract_id IS NOT NULL
        ON CONFLICT (parent_contract_id, child_contract_id) DO NOTHING
        """,
    )

    _assert_backfilled_relation_semantics(bind)


def downgrade() -> None:
    # Legacy backfill is intentionally best-effort only; keep migrated rows in place.
    return None
