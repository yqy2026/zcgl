"""remove_deprecated_ocr_fields

Revision ID: c6fd8148eb25
Revises: 345d5f07ee41
Create Date: 2026-01-31 21:45:43.548066

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6fd8148eb25'
down_revision: Union[str, None] = '345d5f07ee41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove deprecated OCR fields from PDF import tables.

    OCR functionality (PaddleOCR, Tesseract) was removed in v2.0,
    replaced by LLM Vision API (GLM-4V, Qwen-VL, DeepSeek-VL).

    Drops:
    - pdf_import_sessions.ocr_used
    - pdf_import_configurations.prefer_ocr
    - pdf_import_configurations.ocr_languages
    - pdf_import_configurations.dpi
    """
    # Drop from pdf_import_sessions
    op.drop_column('pdf_import_sessions', 'ocr_used')

    # Drop from pdf_import_configurations
    op.drop_column('pdf_import_configurations', 'prefer_ocr')
    op.drop_column('pdf_import_configurations', 'ocr_languages')
    op.drop_column('pdf_import_configurations', 'dpi')


def downgrade() -> None:
    """
    Restore deprecated OCR fields for rollback compatibility.
    """
    # Restore to pdf_import_sessions
    op.add_column(
        'pdf_import_sessions',
        sa.Column('ocr_used', sa.Boolean(), nullable=False, server_default='false')
    )

    # Restore to pdf_import_configurations
    op.add_column(
        'pdf_import_configurations',
        sa.Column('prefer_ocr', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column(
        'pdf_import_configurations',
        sa.Column('ocr_languages', sa.JSON(), nullable=True)
    )
    op.add_column(
        'pdf_import_configurations',
        sa.Column('dpi', sa.Integer(), nullable=False, server_default='300')
    )
