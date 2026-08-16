"""author_photos table

Revision ID: 4d4e4f505152
Revises: 11aa22bb33cc
Create Date: 2026-08-13 19:00:00.000000

Crea la tabla `author_photos` para la cache de fotos de autor
(primaria per normalized author key, status: found|missing).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4d4e4f505152'
down_revision: Union[str, Sequence[str], None] = '11aa22bb33cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'author_photos',
        sa.Column('author_key', sa.String(), nullable=False),
        sa.Column('photo_url', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('author_key'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('author_photos')