"""Add conversation_history table and update tags

Revision ID: 006_conversation_history_tags
Revises: 005_fix_metadata_column_conflict
Create Date: 2025-01-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_conversation_history_tags'
down_revision = '005_fix_metadata_column_conflict'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply the migration."""
    
    # 1. Create conversation_history table
    op.create_table(
        'conversation_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('session_id', sa.String(255), nullable=True, index=True),
        sa.Column('user_id', sa.String(255), nullable=True, index=True),
        sa.Column('user_message', sa.Text(), nullable=False),
        sa.Column('assistant_response', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True, index=True),
        sa.Column('extra_data', postgresql.JSONB(), nullable=True),
    )

    # 2. Add PENDING_REVIEW to processing_status enum
    # First create the new enum type
    new_status_enum = postgresql.ENUM(
        'uploaded', 'transcribing', 'pending_review', 'pending_processing', 
        'improving', 'completed', 'failed', 
        name='processingstatus_new'
    )
    new_status_enum.create(op.get_bind())
    
    # Update the column to use the new enum
    op.execute("ALTER TABLE audio_files ALTER COLUMN processing_status TYPE processingstatus_new USING processing_status::text::processingstatus_new")
    
    # Drop the old enum
    op.execute("DROP TYPE processingstatus")
    
    # Rename the new enum
    op.execute("ALTER TYPE processingstatus_new RENAME TO processingstatus")
    
    # 3. Convert tag column to tags array
    # First, create a backup of existing tags in a temporary column
    op.add_column('audio_files', sa.Column('tag_backup', sa.String(100), nullable=True))
    op.execute("UPDATE audio_files SET tag_backup = tag WHERE tag IS NOT NULL")
    
    # Drop the old tag column
    op.drop_column('audio_files', 'tag')
    
    # Add the new tags array column
    op.add_column('audio_files', sa.Column('tags', postgresql.ARRAY(sa.String(100)), nullable=True, default='{}'))
    
    # Migrate data from tag_backup to tags array
    op.execute("""
        UPDATE audio_files 
        SET tags = ARRAY[tag_backup] 
        WHERE tag_backup IS NOT NULL AND tag_backup != ''
    """)
    
    # Drop the backup column
    op.drop_column('audio_files', 'tag_backup')
    
    # Add index on tags
    op.create_index('ix_audio_files_tags', 'audio_files', ['tags'], postgresql_using='gin')


def downgrade() -> None:
    """Revert the migration."""
    
    # 1. Drop conversation_history table
    op.drop_table('conversation_history')
    
    # 2. Revert tags array back to single tag
    op.drop_index('ix_audio_files_tags', 'audio_files')
    
    # Add backup column and migrate first tag from array
    op.add_column('audio_files', sa.Column('tag_backup', sa.String(100), nullable=True))
    op.execute("""
        UPDATE audio_files 
        SET tag_backup = tags[1] 
        WHERE tags IS NOT NULL AND array_length(tags, 1) > 0
    """)
    
    # Drop tags array
    op.drop_column('audio_files', 'tags')
    
    # Restore original tag column
    op.add_column('audio_files', sa.Column('tag', sa.String(100), nullable=True, index=True))
    op.execute("UPDATE audio_files SET tag = tag_backup WHERE tag_backup IS NOT NULL")
    op.drop_column('audio_files', 'tag_backup')
    
    # 3. Revert processing_status enum (remove PENDING_REVIEW)
    old_status_enum = postgresql.ENUM(
        'uploaded', 'transcribing', 'pending_processing', 'improving', 'completed', 'failed',
        name='processingstatus_old'
    )
    old_status_enum.create(op.get_bind())
    
    # Convert any PENDING_REVIEW to PENDING_PROCESSING
    op.execute("UPDATE audio_files SET processing_status = 'pending_processing' WHERE processing_status = 'pending_review'")
    
    # Update the column to use the old enum
    op.execute("ALTER TABLE audio_files ALTER COLUMN processing_status TYPE processingstatus_old USING processing_status::text::processingstatus_old")
    
    # Drop the new enum
    op.execute("DROP TYPE processingstatus")
    
    # Rename back
    op.execute("ALTER TYPE processingstatus_old RENAME TO processingstatus")