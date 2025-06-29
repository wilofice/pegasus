"""Create audio_files table

Revision ID: 001
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import MetaData, inspect
    
    # Check if table already exists
    inspector = inspect(op.get_bind())
    tables = inspector.get_table_names()
    
    if 'audio_files' in tables:
        print("Table 'audio_files' already exists, skipping creation...")
        return
    
    # Create enum type for processing status (only if it doesn't exist)
    processing_status_enum = sa.Enum(
        'uploaded', 'transcribing', 'improving', 'completed', 'failed',
        name='processingstatus'
    )
    processing_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create audio_files table
    op.create_table('audio_files',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('original_transcript', sa.Text(), nullable=True),
        sa.Column('improved_transcript', sa.Text(), nullable=True),
        sa.Column('transcription_engine', sa.String(length=50), nullable=True),
        sa.Column('transcription_started_at', sa.DateTime(), nullable=True),
        sa.Column('transcription_completed_at', sa.DateTime(), nullable=True),
        sa.Column('improvement_completed_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('upload_timestamp', sa.DateTime(), nullable=True),
        sa.Column('processing_status', processing_status_enum, nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_path')
    )
    
    # Create indexes
    op.create_index(op.f('ix_audio_files_processing_status'), 'audio_files', ['processing_status'], unique=False)
    op.create_index(op.f('ix_audio_files_upload_timestamp'), 'audio_files', ['upload_timestamp'], unique=False)
    op.create_index(op.f('ix_audio_files_user_id'), 'audio_files', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_audio_files_user_id'), table_name='audio_files')
    op.drop_index(op.f('ix_audio_files_upload_timestamp'), table_name='audio_files')
    op.drop_index(op.f('ix_audio_files_processing_status'), table_name='audio_files')
    
    # Drop table
    op.drop_table('audio_files')
    
    # Drop enum type
    sa.Enum(name='processingstatus').drop(op.get_bind())