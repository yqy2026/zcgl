"""add llm prompt management tables

Revision ID: 20250118_add_llm_prompt
Revises: previous_revision_id
Create Date: 2025-01-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250118_add_llm_prompt'
down_revision = None  # 你需要填入实际的上一版本ID
branch_labels = None
depends_on = None


def upgrade():
    # ============================================================
    # 创建Prompt模板表
    # ============================================================
    op.create_table(
        'prompt_templates',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('doc_type', sa.String(50), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('description', sa.String(500)),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('user_prompt_template', sa.Text(), nullable=False),
        sa.Column('few_shot_examples', sa.JSON()),
        sa.Column('version', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('tags', sa.JSON()),
        sa.Column('avg_accuracy', sa.Float(), default=0.0),
        sa.Column('avg_confidence', sa.Float(), default=0.0),
        sa.Column('total_usage', sa.Integer(), default=0),
        sa.Column('current_version_id', sa.String()),
        sa.Column('parent_id', sa.String()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.String(100)),
        sa.ForeignKeyConstraint(['current_version_id'], ['prompt_versions.id'], name='prompt_templates_current_version_id_fkey'),
        sa.ForeignKeyConstraint(['parent_id'], ['prompt_templates.id'], name='prompt_templates_parent_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_prompt_templates_name')
    )
    op.create_index('ix_prompt_templates_doc_type', 'prompt_templates', ['doc_type'])
    op.create_index('ix_prompt_templates_provider', 'prompt_templates', ['provider'])
    op.create_index('ix_prompt_templates_status', 'prompt_templates', ['status'])

    # ============================================================
    # 创建Prompt版本表
    # ============================================================
    op.create_table(
        'prompt_versions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('template_id', sa.String(), nullable=False),
        sa.Column('version', sa.String(20), nullable=False),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('user_prompt_template', sa.Text(), nullable=False),
        sa.Column('few_shot_examples', sa.JSON()),
        sa.Column('change_description', sa.String(500)),
        sa.Column('change_type', sa.String(50)),
        sa.Column('auto_generated', sa.Boolean(), default=False),
        sa.Column('accuracy', sa.Float()),
        sa.Column('confidence', sa.Float()),
        sa.Column('usage_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', sa.String(100)),
        sa.ForeignKeyConstraint(['template_id'], ['prompt_templates.id'], name='prompt_versions_template_id_fkey'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_prompt_versions_template_id', 'prompt_versions', ['template_id'])

    # ============================================================
    # 创建反馈收集表
    # ============================================================
    op.create_table(
        'extraction_feedback',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('template_id', sa.String(), nullable=False),
        sa.Column('version_id', sa.String()),
        sa.Column('doc_type', sa.String(50)),
        sa.Column('file_path', sa.String(500)),
        sa.Column('session_id', sa.String(100)),
        sa.Column('field_name', sa.String(100)),
        sa.Column('original_value', sa.Text()),
        sa.Column('corrected_value', sa.Text()),
        sa.Column('confidence_before', sa.Float()),
        sa.Column('user_action', sa.String(50)),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['prompt_templates.id'], name='extraction_feedback_template_id_fkey'),
        sa.ForeignKeyConstraint(['version_id'], ['prompt_versions.id'], name='extraction_feedback_version_id_fkey'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_extraction_feedback_template_id', 'extraction_feedback', ['template_id'])
    op.create_index('ix_extraction_feedback_created_at', 'extraction_feedback', ['created_at'])

    # ============================================================
    # 创建性能指标表
    # ============================================================
    op.create_table(
        'prompt_metrics',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('template_id', sa.String(), nullable=False),
        sa.Column('version_id', sa.String()),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total_extractions', sa.Integer(), default=0),
        sa.Column('successful_extractions', sa.Integer(), default=0),
        sa.Column('corrected_fields', sa.Integer(), default=0),
        sa.Column('avg_accuracy', sa.Float(), default=0.0),
        sa.Column('avg_confidence', sa.Float(), default=0.0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['prompt_templates.id'], name='prompt_metrics_template_id_fkey'),
        sa.ForeignKeyConstraint(['version_id'], ['prompt_versions.id'], name='prompt_metrics_version_id_fkey'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_prompt_metrics_template_id', 'prompt_metrics', ['template_id'])
    op.create_index('ix_prompt_metrics_date', 'prompt_metrics', ['date'])
    op.create_index('ix_prompt_metrics_template_date', 'prompt_metrics', ['template_id', 'date'])


def downgrade():
    # 删除表（按依赖关系逆序）
    op.drop_index('ix_prompt_metrics_template_date', table_name='prompt_metrics')
    op.drop_index('ix_prompt_metrics_date', table_name='prompt_metrics')
    op.drop_index('ix_prompt_metrics_template_id', table_name='prompt_metrics')
    op.drop_table('prompt_metrics')

    op.drop_index('ix_extraction_feedback_created_at', table_name='extraction_feedback')
    op.drop_index('ix_extraction_feedback_template_id', table_name='extraction_feedback')
    op.drop_table('extraction_feedback')

    op.drop_index('ix_prompt_versions_template_id', table_name='prompt_versions')
    op.drop_table('prompt_versions')

    op.drop_index('ix_prompt_templates_status', table_name='prompt_templates')
    op.drop_index('ix_prompt_templates_provider', table_name='prompt_templates')
    op.drop_index('ix_prompt_templates_doc_type', table_name='prompt_templates')
    op.drop_table('prompt_templates')
