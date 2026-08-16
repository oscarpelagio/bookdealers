"""create_asteroide_author_index

Revision ID: f6a8b2c4d6e0
Revises: e5f7a9b1c3d5
Create Date: 2026-08-15 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = 'f6a8b2c4d6e0'
down_revision: Union[str, Sequence[str], None] = 'e5f7a9b1c3d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'asteroide_author_index',
        sa.Column('slug', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('name_normalized', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('slug'),
    )
    op.create_index(
        op.f('ix_asteroide_author_index_name_normalized'),
        'asteroide_author_index',
        ['name_normalized'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_asteroide_author_index_name_normalized'),
        table_name='asteroide_author_index',
    )
    op.drop_table('asteroide_author_index')
