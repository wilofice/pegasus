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
    from sqlalchemy import inspect
    
    # Check what columns already exist
    inspector = inspect(op.get_bind())
    columns = [col['name'] for col in inspector.get_columns('audio_files')]
    
    # Add tag column if it doesn't exist
    if 'tag' not in columns:
        op.add_column('audio_files', sa.Column('tag', sa.String(length=100), nullable=True))
        print("Added 'tag' column")
    else:
        print("Column 'tag' already exists, skipping...")
    
    # Add category column if it doesn't exist
    if 'category' not in columns:
        op.add_column('audio_files', sa.Column('category', sa.String(length=100), nullable=True))
        print("Added 'category' column")
    else:
        print("Column 'category' already exists, skipping...")
    
    # Check what indexes already exist
    indexes = [idx['name'] for idx in inspector.get_indexes('audio_files')]
    
    # Create tag index if it doesn't exist
    tag_index_name = 'ix_audio_files_tag'
    if tag_index_name not in indexes:
        op.create_index(op.f(tag_index_name), 'audio_files', ['tag'], unique=False)
        print("Created tag index")
    else:
        print("Tag index already exists, skipping...")
    
    # Create category index if it doesn't exist  
    category_index_name = 'ix_audio_files_category'
    if category_index_name not in indexes:
        op.create_index(op.f(category_index_name), 'audio_files', ['category'], unique=False)
        print("Created category index")
    else:
        print("Category index already exists, skipping...")


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_audio_files_category'), table_name='audio_files')
    op.drop_index(op.f('ix_audio_files_tag'), table_name='audio_files')
    
    # Drop columns
    op.drop_column('audio_files', 'category')
    op.drop_column('audio_files', 'tag')