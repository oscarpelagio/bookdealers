"""book price column

Revision ID: c9d0e1f20311
Revises: b8c9d0e1f203
Create Date: 2026-08-11 12:00:00.000000

Añade la columna `price` a `books`: precio único del libro en euros,
aportado por el catálogo de todostuslibros.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f20311'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f203'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'books',
        sa.Column('price', sa.Numeric(8, 2), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('books', 'price')
