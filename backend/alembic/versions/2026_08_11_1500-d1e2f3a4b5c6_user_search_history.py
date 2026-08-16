"""user search history

Revision ID: d1e2f3a4b5c6
Revises: 93af173722b7
Create Date: 2026-08-11 15:00:00.000000

Añade la tabla `user_search_history`: libros abiertos desde búsquedas,
usado para mostrar búsquedas recientes (máx. 5) del usuario.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = '93af173722b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'user_search_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'book_id',
            sa.Integer(),
            sa.ForeignKey('books.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('clicked_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('user_id', 'book_id', name='uq_user_search_history_user_book'),
    )
    op.create_index(
        'ix_user_search_history_user_clicked',
        'user_search_history',
        ['user_id', 'clicked_at'],
        unique=False,
    )
    op.create_index(
        'ix_user_search_history_user_id',
        'user_search_history',
        ['user_id'],
        unique=False,
    )
    op.create_index(
        'ix_user_search_history_book_id',
        'user_search_history',
        ['book_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_user_search_history_book_id', table_name='user_search_history')
    op.drop_index('ix_user_search_history_user_id', table_name='user_search_history')
    op.drop_index('ix_user_search_history_user_clicked', table_name='user_search_history')
    op.drop_table('user_search_history')
