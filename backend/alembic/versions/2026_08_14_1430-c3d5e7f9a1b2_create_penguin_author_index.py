"""create_penguin_author_index

Revision ID: c3d5e7f9a1b2
Revises: a2b4c6d8e0f1
Create Date: 2026-08-14 14:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'c3d5e7f9a1b2'
down_revision: Union[str, Sequence[str], None] = 'a2b4c6d8e0f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'penguin_author_index',
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('name_normalized', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('slug', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('thumb', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('author_id'),
    )
    op.create_index(
        op.f('ix_penguin_author_index_name_normalized'),
        'penguin_author_index',
        ['name_normalized'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_penguin_author_index_name_normalized'),
        table_name='penguin_author_index',
    )
    op.drop_table('penguin_author_index')