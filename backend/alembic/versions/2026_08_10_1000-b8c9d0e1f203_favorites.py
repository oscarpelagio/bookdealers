"""favorites: user_catalogs + user_favorite_establishments

Revision ID: b8c9d0e1f203
Revises: a7b8c9d0e1f2
Create Date: 2026-08-10 10:00:00.000000

Añade el contexto FAVORITES de forma aditiva:
- `user_catalogs`: catálogos que usa cada usuario (sustituye el hardcode
  de aladi/ebiblio/catalunya).
- `user_favorite_establishments`: establecimientos favoritos (bibliotecas
  físicas type=LIBRARY y librerías type=BOOK_SHOP).

No modifica ninguna tabla existente.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f203'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'user_catalogs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('catalog_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['catalog_id'], ['catalogs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'user_id', 'catalog_id', name='uq_user_catalogs_user_catalog'
        ),
    )
    op.create_index('ix_user_catalogs_user', 'user_catalogs', ['user_id'])
    op.create_index('ix_user_catalogs_catalog', 'user_catalogs', ['catalog_id'])

    op.create_table(
        'user_favorite_establishments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('establishment_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['establishment_id'], ['establishments.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'user_id',
            'establishment_id',
            name='uq_user_fav_estab_user_estab',
        ),
    )
    op.create_index(
        'ix_user_fav_estab_user', 'user_favorite_establishments', ['user_id']
    )
    op.create_index(
        'ix_user_fav_estab_estab',
        'user_favorite_establishments',
        ['establishment_id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_user_fav_estab_estab', table_name='user_favorite_establishments')
    op.drop_index('ix_user_fav_estab_user', table_name='user_favorite_establishments')
    op.drop_table('user_favorite_establishments')

    op.drop_index('ix_user_catalogs_catalog', table_name='user_catalogs')
    op.drop_index('ix_user_catalogs_user', table_name='user_catalogs')
    op.drop_table('user_catalogs')
