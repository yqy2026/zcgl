"""Add security_events table

Revision ID: 20250120_add_security_events
Revises: 20250118_add_property_cert_tables
Create Date: 2026-01-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250120_add_security_events'
down_revision = '20250118_add_property_cert_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create security_events table
    op.create_table(
        'security_events',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False, comment='Event type'),
        sa.Column('severity', sa.String(length=20), nullable=False, comment='Severity level'),
        sa.Column('user_id', sa.String(), nullable=True, comment='User ID if applicable'),
        sa.Column('ip_address', sa.String(length=45), nullable=True, comment='IP address (IPv4 or IPv6)'),
        sa.Column('metadata', sa.JSON(), nullable=True, comment='Event metadata (JSON)'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='Event timestamp'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for querying
    op.create_index('ix_security_events_event_type', 'security_events', ['event_type'])
    op.create_index('ix_security_events_user_id', 'security_events', ['user_id'])
    op.create_index('ix_security_events_ip_address', 'security_events', ['ip_address'])
    op.create_index('ix_security_events_created_at', 'security_events', ['created_at'])
    op.create_index('ix_security_events_event_type_created_at', 'security_events', ['event_type', 'created_at'])
    op.create_index('ix_security_events_user_id_created_at', 'security_events', ['user_id', 'created_at'])
    op.create_index('ix_security_events_ip_created_at', 'security_events', ['ip_address', 'created_at'])
    op.create_index('ix_security_events_severity_created_at', 'security_events', ['severity', 'created_at'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_security_events_severity_created_at', table_name='security_events')
    op.drop_index('ix_security_events_ip_created_at', table_name='security_events')
    op.drop_index('ix_security_events_user_id_created_at', table_name='security_events')
    op.drop_index('ix_security_events_event_type_created_at', table_name='security_events')
    op.drop_index('ix_security_events_created_at', table_name='security_events')
    op.drop_index('ix_security_events_ip_address', table_name='security_events')
    op.drop_index('ix_security_events_user_id', table_name='security_events')
    op.drop_index('ix_security_events_event_type', table_name='security_events')

    # Drop table
    op.drop_table('security_events')
