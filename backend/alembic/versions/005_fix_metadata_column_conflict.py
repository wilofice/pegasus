"""fix metadata column conflict

Revision ID: 005_fix_metadata_column_conflict
Revises: 004_add_job_queue_tables
Create Date: 2025-07-02 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005_fix_metadata_column_conflict'
down_revision = '004_add_job_queue_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Rename metadata column to status_metadata to avoid SQLAlchemy conflict."""
    # Rename the metadata column to status_metadata
    op.alter_column('job_status_history', 'metadata', new_column_name='status_metadata')


def downgrade() -> None:
    """Rename status_metadata column back to metadata."""
    # Rename the status_metadata column back to metadata
    op.alter_column('job_status_history', 'status_metadata', new_column_name='metadata')