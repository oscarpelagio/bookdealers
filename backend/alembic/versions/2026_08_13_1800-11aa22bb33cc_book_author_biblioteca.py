"""book author_biblioteca column

Revision ID: 11aa22bb33cc
Revises: ff1122334455
Create Date: 2026-08-13 18:00:00.000000

Añade la columna `author_biblioteca` a `books`: encabezado de autor tal y
como lo da la biblioteca (apellido-primero, p. ej. "Solà, Irene"), usado
para construir la búsqueda por autor en el catálogo z39.50.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '11aa22bb33cc'
down_revision: Union[str, Sequence[str], None] = 'ff1122334455'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'books',
        sa.Column('author_biblioteca', sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('books', 'author_biblioteca')
