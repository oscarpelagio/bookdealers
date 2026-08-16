"""reviews: columna visibility (snapshot ADR-4) + filtrado público

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-06 15:00:00.000000

Corrige la fuga de reviews PRIVATE/FOLLOWERS en la lista pública de un
libro (auditoría P1-1). Aditivo sobre `reviews`:

- Columna `visibility` con snapshot de `privacy_settings.reviews_visibility`
  del autor en el momento de publicar (mismo patrón que `activities`,
  ADR-4).
- Backfill: las reviews existentes copian la visibilidad actual del autor.

`books` y `users` no se tocan.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_VISIBILITY = ["PUBLIC", "FOLLOWERS", "PRIVATE"]


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'reviews',
        sa.Column(
            'visibility',
            postgresql.ENUM(*_VISIBILITY, name='visibility', create_type=False),
            nullable=False,
            server_default='PUBLIC',
        ),
    )
    # Backfill: copia la visibilidad de reviews del autor que exista hoy.
    op.execute(
        """
        UPDATE reviews r
        SET visibility = COALESCE(
            (SELECT ps.reviews_visibility
             FROM privacy_settings ps
             WHERE ps.user_id = r.user_id),
            'PUBLIC')
        """
    )
    # El default vive en el modelo (Python side); se quita el server_default.
    op.alter_column('reviews', 'visibility', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('reviews', 'visibility')
