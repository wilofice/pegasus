"""Add tag and category columns to audio_files table

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add tag and category columns
    op.add_column('audio_files', sa.Column('tag', sa.String(length=100), nullable=True))
    op.add_column('audio_files', sa.Column('category', sa.String(length=100), nullable=True))
    
    # Create indexes
    op.create_index(op.f('ix_audio_files_tag'), 'audio_files', ['tag'], unique=False)
    op.create_index(op.f('ix_audio_files_category'), 'audio_files', ['category'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_audio_files_category'), table_name='audio_files')
    op.drop_index(op.f('ix_audio_files_tag'), table_name='audio_files')
    
    # Drop columns
    op.drop_column('audio_files', 'category')
    op.drop_column('audio_files', 'tag')