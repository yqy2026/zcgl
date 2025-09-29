"""add rent contract tables

Revision ID: rent_contract_001
Revises: base
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'rent_contract_001'
down_revision = 'base'
branch_labels = None
depends_on = None


def upgrade():
    # 创建租金合同表
    op.create_table('rent_contracts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('contract_number', sa.String(length=100), nullable=False),
        sa.Column('asset_id', sa.String(length=36), nullable=False),
        sa.Column('ownership_id', sa.String(length=36), nullable=False),
        sa.Column('tenant_name', sa.String(length=200), nullable=False),
        sa.Column('tenant_contact', sa.String(length=100), nullable=True),
        sa.Column('tenant_phone', sa.String(length=20), nullable=True),
        sa.Column('tenant_address', sa.String(length=500), nullable=True),
        sa.Column('sign_date', sa.Date(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('total_deposit', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('monthly_rent_base', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('contract_status', sa.String(length=20), nullable=True),
        sa.Column('payment_terms', sa.Text(), nullable=True),
        sa.Column('contract_notes', sa.Text(), nullable=True),
        sa.Column('data_status', sa.String(length=20), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('tenant_id', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
        sa.ForeignKeyConstraint(['ownership_id'], ['ownerships.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('contract_number')
    )

    # 创建租金条款表
    op.create_table('rent_terms',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('contract_id', sa.String(length=36), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('monthly_rent', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('rent_description', sa.String(length=500), nullable=True),
        sa.Column('management_fee', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('other_fees', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('total_monthly_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['contract_id'], ['rent_contracts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建租金台账表
    op.create_table('rent_ledger',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('contract_id', sa.String(length=36), nullable=False),
        sa.Column('asset_id', sa.String(length=36), nullable=False),
        sa.Column('ownership_id', sa.String(length=36), nullable=False),
        sa.Column('year_month', sa.String(length=7), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('due_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('paid_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('overdue_amount', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('payment_status', sa.String(length=20), nullable=True),
        sa.Column('payment_date', sa.Date(), nullable=True),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('payment_reference', sa.String(length=100), nullable=True),
        sa.Column('late_fee', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('late_fee_days', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('data_status', sa.String(length=20), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
        sa.ForeignKeyConstraint(['contract_id'], ['rent_contracts.id'], ),
        sa.ForeignKeyConstraint(['ownership_id'], ['ownerships.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建租金合同历史表
    op.create_table('rent_contract_history',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('contract_id', sa.String(length=36), nullable=False),
        sa.Column('change_type', sa.String(length=50), nullable=False),
        sa.Column('change_description', sa.Text(), nullable=True),
        sa.Column('old_data', sa.JSON(), nullable=True),
        sa.Column('new_data', sa.JSON(), nullable=True),
        sa.Column('operator', sa.String(length=100), nullable=True),
        sa.Column('operator_id', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['contract_id'], ['rent_contracts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建索引
    op.create_index('idx_rent_contracts_asset_id', 'rent_contracts', ['asset_id'])
    op.create_index('idx_rent_contracts_ownership_id', 'rent_contracts', ['ownership_id'])
    op.create_index('idx_rent_contracts_contract_number', 'rent_contracts', ['contract_number'])
    op.create_index('idx_rent_terms_contract_id', 'rent_terms', ['contract_id'])
    op.create_index('idx_rent_ledger_contract_id', 'rent_ledger', ['contract_id'])
    op.create_index('idx_rent_ledger_asset_id', 'rent_ledger', ['asset_id'])
    op.create_index('idx_rent_ledger_ownership_id', 'rent_ledger', ['ownership_id'])
    op.create_index('idx_rent_ledger_year_month', 'rent_ledger', ['year_month'])
    op.create_index('idx_rent_ledger_payment_status', 'rent_ledger', ['payment_status'])
    op.create_index('idx_rent_contract_history_contract_id', 'rent_contract_history', ['contract_id'])


def downgrade():
    # 删除索引
    op.drop_index('idx_rent_contract_history_contract_id', table_name='rent_contract_history')
    op.drop_index('idx_rent_ledger_payment_status', table_name='rent_ledger')
    op.drop_index('idx_rent_ledger_year_month', table_name='rent_ledger')
    op.drop_index('idx_rent_ledger_ownership_id', table_name='rent_ledger')
    op.drop_index('idx_rent_ledger_asset_id', table_name='rent_ledger')
    op.drop_index('idx_rent_ledger_contract_id', table_name='rent_ledger')
    op.drop_index('idx_rent_terms_contract_id', table_name='rent_terms')
    op.drop_index('idx_rent_contracts_contract_number', table_name='rent_contracts')
    op.drop_index('idx_rent_contracts_ownership_id', table_name='rent_contracts')
    op.drop_index('idx_rent_contracts_asset_id', table_name='rent_contracts')

    # 删除表
    op.drop_table('rent_contract_history')
    op.drop_table('rent_ledger')
    op.drop_table('rent_terms')
    op.drop_table('rent_contracts')