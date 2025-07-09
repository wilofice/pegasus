"""Add session management tables

Revision ID: 010_add_session_management
Revises: 009_add_extra_data_to_conversation
Create Date: 2025-01-09

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '010_add_session_management'
down_revision = '009_add_extra_data_to_conversation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_sessions table
    op.create_table('user_sessions',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('is_alive', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('user_id')
    )
    
    # Create indexes for user_sessions
    op.create_index('idx_user_session_alive', 'user_sessions', ['user_id', 'is_alive'])
    op.create_index('idx_session_id', 'user_sessions', ['session_id'])
    
    # Create session_transcripts table
    op.create_table('session_transcripts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('transcript_id', sa.String(), nullable=False),
        sa.Column('transcript_content', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for session_transcripts
    op.create_index('idx_session_transcript', 'session_transcripts', ['session_id', 'transcript_id'])
    op.create_index('idx_user_session_active', 'session_transcripts', ['user_id', 'session_id', 'is_active'])
    op.create_index('idx_sent_at', 'session_transcripts', ['sent_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_sent_at', table_name='session_transcripts')
    op.drop_index('idx_user_session_active', table_name='session_transcripts')
    op.drop_index('idx_session_transcript', table_name='session_transcripts')
    
    op.drop_index('idx_session_id', table_name='user_sessions')
    op.drop_index('idx_user_session_alive', table_name='user_sessions')
    
    # Drop tables
    op.drop_table('session_transcripts')
    op.drop_table('user_sessions')