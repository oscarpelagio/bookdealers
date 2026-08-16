"""lists & collaborators: lists, list_items, list_collaborators

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-05 20:10:00.000000

Añade el contexto LISTS & COLLABORATORS (FASE 7) de forma aditiva:
- `lists` (listas curadas del owner, UNIQUE (owner_id, slug), soft delete)
- `list_items` (libro en lista, UNIQUE (list_id, book_id), book RESTRICT)
- `list_collaborators` (invitación del owner, UNIQUE (list_id, user_id))

No modifica ninguna tabla existente. Tipo enum nuevo (`collaborator_role`);
`visibility` ya existía (FASE 1).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_VISIBILITY = ('PUBLIC', 'FOLLOWERS', 'PRIVATE')
_COLLABORATOR_ROLE = ('EDITOR', 'VIEWER')


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'lists',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('visibility', postgresql.ENUM(*_VISIBILITY, name='visibility', create_type=False), nullable=False),
        sa.Column('slug', sa.String(length=160), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner_id', 'slug', name='uq_lists_owner_slug'),
    )
    op.create_index('ix_lists_owner', 'lists', ['owner_id'], unique=False)

    op.create_table(
        'list_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('list_id', sa.UUID(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('added_by', sa.UUID(), nullable=False),
        sa.Column('note', sa.String(length=200), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['added_by'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['list_id'], ['lists.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('list_id', 'book_id', name='uq_list_items_list_book'),
    )
    op.create_index('ix_list_items_list', 'list_items', ['list_id'], unique=False)
    op.create_index('ix_list_items_book', 'list_items', ['book_id'], unique=False)

    op.create_table(
        'list_collaborators',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('list_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.Enum(*_COLLABORATOR_ROLE, name='collaborator_role'), nullable=False),
        sa.Column('can_add_books', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['list_id'], ['lists.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('list_id', 'user_id', name='uq_list_collaborators_list_user'),
    )
    op.create_index('ix_list_collaborators_list', 'list_collaborators', ['list_id'], unique=False)
    op.create_index('ix_list_collaborators_user', 'list_collaborators', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_list_collaborators_user', table_name='list_collaborators')
    op.drop_index('ix_list_collaborators_list', table_name='list_collaborators')
    op.drop_table('list_collaborators')
    op.execute('DROP TYPE IF EXISTS collaborator_role')
    op.drop_index('ix_list_items_book', table_name='list_items')
    op.drop_index('ix_list_items_list', table_name='list_items')
    op.drop_table('list_items')
    op.drop_index('ix_lists_owner', table_name='lists')
    op.drop_table('lists')
