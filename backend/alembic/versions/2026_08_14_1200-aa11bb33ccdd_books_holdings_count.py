"""books holdings_count column

Revision ID: aa11bb33ccdd
Revises: 4d4e4f505152
Create Date: 2026-08-14 12:00:00.000000

Añade `holdings_count` a `books`: número total de unidades (holdings) que el
catálogo tiene del libro. Se rellena en cada búsqueda z39.50 (formato OPAC) y
sirve para ordenar el estante de un autor ("Sus libros" / "Más de") por
popularidad.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'aa11bb33ccdd'
down_revision: Union[str, Sequence[str], None] = '4d4e4f505152'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'books',
        sa.Column('holdings_count', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('books', 'holdings_count')
