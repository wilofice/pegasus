"""Add language column to audio_files

Revision ID: 003_add_language_column
Revises: 002
Create Date: 2025-06-29 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_language_column'
down_revision = '002_add_audio_tags'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add language column to audio_files table."""
    # Add language column with default value 'en'
    op.add_column('audio_files', sa.Column('language', sa.String(length=10), server_default='en', nullable=True))
    
    # Create index on language column
    op.create_index(op.f('ix_audio_files_language'), 'audio_files', ['language'], unique=False)


def downgrade() -> None:
    """Remove language column from audio_files table."""
    # Drop index first
    op.drop_index(op.f('ix_audio_files_language'), table_name='audio_files')
    
    # Drop the column
    op.drop_column('audio_files', 'language')