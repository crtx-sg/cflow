"""Add openspec_tool column to projects table.

Revision ID: 001
Revises:
Create Date: 2024-12-17
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add openspec_tool column with default value 'none'
    op.add_column(
        'projects',
        sa.Column('openspec_tool', sa.String(50), nullable=False, server_default='none')
    )


def downgrade() -> None:
    op.drop_column('projects', 'openspec_tool')
