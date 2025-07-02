"""Add job queue tracking tables

Revision ID: 004_add_job_queue_tables
Revises: 003_add_language_column
Create Date: 2025-01-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_add_job_queue_tables'
down_revision: Union[str, None] = '003_add_language_column'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create job queue tracking tables."""
    
    # Create job status enum
    job_status_enum = sa.Enum(
        'pending', 'processing', 'completed', 'failed', 'retrying',
        name='jobstatus'
    )
    job_status_enum.create(op.get_bind(), checkfirst=True)
    
    # Create job type enum
    job_type_enum = sa.Enum(
        'transcript_processing', 'vector_indexing', 'graph_building', 
        'document_chunking', 'entity_extraction', 'plugin_execution',
        name='jobtype'
    )
    job_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Create processing_jobs table
    op.create_table(
        'processing_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('job_type', job_type_enum, nullable=False),
        sa.Column('status', job_status_enum, nullable=False, default='pending'),
        sa.Column('priority', sa.Integer, nullable=False, default=0),
        sa.Column('input_data', postgresql.JSONB, nullable=True),
        sa.Column('result_data', postgresql.JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('error_traceback', sa.Text, nullable=True),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('audio_file_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('celery_task_id', sa.String(255), nullable=True),
        sa.Column('retry_count', sa.Integer, nullable=False, default=0),
        sa.Column('max_retries', sa.Integer, nullable=False, default=3),
        sa.Column('timeout_seconds', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=False, default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create job_status_history table for tracking status changes
    op.create_table(
        'job_status_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('uuid_generate_v4()')),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('old_status', job_status_enum, nullable=True),
        sa.Column('new_status', job_status_enum, nullable=False),
        sa.Column('message', sa.Text, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, default=sa.func.now()),
    )
    
    # Create indexes for performance
    op.create_index('ix_processing_jobs_status', 'processing_jobs', ['status'])
    op.create_index('ix_processing_jobs_job_type', 'processing_jobs', ['job_type'])
    op.create_index('ix_processing_jobs_user_id', 'processing_jobs', ['user_id'])
    op.create_index('ix_processing_jobs_audio_file_id', 'processing_jobs', ['audio_file_id'])
    op.create_index('ix_processing_jobs_celery_task_id', 'processing_jobs', ['celery_task_id'])
    op.create_index('ix_processing_jobs_created_at', 'processing_jobs', ['created_at'])
    op.create_index('ix_processing_jobs_priority_status', 'processing_jobs', ['priority', 'status'])
    
    op.create_index('ix_job_status_history_job_id', 'job_status_history', ['job_id'])
    op.create_index('ix_job_status_history_created_at', 'job_status_history', ['created_at'])
    
    # Add foreign key constraints
    op.create_foreign_key(
        'fk_processing_jobs_audio_file',
        'processing_jobs', 'audio_files',
        ['audio_file_id'], ['id'],
        ondelete='SET NULL'
    )
    
    op.create_foreign_key(
        'fk_job_status_history_job',
        'job_status_history', 'processing_jobs',
        ['job_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Add vector indexing tracking columns to audio_files table
    op.add_column('audio_files', sa.Column('vector_indexed', sa.Boolean, nullable=False, default=False))
    op.add_column('audio_files', sa.Column('vector_indexed_at', sa.DateTime, nullable=True))
    op.add_column('audio_files', sa.Column('graph_indexed', sa.Boolean, nullable=False, default=False))
    op.add_column('audio_files', sa.Column('graph_indexed_at', sa.DateTime, nullable=True))
    op.add_column('audio_files', sa.Column('entities_extracted', sa.Boolean, nullable=False, default=False))
    op.add_column('audio_files', sa.Column('entities_extracted_at', sa.DateTime, nullable=True))
    
    # Create indexes for new columns
    op.create_index('ix_audio_files_vector_indexed', 'audio_files', ['vector_indexed'])
    op.create_index('ix_audio_files_graph_indexed', 'audio_files', ['graph_indexed'])
    op.create_index('ix_audio_files_entities_extracted', 'audio_files', ['entities_extracted'])


def downgrade() -> None:
    """Drop job queue tracking tables."""
    
    # Drop indexes for audio_files new columns
    op.drop_index('ix_audio_files_entities_extracted', 'audio_files')
    op.drop_index('ix_audio_files_graph_indexed', 'audio_files')
    op.drop_index('ix_audio_files_vector_indexed', 'audio_files')
    
    # Drop new columns from audio_files
    op.drop_column('audio_files', 'entities_extracted_at')
    op.drop_column('audio_files', 'entities_extracted')
    op.drop_column('audio_files', 'graph_indexed_at')
    op.drop_column('audio_files', 'graph_indexed')
    op.drop_column('audio_files', 'vector_indexed_at')
    op.drop_column('audio_files', 'vector_indexed')
    
    # Drop foreign key constraints
    op.drop_constraint('fk_job_status_history_job', 'job_status_history', type_='foreignkey')
    op.drop_constraint('fk_processing_jobs_audio_file', 'processing_jobs', type_='foreignkey')
    
    # Drop indexes
    op.drop_index('ix_job_status_history_created_at', 'job_status_history')
    op.drop_index('ix_job_status_history_job_id', 'job_status_history')
    
    op.drop_index('ix_processing_jobs_priority_status', 'processing_jobs')
    op.drop_index('ix_processing_jobs_created_at', 'processing_jobs')
    op.drop_index('ix_processing_jobs_celery_task_id', 'processing_jobs')
    op.drop_index('ix_processing_jobs_audio_file_id', 'processing_jobs')
    op.drop_index('ix_processing_jobs_user_id', 'processing_jobs')
    op.drop_index('ix_processing_jobs_job_type', 'processing_jobs')
    op.drop_index('ix_processing_jobs_status', 'processing_jobs')
    
    # Drop tables
    op.drop_table('job_status_history')
    op.drop_table('processing_jobs')
    
    # Drop enums
    sa.Enum(name='jobtype').drop(op.get_bind())
    sa.Enum(name='jobstatus').drop(op.get_bind())